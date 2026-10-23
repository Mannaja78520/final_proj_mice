"""Prize machines: tabs, and a pasted Google Sheet the hub READS and WRITES (A47-14, A47-15).

User 2026-10-23: "ขอเป็น tab ... และขอให้แก้ไฟล์ใน google sheet ได้ด้วยถ้าเอาลิ้งมาใส่".
Google is faked by two local servers, and every assert is on what reached
the fake sheet, never on what the page says:

  * script way: a fake Apps Script web app that keeps tabs in memory and,
    like apps/gacha/sheet_script.gs, refuses a wrong secret. The script text
    the hub hands out carries the hub's own secret (never the placeholder);
    a tab written from the page lands exactly; rules pushed and pulled go
    through the items/people tabs; "every saved rule goes to the sheet" and
    "each prize is a row" really write; a script with another secret writes
    nothing and the hub says so.
  * service way: a fake token server checks the RS256 signature with the key
    file's public half, and a fake Sheets API takes the bearer token: a tab
    written that way lands too (skipped when cryptography is not installed).
  * link way only reads: a write is refused in words, nothing is sent.
  * logged out, the sheet routes and the script (it holds the secret) are 401.
  * the page: every card sits in a tab of TABS and every tab has a card,
    the tab row is the shared .tabs/.tab look.
"""
import base64
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "prize machines: tabs, and the pasted Google Sheet is read and written"

ROOT = Path(__file__).resolve().parents[2]


