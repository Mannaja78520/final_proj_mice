"""Prize machines: the hub picks the machine, keeps the rules, logs and tells (A47-2).

Two fake dispensers sit on the fake bus (ids 70 and 71, qc/lib/fake_serial.py
_Gacha), both holding "keychain", 70 standing next to 71. Asserted on the WIRE
(fake_serial.gacha_wire), never on the page's opinion:

  * a prize goes to the asked machine, and the hub waits until it fell;
  * a person past their limit gets no GDISPENSE at all;
  * an empty machine hands over to the next one of the same kind, and the
    answer says where to go (user 2026-10-22: "use another machine and tell
    the person to go there");
  * the admin's force goes out as GDISPENSE FORCE and still counts;
  * a program on this PC may ask; the venue WiFi may not; force needs a login;
  * closing the event reaches every machine and refuses the next prize;
  * webhooks hear "dispensed"; rules come in from a sheet's CSV tabs;
  * the log is a CSV with every prize;
  * Voice (A47-3): every answered question is logged with its topic, and an
    answer a prize rule names gives that prize and says where to get it.
"""
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import fake_serial
import qc as F

AREA = "hub"
TITLE = "prize machines: right machine, rules per person, hand-over when empty, log and webhooks"


def _post(base, path, body, cookie=True):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    if cookie and F._cookie[0]:
        req.add_header("Cookie", F._cookie[0])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _dispenses():
    return [(b, c) for b, c in fake_serial.gacha_wire if c.upper().startswith("GDISPENSE")]


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_gacha_"))
    heard = []

    class Hook(BaseHTTPRequestHandler):
        def do_POST(self):                                   # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            heard.append(json.loads(self.rfile.read(n).decode() or "{}"))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    hook = HTTPServer(("127.0.0.1", F._free_port()), Hook)
    threading.Thread(target=hook.serve_forever, daemon=True).start()
    cfg = {
        "machines": [
            {"id": "g1", "dev": "usb:COM99:70", "label": "ตู้หน้าเวที", "item": "keychain",
             "place": "หน้าเวที", "near": ["g2"]},
            {"id": "g2", "dev": "usb:COM99:71", "label": "ตู้ข้างประตู", "item": "keychain",
             "place": "ข้างประตู"},
        ],
        "items": {"keychain": {"label": "พวงกุญแจ"}},
        "event": {"name": "qc day", "open": True},
        "webhooks": {"dispensed": ["http://127.0.0.1:%d/hook" % hook.server_port]},
        "wait_s": 5,
    }
    (tmp / "gacha.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    os.environ["MICE_GACHA_CONFIG"] = str(tmp / "gacha.json")
    os.environ["MICE_GACHA_DATA"] = str(tmp / "data")
    base, main = F.start_hub()
    fake_serial.reset()
    g = main.hub_api_gacha.gacha()
    g.save_rules({"items": [{"event": "qc day", "item": "keychain", "total": "10", "per_person": "1"}],
                  "people": [{"event": "", "person": "Ann", "item": "*", "times": "3", "special": "yes"}]})
    try:
        code, got = _post(base, "/api/gacha/machine", {"machine": "g1", "cmd": "GSTOCK 1"})
        _post(base, "/api/gacha/machine", {"machine": "g2", "cmd": "GSTOCK 5"})
        t.ok(fake_serial.GACHAS[70].stock == 1 and fake_serial.GACHAS[71].stock == 5,
             "balls set on each board from the hub", (code, got))

        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Bob",
                                                        "app": "qc", "wait": True})
        t.ok(got.get("ok") and got.get("machine") == "g1" and got.get("result") == "done",
             "Bob's prize comes from the asked machine and the hub waits until it fell", got)
        t.ok(_dispenses() == [(70, "GDISPENSE Bob")], "and the board was told exactly that",
             fake_serial.gacha_wire)

        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Bob"})
        t.ok(not got.get("ok") and got.get("reason") == "person limit reached",
             "a second prize for Bob is refused by the per-person rule", got)
        t.ok(len(_dispenses()) == 1, "and no machine was asked to turn", _dispenses())

        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Ann",
                                                        "machine": "g1", "wait": True})
        t.ok(got.get("ok") and got.get("machine") == "g2" and got.get("moved"),
             "the asked machine is empty: the prize comes from the next machine of that kind", got)
        t.ok("ตู้ข้างประตู" in (got.get("message") or ""),
             "and the answer tells the person where to go", got.get("message"))
        t.ok(_dispenses()[-1] == (71, "GDISPENSE Ann"), "the second board turned, not the empty one",
             _dispenses())

        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Bob",
                                                        "force": True, "wait": True})
        t.ok(got.get("ok") and _dispenses()[-1] == (71, "GDISPENSE FORCE Bob"),
             "the admin's extra prize goes out as FORCE", (got, _dispenses()))
        t.ok(g.given(item="keychain", person="Bob") == 2, "and it still counts for Bob",
             g.given(item="keychain", person="Bob"))

        F.logout_qc()
        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Ann"})
        t.ok(code == 200 and got.get("ok"), "a program on this PC may ask for a prize", (code, got))
        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Ann",
                                                        "force": True})
        t.ok(code == 401, "but only a logged-in person may force one", (code, got))
        real = main.is_self
        main.is_self = lambda ip: False                     # a caller on the venue WiFi
        try:
            n = len(_dispenses())
            code, got = _post(base, "/api/gacha/dispense", {"item": "keychain"})
            t.ok(code == 401 and len(_dispenses()) == n,
                 "from the network a prize needs a sign-in, and nothing turns", (code, got))
        finally:
            main.is_self = real
        F.login(base)

        code, got = _post(base, "/api/gacha/event", {"open": False})
        closes = [b for b, c in fake_serial.gacha_wire if c == "GEVENT CLOSE"]
        t.ok(sorted(closes) == [70, 71], "closing the event reaches every machine", closes)
        time.sleep(0.4)
        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Cat"})
        t.ok(got.get("reason") == "event closed", "and the next prize is refused", got)
        _post(base, "/api/gacha/event", {"open": True})

        until = time.time() + 5
        while time.time() < until and not any(h.get("type") == "gacha.dispensed" for h in heard):
            time.sleep(0.1)
        t.ok(any(h.get("type") == "gacha.dispensed" and h.get("result") == "done" for h in heard),
             "the webhook heard that a prize fell", heard[:3])

        g.fetch = lambda url: ("event,item,total,per_person\n,keychain,3,2\n" if "items" in url
                               else "person,item,times,special\nDan,keychain,5,yes\n")
        g.save_cfg({"rules": {"source": "sheet", "sheet_items_csv": "http://sheet/items",
                              "sheet_people_csv": "http://sheet/people"}})
        code, got = _post(base, "/api/gacha/rules/pull", {})
        r = g.rules()
        t.ok(got.get("ok") and r["items"][0]["per_person"] == "2" and r["people"][0]["person"] == "Dan",
             "rules come in from the sheet's two tabs", (got, r))

        code, body = F.get(base + "/api/gacha/log?limit=0&csv=1")
        t.ok(code == 200 and body.count("Bob") >= 2 and "person" in body.splitlines()[0],
             "the log downloads as a CSV with every prize", body[:300])

        # ---- Voice: topic log + an answer that gives a prize (A47-3) ----
        (tmp / "prizes.json").write_text(json.dumps({"enabled": True, "say": True, "rules": [
            {"when": {"topic": "prize"}, "item": "keychain"}]}), encoding="utf-8")
        os.environ["MICE_VOICE_PRIZES"] = str(tmp / "prizes.json")
        os.environ["MICE_QUESTIONS_DATA"] = str(tmp / "voice")
        g.save_rules({"items": [], "people": []})        # the sheet's 3 keychains are given out
        n = len(_dispenses())
        out = json.loads(main.hub_api_gacha.voice_after_ask(
            json.dumps({"text": "ขอรางวัลหน่อยได้ไหม", "person": "Eve"}).encode(),
            json.dumps({"ok": True, "answer": "ได้เลยครับ", "source": "faq", "person": "Eve"},
                       ensure_ascii=False).encode()).decode())
        t.ok(out.get("topic") == "prize" and (out.get("prize") or {}).get("ok"),
             "a prize question is logged as 'prize' and the rule gives one", out)
        t.ok(len(_dispenses()) == n + 1 and _dispenses()[-1][1] == "GDISPENSE Eve",
             "the voice prize reached a board, for the person asking", _dispenses()[-2:])
        t.ok("พวงกุญแจ" in out.get("answer", "") and out["answer"].startswith("ได้เลยครับ"),
             "and the robot's answer says where to get it", out.get("answer"))
        code, got = _post(base, "/api/gacha/voice", {"enabled": False, "rules": [
            {"when": {"topic": "prize"}, "item": "keychain"}]})
        n = len(_dispenses())
        out = json.loads(main.hub_api_gacha.voice_after_ask(
            json.dumps({"text": "ขอรางวัลอีกได้ไหม", "person": "Fay"}).encode(),
            json.dumps({"ok": True, "answer": "ได้", "source": "faq"}).encode()).decode())
        t.ok(code == 200 and "prize" not in out and len(_dispenses()) == n,
             "the page's switch turns voice prizes off, and then nothing turns", (code, out))
        main.hub_api_gacha.voice_after_ask(json.dumps({"text": "ห้องน้ำอยู่ไหน"}).encode(),
                                           json.dumps({"ok": True, "answer": "ทางซ้าย", "source": "faq"}).encode())
        code, body = F.get(base + "/api/questions")
        st = json.loads(body).get("stats", {})
        t.ok(st.get("topic", {}).get("prize") == 2 and st.get("topic", {}).get("directions") == 1
             and st.get("total") == 3, "the Questions tab counts each topic", st.get("topic"))
        code, body = F.get(base + "/api/questions?csv=1")
        t.ok("ห้องน้ำอยู่ไหน" in body and body.splitlines()[0].lstrip("\ufeff").startswith("time,"),
             "and every question downloads as a CSV", body[:200])
    finally:
        for k in ("MICE_VOICE_PRIZES", "MICE_QUESTIONS_DATA"):
            os.environ.pop(k, None)
        hook.shutdown()
        os.environ.pop("MICE_GACHA_CONFIG", None)
        os.environ.pop("MICE_GACHA_DATA", None)
