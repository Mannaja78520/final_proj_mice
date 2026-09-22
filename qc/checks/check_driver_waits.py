"""A browser driver waits for the page; it never sleeps and hopes.

The flake that hit a different browser check in every full gate on 2026-09-22
had three causes (A26-94). This holds the third: a driver that ran its
measurement a fixed number of milliseconds after `load`. On a quiet machine
that was enough; under sixteen parallel workers Studio had not logged in, the
cable was not open or an iframe's document was not built, so the driver threw
on a missing element, or sent a mark nothing carried, and the check failed for
a reason that had nothing to do with the code it tests.

The cure is one line per driver: wait for a CONDITION (`qcStudioReady()`,
`qcWaitFor(...)`, or a poll of its own) and measure after it. Every driver did
this by 2026-09-23; this keeps the next one honest.

Drivers that only report marks and never read the page are listed in
qc/data/driver_waits.json - one entry, no code.
"""
import json
import re

import qc as F

AREA = "qc"
TITLE = "every browser driver waits for the page instead of sleeping"

WAITS = re.compile(r'qcStudioReady|qcWaitFor|function ready|'
                   r'typeof [A-Za-z_$]+ [!=]== "function"|setTimeout\(step')


def run(t):
    data = json.loads((F.QC / "data" / "driver_waits.json")
                      .read_text(encoding="utf-8"))
    allowed = set(data.get("marksOnly") or [])
    drivers, bad = [], []
    for f in sorted((F.QC / "checks").glob("check_*.py")):
        src = f.read_text(encoding="utf-8", errors="replace")
        if 'addEventListener("load"' not in src:
            continue
        drivers.append(f.stem)
        if f.stem in allowed or WAITS.search(src):
            continue
        bad.append(f.stem)
    t.ok(len(drivers) >= 20, "there are browser drivers to check (%d)" % len(drivers),
         "this check would pass on an empty list")
    t.ok(not bad, "every driver waits for something real before it measures",
         "these run on a timer and will fail under a full gate: %s" % ", ".join(bad))
    gone = sorted(allowed - set(drivers))
    t.ok(not gone, "the marks-only list names checks that still exist",
         "stale entries in qc/data/driver_waits.json: %s" % ", ".join(gone))
