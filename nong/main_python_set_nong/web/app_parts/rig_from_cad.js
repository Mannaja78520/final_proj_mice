// --- the simple shapes made from the CAD (A48-6) ---
//
// User 2026-10-23: "why 15 deg off? make it like the real one - the rig was
// set up roughly in a hurry, the real robot follows the CAD", then "but keep
// the old rig's axes, they were tuned to the real robot". So from the CAD:
// sizes, where each shoulder sits and the shrug pivot. With "joints" in the
// data also each joint's tilt, a fixed turn after each servo (RIG.after: a
// CAD bone is not square to its joint) and the CAD's pair order.
// Measured at the zero pose with the fitted sense and zero of every joint
// (urdf_view.js), so the shapes then move EXACTLY like the CAD.
//
// What it never changes: zero, home, invert, min, max, offset. Those are the
// servo numbers; a pose keeps the same numbers and the CAD the same pose.
// The old rig is kept in RIG.view.oldRig and comes back with one button.
// Which parts are taken: urdf_view.json "rigFromCad". check_urdf_look holds it.

const RIG_CAD_KEYS = ["dims", "tilt", "after", "mount", "order"];   // what is replaced (and kept)
let rigCadLast = "";              // what the last make/undo said

function rigCadCfg() { return (URDF_CFG && URDF_CFG.rigFromCad) || {}; }
function rigCadTakes(part) { return (rigCadCfg().take || ["sizes", "shoulders", "shrugPivot"]).includes(part); }
function rigCadLabel() { return rigCadCfg().label || (rigCadTakes("joints") ? "Make the simple shapes match the CAD" : "Use the CAD's sizes and shoulder spots"); }

