"""A show's time bar and the robot keep one clock; joins and music are the show's.

User 2026-09-27: the time bar said 49 s where the robot really got there at
52 s. Two causes, both in the hub:

  * ShowPlayer slept each move's T AFTER the board had answered, so every
    command's round trip was added on top and never paid back. Measured on the
    user's show LhongMarePing: 20 moves before the 48 s mark, 3 s late, about
    150 ms a move - the cable's answer time. Moves now leave on deadlines
    counted from the start of the run.
  * The move into each sequence was asked for at the sequence's own speed,
    below the board's floor (per-joint max deg/s, and biggest change x pi/2
    over safe_dps). The board lengthened it and the player waited, unseen by
    the bar. Studio now sends its limits and the hub never asks for less.

Same day, two show settings: `join_dps` / `join_ms` make the move between
sequences gentler than the next sequence's speed (it looked like a snap), and
`music` is the show's own track, started with the show and stopped at its end,
with the sequences' own play/vol cues left out so they cannot cut it off.
"""
import math
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "sequences"
TITLE = "a show keeps the time bar's clock; joins and music are the show's"
SLOW = False

A = [90.0] * 10
B = [150.0] + [90.0] * 9


def seq(name, first, last, extra=""):
    return ("name: %s\nsteps:\n  - speed: 60\n%s"
            '  - pose: "%s T 1000"\n'
            '  - pose: "%s T 500"\n' % (name, extra,
                                        " ".join("%g" % v for v in first),
                                        " ".join("%g" % v for v in last)))


def test_times(t, shows):
    lim = {"safe_dps": 60, "max_dps": [400] * 10}
    t.eq(shows.link_time(A, B, 60, lim), math.ceil(60 * math.pi / 2 / 60 * 1000),
         "a join is never asked for less than the board's safety floor")
    t.eq(shows.link_time(A, B, 60, {"safe_dps": 0, "max_dps": [30] + [400] * 9}),
         2000, "nor less than the slowest joint's servo max allows")
    t.eq(shows.link_time(A, B, 60, None, {"dps": 20, "ms": 0}), 3000,
         "the show's join speed slows the move between sequences")
    t.eq(shows.link_time(A, B, 60, None, {"dps": 0, "ms": 2500}), 2500,
         "the show's join time is the shortest a join may take")
    t.eq(shows.link_time(A, A, 60, None, {"dps": 0, "ms": 2500}), shows.MIN_T,
         "but two identical poses still run straight on")


def test_steps(t, main, shows):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "seqs").mkdir()
        (d / "seqs" / "one.yaml").write_text(
            seq("one", A, A, "  - play: own.mp3\n"), encoding="utf-8", newline="\n")
        (d / "seqs" / "two.yaml").write_text(
            seq("two", B, A), encoding="utf-8", newline="\n")
        sh = shows.Shows(d / "shows", d / "seqs")
        show = {"name": "qc", "items": [{"seq": "one.yaml"}, {"seq": "two.yaml"}],
                "join_ms": 2500, "music": "song.mp3", "music_vol": 70}
        out = sh.steps(show, main.seq_steps)
        t.eq(out[2]["t"], 2500, "the join into sequence two takes the show's join time")
        t.eq(out[0].get("cues"), ["vol: 70", "play: song.mp3"],
             "the show's track starts on its first pose, the sequence's own is left out")
        t.eq(out[-1].get("cues_after"), ["play: STOP"],
             "and the track stops when the show ends")
        lim = {"safe_dps": 60, "max_dps": [400] * 10}
        out = sh.steps({"name": "qc", "items": show["items"]}, main.seq_steps,
                       limits=lim)
        t.ok(out[3]["t"] >= shows.move_floor(B, A, lim),
             "a move inside a sequence is raised to the board's floor too",
             out[3])
        name, _ = sh.save(show)
        back = sh.load("qc")
        t.ok(back["join_ms"] == 2500 and back["music"] == "song.mp3"
             and back["music_vol"] == 70,
             "the join and music settings survive save and open", back)


