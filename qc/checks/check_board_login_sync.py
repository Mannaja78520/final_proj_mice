"""The hub finds a login a board accepts: the hub's own, then the known ones.

Bench 2026-09-17, nong #67 in the lab: RS485 moved the arm, WiFi did not.
The board had only the old account manny/12345678 and the hub tried only
admin/admin123, so every JOINT/POSE from Nong Studio came back
`refused the login for "admin"` while PING and status (open) worked.

The user asked for two things: log in to the hub and the module logs in too,
and boards on older logins must still work. So the hub tries, in order, the
account typed into the hub, then config/board_logins.json.

Driven against a FAKE BOARD that accepts only the accounts it is told to,
asserting on the login and the command the board RECEIVED.
"""
import json
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import qc as F

AREA = "hub"
TITLE = "the hub logs in to a board with the hub login or a known board login"

COOKIE = "qclogin"
BOARD = {"accept": set(), "logins": [], "cmds": []}


class Board(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):                                    # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        form = urllib.parse.parse_qs((self.rfile.read(n) if n else b"").decode())
        pair = ((form.get("user") or [""])[0], (form.get("pass") or [""])[0])
        BOARD["logins"].append(pair)
        if pair not in BOARD["accept"]:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"ERR auth")
            return
        self.send_response(200)
        self.send_header("Set-Cookie", "mice_board=%s; Path=/" % COOKIE)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def do_GET(self):                                     # noqa: N802
        if COOKIE not in (self.headers.get("Cookie") or ""):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"ERR log in first")
            return
        BOARD["cmds"].append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK WAIST=90.0 T=80ms")


def _move(main, dev):
    main._board_cookies.clear()                           # noqa: SLF001
    try:
        return main.dev_cmd(dev, "JOINT WAIST 90"), ""
    except Exception as e:                                # noqa: BLE001
        return "", str(e)


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main                                           # noqa: E402

    srv = HTTPServer(("127.0.0.1", 0), Board)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dev = "wifi:127.0.0.1:%d" % srv.server_address[1]
    saved = dict(main._hub_login)                         # noqa: SLF001
    try:
        # 1. a board still on the OLD shipped login, nobody logged in to the hub
        main._hub_login.update(user="", password="")      # noqa: SLF001
        BOARD.update(accept={("manny", "12345678")}, logins=[], cmds=[])
        said, err = _move(main, dev)
        t.ok(not err and said.startswith("OK"),
             "a board on the old login manny/12345678 takes a move over WiFi",
             "hub said: %s | board saw logins %r" % (err, BOARD["logins"]))
        t.ok(any("JOINT" in urllib.parse.unquote(c) for c in BOARD["cmds"]),
             "and the JOINT command reached the board", repr(BOARD["cmds"]))

        # 2. the account typed into the hub is tried FIRST
        main._hub_login.update(user="lab", password="labpass99")  # noqa: SLF001
        BOARD.update(accept={("lab", "labpass99")}, logins=[], cmds=[])
        said, err = _move(main, dev)
        t.ok(not err and said.startswith("OK"),
             "a board with the same account as the hub login takes a move",
             "hub said: %s | board saw logins %r" % (err, BOARD["logins"]))
        t.ok(BOARD["logins"][:1] == [("lab", "labpass99")],
             "and the hub login was the first one tried", repr(BOARD["logins"]))

        # 3. nothing fits: say so plainly, and still never crash
        main._hub_login.update(user="", password="")      # noqa: SLF001
        BOARD.update(accept=set(), logins=[], cmds=[])
        said, err = _move(main, dev)
        t.ok("refused every known login" in err and not BOARD["cmds"],
             "a board that refuses every login is reported, not moved",
             "said=%r err=%r" % (said, err))
    finally:
        main._hub_login.clear()                           # noqa: SLF001
        main._hub_login.update(saved)                     # noqa: SLF001
        main._board_cookies.clear()                       # noqa: SLF001
        srv.shutdown()

    # 4. a real login to the hub is what the boards get offered first
    base, hub = F.start_hub()
    hub._hub_login.update(user="", password="")           # noqa: SLF001
    F.login(base)
    first = (hub.board_logins() or [("", "")])[0]
    t.ok(first[1] == F.HUB_PASSWORD and first[0],
         "logging in to the hub puts that account first in the board logins",
         "first board login tried: %r" % (first,))
    cfg = json.loads((F.CODE / "config" / "board_logins.json").read_text(encoding="utf-8"))
    t.ok(("manny", "12345678") in [(e["user"], e["password"]) for e in cfg["logins"]],
         "config/board_logins.json lists the old shipped login", repr(cfg))
