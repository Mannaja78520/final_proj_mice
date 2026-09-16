"""The packing list says what to bring, and stays true as tasks move.

Asked for 2026-08-19: *which one need SD card, which one need RS485, which one
need the thing*. The answer lives twice on purpose - `hw=` on each task line,
and a table sorted by PART, because that is the order things get packed in.

Two copies of one fact drift. The packing table is hand-written HTML and cannot
update itself, so this check is what keeps it honest:

  * a task that needs hardware must be NAMED in the list, or the part it needs
    gets left at home;
  * a task named in the list must still exist, or somebody packs for work that
    no longer exists;
  * and when every task needing a part is done, the row must SAY the part is no
    longer needed - the second half of what this task asked for. A packing list
    that only ever grows is one nobody trusts.
"""
import json
import re

import qc as F

AREA = "docs"
TITLE = "the packing list matches the tasks that actually need hardware"

DONE_WORDS = ("done", "no longer", "not needed", "here, and working", "finished")


def docs_dir():
    """Where the ONE real plan lives.

    `docs/PLAN.html` and `plan_state.js` are in promote.py's SKIP_FILES: they
    are written by the running system, not source, so they never travel into
    staging. There is exactly one copy, and a gate running from `.staging` has
    to look next door for it rather than skip - a check that quietly skips
    during every gate guards nothing at all.
    """
    # Ask for the file this check actually reads. Testing for plan_state.js
    # instead was wrong: that one is NOT in SKIP_FILES, so it IS copied into a
    # working copy while PLAN.html beside it is not. In `.staging` the two
    # happen to sit together, left from before PLAN.html was skipped; in a
    # freshly made tree only plan_state.js arrives, the test said *here*, and
    # the check died on a PLAN.html that was never copied. Found 2026-09-10 in
    # `.staging-integral`, the first tree made since the skip rule existed.
    # ...and asking whether the file EXISTS is still not enough. `.staging/docs`
    # holds a deliberate 919-byte SIGNPOST titled *The plan is not here*, which
    # redirects a reader to the real tree. It satisfied is_file(), so this check
    # read the signpost, found no packing table and failed with `there is a
    # packing list` — while the real 288 KB plan sat next door with one in it.
    # Found 2026-09-10. So test for the real thing: only the published plan
    # loads plan_state.js, and the signpost carries no script at all.
    here = F.CODE / "docs"
    p = here / "PLAN.html"
    if p.is_file() and "plan_state.js" in p.read_text(encoding="utf-8",
                                                     errors="replace"):
        return here
    return F.CODE.parent / "docs"


def state_lines():
    """Each task line from the published plan state."""
    js = (docs_dir() / "plan_state.js").read_text(encoding="utf-8")
    raw = json.loads(js[js.index("=") + 1:].rstrip().rstrip(";"))["raw"]
    out = {}
    for ln in raw.splitlines():
        m = re.match(r"^([A-Z]\d+-\d+):\s+(\w+)\s", ln)
        if m:
            out[m.group(1)] = {"status": m.group(2), "line": ln}
    return out


def run(t):
    plan = (docs_dir() / "PLAN.html").read_text(encoding="utf-8",
                                               errors="replace")
    tasks = state_lines()
    if not t.ok(tasks, "the plan state has tasks in it"):
        return

    # ---- the packing table exists and names tasks --------------------
    i = plan.find('id="packing"')
    if not t.ok(i > 0, "there is a packing list"):
        return
    table = plan[plan.find("<table", i):plan.find("</table>", i)]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)
    t.ok(len(rows) >= 3, "with rows in it", "found %d" % len(rows))

    named = set(re.findall(r"\b([A-Z]\d+-\d+)\b", table))
    t.ok(named, "and it names the tasks each part unlocks",
         "a row that names no task is a part nobody can justify packing")

    # ---- every named task is real ------------------------------------
    ghosts = sorted(n for n in named if n not in tasks)
    t.eq(ghosts, [],
         "every task the packing list names still exists")

    # ---- every hardware task is on the list --------------------------
    # `hw=` is what makes a task skippable when the boards are elsewhere, so a
    # task carrying one and named nowhere means its part gets left at home.
    # THE FIELD, not the word. A task line is `id: status <when> field=... —
    # note`, and a NOTE that happens to mention hw= is prose, not a
    # requirement. Matching the whole line reported A12-3 as needing hardware
    # because a note about the bench constraint listed the field by name.
    needs_hw = {tid for tid, d in tasks.items()
                if "hw=" in d["line"].split("—")[0]}
    open_hw = {tid for tid in needs_hw if tasks[tid]["status"] != "done"}
    missing = sorted(tid for tid in open_hw if tid not in named)
    t.eq(missing, [],
         "every unfinished task that needs hardware is on the packing list")

    # ---- a part whose tasks are all done says so ---------------------
    for row in rows:
        ids = re.findall(r"\b([A-Z]\d+-\d+)\b", row)
        if not ids:
            continue
        live = [i2 for i2 in ids if i2 in tasks and tasks[i2]["status"] != "done"]
        if live:
            continue
        part = re.sub(r"<[^>]+>", " ", row).strip()[:48]
        t.ok(any(w in row.lower() for w in DONE_WORDS),
             "a part whose tasks are all finished says so: %s" % part,
             "the second half of what this task asked for - a packing list "
             "that only ever grows is one nobody trusts, and it is read while "
             "packing, in a hurry")

    # ---- and new tasks can carry the field ---------------------------
    src = (F.CODE / "tools" / "plan.py").read_text(encoding="utf-8")
    t.contains(src, '"--hw"',
               "plan.py can set hw= when a task is added")
    add = src[src.find("    def add(self, tid"):]
    add = add[:add.find("\n    def ", 1)]
    t.contains(add, "hw=%s",
               "and writes it onto the task line")
    t.ok("hw" in add.split("def add(self, tid")[0] or "hw=None" in add[:120],
         "as an argument, not a guess",
         "a task added without it looks like a task a PC can finish, and gets "
         "picked up when the boards are not on the bench")
