"""A move can be given to the front or the back arm, and mirrored to the other.

User 2026-09-23, choosing between three readings of *the move make can select
the upper hand or back hand*: **front arm / back arm on stage** - the nong has a
near arm and a far arm as the audience sees it; a move picks which arm plays it,
so the same move can be mirrored.

Three things have to be true, and only the third is obvious:

  * a move pinned to one arm leaves the OTHER arm exactly where the move before
    it left it. Asserted on playKeys(), which is what buildYaml and
    hubShowSteps both read - assert on the keyframe and you have asserted on
    the editor's opinion of itself, not on what the robot gets;
  * which arm is "front" is a rig setting, not a constant. Turning the nong
    round changes which physical joints a pinned move drives, with nothing
    re-typed;
  * mirroring swaps the two blocks of four joint numbers, with no sign
    arithmetic - because the renderer already builds the right arm as the
    left's mirror image (BASE_DIR). That is an ASSUMPTION about the rig, so it
    is measured here in WORLD SPACE: mirror a pose and the two hands must swap
    sides. If the rig's mirroring ever changes, this fails instead of the
    puppet quietly waving with the wrong shape.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a move plays on the front or back arm, and mirrors to the other"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK ARMM~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    RIG.frontArm = "L";
    var a = Array(NJ).fill(90);
    // keyframe 1 moves BOTH arms, keyframe 2 is pinned to the front arm only
    var b = Array(NJ).fill(90); for (var i = 0; i < 8; i++) b[i] = 120;
    var c = Array(NJ).fill(90); for (var i = 0; i < 8; i++) c[i] = 60;
    keys = [{pose: a.slice(), t: 80, hold: 0},
            {pose: b.slice(), t: 500, hold: 0},
            {pose: c.slice(), t: 500, hold: 0, arm: "front"}];
    selKey = 0;
    bumpKeys();
    var K = playKeys();
    // front = L = joints 0..3, so 4..7 must still be keyframe 1's 120
    var frontTook = K[2].pose.slice(0, 4).join(",");
    var backHeld = K[2].pose.slice(4, 8).join(",");
    // the keyframe itself is untouched: pinning is a PLAYING rule, not an edit
    var keyIntact = keys[2].pose.slice(4, 8).join(",");

    // turn the nong round: "front" is now the RIGHT arm, nothing re-typed
    RIG.frontArm = "R";
    bumpKeys();
    K = playKeys();
    var flippedTook = K[2].pose.slice(4, 8).join(",");
    var flippedHeld = K[2].pose.slice(0, 4).join(",");

    // ---- mirroring, measured in WORLD SPACE ----------------------------
    RIG.frontArm = "L";
    var m = Array(NJ).fill(90);
    m[0] = 130; m[1] = 120; m[2] = 60; m[3] = 105;
    keys = [{pose: a.slice(), t: 80, hold: 0}, {pose: m.slice(), t: 500, hold: 0}];
    selKey = 1; pose = m.slice(); applyPose();
    var lw = wristBalls[0].getWorldPosition(new THREE.Vector3());
    var rw = wristBalls[1].getWorldPosition(new THREE.Vector3());
    mirrorKeyArms(1);
    pose = keys[1].pose.slice(); applyPose();
    var lw2 = wristBalls[0].getWorldPosition(new THREE.Vector3());
    var rw2 = wristBalls[1].getWorldPosition(new THREE.Vector3());
    // the LEFT hand must now stand where the RIGHT one did, mirrored in X
    var dx = Math.abs(lw2.x + rw.x) + Math.abs(lw2.y - rw.y) + Math.abs(lw2.z - rw.z);
    var dx2 = Math.abs(rw2.x + lw.x) + Math.abs(rw2.y - lw.y) + Math.abs(rw2.z - lw.z);
    // mirroring a PINNED move flips which arm holds it too
    keys[1].arm = "front";
    mirrorKeyArms(1);
    var flippedPin = keys[1].arm;

    // The Pose tab's own Mirror button must take the SAME mirror. It used to
    // swap the joint numbers itself, which is the 613 mm bug - one rule, one
    // function, or the two buttons drift apart.
    var start = Array(NJ).fill(90);
    start[0] = 130; start[1] = 120; start[2] = 60; start[3] = 105; start[8] = 120;
    pose = start.slice();
    var viaPose = mirrorPose(pose);
    pose = start.slice();
    mirrorLR();
    var sameAsMirror = pose.join(",") === viaPose.join(",");
    var waistFlipped = Math.round(pose[8]) === 60;

    report("frontTook=" + frontTook + "~backHeld=" + backHeld +
           "~keyIntact=" + keyIntact +
           "~flippedTook=" + flippedTook + "~flippedHeld=" + flippedHeld +
           "~mirrorL=" + dx.toFixed(2) + "~mirrorR=" + dx2.toFixed(2) +
           "~lw=" + [lw.x,lw.y,lw.z].map(n=>n.toFixed(0)).join("_") +
           "~rw=" + [rw.x,rw.y,rw.z].map(n=>n.toFixed(0)).join("_") +
           "~lw2=" + [lw2.x,lw2.y,lw2.z].map(n=>n.toFixed(0)).join("_") +
           "~rw2=" + [rw2.x,rw2.y,rw2.z].map(n=>n.toFixed(0)).join("_") +
           "~zeroL=" + RIG.zero.slice(0,4).join("_") + "~zeroR=" + RIG.zero.slice(4,8).join("_") +
           "~axL=" + RIG.axis.slice(0,4).join("_") + "~axR=" + RIG.axis.slice(4,8).join("_") +
           "~invL=" + RIG.invert.slice(0,4).join("_") + "~invR=" + RIG.invert.slice(4,8).join("_") +
           "~flippedPin=" + flippedPin + "~sameAsMirror=" + sameAsMirror +
           "~waistFlipped=" + waistFlipped);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("ARMM~")]
    got = next((m for m in marks if m.startswith("frontTook=")), "")
    if not t.ok(got, "the driver measured the arms", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.eq(v.get("frontTook"), "60,60,60,60",
         "a move pinned to the front arm drives the front arm's four joints")
    t.eq(v.get("backHeld"), "120,120,120,120",
         "and the back arm holds exactly where the move before it left it")
    t.eq(v.get("keyIntact"), "60,60,60,60",
         "the keyframe itself is untouched - pinning is a playing rule, not an edit")
    t.eq(v.get("flippedTook"), "60,60,60,60",
         "turning the nong round makes the same move drive the other arm")
    t.eq(v.get("flippedHeld"), "120,120,120,120",
         "and the arm that is now at the back holds still instead")
    for key, label in (("mirrorL", "mirroring puts the left hand where the right one was"),
                       ("mirrorR", "and the right hand where the left one was")):
        t.ok(float(v.get(key) or 999) < 2.0,
             label + " (measured in world space, not assumed)",
             "%s mm off a perfect mirror - if the rig stops building the right "
             "arm as the left's mirror image, swapping joint numbers is no "
             "longer a mirror and this is where it shows. %s"
             % (v.get(key), got))
    t.eq(v.get("flippedPin"), "back",
         "mirroring a pinned move flips the pin, so the held arm is still the far one")
    t.ok(v.get("sameAsMirror") == "true",
         "the Pose tab's Mirror button takes the same mirror as the timeline's",
         "it used to swap the joint numbers itself, which is the 613 mm bug - "
         "one rule, one function, or the two buttons drift apart: %s" % v)
    t.ok(v.get("waistFlipped") == "true",
         "and the waist still turns to the other side",
         "reflecting about 90 is the rule mirrorLR always used and people have "
         "posed against it: %s" % v)
