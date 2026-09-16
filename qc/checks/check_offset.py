"""One joint can be nudged a few degrees, without re-zeroing the other nine.

Asked 2026-09-10: *make can set offset to servo because sometime i set it not
exact 0 or 90*. A servo horn only refits in whole teeth — about 14 deg of shaft —
so a joint lands a few degrees out however carefully it is built.

The correction already existed as `trim_`, but there was no way to reach it. The
ONLY writer was `SETZERO`, which takes all ten joints from the current pose and
sits behind a password: to fix one elbow you had to re-jog the whole robot and
re-zero everything, and could easily make the other nine worse. Nothing showed
the value either — `status()` skips `trim`.

Three things this pins down, each of which was a decision that could have gone
the other way and would be invisible if it silently regressed:

* **The unit.** `trim` is stored in SERVO degrees, added after the gear
  multiplication. The command and the box on screen take JOINT degrees, because
  that is what a person can see on the arm — so the same typed number moves a
  15:18 shoulder and a 1:1 waist by the same visible amount. The scaling is
  `servoPerJoint()`, shared with SETZERO so the two cannot disagree about which
  way up the ratio goes.
* **No invert special case, on purpose.** `trim` is added BEFORE the invert
  (`NongMath::jointToServoDeg`), so it passes through the mirror exactly as the
  joint term does: +1 deg of offset moves the arm the way +1 deg of joint angle
  would, inverted or not. If someone ever moves `trim` to after the invert, every
  plus button on the page silently starts working backwards — so that ordering is
  asserted here rather than left as a comment.
* **The arm must move.** Seeing the correction is the whole point, which is what
  separates OFFSET from SETZERO, where the arm deliberately stays put.

And one thing that is not a decision but a trap: `pushLimits()` sends a JCFG
batch and then does `continue`, skipping that joint's individual commands
entirely. A line put in `parts` would therefore never be sent to any board that
understands JCFG. The offset rides in `always`, which is sent either way.

`fake_serial.NONG.offset` is the witness — it is written by the fake module's own
handling of the line, so it says the number reached the board.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "sendrig"
TITLE = "one joint can be nudged without re-zeroing the rest"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof sendOffset !== "function" || typeof renderOffsets !== "function")
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);

    // ---- A: the card really draws a row per joint, with the controls on it
    renderRigUI();
    var rows = document.querySelectorAll("#trimUI .trow-t");
    qcMark("Arows=" + rows.length);
    var r0 = rows[0];
    qcMark("Abtns=" + r0.querySelectorAll("button").length);
    qcMark("Ainput=" + (r0.querySelector("input.t-val") ? "yes" : "no"));

    // ---- B: pressing + twice moves that ONE joint, and leaves the rest alone
    rawCmd("MOVE QCMARK NUDGE").then(function(){
      var plus = r0.querySelectorAll("button")[1];   // label, -, [input], +, 0
      plus.click();
      setTimeout(function(){
        plus.click();
        setTimeout(function(){
          qcMark("Bvalue=" + RIG.offset[0]);
          qcMark("Brest=" + RIG.offset.slice(1).join(","));

          // ---- C: typing a wild number is cut down, not sent as typed.
          // Marked, so phase B's two presses can be read on their own: this
          // phase sends an OFFSET line too, and it was being counted as a third.
          rawCmd("MOVE QCMARK CLAMP").then(function(){
          var box = document.querySelectorAll("#trimUI .trow-t")[2]
                      .querySelector("input.t-val");
          box.value = 900;
          box.onchange();
          setTimeout(function(){
            qcMark("Cclamped=" + RIG.offset[2]);

            // ---- D: send rig must carry the offset even on a board that
            // understands JCFG, where the per-joint lines are skipped
            RIG.offset[5] = -2.5;
            rawCmd("MOVE QCMARK SENDRIG").then(function(){
              pushLimits().then(function(){

                // ---- E: read it back off the board
                RIG.offset = RIG.offset.map(function(){ return 0; });
                pullOffsets().then(function(){
                  qcMark("Epulled=" + RIG.offset.join(","));

                  // ---- F: Clear all really clears the board too
                  clearOffsets().then(function(){
                    qcMark("Fcleared=" + RIG.offset.join(","));
                    qcMark("done");
                  });
                });
              });
            });
          }, 350);
          });
        }, 350);
      }, 350);
    });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def _tok(line, n):
    """Token n of a command line, or "" — a check that CRASHES on a short line
    reports nothing about the nine assertions after it, which is worse than a
    plain failure."""
    parts = (line or "").split()
    return parts[n] if len(parts) > n else ""


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
    hdr = (F.FIRMWARE / "src" / "modules" / "nong" / "NongModule.h").read_text(
        encoding="utf-8", errors="replace")
    math = (F.FIRMWARE / "src" / "modules" / "nong" / "NongMath.h").read_text(
        encoding="utf-8", errors="replace")

    # ---- the command ----------------------------------------------------
    off = _handler(src, "OFFSET")
    if t.ok(off, "the board has an OFFSET command"):
        # The WRITE, named exactly. A loose `"servoPerJoint" in off` passed with
        # the multiply deleted, because the OFFSET? branch below divides by it —
        # the same name, doing the opposite job, two lines away.
        t.ok(re.search(r"trim_\[i\]\s*=\s*d\s*\*\s*servoPerJoint\(i\)", off),
             "the typed angle is scaled INTO servo degrees when it is stored",
             "writing the typed number straight into trim_ moves a geared "
             "shoulder by the wrong amount")
        t.ok(re.search(r"trim_\[i\]\s*/\s*servoPerJoint\(i\)", off),
             "and scaled back OUT when it is reported, so the two are inverse")
        t.ok("writeServos" in off,
             "and the arm MOVES, which is how you aim it",
             "without this you nudge blind: SETZERO is the one that stays put")
        t.ok("saveCalSoon" in off or "saveCal" in off,
             "the correction survives a power cycle")
        t.ok("jointrule::offset" in off,
             "and a wild value is refused by the shared rule",
             "an unbounded offset drives the servo into its end stop and stalls it")

    # ---- ONE ratio, not two ---------------------------------------------
    t.ok("servoPerJoint" in hdr, "the ratio has one home")
    sz = _handler(src, "SETZERO")
    t.ok("servoPerJoint" in sz,
         "SETZERO uses that same one",
         "two copies of a ratio is two chances to get it upside down")
    t.ok(not re.search(r"gearGear_\[i\]\s*/\s*\(float\)gearPinion_", sz),
         "and no longer computes its own")

    # ---- the ordering the whole no-special-case argument rests on --------
    m = re.search(r"inline float jointToServoDeg.*?\n\}", math, re.S)
    if t.ok(m, "the joint-to-servo formula is where it was"):
        body = m.group(0)
        t.ok("invert" not in body,
             "trim is applied BEFORE the invert, so an inverted joint needs no "
             "special case",
             "move trim after the invert and every + button silently reverses")
    inv = re.search(r"inline int servoDegToUs.*?\n\}", math, re.S)
    if inv:
        t.ok("invert" in inv.group(0),
             "the invert still happens later, in servo space")

    # ---- the trap in send rig -------------------------------------------
    app = (F.CODE / "nong" / "main_python_set_nong" / "web" / "app.js").read_text(
        encoding="utf-8", errors="replace")
    push = app[app.index("async function pushLimits()"):]
    push = push[:push.index("async function pullLimits()")]
    t.ok("always" in push,
         "send rig has a path for lines the JCFG batch cannot carry",
         "the batch path does `continue`, so anything left in parts is dropped "
         "on every board that understands JCFG")
    t.ok(re.search(r"for \(const c of job\.always\)", push),
         "and it really sends them")
    t.ok(push.index("job.always") < push.index("if (useBatch"),
         "before the batch, so a refused batch cannot skip them too")

    # ---- now drive it ----------------------------------------------------
    if not browser.available():
        t.give_up("headless Edge not found — the source half above still ran")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)

    t.eq(_mark(marks, "Arows"), "10", "there is a row for every joint")
    t.eq(_mark(marks, "Abtns"), "3", "each row has minus, plus and a clear button")
    t.eq(_mark(marks, "Ainput"), "yes", "and a box you can type into")

    # ---- one joint moved, the others did not ----------------------------
    t.eq(_mark(marks, "Bvalue"), "1", "two presses of + is one degree")
    t.eq(_mark(marks, "Brest"), ",".join(["0"] * 9),
         "and the other nine joints were left alone",
         )
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK NUDGE")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    clamp = wire.index("MOVE QCMARK CLAMP") if "MOVE QCMARK CLAMP" in wire else len(wire)
    j = wire.index("MOVE QCMARK SENDRIG") if "MOVE QCMARK SENDRIG" in wire else len(wire)
    nudges = [c for c in wire[i + 1:clamp] if c.upper().startswith("OFFSET ")]
    t.eq(len(nudges), 2, "each press reached the board on its own, two presses two lines")
    t.ok(all(_tok(c, 1) == "1" for c in nudges),
         "and every one named joint 1, never a broadcast", nudges[:3])
    t.eq(_tok(nudges[-1] if nudges else "", 2), "1",
         "the last press sent the value the page is showing")

    t.eq(_mark(marks, "Cclamped"), "30",
         "a typed 900 is cut to the 30 deg the board would accept")

    # ---- send rig carried it, past the JCFG batch ------------------------
    after = [c for c in wire[j + 1:] if c.upper().startswith("OFFSET ")]
    t.ok(any(_tok(c, 1) == "6" and _tok(c, 2) == "-2.5" for c in after),
         "send rig delivered joint 6's offset even though JCFG ran for it",
         after[:4] or "nothing after the marker: the batch swallowed it")

    # The board itself is the witness, read at the time — the final state cannot
    # answer for this, because Clear all deliberately wipes it two phases later.
    pulled = _mark(marks, "Epulled") or ""
    t.contains(pulled, "-2.5",
               "the board really holds it, and reading it back fills the page")

    t.eq(_mark(marks, "Fcleared"), ",".join(["0"] * 10),
         "Clear all zeroes every joint on the page")
    t.eq([float(v) for v in fake_serial.NONG.offset], [0.0] * 10,
         "and on the board")
