"""Each joint starts where you chose, not at 90 — and Set zero does not undo it.

Asked 2026-09-10: *when start make can change position of servo when start not
only 90 can select own deg per joint*. Chosen shape: set it in Studio's Setup
tab, send it to the board, and let boot / `HOME` / the Neutral button all use it.

Most of this already existed. `neutral_[N]` was already per joint, already what
`begin()` drives the arm to and what `HOME` moves to, already in `CalBlob` and
already in the one declared-once field table. What was missing was any way to
CHANGE it and any way to READ it back — and one bug that made the whole feature
impossible:

**`SETZERO` used to write `neutral_[i] = 90.0f`.** So calibrating threw away
every chosen start angle, and silently: trim absorbs the offset, so the arm does
not move and nothing on screen changes. The loss only appeared on the next boot,
which is the hardest kind of bug to connect to its cause. It also trimmed against
a literal 90 instead of against this joint's own neutral, so with a non-90 start
pose the calibration was wrong by exactly that difference.

The other 90s in `NongModule.cpp` (`writeServos`, the servo maths) are the CENTRE
OF JOINT SPACE, not a start pose. This check must not push anyone into changing
those, so it asserts on `SETZERO`'s own body rather than on the file.

`fake_serial.NONG.neutral` is the witness: it is written by the fake module's own
handling of the line, so it says the angles reached the board — not that the page
believes it sent them.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "sendrig"
TITLE = "each joint starts where you chose, and Set zero keeps it"
SLOW = True

# Nothing is 90, and every value differs from its neighbours, so a check that
# reads one joint and fills the rest cannot pass.
WANT = [95, 85, 100, 80, 96, 84, 101, 79, 92, 88]

DRIVER = """
function step(){
  try{
    if (typeof pushLimits !== "function" || typeof neutralFromPose !== "function")
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    var WANT = %s;

    // ---- A: the Setup table really has a start angle per joint
    renderRigUI();
    // The servo/gear block below reuses .rigjrow, so only the first 11 rows are
    // the header plus the ten joints.
    var rows = document.querySelectorAll("#rigJoints .rigjrow");
    qcMark("Arows=" + rows.length);
    qcMark("Acols=" + rows[1].children.length);
    var hdr = [].map.call(rows[0].children, function(c){ return c.textContent; });
    qcMark("Ahdr=" + hdr.join("|"));

    // ---- B: typing a start angle is kept, and clamped into that joint's limits
    for (var i = 0; i < NJ; i++) { RIG.min[i] = 20; RIG.max[i] = 160; }
    renderRigUI();
    var box = document.querySelectorAll("#rigJoints .rigjrow")[1].children[2];
    box.value = 900;                    // far outside: a typed number bypasses max=
    box.onchange();
    qcMark("Bclamped=" + RIG.neutral[0]);
    for (var i = 0; i < NJ; i++) RIG.neutral[i] = WANT[i];

    // ---- C: send the rig — the start angles must reach the board
    qcMark("start");
    pushLimits().then(function(){
      qcMark("Csent=" + document.getElementById("limStat").textContent
        .replace(/[^A-Za-z0-9 ]/g, "").slice(0, 60).replace(/ /g, "_"));
      // Ask the BOARD what it now holds, here and not at the end: phase E
      // deliberately overwrites it, so the final state cannot answer for this.
      rawCmd("NEUTRAL?").then(function(r){
      qcMark("Cboard=" + String(r).replace(/[^0-9,.\\[\\]]/g, ""));

      // ---- D: read it back off the board into the rig
      for (var i = 0; i < NJ; i++) RIG.neutral[i] = 1;   // wipe, so a pull must fill it
      pullLimits().then(function(){
        qcMark("Dpulled=" + RIG.neutral.join(","));

        // ---- E: "Keep this as neutral" sends the pose as ONE line
        pose = pose.map(function(v, i){ return 70 + i; });
        rawCmd("MOVE QCMARK KEEP").then(function(){
          neutralFromPose().then(function(){
            qcMark("Ekept=" + RIG.neutral.join(","));
            qcMark("done");
          });
        });
      });
      });
    });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % ("[" + ",".join(str(v) for v in WANT) + "]")


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def _handler(src, verb):
    """The body of one `cmd == "VERB"` branch."""
    m = re.search(r'cmd == "%s"' % verb, src)
    if not m:
        return ""
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    return src[i:]


def run(t):
    src = (F.FIRMWARE / "src" / "modules" / "nong" / "NongModule.cpp").read_text(
        encoding="utf-8", errors="replace")

    # ---- the command exists, persists, and does not move the arm --------
    neu = _handler(src, "NEUTRAL")
    if t.ok(neu, "the board has a NEUTRAL command"):
        t.ok("saveCalSoon" in neu or "saveCal" in neu,
             "and it saves, so a start pose survives a power cycle")
        t.ok("clampJoint" in neu,
             "each angle is clamped into that joint's own limits",
             "a typed 900 would otherwise be written to the servo table")
        t.ok("startMove" not in neu,
             "setting where home IS does not send the arm there",
             "moving on NEUTRAL would swing the arm while somebody holds it")
        t.ok("forward(" in neu,
             "and it is forwarded, so a linked second board agrees")

    # ---- THE BUG: Set zero must not wipe the chosen start pose ----------
    sz = _handler(src, "SETZERO")
    if t.ok(sz, "SETZERO still exists"):
        t.ok(not re.search(r"neutral_\[i\]\s*=\s*90", sz),
             "SETZERO does NOT reset the start pose to 90",
             "it used to, and silently: trim hides it until the next boot")
        t.ok("neutral_[i]) * sPerJoint" in sz.replace("  ", " ") or
             re.search(r"cur_\[i\]\s*-\s*neutral_\[i\]", sz),
             "and it trims against this joint's own start angle, not a flat 90",
             "with a non-90 start pose the calibration is out by the difference")

    # ---- the board can be asked what it is set to -----------------------
    lim = _handler(src, "LIMIT")
    # The JSON is built as a C++ string, so the key appears escaped in the source.
    t.ok('\\"neutral\\"' in lim,
         "LIMIT? reports the start angles",
         "Studio cannot tell an angle that already matches from one that does not")
    st = src[src.index("void NongModule::status") if "void NongModule::status" in src
             else 0:]
    skip = re.search(r"strcmp\(key, \"joint_min\"\).*?continue;", st, re.S)
    if t.ok(skip, "the status JSON still skips the fields it renames"):
        t.ok("neutral" not in skip.group(0),
             "but no longer hides the start angles",
             "a setting somebody chose has to be visible on the page")

    # ---- JCFG carries it, appended ---------------------------------------
    jc = _handler(src, "JCFG")
    t.ok("argc >= 12" in jc,
         "JCFG accepts the start angle as an optional 12th token",
         "an older Studio must still work, and an older board must not break")
    t.ok("argv[11]" in jc, "and reads it from the LAST position")

    # ---- now drive it ----------------------------------------------------
    if not browser.available():
        t.give_up("headless Edge not found — the source half above still ran")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=26)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)

    t.ok(int(_mark(marks, "Arows") or 0) >= 11,
         "the Setup table has a header and all 10 joints",
         "got %s rows" % _mark(marks, "Arows"))
    t.eq(_mark(marks, "Acols"), "7",
         "and a joint row now has seven cells, the start angle among them")
    hdr = _mark(marks, "Ahdr") or ""
    t.contains(hdr, "start°", "and a start angle column, in plain words")
    t.eq(hdr.split("|")[2] if "|" in hdr else "", "start°",
         "sitting where the row actually puts it, third")

    t.eq(_mark(marks, "Bclamped"), "160",
         "a typed 900 is cut down to that joint's own maximum")

    # ---- what reached the board, read back FROM the board ----------------
    board = _mark(marks, "Cboard") or ""
    got = [int(float(v)) for v in re.findall(r"[\d.]+", board)]
    t.eq(got, WANT,
         "every joint's chosen start angle reached the board, and it says so")
    wire = [c for _, c in fake_serial.wire]
    carried = [c for c in wire
               if c.upper().startswith("JCFG") or c.upper().startswith("NEUTRAL")]
    t.ok(carried, "the start angles travelled as JCFG or NEUTRAL lines", wire[-4:])

    pulled = _mark(marks, "Dpulled") or ""
    t.eq(pulled, ",".join(str(v) for v in WANT),
         "and reading the board back fills the rig with them again")

    # ---- Keep this as neutral: one line, and the board agrees ------------
    kept = _mark(marks, "Ekept") or ""
    t.eq(kept, ",".join(str(70 + i) for i in range(10)),
         "Keep this as neutral takes the pose on screen")
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK KEEP")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    after = [c for c in wire[i + 1:] if c.upper().startswith("NEUTRAL")]
    t.eq(len(after), 1, "and sends it as ONE whole-pose line, not ten")
    if after:
        vals = [int(float(v)) for v in after[0].split()[1:]]
        t.eq(vals, [70 + i for i in range(10)],
             "carrying all ten angles the editor is showing")
    t.eq([int(float(v)) for v in fake_serial.NONG.neutral],
         [70 + i for i in range(10)],
         "so the board's start pose is what the editor last saved")
