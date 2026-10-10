"""A fake Face_Regonize that answers what the BRIEF asks of them (system A13).

The brief (Claude Doc "API ที่ขอจาก Face_Regonize", 2026-10-09) proposes
POST /api/look, GET /api/node/{node_id}/present, strangers and call_as. Their
real version has none of it yet, so this fake is written from the brief's own
examples, LITERALLY - not from config/partners.json. That way a typo in our
registry fails a check instead of agreeing with itself. When their version
lands with other names, this file and the registry change together.

`offers` decides which of the new routes its /openapi.json lists, so one fake
plays both their app today (nothing new) and their app after the brief.
Everything that arrived is recorded in `calls`, for asserting on what reached
them rather than on what our code says it sent.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = "tok-friend"


def parse_multipart(body, ctype):
    """{name: bytes} from a multipart/form-data body (stdlib has no parser
    since cgi went away)."""
    boundary = ctype.split("boundary=", 1)[-1].strip().strip('"').encode()
    out = {}
    for part in body.split(b"--" + boundary):
        head, sep, data = part.partition(b"\r\n\r\n")
        if not sep or b'name="' not in head:
            continue
        name = head.split(b'name="', 1)[1].split(b'"', 1)[0].decode()
        out[name] = data[:-2] if data.endswith(b"\r\n") else data
    return out


class FakeFriend:
    def __init__(self, offers=()):
        self.offers = set(offers)
        self.calls = []                 # (method, path, detail)
        self.look_code = 200            # anything else: answered with that code
        self.kept = False               # what /api/look says it kept
        # The brief's own example answer: the nearest face known, one stranger.
        self.look_faces = [
            {"box": [0.05, 0.30, 0.12, 0.44], "face_score": 0.77, "status": "unknown"},
            {"box": [0.41, 0.22, 0.55, 0.47], "face_score": 0.91, "status": "matched",
             "person_id": "u-1", "participant_id": "P0123", "first_name": "Boss",
             "name": "Boss Somchai", "confidence": 0.62, "call_as": "พี่บอส",
             "title": "นาย", "language": "th"},
        ]
        self.present = {"kiosk-1": {
            "node_id": "kiosk-1", "faces_now": 2, "unknown_now": 1,
            "people": [{"participant_id": "P0124", "name": "Far Person", "call_as": "",
                        "title": "", "last_seen": "2026-10-09T13:01:02",
                        "box": [0.10, 0.10, 0.15, 0.17]},
                       {"participant_id": "P0123", "name": "Boss Somchai",
                        "call_as": "พี่บอส", "title": "นาย",
                        "last_seen": "2026-10-09T13:01:02", "box": [0.41, 0.22, 0.55, 0.47]}]}}
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj, code=200):
                raw = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _authed(self):
                return self.headers.get("Authorization") == "Bearer " + TOKEN

            def do_GET(self):                                    # noqa: N802
                u = urlparse(self.path)
                fake.calls.append(("GET", u.path, parse_qs(u.query)))
                if u.path == "/openapi.json":
                    paths = {"/api/recognition/upload": {"post": {"parameters": []}},
                             "/api/node/status": {"get": {}}}
                    if "look" in fake.offers:
                        paths["/api/look"] = {"post": {"requestBody": {}}}
                    if "present" in fake.offers:
                        paths["/api/node/{node_id}/present"] = {"get": {"parameters": [
                            {"name": "node_id", "in": "path"},
                            {"name": "seconds", "in": "query"}]}}
                    return self._send({"openapi": "3.1.0", "paths": paths})
                if u.path == "/api/health":
                    return self._send({"status": "ok"})
                if not self._authed():
                    return self._send({"detail": "Not authenticated"}, 401)
                if u.path.startswith("/api/node/") and u.path.endswith("/present") \
                        and "present" in fake.offers:
                    node = u.path[len("/api/node/"):-len("/present")]
                    got = fake.present.get(node)
                    return self._send(got or {"node_id": node, "faces_now": 0,
                                              "people": [], "unknown_now": 0})
                if u.path == "/api/node/status":
                    return self._send({"nodes": [{"node_id": "kiosk-1", "online": True,
                                                  "camera_label": "Front desk"}]})
                if u.path == "/api/history":
                    return self._send({"items": []})
                return self._send({"detail": "Not Found"}, 404)

            def do_POST(self):                                   # noqa: N802
                u = urlparse(self.path)
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n)
                if u.path == "/api/auth/login":
                    fake.calls.append(("POST", u.path, {}))
                    return self._send({"access_token": TOKEN, "token_type": "bearer"})
                if u.path == "/api/look" and "look" in fake.offers:
                    form = parse_multipart(body, self.headers.get("Content-Type") or "")
                    fake.calls.append(("POST", u.path, {
                        "auth": self.headers.get("Authorization") or "", "form": form}))
                    if not self._authed():
                        return self._send({"detail": "Not authenticated"}, 401)
                    if fake.look_code != 200:
                        return self._send({"detail": "refused"}, fake.look_code)
                    if not form.get("photo"):
                        return self._send({"detail": "no photo"}, 400)
                    return self._send({"image": {"w": 640, "h": 480}, "took_ms": 84,
                                       "kept": fake.kept, "faces": fake.look_faces})
                fake.calls.append(("POST", u.path, {"bytes": len(body)}))
                return self._send({"detail": "Not Found"}, 404)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.srv.server_port

    def looks(self):
        return [c for c in self.calls if c[0] == "POST" and c[1] == "/api/look"]

    def stop(self):
        self.srv.shutdown()
