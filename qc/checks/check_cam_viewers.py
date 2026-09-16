"""One camera, several people watching it.

Asked for 2026-08-21: *now it cannot use 1 cam more than 1 viewer fix that
too*. The second person to open the live view was told *someone is already
watching — one live view at a time*.

THE BOARD IS RIGHT TO REFUSE, SO THE HUB WATCHES INSTEAD
--------------------------------------------------------
The camera has ONE frame buffer — PSRAM is deliberately off for that build,
measured twice on real hardware — and CamModule::take() reclaims whatever
frame is out on loan, so two streams tear each other's pictures. The limit is
the hardware. What was wrong was the hub piping each browser straight through
to the board, which turned the hardware's limit into the product's limit.

`main_python/cam_relay.py` holds ONE connection and hands the newest frame to
every viewer.

WHAT THIS CHECK HAS TO PROVE, AND WHY THE FAKE REFUSES TOO
----------------------------------------------------------
If the fake camera let two streams in, two viewers would work with or without
the relay and this check would prove nothing. So the fake answers 503 to a
second watcher exactly as the board does, and counts the connections it was
given. Two viewers must both get frames from ONE connection.

The other half is the failure the panel named: a viewer that reads slowly must
not hold up the others, and the relay must hand out the LATEST frame rather
than a backlog — a queue per viewer would cost memory and show everyone else
the past.
"""
import re
import threading
import time

import fake_wifi
import qc as F

AREA = "firmware"
TITLE = "one camera can be watched by several people at once"
# It holds three sockets open for seconds at a time. In the quick suite that
# is 22s inside a 26s run, and it starved check_ota's 1.3 MB loopback POST
# until it timed out - a red suite that was really contention, twice over.
SLOW = True


def _watch(base, dev, frames, out, key, slow=0.0):
    """Read `frames` JPEG parts from the hub's live view. -> into out[key]."""
    import urllib.request
    got, seen, at = [], b"", []
    started = time.time()
    url = base + "/api/dev/cam.stream?dev=" + dev
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            out[key + "_type"] = r.headers.get("Content-Type", "")
            while len(got) < frames:
                # read1: take what has arrived rather than waiting for a
                # full buffer, which is what a browser does with an <img>.
                chunk = r.read1(512)
                if not chunk:
                    break
                seen += chunk
                while True:
                    m = re.search(rb"Content-Length: (\d+)\r\n\r\n", seen)
                    if not m:
                        break
                    n = int(m.group(1))
                    start = m.end()
                    if len(seen) < start + n:
                        break
                    got.append(seen[start:start + n])
                    at.append(time.time())
                    seen = seen[start + n:]
                    if slow:
                        time.sleep(slow)     # a viewer on bad WiFi
    except Exception as e:                   # noqa: BLE001
        out[key + "_err"] = "%s: %s" % (type(e).__name__, e)
    out[key] = got
    # THE GAP BETWEEN FRAMES, not the average over the whole run: the
    # connection and the first frame cost the same for everybody, and
    # dividing that by five frames buried the difference under it.
    gaps = [at[i + 1] - at[i] for i in range(len(at) - 1)]
    gaps.sort()
    out["gap"] = gaps[len(gaps) // 2] if gaps else 99.0


def run(t):
    import fake_serial
    fake_serial.reset()
    base, main = F.start_hub()
    wifi = fake_wifi.start()
    fake_wifi.MODULE.reset()
    fake_wifi.MODULE.stream_frames = 80      # long enough for both viewers
    dev = "wifi:" + wifi

    # ---- the fake really refuses a second watcher ---------------------
    # Without this the whole check is theatre: two viewers would work anyway.
    import urllib.request
    import urllib.error
    # It has to still be HOLDING when the direct connection is tried. Asking
    # for three frames was enough when a frame took a second and a half to
    # arrive; once the relay stopped batching, this viewer finished and let go
    # before the test below ran, and the camera accepted the direct connection
    # exactly as it should have.
    hold = {}
    first = threading.Thread(target=_watch, args=(base, dev, 60, hold, "hold"),
                             daemon=True)
    first.start()
    time.sleep(0.6)
    direct_refused = False
    try:
        with urllib.request.urlopen("http://%s/api/cam.stream" % wifi, timeout=5) as r:
            direct_refused = False
            r.read(64)
    except urllib.error.HTTPError as e:
        direct_refused = e.code == 503
    except Exception:                        # noqa: BLE001
        direct_refused = False
    t.ok(direct_refused,
         "the camera itself still allows only one watcher",
         "if the fake accepts two, two viewers prove nothing about the relay")
    first.join(timeout=30)

    # ---- two viewers through the hub, at the same time ----------------
    a, b = {}, {}
    ta = threading.Thread(target=_watch, args=(base, dev, 5, a, "f"), daemon=True)
    tb = threading.Thread(target=_watch, args=(base, dev, 5, b, "f", 0.08),
                          daemon=True)
    ta.start()
    time.sleep(0.3)                          # the second arrives mid-stream
    tb.start()
    ta.join(timeout=30)
    tb.join(timeout=30)

    t.ok(len(a.get("f") or []) >= 3,
         "the first viewer gets pictures (%d)" % len(a.get("f") or []),
         a.get("f_err", ""))
    t.ok(len(b.get("f") or []) >= 3,
         "and so does a SECOND viewer at the same time (%d)"
         % len(b.get("f") or []),
         "this is the whole point: %s" % b.get("f_err", ""))
    t.contains(a.get("f_type", ""), "multipart/x-mixed-replace",
               "both are served as a live view, not a single picture")

    # ---- from ONE connection to the board ------------------------------
    # COUNTED ACROSS THE WHOLE CHECK: three viewers have come and gone by
    # now, and the board must have been opened once for all of them. Resetting
    # this counter half way through measured nothing - the later viewers
    # joined the connection that was already open, so it read 0.
    t.ok(fake_wifi.MODULE.streams_opened == 1,
         "and the board was opened ONCE for all three viewers (%d)"
         % fake_wifi.MODULE.streams_opened,
         "one connection is what makes the second viewer possible at all")

    # ---- the slow one did not hold the quick one up --------------------
    # PACE, NOT COUNT. Both viewers stop at the same target, so comparing how
    # many frames each collected compares almost nothing — it read 4 vs 5 and
    # failed while the relay was working perfectly. What matters is how long
    # each took per frame: the slow viewer sleeps between frames, and if the
    # relay queued per viewer the quick one would be dragged to that pace.
    qa = a.get("gap", 99.0)
    qb = b.get("gap", 0.0)
    t.ok(qa < qb,
         "a slow viewer does not hold back a quick one (%.0fms vs %.0fms between frames)"
         % (qa * 1000, qb * 1000),
         "frames are handed out latest-first, never queued per viewer")

    # ---- and the page no longer blames another viewer ------------------
    ui = (F.FIRMWARE / "src" / "web" / "WebUI.h").read_text(
        encoding="utf-8", errors="replace")
    t.ok("someone else may be watching" not in ui,
         "the module page has stopped telling people to take turns",
         "the relay removed that limit; the message outlived it")
