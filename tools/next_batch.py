#!/usr/bin/env python3
"""Which tasks can be worked on together, and which have to wait.

    python tools/next_batch.py

A batch is several tasks edited together and put through ONE QC gate. The gate
is 9 to 14 minutes and has to stay full — three times on 2026-08-18 a change
broke a check that looked unrelated — so the saving is not in running less, it
is in fitting more finished work into each run.

NOTHING HERE IS HARDCODED, and that is the point.
--------------------------------------------------
The facts this needs — what a task touches, and what it waits for — live on the
task's own line in the STATE block of docs/PLAN.html, beside everything else
about that task:

    A2-2: todo  touches=hub.html  needs=A2-1  — a real Firmware section, ...
    A9-3: todo  touches=mice.css,hub.html,WebUI.h  — arrow-key reachable ...

Add a task, write what it touches on its line, and this file needs no edit.
A task with no `touches=` is reported as unknown rather than guessed at: a
wrong guess here means two people editing one file, which is a lost edit.

The rules it applies are deliberately few and each one is a mistake already
made in this project:

  same file      two tasks editing one file is a lost edit
  needs=         some work is pointless before other work: a Firmware SECTION
                 before the nav slot that shows it
  crosses 3+     a task spanning three files fails with three suspects
  [hw]           needs a real board, so it is not a candidate at all
  the gate       a change to qc/ or promote.py cannot be verified BY the gate,
                 and if it breaks the runner every other task in the batch
                 becomes unverifiable at the same moment
"""
import argparse
import re
import sys
from pathlib import Path

def _plan_path():
    """The REAL tree's plan, even when this file is running from .staging.

    docs/PLAN.html is in promote.py's SKIP_FILES: it records progress and is
    edited in the real tree as work lands, so a staging copy is stale the
    moment staging is made. Reading the staging copy showed finished tasks as
    todo and every annotation as missing.
    """
    here = Path(__file__).resolve().parent.parent
    if here.name == ".staging":
        here = here.parent
    return here / "docs" / "PLAN.html"


PLAN = _plan_path()

# Files that ARE the gate. Touch one and the batch is verified by something
# that just changed underneath it.
GATE = {"qc/", "promote.py"}
CROSSES_TOO_MUCH = 3
MAX_IN_BATCH = 6


class Task:
    """One line of the STATE block, and what it says about itself."""

    LINE = re.compile(r"^([A-Z]\d+-\d+):\s+(todo|doing|qc|done|blocked)\s*(.*)$")

    def __init__(self, tid, status, rest):
        self.id = tid
        self.status = status
        self.note = rest
        self.touches = self._annotation("touches", split=True)
        self.needs = self._annotation("needs")

    def _annotation(self, key, split=False):
        m = re.search(r"\b%s=(\S+)" % key, self.note)
        if not m:
            return [] if split else None
        return m.group(1).split(",") if split else m.group(1)

    @property
    def hardware(self):
        return "[hw]" in self.note

    @property
    def summary(self):
        clean = re.sub(r"\b(touches|needs)=\S+\s*", "", self.note)
        clean = clean.lstrip("— ").strip()
        return clean.split(".")[0][:70]

    def __repr__(self):
        return "<%s %s>" % (self.id, self.status)


def read_plan(path=PLAN):
    """Every task, with its continuation lines folded in."""
    tasks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = Task.LINE.match(line)
        if m:
            cur = Task(*m.groups())
            tasks.append(cur)
        elif cur is not None and line.startswith("      "):
            cur.note += " " + line.strip()
    return tasks


def choose(tasks, limit=MAX_IN_BATCH):
    """-> (batch, skipped, waiting). Every decision carries its reason."""
    done = {t.id for t in tasks if t.status == "done"}
    batch, skipped, waiting, claimed = [], [], [], set()

    for t in sorted((t for t in tasks if t.status == "todo"), key=lambda t: t.id):
        if t.hardware:
            continue
        if t.needs and t.needs not in done:
            waiting.append((t, "needs %s first" % t.needs))
            continue
        if not t.touches:
            skipped.append((t, "no touches= on its line, so it cannot be placed"))
            continue
        if GATE & set(t.touches):
            skipped.append((t, "changes the gate itself — alone, and first"))
            continue
        if len(t.touches) >= CROSSES_TOO_MUCH:
            skipped.append((t, "crosses %d files — alone" % len(t.touches)))
            continue
        clash = claimed & set(t.touches)
        if clash:
            skipped.append((t, "shares %s with this batch" % ", ".join(sorted(clash))))
            continue
        if len(batch) >= limit:
            skipped.append((t, "batch is full"))
            continue
        batch.append(t)
        claimed |= set(t.touches)

    return batch, skipped, waiting


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=MAX_IN_BATCH,
                    help="most tasks in one batch (default %d)" % MAX_IN_BATCH)
    ap.add_argument("--all", action="store_true", help="show why each one was left out")
    a = ap.parse_args(argv)

    tasks = read_plan()
    batch, skipped, waiting = choose(tasks, a.limit)

    print("BATCH — one QC gate covers all of these:")
    for t in batch:
        print("  %-7s %-28s %s" % (t.id, "+".join(t.touches), t.summary))
    if not batch:
        print("  (nothing can be batched — see below)")

    if a.all and skipped:
        print("\nNOT THIS TIME:")
        for t, why in skipped:
            print("  %-7s %s" % (t.id, why))

    if waiting:
        print("\nWAITING ON OTHER WORK:")
        for t, why in waiting:
            print("  %-7s %s" % (t.id, why))

    missing = [t.id for t in tasks
               if t.status == "todo" and not t.hardware and not t.touches]
    if missing:
        print("\nNO touches= YET (add it to the task's line in the plan):")
        print("  " + " ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
