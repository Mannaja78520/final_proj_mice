"""Every AI starts from HANDOFF.md and keeps its own task file.

Asked 2026-10-21: picking up after another AI took many turns, because the
state sat in five places (a file outside the repo, docs/HANDOVER.md,
docs/BRIDGE.md, PLAN rows, AGENTS.md) and none said which was current. Then:
several agents work at once, so one shared file would clash. The fix is
HANDOFF.md (stable rules) + one file per task in handoff/tasks/, and every
AI entry file (CLAUDE.md, AGENTS.md, GEMINI.md) pointing there at the top.
This keeps the pointers, the per-task fields (taken from the template, so a
new field needs no edit here) and tools/handoff.py's new/take/done.
"""
import importlib.util
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "every AI starts from HANDOFF.md and keeps one task file"

ENTRY_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")
TOP_LINES = 15
MAX_LINES = 150       # user 2026-10-21: every AI reads these whole, on every pick-up
# The instruction itself, not just the name: a heading alone tells nobody to read it.
POINTER = "Read `HANDOFF.md` first"


def run(t):
    hand = F.CODE / "HANDOFF.md"
    t.ok(hand.is_file(), "HANDOFF.md is at the repo root", "a new AI has nowhere to start")
    text = hand.read_text(encoding="utf-8") if hand.is_file() else ""
    # "## Doing now" (user 2026-10-22): what an agent is about to do is pushed
    # BEFORE the step, so a run that dies mid-step still says what it was on.
    for need in ("handoff/tasks/", "python tools/handoff.py list", "## Hard rules",
                 "## Doing now"):
        t.ok(need in text, "HANDOFF.md names %s" % need, "the pick-up steps lost a piece")

    t.ok(len(text.splitlines()) <= MAX_LINES, "HANDOFF.md stays under %d lines" % MAX_LINES,
         "%d lines - move detail to a task file or docs/" % len(text.splitlines()))

    for name in ENTRY_FILES:
        top = "\n".join((F.CODE / name).read_text(encoding="utf-8").splitlines()[:TOP_LINES])
        t.ok(POINTER in top and "handoff/tasks/" in top,
             "%s points to HANDOFF.md and the task files at the top" % name,
             "that AI reads its own rules first and never finds the handoff")

    spec = importlib.util.spec_from_file_location("handoff_under_test", str(F.CODE / "tools" / "handoff.py"))
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    need = set(H.fields(H.TEMPLATE.read_text(encoding="utf-8")))
    t.ok({"Owner", "Updated", "Last commit"} <= need, "the template carries Owner, Updated, Last commit",
         "got %s" % sorted(need))
    t.ok("## Doing now" in H.TEMPLATE.read_text(encoding="utf-8"),
         "the template has a Doing now section", "agents only record what is finished")
    for f in sorted(H.TASKS.glob("*.md")):
        body = f.read_text(encoding="utf-8")
        gone = need - set(H.fields(body))
        t.ok(not gone, "%s has every template field" % f.name, "missing: %s" % ", ".join(sorted(gone)))
        t.ok(len(body.splitlines()) <= MAX_LINES, "%s stays under %d lines" % (f.name, MAX_LINES),
             "%d lines - trim Done to the evidence that still matters" % len(body.splitlines()))

    with tempfile.TemporaryDirectory() as tmp:
        H.TASKS = Path(tmp)
        H.cmd_new("probe", "Probe task")
        made = H.TASKS / "probe.md"
        body = made.read_text(encoding="utf-8")
        t.ok(body.startswith("# Probe task") and H.fields(body).get("Owner", "x") == "",
             "new makes a free task file with the given title", body[:120])
        H.cmd_take("probe", "someone:1")
        t.ok(H.fields(made.read_text(encoding="utf-8")).get("Owner") == "someone:1",
             "take writes the agent id as Owner", made.read_text(encoding="utf-8")[:120])
        H.cmd_done("probe")
        t.ok(not made.exists(), "done removes the task file", "the finished task still looks open")
