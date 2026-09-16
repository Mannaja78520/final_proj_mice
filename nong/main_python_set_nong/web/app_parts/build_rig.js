// --- build rig ---
// Everything is rebuilt from RIG whenever the Rig setup card changes, so the
// model can be matched to the real robot at runtime.
let robot = null;
let bodyGroup = null;   // WAIST yaws this (torso + head + both arms) about vertical
let shoulderMount = null; // SHRUG lifts this (both arm anchors) up/down
// The 4-bar shrug: each shoulder gets its own rise, from measured points.
const shrugAnchors = { L: null, R: null };
let shrugBaseY = 0;
let jointGroups = [];   // THREE.Group per logical joint (rotation applied here)
let pickMeshes = [];    // meshes that select a pair on click
let wristBalls = [];    // wrist IK handle per arm (moves all 4 joints)
let elbowBalls = [];    // elbow IK handle per arm (moves the 2 shoulder joints)
let linkHolders = {};   // name -> group whose first child is the visual (STL-replaceable)
let pairRingParents = [];

function linkVisual(name, defaultMesh) {
  const holder = new THREE.Group();
  holder.name = "link_" + name;
  holder.add(defaultMesh);
  linkHolders[name] = holder;
  return holder;
}

// one arm segment: the joint ball at its top + the bar hanging from it.
// jointR (ball) and barR (bar thickness) are per-joint sizes from the rig.
function armSegment(len, barR, jointR, mat, pairIdx) {
  const g = new THREE.Group();
  // skeleton (userData.skel): joint ball + thin bone — NEVER hidden, so the
  // joint centers and segment lengths stay visible under an assigned STL
  const ball = new THREE.Mesh(new THREE.SphereGeometry(jointR, 20, 14), matJoint);
  ball.userData.skel = true;
  const boneR = Math.max(1.5, Math.min(3, barR * 0.25));
  const bone = new THREE.Mesh(new THREE.CylinderGeometry(boneR, boneR, len, 8), matJoint);
  bone.position.y = -len / 2;
  bone.userData.skel = true;
  // flesh: the placeholder bar, hidden when an STL is assigned
  const tube = new THREE.Mesh(new THREE.CylinderGeometry(barR, barR * 0.82, len, 14), mat);
  tube.position.y = -len / 2;
  ball.userData.pair = bone.userData.pair = tube.userData.pair = pairIdx;
  pickMeshes.push(ball, bone, tube);
  g.add(ball, bone, tube);
  return g;
}

