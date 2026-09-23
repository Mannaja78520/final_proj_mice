"""SHOWS: saved sequences played one after another.

Asked 2026-09-17: *another tab to mix a lot of sequence ... link the sequence in
series ... like greeting then run the sequence byebye ... mix and match*.

A show is one small JSON file in shows/, listing sequence files by name:

    {"name": "welcome", "loop": false,
     "items": [{"seq": "greeting.yaml", "hold": 500},
               {"seq": "wave.yaml", "repeat_mode": "times", "repeat": 3},
               {"seq": "sway.yaml", "repeat_mode": "seconds", "repeat": 60},
               {"seq": "byebye.yaml"}]}

Per item:
    hold          ms of stillness AFTER the item. 0 = none, and 0 is the default
                  (user 2026-09-23: *no stop before go to other sequence if not
                  insert pause number*).
    repeat_mode   "" play once - "times" play `repeat` times - "seconds" keep
                  playing whole passes until `repeat` seconds have elapsed.
    repeat        the number that goes with the mode.

Seconds mode never cuts a pass in half: it starts another pass while the item's
elapsed time is still under the target, so 60 s of a 22 s sequence is three
passes (66 s). A truncated pass would stop the arm wherever the clock ran out,
which is not a pose anybody chose.

Seconds counts the times the hub ASKS for, not the times the board reports. The
board may lengthen a move (its own speed cap), so a 60 s item can run a little
longer than 60 s. It can never run SHORT, which is the direction that would
matter, and the hub cannot know the board's answer before it sends the move.

The sequences are never copied or changed, so one greeting can sit in many
shows. A person can edit the file by hand; Studio's Shows tab writes the same.
The hub plays a show as one list of steps (ShowPlayer), so it runs over any
link and the robot's own speed cap times the move from one sequence into the next.
"""
import json
import re
import time
from pathlib import Path

NAME = re.compile(r"^[A-Za-z0-9_\-][A-Za-z0-9 _.\-]{0,79}$")
REPEAT_MODES = ("", "times", "seconds")
DEF_DPS = 60.0       # the same fallback seq_steps uses for a file with no speed
MIN_T = 80           # ms, the floor the firmware, Studio and ShowPlayer share
# A 60 s target against a sequence that parses to almost nothing would expand
# into tens of thousands of steps and take the hub down with it. Refuse, and
# say which sequence, rather than building a list nobody can stop.
MAX_PASSES = 500


def total_ms(steps):
    return sum(int(s.get("t", 0)) + int(s.get("hold", 0)) for s in steps)


def link_time(prev, nxt, dps):
    """How long the move from one sequence's end into the next one's start takes.

    The same rule the firmware and Studio use: biggest joint change over the
    sequence's own speed, with the shared 80 ms floor. Identical poses give the
    floor, so two sequences that end and start on the same pose run straight on.
    """
    delta = max((abs(a - b) for a, b in zip(prev, nxt)), default=0.0)
    return max(MIN_T, int(delta / max(1.0, float(dps)) * 1000))


def _file(name):
    name = str(name or "").strip()
    if name.endswith(".json"):
        name = name[:-5]
    if not NAME.match(name):
        raise ValueError("a show name may use letters, numbers, space, _ - and .")
    return name + ".json"


