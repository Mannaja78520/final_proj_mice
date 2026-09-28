"""One lost reply does not end a show; a robot that is gone does, and goes quiet.

Real nong, 2026-09-28: a Show reached its start pose, then COM21 said "no reply
from bus id 67". Every POSE went through `_say`, and ONE exception there ended
the show thread: the arm froze on the start pose while the song it had just
started played on - the hub only silences music in stop(), and a show that
dies of an error never calls it. On RS485 a reply can be lost to a busy board
(check_id3_skip has the case that hit), so a single miss is a hiccup: the next
pose still goes out on its time and the arm catches up, the board capping a
move that would be too fast.

Held, on real threads with a fake robot whose replies go missing on cue:
  * one lost reply: every keyframe still goes out, the show ends normally,
    and the status says a move was missed and the show carried on;
  * misses that are not in a row never add up to giving up;
  * MAX_MISSES in a row: the show stops sending, says why, and the song is
    stopped - but a show with no music sends no PLAY STOP (a board with no
    speaker would answer ERR, and that would be the last word on the stop).
"""
import sys
import threading
import time

import qc as F

AREA = "hub"
TITLE = "one lost reply does not end a show; a robot that is gone ends it quietly"

N = 7                     # keyframes: the start pose and six moves


class Robot:
    """dev_cmd for a robot whose replies go missing when `lose(n)` says so,
    n counting POSE commands from 1. Records every command it was sent."""

    def __init__(self, lose):
        self.lose = lose
        self.sent = []
        self.poses = 0
        self._lock = threading.Lock()

    def __call__(self, dev, c):
        with self._lock:
            self.sent.append(c)
            n = 0
            if c.startswith("POSE"):
                self.poses += 1
                n = self.poses
        if n and self.lose(n):
            time.sleep(0.05)              # stands in for usb_cmd's 2 s wait
            raise TimeoutError("no reply from COM99 (bus id 67)")
        return "OK"


def _steps(music):
    steps = [{"pose": [90 + (i % 2) * 10] * 10, "t": 100, "hold": 0}
             for i in range(N)]
    if music:
        steps[0]["cues"] = ["play: song.mp3"]
    return steps


def _play(main, lose, music=True):
    robot = Robot(lose)
    sp = main.ShowPlayer(cmd_fn=robot)
    sp.start("usb:COM99:67", _steps(music), name="qc_misses")
    end = time.time() + 15
    while sp.running() and time.time() < end:
        time.sleep(0.05)
    time.sleep(0.2)                       # anything sent after it gave up
    return robot, sp.status()


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415
    most = main.ShowPlayer.MAX_MISSES
    t.ok(most >= 2, "a show survives at least one lost reply", most)

    # ---- one hiccup ---------------------------------------------------
    robot, st = _play(main, lambda n: n == 3)
    t.eq(robot.poses, N, "every keyframe still went out after one lost reply")
    t.ok(not st["running"] and st["step"] == N - 1,
         "and the show ran to its last keyframe", st)
    t.ok("carried on" in (st["error"] or ""),
         "the status says a move was missed and the show carried on", st["error"])
    t.ok("PLAY STOP" not in robot.sent,
         "a show that finished leaves its song alone", robot.sent[-4:])

    # ---- scattered misses never add up ---------------------------------
    robot, st = _play(main, lambda n: n in (2, 4, 6))
    t.eq(robot.poses, N, "misses that are not in a row never end the show")

    # ---- the robot is gone ---------------------------------------------
    good = 2
    robot, st = _play(main, lambda n: n > good)
    t.eq(robot.poses, good + most,
         "after MAX_MISSES in a row the show stops sending poses")
    t.ok(not st["running"] and "no reply" in (st["error"] or "")
         and "carried on" not in (st["error"] or ""),
         "and says why it stopped", st)
    t.ok(robot.sent and robot.sent[-1] == "PLAY STOP",
         "and its song is stopped, not left playing over a still arm",
         robot.sent[-4:])

    robot, st = _play(main, lambda n: n > good, music=False)
    t.ok("PLAY STOP" not in robot.sent,
         "a show with no music sends no PLAY STOP when it gives up",
         robot.sent[-4:])