def test_clock(t, main):
    # every command takes 100 ms to answer, like a slow cable
    def slow_cmd(dev, c):
        time.sleep(0.1)
        return "OK"
    sp = main.ShowPlayer(cmd_fn=slow_cmd, parse_fn=lambda dev: None,
                         cues_fn=lambda c: [])
    steps = [{"pose": [90 + i] + [90] * 9, "t": 200, "hold": 0} for i in range(6)]
    t0 = time.monotonic()
    sp.start("usb:QC", steps)
    sp.thread.join(timeout=10)
    took = time.monotonic() - t0
    # MOVE STOP 0.1 + entry 0.1 + 0.2, then five moves of 0.2 on the clock =
    # 1.4 s. Sleeping after each answer made it 1.9 s.
    t.ok(took < 1.65, "the round trips do not add up behind the time bar",
         "%.2f s for a 1.4 s run" % took)


def test_music_end_and_speed(t, main, shows):
    """Same day, two more: *let the music run N more seconds after the show,
    or N seconds in all*, and *make a sequence slower or faster in a show*."""
    steps = [{"pose": A, "t": 1000, "hold": 0}, {"pose": B, "t": 2000, "hold": 500}]
    base = {"items": [{"seq": "x.yaml"}], "music": "song.mp3"}
    t.eq(shows.Shows.music_stop_ms(dict(base, music_end="after", music_secs=4), steps),
         6500, "'after' stops the track N s after the show's last move")
    t.eq(shows.Shows.music_stop_ms(dict(base, music_end="total", music_secs=3), steps),
         3000, "'total' stops it N s after the first pose")
    t.eq(shows.Shows.music_stop_ms(base, steps), None,
         "with neither, the track stops with the last move (a cue, no timer)")

    said = []

    def cmd(dev, c):
        said.append((time.monotonic(), c))
        return "OK"
    sp = main.ShowPlayer(cmd_fn=cmd, parse_fn=lambda dev: None,
                         cues_fn=lambda c: [])
    moves = [{"pose": [90 + i] + [90] * 9, "t": 200, "hold": 0} for i in range(3)]
    sp.start("usb:QC", moves, music_stop_ms=900)
    sp.thread.join(timeout=5)
    time.sleep(1.2)
    first = [w for w, c in said if c.startswith("POSE")][0]
    off = [w for w, c in said if c == "PLAY STOP"]
    t.ok(len(off) == 1 and 0.95 < off[0] - first < 1.35,
         "the hub's timer stops the track after the moves are done",
         [(round(w - first, 2), c) for w, c in said])

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "seqs").mkdir()
        (d / "seqs" / "one.yaml").write_text(seq("one", A, B), encoding="utf-8",
                                             newline="\n")
        sh = shows.Shows(d / "shows", d / "seqs")
        norm = sh.steps({"items": [{"seq": "one.yaml"}]}, main.seq_steps)
        slow = sh.steps({"items": [{"seq": "one.yaml", "speed_pct": 50}]},
                        main.seq_steps)
        t.eq(slow[1]["t"], norm[1]["t"] * 2,
             "a sequence at 50 % in a show takes twice as long on the time bar")


def test_music_on_first_pose(t, main):
    """User 2026-09-27: *move to the start pose first, then start everything
    at the same time* - the song began during the walk to the first pose, so
    it ran seconds ahead of the moves."""
    said = []

    def cmd(dev, c):
        said.append((time.monotonic(), c))
        return "OK"
    sp = main.ShowPlayer(cmd_fn=cmd, parse_fn=lambda dev: None,
                         cues_fn=lambda c: list(c or []))
    steps = [{"pose": A, "t": 600, "hold": 0, "cues": ["PLAY song.mp3"]},
             {"pose": B, "t": 200, "hold": 0}]
    sp.start("usb:QC", steps)
    sp.thread.join(timeout=5)
    entry = [w for w, c in said if c.startswith("POSE 90")][0]
    play = [w for w, c in said if c.startswith("PLAY")]
    t.ok(play and play[0] - entry >= 0.55,
         "the show's music starts when the arm is ON the first pose, not during "
         "the walk there", [(round(w - entry, 2), c) for w, c in said])


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main    # noqa: PLC0415
    import shows   # noqa: PLC0415
    test_times(t, shows)
    test_steps(t, main, shows)
    test_clock(t, main)
    test_music_end_and_speed(t, main, shows)
    test_music_on_first_pose(t, main)