function buildArm(side) {           // side: +1 = robot left (+X), -1 = right
  const d = RIG.dims;
  const base = side > 0 ? 0 : 4;    // first logical joint of this arm
  const pairSh = side > 0 ? 0 : 2, pairEl = side > 0 ? 1 : 3;

  const anchor = new THREE.Group(); // fixed shoulder anchor on the torso
  // shoulderMount's origin is the shrug bearing (shoulderY + shrugPivot up), so
  // the anchor hangs shrugPivot below it and lands back on the shoulder line.
  anchor.position.set(side * d.shoulderX, -(d.shrugPivot || 0), 0);
  shoulderMount.add(anchor);        // SHRUG rocks the mount; WAIST yaws the body
  // Keep a handle on each anchor and its resting height. With a 4-bar shrug
  // the two shoulders do NOT move by the same amount, so each one is placed
  // from its own measured curve instead of both riding one rotation.
  // side > 0 is the LEFT arm everywhere else in this function (d.upperLenL,
  // "L_upper", userData.arm = 0). This one line had it backwards, so the
  // measured left rise was applied to the right shoulder and vice versa —
  // the preview lifted the wrong shoulder, which is exactly the asymmetry the
  // 4-bar measurement table exists to show.
  shrugAnchors[side > 0 ? "L" : "R"] = anchor;
  shrugBaseY = -(d.shrugPivot || 0);

  const shP = new THREE.Group(); anchor.add(shP);      // joint base+0
  const shR = new THREE.Group(); shP.add(shR);         // joint base+1
  jointGroups[base] = shP; jointGroups[base + 1] = shR;

  const upperLen = side > 0 ? d.upperLenL : d.upperLenR;
  const foreLen = side > 0 ? d.foreLenL : d.foreLenR;
  const upperName = side > 0 ? "L_upper" : "R_upper";
  shR.add(linkVisual(upperName, armSegment(upperLen, RIG.barR[pairSh], RIG.jointR[pairSh],
                                           partMat(upperName), pairSh)));

  const elAnchor = new THREE.Group();
  elAnchor.position.set(0, -upperLen, 0);
  shR.add(elAnchor);

  // orange ball = the elbow IK drag handle. Dragging it rotates the 2
  // SHOULDER servos to move the elbow there (the rings still rotate each
  // servo). On elAnchor (elbow center, before the elbow's own rotation).
  const elbowMat = new THREE.MeshBasicMaterial({ color: 0xff9944, depthTest: false });
  const elbowBall = new THREE.Mesh(new THREE.SphereGeometry(12, 18, 12), elbowMat);
  elbowBall.userData.arm = side > 0 ? 0 : 1;
  elbowBall.renderOrder = 19;
  elAnchor.add(elbowBall);
  elbowBalls.push(elbowBall);

  const elP = new THREE.Group(); elAnchor.add(elP);    // joint base+2
  const elR = new THREE.Group(); elP.add(elR);         // joint base+3
  jointGroups[base + 2] = elP; jointGroups[base + 3] = elR;

  const foreName = side > 0 ? "L_fore" : "R_fore";
  elR.add(linkVisual(foreName, armSegment(foreLen, RIG.barR[pairEl], RIG.jointR[pairEl],
                                          partMat(foreName), pairEl)));

  // green ball = the IK drag handle at the end of the forearm (no paddle
  // hand). depthTest off so it is always visible/grabbable.
  const handleMat = new THREE.MeshBasicMaterial({ color: 0x3ecf8e, depthTest: false });
  const wrist = new THREE.Mesh(new THREE.SphereGeometry(14, 20, 14), handleMat);
  wrist.position.set(0, -foreLen, 0);
  wrist.userData.arm = side > 0 ? 0 : 1;
  wrist.renderOrder = 20;
  elR.add(wrist);
  wristBalls.push(wrist);
  return { anchor, shP, elAnchor, elP };
}

function buildRobot() {
  if (robot) {
    scene.remove(robot);
    // Free the GPU side of the OLD robot. Removing it from the scene only
    // drops the JavaScript reference — the buffers and shader programs stay
    // on the graphics card until they are disposed by hand.
    //
    // Geometry was already freed here. MATERIALS were not, and partMat()
    // builds a brand new one for every mesh on every build. buildRobot() runs
    // on every rig edit, so tuning the rig quietly leaked a material per mesh
    // per keystroke. Enough of them exhausts GPU memory, and what you see is
    // the browser or the whole machine falling over — not an error message.
    //
    // Textures are deliberately NOT disposed: getTex() caches them and hands
    // the same instance to every build, so disposing one here would blank it
    // for every mesh that uses it afterwards.
    robot.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material;
      if (!m) return;
      (Array.isArray(m) ? m : [m]).forEach(x => { if (x && x.dispose) x.dispose(); });
    });
  }
  robot = new THREE.Group();
  scene.add(robot);
  // robot -> bodyGroup (WAIST yaw) -> {torso, head, shoulderMount (SHRUG)}.
  // The waist turns the WHOLE upper body (torso, head, both arms) left/right;
  // the shrug rocks the shoulder mount. Both are visual here — the real
  // joint value is what gets sent to the robot.
  bodyGroup = new THREE.Group(); robot.add(bodyGroup);
  const d = RIG.dims;
  // The shrug see-saw pivots on a BEARING above the shoulder line (shrugPivot
  // mm up), NOT at the servo. Put the mount's ORIGIN at that bearing so the
  // rock happens about the real pivot; the arm anchors then hang shrugPivot mm
  // below it (added in buildArm at y = -shrugPivot), landing on the shoulder line.
  shoulderMount = new THREE.Group();
  shoulderMount.position.set(0, d.shoulderY + (d.shrugPivot || 0), 0);
  bodyGroup.add(shoulderMount);
  jointGroups = []; pickMeshes = []; wristBalls = []; elbowBalls = []; linkHolders = {};

  // torso + head (visuals replaceable by STL)
  const torsoMesh = new THREE.Mesh(new THREE.BoxGeometry(d.torsoW, d.torsoH, d.torsoD), partMat("torso"));
  bodyGroup.add(linkVisual("torso", torsoMesh));
  const headG = new THREE.Group();
  const headMat = partMat("head");
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(22, 26, 40, 12), headMat);
  neck.position.y = d.torsoH / 2 + 15;
  const head = new THREE.Mesh(new THREE.SphereGeometry(46, 24, 18), headMat);
  head.position.y = d.torsoH / 2 + 68;
  headG.add(neck, head);
  bodyGroup.add(linkVisual("head", headG));

  const armL = buildArm(+1);
  const armR = buildArm(-1);
  // gizmo ring parents: axis-1 ring on the fixed anchor, axis-2 ring inside joint-1
  pairRingParents = [
    [armL.shP.parent, armL.shP], [armL.elP.parent, armL.elP],
    [armR.shP.parent, armR.shP], [armR.elP.parent, armR.elP],
  ];
  clearGizmo(); selPair = -1;
  applyMeshes();   // put assigned STLs back onto the fresh link holders
  applyPose();
}

