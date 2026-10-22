"""Prize dispensers (gachapon) on the hub: several machines, one brain (A47-2).

The board (firmware/src/modules/gacha) only counts magnets, turns and refuses
when closed or empty. Everything that needs to know about MORE than one
machine or about PEOPLE lives here:

  * which machine holds which item type, and which machines stand near it;
  * "give item X (to person P)": pick a machine of that type that has stock,
    and when the asked one is empty, use another of the same type and say
    where the person should go (user 2026-10-22);
  * per-event rules: how many of each item, how many times per person, special
    people by their Face_Regonize name, an admin force that still counts;
  * rules kept locally and/or pulled from a Google Sheet (CSV export), with a
    write-back through an Apps Script web app the user owns;
  * every dispense, refusal and stock change logged (CSV + JSON lines), and
    webhooks to other apps (dispensed, empty, out everywhere, refused, jam).

Pure Python, no hub import: the hub hands in how to talk to a board
(`send(dev, cmd) -> reply text`) and how to find a board by name
(`find_dev(name) -> dev or None`), so QC drives this with fake boards.
Settings: config/gacha.json. Rules and logs hold people's names, so they live
in <data>/.local/gacha/ (git-ignored, never under apps/ which needs no login).
"""
import csv
import io
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

DEFAULT_CFG = {
    "machines": [],
    "items": {},
    "event": {"name": "", "open": True},
    "rules": {"source": "local", "sheet_items_csv": "", "sheet_people_csv": "",
              "sheet_write_url": ""},
    "webhooks": {},
    "low_stock": 2,
    "wait_s": 20,
    "messages": {},
}

# Every log row has these columns, in this order (one source for the CSV
# header, the log reader and the sample sheet).
LOG_FIELDS = ["time", "event", "kind", "machine", "item", "person", "app",
              "forced", "by", "result", "seq", "stock", "asked_machine",
              "reason", "message"]

# Sheet / CSV layout for rules. Same names in the local rules.json, the
# sample CSVs in docs/gacha/ and the Google Sheet tabs.
ITEM_COLS = ["event", "item", "total", "per_person", "note"]
PEOPLE_COLS = ["event", "person", "item", "times", "special", "note"]


def _int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


def _yes(v):
    return str(v).strip().lower() in ("1", "yes", "y", "true", "ใช่", "x", "✓")


def _same(a, b):
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def read_json(path, default):
    """A config file with // comments, like every registry in this project."""
    if not Path(path).is_file():
        return json.loads(json.dumps(default))
    try:
        import registry                      # tools/registry.py: the one comment-aware reader
        return registry.load(Path(path)) or {}
    except ImportError:
        txt = Path(path).read_text(encoding="utf-8")
        lines = [ln for ln in txt.splitlines() if not ln.lstrip().startswith("//")]
        return json.loads("\n".join(lines) or "{}")


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def parse_rules_csv(items_text, people_text):
    """Two CSV tables (the sheet's two tabs) -> {"items": [...], "people": [...]}.
    Header names decide the columns, so extra columns or another order are fine."""
    def rows(text, cols):
        out = []
        for r in csv.DictReader(io.StringIO(text or "")):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            if not any(r.get(c) for c in cols[:3]):
                continue
            out.append({c: r.get(c, "") for c in cols})
        return out
    return {"items": rows(items_text, ITEM_COLS), "people": rows(people_text, PEOPLE_COLS)}


def rules_to_csv(rules):
    """The other way, for download and for building the Google Sheet."""
    out = {}
    for key, cols in (("items", ITEM_COLS), ("people", PEOPLE_COLS)):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rules.get(key) or []:
            w.writerow(r)
        out[key] = buf.getvalue()
    return out


