"""The local AI (Ollama) starts when it is first needed, not by hand and not at login.

Asked 2026-11-20: opening it by hand after every reboot was a chore; the user
chose "open it when it is used" over a Windows-login startup. Proven with a
stand-in server (a tiny script that answers on a free port): it is down, the
first call starts it hidden and waits, a second call does not start another,
a start that never answers gives up with a plain sentence and is not retried
for a minute, and the real think call goes through the same wake-up.
"""
import socket
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "voice"
TITLE = "the local AI starts itself on first use and gives up politely"

FAKE = '''
import http.server, os, sys, threading
threading.Timer(45, lambda: os._exit(0)).start()   # the stand-in ends itself
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
'''


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def run(t):
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import local_ai                                           # noqa: E402
    import providers                                          # noqa: E402
    tmp = Path(tempfile.mkdtemp(prefix="qc_localai_"))
    (tmp / "fake.py").write_text(FAKE, encoding="utf-8")
    port = free_port()
    url = "http://127.0.0.1:%d/api/tags" % port
    prov = {"autoStart": {"command": ["{python}", str(tmp / "fake.py"), str(port)],
                          "ready": url, "waitSeconds": 15}}
    t.ok(local_ai.wake({}) == (True, ""), "a provider without autoStart is left alone", "")
    t.ok(not local_ai.is_up(url), "it starts out down", url)
    t0 = time.time()
    up, why = local_ai.wake(prov)
    t.ok(up and local_ai.is_up(url), "the first use starts it and waits until it answers",
         "%s %s %.1fs" % (up, why, time.time() - t0))
    t0 = time.time()
    t.ok(local_ai.wake(prov) == (True, "") and time.time() - t0 < 3,
         "the second use is instant and starts nothing", "")

    bad = {"autoStart": {"command": ["{python}", "-c", "pass"], "ready": "http://127.0.0.1:%d/x" % free_port(),
                         "waitSeconds": 2}}
    up, why = local_ai.wake(bad)
    t.ok(not up and "did not answer" in why, "a start that never answers says so in plain words", why)
    t0 = time.time()
    up2, why2 = local_ai.wake(bad)
    t.ok(not up2 and time.time() - t0 < 1.5 and "try again" in why2,
         "and is not retried for a minute (answers stay quick)", why2)

    seen = []
    real = local_ai.wake
    local_ai.wake = lambda p: (seen.append(p), (False, "stand-in: down"))[1]
    try:
        text, err = providers.openai_think({"base": "http://127.0.0.1:9/v1", "autoStart": {"x": 1}},
                                           "", {"model": "m"}, "s", [], 10, 3)
    finally:
        local_ai.wake = real
    t.ok(text is None and err == "stand-in: down" and len(seen) == 1,
         "a real think call goes through the same wake-up first", (text, err, len(seen)))
