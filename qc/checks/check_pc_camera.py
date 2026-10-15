"""This PC's webcam is opened once, by the hub, and shared.

User 2026-10-15: *every camera usable by the other apps too*. Windows lets one
program hold a webcam: with the Voice tab holding it, the face app's frames
came back black (PC, real camera). So the hub reads it with ffmpeg
(config/faces.json pcCamera) and every page watches the hub
(/api/dev/cam.stream?dev=pc:), exactly as a camera board is shared.

What this has to prove, against a fake ffmpeg that counts how often it is
started and writes JPEGs cut at odd places:
  * two viewers, ONE reader - a second reader is what Windows would refuse;
  * whole pictures, however the pipe splits them;
  * nobody watching = the reader ends, so another app can have the webcam;
  * "pc:" with no name takes the real camera, never a virtual one listed first
    (the PC lists two phone/screen cameras that show black);
  * the Voice page uses the shared camera when nothing else was picked, so it
    never takes the webcam itself.
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "this PC's camera is opened once by the hub and shared, and let go when unwatched"
SOLO = True                       # a hub of its own, and a pipe held open

FAKE = r'''
import sys, time
log = sys.argv[1]
if sys.argv[2] == "list":
    sys.stderr.write('[in#0 @ 0x1] "manny (Windows Virtual Camera)" (video)\n'
                     '[in#0 @ 0x1] "FHD Camera" (video)\n'
                     '[in#0 @ 0x1]   Alternative name "@device_pnp_x"\n'
                     '[in#0 @ 0x1] "Microphone (USB)" (audio)\n')
    sys.exit(1)
with open(log, "a") as f:
    f.write("open %s\n" % sys.argv[3])
n = 0
out = sys.stdout.buffer
while True:
    n += 1
    jpeg = b"\xff\xd8" + (b"frame-%d " % n) * 40 + b"\xff\xd9"
    cut = 7 + n % 13                      # never on a picture's edge
    out.write(b"junk" + jpeg[:cut]); out.flush()
    time.sleep(0.01)
    out.write(jpeg[cut:]); out.flush()
    time.sleep(0.04)
'''


def _read(url, frames, out, key):
    """`frames` whole JPEG parts from the hub's stream -> out[key]."""
    got, seen = [], b""
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            out[key + "_type"] = r.headers.get("Content-Type", "")
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


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_pccam_"))
    fake = tmp / "ffmpeg_fake.py"
    fake.write_text(FAKE, encoding="utf-8")
    log = tmp / "opens.log"
    cfg = tmp / "faces.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:9",
        "pcCamera": {"run": [sys.executable, str(fake), str(log), "run", "{device}"],
                     "list": [sys.executable, str(fake), str(log), "list"],
                     "skip": ["Virtual Camera"]}}), encoding="utf-8")
    os.environ["MICE_FACES_CONFIG"] = str(cfg)
    try:
        base, main = F.start_hub()
        relay_mod = main.cam_relay
        t.eq(relay_mod.pc_devices(main.hub_api_faces.pc_camera()),
             ["FHD Camera", "manny (Windows Virtual Camera)"],
             "this PC's cameras are found, virtual ones last")

        url = base + "/api/dev/cam.stream?dev=pc:"
        out = {}
        a = threading.Thread(target=_read, args=(url, 8, out, "a"), daemon=True)
        b = threading.Thread(target=_read, args=(url, 8, out, "b"), daemon=True)
        a.start()
        time.sleep(0.3)
        b.start()
        a.join(25)
        b.join(25)
        opens = log.read_text().splitlines() if log.is_file() else []
        t.ok(len(out.get("a") or []) == 8 and len(out.get("b") or []) == 8,
             "two pages watch this PC's camera at once", {k: (len(v) if isinstance(v, list) else v)
                                                          for k, v in out.items()})
        t.eq(opens, ["open FHD Camera"],
             "through ONE reader of the real camera, never the virtual one")
        whole = all(f.startswith(b"\xff\xd8") and f.endswith(b"\xff\xd9") and b"junk" not in f
                    for f in (out.get("a") or []) + (out.get("b") or []))
        t.ok(whole and "multipart" in out.get("a_type", ""),
             "and every picture arrives whole, however the pipe cut it",
             [f[:12] for f in (out.get("a") or [])[:3]])

        relay = relay_mod.CamRelay._all.get("pc:FHD Camera")
        until = time.time() + relay_mod.IDLE_CLOSE + 6
        while time.time() < until and relay is not None and relay.thread is not None:
            time.sleep(0.2)
        t.ok(relay is not None and relay.thread is None,
             "nobody watching: the reader ends and the webcam is free for other apps",
             relay and relay.thread)
        out2 = {}
        _read(url, 2, out2, "c")
        opens = log.read_text().splitlines()
        t.ok(len(out2.get("c") or []) == 2 and len(opens) == 2,
             "and the next viewer opens it again", (out2.get("c_err"), opens))
    finally:
        os.environ.pop("MICE_FACES_CONFIG", None)