class Gacha:
    def __init__(self, cfg_path, data_dir, send, find_dev, fetch=None, post=None,
                 clock=time.time, sleep=time.sleep):
        self.cfg_path = Path(cfg_path)
        self.data = Path(data_dir)
        self.send = send
        self.find_dev = find_dev
        self.fetch = fetch or self._fetch
        self.post = post or self._post
        self.clock = clock
        self.sleep = sleep
        self.lock = threading.RLock()     # one dispense decision at a time
        self.hook_log = []                # last webhook results, for the page

    # ---- files ---------------------------------------------------------------
    @property
    def rules_path(self):
        return self.data / "rules.json"

    @property
    def log_csv(self):
        return self.data / "dispense_log.csv"

    @property
    def log_jsonl(self):
        return self.data / "events.jsonl"

    def cfg(self):
        c = json.loads(json.dumps(DEFAULT_CFG))
        try:
            raw = read_json(self.cfg_path, {})
        except ValueError:
            raw = {}
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(c.get(k), dict):
                c[k].update(v)
            else:
                c[k] = v
        return c

    def save_cfg(self, change):
        """Merge a change from the page into config/gacha.json. -> (ok, why)."""
        if not isinstance(change, dict):
            return False, "settings must be an object"
        with self.lock:
            try:
                raw = read_json(self.cfg_path, {})
            except ValueError as e:
                return False, "config/gacha.json could not be read (%s)" % e
            for k, v in change.items():
                if k not in DEFAULT_CFG:
                    return False, "unknown setting %r" % k
                raw[k] = v
            ids = [m.get("id") for m in raw.get("machines") or []]
            if any(not i for i in ids) or len(ids) != len(set(ids)):
                return False, "every machine needs its own id"
            write_json(self.cfg_path, raw)
        self.log_event({"kind": "settings", "reason": ",".join(sorted(change))})
        return True, ""

    def rules(self):
        try:
            r = read_json(self.rules_path, {"items": [], "people": []})
        except ValueError:
            r = {"items": [], "people": []}
        r.setdefault("items", [])
        r.setdefault("people", [])
        return r

    def save_rules(self, rules, why="edited"):
        if not isinstance(rules, dict):
            return False, "rules must be an object"
        clean = parse_rules_csv(**{k + "_text": v for k, v in rules_to_csv(rules).items()})
        write_json(self.rules_path, clean)
        self.log_event({"kind": "rules", "reason": why,
                        "message": "%d item rows, %d people rows"
                                   % (len(clean["items"]), len(clean["people"]))})
        return True, ""

    # ---- Google Sheet (or any CSV address) ------------------------------------
    def _fetch(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "MiceHub-gacha"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8-sig", errors="replace")

    def _post(self, url, body):
        req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status

    def pull_rules(self):
        """Fetch the sheet's two tabs (CSV export links) and keep them locally."""
        rc = self.cfg()["rules"]
        if not rc.get("sheet_items_csv") and not rc.get("sheet_people_csv"):
            return False, "no sheet address set (rules ▸ sheet links)", None
        try:
            items = self.fetch(rc["sheet_items_csv"]) if rc.get("sheet_items_csv") else ""
            people = self.fetch(rc["sheet_people_csv"]) if rc.get("sheet_people_csv") else ""
        except Exception as e:                                   # noqa: BLE001
            return False, "the sheet could not be read (%s)" % e, None
        rules = parse_rules_csv(items, people)
        self.save_rules(rules, why="pulled from the sheet")
        return True, "", rules

    def push_rules(self):
        """Send the local rules to the user's Apps Script (docs/gacha/apps_script.gs)."""
        url = self.cfg()["rules"].get("sheet_write_url")
        if not url:
            return False, "no write address set (see docs/gacha/README.md)"
        try:
            self.post(url, {"kind": "rules", "rules": self.rules()})
        except Exception as e:                                   # noqa: BLE001
            return False, "the sheet did not take it (%s)" % e
        self.log_event({"kind": "rules", "reason": "pushed to the sheet"})
        return True, ""

    # ---- logging + webhooks -----------------------------------------------------
    def log_event(self, row):
        row = dict(row)
        row.setdefault("time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.clock())))
        row.setdefault("event", self.cfg()["event"].get("name", ""))
        self.data.mkdir(parents=True, exist_ok=True)
        with open(self.log_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if row.get("kind") in ("dispense", "refused", "jam", "done"):
            new = not self.log_csv.is_file()
            with open(self.log_csv, "a", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=LOG_FIELDS, extrasaction="ignore")
                if new:
                    w.writeheader()
                w.writerow({k: row.get(k, "") for k in LOG_FIELDS})
        return row

    def log_rows(self, limit=200):
        if not self.log_csv.is_file():
            return []
        with open(self.log_csv, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        return rows[-limit:] if limit else rows

    def hook(self, kind, payload):
        """POST to every webhook registered for `kind` (config webhooks.<kind>),
        in the background: a slow app must not hold a prize up."""
        urls = self.cfg().get("webhooks", {}).get(kind) or []
        if isinstance(urls, str):
            urls = [urls]
        body = dict(payload, type="gacha." + kind)

        def go(u):
            try:
                st = self.post(u, body)
                res = {"url": u, "kind": kind, "ok": True, "status": st}
            except Exception as e:                               # noqa: BLE001
                res = {"url": u, "kind": kind, "ok": False, "error": str(e)}
            self.hook_log.append(dict(res, time=self.clock()))
            del self.hook_log[:-50]
            self.log_event({"kind": "webhook", "reason": kind,
                            "result": "ok" if res["ok"] else "failed",
                            "message": res.get("error") or u})
        for u in urls:
            threading.Thread(target=go, args=(u,), daemon=True).start()
        return len(urls)

    # ---- machines -----------------------------------------------------------------
    def machine(self, mid):
        for m in self.cfg()["machines"]:
            if _same(m.get("id"), mid):
                return m
        return None

    def dev_of(self, m):
        return m.get("dev") or self.find_dev(m.get("module") or m.get("id"))

    def ask(self, m, cmd):
        dev = self.dev_of(m)
        if not dev:
            raise ConnectionError("machine %s is not reachable" % m.get("id"))
        return self.send(dev, cmd)

    def status_of(self, m):
        """The board's own G? answer, or {"error": why} when it cannot be read."""
        try:
            txt = self.ask(m, "G?")
            st = json.loads(txt[txt.index("{"):])
            return st
        except Exception as e:                                   # noqa: BLE001
            return {"error": str(e)}

    def machines_view(self):
        out = []
        for m in self.cfg()["machines"]:
            st = self.status_of(m)
            out.append(dict(m, live=st))
        return out

    def label(self, m):
        return m.get("label") or m.get("id")

    # ---- rules ----------------------------------------------------------------------
    def _event_rows(self, key):
        ev = self.cfg()["event"].get("name", "")
        return [r for r in self.rules().get(key) or []
                if not r.get("event") or r.get("event") == "*" or _same(r.get("event"), ev)]

    def person_rule(self, person, item):
        """The people row for this person (item-specific beats '*'), or None."""
        best = None
        for r in self._event_rows("people"):
            if not _same(r.get("person"), person):
                continue
            if _same(r.get("item"), item):
                return r
            if not r.get("item") or r.get("item") == "*":
                best = r
        return best

    def item_rule(self, item):
        for r in self._event_rows("items"):
            if _same(r.get("item"), item):
                return r
        return None

    def given(self, item=None, person=None):
        """Prizes handed out THIS event, from the log (forced ones count too)."""
        ev = self.cfg()["event"].get("name", "")
        n = 0
        for r in self.log_rows(limit=0):
            if r.get("kind") != "dispense" or not _same(r.get("event"), ev):
                continue
            if item is not None and not _same(r.get("item"), item):
                continue
            if person is not None and not _same(r.get("person"), person):
                continue
            n += 1
        return n

    def check(self, item, person="", force=False):
        """May `person` have `item` now? -> (ok, reason, detail). No machine moves."""
        cfg = self.cfg()
        if not item and person:
            pr = self.person_rule(person, "")
            item = (pr or {}).get("item") if pr and pr.get("item") not in ("", "*") else ""
        if not item:
            return False, "no item", {"item": item}
        detail = {"item": item}
        if force:
            return True, "", detail
        if not cfg["event"].get("open", True):
            return False, "event closed", detail
        ir = self.item_rule(item)
        total = _int((ir or {}).get("total"), 0)
        if total and self.given(item=item) >= total:
            return False, "item used up for this event", dict(detail, total=total)
        if person:
            pr = self.person_rule(person, item)
            limit = _int(pr.get("times"), 0) if pr and str(pr.get("times", "")).strip() \
                else _int((ir or {}).get("per_person"), 0)
            had = self.given(item=item, person=person)
            detail.update(limit=limit, had=had, special=bool(pr and _yes(pr.get("special"))))
            if limit and had >= limit:
                return False, "person limit reached", detail
        return True, "", detail

    # ---- the one way a prize comes out ---------------------------------------
    def candidates(self, item, asked=None):
        """Machines holding `item`: the asked one first, then its neighbours
        (its `near` list), then any other machine of the same type."""
        ms = [m for m in self.cfg()["machines"] if _same(m.get("item"), item)
              and m.get("enabled", True)]
        first = self.machine(asked) if asked else None
        order = []
        if first and first in ms:
            order.append(first)
            for nid in first.get("near") or []:
                n = self.machine(nid)
                if n in ms and n not in order:
                    order.append(n)
        for m in ms:
            if m not in order:
                order.append(m)
        return order

    def message(self, key, **kw):
        msgs = self.cfg().get("messages") or {}
        txt = msgs.get(key) or DEFAULT_MESSAGES.get(key) or ""
        try:
            return txt.format(**kw)
        except (KeyError, IndexError):
            return txt

    def dispense(self, item="", person="", app="", machine=None, force=False,
                 by="", wait=False):
        """Give one `item`. -> dict with ok, machine, message, seq, ... .

        The asked machine (or the first of the type) is used while it has
        stock; an empty or unreachable one hands over to the next machine of
        the same type, and the answer says where to go (`moved`)."""
        with self.lock:
            ok, why, detail = self.check(item, person, force)
            item = detail.get("item") or item
            base = {"item": item, "person": person, "app": app,
                    "forced": 1 if force else 0, "by": by}
            if not ok:
                row = self.log_event(dict(base, kind="refused", reason=why,
                                          message=self.message("refused_" + why.replace(" ", "_"),
                                                               item=self.item_label(item), person=person)))
                self.hook("refused", row)
                return dict(detail, ok=False, reason=why, message=row["message"])
            asked = machine
            tried = []
            # Read every candidate once. A forced prize still prefers a machine
            # with balls: FORCE skips the count, it does not make an empty box give.
            seen = [(m, self.status_of(m)) for m in self.candidates(item, asked)]
            if force:
                seen.sort(key=lambda ms: ms[1].get("stock") == 0)
            for m, st in seen:
                if st.get("error"):
                    tried.append({"machine": m["id"], "why": "not reachable"})
                    continue
                if st.get("stock") == 0 and not force:
                    tried.append({"machine": m["id"], "why": "empty"})
                    continue
                if st.get("state") not in (None, "idle"):
                    tried.append({"machine": m["id"], "why": "busy"})
                    continue
                cmd = "GDISPENSE " + ("FORCE " if force else "") + (person or app or "hub")
                try:
                    reply = self.ask(m, cmd)
                except Exception as e:                           # noqa: BLE001
                    tried.append({"machine": m["id"], "why": str(e)})
                    continue
                if not reply.startswith("OK"):
                    tried.append({"machine": m["id"], "why": reply})
                    continue
                seq = _int(reply.split("seq=")[1].split()[0], 0) if "seq=" in reply else 0
                stock = _int(reply.split("stock=")[1].split()[0], -1) if "stock=" in reply else -1
                first = asked or (self.candidates(item)[0]["id"] if self.candidates(item) else "")
                moved = bool(first) and not _same(m["id"], first)
                msg = self.message("go_to" if moved else "here", item=self.item_label(item),
                                   machine=self.label(m), place=m.get("place", ""),
                                   person=person, asked=self.label(self.machine(first) or {"id": first}))
                row = self.log_event(dict(base, kind="dispense", machine=m["id"], seq=seq,
                                          stock=stock, result="turning",
                                          asked_machine=first if moved else "", message=msg))
                out = dict(detail, ok=True, machine=m["id"], label=self.label(m),
                           place=m.get("place", ""), seq=seq, stock=stock, moved=moved,
                           asked=first, message=msg, tried=tried)
                self._after(m, item, stock, row)
                break
            else:
                why = "out everywhere" if any(t["why"] == "empty" for t in tried) else "no machine"
                row = self.log_event(dict(base, kind="refused", reason=why,
                                          message=self.message("refused_" + why.replace(" ", "_"),
                                                               item=self.item_label(item))))
                self.hook("refused", row)
                if why == "out everywhere":
                    self.hook("out", {"item": item, "machines": [t["machine"] for t in tried]})
                return dict(detail, ok=False, reason=why, tried=tried, message=row["message"])
        if wait:
            out["result"] = self.wait_done(m, seq)
        else:
            threading.Thread(target=self.wait_done, args=(m, seq), daemon=True).start()
        return out

    def _after(self, m, item, stock, row):
        low = _int(self.cfg().get("low_stock"), 0)
        if stock == 0:
            self.hook("empty", {"machine": m["id"], "label": self.label(m), "item": item})
            others = [c for c in self.candidates(item) if c is not m]
            left = [c for c in others if self.status_of(c).get("stock") not in (0, None)]
            if not left:
                self.hook("out", {"item": item, "machines": [m["id"]] + [c["id"] for c in others]})
        elif low and 0 < stock <= low:
            self.hook("low", {"machine": m["id"], "label": self.label(m), "item": item,
                              "stock": stock})

    def wait_done(self, m, seq):
        """Poll the board until its last dispense is `seq` and finished; log + hook it."""
        end = self.clock() + _int(self.cfg().get("wait_s"), 20)
        res = "unknown"
        while self.clock() < end:
            st = self.status_of(m)
            last = st.get("last") or {}
            if last.get("seq") == seq and last.get("result") not in ("turning", None):
                res = last["result"]
                break
            self.sleep(0.25)
        row = self.log_event({"kind": "done" if res == "done" else "jam", "machine": m["id"],
                              "seq": seq, "result": res, "item": m.get("item", ""),
                              "person": (self.status_of(m).get("last") or {}).get("who", "")})
        self.hook("dispensed" if res == "done" else "jam", row)
        return res

    def item_label(self, item):
        it = (self.cfg().get("items") or {}).get(item) or {}
        return it.get("label") or item

    # ---- every machine at once (start / close an event, stock) -------------------
    def all_machines(self, cmd):
        out = {}
        for m in self.cfg()["machines"]:
            try:
                out[m["id"]] = self.ask(m, cmd)
            except Exception as e:                               # noqa: BLE001
                out[m["id"]] = "ERR %s" % e
        self.log_event({"kind": "machines", "reason": cmd,
                        "message": json.dumps(out, ensure_ascii=False)})
        return out

    def set_event(self, name=None, open_=None, reset=False):
        cfg = read_json(self.cfg_path, {})
        ev = dict(DEFAULT_CFG["event"], **(cfg.get("event") or {}))
        sent = {}
        if name is not None:
            ev["name"] = str(name).strip()[:40]
            sent["name"] = self.all_machines("GEVENT NAME " + ev["name"])
        if open_ is not None:
            ev["open"] = bool(open_)
            sent["open"] = self.all_machines("GEVENT " + ("OPEN" if open_ else "CLOSE"))
        if reset:
            sent["reset"] = self.all_machines("GEVENT RESET")
        cfg["event"] = ev
        write_json(self.cfg_path, cfg)
        return sent

    def stats(self):
        """Counts for the page: per item, per machine, per person, this event."""
        ev = self.cfg()["event"].get("name", "")
        per = {"item": {}, "machine": {}, "person": {}, "app": {}, "refused": {}}
        for r in self.log_rows(limit=0):
            if not _same(r.get("event"), ev):
                continue
            if r.get("kind") == "dispense":
                for k in ("item", "machine", "person", "app"):
                    v = r.get(k) or "-"
                    per[k][v] = per[k].get(v, 0) + 1
            elif r.get("kind") == "refused":
                v = r.get("reason") or "-"
                per["refused"][v] = per["refused"].get(v, 0) + 1
        return per


DEFAULT_MESSAGES = {
    "here": "รับ{item}ที่{machine}ได้เลย",
    "go_to": "{asked}หมดแล้ว เชิญรับ{item}ที่{machine} {place}",
    "refused_event_closed": "ตอนนี้ยังไม่เปิดแจกของ",
    "refused_person_limit_reached": "{person} รับ{item}ครบแล้ว",
    "refused_item_used_up_for_this_event": "{item}หมดสำหรับงานนี้แล้ว",
    "refused_out_everywhere": "{item}หมดทุกตู้แล้ว",
    "refused_no_machine": "ยังไม่มีตู้ที่ใส่{item}",
    "refused_no_item": "ไม่ได้บอกว่าจะให้ของอะไร",
}
