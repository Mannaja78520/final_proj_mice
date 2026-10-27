"""A Studio sequence played on the board's own clock, as the firmware does it.

Mirrors firmware/src/core/SequencePlayer.cpp + modules/nong (NongMath.h):
a pose step lasts max(asked T or the show speed, slowest-servo floor, safety
floor), follows the cosine ease, and the next step leaves on that deadline.
`wait` adds to the same clock. `pace: music` swaps the safety cap for
music_dps (0 = only the servos' own limit) until `pace: normal` or the end,
as NongModule's PACE does. What the board lengthens is exactly where the
dance falls behind its music, so every lengthened step is reported.
"""
import math
import re
from dataclasses import dataclass

STEP = re.compile(r"^\s*-\s*([a-z_]+)\s*:\s*(.*?)\s*(#.*)?$")


def parse_sequence(text):
    """Studio's YAML: `steps:` then one `- key: value` per line."""
    steps, inside = [], False
    for line in text.splitlines():
        if line.startswith("steps:"):
            inside = True
            continue
        m = STEP.match(line) if inside else None
        if m:
            steps.append((m.group(1), m.group(2).strip().strip('"')))
    return steps


@dataclass
class Move:
    start: float          # s on the board clock
    asked: float          # s the file asked for (where the music is)
    took: float           # s the board will really take
    start_pose: list
    pose: list
    line: int             # which step in the file


class BoardClock:
    def __init__(self, rig, facts, safe_dps=None, speed_dps=None, music_dps=None):
        self.rig, self.facts = rig, facts
        self.safe_dps = safe_dps or facts.safe_dps
        self.music_dps = facts.music_dps if music_dps is None else music_dps
        self.cap = self.safe_dps
        self.music_at = None      # board time the first `play:` step fires
        self.speed = speed_dps or 60.0
        self.max_dps = [max(30.0, min(facts.max_dps, v or facts.max_dps)) for v in rig["servoMaxDps"]]

    def clamp(self, pose):
        return [min(self.rig["max"][i], max(self.rig["min"][i], v)) for i, v in enumerate(pose)]

    def floor_ms(self, a, b):
        """NongModule::minDuration: max(physical, safety), both >= the min move."""
        phys = max(abs(y - x) / d for x, y, d in zip(a, b, self.max_dps))
        if self.cap <= 0:                       # music pace, no cap: nongmath::moveFloor
            return max(self.facts.min_move_ms, int(phys * 1000))
        big = max(abs(y - x) for x, y in zip(a, b))
        safe = big * (math.pi / 2) / max(1.0, self.cap)
        return max(self.facts.min_move_ms, int(phys * 1000), int(safe * 1000))

    def plan(self, steps):
        cur = self.clamp(self.rig["home"])
        moves, t, asked_t = [], 0.0, 0.0
        for n, (key, value) in enumerate(steps):
            if key == "speed":
                self.speed = float(value)
            elif key == "pace":
                self.cap = self.music_dps if value.strip().lower() == "music" else self.safe_dps
            elif key == "play" and self.music_at is None:
                self.music_at = t
            elif key == "wait":
                t += max(0, float(value)) / 1000
                asked_t += max(0, float(value)) / 1000
            elif key == "pose":
                words = value.split()
                pose = self.clamp([float(v) for v in words[:10]])
                ask_ms = float(words[words.index("T") + 1]) if "T" in words else \
                    max(self.facts.min_move_ms, max(abs(y - x) for x, y in zip(cur, pose)) / max(1.0, self.speed) * 1000)
                took = max(ask_ms, self.floor_ms(cur, pose)) / 1000
                moves.append(Move(t, ask_ms / 1000, took, cur, pose, n))
                t += took
                asked_t += ask_ms / 1000
                cur = pose
        self.length, self.asked_length = t, asked_t
        self.cap = self.safe_dps                 # the show's end puts the pace back
        return moves

    @staticmethod
    def ease(f):
        return 0.0 if f <= 0 else 1.0 if f >= 1 else 0.5 - 0.5 * math.cos(math.pi * f)

    @staticmethod
    def target(moves, t):
        """The pose the board commands at time t (between frames it holds)."""
        for m in moves:
            if t < m.start + m.took:
                e = BoardClock.ease((t - m.start) / m.took)
                return [a + (b - a) * e for a, b in zip(m.start_pose, m.pose)]
        return list(moves[-1].pose) if moves else None
