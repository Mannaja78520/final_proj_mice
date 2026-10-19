"""Their page's proxy never becomes the face app's api address.

partner_launch.live() follows where their parts really printed they answer,
because their ports can move with any update. But their page (Vite) PROXIES
/api to the backend, so it answers /api/health with JSON as well, and being
started last it won: the watcher sent every frame through the proxy - /api/look
2.1-2.3 s instead of 0.08-0.17 s, empty bodies ("Expecting value"), and the
live feed timed out (PC, 2026-10-19, main 617a30f).

Held here, with two throwaway servers that both answer health with JSON:
  * the configured api wins while it answers;
  * an address on the page's own port is the page, never the api;
  * a backend that really moved port is still followed.
"""
import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import qc as F

AREA = "hub"
TITLE = "their page's proxy never becomes the face app's api"


class _Health(BaseHTTPRequestHandler):
    """Answers /api/health with JSON, like their backend and their Vite proxy."""

    def log_message(self, *a):
        pass

    def do_GET(self):                                        # noqa: N802
        json_ok = self.path.startswith("/api/")
        body = b'{"status": "ok"}' if json_ok else b"<!doctype html><div id=root>"
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if json_ok else "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_port


def _dead_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    import partner_launch as PL                             # noqa: E402
    back, bport = _serve()
    page, pport = _serve()
    other, oport = _serve()             # another backend copy, printed later
    pid = "qc_live_%d" % bport
    memo = PL._memo_path(pid)
    try:
        entry = {"open": "http://localhost:%d" % pport, "api": "http://127.0.0.1:%d" % bport,
                 "health": "/api/health"}
        # The PC's memo, in the order it was written: the page started last.
        memo.write_text(json.dumps({"urls": {
            "npm run dev": "http://localhost:%d" % pport,
            "uvicorn": "http://127.0.0.1:%d" % bport,
            "npm run dev -- --host 0.0.0.0": "http://localhost:%d/" % pport,
            "uvicorn --port": "http://127.0.0.1:%d" % oport}}),
            encoding="utf-8")
        got = PL.live(pid, entry)
        t.eq(got["api"], "http://127.0.0.1:%d" % bport,
             "the configured api is kept while it answers, page or no page")
        t.eq(got["open"], "http://localhost:%d" % pport, "and the page is the page")

        # Their backend moved: the configured port is silent. The new one is
        # followed - and still never the page's proxy.
        other.shutdown()
        other.server_close()
        entry["api"] = "http://127.0.0.1:%d" % _dead_port()
        got = PL.live(pid, entry)
        t.eq(got["api"], "http://127.0.0.1:%d" % bport,
             "a backend that moved port is followed, not the page's proxy")
        t.eq(got["open"], "http://localhost:%d" % pport,
             "and a part that stopped answering is not taken for the page")

        back.shutdown()
        back.server_close()
        got = PL.live(pid, entry)
        t.ok(got["api"] != "http://localhost:%d" % pport,
             "with their backend down, the page's proxy is still not the api", got)
    finally:
        page.shutdown()
        memo.unlink(missing_ok=True)
