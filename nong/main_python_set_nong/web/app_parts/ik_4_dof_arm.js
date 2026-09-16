// --- IK (4-DOF arm) ---
function wristPos(arm, out) {
  return wristBalls[arm].getWorldPosition(out || new THREE.Vector3());
}
function solveIK(arm, target, iters = 8) {
  // damped least squares on the arm's 4 joints
  const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
  // EPS = deg step for the numeric jacobian (mm/deg). LAMBDA2 damps the
  // solve — it adds to J·Jᵀ (units mm²/deg², order ~10-40 here), so it must
  // be small (~a few) or every step is over-damped and the wrist barely
  // moves. Higher = smoother but slower; lower = faster but jittery.
  const EPS = 0.6, LAMBDA2 = 4;
  const tmp = new THREE.Vector3();
  for (let iter = 0; iter < iters; iter++) {
    applyPose(); robot.updateMatrixWorld(true);
    const p = wristPos(arm);
    const e = target.clone().sub(p);
    if (e.length() < 1.0) break;
    if (e.length() > 120) e.setLength(120);     // reach further per iteration

    // numeric jacobian: 3 x 4 (mm per deg)
    const J = [];
    for (let c = 0; c < 4; c++) {
      const j = idx[c], old = pose[j];
      pose[j] = clampJ(j, old + EPS);
      applyPose(); robot.updateMatrixWorld(true);
      wristPos(arm, tmp);
      J.push(tmp.clone().sub(p).divideScalar(pose[j] - old || EPS));
      pose[j] = old;
    }
    // A = J*J^T + lambda^2 I  (3x3), solve A y = e, dq = J^T y
    const A = [[LAMBDA2, 0, 0], [0, LAMBDA2, 0], [0, 0, LAMBDA2]];
    const comp = (v, k) => (k === 0 ? v.x : k === 1 ? v.y : v.z);
    for (let r = 0; r < 3; r++)
      for (let c = 0; c < 3; c++)
        for (let k = 0; k < 4; k++) A[r][c] += comp(J[k], r) * comp(J[k], c);
    const y = solve3(A, [e.x, e.y, e.z]);
    if (!y) break;
    for (let c = 0; c < 4; c++) {
      const dq = comp(J[c], 0) * y[0] + comp(J[c], 1) * y[1] + comp(J[c], 2) * y[2];
      pose[idx[c]] = clampJ(idx[c], pose[idx[c]] + dq);
    }
  }
  // Coordinate-descent (CCD) polish: DLS stalls at straight-arm singularities
  // (rotating the shoulder there moves the wrist sideways, not toward an
  // above/below target). CCD tries each joint with finite steps and keeps
  // whatever gets closer, so it always makes progress and escapes the
  // singularity — this is what lets a drag actually reach the target by
  // coordinating shoulder + elbow.
  ccdPolish(arm, target, 12);
  applyPose();
}
// generic coordinate-descent over a joint set toward a target end point.
// endBall = the mesh whose world position should reach the target.
function ccdChain(idx, endBall, target, rounds) {
  const dist = () => {
    applyPose(); robot.updateMatrixWorld(true);
    return endBall.getWorldPosition(new THREE.Vector3()).distanceTo(target);
  };
  let best = dist();
  for (let r = 0; r < rounds && best > 0.6; r++) {
    let improved = false;
    for (const j of idx) {
      for (const step of [10, 4, 1.5, 0.5]) {
        for (const dir of [1, -1]) {
          const old = pose[j];
          const nv = clampJ(j, old + dir * step);
          if (nv === old) continue;
          pose[j] = nv;
          const d = dist();
          if (d < best - 0.02) { best = d; improved = true; }
          else pose[j] = old;
        }
      }
    }
    if (!improved) break;
  }
  return best;
}
function ccdPolish(arm, target, rounds) {
  return ccdChain(arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7], wristBalls[arm], target, rounds);
}
// drag the elbow: rotate ONLY the 2 shoulder servos to place the elbow.
// Walk the target in small steps (robust, like the wrist drag) then polish.
function solveElbowIK(arm, target) {
  const idx = arm === 0 ? [0, 1] : [4, 5];
  const eb = elbowBalls[arm];
  const start = eb.getWorldPosition(new THREE.Vector3());
  const steps = Math.min(30, Math.max(4, Math.ceil(start.distanceTo(target) / 15)));
  for (let s = 1; s <= steps; s++) ccdChain(idx, eb, start.clone().lerp(target, s / steps), 4);
  ccdChain(idx, eb, target, 20);
  applyPose();
}
function solve3(A, b) { // gaussian elimination, 3x3
  const M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < 3; c++) {
    let p = c;
    for (let r = c + 1; r < 3; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-9) return null;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < 3; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      for (let k = c; k < 4; k++) M[r][k] -= f * M[c][k];
    }
  }
  return [M[0][3] / M[0][0], M[1][3] / M[1][1], M[2][3] / M[2][2]];
}