// The rig parts from the CAD on screen, or {error}. Touches nothing.
function rigFromCadMeasure() {
  if (!urdfOn) return { error: "the CAD model is not shown" };
  const cfg = rigCadCfg(), dp = Math.pow(10, cfg.round == null ? 4 : cfg.round);
  const rd = (v) => Math.round(v * dp) / dp;
  for (const side of ["L", "R"])
    if (((URDF_CFG.hands || {})[side] || {}).tip === "mesh" && !urdfTip[side].fromMesh)
      return { error: "the " + (side === "L" ? "left" : "right") + " forearm part has not arrived yet" };
  const keep = pose;
  pose = RIG.zero.slice(); applyPose(); robot.updateMatrixWorld(true);
  try {
    const rq = robot.getWorldQuaternion(new THREE.Quaternion()).invert();
    const at = (o) => robot.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    // the waist turns about the body's middle: measure from its line
    const w0 = urdfJ[8] ? at(urdfJ[8].org) : new THREE.Vector3();
    const P = (o) => { const v = at(o); v.x -= w0.x; v.z -= w0.z; return v; };
    const out = { dims: {}, tilt: RIG.tilt.map(t => t.slice()), after: RIG.after.map(t => t.slice()),
                  mount: { L: RIG.mount.L.slice(), R: RIG.mount.R.slice() }, order: RIG.order.map(o => o.slice()), warn: [] };
    const eul = (q) => { const e = new THREE.Euler().setFromQuaternion(q, "XYZ"); return [e.x, e.y, e.z].map(v => rd(THREE.MathUtils.radToDeg(v))); };
    const S = [], E = [], T = [];
    for (let a = 0; a < 2; a++) {
      const b = a * 4, ch = urdfArm[a];
      S[a] = P(ch[0].org); E[a] = P(ch[2].org); T[a] = P(wristBalls[a]);
      if (P(ch[1].org).distanceTo(S[a]) > (cfg.colocatedMm || 1) || P(ch[3].org).distanceTo(E[a]) > (cfg.colocatedMm || 1))
        out.warn.push("a joint pair of the " + (a ? "right" : "left") + " arm is not at one point in the CAD");
      const ord = [b, b + 1, b + 2, b + 3].sort((x, y) => urdfJ[x].depth - urdfJ[y].depth);
      if ([ord[0], ord[1]].sort().join() !== [b, b + 1].join()) return { error: "the CAD chains the " + (a ? "right" : "left") + " arm in an order the shapes cannot follow" };
      let Wp = new THREE.Quaternion();
      const tilt = [], after = [];
      ord.forEach((j, c) => {
        const e = urdfJ[j];
        // the CAD axis in the body, turned the way the Studio joint turns
        const aw = e.axis.clone().applyQuaternion(e.mov.getWorldQuaternion(new THREE.Quaternion())).applyQuaternion(rq).multiplyScalar(e.sign).normalize();
        const T0 = new THREE.Quaternion().setFromUnitVectors(_AXVEC[RIG.axis[j]], aw.applyQuaternion(Wp.clone().invert()));
        let Wn = Wp.clone().multiply(T0), U = new THREE.Quaternion();
        if (c === 1 || c === 3) {
          // the bar hangs along -Y: turn it onto the CAD's own bone
          const bone = (c === 1 ? E[a].clone().sub(S[a]) : T[a].clone().sub(E[a])).normalize();
          // the forearm takes the CAD hand's own frame (its -Y lies on the
          // forearm, urdfPlaceHand), less the palm turn the hand adds back
          const R = c === 3
            ? rq.clone().multiply(urdfTip[a ? "R" : "L"].hand.getWorldQuaternion(new THREE.Quaternion()))
                .multiply(new THREE.Quaternion().setFromAxisAngle(_AXVEC.y, -THREE.MathUtils.degToRad(RIG.palmTurn[a] || 0)))
                .multiply(Wn.clone().invert())
            : new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, -1, 0).applyQuaternion(Wn), bone);
          const W2 = R.multiply(Wn);
          U = Wn.clone().invert().multiply(W2);
          Wn = W2;
        }
        tilt[j] = eul(T0); after[j] = eul(U);
        Wp = Wn;
      });
      if (rigCadTakes("joints")) {
        out.order[a] = ord;
        ord.forEach(j => { out.tilt[j] = tilt[j]; out.after[j] = after[j]; });
      }
    }
    const sx = (S[0].x - S[1].x) / 2, sy = RIG.dims.shoulderY || 0;
    if (rigCadTakes("shoulders")) {
      out.dims.shoulderX = rd(sx);
      out.mount.L = [S[0].x - sx, S[0].y - sy, S[0].z].map(rd);
      out.mount.R = [S[1].x + sx, S[1].y - sy, S[1].z].map(rd);
    }
    if (rigCadTakes("sizes")) {
      out.dims.upperLenL = rd(E[0].distanceTo(S[0])); out.dims.upperLenR = rd(E[1].distanceTo(S[1]));
      out.dims.foreLenL = rd(T[0].distanceTo(E[0])); out.dims.foreLenR = rd(T[1].distanceTo(E[1]));
    }
    if (rigCadTakes("shrugPivot") && urdfJ[9])
      out.dims.shrugPivot = rd(P(urdfJ[9].org).y - (S[0].y + S[1].y) / 2);
    return out;
  } finally { pose = keep; applyPose(); }
}
// the shapes' hands at a pose (arms only), for a rig `r`: how far a change moves them
function rigHandsAt(r, p) {
  const keep = RIG; RIG = r;
  try {
    return [0, 1].map(a => {
      const b = a * 4, d = [0, 1, 2, 3].map(k => (p[b + k] - RIG.zero[b + k]) * jdir(b + k));
      const c = rigChain(b, d), side = a ? -1 : 1, D = RIG.dims, m = RIG.mount[a ? "R" : "L"];
      return new THREE.Vector3(side * D.shoulderX + m[0], D.shoulderY + m[1], m[2])
        .addScaledVector(new THREE.Vector3(0, -1, 0).applyQuaternion(c.at[1]), a ? D.upperLenR : D.upperLenL)
        .addScaledVector(new THREE.Vector3(0, -1, 0).applyQuaternion(c.at[3]), a ? D.foreLenR : D.foreLenL);
    });
  } finally { RIG = keep; }
}
// Make it: the old rig is kept (once: a second make keeps the hand-made one).
function rigFromCad() {
  const m = rigFromCadMeasure();
  if (m.error) { rigCadLast = "Cannot make the simple shapes from the CAD: " + m.error + "."; renderRigCadUI(); return false; }
  const v = RIG.view;
  if (!v.oldRig) v.oldRig = JSON.parse(JSON.stringify(RIG_CAD_KEYS.reduce((o, k) => (o[k] = RIG[k], o), {})));
  const before = rigHandsAt(RIG, RIG.home);
  const next = JSON.parse(JSON.stringify(RIG));
  Object.assign(next.dims, m.dims);
  ["tilt", "after", "mount", "order"].forEach(k => { next[k] = m[k]; });
  const after = rigHandsAt(next, next.home);
  ["tilt", "after", "mount", "order"].forEach(k => { RIG[k] = m[k]; });
  Object.assign(RIG.dims, m.dims);
  v.sizes = "cad";
  const mv = after.map((p, a) => Math.round(p.distanceTo(before[a])));
  rigCadLast = (rigCadTakes("joints") ? "The simple shapes now match the CAD." : "The simple shapes now have the CAD's sizes and shoulder spots; your joints are kept.") + " At home the left hand moved " + mv[0] + " mm and the right " + mv[1] +
    " mm; the servo numbers did not change." + (m.warn.length ? " " + m.warn.join("; ") + "." : "");
  rigChanged();
  return true;
}
// Back to the rig kept before the first make.
function rigOldBack() {
  const v = RIG.view;
  if (!v.oldRig) return false;
  RIG_CAD_KEYS.forEach(k => { if (v.oldRig[k] !== undefined) RIG[k] = JSON.parse(JSON.stringify(v.oldRig[k])); });
  v.oldRig = null;
  v.sizes = "custom";
  rigCadLast = "Your old simple shapes are back.";
  rigChanged();
  return true;
}
function renderRigCadUI() {
  const mk = $("rigCadMake"), back = $("rigCadBack"), st = $("rigCadStat");
  if (!mk) return;
  mk.hidden = !(typeof urdfOn !== "undefined" && urdfOn);
  mk.textContent = rigCadLabel();
  if ($("lookUseCad")) $("lookUseCad").textContent = rigCadLabel();
  back.hidden = !(RIG.view && RIG.view.oldRig);
  st.textContent = rigCadLast;
}
