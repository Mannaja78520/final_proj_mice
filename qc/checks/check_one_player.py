"""Only ONE thing drives the servos at a time.

The board plays a sequence on its own clock — that is what lets a show survive
the browser being closed. Nong Studio also streams poses down the same cable
while you press Play. Both were allowed to run at once, so the module kept
firing the next keyframe of its own sequence while Studio sent the pose it
thought was current: the moves overlapped, the arm fought itself, and Pause in
Studio did not stop the robot because only the browser had stopped.

The rule now: a command that MOVES the robot, arriving from anywhere except the
sequence player itself, stops the sequence first. Whoever moved the robot last
owns it. Configuration commands (SPEED, LIMIT, SERVO) deliberately do not — you
must be able to change the speed of a running show without ending it.

Asserted three ways: the declaration (commands.json), the firmware that reads
it, and the behaviour end to end through the hub.
"""
import base64
import json
import re

import fake_serial
import qc as F

AREA = "sequences"
TITLE = "one player: a live command stops the module's own sequence"
SLOW = False

SEQ = ("name: qc_overlap\n"
       "loop: true\n"
       "steps:\n"
       "  - speed: 120\n"
       '  - pose: "90 90 90 90 90 90 90 90 90 90 T 800"\n'
       '  - pose: "20 160 90 90 90 90 90 90 90 90 T 900"\n')

# what must interrupt a show, and what must NOT
MOVERS = ["POSE 90 90 90 90 90 90 90 90 90 90 T 500", "JOINT 1 100", "HOME",
          "RELAX", "STOP"]
SETTERS = ["SPEED 90", "LIMIT 1 10 170", "SERVO ALL mg90s"]


def _running(base, port):
    s, b = F.cmd(base, "INFO", port)
    try:
        return json.loads(b).get("seq", {}).get("running", None)
    except Exception:
        return None


def run(t):
    # ---- 1. it is DECLARED, once, where every path reads it ----------
    import registry
    decl = {(c["name"], c["scope"]): c for c in registry.commands()}
    for name, scope in (("POSE", "nong"), ("JOINT", "nong"), ("HOME", "nong"),
                        ("STOP", "nong"), ("RELAX", "nong"), ("ATTACH", "nong"),
                        ("GOTO", "lift"), ("UP", "lift"), ("DOWN", "lift")):
        c = decl.get((name, scope), {})
        t.ok(c.get("motion") is True,
             "%s (%s) is declared as motion" % (name, scope),
             "a moving command that is not marked cannot stop a sequence, so "
             "it would play over one")
    for name, scope in (("SPEED", "nong"), ("LIMIT", "nong"), ("SERVO", "nong"),
                        ("CFG", "core"), ("INFO", "core"), ("MOVE", "core")):
        c = decl.get((name, scope), {})
        t.ok(not c.get("motion"),
             "%s (%s) is NOT motion" % (name, scope),
             "changing a setting, or asking a question, must not end a show")
    # every query is by definition not motion
    for (name, scope), c in decl.items():
        if c.get("query"):
            t.ok(not c.get("motion"), "%s (%s): a query never moves anything"
                 % (name, scope))

    # ---- 2. the firmware acts on it ---------------------------------
    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(router, "preemptSequence", "the router preempts a running sequence")
    t.contains(router, "commandIsMotion",
               "and asks the generated table which commands move the robot")
    m = re.search(r"bool CommandRouter::preemptSequence.*?\n}", router, re.S)
    if t.ok(m, "preemptSequence is implemented"):
        t.contains(m.group(0), "seq_->stop()", "it really stops the player")
    # ...but a sequence's OWN steps must not stop the sequence
    player = (F.FIRMWARE / "src/core/SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.ok("router_->handle(" not in player,
         "sequence steps do not go through the preempting entry point",
         "the player would stop itself on its first pose")
    t.contains(player, "handleFromSequence",
               "sequence steps use handleFromSequence()")
    hdr = F.generated("core/CommandHelp.h").read_text(encoding="utf-8", errors="replace")
    t.contains(hdr, "commandIsMotion", "the generated table answers that question")

    # ---- 3. the behaviour, end to end through the hub ----------------
    for cmd in MOVERS:
        fake_serial.reset()
        base, main = F.start_hub()
        port = fake_serial.PORT
        # load a sequence and start it, exactly as Studio's Run does
        F.cmd(base, "FBEGIN qc_overlap.yaml", port)
        F.cmd(base, "FDATA " + base64.b64encode(SEQ.encode()).decode(), port)
        F.cmd(base, "FEND", port)
        s, b = F.cmd(base, "MOVE qc_overlap.yaml", port)
        if not t.ok(_running(base, port) is True,
                    "the module is playing its own sequence (%s)" % cmd.split()[0], b):
            continue
        s, b = F.cmd(base, cmd, port)
        t.ok(_running(base, port) is False,
             "%s stops it — the robot is not driven by two clocks"
             % cmd.split()[0],
             "the module kept playing while a live command moved it too")
        # and it SAYS so: silence is how an app loses track of what the board
        # is doing, which is how this bug survived so long
        t.contains(b, "sequence stopped",
                   "the reply says the sequence was stopped (%s)" % cmd.split()[0])

    for cmd in SETTERS:
        fake_serial.reset()
        base, main = F.start_hub()
        port = fake_serial.PORT
        F.cmd(base, "FBEGIN qc_overlap.yaml", port)
        F.cmd(base, "FDATA " + base64.b64encode(SEQ.encode()).decode(), port)
        F.cmd(base, "FEND", port)
        F.cmd(base, "MOVE qc_overlap.yaml", port)
        F.cmd(base, cmd, port)
        t.ok(_running(base, port) is True,
             "%s does NOT stop the show" % cmd.split()[0],
             "a setting change must not end a sequence that is running")

    # ---- 4. Studio still takes control explicitly -------------------
    # The firmware rule is the safety net; Studio saying so is what makes the
    # arm start from the right place. Both, not either.
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "stopRobotSequence",
               "Studio stops the module's sequence when it takes over")
    for fn in ("function togglePlay", "function scrubTo"):
        body = app[app.find(fn):]
        body = body[:body.find("\n}")]
        t.contains(body, "stopRobotSequence", "%s() takes control first" % fn.split()[1])
    pause = app[app.find("function livePause"):]
    pause = pause[:pause.find("\n}")]
    t.contains(pause, '"STOP"', "pausing sends STOP, which now also ends the show")