class Shows:
    """The shows folder: list, load, save, delete, and turn one into steps."""

    def __init__(self, folder: Path, sequences: Path):
        self.folder = Path(folder)
        self.sequences = Path(sequences)

    def names(self):
        if not self.folder.is_dir():
            return []
        return sorted(p.stem for p in self.folder.glob("*.json") if p.is_file())

    def load(self, name):
        f = self.folder / _file(name)
        if not f.is_file():
            raise FileNotFoundError("no show called %s" % name)
        return self.clean(json.loads(f.read_text(encoding="utf-8")))

    @staticmethod
    def clean(show):
        """Only the fields a show has, with sane values - what is saved is what plays."""
        items = []
        for it in (show or {}).get("items") or []:
            it = it or {}
            seq = str(it.get("seq") or "").strip()
            if not seq:
                continue
            mode = str(it.get("repeat_mode") or "").strip().lower()
            if mode not in REPEAT_MODES:
                mode = ""
            try:
                n = float(it.get("repeat") or 0)
            except (TypeError, ValueError):
                n = 0
            # A mode with no number, or a number with no mode, is half a
            # setting: it would play once and look like the repeat was lost.
            # Both or neither, decided HERE so the file, the editor and the
            # player can never read it three ways.
            if mode == "times":
                n = int(round(n))
            elif mode == "seconds":
                n = round(float(n), 3)
            if (mode == "times" and n < 2) or (mode == "seconds" and n <= 0):
                mode = ""
            if not mode:
                n = 0
            items.append({"seq": seq, "hold": max(0, int(it.get("hold") or 0)),
                          "repeat_mode": mode, "repeat": n})
        return {"name": str((show or {}).get("name") or "").strip(),
                "loop": bool((show or {}).get("loop")), "items": items}

    def save(self, show):
        show = self.clean(show)
        fname = _file(show["name"])
        self.folder.mkdir(parents=True, exist_ok=True)
        f = self.folder / fname
        existed = f.exists()
        tmp = f.with_suffix(".tmp")
        tmp.write_bytes(json.dumps(show, indent=1).encode("utf-8"))
        tmp.replace(f)
        return fname, existed

    def delete(self, name):
        """Moved into shows/.deleted/, never erased: a mis-click is recoverable."""
        f = self.folder / _file(name)
        if not f.is_file():
            raise FileNotFoundError("no show called %s" % name)
        bin_ = self.folder / ".deleted"
        bin_.mkdir(exist_ok=True)
        dest = bin_ / (time.strftime("%Y%m%d-%H%M%S_") + f.name)
        f.replace(dest)
        return ".deleted/" + dest.name

    def steps(self, show, parse, marks=None):
        """All the sequences' steps, in order. parse(text) is main.seq_steps.

        A missing or broken sequence stops the whole show with its name: playing
        half a show and skipping the rest silently is worse than not starting.

        `marks`, when a list is passed in, is filled with one row per pass -
        {at, step, seq, pass, of} - so Studio can draw the same chain on its own
        timeline and name each piece (A31-3). The player ignores it.
        """
        show = self.clean(show)
        if not show["items"]:
            raise ValueError("this show has no sequences in it yet")
        out = []
        for n, it in enumerate(show["items"], 1):
            f = self.sequences / it["seq"]
            if "/" in it["seq"] or "\\" in it["seq"] or not f.is_file():
                raise ValueError("step %d: no saved sequence called %s" % (n, it["seq"]))
            try:
                parsed = parse(f.read_text(encoding="utf-8"))
            except ValueError as e:
                raise ValueError("step %d, %s: %s" % (n, it["seq"], e))
            got = parsed["steps"]
            if not got:
                raise ValueError("step %d: %s has no poses" % (n, it["seq"]))
            speed = float(parsed.get("speed") or 0) or DEF_DPS
            # MAX_PASSES guarded only the seconds branch at first, so a `times`
            # of a million - one typo in a hand-edited shows/*.json - built a
            # million passes and took the hub's memory with it. Found by Codex
            # 2026-09-23 reviewing the landed change. Refused UP FRONT, before
            # a single pass is built, because the point is not to build it.
            if it["repeat_mode"] == "times" and it["repeat"] > MAX_PASSES:
                raise ValueError("step %d: %s cannot repeat %d times (the most "
                                 "is %d)" % (n, it["seq"], it["repeat"], MAX_PASSES))
            passes, elapsed = 0, 0
            while True:
                pass_steps = [dict(s) for s in got]
                # THE GAP THAT LOOKED LIKE A STOP. Every sequence's first step
                # is its start pose, timed for travel from wherever the robot
                # happened to be - yakyai carries T 3273. Chained, the arm is
                # already standing on the previous pose, so that 3.3 s was the
                # arm holding almost still between sequences (user 2026-09-23:
                # *make every sequence in show run continute no stop*). Re-time
                # it from the REAL previous pose at this sequence's own speed.
                # The board lengthens it again if its own cap needs more, and
                # ShowPlayer._took waits for what the board says, so asking for
                # the short time is always safe.
                if out:
                    pass_steps[0]["t"] = link_time(out[-1]["pose"],
                                                   pass_steps[0]["pose"], speed)
                if marks is not None:
                    marks.append({"at": total_ms(out), "step": len(out),
                                  "seq": it["seq"], "item": n,
                                  "pass": passes + 1,
                                  "of": it["repeat"] if it["repeat_mode"] == "times" else 0,
                                  "mode": it["repeat_mode"]})
                out += pass_steps
                passes += 1
                elapsed += total_ms(pass_steps)
                if it["repeat_mode"] == "times":
                    if passes >= it["repeat"]:
                        break
                elif it["repeat_mode"] == "seconds":
                    # START another whole pass while the target is not reached
                    # yet; never cut one short. A pass stopped mid-move leaves
                    # the arm at a pose nobody chose.
                    if elapsed >= it["repeat"] * 1000:
                        break
                    if passes >= MAX_PASSES:
                        raise ValueError(
                            "step %d: %s is too short to fill %g s (it would "
                            "repeat more than %d times)"
                            % (n, it["seq"], it["repeat"], MAX_PASSES))
                else:
                    break
            out[-1]["hold"] = out[-1].get("hold", 0) + it["hold"]   # pause after it
        return out