const _AXVEC = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const _qBase = new THREE.Quaternion(), _qAxis = new THREE.Quaternion(), _eTilt = new THREE.Euler();
// a joint's rotation axis (unit, in its parent frame) = tilt applied to the
// primary axis. Used by applyPose and the gizmo rings so both agree.
function jointTiltQuat(i, out) {
  const t = RIG.tilt[i] || [0, 0, 0];
  _eTilt.set(THREE.MathUtils.degToRad(t[0]), THREE.MathUtils.degToRad(t[1]),
             THREE.MathUtils.degToRad(t[2]), "XYZ");
  return (out || new THREE.Quaternion()).setFromEuler(_eTilt);
}
function jointAxisVec(i) {
  return _AXVEC[RIG.axis[i]].clone().applyQuaternion(jointTiltQuat(i)).normalize();
}
// joint angle relative to its zero, in degrees — always FINITE. A missing
// pose/zero (e.g. a half-migrated rig) must never leak NaN into a transform,
// or the whole group it drives renders at NaN = invisible.
function jointDelta(i) {
  const p = pose[i], z = RIG.zero[i];
  const v = (Number.isFinite(p) ? p : 90) - (Number.isFinite(z) ? z : 90);
  return v * jdir(i);
}
function applyPose() {
  // the editor works in JOINT degrees — pose[i] IS the physical joint angle.
  // each joint = a mounting TILT (roll/pitch/yaw, for axes not exactly at 90°)
  // then the servo rotation about its primary axis (in the tilted frame).
  for (let i = 0; i < ARMJ; i++) {
    const g = jointGroups[i];
    if (!g) continue;
    const ax = RIG.axis[i];
    const v = jointDelta(i);
    const t = RIG.tilt[i] || [0, 0, 0];
    _eTilt.set(THREE.MathUtils.degToRad(t[0]), THREE.MathUtils.degToRad(t[1]),
               THREE.MathUtils.degToRad(t[2]), "XYZ");
    _qBase.setFromEuler(_eTilt);
    _qAxis.setFromAxisAngle(_AXVEC[ax], THREE.MathUtils.degToRad(v));
    g.quaternion.copy(_qBase).multiply(_qAxis);    // rotate about the tilted axis
  }
  // WAIST (joint 9) yaws the whole upper body about vertical; SHRUG (joint 10)
  // pitches the shoulder mount so both shoulders rise/fall together.
  if (bodyGroup)
    bodyGroup.rotation.set(0, THREE.MathUtils.degToRad(jointDelta(8)), 0);
  if (shoulderMount) {
    const rise = shrugRise(pose[9]);
    if (rise) {
      // Calibrated 4-bar: each shoulder is placed at its OWN measured height.
      // The mount itself does not rock, or the rotation would be applied on
      // top of the measurement and double-count it.
      shoulderMount.rotation.set(0, 0, 0);
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY + rise.l;
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY + rise.r;
    } else {
      // Uncalibrated: the original symmetric see-saw, unchanged. SHRUG is a
      // ROLL about the front-back axis (Z) — one shoulder rises while the
      // other drops. Exaggerated x3 so the small (~6°) move reads.
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY;
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY;
      shoulderMount.rotation.set(0, 0, THREE.MathUtils.degToRad(jointDelta(9) * 3));
    }
  }
}

