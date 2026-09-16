"""The hub logs in to a board before writing to its card.

Boards have had their own login since A1-1, and `robot_get` learned to carry a
session: it tries, and on a 401 it logs in and asks again. The UPLOAD path
never learned. So over WiFi every file sent through the hub went out as a
stranger and came back `HTTP Error 401: Unauthorized`, while commands to the
same board worked - which is exactly the shape of a bug nobody can diagnose
from the outside. The user hit it on 2026-09-07 with that line on screen.

Driven against a FAKE BOARD that behaves like the real one: it refuses
anything without a session, accepts the shipped login, and then takes the
file. Asserting on what the board received, not on what the hub says it did.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import qc as F

AREA = "hub"
TITLE = "the hub logs in to a board before putting a file on its card"

GOT = {"tries": 0, "logins": 0, "body": b"", "cookie_seen": ""}
COOKIE = "qcsession"


class Board(BaseHTTPRequestHandler):
    """A board with a login, in thirty lines: 401 until you have a session."""

    def log_message(self, *a):
        pass

    def do_POST(self):                                    # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        if self.path.startswith("/api/login"):
            GOT["logins"] += 1
            self.send_response(200)
            self.send_header("Set-Cookie", "mice_board=%s; Path=/" % COOKIE)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        GOT["tries"] += 1
        if COOKIE not in (self.headers.get("Cookie") or ""):
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ERR log in first")
            return
        GOT["cookie_seen"] = self.headers.get("Cookie") or ""
        GOT["body"] = body
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main                                            # noqa: E402

    srv = HTTPServer(("127.0.0.1", 0), Board)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    dev = "wifi:127.0.0.1:%d" % srv.server_address[1]
    payload = b"RIFF" + bytes(1200)
    try:
        main._board_cookies.clear()                        # noqa: SLF001
        said, blew_up = "", ""
        try:
            said = main.dev_upload(dev, "/music", "qc.wav", payload)
        except Exception as e:                             # noqa: BLE001
            blew_up = repr(e)          # a stranger's upload raises 401 here
    finally:
        srv.shutdown()

    t.ok(not blew_up, "the upload went through", blew_up)
    t.eq(said.strip(), "OK", "and the board said so")
    t.ok(GOT["logins"] >= 1,
         "the hub logged in to the board when it was refused",
         "it used to give up with HTTP Error 401 and tell the user their "
         "upload failed, while commands to the same board worked")
    t.ok(GOT["tries"] >= 2,
         "and asked again as a session, rather than once as a stranger",
         "tries=%s" % GOT["tries"])
    t.contains(GOT["cookie_seen"], COOKIE,
               "the second attempt carried the board's own cookie")
    t.ok(payload in GOT["body"],
         "the file itself arrived, whole, inside the form",
         "%d bytes reached the board" % len(GOT["body"]))
