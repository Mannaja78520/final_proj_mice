"""Each hand can show its palm or its back on top (A44-1).

User 2026-10-19: hand-like parts are fixed to the forearms, and whether the
audience sees the palm or the back on top changes the feeling of a move and of
the end pose - so it must be settable per hand. It replaces A31-6's "front arm
/ back arm" picker, which was a misreading of the same wish.

The arm has no wrist twist. Four joints, three numbers for where the hand is:
the one left over swings the elbow round the shoulder-to-hand line, and that
rolls the hand. facePalm() walks that swing and keeps the shape that shows the
asked-for side most nearly on top, WITHOUT moving the hand. Joint limits cap
it, so some reaches cannot turn far - the check picks a reach that can, from
the rig itself (joint values are never hardcoded: the rig is user data).

Asserted where it matters: the turned pose is what reaches the module on the
wire (Pose tab, live link) and what the timeline plays (playKeys(), which the
file and the hub both read); the drawn hand is turned by the Setup button.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "each hand shows its palm or its back on top, with the hand kept in place"
SLOW = True

DRIVER = """
function report(s){
  if (typeof rawCmd === "function") rawCmd("MOVE QCMARK PALM~" + s);
  else qcMark("PALM~" + s);
}
function hand(arm){ return wristBalls[arm].getWorldPosition(new THREE.Vector3()); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof facePalm === "function" && typeof palmMarks !== "undefined"
           && palmMarks.length === 2 && document.getElementById("liveChk")
           && typeof haveUsb === "function" && haveUsb();
  }, 20000).then(function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try{
    // A reach where the left hand can show either side, found from the rig.
    var seed = 11, P = null, up = null, back = null;
    function rnd(){ seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    for (var n = 0; n < 60 && !P; n++) {
      var p = pose.slice();
      for (var i = 0; i < 4; i++)
        p[i] = Math.round(RIG.min[i] + rnd() * (RIG.max[i] - RIG.min[i]));
      var a = facePalm(p, 0, 1), b = facePalm(p, 0, -1);
      if (a.upness > 0.5 && b.upness < -0.5) { P = p; up = a; back = b; }
    }
    if (!P) { report("ERR-no-reach-in-this-rig-turns-both-ways"); report("done"); return; }
    pose = P.slice(); applyPose(); var h0 = hand(0);
    pose = up.pose.slice(); applyPose(); var hUp = hand(0);
    pose = back.pose.slice(); applyPose(); var hBack = hand(0);
    var rightKept = up.pose.slice(4).join(",") === P.slice(4).join(",");

    // Pose tab, live link on: the turned pose is what goes to the module
    document.getElementById("liveChk").checked = true;
    pose = P.slice(); poseChanged(false);
    setTimeout(function(){
      rawCmd("MOVE QCMARK PALMSENT");
      turnPalm(0, -1);
      var sent = pose.map(fmtA).join(" ");
      var shown = (document.getElementById("handNow0") || {}).textContent || "";
      setTimeout(function(){
        document.getElementById("liveChk").checked = false;
        // the timeline: pick "palm up" on a move, and the PLAYED move turns
        keys = [{pose: pose.slice(), t: 80, hold: 0}, {pose: P.slice(), t: 600, hold: 0}];
        selKey = 0; bumpKeys(); renderTimeline();
        turnKeyPalm(1, 0, 1);
        var played = playKeys()[1].pose;
        var playedUp = palmUpnessOf(played, 0);
        var pick = document.querySelectorAll(".kpalm");
        var picked = pick.length > 2 ? pick[2].value : "missing";   // move 1, left hand

        // Setup: turning the drawn hand half round puts the other side on top
        var before = palmUpnessOf(up.pose, 0);
        RIG.palmTurn[0] = (RIG.palmTurn[0] + 180) % 360; rigChanged();
        var after = palmUpnessOf(up.pose, 0);
        RIG.palmTurn[0] = (RIG.palmTurn[0] + 180) % 360; rigChanged();

        report("upU=" + up.upness.toFixed(2) + "~backU=" + back.upness.toFixed(2) +
               "~movedUp=" + hUp.distanceTo(h0).toFixed(1) +
               "~movedBack=" + hBack.distanceTo(h0).toFixed(1) +
               "~rightKept=" + rightKept + "~sent=" + sent.replace(/ /g, "_") +
               "~shown=" + shown.replace(/[ ~]/g, "_") +
               "~playedUp=" + playedUp.toFixed(2) + "~picked=" + picked +
               "~before=" + before.toFixed(2) + "~after=" + after.toFixed(2));
        setTimeout(function(){ report("done"); }, 300);
      }, 900);
    }, 500);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); report("done"); }
}); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("PALM~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("upU=")), "")
    if not t.ok(got, "the driver measured the hands", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.ok(float(v["upU"]) > 0.5, "palm up puts the palm on top", v)
    t.ok(float(v["backU"]) < -0.5, "back up puts the back of the hand on top", v)
    for key, label in (("movedUp", "turning to the palm leaves the hand where it was"),
                       ("movedBack", "and so does turning to the back")):
        t.ok(float(v[key]) < 5.0, label + " (%s mm)" % v[key],
             "the hand is the thing being placed; only the arm's shape may change: %s" % v)
    t.ok(v["rightKept"] == "true", "the other arm is not touched", v)
    t.ok(v["shown"].startswith("now:_back"), "the Pose tab says the back is on top", v)

    # what reached the module after the button, not what the page thinks
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK PALMSENT")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    poses = [c for c in wire[i + 1:] if c.upper().startswith("POSE ")]
    if t.ok(poses, "turning the hand sent the new pose to the robot", wire[i + 1:][:4]):
        got_nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", poses[-1].split(" T ")[0])]
        want = [float(x) for x in v["sent"].split("_")]
        t.ok(len(got_nums) == len(want) and
             all(abs(a - b) < 0.11 for a, b in zip(got_nums, want)),
             "and it is the turned pose", "wire %r, turned %r" % (poses[-1], want))

    t.ok(float(v["playedUp"]) > 0.5,
         "a move set to palm up PLAYS with the palm up (what the file and hub read)", v)
    t.eq(v["picked"], "palm", "and its picker says so")
    t.ok(float(v["before"]) * float(v["after"]) < 0 and
         abs(float(v["before"]) + float(v["after"])) < 0.1,
         "Setup's turn of the drawn hand puts the other side on top", v)

    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.ok("front arm (" not in app and "frontArmSide" not in app,
         "the front arm / back arm picker is gone (the user did not want it)",
         "A31-6's picker is still in app.js")
