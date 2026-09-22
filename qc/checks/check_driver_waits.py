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

Drivers that wait in their own way are listed, with the reason, in
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
    allowed = set(data.get("waitsItsOwnWay") or {})
    drivers, bad = [], []
    for f in sorted((F.QC / "checks").glob("check_*.py")):
        src = f.read_text(encoding="utf-8", errors="replace")
        # Two shapes: a driver that runs on `load`, and one that measures a page
        # inside an iframe from a bare timer. Both used to bet on a number.
        if ('addEventListener("load"' not in src
                and not re.search(r"^setTimeout\(", src, re.M)):
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
    t.ok(not gone, "the exception list names checks that still exist",
         "stale entries in qc/data/driver_waits.json: %s" % ", ".join(gone))
    empty = sorted(k for k, v in (data.get("waitsItsOwnWay") or {}).items()
                   if not str(v).strip())
    t.ok(not empty, "and every exception says why it is one",
         "no reason given for: %s" % ", ".join(empty))

    # A MARK MUST OUTLAST THE HUB'S OWN USE OF THE CABLE. The port probe holds
    # the fake port for up to 5.4 s (an RS485 census) and refuses every mark
    # meanwhile. Four tries over 600 ms gave up inside that window, so three
    # checks reported "[]" in one gate and passed alone (A26-94).
    lib = (F.QC / "lib" / "browser.py").read_text(encoding="utf-8")
    budgets = [int(a) * int(b) for a, b in
               re.findall(r"if \(tries >= (\d+)\) return;.*?setTimeout\(go, (\d+)\)",
                          lib, re.S)]
    t.ok(len(budgets) == 2, "both preludes retry a refused mark (%d found)" % len(budgets),
         "the studio page and the raw page each carry a copy")
    t.ok(budgets and min(budgets) >= 6000,
         "and they keep trying past the bus census (worst %d ms)"
         % (min(budgets) if budgets else 0),
         "a mark refused while the hub holds the cable is a check that reports "
         "nothing at all")
