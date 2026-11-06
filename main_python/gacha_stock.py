"""Stock both ways, play only, other sources and the random box (Gacha mixin).

Split out of gacha.py so that file keeps one job (the dispense decision):

  stock_view()     what the machines hold now, per kind, with odds. The game
                   asks for it (GET /api/gacha/stock) or is told through the
                   "stock" webhook, so its prize list follows the real stock.
  load()           put stock in: a count for a normal machine, or the count of
                   every item for a random box. Tells the board (GSTOCK).
  give()           the one door for a program: source rules, play only, then
                   dispense. A game's win comes in through game_event().
  draw()           a random box: the machine turns, the hub picks WHICH item
                   it was, weighted by what is left of each.

Everything is data (config/gacha.json): `play_only` {source: true}, `sources`
{name: {label, enabled, items}}, a machine's `mode`. The hub keeps the random
boxes' counts in <data>/boxes.json; the board only counts balls.
"""
import json
import random
import threading
from pathlib import Path

# Added to gacha.DEFAULT_MESSAGES (overridable in config "messages").
MESSAGES = {
    "drawn": "ได้{drawn}! รับที่{machine}",
    "play_only": "เล่นเพื่อความสนุก ไม่แจกของจริง",
    "refused_source_closed": "ช่องทางนี้ปิดอยู่",
    "refused_source_item": "ช่องทางนี้แจก{item}ไม่ได้",
    "refused_box_empty": "ตู้สุ่มหมดแล้ว",
}

# A machine's mode -> the method that gives. One entry per mode; a new mode is
# a method here, nothing else changes (the page lists whatever the hub names).
MODES = {"normal": "dispense", "random": "draw"}


def _n(v, default=0):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


