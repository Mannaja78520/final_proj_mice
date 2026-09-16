"""A show played BY THE HUB carries its music, not only its moves.

The nong has a speaker (A7-9/A24-16) and a saved show can name a track:
`- play: song.mp3` is a step key like any other, declared on PLAY in
firmware/config/commands.json. A show played from the module's own SD card
therefore had music, and the identical file played from the hub - which is
what Studio and the voice answer both do - ran silent: `seq_steps` matched
pose lines and dropped every other line, and `ShowPlayer` only ever sent
POSE. The user asked for it on 2026-09-07 (A24-22): *push the music to
sdcard and run follow the pc*.

Four halves of that bargain, so none can rot back:

* the parser keeps non-pose steps as CUES bound to the keyframe they sit in
  front of, in file order;
* the player fires them before that keyframe's move goes out;
* stopping a show that started audio also stops the audio - a panic stop
  must mean quiet, not only still (A24-18), and stopall does not freeze;
* MOTION step keys are never cues. While the hub is the clock, a step that
  moves the robot would be a second clock (check_one_player), so the map is
  built from commands.json with `motion` entries left out - which also means
  a new audio/light step key costs no hub code at all.
"""
import json
import time

import fake_serial
import qc as F

AREA = "sequences"
TITLE = "a hub-played show plays its music too"
SLOW = False

SEED = ("name: qcmusic\nloop: false\n"
        "- vol: 80\n"
        "- play: song.mp3\n"
        "- home:\n"                       # motion: the hub is the clock, drop it
        "- pose: 90 90 90 90 90 90 90 90 90 90 T 300\n"
        # a cue on a LATER keyframe: the first one is placed by a different
        # branch of the player (the travel move onto the start pose), so a
        # show whose only cue sits at the top proves half the path
        "- vol: 30\n"
        "- pose: 20 90 90 90 90 90 90 90 90 90 T 300\n"
        "- play: STOP\n")


def _wire():
    return [c for _, c in fake_serial.wire]


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- 1. the parser keeps the cues, and drops motion steps ----------
    seq_dir = main.SEQUENCES
    seq_dir.mkdir(exist_ok=True)
    seed = seq_dir / "qc_music.yaml"
    seed.write_text(SEED, encoding="utf-8", newline="\n")
    try:
        got = json.loads(F.get(base + "/api/seqsteps?name=qc_music.yaml")[1])
    finally:
        seed.unlink()
    steps = got.get("steps") or []
    if not t.ok(len(steps) == 2, "the seeded show parsed into two keyframes",
                got):
        return
    t.eq(steps[0].get("cues"), ["vol: 80", "play: song.mp3", "home:"],
         "the file's own steps ride on the keyframe they precede, unchanged")
    t.eq(steps[1].get("cues"), ["vol: 30"],
         "a cue in the middle of the file belongs to the keyframe after it")
    t.eq(steps[1].get("cues_after"), ["play: STOP"],
         "a cue after the last keyframe fires when the show ends")
    t.eq(main.cue_lines(["play: song.mp3", "home:", "nosuch: 1"]),
         ["PLAY song.mp3"],
         "only a non-motion step the firmware knows becomes a command - the "
         "hub is the clock, so a MOTION step would be a second one")

    # ---- 2. the player sends them, before that keyframe's move ---------
    body = {"dev": "usb:" + fake_serial.PORT, "steps": steps,
            "loop": False, "name": "qc_music"}
    st = json.loads(F.post(base + "/api/play", json.dumps(body).encode())[1])
    t.ok(st.get("running") is True, "the hub started the show", st)
    end = time.time() + 6.0
    while time.time() < end:
        if not json.loads(F.get(base + "/api/play")[1])["running"]:
            break
        time.sleep(0.05)

    wire = _wire()
    got_play = t.contains(wire, "PLAY song.mp3", "the track reached the module")
    t.contains(wire, "VOL 80", "so did the volume the file asked for")
    t.ok(not any(c.startswith("HOME") for c in wire),
         "and the motion step in the file never reached it", wire)
    poses = [i for i, c in enumerate(wire) if c.startswith("POSE ")]
    if t.ok(poses, "the show still drove the arm", wire[-4:]) and got_play:
        t.ok(wire.index("PLAY song.mp3") < poses[0],
             "the music starts BEFORE the move it belongs to, not after it",
             wire[:6])
        t.ok("PLAY STOP" in wire and wire.index("PLAY STOP") > poses[-1],
             "and the trailing cue fires after the last move", wire[-4:])
        t.ok("VOL 30" in wire and poses[0] < wire.index("VOL 30") < poses[-1],
             "a cue on a later keyframe fires with THAT keyframe, mid-show",
             wire)

    # ---- 3. stopping a show with music also stops the music ------------
    fake_serial.reset()
    F.post(base + "/api/play", json.dumps(body).encode())
    time.sleep(0.15)
    F.post(base + "/api/play/stop", b"")
    stopped = _wire()
    t.contains(stopped, "PLAY STOP",
               "stopping the show silenced the speaker as well")

    # ---- 4. the cue map is DATA, not a list in main.py -----------------
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry  # noqa: E402  (JSONC loader - commands.json has comments)
    want = {}
    for c in registry.commands():
        if c.get("motion"):
            continue
        for s in c.get("steps") or []:
            if s.get("key"):
                want[str(s["key"]).lower()] = c["name"] + (
                    (" " + s["sub"]) if s.get("sub") else "")
    t.eq(main.cue_cmds(), want,
         "every non-motion step key in commands.json is a cue, and only those")
