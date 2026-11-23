"""One camera system: boards, this PC's webcams and added links, watched together.

User 2026-11-23: *one camera system - ESP32-CAM and other cameras used at the
same time by recording, face recognition, and later a window others can watch*.

Proved against a fake ffmpeg (counts how often it is opened, writes JPEGs cut
at odd places) and the fake ESP32-CAM:
  * /api/cameras lists a board, a webcam and an added camera in ONE list;
  * an added link camera is watched by two pages and the face watcher's reader
    through ONE reader (the camera sees one watcher), whole pictures;
  * /api/dev/cam.jpg gives one picture of a hub-read camera;
  * adding needs the login, refuses this PC's own address, other schemes
    (file:, a path) and a name used twice, and never shows the link's password;
  * a camera marked for faces is in ?face=1 and the watcher's sync starts and
    then stops a Looker for it, with no restart;
  * removing a camera lets it go.
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import fake_wifi
import qc as F

AREA = "hub"
TITLE = "boards, webcams and added cameras are one list, each read once however many watch"
SOLO = True

FAKE = r'''
import sys, time
log = sys.argv[1]
if sys.argv[2] == "list":
    sys.stderr.write('[in#0 @ 0x1] "FHD Camera" (video)\n')
    sys.exit(1)
with open(log, "a") as f:
    f.write("open %s\n" % " ".join(sys.argv[3:]))
n = 0
out = sys.stdout.buffer
while True:
    n += 1
    jpeg = b"\xff\xd8" + (b"frame-%d " % n) * 40 + b"\xff\xd9"
    cut = 7 + n % 13
    out.write(jpeg[:cut]); out.flush()
    time.sleep(0.01)
    out.write(jpeg[cut:]); out.flush()
    time.sleep(0.04)
'''


def _read(url, frames, out, key):
    got, seen = [], b""
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            while len(got) < frames:
                chunk = r.read1(4096)
                if not chunk:
                    break
                seen += chunk
                while b"Content-Length: " in seen:
                    head, _, rest = seen.partition(b"Content-Length: ")
                    num, sep, body = rest.partition(b"\r\n\r\n")
                    if not sep or len(body) < int(num):
                        break
                    got.append(body[:int(num)])
                    seen = body[int(num):]
    except Exception as e:                                   # noqa: BLE001
        out[key + "_err"] = "%s: %s" % (type(e).__name__, e)
    out[key] = got


def _post(base, path, body):
    code, text = F.post(base + path, json.dumps(body).encode())
    try:
        return code, json.loads(text)
    except ValueError:
        return code, {}


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_camhub_"))
    fake = tmp / "ffmpeg_fake.py"
    fake.write_text(FAKE, encoding="utf-8")
    log = tmp / "opens.log"
    py = sys.executable
    faces = tmp / "faces.json"
    faces.write_text(json.dumps({"service": "http://127.0.0.1:9", "pcCamera": {
        "run": [py, str(fake), str(log), "run", "{device}"],
        "list": [py, str(fake), str(log), "list"], "skip": []}}), encoding="utf-8")
    kinds = tmp / "cameras.json"
    kinds.write_text(json.dumps({"kinds": {
        "link": {"label": "link", "needs": "value", "schemes": ["http", "rtsp"],
                 "extra": {"rtsp": ["-tcp"]}, "run": [py, str(fake), str(log), "run", "{input}"]},
        "demo": {"label": "demo", "needs": "", "run": [py, str(fake), str(log), "run", "demo"]}}}),
        encoding="utf-8")
    os.environ.update(MICE_FACES_CONFIG=str(faces), MICE_CAMERAS_CONFIG=str(kinds),
                      MICE_CAMERAS_DATA=str(tmp / "data"))
    wifi = fake_wifi.start()
    fake_wifi.MODULE.reset()
    try:
        base, main = F.start_hub()
        F.logout_qc()

        # ---- adding needs the login ------------------------------------
        code, _ = _post(base, "/api/cameras/add", {"name": "Door", "kind": "demo"})
        t.ok(code == 401, "adding a camera needs the login", code)
        F.login(base)

        # ---- what is refused -------------------------------------------
        for bad, why in [("http://127.0.0.1:8642/x", "this PC itself"),
                         ("http://localhost/x", "localhost"),
                         ("http://169.254.169.254/latest", "link-local metadata"),
                         ("file:///etc/passwd", "a file"),
                         ("/etc/passwd", "a path"),
                         ("ftp://cam.local/x", "another scheme"),
                         ("http://cam.local/a b", "spaces")]:
            code, got = _post(base, "/api/cameras/add", {"name": "Bad", "kind": "link", "value": bad})
            t.ok(code == 400 and not got.get("ok"), "refused: " + why, (code, got))
        code, got = _post(base, "/api/cameras/add", {"name": "", "kind": "demo"})
        t.ok(code == 400, "a camera needs a name", got)
        code, got = _post(base, "/api/cameras/add", {"name": "X", "kind": "nope"})
        t.ok(code == 400, "an unknown kind is refused", got)

        # ---- added: a link with a password, and a demo ------------------
        code, door = _post(base, "/api/cameras/add", {
            "name": "Door", "kind": "link", "value": "rtsp://admin:hunter2@192.168.1.50:554/s1"})
        t.ok(code == 200 and door.get("dev", "").startswith("cam:"), "a network camera is added", door)
        code, dup = _post(base, "/api/cameras/add", {"name": "door", "kind": "demo"})
        t.ok(code == 400, "the same name twice is refused", dup)
        code, demo = _post(base, "/api/cameras/add", {"name": "Demo", "kind": "demo"})
        t.ok(code == 200, "a demo camera is added", demo)

        # ---- one list --------------------------------------------------
        fake_wifi.MODULE.stream_frames = 100000
        code, text = F.get(base + "/api/cameras")
        rows = json.loads(text).get("cameras", [])
        kinds_seen = {r["kind"] for r in rows}
        t.ok("usb" in kinds_seen and "link" in kinds_seen and "demo" in kinds_seen,
             "this PC's webcam and the added cameras are in one list",
             [(r["dev"], r["kind"]) for r in rows])
        t.ok("hunter2" not in text, "the list never shows the camera's password", text[:200])
        t.ok(any(r["name"] == "FHD Camera" and r["dev"] == "pc:FHD Camera" for r in rows),
             "the webcam is named as the PC names it")

        # ---- one reader for many watchers ------------------------------
        url = base + "/api/dev/cam.stream?dev=" + door["dev"]
        out = {}
        a = threading.Thread(target=_read, args=(url, 8, out, "a"), daemon=True)
        b = threading.Thread(target=_read, args=(url, 8, out, "b"), daemon=True)
        a.start()
        time.sleep(0.3)
        b.start()
        # and the face watcher's own kind of reader, over the hub
        sys.path.insert(0, str(F.CODE / "apps" / "faces"))
        import look as L
        face_frames = L.hub_frames(base, door["dev"])
        seen, jpeg = face_frames(0, 10)
        a.join(25)
        b.join(25)
        opens = [ln for ln in log.read_text().splitlines() if ln.startswith("open ")]
        t.ok(len(out.get("a") or []) == 8 and len(out.get("b") or []) == 8 and jpeg,
             "two pages and the face reader watch one added camera at once",
             {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()})
        t.ok(len(opens) == 1 and "rtsp://admin:hunter2@192.168.1.50:554/s1" in opens[0]
             and "-tcp" in opens[0],
             "through ONE reader, started with the link and its scheme's extra arguments", opens)
        t.ok(all(f.startswith(b"\xff\xd8") and f.endswith(b"\xff\xd9")
                 for f in (out.get("a") or []) + [jpeg]),
             "every picture arrives whole")
        face_frames.rest()

        # ---- one picture -----------------------------------------------
        with urllib.request.urlopen(base + "/api/dev/cam.jpg?dev=" + demo["dev"], timeout=20) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
        t.ok(ctype == "image/jpeg" and body.startswith(b"\xff\xd8"),
             "one picture can be taken from a camera the hub reads itself", (ctype, body[:8]))

        # ---- faces: marked, listed, followed, unmarked, let go ---------
        code, _ = _post(base, "/api/cameras/face", {"dev": demo["dev"], "on": True})
        rows = json.loads(F.get(base + "/api/cameras?face=1")[1]).get("cameras", [])
        t.ok(code == 200 and [r["dev"] for r in rows] == [demo["dev"]],
             "a camera marked for faces is the only one in ?face=1", rows)

        class State:
            look = {"perSecond": 20}
            lookers = []

            def entry(self):
                return {}

        st = State()
        started = []
        real = L.Looker

        class Probe(real):
            def start(self):                 # no thread: this only watches who is started
                started.append(self.camera)
                return self
        L.Looker = Probe
        try:
            once = L.sync(st, base, every=3600)
            once()
            t.ok(started == ["Demo"] and [lk.camera for lk in st.lookers] == ["Demo"],
                 "the face watcher starts looking at it with no restart", (started, st.lookers))
            once()
            t.ok(started == ["Demo"], "and not a second time", started)
            _post(base, "/api/cameras/face", {"dev": demo["dev"], "on": False})
            once()
            t.ok(st.lookers == [], "switched off, the watcher lets it go", st.lookers)
        finally:
            L.Looker = real

        # ---- removing lets it go ---------------------------------------
        code, _ = _post(base, "/api/cameras/remove", {"id": demo["id"]})
        rows = json.loads(F.get(base + "/api/cameras")[1]).get("cameras", [])
        t.ok(code == 200 and not any(r["dev"] == demo["dev"] for r in rows),
             "a removed camera leaves the list")
        code, _ = F.get(base + "/api/dev/cam.stream?dev=" + demo["dev"])
        t.ok(code == 503, "and cannot be watched any more", code)
    finally:
        for k in ("MICE_FACES_CONFIG", "MICE_CAMERAS_CONFIG", "MICE_CAMERAS_DATA"):
            os.environ.pop(k, None)
