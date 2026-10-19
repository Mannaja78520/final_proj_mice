"""Still photos down every road a webcam frame takes, against a fake face app.

User 2026-10-19: *เทสโดยเอาภาพมาเทสก่อนเลย* - test with pictures before the
live camera. tools/face_photo_test.py is that test; on the PC it runs against
the real face app (--photos DIR). Here it runs with --fake's drawn pictures,
so the roads themselves cannot rot: their /api/look alone, the watcher's
camera then Voice asking the watcher, and Voice's own one-frame check.

Asserted on what reached the fake: each photo's own bytes, once per road,
and the answers each road gave for a known face, a stranger and no face.
Tested against fakes only: on the real face app see the tool's --photos run.
"""
import importlib.util
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "a known face, a stranger and an empty picture each give the right answer on every road"


def run(t):
    spec = importlib.util.spec_from_file_location("_face_photo_test",
                                                  F.CODE / "tools" / "face_photo_test.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    tmp = tempfile.mkdtemp(prefix="mice_photos_qc_")
    old_login = os.environ.get("MICE_FACES_LOGIN")
    fake, st, env, photos = tool.fake_rig(tmp)
    try:
        result = tool.run(photos, st, env, tmp)
    finally:
        fake.stop()
        # fake_rig points the watcher at a throwaway login: not the next check's
        if old_login is None:
            os.environ.pop("MICE_FACES_LOGIN", None)
        else:
            os.environ["MICE_FACES_LOGIN"] = old_login
    lines = []
    tool.report(result, lines.append)
    rows = {r["kind"]: r for r in result["rows"]}
    for kind, want in (("known", "Somchai"), ("unknown", "a face nobody knows"),
                       ("noface", "no face")):
        roads = (rows.get(kind) or {}).get("roads") or {}
        t.eq(sorted(roads), ["look", "voice", "watcher"],
             "the %s photo went down all three roads" % kind)
        for road, got in roads.items():
            t.ok(got["passed"] and want in str(got["found"]),
                 "%s photo, %s road: %s" % (kind, road, want),
                 "found %r - %s" % (got.get("found"), "\n".join(lines)))
    sent = [c[2]["form"].get("photo") for c in fake.looks()]
    for kind, _want, path in photos:
        t.eq(sent.count(path.read_bytes()), 3,
             "the %s photo's own bytes reached the face app once per road" % kind)
    t.ok(result["passed"], "the tool says PASS", "\n".join(lines))
    # The PC run printed nothing about their feed, and nobody could tell
    # silent from not listened to (2026-10-19). It always says which.
    t.ok(any(ln.startswith("their live feed: not listened to") for ln in lines),
         "the report always says what their live feed did", "\n".join(lines))

    # --fetch-unknown saved their new HTML front page as unknown_generated.jpg
    # (PC, 2026-10-19). Only a JPEG may become a photo; an old HTML one goes.
    class Page(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):                                    # noqa: N802
            body = b"<!DOCTYPE html><html><img src=x></html>"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Page)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tool.STRANGER_URL = "http://127.0.0.1:%d/" % srv.server_port
    folder = Path(tempfile.mkdtemp(prefix="mice_stranger_"))
    (folder / "unknown_generated.jpg").write_bytes(b"<html>saved by an older run</html>")
    try:
        got, why = tool.fetch_stranger(folder)
    finally:
        srv.shutdown()
    # A busy answer is waited out and tried again; the time reported is until
    # the answer, waits included - only the last try was (PC, 2026-10-19).
    answers = iter([("busy", [], ""), ("busy", [], ""), ("ok", [], "80 ms")])

    class Token:
        def token_now(self):
            return "tok", ""

        def entry(self):
            return {}
    real_look = tool.friend_api.look
    tool.friend_api.look = lambda *a, **k: next(answers)
    try:
        got_look = tool.road_look(Token(), b"\xff\xd8")
    finally:
        tool.friend_api.look = real_look
    t.ok(got_look["tries"] == 3 and got_look["seconds"] >= 1.4 and got_look["last"] < 0.5,
         "busy answers are waited out, and the time says how long that took", got_look)
    t.ok(got is None and "did not send a picture" in why
         and not (folder / "unknown_generated.jpg").exists(),
         "a web page is never kept as the stranger's photo", (got, why))
