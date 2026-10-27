// --- collisions ---
// Self-collision check: arms vs torso box, head sphere, and each other.
// Bodies are capsules along the arm segments (radii from the built-in
// shapes) with a small safety margin. Checked for every keyframe AND along
// the interpolated path between keyframes (collisions often happen mid-move).
const CLEAR = 4;         // safety margin (mm)
const R_ARM = 14, R_WRIST = 16, R_HEAD = 46;

function distToBox(p, hx, hy, hz) { // 0 = inside the torso box
  const dx = Math.max(Math.abs(p.x) - hx, 0);
  const dy = Math.max(Math.abs(p.y) - hy, 0);
  const dz = Math.max(Math.abs(p.z) - hz, 0);
  return Math.hypot(dx, dy, dz);
}
function segPoint(a, b, t) {
  return new THREE.Vector3(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t);
}
function segSegDist(p1, q1, p2, q2) { // closest distance between two segments
  const d1 = q1.clone().sub(p1), d2 = q2.clone().sub(p2), r = p1.clone().sub(p2);
  const a = d1.dot(d1), e = d2.dot(d2), f = d2.dot(r);
  let s, t;
  if (a <= 1e-8 && e <= 1e-8) return r.length();
  if (a <= 1e-8) { s = 0; t = Math.min(1, Math.max(0, f / e)); }
  else {
    const c = d1.dot(r);
    if (e <= 1e-8) { t = 0; s = Math.min(1, Math.max(0, -c / a)); }
    else {
      const b = d1.dot(d2), den = a * e - b * b;
      s = den > 1e-8 ? Math.min(1, Math.max(0, (b * f - c * e) / den)) : 0;
      t = (b * s + f) / e;
      if (t < 0) { t = 0; s = Math.min(1, Math.max(0, -c / a)); }
      else if (t > 1) { t = 1; s = Math.min(1, Math.max(0, (b - c) / a)); }
    }
  }
  return segPoint(p1, q1, s).sub(segPoint(p2, q2, t)).length();
}

// world positions of the arm joints for a given pose (rig restored after)
function fkPoints(p) {
  const saved = pose;
  // arm positions for the XYZ readout + collision are taken in the BODY frame:
  // hold WAIST + SHRUG at neutral so a rigid body yaw (which turns the torso
  // AND the arms together) never changes arm-vs-torso clearance or the readout.
  pose = p.slice();
  pose[8] = RIG.zero[8]; pose[9] = RIG.zero[9];
  applyPose();
  robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const out = {
    shL: W(jointGroups[0].parent), elL: W(jointGroups[2].parent), wrL: W(wristBalls[0]),
    shR: W(jointGroups[4].parent), elR: W(jointGroups[6].parent), wrR: W(wristBalls[1]),
  };
  pose = saved;
  applyPose();
  return out;
}

// returns null (safe) or a short reason string
function collisionAt(p) {
  return StudioCollisionGeometry.hit(p);
}

function clearBadMarks() { keys.forEach(k => delete k.bad); }

// checks every keyframe + the path between them; marks bad keyframes RED
// ---- may a movement that crashes reach the robot? -----------------------
//
// One place decides, for every route to the arm: Play, Run on robot, and
// upload. It used to be inconsistent AND wrong. Run and upload were blocked
// outright with no way past, so a check that was wrong about your rig left you
// stuck; and Play said "the 3D preview will play so you can see where" while
// hubPlay() and the live sends drove the real arm anyway.
//
// Preview can show a refused move, but the robot cannot bypass this gate.
// Match the model and clothing gap in Setup before asking for another route.
let crashForced = false;
let previewOnly = false;   // this run draws, but does not drive the arm

function crashGate(action) {
  const problems = checkCollisions(false);
  if (!problems.length) { crashForced = false; return true; }
  const shown = problems.slice(0, 6).join("\n") +
    (problems.length > 6 ? "\n…and " + (problems.length - 6) + " more" : "");
  crashForced = false;
  const st = $("tlStat");
  const message="Not sent: this movement does not keep the safety gap. Fix the red keyframes or adjust the rig/gap in Setup.\n"+shown;
  if (st) st.textContent = message;
  notice(message);
  return false;
}

function checkCollisions(showAlert) {
  clearBadMarks();
  const problems = [];
  // only what actually runs: a suspended keyframe cannot crash the robot, and
  // skipping one creates a NEW move (1->3) that has never been checked
  const K = playKeys();
  if (K.length) {
    const c0 = collisionAt(K[0].pose);
    if (c0) { keys[K[0].src].bad = c0; problems.push("keyframe " + K[0].src + " (start pose): " + c0); }
  }
  for (let i = 1; i < K.length; i++) {
    for (let s = 1; s <= 12; s++) {
      const f = 0.5 - 0.5 * Math.cos(Math.PI * s / 12); // same ease as the robot
      const p = K[i - 1].pose.map((a, j) => a + (K[i].pose[j] - a) * f);
      const hit = collisionAt(p);
      if (hit) {
        keys[K[i].src].bad = hit + (s < 12 ? " (during the move)" : "");
        problems.push("keyframe " + K[i].src + ": " + keys[K[i].src].bad);
        break;
      }
    }
  }
  renderTimeline();
  if (showAlert) {
    if (problems.length)
      alert("CAN'T RUN — the robot will crash:\n\n" + problems.join("\n") +
            "\n\nThe bad keyframes are marked RED in the timeline. Fix the pose (or add an in-between keyframe that goes around) and check again.");
    else
      $("tlStat").textContent = "collision check passed — the sequence is safe ✓";
  }
  return problems;
}
