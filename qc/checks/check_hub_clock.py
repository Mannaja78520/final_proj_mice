"""The HUB can be the show's clock, so a rehearsal survives the browser.

A hidden tab has requestAnimationFrame stopped and its timers throttled to
about once a minute. That is browser policy: a show driven from the page froze
the moment you clicked away, and at a rehearsal that is constantly. Handing the
whole sequence to the MODULE fixes a show (it survives the PC being off) but
not editing — nothing has been uploaded yet.

The hub is a native process that already owns the serial ports and nothing
throttles it. So it plays: same commands, same `POSE ... T <ms>` moves the
module interpolates itself, only the timing decided somewhere that cannot be
suspended.

The rule from check_one_player.py still holds and is checked here too: exactly
ONE clock at a time. A live motion command aimed at the same device stops the
hub's playback, and while the hub plays, the page must send nothing itself.
"""
import json
import re
import time

import fake_serial
import qc as F

AREA = "unattended"
TITLE = "the hub plays the show, so a hidden tab cannot stop it"
SLOW = False

STEPS = [{"pose": [90] * 10, "t": 120, "hold": 0},
         {"pose": [20, 160] + [90] * 8, "t": 200, "hold": 80},
         {"pose": [120] + [90] * 9, "t": 200, "hold": 0}]


def _play(base, **over):
    body = {"dev": "usb:" + fake_serial.PORT, "steps": STEPS,
            "loop": False, "name": "qc_hub"}
    body.update(over)
    return json.loads(F.post(base + "/api/play", json.dumps(body).encode())[1])


def _status(base):
    return json.loads(F.get(base + "/api/play")[1])


def _wait_idle(base, limit=6.0):
    end = time.time() + limit
    while time.time() < end:
        if not _status(base)["running"]:
            return True
        time.sleep(0.05)
    return False


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- 1. it plays, and the module gets real moves ----------------
    st = _play(base)
    t.ok(st.get("running") is True, "the hub starts playing", st)
    t.eq(st.get("total_ms"), 600, "it knows how long the show is")
    t.ok(_wait_idle(base), "and it finishes on its own")

    sent = [c for _, c in fake_serial.wire]
    poses = [c for c in sent if c.startswith("POSE")]
    t.eq(len(poses), 3, "every keyframe was sent as one whole move")
    t.ok(sent and sent[0] == "MOVE STOP",
         "it takes the robot first, so the module is not a second clock", sent[:2])
    # the move times are the ones the timeline asked for — the hub decides WHEN
    # a move starts, never how long it takes
    t.contains(poses[1], "T 200", "a segment carries its own duration")
    t.contains(poses[1], "20 160", "and the pose it was given")

    # ---- 2. the timing is real, not a burst -------------------------
    # The bug this would hide: sending every pose immediately "works" on a fake
    # module and looks like a show that plays at infinite speed on a real one.
    ms = [t0 for t0, c in fake_serial.wire if c.startswith("POSE")]
    gap = ms[2] - ms[1]
    t.ok(gap >= 200, "it waits for a move to finish before starting the next "
         "(%d ms between segment 2 and 3)" % gap,
         "the hub sent the whole show at once — the robot would jump")
    t.under(gap, 900, "and it does not dawdle", "ms")

    # ---- 3. stop means stop -----------------------------------------
    fake_serial.reset()
    _play(base, loop=True)
    time.sleep(0.15)
    t.ok(_status(base)["running"] is True, "a looping show keeps going")
    F.post(base + "/api/play/stop", b"")
    t.ok(_status(base)["running"] is False, "stop ends it")
    after = len(fake_serial.wire)
    time.sleep(0.35)
    # the thread really ended: nothing else appears on the wire
    t.eq(len(fake_serial.wire), after,
         "and nothing more goes down the wire after stop")
    t.ok(any(c == "STOP" for _, c in fake_serial.wire),
         "the module is told to hold where it is")

    # ---- 4. ONE clock: a live move takes the robot ------------------
    fake_serial.reset()
    _play(base, loop=True)
    time.sleep(0.15)
    t.ok(_status(base)["running"] is True, "playing before the interruption")
    F.cmd(base, "JOINT 1 120", fake_serial.PORT)      # a slider drag
    st = _status(base)
    t.ok(st["running"] is False,
         "a live motion command stops the hub's playback",
         "the hub kept playing while something else moved the same robot")
    t.contains(st.get("error", ""), "took over",
               "and it says why it stopped")

    # ...but a SETTING does not end a rehearsal
    fake_serial.reset()
    _play(base, loop=True)
    time.sleep(0.15)
    F.cmd(base, "SPEED 90", fake_serial.PORT)
    t.ok(_status(base)["running"] is True,
         "changing a setting does NOT stop the show",
         "you must be able to tune a sequence while it plays")
    F.post(base + "/api/play/stop", b"")

    # ---- 5. resuming from the middle asks for what is LEFT ----------
    fake_serial.reset()
    _play(base, from_ms=180)          # 60 ms into segment 1 (120..320)
    time.sleep(0.05)
    first = [c for _, c in fake_serial.wire if c.startswith("POSE")]
    if t.ok(first, "a resumed show sends a move"):
        m = re.search(r"T (\d+)", first[0])
        t.ok(m and int(m.group(1)) < 200,
             "and asks for the time REMAINING, not the whole segment",
             "the robot would replay a move the editor has already passed")
    F.post(base + "/api/play/stop", b"")

    # ---- 6. the page hands over instead of sending too --------------
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "/api/play", "Studio asks the hub to play")
    t.contains(app, "function hubDriven", "and knows when the hub holds the clock")
    tick = app[app.find("function playTick"):]
    tick = tick[:tick.find("\nfunction ")]
    # two clocks on one robot is the exact bug this replaces
    t.contains(tick, "!hubDriven()",
               "the preview sends nothing while the hub is playing")
    hand = app[app.find("async function handOffToRobot"):]
    hand = hand[:hand.find("\n}")]
    t.contains(hand, "hubDriven",
               "and it does not ALSO hand the show to the module")
    vis = app[app.find('addEventListener("visibilitychange"'):]
    vis = vis[:vis.find("\n});")]
    # otherwise the preview sits behind the arm for the rest of the show
    t.contains(vis, "/api/play",
               "coming back to the page re-syncs the play head to the hub")
