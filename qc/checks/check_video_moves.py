"""Moves made from a video of a person copy the person's arms (A44-4).

User 2026-10-19: make the robot's moves from a video of a person, taking the
person's skeleton and getting the robot as close as its joints allow. Studio
finds the skeleton with MediaPipe Pose in the browser; that part needs a real
video and the internet, so this check hands movesFromFrames() the skeleton
itself, in MediaPipe's own shape (33 world points, metres, x right in the
picture, y down, z away from the camera), and measures the ROBOT afterwards.

What is held, each measured in the body's own frame on the drawn rig (never
joint numbers: the rig is user data and the arms are not mirror images):

* an arm pointing out to the person's side, forward, or hanging down puts the
  robot's upper arm and forearm the same way - the person's own left drives
  the robot's left, and "Move like a mirror" swaps them;
* a person standing turned to the camera drives the arms the same as one
  facing it (the frame turns with the shoulder line); "Turn the waist" turns
  the robot's body the SAME way the person turned;
* frames where an arm is not seen are filled from the nearest seen one;
* a slow raise of one arm is thinned to a few moves at its turning points,
  with the video's own timing pinned, and "Close" keeps more moves than
  "Smooth" - every move eases to a stop, so fewer is smoother;
* the per-hand palm / back choice (A44-1) is applied to the made moves;
* "Use as new moves" puts them on the time bar, and the YAML the robot plays
  carries every one with its T.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "moves made from a video skeleton copy the person's arms"
SLOW = True

DRIVER = """
function report(s){ qcMark("VID~" + s); }
// A person in MediaPipe's world shape. Body frame: x their left, y up, z their
// front. yaw = how far they are turned toward their own left, in degrees.
function person(L, R, yaw, seeL){
  var w = []; for (var i = 0; i < 33; i++) w.push({x:0, y:0, z:0, v:1});
  var c = Math.cos(yaw * Math.PI / 180), s = Math.sin(yaw * Math.PI / 180);
  function put(i, p, v){   // body -> camera (y up, z toward) -> MediaPipe
    var x = p[0] * c + p[2] * s, z = -p[0] * s + p[2] * c;
    w[i] = {x: x, y: -p[1], z: -z, v: v == null ? 1 : v};
  }
  function n(d){ var l = Math.hypot(d[0], d[1], d[2]); return [d[0]/l, d[1]/l, d[2]/l]; }
  [[11, 13, 15, L, 1, seeL], [12, 14, 16, R, -1, 1]].forEach(function(a){
    var sh = [0.18 * a[4], 0.45, 0], u = n(a[3][0]), f = n(a[3][1]);
    var el = [sh[0] + u[0]*0.28, sh[1] + u[1]*0.28, sh[2] + u[2]*0.28];
    var wr = [el[0] + f[0]*0.25, el[1] + f[1]*0.25, el[2] + f[2]*0.25];
    put(a[0], sh); put(a[1], el, a[5]); put(a[2], wr, a[5]);
  });
  put(23, [0.1, 0, 0]); put(24, [-0.1, 0, 0]);
  return w;
}
function still(L, R, yaw, n){ var f = []; for (var i = 0; i < (n || 6); i++) f.push({t: i / 10, w: person(L, R, yaw || 0)}); return f; }
var OUT = [[1,0,0],[1,0,0]], FWD = [[0,0,1],[0,0,1]], DOWN = [[0,-1,0],[0,-1,0]];
var ROUT = [[-1,0,0],[-1,0,0]];
var BASE = {tol: 8, mirror: false, waist: false, hand: [0, 0], force: [false, false], music: false};
function opt(o){ var r = {}; for (var k in BASE) r[k] = BASE[k]; for (var k in o) r[k] = o[k]; return r; }
// angle (deg) between where a robot bone points and where it should, body frame
function bones(p, arm){
  var keep = pose; pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
  function L(o){ return bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3())); }
  var S = L(jointGroups[arm ? 4 : 0]), E = L(elbowBalls[arm]), H = L(wristBalls[arm]);
  var d = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.quaternion);
  pose = keep; applyPose();
  return {u: E.clone().sub(S).normalize(), f: H.clone().sub(E).normalize(), yaw: Math.atan2(d.x, d.z) * 180 / Math.PI};
}
function off(p, arm, want){
  var b = bones(p, arm), u = new THREE.Vector3().fromArray(want[0]).normalize(),
      f = new THREE.Vector3().fromArray(want[1]).normalize();
  return Math.max(b.u.angleTo(u), b.f.angleTo(f)) * 180 / Math.PI;
}
function last(r){ return r.keys[r.keys.length - 1].pose; }
// The robot's own bone directions in a pose, as a person's arms: whatever the
// rig is, a person built from them is a shape the robot can surely make.
function shapeOf(p){ var l = bones(p, 0), r = bones(p, 1);
  return [[l.u.toArray(), l.f.toArray()], [r.u.toArray(), r.f.toArray()]]; }