// The measurement table. Rows are "at this SHRUG angle, the left shoulder rose
// L mm and the right rose R mm". Two rows is the minimum that defines a line;
// more rows describe the curve the 4-bar actually follows.
function renderShrugCurve() {
  const box = $("shrugCurve");
  if (!box) return;
  const c = RIG.shrugCurve || (RIG.shrugCurve = []);
  box.innerHTML = "";

  const head = document.createElement("div");
  head.className = "jrow";
  head.innerHTML = '<span class="jname mini">SHRUG&deg;</span>' +
                   '<span class="mini">left rise mm</span>' +
                   '<span class="mini">right rise mm</span><span></span>';
  box.appendChild(head);

  c.forEach((pt, i) => {
    const row = document.createElement("div"); row.className = "jrow";
    const mk = (key, w) => {
      const el = document.createElement("input");
      el.type = "number"; el.step = key === "j" ? 1 : 0.5; el.value = pt[key];
      el.style.width = w;
      el.onchange = () => {
        pt[key] = +el.value || 0;
        rigChanged();               // re-render the robot with the new curve
        renderShrugCurve();
      };
      return el;
    };
    const nm = document.createElement("span"); nm.className = "jname";
    nm.appendChild(mk("j", "62px"));
    row.appendChild(nm);
    row.appendChild(mk("l", "70px"));
    row.appendChild(mk("r", "70px"));
    const del = document.createElement("button");
    del.textContent = "✕";
    del.title = "remove this measurement";
    del.onclick = () => { c.splice(i, 1); rigChanged(); renderShrugCurve(); };
    row.appendChild(del);
    box.appendChild(row);
  });

  const add = document.createElement("button");
  add.textContent = "+ add a measurement";
  add.onclick = () => {
    const last = c.length ? c[c.length - 1].j : 87;
    c.push({ j: Math.round(last) + 3, l: 0, r: 0 });
    rigChanged(); renderShrugCurve();
  };
  box.appendChild(add);

  const note = document.createElement("div");
  note.className = "mini";
  note.textContent = c.length >= 2
    ? c.length + " measurements — the preview now moves each shoulder by its own amount"
    : "fewer than 2 measurements: the preview still uses the old symmetric rock";
  box.appendChild(note);
}

// ---- SHRUG: a 4-bar linkage is not a see-saw ---------------------------
//
// One servo drives the linkage that lifts BOTH shoulders, so there is only
// ever one angle to command — but the linkage does not give the two sides the
// same movement, and the ratio changes across the travel. The robot does
// whatever the mechanism does; it was the PREVIEW that was wrong, because it
// rocked one rigid mount and so always showed the two sides as mirror images.
//
// RIG.shrugCurve is what you measured on the real robot:
//     [{ j: 87, l: -4, r: 6.5 }, { j: 90, l: 0, r: 0 }, { j: 93, l: 5, r: -7.5 }]
// j = the SHRUG joint angle, l/r = how far that shoulder actually rose, in mm
// (up positive). Points may be in any order and there can be as few as two.
//
// Measured beats computed here: the real linkage carries horn spline offset,
// bearing slop and mounting error, none of which the CAD knows about.
//
// With no curve set, behaviour is exactly as before — a symmetric rock.
function shrugRise(j) {
  const c = (RIG.shrugCurve || []).filter(p => p && isFinite(p.j));
  if (c.length < 2) return null;                 // not calibrated: old behaviour
  const pts = c.slice().sort((a, b) => a.j - b.j);
  if (j <= pts[0].j) return { l: +pts[0].l || 0, r: +pts[0].r || 0 };
  const last = pts[pts.length - 1];
  if (j >= last.j) return { l: +last.l || 0, r: +last.r || 0 };
  for (let i = 1; i < pts.length; i++) {
    if (j > pts[i].j) continue;
    const a = pts[i - 1], b = pts[i];
    const span = b.j - a.j;
    // two measurements at the same angle would divide by zero
    const f = span > 1e-9 ? (j - a.j) / span : 0;
    return { l: (+a.l || 0) + ((+b.l || 0) - (+a.l || 0)) * f,
             r: (+a.r || 0) + ((+b.r || 0) - (+a.r || 0)) * f };
  }
  return { l: +last.l || 0, r: +last.r || 0 };
}