class GachaStock:
    """Mixed into gacha.Gacha: uses its cfg(), machine(), status_of(), ask(),
    dispense(), check(), game_item(), game_win(), hook(), log_event(), lock."""

    _box_lock = threading.RLock()

    # ---- the random boxes' counts ---------------------------------------------------
    @property
    def boxes_path(self):
        return self.data / "boxes.json"

    def boxes(self):
        try:
            d = json.loads(self.boxes_path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_boxes(self, boxes):
        self.data.mkdir(parents=True, exist_ok=True)
        tmp = self.boxes_path.with_name("boxes.json.tmp")
        tmp.write_text(json.dumps(boxes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.boxes_path)

    def mode_of(self, m):
        mode = str((m or {}).get("mode") or "normal").lower()
        return mode if mode in MODES else "normal"

    # ---- what is in stock ------------------------------------------------------------
    def stock_view(self, source=""):
        """-> {items: [{item, label, stock, weight, odds, available, machines}], ...}

        stock None = a machine that does not count (never empty). A kind with
        an event total is capped to what the total still allows. `odds` is the
        share of the kinds that can be won now; a game may use it as its chance."""
        cfg = self.cfg()
        boxes = self.boxes()
        per = {}                                      # item -> {"stock", "machines"}

        def add(item, n, mid):
            e = per.setdefault(item, {"stock": 0, "machines": [], "uncounted": False})
            if n is None:
                e["uncounted"] = True
            else:
                e["stock"] += max(0, n)
            if mid not in e["machines"]:
                e["machines"].append(mid)

        for m in cfg["machines"]:
            if m.get("enabled", True) is False:
                continue
            st = self.status_of(m)
            live = None if st.get("error") else st.get("stock", -1)
            if live is not None and live < 0:
                live = None                           # board is not counting
            if self.mode_of(m) == "random":
                for item, n in (boxes.get(m["id"]) or {}).items():
                    add(item, _n(n) if live != 0 else 0, m["id"])
            elif m.get("item"):
                add(m["item"], 0 if st.get("error") else live, m["id"])
        for item in cfg["items"]:
            per.setdefault(item, {"stock": 0, "machines": [], "uncounted": False})
        allowed = self.source_items(source)
        rows = []
        for item, e in per.items():
            if allowed and item not in allowed:
                continue
            n = None if e["uncounted"] else e["stock"]
            ir = self.item_rule(item)
            total = _n((ir or {}).get("total"), 0)
            if total:
                left = max(0, total - self.given(item=item))
                n = left if n is None else min(n, left)
            meta = cfg["items"].get(item) or {}
            weight = n if n is not None else _n(meta.get("weight"), 1)
            rows.append({"item": item, "label": meta.get("label") or item, "stock": n,
                         "weight": max(0, weight), "available": weight > 0,
                         "machines": e["machines"]})
        pool = sum(r["weight"] for r in rows if r["available"]) or 0
        for r in rows:
            r["odds"] = round(r["weight"] / pool, 4) if pool and r["available"] else 0.0
        return {"ok": True, "items": rows, "event": cfg["event"],
                "play_only": self.play_only_for(source)}

    def push_stock(self, why=""):
        """Tell the apps on webhooks.stock what is in stock now (background:
        the boards are read, which a prize must not wait for)."""
        urls = self.cfg().get("webhooks", {}).get("stock")
        if not urls:
            return 0

        def go():
            view = self.stock_view()
            self.hook("stock", {"stock": view["items"], "why": why})
        threading.Thread(target=go, daemon=True).start()
        return 1

    # ---- loading stock ---------------------------------------------------------------
    def load(self, mid, count=None, items=None, mode="set", by=""):
        """Put stock into a machine. A normal machine takes `count`; a random
        box takes `items` {item: count} (or [{item, count}]). mode "set" says
        what is in there now, "add" puts more in. -> dict with ok, reply, box."""
        m = self.machine(mid)
        if not m:
            return {"ok": False, "reason": "no such machine"}
        add = str(mode).lower() == "add"
        with self._box_lock:
            if self.mode_of(m) == "random":
                if isinstance(items, list):
                    items = {str(r.get("item")): r.get("count") for r in items if isinstance(r, dict)}
                if not isinstance(items, dict):
                    return {"ok": False, "reason": "a random box needs the count of each item"}
                boxes = self.boxes()
                box = dict(boxes.get(mid) or {}) if add else {}
                for item, n in items.items():
                    n = max(0, _n(n))
                    box[str(item)] = box.get(str(item), 0) + n if add else n
                box = {k: v for k, v in box.items() if v > 0}
                boxes[mid] = box
                self._save_boxes(boxes)
                total = sum(box.values())
                cmd = "GSTOCK ADD %d" % sum(max(0, _n(n)) for n in items.values()) if add \
                    else "GSTOCK %d" % total
            else:
                if count is None:
                    return {"ok": False, "reason": "how many to put in"}
                box = None
                cmd = "GSTOCK %s%d" % ("ADD " if add else "", max(0, _n(count)))
            try:
                reply = self.ask(m, cmd)
            except Exception as e:                               # noqa: BLE001
                reply = "ERR %s" % e
            ok = reply.startswith("OK")
            self.log_event({"kind": "load", "machine": mid, "by": by, "reason": cmd,
                            "result": "ok" if ok else "failed",
                            "message": json.dumps(box, ensure_ascii=False) if box is not None else reply})
        self.push_stock("load")
        return {"ok": ok, "reply": reply, "box": box, "machine": mid}

    # ---- play only and sources ---------------------------------------------------------
    def play_only_for(self, source="", rule=None, override=None):
        """Is this request only for play (nothing real is given)? The request's
        own flag wins (one session), then the rule, then config play_only for
        the source ("game:quiz", an app name), then its "*"."""
        if override is not None and override != "":
            return str(override).strip().lower() in ("1", "true", "yes", "y", "on")
        if isinstance(rule, dict) and rule.get("play_only") not in (None, ""):
            return str(rule["play_only"]).strip().lower() in ("1", "true", "yes", "y", "on")
        po = self.cfg().get("play_only") or {}
        for key in (str(source or ""), "*"):
            if key in po:
                return bool(po[key])
        return False

    def source_items(self, source):
        """The kinds a source may ask for (empty = any). A source nobody wrote
        down is allowed, so a new program needs no entry to work."""
        s = (self.cfg().get("sources") or {}).get(str(source or "")) or {}
        return [str(i) for i in s.get("items") or []]

    def source_ok(self, source, item):
        s = (self.cfg().get("sources") or {}).get(str(source or ""))
        if s is None:
            return True, ""
        if s.get("enabled", True) is False:
            return False, "source closed"
        allowed = self.source_items(source)
        if allowed and item and item not in allowed:
            return False, "source item"
        return True, ""

    def give(self, item="", person="", app="", machine=None, force=False, by="",
             wait=False, play_only=None):
        """The door for a program: the source's rules, play only, then the
        machine (a random box also says which item came out). -> dispense answer."""
        ok, why = self.source_ok(app, item)
        if not ok:
            row = self.log_event({"kind": "refused", "item": item, "person": person, "app": app,
                                  "by": by, "reason": why,
                                  "message": self.message("refused_" + why.replace(" ", "_"),
                                                          item=self.item_label(item))})
            return {"ok": False, "reason": why, "message": row["message"]}
        if self.play_only_for(app, override=play_only):
            return self._pretend(item, person, app, force, by)
        m = self.machine(machine) if machine else None
        if m and self.mode_of(m) == "random":
            return self.draw(machine, person=person, app=app, force=force, by=by, wait=wait)
        return self.dispense(item=item, person=person, app=app, machine=machine,
                             force=force, by=by, wait=wait)

    def _pretend(self, item, person, app, force, by):
        """Play only: the rules are asked, the machine is not moved."""
        ok, why, detail = self.check(item, person, force)
        item = detail.get("item") or item
        msg = self.message("play_only")
        self.log_event({"kind": "playonly", "item": item, "person": person, "app": app,
                        "by": by, "reason": "" if ok else why, "result": "pretend", "message": msg})
        return dict(detail, ok=ok, play_only=True, reason=why, item=item,
                    label=self.item_label(item), message=msg)

    # ---- a game says someone won -------------------------------------------------------
    def game_event(self, game, result, person="", ref="", by="game", total=None,
                   item="", play_only=None):
        """A win from a game. `item` = the game already chose from the stock
        list the hub gave it (a kind the hub knows); otherwise the rules
        (games_skip, score range) decide as before. -> the answer."""
        game = str(game or "").strip()
        source = "game:" + game
        direct = str(item or "").strip()
        if direct and direct not in self.cfg()["items"]:
            direct = ""
        rule = {"item": direct} if direct else self.game_item(game, result, total)
        if not rule or not rule.get("item"):
            return self.game_win(game, result, person=person, ref=ref, by=by, total=total)
        pretend = self.play_only_for(source, rule=rule, override=play_only)
        if not pretend and not direct:
            return self.game_win(game, result, person=person, ref=ref, by=by, total=total)
        key = game + ":" + str(ref) if ref else ""
        with self.lock:
            if key and key in self.wins_seen:
                return {"ok": True, "repeat": True, "message": ""}
            if key:
                self.wins_seen = (self.wins_seen + [key])[-500:]
        who = person or rule.get("person") or ""
        if pretend:
            return self._pretend(rule["item"], who, source, False, by)
        return self.give(item=rule["item"], person=who, app=source,
                         machine=rule.get("machine") or None, by=by)

    # ---- the random box ----------------------------------------------------------------
    def pick(self, mid, rng=random):
        """Weighted pick from a box by what is left of each. -> item or None."""
        box = {k: v for k, v in (self.boxes().get(mid) or {}).items() if _n(v) > 0}
        if not box:
            return None
        items = list(box)
        return rng.choices(items, weights=[box[i] for i in items], k=1)[0]

    def draw(self, mid, person="", app="", force=False, by="", wait=False):
        """Turn a random box. A box with nothing left is refused (FORCE skips
        that; the board's own stock still rules). The item is picked in
        settle_draw, which dispense() calls for every machine that gave."""
        m = self.machine(mid)
        if not m or self.mode_of(m) != "random":
            return {"ok": False, "reason": "not a random box"}
        if not force and not any(_n(v) > 0 for v in (self.boxes().get(mid) or {}).values()):
            row = self.log_event({"kind": "refused", "machine": mid, "item": m.get("item", ""),
                                  "person": person, "app": app, "by": by, "reason": "box empty",
                                  "message": self.message("refused_box_empty")})
            self.hook("empty", {"machine": mid, "label": self.label(m), "item": m.get("item", "")})
            return {"ok": False, "reason": "box empty", "message": row["message"]}
        return self.dispense(item=m.get("item", ""), person=person, app=app, machine=mid,
                             force=force, by=by, wait=wait)

    def settle_draw(self, out, person="", app="", by="", rng=random):
        """Called by dispense() after a machine gave: when that machine is a
        random box, pick which item it was (weighted by what is left) and take
        one off its count. The answer gets `drawn`, `drawn_label`, a new message."""
        m = self.machine(out.get("machine"))
        if not m or self.mode_of(m) != "random":
            return out
        with self._box_lock:
            boxes = self.boxes()
            drawn = self.pick(m["id"], rng)
            if drawn:
                boxes[m["id"]][drawn] = _n(boxes[m["id"]][drawn]) - 1
                boxes[m["id"]] = {k: v for k, v in boxes[m["id"]].items() if v > 0}
                self._save_boxes(boxes)
        label = self.item_label(drawn) if drawn else ""
        out.update(drawn=drawn or "", drawn_label=label)
        if drawn:
            out["message"] = self.message("drawn", drawn=label, machine=out.get("label", ""))
        self.log_event({"kind": "draw", "machine": m["id"], "item": drawn or "", "person": person,
                        "app": app, "by": by, "seq": out.get("seq", ""), "message": out.get("message", "")})
        self.push_stock("draw")
        return out