function flip(sh){ function m(v){ return [-v[0], v[1], v[2]]; }
  return [[m(sh[1][0]), m(sh[1][1])], [m(sh[0][0]), m(sh[0][1])]]; }
var seed = 7;
function rnd(){ seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
function randomPose(){
  // Kinematic imitation is measured only on physically clear target shapes.
  // Random joint angles can now correctly collide with a hand or joint ball.
  for (var attempt = 0; attempt < 300; attempt++) {
    var p = RIG.neutral.slice();
    for (var i = 0; i < 8; i++) p[i] = Math.round(RIG.min[i] + rnd() * (RIG.max[i] - RIG.min[i]));
    if (!collisionAt(p)) return p;
  }
  throw new Error('no collision-clear reference pose');
}
function worst(p, sh){ return Math.max(off(p, 0, sh[0]), off(p, 1, sh[1])); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof movesFromFrames === "function" && typeof elbowBalls !== "undefined"
           && elbowBalls.length === 2 && document.getElementById("vidDetail");
  }, 20000).then(function(ready){
  if (!ready) { report("ERR-the-app-never-finished-loading"); report("done"); return; }
  try{
    var o = {copy: 0, mirror: 0, turned: 0, waistArm: 0}, t0 = performance.now();
    // 1-4 on shapes the rig itself makes, so a joint limit never decides it
    for (var n = 0; n < 6; n++) {
      var sh = shapeOf(randomPose());
      var r = movesFromFrames(still(sh[0], sh[1]), BASE);
      o.copy = Math.max(o.copy, worst(last(r), sh));
      // as a mirror: the person's sides swap and the picture flips
      r = movesFromFrames(still(flip(sh)[0], flip(sh)[1]), opt({mirror: true}));
      o.mirror = Math.max(o.mirror, worst(last(r), sh));
      // turned to the camera: the same arms as facing it
      r = movesFromFrames(still(sh[0], sh[1], 35), BASE);
      o.turned = Math.max(o.turned, worst(last(r), sh));
      var w = last(movesFromFrames(still(sh[0], sh[1], 35), opt({waist: true})));
      o.waistArm = Math.max(o.waistArm, worst(w, sh));
      o.waistYaw = bones(w, 0).yaw.toFixed(1);
    }
    ["copy", "mirror", "turned", "waistArm"].forEach(function(k){ o[k] = o[k].toFixed(1); });
    // the person's own left drives the robot's left: their left arm out, right down
    var r = movesFromFrames(still(OUT, DOWN), BASE);
    o.outL = off(last(r), 0, OUT).toFixed(1); o.downR = off(last(r), 1, DOWN).toFixed(1);
    // 5. left arm unseen in the first frames: filled from the first seen one
    var f5 = still(OUT, DOWN, 0, 8);
    for (var i = 0; i < 4; i++) f5[i].w = person(DOWN, DOWN, 0, 0.1);
    r = movesFromFrames(f5, BASE);
    o.filled = off(r.keys[0].pose, 0, OUT).toFixed(1);
    // 6. one gesture there and back over 4 s at 10 frames/s, between two shapes
    // the rig makes, eased like a person moves (not a straight line in time)
    var A = randomPose(), B = randomPose(), f6 = [];
    for (var i = 0; i <= 40; i++) {
      var e = (1 - Math.cos(2 * Math.PI * i / 40)) / 2;
      var sh6 = shapeOf(A.map(function(v, j){ return v + (B[j] - v) * e; }));
      f6.push({t: i / 10, w: person(sh6[0], sh6[1], 0)});
    }
    var sm = movesFromFrames(f6, opt({tol: 14})), cl = movesFromFrames(f6, opt({tol: 4}));
    o.smooth = sm.keys.length; o.close = cl.keys.length; o.videoMs = sm.videoMs;
    o.pinned = sm.keys.slice(1).every(function(k){ return k.tset; });
    o.spanMs = sm.keys.slice(1).reduce(function(s, k){ return s + k.t + (k.hold || 0); }, sm.keys[0].hold || 0);
    // 7. hand choice, on a reach where the rig can show the left hand either way
    var hp = null;
    for (var n = 0; n < 80 && !hp; n++) {
      var p = randomPose(), a = facePalm(p, 0, 1), b = facePalm(p, 0, -1);
      if (a.upness > 0.6 && b.upness < -0.6 && !collisionAt(a.pose) && !collisionAt(b.pose)) hp = p;
    }
    if (hp) {
      var hs = shapeOf(hp);
      o.palmUp = palmUpnessOf(last(movesFromFrames(still(hs[0], hs[1]), opt({hand: [1, 0]}))), 0).toFixed(2);
      o.backUp = palmUpnessOf(last(movesFromFrames(still(hs[0], hs[1]), opt({hand: [-1, 0]}))), 0).toFixed(2);
      o.goodNote = vidHandNote(movesFromFrames(still(hs[0], hs[1]), opt({hand: [1, 0]}))).length;
      // a back that DID turn is not a miss (upness is -1 for the back on top)
      o.backMiss = movesFromFrames(still(hs[0], hs[1]), opt({hand: [-1, 0]})).handMiss[0];
    } else { o.palmUp = "none"; o.backUp = "none"; }
    // a straight arm cannot roll its hand: the made moves must say so, not stay silent
    document.getElementById("vidHand0").value = "palm";
    var st = movesFromFrames(still(OUT, DOWN), opt({hand: [1, 0]}));
    o.straightMiss = st.handMiss[0];
    o.straightNote = /left hand could not show its palm/.test(vidHandNote(st));
    // 9. forced: the same straight arm shows its palm, the hand moving as little as it can
    var fo = movesFromFrames(still(OUT, DOWN), opt({hand: [1, 0], force: [true, false]}));
    o.forceUp = palmUpnessOf(last(fo), 0).toFixed(2); o.forceMiss = fo.handMiss[0];
    o.forceMoved = (function(){ var keep = pose;
      function H(p){ pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
        return wristBalls[0].getWorldPosition(new THREE.Vector3()); }
      var d = H(last(st)).distanceTo(H(last(fo))); pose = keep; applyPose(); return d; })().toFixed(0);
    document.getElementById("vidHand0").value = "video";
    // 10. a person faster than the servos: B and A swapped every 0.1 s. With
    // the music the cap is only the servos' own max (A48-23), so the swap has
    // to beat THAT: 0.2 s fitted a 400 deg/s servo and nothing was cut.
    var f10 = [], P = randomPose(), Q = randomPose();
    for (var i = 0; i <= 40; i++) { var sh10 = shapeOf(i % 4 < 2 ? P : Q); f10.push({t: i / 20, w: person(sh10[0], sh10[1], 0)}); }
    // timed at the pace the FILE will play at (music = PACE MUSIC on the board)
    function slow(r){ var p = planPace(r.keys); return r.keys.slice(1).filter(function(k, j){ return minTime(r.keys[j].pose, k.pose, p) > k.t + 1; }).length; }
    function span(r){ var p = planPace(r.keys); return r.keys.slice(1).reduce(function(s, k){ return s + Math.max(k.t, minTime(r.keys[r.keys.indexOf(k) - 1].pose, k.pose, p)) + k.hold; }, r.keys[0].hold); }
    var mu = movesFromFrames(f10, opt({tol: 4, music: true})), st10 = movesFromFrames(f10, opt({tol: 4, music: false}));
    o.musicSlow = slow(mu); o.musicPartial = mu.partial; o.musicSpan = span(mu); o.music0Span = span(st10); o.fastVideo = mu.videoMs;
    // 10b. music cuts a move short: the forced side must hold on the cut pose,
    // and the miss count must match the poses on the bar (PC 2026-10-19)
    // On a clip where every forced move shows the back by itself, but a plain
    // joint blend toward one does not (found by trying swaps; the PC's
    // jumping jacks were one).
    var BF = opt({tol: 4, music: true, hand: [-1, -1], force: [true, true]}), hard = null;
    var tFind = performance.now();
    for (var n = 0; n < 40 && !hard; n++) {
      var P1 = randomPose(), Q1 = randomPose(), fr = [];
      for (var i = 0; i <= 12; i++) { var s1 = shapeOf(i % 4 < 2 ? P1 : Q1); fr.push({t: i / 10, w: person(s1[0], s1[1], 0)}); }
      var hf = vidFitFrames(fr, BF), prv = null, at0 = 0, cut = false, bad = false;
      vidPicksFor(hf, 4).forEach(function(pk){
        if (bad) return;
        var sd = vidSide(hf.poses[pk.i], pk, BF), sp = sd.pose;
        bad = sd.miss[0] || sd.miss[1];
        if (prv && !cut) {
          var q = vidReachIn(prv, sp, hf.times[pk.i] - at0);
          cut = q !== sp && (palmUpnessOf(q, 0) > -0.5 || palmUpnessOf(q, 1) > -0.5);
        }
        prv = sp; at0 = hf.times[pk.i];
      });
      if (cut && !bad) hard = fr;
      o.hardTries = n + 1;
    }
    o.hard = !!hard;
    o.findMs = Math.round(performance.now() - tFind); t0 += o.findMs;   // the test's own search is not fitting
    var t10 = performance.now();
    var bf = movesFromFrames(hard || f10, BF);
    o.cutMs = (performance.now() - t10).toFixed(0); o.cutPartial = bf.partial; o.cutSlow = slow(bf);
    o.cutBad = [0, 1].map(function(a){ return bf.keys.filter(function(k){ return -palmUpnessOf(k.pose, a) <= 0.5; }).length; }).join("/");
    o.cutMiss = bf.handMiss.join("/");
    o.cutWorst = Math.max.apply(null, bf.keys.map(function(k){ return Math.max(palmUpnessOf(k.pose, 0), palmUpnessOf(k.pose, 1)); })).toFixed(2);
    // the left palm up, back forced, 0.1 s to turn it: whatever comes back,
    // what it says about the hand must be what the pose shows
    o.honest = "no reach";
    if (hp) { var up = facePalm(hp, 0, 1).pose, lies = 0, FB = opt({hand: [-1, 0], force: [true, false], music: true});
      for (var n = 0; n < 5; n++) { var rs = vidReachSide(up, randomPose(), 100, {use: "keep"}, FB);
        if (rs.miss[0] !== (-palmUpnessOf(rs.pose, 0) <= 0.5)) lies++; }
      o.honest = lies + " of 5 wrong"; }
    // 11. leave a move out, fill another with a different moment: later moves keep their time
    var fit = vidFitFrames(f6, BASE), picks = vidPicksFor(fit, 4);
    var whole = vidBuild(fit, picks, opt({})).keys.length;
    picks[1].use = "drop"; picks[2].use = "moment"; picks[2].at = fit.times[picks[2].i + 3] || fit.times[fit.times.length - 2];
    var cut = vidBuild(fit, picks, opt({}));
    o.dropped = whole - cut.keys.length;
    var clock = cut.keys.slice(1, 2).reduce(function(s, k){ return s + k.t; }, cut.keys[0].hold);
    o.slotKept = Math.abs(cut.keys[1].sourceMs - fit.times[picks[2].i]) < 2 && Math.abs(clock - VideoRigFitter.clockForSource(cut.keys, fit.times[picks[2].i]).ms) < 2;
    o.momentPose = cut.keys[1].pose.join(" ") === vidPoseAt(fit, picks[2].at).join(" ");
    vidFrames = f6; vidFit = fit; vidPicks = picks; vidList();
    o.rows = document.querySelectorAll("#vidList .vidrow").length; o.picks = picks.length;
    o.ms = Math.round(performance.now() - t0);
    // 8. onto the time bar, and into the file the robot plays
    vidMade = cl;
    markSaved(workSig(), "", 0);     // nothing unsaved, so no "save first?" question
    vidUse("replace").then(function(){
      o.onBar = keys.length; o.made = cl.keys.length;
      var y = buildYaml().yaml;
      o.yamlPoses = (y.match(/- pose: "[^"]*T \\d+"/g) || []).length;
      o.detail = document.getElementById("vidDetail").options.length;
      o.hand0 = document.getElementById("vidHand0").options.length;
      report(Object.keys(o).map(function(k){ return k + "=" + o[k]; }).join("~"));
      report("done");
    }).catch(function(e){ report("ERR-use-" + String(e && e.stack || e).slice(0,160).replace(/~/g, "_")); report("done"); });
  }catch(e){ report("ERR-" + String(e && e.stack || e).slice(0,160).replace(/~/g, "_")); report("done"); }
}); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=60)
    marks = [m[4:] for m in fake_serial.qc_marks if m.startswith("VID~")]
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    got = next((m for m in marks if m.startswith("copy=")), "")
    if not t.ok(got, "the driver measured the robot", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))
    print("   measured:", v)
    near = 6.0      # degrees between a robot bone and the person's, body frame
    for key, label in (("copy", "the robot's arms point the way the person's do"),
                       ("mirror", "as a mirror, the person's left drives the robot's right"),
                       ("turned", "a person turned to the camera drives the arms as if facing it"),
                       ("waistArm", "with Turn the waist on, the arms still point the person's way")):
        t.ok(float(v[key]) < near, label + " (worst of 6 shapes %s deg off)" % v[key], v)
    t.ok(float(v["waistYaw"]) > 15, "Turn the waist turns the body the way the person turned "
         "(%s deg, person 35)" % v["waistYaw"], v)
    t.ok(float(v["outL"]) < near and float(v["downR"]) < near,
         "the person's own left arm out moves the robot's LEFT arm out", v)
    t.ok(float(v["filled"]) < near, "an arm not seen at first takes its first seen shape", v)
    t.ok(3 <= int(v["smooth"]) <= 6, "a gesture there and back is thinned to a few moves "
         "(%s from 41 frames)" % v["smooth"], v)
    t.ok(int(v["close"]) > int(v["smooth"]), "Close keeps more moves than Smooth", v)
    t.ok(v["pinned"] == "true", "the video's timing is pinned, so Show speed does not re-time it", v)
    t.ok(abs(int(v["spanMs"]) - int(v["videoMs"])) <= 120,
         "and the moves span the video's own length (%s ms of %s)" % (v["spanMs"], v["videoMs"]), v)

    if t.ok(v["palmUp"] != "none", "the rig has a reach where the left hand turns both ways", v):
        t.ok(float(v["palmUp"]) > 0.5, "palm on top is applied to the made moves", v)
        t.ok(float(v["backUp"]) < -0.5, "and back of the hand on top too", v)
        t.ok(v["goodNote"] == "0", "a hand that did turn adds no warning", v)
    if v["palmUp"] != "none":
        t.ok(v["backMiss"] == "0", "a back that did turn is not counted as a hand that could not", v)
    t.ok(float(v["forceUp"]) > 0.5 and v["forceMiss"] == "0",
         "palm on top, always: the straight arm shows its palm after all", v)
    t.ok(0 < int(v["forceMoved"]) < 200, "with the hand moved only as far as needed (%s mm)" % v["forceMoved"], v)
    t.ok(v["musicSlow"] == "0" and int(v["musicPartial"]) > 0,
         "Stay with the music: no move needs longer than its moment in the video; "
         "the too-fast ones go part of the way", v)
    t.ok(abs(int(v["musicSpan"]) - int(v["fastVideo"])) <= 50,
         "so the moves end with the video (%s ms of %s)" % (v["musicSpan"], v["fastVideo"]), v)
    t.ok(int(v["music0Span"]) > int(v["fastVideo"]) + 200,
         "without it the same moves run longer than the video (%s ms)" % v["music0Span"], v)
    t.ok(v["honest"] == "0 of 5 wrong", "a move that cannot keep the side in its time says so (%s)" % v["honest"], v)
    t.ok(v["hard"] == "true", "found a clip where a plain part-way move loses the hand side "
         "(%s tries)" % v["hardTries"], v)
    t.ok(int(v["cutPartial"]) > 0 and v["cutSlow"] == "0",
         "back forced with the music on: moves still go part of the way to keep time "
         "(%s part-way)" % v["cutPartial"], v)
    t.ok(v["cutBad"] == "0/0" and v["cutMiss"] == "0/0",
         "and every move on the bar shows the back on top, both hands (not on top L/R: "
         "%s, said %s, worst upness %s, %s ms)" % (v["cutBad"], v["cutMiss"], v["cutWorst"], v["cutMs"]), v)
    t.ok(v["dropped"] == "1", "a move left out is gone from the moves", v)
    t.ok(v["slotKept"] == "true", "and the move after it still lands on its own moment", v)
    t.ok(v["momentPose"] == "true", "a move filled from another moment takes that moment's pose", v)
    t.ok(v["rows"] == v["picks"], "the list shows one row per made move", v)
    t.ok(int(v["straightMiss"]) > 0 and v["straightNote"] == "true",
         "a straight arm that cannot show the palm is said in words, not left silent", v)

    t.ok(int(v["onBar"]) == int(v["made"]), "Use as new moves puts every one on the time bar", v)
    t.ok(int(v["yamlPoses"]) == int(v["made"]),
         "and the file the robot plays carries each with its time", v)
    t.ok(int(v["detail"]) >= 2 and int(v["hand0"]) >= 2,
         "the choices are filled from their lists", v)
    t.ok(int(v["ms"]) < 30000, "fitting stays quick (%s ms for all of the above)" % v["ms"], v)

    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.ok(re.search(r"tasks-vision@\d+\.\d+\.\d+\b", app) is not None,
         "the body finder is pinned to one exact version", "VID_LIB must name a version")