def _call(base, path, body=None):
    req = urllib.request.Request(base + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    if F._cookie[0]:
        req.add_header("Cookie", F._cookie[0])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _serve(handler):
    srv = HTTPServer(("127.0.0.1", F._free_port()), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_port


def _until(cond, s=5):
    end = time.time() + s
    while time.time() < end and not cond():
        time.sleep(0.05)
    return cond()


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_gsheet_"))
    script = {"tabs": {}, "secret": None, "calls": []}

    class Script(BaseHTTPRequestHandler):
        """What apps/gacha/sheet_script.gs does, in memory."""
        def do_POST(self):                                   # noqa: N802
            b = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            script["calls"].append(b.get("op"))
            tabs = script["tabs"]
            if b.get("secret") != script["secret"]:
                out = {"ok": False, "error": "wrong secret"}
            elif b.get("op") == "tabs":
                out = {"ok": True, "tabs": list(tabs)}
            elif b.get("op") == "read":
                out = {"ok": True, "rows": tabs.get(b["tab"], [])}
            elif b.get("op") == "write":
                tabs[b["tab"]] = b["rows"]
                out = {"ok": True}
            elif b.get("op") == "append":
                rows = tabs.setdefault(b["tab"], [])
                if not rows and b.get("head"):
                    rows.append(b["head"])
                rows.extend(b["rows"])
                out = {"ok": True}
            else:
                out = {"ok": False, "error": "unknown op"}
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv, script_url = _serve(Script)
    cfg = {"machines": [], "items": {"keychain": {"label": "keychain"}},
           "event": {"name": "qc sheet", "open": True}}
    (tmp / "gacha.json").write_text(json.dumps(cfg), encoding="utf-8")
    os.environ["MICE_GACHA_CONFIG"] = str(tmp / "gacha.json")
    os.environ["MICE_GACHA_DATA"] = str(tmp / "data")
    base, main = F.start_hub()
    F.login(base)
    g = main.hub_api_gacha.gacha()
    link = "https://docs.google.com/spreadsheets/d/1QcSheetIdForMiceHub_abcdefgh/edit#gid=0"
    try:
        # ---- the page: tabs ------------------------------------------------
        page = (ROOT / "apps" / "gacha" / "index.html").read_text(encoding="utf-8")
        tabs = re.findall(r'\["(\w+)", "[^"]+", "[^"]+"\]', page[page.index("const TABS"):page.index("const TAB_LOAD")])
        cards = re.findall(r'<div class="card"([^>]*)>', page)
        named = [re.search(r'data-tab="(\w+)"', c) for c in cards]
        untabbed = [c for c, n in zip(cards, named) if not n and 'id="loginHere"' not in c]
        used = {n.group(1) for n in named if n}
        t.ok(len(tabs) >= 6 and not untabbed and used == set(tabs),
             "every card of the page sits in a tab and every tab shows a card",
             {"tabs": tabs, "cards in tabs": sorted(used), "cards in no tab": untabbed})
        t.ok('<div class="tabbed"><nav id="tabs">' in page and "new Mice.Tabs(" in page,
             "the page is built on the shared Mice.Tabs (side list, one section at a time)", "apps/gacha/index.html")

        # ---- the script the user pastes carries this hub's secret ----------
        code, got = _call(base, "/api/gacha/sheet/script")
        text = got.get("script") or ""
        secret = (tmp / "data" / "sheet_secret.txt").read_text(encoding="utf-8").strip() \
            if (tmp / "data" / "sheet_secret.txt").is_file() else ""
        t.ok(code == 200 and len(secret) > 20 and ("var SECRET = '%s';" % secret) in text
             and "__MICE_SECRET__';" not in text,
             "the script to paste has the hub's own secret filled in", (code, text[:200]))
        script["secret"] = secret

        # ---- script way: write a tab, read it back -------------------------
        code, got = _call(base, "/api/gacha/config", {"rules": {"sheet_link": link, "sheet_write_url": script_url,
                                                                "sheet_way": "auto"}})
        script["tabs"]["notes"] = [["a"]]
        code, view = _call(base, "/api/gacha/sheet")
        t.ok(view.get("way") == "script" and view.get("writes") and "notes" in view.get("tabs", [])
             and view.get("id") == "1QcSheetIdForMiceHub_abcdefgh",
             "a pasted link + the script address: the hub can read and write, and lists the tabs", view)
        rows = [["name", "prize"], ["Ann", "keychain"], ["บี", "สติกเกอร์"]]
        code, got = _call(base, "/api/gacha/sheet/write", {"tab": "notes", "rows": rows})
        t.ok(code == 200 and script["tabs"].get("notes") == rows,
             "a tab edited on the page lands in the sheet exactly", (code, got, script["tabs"].get("notes")))
        code, got = _call(base, "/api/gacha/sheet/read?tab=notes")
        t.ok(got.get("rows") == rows, "and reads back the same", got)

        # ---- rules out to the sheet and back -------------------------------
        g.save_rules({"items": [{"event": "qc sheet", "item": "keychain", "total": "9", "per_person": "1"}],
                      "people": [{"person": "Ann", "item": "*", "times": "2", "special": "yes"}]}, why="qc")
        code, got = _call(base, "/api/gacha/rules/push", {})
        items = script["tabs"].get("items") or []
        t.ok(code == 200 and items[:1] == [["event", "item", "total", "per_person", "note"]]
             and items[1][:4] == ["qc sheet", "keychain", "9", "1"]
             and (script["tabs"].get("people") or [[]])[1][1] == "Ann",
             "the rules are written over the sheet's items and people tabs", (got, script["tabs"]))
        script["tabs"]["items"][1][2] = "4"                  # someone edits the sheet
        code, got = _call(base, "/api/gacha/rules/pull", {})
        t.ok(code == 200 and g.rules()["items"][0]["total"] == "4",
             "a change made in the sheet comes back as the rule", (got, g.rules()))

        _call(base, "/api/gacha/config", {"rules": {"sheet_auto_push": True, "sheet_log": True}})
        code, got = _call(base, "/api/gacha/rules", {"items": [{"item": "keychain", "total": "7"}], "people": []})
        t.ok(_until(lambda: (script["tabs"].get("items") or [[], []])[1][2:3] == ["7"]),
             "with 'every saved rule goes to the sheet', a save on the page reaches the sheet",
             script["tabs"].get("items"))
        g.log_event({"kind": "dispense", "machine": "g1", "item": "keychain", "person": "Ann", "app": "qc"})
        t.ok(_until(lambda: len(script["tabs"].get("log") or []) == 2)
             and script["tabs"]["log"][0][:3] == ["time", "event", "kind"]
             and "Ann" in script["tabs"]["log"][1],
             "with 'each prize is a row', a prize adds a row under a header", script["tabs"].get("log"))
        _call(base, "/api/gacha/config", {"rules": {"sheet_auto_push": False, "sheet_log": False}})

        # ---- a script with another secret writes nothing -------------------
        script["secret"] = "someone-else"
        before = json.dumps(script["tabs"])
        code, got = _call(base, "/api/gacha/sheet/write", {"tab": "notes", "rows": [["x"]]})
        t.ok(code == 502 and not got.get("ok") and "secret" in (got.get("error") or "")
             and json.dumps(script["tabs"]) == before,
             "a script with another secret writes nothing, and the hub says why", (code, got))
        script["secret"] = secret

        # ---- link way: read only -------------------------------------------
        sent = []

        def fake_http(method, url, body=None, headers=None, timeout=20):
            sent.append((method, url))
            return 200, "event,item,total\n,keychain,3\n"
        g.sheet_http = fake_http
        _call(base, "/api/gacha/config", {"rules": {"sheet_way": "link"}})
        code, got = _call(base, "/api/gacha/sheet/read?tab=items")
        t.ok(got.get("rows") == [["event", "item", "total"], ["", "keychain", "3"]]
             and "/d/1QcSheetIdForMiceHub_abcdefgh/gviz/tq?tqx=out:csv&sheet=items" in sent[-1][1],
             "read only: the shared link's CSV of that tab is read", (got, sent))
        n = len(sent)
        code, got = _call(base, "/api/gacha/sheet/write", {"tab": "items", "rows": [["x"]]})
        t.ok(code == 502 and len(sent) == n and "only be read" in (got.get("error") or ""),
             "read only: a write is refused in words and nothing goes out", (code, got))
        g.sheet_http = None

        # ---- service way ---------------------------------------------------
        _service(t, base, g, tmp)

        # ---- logged out ----------------------------------------------------
        F.logout_qc()
        codes = [_call(base, p)[0] for p in ("/api/gacha/sheet", "/api/gacha/sheet/script",
                                             "/api/gacha/sheet/read?tab=notes")]
        codes.append(_call(base, "/api/gacha/sheet/write", {"tab": "notes", "rows": [["x"]]})[0])
        t.ok(codes == [401] * 4 and script["tabs"]["notes"] == rows,
             "logged out, the sheet and its script (the secret) are closed", codes)
        F.login(base)
    finally:
        srv.shutdown()
        os.environ.pop("MICE_GACHA_CONFIG", None)
        os.environ.pop("MICE_GACHA_DATA", None)


def _service(t, base, g, tmp):
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ImportError:
        t.ok(True, "service way skipped: cryptography is not installed here", "")
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = key.public_key()
    api = {"tabs": {}, "auth": []}

    class Google(BaseHTTPRequestHandler):
        def _reply(self, out, code=200):
            data = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            return self.rfile.read(int(self.headers.get("Content-Length") or 0))

        def do_POST(self):                                   # noqa: N802
            if self.path == "/token":
                jwt = urllib.parse.parse_qs(self._body().decode())["assertion"][0]
                h, c, s = jwt.split(".")
                pad = lambda x: base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))
                try:
                    pub.verify(pad(s), (h + "." + c).encode(), padding.PKCS1v15(), hashes.SHA256())
                except Exception:                            # noqa: BLE001
                    return self._reply({"error": "bad signature"}, 400)
                return self._reply({"access_token": "tok-qc", "expires_in": 3600})
            return self._sheets("POST")

        def do_GET(self):                                    # noqa: N802
            return self._sheets("GET")

        def do_PUT(self):                                    # noqa: N802
            return self._sheets("PUT")

        def _sheets(self, method):
            api["auth"].append(self.headers.get("Authorization"))
            if self.headers.get("Authorization") != "Bearer tok-qc":
                return self._reply({"error": {"message": "no token"}}, 401)
            body = json.loads(self._body() or b"{}")
            p = urllib.parse.unquote(self.path.split("/spreadsheets/1QcSheetIdForMiceHub_abcdefgh", 1)[1])
            if p.startswith("?fields"):
                return self._reply({"sheets": [{"properties": {"title": n}} for n in api["tabs"]]})
            if p == ":batchUpdate":
                api["tabs"][body["requests"][0]["addSheet"]["properties"]["title"]] = []
                return self._reply({})
            m = re.match(r"/values/'(.+)'(.*)", p)
            tab, rest = m.group(1), m.group(2)
            if rest == ":clear":
                api["tabs"][tab] = []
            elif method == "PUT":
                api["tabs"][tab] = body["values"]
            elif method == "GET":
                return self._reply({"values": api["tabs"].get(tab, [])})
            return self._reply({})

        def log_message(self, *a):
            pass

    srv, url = _serve(Google)
    try:
        kf = tmp / "data" / "google_service.json"
        kf.write_text(json.dumps({"client_email": "qc@x.iam.gserviceaccount.com", "token_uri": url + "/token",
                                  "private_key": key.private_bytes(
                                      serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()).decode()}), encoding="utf-8")
        _call(base, "/api/gacha/config", {"rules": {"sheet_way": "service", "sheet_api": url}})
        rows = [["name"], ["Cat"]]
        code, got = _call(base, "/api/gacha/sheet/write", {"tab": "guests", "rows": rows})
        t.ok(code == 200 and api["tabs"].get("guests") == rows and "Bearer tok-qc" in api["auth"],
             "service account: a signed sign-in, then the tab lands in the sheet", (code, got, api))
        code, got = _call(base, "/api/gacha/sheet/read?tab=guests")
        t.ok(got.get("rows") == rows, "service account: and reads back", got)
    finally:
        srv.shutdown()
        _call(base, "/api/gacha/config", {"rules": {"sheet_way": "auto", "sheet_api": ""}})
