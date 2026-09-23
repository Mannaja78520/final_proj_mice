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
                  playing whole passes until `repeat` seconds have elapsed -
                  "exact" fill `repeat` seconds the same way and then CUT to
                  them, so the item takes exactly that long.
    repeat        the number that goes with the mode.

"seconds" and "exact" differ only in the last pass. "seconds" lets it finish and
so runs over; "exact" cuts at the last keyframe that fits and hands what is left
of the budget to the move into the NEXT sequence's start pose, so the arm is
already travelling there during the time the cut freed and arrives on the
deadline. That is what keeps a show on a timetable without the audience seeing a
join (asked 2026-09-23).

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
REPEAT_MODES = ("", "times", "seconds", "exact")
DEF_DPS = 60.0       # the same fallback seq_steps uses for a file with no speed
MIN_T = 80           # ms, the floor the firmware, Studio and ShowPlayer share
# A 60 s target against a sequence that parses to almost nothing would expand
# into tens of thousands of steps and take the hub down with it. Refuse, and
# say which sequence, rather than building a list nobody can stop.
MAX_PASSES = 500


def total_ms(steps):
    return sum(int(s.get("t", 0)) + int(s.get("hold", 0)) for s in steps)


def cut_to_budget(out, first, began_at, budget, next_pose, speed, marks=None):
    """Cut one item down to `budget` ms and say what is left of it.

    Asked 2026-09-23: *make the show can select that sequence run only for
    ...... sec ... maybe cut the sequence and move to the pose of new sequence
    on time then show on time like that with seamless viewer will not notice
    it*. A show on a timetable cannot wait for a sequence to finish, so the
    sequence is cut wherever it has got to.

    The cut is at a KEYFRAME, never inside a move: the hub's clock sends whole
    poses, and stopping half way through one would leave the arm at a position
    nobody chose - the same reason `seconds` mode never cuts. What makes it
    seamless is the returned remainder: the caller spends it on the move into
    the NEXT sequence's start pose, so the arm is already travelling there
    during the time the cut freed, and arrives exactly on the deadline.

    Returns the leftover ms. Keeps at least one step, because an item that
    contributes nothing at all is a sequence the operator cannot see.
    """
    end = began_at + budget
    running, keep = began_at, first
    for i in range(first, len(out)):
        step_end = running + out[i]["t"] + out[i].get("hold", 0)
        # RESERVE THE HAND-OVER. The next sequence has to START on time, not
        # merely be sent for at the deadline, so the move into its first pose
        # has to fit inside the budget too. Cutting without this was the first
        # version and it ran 333 ms late on every item (measured 2026-09-23).
        hand = link_time(out[i]["pose"], next_pose, speed) if next_pose else 0
        if step_end + hand > end and i > first:
            break
        running = step_end
        keep = i
    del out[keep + 1:]
    if marks is not None:
        marks[:] = [m for m in marks if m["step"] <= keep]
    # A single step longer than the whole budget still has to fit: shorten it
    # rather than overrun the timetable on the very first move.
    hand = link_time(out[keep]["pose"], next_pose, speed) if next_pose else 0
    if running + hand > end and keep == first:
        s = out[keep]
        s["hold"] = 0                       # the pause goes before the move does
        s["t"] = max(MIN_T, min(s["t"], budget - hand))
        running = began_at + s["t"]
    return max(0, end - running)


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
            # A MODE THIS HUB DOES NOT KNOW IS A VERSION MISMATCH, NOT A TYPO.
            # It was silently blanked to "play once", and on 2026-09-23 that
            # cost the user their settings twice over: the Studio page (served
            # from disk, so current) offered "run for exactly ... s" while the
            # running MiceHub.exe was built before that mode existed, so every
            # show answered "play once" - and SAVING the show wrote the blanked
            # value back over the 42 s and 15 s they had typed. Say it instead.
            if mode and mode not in REPEAT_MODES:
                raise ValueError(
                    "this hub does not understand the repeat mode %r. Its "
                    "MiceHub.exe is older than the page that asked for it - "
                    "rebuild it with: python -m PyInstaller --clean MiceHub.spec"
                    % mode)
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
            elif mode in ("seconds", "exact"):
                n = round(float(n), 3)
            if ((mode == "times" and n < 2)
                    or (mode in ("seconds", "exact") and n <= 0)):
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
        owed = 0          # budget a cut item left for the next hand-over
        pending = None    # an `exact` item waiting to be cut (see below)
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
            # THE CUT WAITS FOR THIS MOMENT. An `exact` item cannot be cut
            # until the pose it is handing over TO is known, because the move
            # into that pose has to fit inside its budget. So the previous item
            # is cut here, now that this sequence's first pose is in hand.
            if pending:
                owed = cut_to_budget(out, pending[0], pending[1], pending[2],
                                     got[0]["pose"], speed, marks)
                pending = None
            began_at, began_step = total_ms(out), len(out)
            # The show's clock starts ON its first pose, as Studio's time bar
            # does. The first entry move comes from wherever the robot stands,
            # so it counts toward no item's seconds - counted, a 52 s item drew
            # as 48.7 s beside yakyai's 3.3 s entry (user 2026-09-23, A31-16).
            entry = got[0].get("t", 0) if not out else 0
            passes, elapsed = 0, -entry
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
                # A previous item was CUT to its budget and owes the rest of
                # that budget to this move. Spending it here is what makes the
                # hand-over land exactly on the deadline instead of overrunning
                # it: the arm leaves wherever the cut left it and arrives at
                # this sequence's start pose right on time (A31-14).
                handover = bool(owed and passes == 0)
                if handover:
                    pass_steps[0]["t"] = max(MIN_T, owed)
                    owed = 0
                if marks is not None:
                    # `handover`: this step's move is paid from the CUT item's
                    # budget, so Studio draws it as the end of that item and the
                    # next name lands on the deadline (user 2026-09-23, A31-16).
                    marks.append({"at": total_ms(out), "step": len(out),
                                  "seq": it["seq"], "item": n,
                                  "pass": passes + 1,
                                  "of": it["repeat"] if it["repeat_mode"] == "times" else 0,
                                  "mode": it["repeat_mode"],
                                  "handover": handover})
                out += pass_steps
                passes += 1
                elapsed += total_ms(pass_steps)
                if it["repeat_mode"] == "times":
                    if passes >= it["repeat"]:
                        break
                elif it["repeat_mode"] in ("seconds", "exact"):
                    # START another whole pass while the target is not reached
                    # yet. `seconds` never cuts one short and so overshoots;
                    # `exact` fills the same way and is then CUT to the budget
                    # below, which is the difference between the two.
                    if elapsed >= it["repeat"] * 1000:
                        break
                    if passes >= MAX_PASSES:
                        raise ValueError(
                            "step %d: %s is too short to fill %g s (it would "
                            "repeat more than %d times)"
                            % (n, it["seq"], it["repeat"], MAX_PASSES))
                else:
                    break
            # The pause goes on BEFORE the cut, so an `exact` item's pause is
            # inside its budget like everything else rather than pushing the
            # deadline out. Dropping it instead would silently ignore a number
            # the operator typed.
            out[-1]["hold"] = out[-1].get("hold", 0) + it["hold"]
            if it["repeat_mode"] == "exact":
                pending = (began_step, began_at,
                           int(round(it["repeat"] * 1000)) + entry)
        # The LAST item was `exact`: there is no next sequence to spend the
        # rest of its budget travelling into, so it is held instead. The show
        # is still exactly as long as it was asked to be.
        if pending:
            owed = cut_to_budget(out, pending[0], pending[1], pending[2],
                                 None, DEF_DPS, marks)
        if owed:
            out[-1]["hold"] = out[-1].get("hold", 0) + owed
            owed = 0
        return out
