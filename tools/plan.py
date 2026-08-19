#!/usr/bin/env python3
"""Move a task, or say what is running. One command, so it actually gets done.

    python tools/plan.py doing A2-1 A3-1        picked up, stamped with the clock
    python tools/plan.py qc A2-1                built, waiting on the gate
    python tools/plan.py done A2-1              landed
    python tools/plan.py running full QC for the batch
    python tools/plan.py running --clear        nothing in flight
    python tools/plan.py note A2-1 what changed and why
    python tools/plan.py show                   what the page says right now

WHY THIS EXISTS
---------------
docs/PLAN.html is the only record of progress, and the page in front of the
user renders from it. When updating it meant hand-editing HTML, it got updated
at milestones — so the page said *nothing in progress* for forty minutes while
a suite ran, and the user could not tell working from stalled. The fix is not
more discipline, it is making the update cost one line.

THE TIMESTAMP COMES FROM THE CLOCK, NEVER FROM MEMORY. Stamps written by hand
drifted by up to five hours in one session and two of them were in the future,
which makes the whole page untrustworthy.

The plan lives ONLY in the real tree — it is in promote.py's SKIP_FILES,
because it records progress and a staging copy is stale the moment it is made.
This finds it whether it is run from the real tree or from a staging copy.
"""
import argparse
import re
import sys
import time
from pathlib import Path

STATUSES = ("todo", "doing", "qc", "done", "blocked")


def plan_path():
    """The ONE plan, always in the real tree.

    Climbing out of `.staging` is not a nicety: a copy in there is a day old
    the moment it is written and nothing ever reads it back, so a session that
    updated it would look like it was recording progress and be recording
    nothing.

    MICE_PLAN overrides it, and exists for one reason: the QC check drives this
    tool for real, and a check that writes to the actual plan would stamp its
    own name over whatever is running while it does.
    """
    import os
    override = os.environ.get("MICE_PLAN")
    if override:
        return Path(override)
    here = Path(__file__).resolve().parent.parent
    if here.name == ".staging":
        here = here.parent
    return here / "docs" / "PLAN.html"


def now():
    return time.strftime("%Y-%m-%d %H:%M")


class Plan:
    """The STATE block, edited in place."""

    def __init__(self, path=None):
        self.path = path or plan_path()
        self.text = self.path.read_text(encoding="utf-8")

    def save(self):
        self.path.write_text(self.text, encoding="utf-8", newline="")
        self.publish()

    def publish(self):
        """Write the STATE block beside the page, as a script it can load.

        The page has to update while it is open, with nothing to press - asked
        for 2026-08-19. It is opened from file:///E:/..., and a file:// page may
        not fetch() or XHR a file next to it: the browser gives it a null origin
        and blocks the read. It MAY load a script. So the state is published as
        one, the page pulls it in on a timer, and redraws itself when the stamp
        moves.

        Never required: if this fails, the page still shows the STATE block
        inside it, which is what it did before any of this existed.
        """
        import json
        import time as _t
        block = self.text
        i = block.find("<pre id=" + chr(34) + "state" + chr(34) + ">")
        if i < 0:
            return
        i = block.index(">", block.index("<code", i)) + 1
        j = block.find("</code>", i)
        raw = block[i:j]
        # The page reads this back into a <pre>, so the HTML entities the file
        # stores have to come back as the characters they stand for.
        for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                        ("&quot;", chr(34)), ("&#39;", "'")):
            raw = raw.replace(ent, ch)
        out = {"stamp": _t.strftime("%Y-%m-%d %H:%M:%S"), "raw": raw}
        try:
            (self.path.parent / "plan_state.js").write_text(
                "window.PLAN_STATE=" + json.dumps(out) + ";" + chr(10),
                encoding="utf-8", newline="")
        except OSError:
            pass                      # a convenience, never a requirement

    def set_status(self, tid, status, stamp=True):
        """Rewrite one task's status and timestamp, keeping everything else."""
        pat = re.compile(r"^(%s):\s+(%s)(\s+\d{4}-\d\d-\d\d(?: \d\d:\d\d)?)?(\s*)"
                         % (re.escape(tid), "|".join(STATUSES)), re.M)
        when = ("  " + now()) if stamp else ""
        new, n = pat.subn(lambda m: "%s: %-5s%s  " % (m.group(1), status, when), self.text)
        if not n:
            raise SystemExit("no task %s in %s" % (tid, self.path.name))
        self.text = new
        return True

    def set_running(self, what):
        line = "# RUNNING: " + (what or "nothing right now")
        if what:
            line += ", started " + now()
        new, n = re.subn(r"^# RUNNING: .*$", line, self.text, count=1, flags=re.M)
        if not n:                                  # first use: put it at the top
            new = self.text.replace("<code>STATE\n", "<code>STATE\n" + line + "\n", 1)
        self.text = new

    def append_note(self, tid, note):
        # Anything may sit between the status and the em dash — a timestamp,
        # and annotations like touches= and needs=. Match up to the dash rather
        # than trying to spell out what is allowed in front of it.
        # Anything may sit between the status and the dash: a timestamp,
        # and annotations like touches= and needs=. Match up to the dash
        # rather than trying to spell out what is allowed in front of it.
        # The dash is written as an escape — a literal one has been mangled
        # by a shell more than once in this project.
        pat = re.compile("^(" + re.escape(tid) + "[^\u2014\n]*\u2014.*)$", re.M)
        new, n = pat.subn(lambda m: m.group(1) + " " + note, self.text, count=1)
        if not n:
            raise SystemExit("no task %s" % tid)
        self.text = new

    def summary(self):
        rows = re.findall(r"^([A-Z]\d+-\d+):\s+(\w+)", self.text, re.M)
        counts = {s: sum(1 for _, x in rows if x == s) for s in STATUSES}
        run = re.search(r"^# RUNNING: (.*)$", self.text, re.M)
        live = [tid for tid, s in rows if s in ("doing", "qc")]
        return counts, (run.group(1) if run else "(no RUNNING line)"), live


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", help="one of: %s, running, note, show" % ", ".join(STATUSES))
    ap.add_argument("rest", nargs="*", help="task ids, or the text for running/note")
    ap.add_argument("--clear", action="store_true", help="running: nothing in flight")
    a = ap.parse_args(argv)

    p = Plan()
    if a.action == "show":
        counts, run, live = p.summary()
        print(" · ".join("%d %s" % (v, k) for k, v in counts.items() if v))
        print("RUNNING:", run)
        print("in flight:", ", ".join(live) or "nothing")
        return 0

    if a.action == "running":
        p.set_running("" if a.clear else " ".join(a.rest))
    elif a.action == "note":
        p.append_note(a.rest[0], " ".join(a.rest[1:]))
    elif a.action in STATUSES:
        for tid in a.rest:
            p.set_status(tid, a.action)
    else:
        raise SystemExit("unknown action: %s" % a.action)

    p.save()
    counts, run, live = p.summary()
    print("plan updated — in flight: %s | %s" % (", ".join(live) or "nothing", run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
