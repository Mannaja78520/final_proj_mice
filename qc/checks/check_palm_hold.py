"""The palm or the back stays on top while a hand is dragged or typed to (A45-28).

User 2026-10-22: "เลือกได้ตอน drag หรือแก้ค่าด้วยจะได้เห็นว่าไปถึงไหนอย่างไร
แล้วกดเซฟท่าตามนั้นได้". Picking palm up / back up only after a pose was shaped
(A44-1) hid what the arm can really do there: a 4-joint arm has one spare
freedom (the elbow swinging round the shoulder-to-hand line), and joint limits
or the body cut it short on many reaches. So the side is now HELD while the
hand moves, and the Pose tab shows live what the arm reaches.

What is checked, through the real handlers:
- picking "back on top" turns the arm at once, the hand stays put;
- a real pointer drag of the wrist ball (window pointermove/pointerup) keeps
  the back on top at every step, and the hand follows the pointer;
- a typed wrist position (gotoXyz) keeps it too;
- an out-of-reach typed position says how many mm short, and draws the mark;
- "Save as a new move" stores the pose on screen, and that is what PLAYS
  (playKeys) and what reached the module on the wire while the link was on;
- the safe search never picks a shape that hits the body when the start did not.
The drag search is a +-dragRangeDeg window (hand_side.json) so the elbow does
not flip to the far side mid-pull; the whole swing is searched on release.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "palm or back kept on top while a hand is dragged or typed to, with the reached pose shown and saved"
SLOW = True

DRIVER = """
function report(s){
  if (typeof rawCmd === "function") rawCmd("MOVE QCMARK HOLD~" + s);
  else qcMark("HOLD~" + s);
}
function hand(arm){ robot.updateMatrixWorld(true); return wristBalls[arm].getWorldPosition(new THREE.Vector3()); }
function screenOf(v){
  var r = renderer.domElement.getBoundingClientRect();
  var n = v.clone().project(activeCam());
  return { x: r.left + (n.x + 1) / 2 * r.width, y: r.top + (1 - n.y) / 2 * r.height };
}
function ev(type, s){ window.dispatchEvent(new PointerEvent(type, { clientX: s.x, clientY: s.y, bubbles: true })); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof setHold === "function" && typeof palmMarks !== "undefined"
           && palmMarks.length === 2 && document.getElementById("handHold0")
           && document.getElementById("liveChk")
           && typeof haveUsb === "function" && haveUsb();
  }, 20000).then(function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try{
    // A start, a pull direction and a typed point where the arm left FREE
    // loses the back of the left hand on top but holding it keeps it - found
    // from the rig (joint values are never hardcoded: the rig is user data).
    // Without such a case a broken hold would pass unseen.
    var seed = 7, t00 = performance.now();
    function rnd(){ seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    var DIRS = [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];
    function simPull(P0, dir, keep){
      pose = P0.slice(); applyPose();
      var st = hand(0), w = 1;
      for (var s = 1; s <= 6; s++) {
        solveIK(0, st.clone().addScaledVector(dir, 10 * s), 16);
        if (keep) holdSide(0, false);
        applyPose(); w = Math.min(w, -palmUpness(0));
      }
      return w;
    }
    function typed(P0, at, keep){
      pose = P0.slice(); applyPose(); handHold[0] = keep;
      document.getElementById("tgtLx").value = Math.round(at.x);
      document.getElementById("tgtLy").value = Math.round(at.y);
      document.getElementById("tgtLz").value = Math.round(at.z);
      gotoXyz(0); handHold[0] = 0;
      return -palmUpness(0);
    }
    var P = null, DIR = null, AT = null, typedFree = 1;
    handHold[0] = -1;
    for (var n = 0; n < 60 && !P; n++) {
      var p = pose.slice();
      for (var i = 0; i < 4; i++)
        p[i] = Math.round(RIG.min[i] + rnd() * (RIG.max[i] - RIG.min[i]));
      if (collisionAt(p)) continue;
      var b = facePalm(p, 0, -1, { safe: true });
      if (b.upness > -0.8) continue;
      for (var d = 0; d < DIRS.length && !P; d++) {
        var dir = new THREE.Vector3(DIRS[d][0], DIRS[d][1], DIRS[d][2]);
        if (simPull(b.pose, dir, false) > 0.5) continue;      // free keeps it anyway
        if (simPull(b.pose, dir, true) < 0.6) continue;       // the arm cannot keep it
        pose = b.pose.slice();
        var at = fkPoints(pose).wrL.addScaledVector(dir, 60);
        typedFree = typed(b.pose, at, 0);
        if (typedFree > 0.5 || typed(b.pose, at, -1) < 0.6) continue;
        P = b.pose; DIR = dir; AT = at;
      }
    }
    var searchMs = Math.round(performance.now() - t00);
    handHold[0] = 0;
    if (!P) { report("ERR-no-reach-in-this-rig-where-holding-matters"); report("done"); return; }

    // 1. the picker: back on top at once, hand kept
    pose = facePalm(P, 0, 1).pose; poseChanged(false);
    var h0 = hand(0);
    var sel = document.getElementById("handHold0");
    sel.value = "-1"; sel.dispatchEvent(new Event("change"));
    var pickU = palmUpness(0), pickMoved = hand(0).distanceTo(h0);

    // 2. a real drag of the wrist ball (window pointermove/up), live link on
    document.getElementById("liveChk").checked = true;
    pose = P.slice(); poseChanged(false);
    rawCmd("MOVE QCMARK HOLDDRAG");
    var start = hand(0), dir = DIR;
    // a plane the pull lies in
    var nrm = Math.abs(dir.z) > 0.5 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 0, 1);
    function pull(measure){
      drag = { kind: "ik", arm: 0, normal: nrm, planePoint: start.clone() };
      controls.enabled = false;
      var off = 0;
      for (var s = 1; s <= 6; s++) {
        var tgt = start.clone().addScaledVector(dir, 10 * s);
        var t0 = performance.now();
        ev("pointermove", screenOf(tgt));
        frameMs = Math.max(frameMs, performance.now() - t0);
        var hitp = planeHit(drag.planePoint, drag.normal);
        if (measure) worst = Math.min(worst, -palmUpness(0));
        if (hitp) off = Math.max(off, hand(0).distanceTo(hitp));
      }
      ev("pointerup", screenOf(tgt));
      return off;
    }
    var worst = 1, frameMs = 0;
    handHold[0] = 0;
    var followFree = pull(false);
    pose = P.slice(); poseChanged(false); handHold[0] = -1;
    var follow = pull(true);
    var dragU = palmUpness(0), dropped = drag === null;
    var dragPose = pose.map(fmtA).join(" ");

    setTimeout(function(){
      document.getElementById("liveChk").checked = false;
      // 3. the same point typed in, from the same start: back still on top
      pose = P.slice(); poseChanged(false);
      document.getElementById("tgtLx").value = Math.round(AT.x);
      document.getElementById("tgtLy").value = Math.round(AT.y);
      document.getElementById("tgtLz").value = Math.round(AT.z);
      gotoXyz(0);
      var typedU = palmUpness(0);
      var typedText = document.getElementById("handReach0").textContent;

      // 4. far out of reach: the gap is said, the mark is drawn
      document.getElementById("tgtLx").value = 5000;
      gotoXyz(0); poseChanged(false);
      var farText = document.getElementById("handReach0").textContent;
      var farMark = !!(reachMarks[0] && reachMarks[0].ball.visible);
      // a joint slider moved by hand clears the stale target
      pose[1] = clampJ(1, pose[1] + (pose[1] > RIG.min[1] + 3 ? -3 : 3)); poseChanged(false);
      var clearedText = document.getElementById("handReach0").textContent;
      var clearedMark = !!(reachMarks[0] && reachMarks[0].ball.visible);

      // 5. save as a new move: the pose on screen is what plays
      keys = [{ pose: P.slice(), t: 80, hold: 0 }]; selKey = 0; bumpKeys(); renderTimeline();
      var shown = pose.slice();
      document.getElementById("handSaveNew").click();
      var played = playKeys()[playKeys().length - 1].pose;
      var same = played.length === shown.length && played.every(function(v, j){ return Math.abs(v - shown[j]) < 1e-9; });
      var said = document.getElementById("tlStat").textContent;

      // 6. reaches where the plain search turns the arm INTO the body: the
      // safe one must not (a clear start, so there is something to keep)
      var badSafe = 0, tried = 0, t6 = performance.now();
      for (var m = 0; m < 300 && tried < 3 && performance.now() - t6 < 15000; m++) {
        var q = pose.slice();
        for (var i2 = 0; i2 < 8; i2++)
          q[i2] = Math.round(RIG.min[i2] + rnd() * (RIG.max[i2] - RIG.min[i2]));
        if (collisionAt(q)) continue;
        var arm = m % 2, want = m % 4 < 2 ? 1 : -1;
        if (!collisionAt(facePalm(q, arm, want).pose)) continue;
        tried++;
        var r = facePalm(q, arm, want, { safe: true });
        if (collisionAt(r.pose)) badSafe++;
      }
      setHold(0, 0);

      report("pickU=" + pickU.toFixed(2) + "~pickMoved=" + pickMoved.toFixed(1) +
             "~worst=" + worst.toFixed(2) + "~follow=" + follow.toFixed(1) +
             "~followFree=" + followFree.toFixed(1) +
             "~frameMs=" + Math.round(frameMs) + "~dragU=" + dragU.toFixed(2) +
             "~dropped=" + dropped + "~dragPose=" + dragPose.replace(/ /g, "_") +
             "~typedU=" + typedU.toFixed(2) +
             "~typedText=" + typedText.replace(/[ ~]/g, "_") +
             "~farText=" + farText.replace(/[ ~]/g, "_") + "~farMark=" + farMark +
             "~clearedText=" + clearedText.replace(/[ ~]/g, "_") + "~clearedMark=" + clearedMark +
             "~same=" + same + "~said=" + said.replace(/[ ~]/g, "_") +
             "~tried=" + tried + "~badSafe=" + badSafe + "~typedFree=" + typedFree.toFixed(2) +
             "~searchMs=" + searchMs + "~safeMs=" + Math.round(performance.now() - t6));
      setTimeout(function(){ report("done"); }, 300);
    }, 900);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); report("done"); }
}); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=90)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("HOLD~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("pickU=")), "")
    if not t.ok(got, "the driver measured the hand", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.ok(float(v["pickU"]) < -0.5, "picking 'back on top' turns the back up at once", v)
    t.ok(float(v["pickMoved"]) < 5.0, "and the hand stays where it was (%s mm)" % v["pickMoved"], v)
    t.ok(float(v["worst"]) > 0.5,
         "dragging the hand keeps the back on top at every step (worst %s)" % v["worst"], v)
    # keeping a side may cost reach (a joint at its stop), but only a little
    t.ok(float(v["follow"]) < float(v["followFree"]) + 6.0,
         "and the hand follows the pointer (%s mm off at worst, %s with nothing kept)"
         % (v["follow"], v["followFree"]), v)
    t.ok(float(v["dragU"]) < -0.5 and v["dropped"] == "true",
         "after letting go the back is still on top", v)
    # generous: catches a search that walks the whole swing every frame
    t.ok(int(v["frameMs"]) < 1500, "one drag step takes %s ms" % v["frameMs"], v)
    t.ok(float(v["typedU"]) < -0.5,
         "a typed wrist position keeps the back on top too (free: %s)" % v["typedFree"], v)
    t.ok("reached" in v["typedText"] or "short" in v["typedText"],
         "the readout says how close the hand got", v["typedText"])
    t.ok(re.search(r"\d+_mm_short", v["farText"]) is not None and v["farMark"] == "true",
         "out of reach: the gap in mm is said and the orange mark is drawn", v)
    t.ok("short" not in v["clearedText"] and v["clearedMark"] == "false",
         "moving a joint another way drops the old target and its mark", v)
    t.ok(v["same"] == "true", "Save as a new move stores exactly the pose shown, and it plays", v)
    t.ok("exactly_the_pose_shown" in v["said"], "and the line says so", v["said"])
    t.ok(int(v["tried"]) >= 1 and v["badSafe"] == "0",
         "the safe search never picks a shape that hits the body (%s/%s)"
         % (v["badSafe"], v["tried"]), v)

    # what reached the module during the drag, not what the page thinks
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK HOLDDRAG")
    except ValueError:
        t.ok(False, "the drag marker reached the module", wire[-4:])
        return
    poses = [c for c in wire[i + 1:] if c.upper().startswith("POSE ")]
    if t.ok(poses, "the drag sent poses to the robot", wire[i + 1:][:4]):
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", poses[-1].split(" T ")[0])]
        want = [float(x) for x in v["dragPose"].split("_")]
        t.ok(len(nums) == len(want) and all(abs(a - b) < 0.11 for a, b in zip(nums, want)),
             "and the last one is the pose the drag ended on, back on top",
             "wire %r, shown %r" % (poses[-1], want))
