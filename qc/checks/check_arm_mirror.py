"""A pose mirrors to the other arm, left/right or front/back.

User 2026-09-23 (A31-6) asked for *the move make can select the upper hand or
back hand*, read then as a front arm and a back arm on stage. User 2026-10-19
(A44-1) said that reading was wrong: it is the PALM or the BACK of each hand
on top (check_palm_side). The pinning went; the mirrors stay, because they
were wanted on their own.

Mirroring does NOT swap the two blocks of four joint numbers - the two arms
carry different invert flags, and that put the hand 613 mm out. So it is
measured here in WORLD SPACE: mirror a pose and the two hands must swap sides.
If the rig's mirroring ever changes, this fails instead of the puppet quietly
waving with the wrong shape.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a pose mirrors to the other arm, left/right and front/back"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK ARMM~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var a = Array(NJ).fill(90);
    // ---- mirroring, measured in WORLD SPACE ----------------------------
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

    // ---- FRONT/BACK is a different mirror, not the same one ------------
    // Measured in the BODY's own frame, so a turned waist cannot tilt it.
    // Each arm must stay on its own SIDE (x keeps its sign) and turn its
    // reach round (z flips). Left/right is the other way about.
    function local(b){
      return bodyGroup.worldToLocal(b.getWorldPosition(new THREE.Vector3()));
    }
    var q = Array(NJ).fill(90);
    q[0]=130; q[1]=120; q[2]=60; q[3]=105; q[8]=120;
    pose = q.slice(); applyPose(); robot.updateMatrixWorld(true);
    var l0 = local(wristBalls[0]), r0 = local(wristBalls[1]);
    var fb = mirrorPose(q, "fb");
    pose = fb.slice(); applyPose(); robot.updateMatrixWorld(true);
    var l1 = local(wristBalls[0]), r1 = local(wristBalls[1]);
    // same side: x keeps its sign and roughly its size
    var stayedSide = (Math.sign(l1.x) === Math.sign(l0.x)) &&
                     (Math.sign(r1.x) === Math.sign(r0.x));
    // reach turned round: z is the negative of what it was
    var zFlipL = Math.abs(l1.z + l0.z), zFlipR = Math.abs(r1.z + r0.z);
    var xKeptL = Math.abs(l1.x - l0.x);
    // and it is NOT the same answer the left/right mirror gives
    var lr = mirrorPose(q, "lr");
    var differs = fb.join(",") !== lr.join(",");

    report("mirrorL=" + dx.toFixed(2) + "~mirrorR=" + dx2.toFixed(2) +
           "~lw=" + [lw.x,lw.y,lw.z].map(n=>n.toFixed(0)).join("_") +
           "~rw=" + [rw.x,rw.y,rw.z].map(n=>n.toFixed(0)).join("_") +
           "~lw2=" + [lw2.x,lw2.y,lw2.z].map(n=>n.toFixed(0)).join("_") +
           "~rw2=" + [rw2.x,rw2.y,rw2.z].map(n=>n.toFixed(0)).join("_") +
           "~zeroL=" + RIG.zero.slice(0,4).join("_") + "~zeroR=" + RIG.zero.slice(4,8).join("_") +
           "~axL=" + RIG.axis.slice(0,4).join("_") + "~axR=" + RIG.axis.slice(4,8).join("_") +
           "~invL=" + RIG.invert.slice(0,4).join("_") + "~invR=" + RIG.invert.slice(4,8).join("_") +
           "~sameAsMirror=" + sameAsMirror +
           "~waistFlipped=" + waistFlipped +
           "~stayedSide=" + stayedSide + "~zFlipL=" + zFlipL.toFixed(1) +
           "~zFlipR=" + zFlipR.toFixed(1) + "~xKeptL=" + xKeptL.toFixed(1) +
           "~differs=" + differs);
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
    got = next((m for m in marks if m.startswith("mirrorL=")), "")
    if not t.ok(got, "the driver measured the arms", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    for key, label in (("mirrorL", "mirroring puts the left hand where the right one was"),
                       ("mirrorR", "and the right hand where the left one was")):
        t.ok(float(v.get(key) or 999) < 2.0,
             label + " (measured in world space, not assumed)",
             "%s mm off a perfect mirror - if the rig stops building the right "
             "arm as the left's mirror image, swapping joint numbers is no "
             "longer a mirror and this is where it shows. %s"
             % (v.get(key), got))
    t.ok(v.get("sameAsMirror") == "true",
         "the Pose tab's Mirror button takes the same mirror as the timeline's",
         "it used to swap the joint numbers itself, which is the 613 mm bug - "
         "one rule, one function, or the two buttons drift apart: %s" % v)
    t.ok(v.get("waistFlipped") == "true",
         "and the waist still turns to the other side",
         "reflecting about 90 is the rule mirrorLR always used and people have "
         "posed against it: %s" % v)

    # ---- the SECOND mirror (user 2026-09-23: "mirror front back") ---------
    t.ok(v.get("stayedSide") == "true",
         "front/back mirroring leaves each arm on its own side",
         "that is the whole difference from left/right: the gesture turns "
         "round, the arms do not swap. %s" % v)
    for key, label in (("zFlipL", "the left hand's reach turns front to back"),
                       ("zFlipR", "and the right hand's does too")):
        t.ok(float(v.get(key) or 999) < 12.0,
             label + " (measured in the body's own frame)",
             "%s mm away from the reflected position - a turned waist must not "
             "tilt this mirror, which is why it is measured in the body frame "
             "and not the world's: %s" % (v.get(key), v))
    t.ok(float(v.get("xKeptL") or 999) < 12.0,
         "and it does not drift sideways while doing it", v)
    t.ok(v.get("differs") == "true",
         "front/back and left/right really are two different mirrors",
         "if they gave the same answer one of the two buttons would be a lie: %s" % v)
