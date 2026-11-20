"""A friend's game that needs its own server is played through the hub (play_proxy.py).

A fake game server stands in for All-Jao-Games' server.cjs (read from their code
2026-11-05): GET / is a page, PUT /api/state/quiz refuses an Origin that is not
http://<Host> (403 as theirs does), GET /api/versions answers JSON, and
/api/gacha/events streams server-sent events. Through the hub:

  * /play/g/ is their page with the win reporter (MICE_PLAY) added;
  * PUT /api/state/quiz from the hub's origin reaches it and is accepted
    (Host and Origin rewritten to the game server's own);
  * /api/versions and the event stream come through; the first event arrives
    while the stream is still open (not buffered);
  * a game server that is down gives 502, not a hung request.
"""
import http.client
import json
import os
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "a friend's game with its own server plays through the hub (page, saves, event stream)"

SEEN = []


class Game(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, "<html><body><p>game</p></body></html>".encode(), "text/html")
        if self.path == "/api/versions":
            return self._send(200, b'{"wheel":1}')
        if self.path == "/api/gacha/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(b"event: gacha.out\ndata: {\"id\":\"e1\"}\n\n")
            self.wfile.flush()
            time.sleep(3)                       # stays open: a buffering proxy would hold the event
            return None
        return self._send(404, b"{}")

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host", ""):
            return self._send(403, b'{"error":"Invalid origin"}')
        SEEN.append((self.path, body))
        return self._send(200, b'{"ok":true}')


def run(t):
    game = ThreadingHTTPServer(("127.0.0.1", F._free_port()), Game)
    threading.Thread(target=game.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % game.server_address[1]
    tmp = Path(tempfile.mkdtemp(prefix="mice_proxy_"))
    (tmp / "partners.json").write_text(json.dumps({"g": {
        "name": "G", "folder": str(tmp), "play": {
            "proxy": url, "proxy_paths": ["/api/state/", "/api/versions", "/api/gacha/events"],
            "inject": "/app/all-jao/link.js", "watch": [{"event": "alljao:win"}]}}}), encoding="utf-8")
    os.environ["MICE_PARTNERS"] = str(tmp / "partners.json")
    try:
        base, main = F.start_hub()
        main.PLAY_GAMES.at = -1e9                       # not the 5 s memory of an earlier hub
        host, port = base.replace("http://", "").split(":")

        def call(method, path, body=None, headers=None):
            c = http.client.HTTPConnection(host, int(port), timeout=10)
            c.request(method, path, body, headers or {})
            r = c.getresponse()
            return c, r

        c, r = call("GET", "/play/g/")
        page = r.read().decode()
        t.ok(r.status == 200 and "<p>game</p>" in page and "window.MICE_PLAY" in page
             and "/app/all-jao/link.js" in page, "their page comes through with the win reporter", page[:200])
        c.close()

        c, r = call("PUT", "/api/state/quiz", b'{"players":[]}',
                    {"Content-Type": "application/json", "Origin": base})
        t.ok(r.status == 200 and SEEN and SEEN[-1] == ("/api/state/quiz", b'{"players":[]}'),
             "a save from the hub's origin is accepted by their origin check and arrives intact",
             (r.status, r.read(), SEEN))
        c.close()

        c, r = call("GET", "/api/versions")
        t.ok(r.status == 200 and json.loads(r.read()) == {"wheel": 1}, "/api/versions comes through")
        c.close()

        t0 = time.time()
        c, r = call("GET", "/api/gacha/events")
        first = r.fp.readline() if r.status == 200 else b""
        t.ok(first.startswith(b"event: gacha.out") and time.time() - t0 < 2.5,
             "the event stream arrives while it is still open", (r.status, first, time.time() - t0))
        c.close()

        game.shutdown()
        game.server_close()
        c, r = call("GET", "/api/versions")
        t.ok(r.status == 502, "a game server that is down gives 502 at once", r.status)
        c.close()
    finally:
        os.environ.pop("MICE_PARTNERS", None)
