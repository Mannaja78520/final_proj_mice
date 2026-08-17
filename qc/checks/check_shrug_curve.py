"""SHRUG is a 4-bar linkage, and a 4-bar is not a see-saw.

One servo drives the linkage that lifts BOTH shoulders, so there is only ever
one angle to command. But the linkage does not give the two sides the same
movement, and the ratio changes across the travel. The preview rocked a single
rigid bar, so it always drew the two shoulders as exact mirror images — which
is not what the robot does. The ROBOT was right the whole time; the picture was
wrong, and that is a large part of "the robot and the web are not the same".

The fix is a measured curve: at a few SHRUG angles, how far each shoulder
actually rose, in mm. Measured beats computed here — the real linkage carries
horn spline offset, bearing slop and mounting error, none of which the CAD
knows about.

Two properties matter most and are checked in a real browser against the real
code:

  * with NO measurements, nothing changes — every rig saved before this keeps
    looking exactly as it did;
  * with measurements, the two shoulders move by DIFFERENT amounts, and the
    mount stops rocking so the rotation cannot be double-counted on top.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the shrug 4-bar moves each shoulder by its own measured amount"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK " + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];

    // Take the test angles FROM THE RIG, never hard-coded. SHRUG's neutral is
    // whatever the user tuned it to (theirs is 93, not 90), and its travel is
    // small. Hard-coding 93 as "a moved position" made this check assert that
    // the bar rocks while sitting exactly at rest — it failed the moment the
    // real rig was tuned, and blamed the code for it.
    var NEU = (RIG.neutral && RIG.neutral[9] != null) ? RIG.neutral[9] : 90;
    var HI  = Math.min(RIG.max[9], NEU + 8);
    var LO  = Math.max(RIG.min[9], NEU - 8);
    var MID = (NEU + HI) / 2;
    out.push("moved=" + (Math.abs(HI - NEU) >= 2 ? "yes" : "no"));

    // ---- 1. no measurements: the old symmetric rock, untouched ----------
    RIG.shrugCurve = [];
    pose[9] = HI; applyPose();
    out.push("uncal_rot=" + (Math.abs(shoulderMount.rotation.z) > 1e-6 ? "rocks" : "flat"));
    out.push("uncal_same=" + (shrugAnchors.L.position.y === shrugAnchors.R.position.y
                              ? "yes" : "no"));

    // ---- 2. measured: each side gets its own rise -----------------------
    RIG.shrugCurve = [{j:LO,l:-4,r:6.5},{j:NEU,l:0,r:0},{j:HI,l:5,r:-7.5}];
    pose[9] = HI; applyPose();
    var L = shrugAnchors.L.position.y, R = shrugAnchors.R.position.y;
    out.push("cal_rot=" + (Math.abs(shoulderMount.rotation.z) < 1e-9 ? "flat" : "rocks"));
    out.push("cal_diff=" + (Math.abs((L - R) - (5 - (-7.5))) < 0.01 ? "exact" : (L-R)));

    // ---- 3. between two points it interpolates -------------------------
    pose[9] = MID; applyPose();           // halfway from NEU to HI
    var half = shrugAnchors.L.position.y - shrugAnchors.R.position.y;
    out.push("mid=" + (Math.abs(half - (2.5 - (-3.75))) < 0.01 ? "linear" : half));

    // ---- 4. past the ends it holds, never extrapolates off ------------
    pose[9] = 1e4; applyPose();           // far past any limit
    var farL = shrugAnchors.L.position.y;
    pose[9] = HI; applyPose();
    out.push("clamp=" + (Math.abs(farL - shrugAnchors.L.position.y) < 1e-9 ? "held" : "ran-away"));
    // and the SAME at the bottom: below the first measurement it must hold at
    // that measurement, not carry on down past it
    pose[9] = -1e4; applyPose();
    var lowL = shrugAnchors.L.position.y;
    pose[9] = LO; applyPose();
    out.push("clamplow=" + (Math.abs(lowL - shrugAnchors.L.position.y) < 1e-9
                            ? "held" : "ran-away"));

    // ---- 5. one measurement is not a curve -----------------------------
    RIG.shrugCurve = [{j:NEU,l:3,r:-3}];
    pose[9] = HI; applyPose();
    out.push("single=" + (Math.abs(shoulderMount.rotation.z) > 1e-6 ? "falls-back" : "used"));

    // ---- 6. nothing renders as NaN -------------------------------------
    RIG.shrugCurve = [{j:NEU,l:0,r:0},{j:NEU,l:5,r:5}];  // two points, one angle
    pose[9] = NEU; applyPose();
    out.push("nan=" + (isFinite(shrugAnchors.L.position.y) &&
                       isFinite(shrugAnchors.R.position.y) ? "no" : "YES"));

    RIG.shrugCurve = [];
    report(out.join("~"));
  }catch(e){ report("ERR~" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = [m for m in fake_serial.qc_marks if "~" in m]
    if not t.ok(marks, "the shrug driver reported",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1].split("~") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the driver ran without throwing", got["ERR"])
        return

    t.eq(got.get("moved"), "yes",
         "the rig gives SHRUG enough travel to test with",
         )

    # nothing changes for a rig that has not been measured
    t.eq(got.get("uncal_rot"), "rocks",
         "with no measurements the preview still rocks the shoulder bar")
    t.eq(got.get("uncal_same"), "yes",
         "and both shoulders sit at the same height, exactly as before")

    # measured: the whole point
    t.eq(got.get("cal_diff"), "exact",
         "each shoulder is placed at its OWN measured rise")
    t.eq(got.get("cal_rot"), "flat",
         "and the bar stops rocking, so the rotation is not counted twice "
         "on top of the measurement")
    t.eq(got.get("mid"), "linear",
         "between two measurements it interpolates")
    t.eq(got.get("clamp"), "held",
         "beyond the last measurement it holds, instead of extrapolating the "
         "shoulder off into space")
    t.eq(got.get("clamplow"), "held",
         "and below the first measurement too — both ends, not just the top")
    t.eq(got.get("single"), "falls-back",
         "a single measurement is not a curve and is ignored")
    t.ok(got.get("nan") == "no",
         "two measurements at the same angle do not divide by zero",
         "a NaN here makes the whole robot vanish from the view")

    # the rig must carry it, or a measurement is lost on reload
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "r.shrugCurve",
               "the curve is migrated, so an older saved rig still loads")
    idx = (F.STUDIO / "web/index.html").read_text(encoding="utf-8", errors="replace")
    t.contains(idx, 'id="shrugCurve"',
               "and there is somewhere to type the measurements")
