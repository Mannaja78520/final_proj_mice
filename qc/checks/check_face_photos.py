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
