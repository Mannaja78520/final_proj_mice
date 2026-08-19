"""SHRUG travels 26 degrees, and every place that says so agrees.

Measured on the robot 2026-08-19, after the shoulder bar was rebuilt as a 4-bar
linkage: the joint swings 26 deg in total, 90 plus or minus 13. It was 6 deg
(87..93) while the bar was a see-saw, and that number had been copied into four
places - the firmware's power-on limits, Nong Studio's limits, COMMANDS.md and
the help page.

Four copies of one measurement is how a robot ends up clamped to a range its
mechanism no longer has: the firmware would stop the joint at 93 while Studio
drew it moving to 103, and the arm would simply stop short with nothing said.
The number cannot be read from one file at runtime - one copy is C++ compiled
into the board, one is browser JavaScript, two are prose - so the guard is that
they must MATCH, and this check is what makes them.

When the 4-bar's own measurements arrive (how far each shoulder rises, in mm),
they go in the rig setup, not here: this is the joint's travel, not the linkage
curve. See check_shrug_curve for that half.
"""
import re

import qc as F

AREA = "nong"
TITLE = "the shrug's 26 degrees are the same number in every place that states it"

NEUTRAL = 90


def run(t):
    head = (F.CODE / "firmware" / "config" /
            "esp32_hardware_nong_module.h").read_text(encoding="utf-8")
    lo = _last(head, "NONG_MIN_DEF")
    hi = _last(head, "NONG_MAX_DEF")
    if not t.ok(lo is not None and hi is not None,
                "the firmware states the shrug's limits",
                "NONG_MIN_DEF / NONG_MAX_DEF not found or not readable"):
        return

    span = hi - lo
    t.eq(span, 26, "the joint travels 26 degrees")
    t.eq(NEUTRAL - lo, 13, "13 degrees below neutral")
    t.eq(hi - NEUTRAL, 13, "and 13 above it")

    # ---- Nong Studio clamps to the same range -----------------------
    app = (F.CODE / "nong" / "main_python_set_nong" / "web" /
           "app.js").read_text(encoding="utf-8")
    t.eq(_js_last(app, "min"), lo,
         "Studio's lower limit is the firmware's lower limit")
    t.eq(_js_last(app, "max"), hi,
         "and its upper limit matches too")

    # ---- and the prose says the same thing --------------------------
    # Both documents are what a person reads before touching the robot. A doc
    # that still says 6 degrees is not a stale comment, it is an instruction to
    # expect the wrong movement.
    cmds = (F.CODE / "firmware" / "COMMANDS.md").read_text(encoding="utf-8")
    t.ok("%d–%d" % (lo, hi) in cmds or "%d-%d" % (lo, hi) in cmds,
         "COMMANDS.md quotes the real limits",
         "it still names an older range; the firmware says %d..%d" % (lo, hi))
    t.contains(cmds, "26°", "and the real travel")

    helpp = (F.CODE / "main_python" / "web" /
             "help.html").read_text(encoding="utf-8")
    i = helpp.find("<td>SHRUG</td>")
    row = helpp[i:i + 400] if i > 0 else ""
    t.ok("26°" in row,
         "the help page's joint table says 26 degrees",
         "the row still describes the see-saw's 6 degrees, which is the "
         "movement the robot no longer has")
    # A STANDALONE 6, not the 6 inside 26 - the first version of this check
    # failed on its own fix, which is a good reminder that a substring is not
    # a number.
    t.ok(not re.search(r"(?<!\d)6\s*°", row),
         "and does not still carry the old number as well",
         "two ranges in one sentence is worse than the wrong one alone")


def _last(text, name):
    """The last entry of a C array define — the shrug is joint 10 of 10."""
    m = re.search(re.escape(name) + r"\s+\{([^}]*)\}", text)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(",")]
    try:
        return int(parts[-1])
    except ValueError:
        return None


def _js_last(text, name):
    """The last entry of a JavaScript array literal `name: [...]`."""
    m = re.search(r"\b" + re.escape(name) + r":\s*\[([^\]]*)\]", text)
    if not m:
        return None
    try:
        return int(m.group(1).split(",")[-1].strip())
    except ValueError:
        return None
