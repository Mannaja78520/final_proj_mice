"""Every task on the plan page carries its OWN area name.

Found by the user, 2026-08-27: the Progress card said A24-16 was part of
*Getting it onto another PC*, when A24-16 is the nong's speaker. Nothing was
wrong with the task. The STATE block's headings simply stopped at `# A15`
while the ids ran on to A24, and the renderer gave each task **the last
heading it had seen above it** — so about sixty tasks wore the A15 name, and
tasks added out of order wore whichever heading they happened to land beside.

A wrong area name is not cosmetic here: the page is how the user checks that
work is happening, and a task filed under the wrong heading reads as work on
something they did not ask for. So two halves are held:

* every id prefix in the STATE block has a `# A<n>  Title` heading, so a new
  area cannot be opened without naming it;
* the page labels a task by its id prefix, not by position. The fallback to
  the nearest heading stays for an id that has no heading yet, which is why
  the first half exists at all.

Both read the REAL plan: `docs/PLAN.html` never lives in `.staging`
(`check_plan_live` holds that), so this climbs out the same way plan.py does.
"""
import re
import sys

import qc as F

AREA = "docs"
TITLE = "every task on the plan is filed under its own area"


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import plan  # noqa: PLC0415 — the same module the page is written by

    text = plan.plan_path().read_text(encoding="utf-8", errors="replace")

    headings = dict(re.findall(r"^#\s+(A\d+)\s+(.+)$", text, re.M))
    prefixes = sorted({m.group(1) for m in re.finditer(r"^(A\d+)-\d+:", text, re.M)},
                      key=lambda s: int(s[1:]))
    t.ok(prefixes, "the STATE block has tasks to file", len(prefixes))

    missing = [p for p in prefixes if p not in headings]
    t.eq(missing, [], "every area with tasks in it has a heading")

    for p in prefixes:
        title = headings.get(p, "")
        t.ok(len(title.strip()) >= 4, "%s's heading says something" % p, repr(title))

    # The renderer: labelled by id, not by whatever sits above the line.
    page = plan.plan_path().read_text(encoding="utf-8", errors="replace")
    t.contains(page, "AREA[m[1].split('-')[0]]",
               "the page reads a task's area from its own id")
    t.contains(page, "^#\\\\s+(A\\\\d+)\\\\s+(.+)$".replace("\\\\", "\\"),
               "and builds that lookup from the headings themselves")
