// --- keep the palm or the back on top while a hand moves (A45-28) ---
// User 2026-10-22: picking palm up / back up after the fact hid what the arm
// can really do there, so the choice now holds WHILE you drag a hand or type
// where a wrist goes, and the Pose tab shows live what the arm reaches: the
// gap to where you pulled, how far the palm is from straight up, which joints
// sit at their stop, and whether it hits itself. What is shown is the joint
// angles the robot gets, so saving keeps exactly that. Settings are DATA in
// hand_side.json beside this page; the story is in qc/checks/check_palm_hold.py.
let HOLD = {
  dragRangeDeg: 30,   // while dragging: look this far round each way, no further
  stepDeg: 5,
  reachMm: 4,         // a gap this small counts as "the hand got there"
  stopDeg: 0.5,       // this close to a joint limit counts as "at its stop"
  avoidSelfHit: true, // never turn the arm into a shape that hits the body
};
fetch("hand_side.json").then(r => r.json()).then(j => {
  Object.keys(HOLD).forEach(k => { if (k in j) HOLD[k] = j[k]; });
}).catch(() => {});        // no file: the built-in values above

const handHold = HANDS.map(() => 0);     // per hand: 0 free, 1 palm on top, -1 back
const reachAsk = HANDS.map(() => null);  // per hand: { target (world), joints } last asked for
const reachMarks = [];                   // per hand: the asked-for point and a line to the hand

const armJoints = (arm) => arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
const armKey = (arm) => armJoints(arm).map(j => pose[j].toFixed(2)).join(",");

// Turn the arm to the held side, hand kept in place. full = the whole swing
// (a button, a typed position, the end of a drag); otherwise only near the
// shape it has, so a drag never flips the elbow to the far side mid-pull.
function holdSide(arm, full) {
  const want = handHold[arm];
  if (!want) return;
  const r = facePalm(pose, arm, want, full ? { safe: HOLD.avoidSelfHit }
    : { range: HOLD.dragRangeDeg, step: HOLD.stepDeg, safe: HOLD.avoidSelfHit });
  if (r) { pose = r.pose; applyPose(); }  // facePalm redraws the pose it was given
}
// Remember where this hand was asked to go (world space), for the gap readout
// and the 3D mark. It goes stale the moment that arm's joints change any other way.
function askReach(arm, target) {
  reachAsk[arm] = { target: target.clone(), joints: armKey(arm) };
  drawReach(arm);
}
function drawReach(arm) {
  if (!reachMarks[arm]) {
    const ball = new THREE.Mesh(new THREE.SphereGeometry(9, 12, 8),
      new THREE.MeshBasicMaterial({ color: 0xff9f1c, wireframe: true }));
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(
      [new THREE.Vector3(), new THREE.Vector3()]),
      new THREE.LineBasicMaterial({ color: 0xff9f1c }));
    scene.add(ball, line);
    reachMarks[arm] = { ball, line };
  }
  const m = reachMarks[arm], a = reachAsk[arm];
  const gap = reachGap(arm);
  m.ball.visible = m.line.visible = gap !== null && gap > HOLD.reachMm;
  if (!m.ball.visible) return;
  m.ball.position.copy(a.target);
  m.line.geometry.setFromPoints([a.target, wristPos(arm)]);
}
// mm between where the hand was asked to go and where it is; null = nothing asked
function reachGap(arm) {
  const a = reachAsk[arm];
  if (!a || !wristBalls[arm]) return null;
  if (a.joints !== armKey(arm)) { reachAsk[arm] = null; return null; }
  robot.updateMatrixWorld(true);
  return a.target.distanceTo(wristPos(arm));
}
// One plain line per hand: which side is on top and by how much, the gap,
// the joints at their stop, a self-hit. Built from the pose the robot gets.
function reachText(arm) {
  const up = palmUpness(arm), want = handHold[arm] || (up >= 0 ? 1 : -1);
  const off = Math.round(THREE.MathUtils.radToDeg(Math.acos(Math.max(-1, Math.min(1, want * up)))));
  const side = want > 0 ? "palm" : "back of the hand";
  const out = [off <= 60 ? side + " on top, " + off + "° from straight up"
                         : "on its edge — the " + side + " is " + off + "° from straight up"];
  const gap = reachGap(arm);
  if (gap !== null) out.push(gap <= HOLD.reachMm ? "reached where you put it"
    : Math.round(gap) + " mm short of where you put it (the orange mark)");
  const stops = armJoints(arm).filter(j => pose[j] <= RIG.min[j] + HOLD.stopDeg
                                         || pose[j] >= RIG.max[j] - HOLD.stopDeg);
  if (stops.length) out.push("at its stop: " + stops.map(j => JOINT_LABELS[j]).join(", "));
  const hit = collisionAt(pose);
  if (hit) out.push("⚠ " + hit);
  return out.join(" · ");
}
function renderReach() {
  HANDS.forEach((h, i) => {
    const el = $("handReach" + i);
    if (el) el.textContent = reachText(i);
    drawReach(i);
  });
}
function setHold(arm, want) {
  handHold[arm] = want;
  if (!want) return;
  holdSide(arm, true);
  poseChanged(false);
}
// Save the pose on screen: these are the joint angles the robot is sent, so the
// move plays exactly what you see, gap and all.
function saveShownPose(asNew) {
  if (asNew) addKey(); else if (keys[selKey]) updateKey(); else return;
  $("tlStat").textContent = (asNew ? "added as move " : "saved into move ") + selKey
    + " — exactly the pose shown, which is what the arm will do";
}
