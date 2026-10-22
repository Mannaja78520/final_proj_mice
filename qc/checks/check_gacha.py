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
  * A47-6: the friend's game folder is served at /play/<id>/ with our watcher
    added on the way out (their file on disk unchanged, nothing outside it or
    in .git served); a win reported from a hub page on this PC turns a board,
    the same win twice turns it once, a loss and a foreign site turn nothing.
  * A47-7: an app key lets another PC ask (never force); a removed key stops.
  * A47-8: a voice prize rule tied to an event fits only during that event;
    topics are edited from the page (a broken pattern refused) and pick the
    next question's topic; questions with no saved answer are listed apart.
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


def _post_as(base, path, body, headers):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers=dict({"Content-Type": "application/json"}, **headers))
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
        # ---- A47-6: a win in the friend's game gives a prize ----
        games = tmp / "games"
        (games / ".git").mkdir(parents=True)
        (games / ".git" / "config").write_text("secret", encoding="utf-8")
        page = "<html><body><p>wheel</p></body></html>"
        (games / "index.html").write_text(page, encoding="utf-8")
        (tmp / "outside.txt").write_text("no", encoding="utf-8")
        (tmp / "partners.json").write_text(json.dumps({"games": {
            "name": "Games", "folder": str(games), "play": {
                "inject": "/app/all-jao/link.js",
                "watch": [{"game": "wheel", "key": "w", "list": "logs", "result": "label"}]}}}),
            encoding="utf-8")
        os.environ["MICE_PARTNERS"] = str(tmp / "partners.json")
        code, body = F.get(base + "/play/games/")
        t.ok(code == 200 and "/app/all-jao/link.js" in body and '"game": "wheel"' in body
             and body.index("link.js") < body.index("</body>"),
             "the game page is served with our watcher and its list added", body[:300])
        t.ok((games / "index.html").read_text(encoding="utf-8") == page,
             "and the friend's file on disk is untouched", "")
        bad = [F.get(base + u)[0] for u in ("/play/games/../outside.txt", "/play/games/.git/config",
                                            "/play/nope/")]
        t.ok(all(c in (400, 403, 404) for c in bad), "nothing outside their folder or in .git is served", bad)
        code, body = F.get(base + "/app/all-jao/link.js")
        t.ok(code == 200 and "/api/gacha/game" in body and "MICE_PLAY" in body,
             "the watcher script itself is served", body[:120])

        _post(base, "/api/gacha/machine", {"machine": "g2", "cmd": "GSTOCK 10"})
        g.save_cfg({"games": [{"game": "wheel", "result": "ตุ๊กตา", "item": "keychain", "person": "Gus"}]})
        F.logout_qc()
        here = {"Origin": base, "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
        n = len(_dispenses())
        code, got = _post_as(base, "/api/gacha/game", {"game": "wheel", "result": "ตุ๊กตาหมี", "ref": "r1"}, here)
        t.ok(code == 200 and got.get("ok") and _dispenses()[-1:] == [(71, "GDISPENSE Gus")],
             "a wheel win from the game page on this PC turns a board, no sign-in", (code, got, _dispenses()[-2:]))
        _post_as(base, "/api/gacha/game", {"game": "wheel", "result": "ตุ๊กตาหมี", "ref": "r1"}, here)
        code, got = _post_as(base, "/api/gacha/game", {"game": "wheel", "result": "ลองใหม่", "ref": "r2"}, here)
        t.ok(len(_dispenses()) == n + 1 and code == 200 and not got.get("ok"),
             "the same win twice turns once, and a result with no prize turns nothing", (got, _dispenses()[-3:]))
        code, got = _post_as(base, "/api/gacha/game", {"game": "wheel", "result": "ตุ๊กตา", "ref": "r3"},
                             {"Origin": "http://evil.example", "Sec-Fetch-Site": "cross-site"})
        t.ok(code == 401 and len(_dispenses()) == n + 1, "a foreign website cannot claim a win", (code, got))

        n = len(_dispenses())
        a1 = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "K1"})[1]
        a2 = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "K2"})[1]
        t.ok(a1.get("ok") and a2.get("ok") and len(_dispenses()) == n + 2,
             "two prizes a moment apart are both given: the busy machine is waited for", (a1, a2))

        # ---- A47-10: the asked kind is out; a neighbour holds another kind ----
        F.login(base)
        g.save_cfg({"machines": [
            {"id": "g1", "dev": "usb:COM99:70", "label": "ตู้หน้าเวที", "item": "sticker", "near": ["g2"]},
            {"id": "g2", "dev": "usb:COM99:71", "label": "ตู้ข้างประตู", "item": "keychain", "near": ["g1"]}],
            "items": {"keychain": {"label": "พวงกุญแจ", "instead": ["sticker"]},
                      "sticker": {"label": "สติกเกอร์"}}})
        _post(base, "/api/gacha/machine", {"machine": "g2", "cmd": "GSTOCK 0"})
        _post(base, "/api/gacha/machine", {"machine": "g1", "cmd": "GSTOCK 3"})
        n = len(_dispenses())
        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Lin", "machine": "g2"})
        t.ok(got.get("ok") and got.get("item") == "sticker" and got.get("instead_of") == "keychain"
             and _dispenses()[n:] == [(70, "GDISPENSE Lin")],
             "keychains are out: the machine next door gives its other kind instead", (got, _dispenses()[n:]))
        t.ok("สติกเกอร์" in (got.get("message") or "") and "พวงกุญแจ" in (got.get("message") or ""),
             "and the answer says what ran out and what is given", got.get("message"))
        code, view = F.get(base + "/api/gacha")
        t.ok('"at": "usb:COM99:70"' in view, "each machine carries its address for its own page link", view[:200])
        g.save_cfg({"items": {"keychain": {"label": "พวงกุญแจ"}, "sticker": {"label": "สติกเกอร์"}}})
        time.sleep(0.5)
        n = len(_dispenses())
        code, got = _post(base, "/api/gacha/dispense", {"item": "keychain", "person": "Lin", "machine": "g2"})
        t.ok(not got.get("ok") and got.get("reason") == "out everywhere" and len(_dispenses()) == n,
             "with no substitute named it still says the kind ran out", got)
        g.save_cfg({"machines": cfg["machines"], "items": cfg["items"]})
        _post(base, "/api/gacha/machine", {"machine": "g2", "cmd": "GSTOCK 10"})
        _post(base, "/api/gacha/machine", {"machine": "g1", "cmd": "GSTOCK 0"})
        F.logout_qc()

        # ---- A47-7: app keys for another PC or a form ----
        F.login(base)
        code, made = _post(base, "/api/gacha/keys", {"make": "pc2 game"})
        key = made.get("key", "")
        code, listed = F.get(base + "/api/gacha/keys")
        t.ok(key and "pc2 game" in listed and key not in listed,
             "a key is made once and the list never shows it whole", listed[:200])
        F.logout_qc()
        main.is_self = lambda ip: False                     # another PC on the venue WiFi
        try:
            n = len(_dispenses())
            code, got = _post_as(base, "/api/gacha/dispense", {"item": "keychain", "person": "Hal"},
                                 {"X-Mice-Key": key})
            t.ok(code == 200 and got.get("ok") and _dispenses()[-1] == (71, "GDISPENSE Hal"),
                 "another PC with the key gets a prize", (code, got))
            code, got = _post_as(base, "/api/gacha/dispense?key=" + key, {"item": "keychain", "person": "Ivy"}, {})
            t.ok(code == 200 and got.get("ok"), "the key also works on the address", (code, got))
            code, got = _post_as(base, "/api/gacha/dispense", {"item": "keychain", "force": True},
                                 {"X-Mice-Key": key})
            code2, got2 = _post_as(base, "/api/gacha/dispense", {"item": "keychain"}, {"X-Mice-Key": key + "x"})
            code3, got3 = _post_as(base, "/api/gacha/config", {"games": []}, {"X-Mice-Key": key})
            t.ok(code == 401 and code2 == 401 and code3 == 401 and len(_dispenses()) == n + 2,
                 "a key can never force, a wrong key is refused, and a key cannot change settings",
                 (code, code2, code3))
            F.login(base)
            _post(base, "/api/gacha/keys", {"drop": "pc2 game"})
            F.logout_qc()
            code, got = _post_as(base, "/api/gacha/dispense", {"item": "keychain"}, {"X-Mice-Key": key})
            t.ok(code == 401 and len(_dispenses()) == n + 2, "a removed key stops working", (code, got))
        finally:
            main.is_self = real
            F.login(base)

        # ---- A47-8: a voice prize rule for one event only ----
        _post(base, "/api/gacha/voice", {"enabled": True, "rules": [
            {"when": {"topic": "prize", "event": "another day"}, "item": "keychain"}]})
        n = len(_dispenses())
        out = json.loads(main.hub_api_gacha.voice_after_ask(
            json.dumps({"text": "ขอรางวัลหน่อย", "person": "Jo"}).encode(),
            json.dumps({"ok": True, "answer": "ได้", "source": "faq"}).encode()).decode())
        t.ok("prize" not in out and len(_dispenses()) == n, "a rule for another event gives nothing today", out)
        _post(base, "/api/gacha/voice", {"enabled": True, "rules": [
            {"when": {"topic": "prize", "event": "QC Day"}, "item": "keychain"}]})
        out = json.loads(main.hub_api_gacha.voice_after_ask(
            json.dumps({"text": "ขอรางวัลหน่อย", "person": "Jo"}).encode(),
            json.dumps({"ok": True, "answer": "ได้", "source": "faq"}).encode()).decode())
        t.ok((out.get("prize") or {}).get("ok") and _dispenses()[-1] == (71, "GDISPENSE Jo"),
             "and the same rule for this event gives one", out)

        # ---- A47-8: topics from the page, questions with no saved answer ----
        topics = tmp / "topics.json"
        topics.write_bytes(Path(main.asset("config", "voice_topics.json")).read_bytes())
        os.environ["MICE_VOICE_TOPICS"] = str(topics)
        code, got = F.get(base + "/api/questions/topics")
        t.ok(code == 200 and "directions" in got, "the topic list reads back for the page", got[:120])
        code, got = _post(base, "/api/questions/topics", {"topics": [{"id": "x", "patterns": ["(broken"]}]})
        t.ok(code == 400 and "directions" in topics.read_text(encoding="utf-8"),
             "a broken pattern is refused and the list is kept", (code, got))
        code, got = _post(base, "/api/questions/topics", {"topics": [
            {"id": "parking", "label": "ที่จอดรถ", "patterns": ["จอดรถ"]}]})
        main.hub_api_gacha.voice_after_ask(json.dumps({"text": "จอดรถตรงไหนได้บ้าง"}).encode(),
                                           json.dumps({"ok": True, "answer": "ข้างหลัง", "source": "model"},
                                                      ensure_ascii=False).encode())
        code, body = F.get(base + "/api/questions")
        st = json.loads(body).get("stats", {})
        t.ok(code == 200 and st.get("topic", {}).get("parking") == 1,
             "a topic saved from the page names the next question", st.get("topic"))
        t.ok("จอดรถตรงไหนได้บ้าง" in st.get("unsaved", {}) and "ห้องน้ำอยู่ไหน" not in st.get("unsaved", {}),
             "a question the model answered is listed as needing a saved answer, a saved one is not",
             st.get("unsaved"))
        F.logout_qc()
        code, got = _post(base, "/api/questions/topics", {"topics": []})
        t.ok(code == 401 and "parking" in topics.read_text(encoding="utf-8"),
             "changing topics needs a sign-in", (code, got))
        F.login(base)
    finally:
        os.environ.pop("MICE_PARTNERS", None)
        for k in ("MICE_VOICE_PRIZES", "MICE_QUESTIONS_DATA", "MICE_VOICE_TOPICS"):
            os.environ.pop(k, None)
        hook.shutdown()
        os.environ.pop("MICE_GACHA_CONFIG", None)
        os.environ.pop("MICE_GACHA_DATA", None)
