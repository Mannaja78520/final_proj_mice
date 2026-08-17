"""A show must keep running when the browser is not looking at it.

Live playback from Nong Studio is driven by requestAnimationFrame, and every
browser STOPS rAF in a hidden tab. Switch to another tab or app and the
sequence freezes mid-move — which is exactly what happens at a show when
someone clicks away from the laptop.

The fix is not to fight the browser: the robot has to own its playback. That
already existed as `MOVE <file>`, but only with an SD card fitted, and a board
without one had no way to run a sequence unattended at all. Upload now falls
back to the module's memory, so the same "send, then run" works on any board —
and the browser can be closed entirely.

Asserted end to end: send a sequence, close nothing, run it, and confirm the
module is playing on its own.
"""
import re

import fake_serial
import qc as F

AREA = "unattended"
TITLE = "the robot runs a sequence on its own, with no SD card"
SLOW = False

SEQ = ("name: qc_show\n"
       "loop: false\n"
       "steps:\n"
       "  - speed: 120\n"
       '  - pose: "90 90 90 90 90 90 90 90 90 90 T 800"\n'
       "  - wait: 300\n"
       '  - pose: "25 155 90 90 90 90 90 90 90 90 T 1200"\n')


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT

    # ---- send it exactly the way Studio already does ------------------
    # Studio's "Send to robot" uses FBEGIN / FDATA / FEND. Nothing in the
    # editor changed for this — the BOARD decides where it lands.
    import base64
    s, b = F.cmd(base, "FBEGIN /moves/qc_show.yaml")
    t.eq(s, 200, "an upload starts")
    t.ok("memory" in b.lower(),
         "with no card it says the sequence is kept in memory",
         "the module gave no hint that there is no SD: %r" % b)

    data = SEQ.encode()
    for i in range(0, len(data), 120):
        s, b = F.cmd(base, "FDATA " + base64.b64encode(data[i:i + 120]).decode())
        if not t.ok(b.startswith("OK"), "each chunk is accepted", b):
            return
    s, b = F.cmd(base, "FEND")
    t.contains(b, "OK", "the upload finishes")
    t.contains(b.lower(), "memory", "and confirms where it went")

    # what the module holds must be what was sent
    t.eq(fake_serial.NONG.held, SEQ,
         "the module holds the sequence byte for byte")

    # ---- and it plays it ITSELF ---------------------------------------
    s, b = F.cmd(base, "MOVE qc_show.yaml")
    t.contains(b, "OK", "the robot starts the sequence")
    t.ok(fake_serial.NONG.playing,
         "the module is playing on its own — no browser involved")

    # stopping does not unload it, so it can be replayed without re-sending
    s, b = F.cmd(base, "MOVE STOP")
    t.contains(b, "OK", "it can be stopped")
    t.eq(fake_serial.NONG.held, SEQ,
         "stopping does NOT throw the sequence away")
    s, b = F.cmd(base, "MOVE qc_show.yaml")
    t.ok(fake_serial.NONG.playing, "so it replays without sending it again")

    # ---- the firmware really does all of this ------------------------
    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(router, "ramOpen_", "the firmware has an in-memory upload path")
    t.contains(router, "RAM_SEQ_MAX",
               "and caps it, so a runaway upload cannot exhaust the heap")
    m = re.search(r'if \(cmd == "MOVE"\)(.*?)\n    \}', router, re.S)
    if t.ok(m, "the MOVE handler is there"):
        t.contains(m.group(1), "hasText",
                   "MOVE plays the in-memory sequence when there is no card")

    player = (F.FIRMWARE / "src/core/SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(player, "startText", "the player can run a sequence from memory")
    t.contains(player, "parseYaml", "parsing it without touching the card")
    sd = (F.FIRMWARE / "src/core/SDStore.cpp").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"bool SDStore::parseYaml.*?\n\}", sd, re.S)
    if t.ok(m, "parseYaml exists"):
        t.ok("SD.open" not in m.group(0) and "lock()" not in m.group(0),
             "and it touches no SD hardware at all",
             "a board with no card would fail here")
