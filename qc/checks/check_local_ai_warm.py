"""The local model is loaded before the first visitor asks (warm-up).

PC measurement 2026-11-21: the first Thai question on an unloaded Ollama took
45 s (model load), the next ones 0.18 s. local_ai.warm() sends the empty
/api/generate that loads it. Proven with a stand-in server that records what it
was asked: it gets the model name and nothing else, a missing server is not an
error, and no model installed is said in plain words.
"""
import http.server
import json
import sys
import threading

import qc as F

AREA = "voice"
TITLE = "the local AI model is loaded ahead of the first question"


def run(t):
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import local_ai                                           # noqa: E402
    seen = []
    models = [{"name": "tiny-model"}]

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"models": models}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            seen.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    prov = {"base": "http://127.0.0.1:%d/v1" % srv.server_address[1]}
    ok, why = local_ai.warm(prov, {})
    t.ok(ok and seen == [("/api/generate", {"model": "tiny-model"})],
         "with no model named it loads the first one the server has", "%s %s %s" % (ok, why, seen))
    seen.clear()
    local_ai.warm(prov, {"model": "named"})
    t.ok(seen == [("/api/generate", {"model": "named"})], "a named model is the one loaded", str(seen))
    models.clear()
    ok, why = local_ai.warm(prov, {})
    t.ok(not ok and "no model" in why, "no model installed is said plainly", "%s %s" % (ok, why))
    srv.shutdown(); srv.server_close()
    ok, why = local_ai.warm(prov, {"model": "x"})
    t.ok(not ok and why, "a server that is not there is a quiet 'no', not a crash", "%s %s" % (ok, why))
