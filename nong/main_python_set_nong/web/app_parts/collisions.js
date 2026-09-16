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
  const d = RIG.dims, k = fkPoints(p);
  const hx = d.torsoW / 2, hy = d.torsoH / 2, hz = d.torsoD / 2;
  const headC = new THREE.Vector3(0, hy + 68, 0);
  const segs = [ // upper arms start next to the torso, so skip their first part
    // radii come from the per-bar sizes in the rig (0=L upper, 1=L fore, 2=R upper, 3=R fore)
    { n: "left upper arm",  a: k.shL, b: k.elL, r: RIG.barR[0] || R_ARM, t0: 0.4 },
    { n: "left forearm",    a: k.elL, b: k.wrL, r: RIG.barR[1] || R_ARM, t0: 0.1 },
    { n: "right upper arm", a: k.shR, b: k.elR, r: RIG.barR[2] || R_ARM, t0: 0.4 },
    { n: "right forearm",   a: k.elR, b: k.wrR, r: RIG.barR[3] || R_ARM, t0: 0.1 },
  ];
  for (const s of segs) {
    for (let i = 0; i <= 6; i++) {
      const t = s.t0 + (1 - s.t0) * i / 6;
      const pt = segPoint(s.a, s.b, t);
      const r = t > 0.9 && s.n.includes("forearm") ? R_WRIST : s.r; // wrist ball
      if (distToBox(pt, hx, hy, hz) < r + CLEAR) return s.n + " hits the body";
      if (pt.distanceTo(headC) < r + R_HEAD + CLEAR) return s.n + " hits the head";
    }
  }
  // left arm vs right arm (all segment pairs)
  const L = [segs[0], segs[1]], R = [segs[2], segs[3]];
  for (const sl of L)
    for (const sr of R)
      if (segSegDist(sl.a, sl.b, sr.a, sr.b) < sl.r + sr.r + CLEAR)
        return sl.n + " hits the " + sr.n;
  if (k.wrL.distanceTo(k.wrR) < 2 * R_WRIST + CLEAR) return "the hands hit each other";
  return null;
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
// Now: the preview always plays — seeing the crash is how you fix it — and the
// ROBOT only moves if you say so. Forcing is allowed because the check works
// from the rig's dimensions, and a rig that does not match the real robot can
// call a safe move a crash. It is your arm; you can see it.
//
// The permission lasts for one action. Any edit to the timeline clears it, so
// a forced run never silently covers a movement you changed afterwards.
let crashForced = false;
let previewOnly = false;   // this run draws, but does not drive the arm

function crashGate(action) {
  const problems = checkCollisions(false);
  if (!problems.length) { crashForced = false; return true; }
  const shown = problems.slice(0, 6).join("\n") +
    (problems.length > 6 ? "\n…and " + (problems.length - 6) + " more" : "");
  const go = confirm(
    "THE ROBOT WILL CRASH\n\n" + shown +
    "\n\nThe bad keyframes are marked RED in the timeline.\n\n" +
    "OK      = " + action + " ANYWAY — the arm may hit itself\n" +
    "Cancel  = stop, and fix it first");
  crashForced = go;
  const st = $("tlStat");
  if (st) st.textContent = go
    ? "⚠ FORCED past the crash check — the arm may hit itself"
    : "stopped: this movement crashes (the red keyframes)";
  return go;
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
