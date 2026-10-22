// --- robot look: simple shapes or the CAD model (URDF) (A48-1) ---
// User 2026-10-23: choose the old look or the URDF; the URDF at the file's
// real sizes; going back asks URDF sizes or your own, and your own are kept.
// The URDF tree IS the robot while it is shown: jointGroups / elbowBalls /
// wristBalls / palmMarks / bodyGroup point into it, so IK, collisions, video
// fitting, dummy follow, playback and monitor (all pose -> applyPose) move the
// CAD chain itself, not shapes laid over the old pivots. Choices, joint names,
// signs and sizes are data: urdf_view.json beside this page.
let URDF_CFG = null;               // urdf_view.json
const urdfFiles = {};              // models path -> parsed file, or {error}
let urdfJ = [];                    // per Studio joint: {axis, sign, off, quality, name}
let urdfTip = {};                  // "L"/"R" -> {link, dir, mm, fromMesh}
let urdfLast = { dims: null, warn: [], error: "" };  // what the last build found
let urdfModelList = [];            // [{path, label}] offered in the box
const urdfGeo = {};                // mesh url -> BufferGeometry (kept across rebuilds)
let urdfBuildGen = 0;              // a mesh arriving after a rebuild is dropped

fetch("urdf_view.json").then(r => r.json()).then(j => {
  URDF_CFG = j;
  renderLookUI();
  urdfRefreshModels();
  if (lookKind() === "urdf") buildRobot();      // a saved URDF look waits for this
}).catch(() => {});

function lookOf(id) {
  const looks = (URDF_CFG && URDF_CFG.looks) || [];
  return looks.find(l => l.id === id) || null;
}
function lookKind() {
  const v = RIG.view || {};
  const l = lookOf(v.look);
  return l ? l.kind : (v.look === "urdf" ? "urdf" : "rig");
}

// ---- reading the file ------------------------------------------------------
// ROS is X front, Y left, Z up; Studio is X left, Y up, Z front. A proper
// rotation (a cyclic swap), applied once at the root, so every rpy and axis
// below stays exactly as the file wrote it.
function urdfRootQuat() {
  const up = ((URDF_CFG && URDF_CFG.frame) || {}).up || "z";
  const q = new THREE.Quaternion();
  if (up === "z")
    q.setFromRotationMatrix(new THREE.Matrix4().set(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1));
  return q;
}
function urdfUnit() { return +(((URDF_CFG && URDF_CFG.frame) || {}).unitMm) || 1000; }
function urdfNumList(el, attr, def) {
  const s = el && el.getAttribute(attr);
  if (!s) return def.slice();
  const v = s.trim().split(/\s+/).map(Number);
  return v.length === def.length && v.every(Number.isFinite) ? v : def.slice();
}
function urdfOrigin(el) {
  const o = el && el.querySelector(":scope > origin");
  return { xyz: urdfNumList(o, "xyz", [0, 0, 0]), rpy: urdfNumList(o, "rpy", [0, 0, 0]) };
}
// -> {links: {name: {visuals}}, joints: [..], root} or throws a plain reason
function urdfRead(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("the file is not readable XML");
  const top = doc.querySelector("robot");
  if (!top) throw new Error("the file has no <robot>");
  const links = {}, joints = [];
  top.querySelectorAll(":scope > link").forEach(l => {
    const visuals = [];
    l.querySelectorAll(":scope > visual").forEach(v => {
      const g = v.querySelector("geometry");
      const m = g && g.querySelector("mesh"), b = g && g.querySelector("box");
      const c = g && g.querySelector("cylinder"), s = g && g.querySelector("sphere");
      const vis = { ...urdfOrigin(v) };
      if (m) Object.assign(vis, { mesh: m.getAttribute("filename") || "", scale: urdfNumList(m, "scale", [1, 1, 1]) });
      else if (b) vis.box = urdfNumList(b, "size", [0, 0, 0]);
      else if (c) vis.cyl = [+c.getAttribute("radius") || 0, +c.getAttribute("length") || 0];
      else if (s) vis.sphere = +s.getAttribute("radius") || 0;
      else return;
      visuals.push(vis);
    });
    links[l.getAttribute("name")] = { visuals };
  });
  top.querySelectorAll(":scope > joint").forEach(j => {
    const lim = j.querySelector("limit");
    joints.push({
      name: j.getAttribute("name"), type: j.getAttribute("type") || "fixed",
      parent: (j.querySelector("parent") || { getAttribute: () => "" }).getAttribute("link"),
      child: (j.querySelector("child") || { getAttribute: () => "" }).getAttribute("link"),
      ...urdfOrigin(j), axis: urdfNumList(j.querySelector("axis"), "xyz", [1, 0, 0]),
      lower: lim ? +lim.getAttribute("lower") : NaN, upper: lim ? +lim.getAttribute("upper") : NaN,
    });
  });
  const kids = new Set();
  for (const j of joints) {
    if (!links[j.parent] || !links[j.child]) throw new Error("joint " + j.name + " names a part the file does not have");
    if (kids.has(j.child)) throw new Error("part " + j.child + " hangs from two joints");
    kids.add(j.child);
  }
  const roots = Object.keys(links).filter(n => !kids.has(n));
  if (roots.length !== 1) throw new Error(roots.length ? "the file has more than one base part" : "the parts form a loop");
  return { links, joints, root: roots[0] };
}
async function urdfLoad(path) {
  if (urdfFiles[path]) return urdfFiles[path];
  try {
    const r = await fetch("/models/" + path.split("/").map(encodeURIComponent).join("/"));
    if (!r.ok) throw new Error("the file is not in the models folder");
    urdfFiles[path] = { path, ...urdfRead(await r.text()) };
  } catch (e) {
    urdfFiles[path] = { path, error: e.message || String(e) };
  }
  return urdfFiles[path];
}
// package://pkg/x -> <the folder named pkg above the URDF>/x; plain names are
// beside the URDF; anything else is looked for by its file name.
function urdfMeshUrls(fn, urdfPath) {
  const dir = urdfPath.split("/").slice(0, -1);
  const out = [];
  const m = /^package:\/\/([^/]+)\/(.*)$/.exec(fn);
  if (m) {
    const k = dir.lastIndexOf(m[1]);
    out.push((k >= 0 ? dir.slice(0, k + 1) : [m[1]]).concat(m[2].split("/")));
  } else if (!/^[a-z]+:\/\//i.test(fn) && !/^[\\/]|^[a-z]:/i.test(fn)) {
    const p = dir.slice();
    fn.split("/").forEach(s => { if (s === "..") p.pop(); else if (s && s !== ".") p.push(s); });
    out.push(p);
  }
  out.push([fn.split(/[\\/]/).pop()]);
  return out.map(p => "/models/" + p.map(encodeURIComponent).join("/"));
}
function urdfMesh(urls, cb, fail) {
  const u = urls[0];
  if (!u) { fail(); return; }
  if (urdfGeo[u]) { cb(urdfGeo[u]); return; }
  stlLoader.load(u, geo => { urdfGeo[u] = geo; cb(geo); }, undefined,
                 () => urdfMesh(urls.slice(1), cb, fail));
}

// ---- building it ------------------------------------------------------------
const _uQ = new THREE.Quaternion(), _uE = new THREE.Euler();
function urdfRpyQuat(rpy, out) {
  // URDF rpy is fixed-axis X then Y then Z = Rz*Ry*Rx = three's "ZYX" order
  return (out || new THREE.Quaternion()).setFromEuler(_uE.set(rpy[0], rpy[1], rpy[2], "ZYX"));
}
// The old shapes' axis of joint i in the world at the zero pose: the tilts of
// that arm's joints up to i, then its own axis. Used to pick each URDF joint's
// sense, so a raised hand goes the way it always went.
function rigRestAxis(i) {
  if (i === 8) return new THREE.Vector3(0, 1, 0);      // waist: bodyGroup yaw
  if (i === 9) return new THREE.Vector3(0, 0, 1);      // shrug: shoulderMount roll
  const q = new THREE.Quaternion();
  for (let k = i - i % 4; k <= i; k++) q.multiply(jointTiltQuat(k));
  return _AXVEC[RIG.axis[i]].clone().applyQuaternion(q).normalize();
}
function urdfJointCfg(i) { return ((URDF_CFG && URDF_CFG.joints) || {})[JOINT_NAMES[i]] || {}; }

// Builds the file's tree into `root` and points every handle into it.
// Returns false (nothing built) when the look is not URDF or not ready yet.
function urdfBuildInto(root) {
  urdfOn = false;
  if (lookKind() !== "urdf" || !URDF_CFG) return false;
  const path = (RIG.view || {}).model;
  if (!path) return false;
  const f = urdfFiles[path];
  if (!f) { urdfLoad(path).then(() => { if ((RIG.view || {}).model === path) buildRobot(); }); return false; }
  if (f.error) { urdfLast.error = f.error; renderLookUI(); return false; }
  const U = urdfUnit(), warn = [];
  const base = new THREE.Group(); base.name = "urdf_root";
  base.quaternion.copy(urdfRootQuat());
  root.add(base);
  const linkG = {}, jointOf = {};                       // link -> group, link -> joint that carries it
  linkG[f.root] = new THREE.Group(); base.add(linkG[f.root]);
  const byParent = {};
  f.joints.forEach(j => (byParent[j.parent] = byParent[j.parent] || []).push(j));
  const walk = (name) => (byParent[name] || []).forEach(j => {
    const org = new THREE.Group(); org.name = "joint_" + j.name;
    org.position.set(j.xyz[0] * U, j.xyz[1] * U, j.xyz[2] * U);
    urdfRpyQuat(j.rpy, org.quaternion);
    const mov = new THREE.Group();
    org.add(mov); linkG[j.parent].add(org);
    linkG[j.child] = mov; jointOf[j.child] = { j, org, mov };
    walk(j.child);
  });
  walk(f.root);

  // Studio joint -> URDF joint, by the names in the data
  const byName = {};
  f.joints.forEach(j => { byName[j.name] = j; });
  const movOf = {};
  Object.values(jointOf).forEach(o => { movOf[o.j.name] = o; });
  urdfJ = [];
  for (let i = 0; i < NJ; i++) {
    const c = urdfJointCfg(i);
    const hit = (c.urdf || [JOINT_NAMES[i]]).map(n => movOf[n]).find(Boolean);
    if (!hit || !/^(revolute|continuous)$/.test(hit.j.type)) {
      urdfJ[i] = null;
      if (i < ARMJ) { urdfLast.error = "the file has no turning joint for " + JOINT_LABELS[i]; root.remove(base); renderLookUI(); return false; }
      warn.push(JOINT_LABELS[i] + " is not in the file and does not move here");
      continue;
    }
    jointGroups[i] = hit.mov;
    urdfJ[i] = { name: hit.j.name, axis: new THREE.Vector3(...hit.j.axis).normalize(),
                 sign: 1, off: THREE.MathUtils.degToRad(+c.offsetDeg || 0), quality: 1, cfgSign: c.sign };
  }
  for (const side of ["L", "R"]) {
    const h = ((URDF_CFG.hands || {})[side]) || {};
    if (!linkG[h.link]) { urdfLast.error = "the file has no part " + (h.link || "?") + " for the " + (side === "L" ? "left" : "right") + " hand"; root.remove(base); renderLookUI(); return false; }
  }

  // which pair (upper/fore arm) a part moves with: its nearest arm joint
  const pairOfLink = (name) => {
    for (let n = name; jointOf[n]; n = jointOf[n].j.parent) {
      const i = urdfJ.findIndex(b => b && b.name === jointOf[n].j.name);
      if (i >= 0 && i < ARMJ) return Math.floor(i / 2);
    }
    return -1;
  };
  const PAIR_PART = ["L_upper", "L_fore", "R_upper", "R_fore"];
  const gen = ++urdfBuildGen;
  Object.entries(f.links).forEach(([name, l]) => {
    const pair = pairOfLink(name);
    l.visuals.forEach(v => {
      const holder = new THREE.Group();
      holder.position.set(v.xyz[0] * U, v.xyz[1] * U, v.xyz[2] * U);
      urdfRpyQuat(v.rpy, holder.quaternion);
      linkG[name].add(holder);
      const mat = partMat(pair >= 0 ? PAIR_PART[pair] : "torso");
      const put = (geo, sc) => {
        const m = new THREE.Mesh(geo, mat);
        m.scale.set(sc[0], sc[1], sc[2]);
        m.userData.pair = pair; m.userData.urdfLink = name;
        if (pair >= 0) pickMeshes.push(m);
        holder.add(m);
        return m;
      };
      if (v.box) put(new THREE.BoxGeometry(...v.box), [U, U, U]);
      else if (v.cyl) put(new THREE.CylinderGeometry(v.cyl[0], v.cyl[0], v.cyl[1], 20), [U, U, U]).rotation.x = Math.PI / 2;
      else if (v.sphere) put(new THREE.SphereGeometry(v.sphere, 20, 14), [U, U, U]);
      else urdfMesh(urdfMeshUrls(v.mesh, f.path), geo => {
        if (gen !== urdfBuildGen || !urdfOn || holder.parent !== linkG[name]) return;
        put(geo, v.scale.map(s => s * U));
        urdfMeshArrived(name);
      }, () => { urdfLast.warn.push("the shape " + v.mesh.split(/[\\/]/).pop() + " is missing"); renderLookUI(); });
    });
  });

  // skeleton balls on every arm joint (pick a pair, see the centres)
  for (let i = 0; i < ARMJ; i++) {
    const ball = new THREE.Mesh(new THREE.SphereGeometry((RIG.jointR[Math.floor(i / 2)] || 16) * 0.5, 16, 10), matJoint);
    ball.userData.skel = true; ball.userData.pair = Math.floor(i / 2);
    jointGroups[i].parent.add(ball); pickMeshes.push(ball);
  }

  // the moving body: the waist's part, turned so it reads like the old body
  bodyGroup = new THREE.Group(); bodyGroup.name = "urdf_body";
  (urdfJ[8] ? jointGroups[8] : linkG[f.root]).add(bodyGroup);
  shoulderMount = urdfJ[9] ? jointGroups[9] : new THREE.Group();
  shrugAnchors.L = shrugAnchors.R = null;

  // arm handles: elbow ball on the elbow joint, wrist ball + hand at the tip
  ["L", "R"].forEach((side, arm) => {
    const b = arm * 4;
    const elbowBall = new THREE.Mesh(new THREE.SphereGeometry(12, 18, 12),
      new THREE.MeshBasicMaterial({ color: 0xff9944, depthTest: false }));
    elbowBall.userData.arm = arm; elbowBall.renderOrder = 19;
    jointGroups[b + 2].parent.add(elbowBall); elbowBalls.push(elbowBall);
    const fore = linkG[URDF_CFG.hands[side].link];
    const wrist = new THREE.Mesh(new THREE.SphereGeometry(14, 20, 14),
      new THREE.MeshBasicMaterial({ color: 0x3ecf8e, depthTest: false }));
    wrist.userData.arm = arm; wrist.renderOrder = 20;
    fore.add(wrist); wristBalls.push(wrist);
    const hand = new THREE.Group();
    const back = new THREE.Mesh(new THREE.BoxGeometry(34, 46, 5), new THREE.MeshStandardMaterial({ color: 0x7d8590 }));
    back.position.y = -30;
    const palm = new THREE.Mesh(new THREE.PlaneGeometry(30, 42), new THREE.MeshStandardMaterial({ color: 0xf2b8a0 }));
    palm.position.set(0, -30, 2.6);
    back.userData.skel = palm.userData.skel = true;
    hand.add(back, palm); fore.add(hand); palmMarks.push(hand);
    urdfTip[side] = { link: URDF_CFG.hands[side].link, fore, wrist, hand, mm: 0, fromMesh: false };
  });
  pairRingParents = [0, 2, 4, 6].map(i => [jointGroups[i].parent, jointGroups[i + 1].parent]);
  urdfOn = true;
  urdfSettle(base, warn);
  return true;
}

// Everything that depends on the zero pose: each joint's sense, where the
// shoulders sit, the tips, the body and hand frames, and the file's sizes.
function urdfSettle(base, warn) {
  const keep = pose;
  pose = RIG.zero.slice();
  base.position.set(0, 0, 0);
  urdfJ.forEach(b => { if (b) b.sign = 1; });
  applyPose(); robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const wq = (o) => o.getWorldQuaternion(new THREE.Quaternion());
  urdfJ.forEach((b, i) => {
    if (!b) return;
    const a = b.axis.clone().applyQuaternion(wq(jointGroups[i].parent));
    const dot = a.dot(rigRestAxis(i));
    b.quality = Math.abs(dot);
    b.sign = b.cfgSign === 1 || b.cfgSign === -1 ? b.cfgSign : (dot < 0 ? -1 : 1);
    if (b.cfgSign === "auto" && b.quality < 0.7 && i < ARMJ)
      warn.push(JOINT_LABELS[i] + " turns about a different axis than the simple shapes");
  });
  // shoulders where the simple shapes have them, so the camera, the torso
  // box and the old saved views still line up
  const mid = W(jointGroups[0].parent).add(W(jointGroups[4].parent)).multiplyScalar(0.5);
  base.position.set(-mid.x, (RIG.dims.shoulderY || 0) - mid.y, -mid.z);
  applyPose(); robot.updateMatrixWorld(true);
  ["L", "R"].forEach((side, arm) => urdfPlaceTip(side, arm));
  bodyGroup.quaternion.copy(wq(bodyGroup.parent).invert());
  robot.updateMatrixWorld(true);
  urdfLast.dims = urdfSizes();
  urdfLast.warn = warn;
  urdfLast.error = "";
  pose = keep;
  applyPose();
  renderLookUI();
}
// The tip: along the upper arm's line at zero, as far as the forearm part
// reaches (tip "mesh"), or the forearm length until that part has arrived.
function urdfPlaceTip(side, arm) {
  const t = urdfTip[side], b = arm * 4;
  const keep = pose;
  pose = RIG.zero.slice(); applyPose(); robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const sh = W(jointGroups[b].parent), el = W(jointGroups[b + 2].parent);
  const dirW = el.clone().sub(sh).normalize();
  const inv = t.fore.getWorldQuaternion(new THREE.Quaternion()).invert();
  const dir = dirW.clone().applyQuaternion(inv).normalize();
  const elLocal = t.fore.worldToLocal(el.clone());
  let mm = side === "L" ? RIG.dims.foreLenL : RIG.dims.foreLenR;
  let reach = -Infinity;
  if (((URDF_CFG.hands || {})[side] || {}).tip === "mesh") {
    t.fore.updateMatrixWorld(true);
    const toFore = new THREE.Matrix4().copy(t.fore.matrixWorld).invert();
    const v = new THREE.Vector3(), m4 = new THREE.Matrix4();
    t.fore.traverse(o => {
      if (!o.isMesh || !o.userData.urdfLink || o.userData.urdfLink !== t.link) return;
      const pos = o.geometry.attributes.position;
      m4.multiplyMatrices(toFore, o.matrixWorld);
      const step = Math.max(1, Math.floor(pos.count / 60000));
      for (let k = 0; k < pos.count; k += step) {
        v.fromBufferAttribute(pos, k).applyMatrix4(m4).sub(elLocal);
        reach = Math.max(reach, v.dot(dir));
      }
    });
  }
  t.fromMesh = reach > 1;
  if (t.fromMesh) mm = reach;
  t.mm = mm;
  t.wrist.position.copy(elLocal).addScaledVector(dir, mm);
  t.hand.position.copy(t.wrist.position);
  // the hand frame of the simple shapes at zero (its tilt chain + palmTurn),
  // with its -Y laid exactly along this forearm
  const q = new THREE.Quaternion();
  for (let k = b; k < b + 4; k++) q.multiply(jointTiltQuat(k));
  q.multiply(new THREE.Quaternion().setFromAxisAngle(_AXVEC.y, THREE.MathUtils.degToRad(RIG.palmTurn[arm] || 0)));
  const local = inv.clone().multiply(q);
  const down = new THREE.Vector3(0, -1, 0).applyQuaternion(local);
  t.hand.quaternion.copy(new THREE.Quaternion().setFromUnitVectors(down, dir).multiply(local));
  palmCache.clear();
  pose = keep; applyPose();
}
function urdfMeshArrived(link) {
  ["L", "R"].forEach((side, arm) => {
    if (!urdfTip[side] || urdfTip[side].link !== link) return;
    urdfPlaceTip(side, arm);
    urdfLast.dims = urdfSizes();
    if (lookKind() === "urdf") { urdfUseSizes(); renderRigUI(); }
    renderLookUI();
  });
}
// the sizes this file gives the Rig setup (urdf_view.json "sizes")
function urdfSizes() {
  if (!urdfOn) return urdfLast.dims;
  const keep = pose;
  pose = RIG.zero.slice(); applyPose(); robot.updateMatrixWorld(true);
  const at = (n) => {
    if (/^tip:/.test(n)) return wristBalls[n.slice(4) === "L" ? 0 : 1].getWorldPosition(new THREE.Vector3());
    const i = JOINT_NAMES.indexOf(n);
    return i >= 0 && jointGroups[i] ? jointGroups[i].parent.getWorldPosition(new THREE.Vector3()) : null;
  };
  const out = {};
  Object.entries(URDF_CFG.sizes || {}).forEach(([k, s]) => {
    const a = at(s.from), b = at(s.to);
    if (a && b) out[k] = Math.round(a.distanceTo(b) * (s.half ? 0.5 : 1) * 10) / 10;
  });
  pose = keep; applyPose();
  return out;
}
// IK reach guesses and the readouts use RIG.dims: while the URDF is shown
// they are the file's own. Your own sizes stay in RIG.view.custom.
function urdfUseSizes() {
  const d = urdfLast.dims || {};
  let changed = false;
  Object.entries(d).forEach(([k, v]) => { if (RIG.dims[k] !== v) { RIG.dims[k] = v; changed = true; } });
  RIG.view.urdfDims = { ...d };
  if (changed) saveRig();
}

function urdfApplyPose() {
  for (let i = 0; i < NJ; i++) {
    const b = urdfJ[i], g = jointGroups[i];
    if (!b || !g) continue;
    g.quaternion.setFromAxisAngle(b.axis, b.sign * THREE.MathUtils.degToRad(jointDelta(i)) + b.off);
  }
}
// a joint's turning axis in its parent frame, its sense folded in (gizmo rings)
function urdfAxisVec(i) {
  const b = urdfJ[i];
  return b ? b.axis.clone().multiplyScalar(b.sign) : _AXVEC[RIG.axis[i]].clone();
}

// ---- the choice ------------------------------------------------------------
function urdfDimsOf(keys, src) {
  const o = {};
  keys.forEach(k => { if (Number.isFinite(src[k])) o[k] = src[k]; });
  return o;
}
function sameDims(a, b) {
  return Object.keys(a || {}).every(k => Math.abs((a[k] || 0) - ((b || {})[k] || 0)) < 0.05);
}
async function urdfRefreshModels() {
  const known = ((URDF_CFG && URDF_CFG.models) || []).slice();
  let found = null;
  try {
    const r = await fetch("/api/list?kind=models&deep=1").then(r => r.json());
    found = (r.files || []).filter(f => /\.urdf$/i.test(f));
  } catch (e) { /* offline list: offer what the data names */ }
  urdfModelList = (found ? known.filter(m => found.includes(m.path)) : known)
    .concat((found || []).filter(p => !known.some(m => m.path === p)).map(p => ({ path: p, label: p.split("/").pop() })));
  renderLookUI();
}
function renderLookUI() {
  const sel = $("lookSel"), msel = $("lookModel"), stat = $("lookStat");
  if (!sel || !URDF_CFG) return;
  const v = RIG.view || {};
  sel.innerHTML = "";
  URDF_CFG.looks.forEach(l => {
    const o = document.createElement("option");
    o.value = l.id; o.textContent = l.label;
    sel.appendChild(o);
  });
  sel.value = lookOf(v.look) ? v.look : URDF_CFG.default;
  msel.innerHTML = "";
  urdfModelList.forEach(m => {
    const o = document.createElement("option");
    o.value = m.path; o.textContent = m.label;
    msel.appendChild(o);
  });
  if (v.model) msel.value = v.model;
  msel.hidden = lookKind() !== "urdf" || urdfModelList.length < 2;
  const tech = $("lookTech");
  if (lookKind() !== "urdf") { stat.textContent = ""; tech.textContent = ""; return; }
  stat.textContent = urdfLast.error ? "Cannot show the CAD model: " + urdfLast.error + ". The simple shapes are shown."
    : !urdfOn ? "Opening the CAD model…"
    : urdfLast.warn.length ? urdfLast.warn.join("; ") : "CAD model at its real sizes.";
  tech.textContent = urdfOn ? (v.model + " · " + urdfJ.map((b, i) => b ? JOINT_NAMES[i] + "→" + b.name +
    (b.sign < 0 ? " (-)" : "") + (b.quality < 0.7 ? " (axis " + b.quality.toFixed(2) + ")" : "") : JOINT_NAMES[i] + "→none").join(", ")) : (v.model || "");
}
function urdfPickModel(path) {
  RIG.view.model = path;
  urdfLast.error = "";
  setLook(RIG.view.look, true);
}
// Pick a look. Into the URDF: your current sizes are kept first (unless they
// are the URDF's own). Back to the shapes: ask which sizes to use.
async function setLook(id, force) {
  const l = lookOf(id);
  if (!l) return;
  const v = RIG.view;
  const wasUrdf = lookKind() === "urdf";
  if (l.kind === "urdf") {
    if (wasUrdf && !force) return;
    if (!v.model) v.model = (urdfModelList[0] || (URDF_CFG.models || [])[0] || {}).path || "";
    const f = await urdfLoad(v.model);
    if (f.error) {
      urdfLast.error = f.error;
      $("lookSel").value = v.look;
      $("lookStat").textContent = "Cannot show the CAD model: " + f.error + ".";
      notice($("lookStat").textContent);
      return;
    }
    const keys = Object.keys(URDF_CFG.sizes || {});
    const mine = urdfDimsOf(keys, RIG.dims);
    if (!wasUrdf && (v.sizes === "custom" || !sameDims(mine, v.urdfDims))) v.custom = mine;
    v.look = id;
    rigChanged();
    if (urdfOn) { urdfUseSizes(); renderRigUI(); }
    return;
  }
  if (!wasUrdf) { v.look = id; rigChanged(); return; }
  const pick = await askLookSizes();
  if (!pick) { renderLookUI(); return; }
  const keys = Object.keys(URDF_CFG.sizes || {});
  if (pick === "urdf") Object.assign(RIG.dims, urdfDimsOf(keys, urdfLast.dims || {}));
  else Object.assign(RIG.dims, urdfDimsOf(keys, v.custom || {}));
  v.sizes = pick;
  v.look = id;
  rigChanged();
}
function lookSizeText(d) {
  if (!d || !Object.keys(d).length) return "";
  const n = (k) => Number.isFinite(d[k]) ? Math.round(d[k]) : "?";
  return `upper arm ${n("upperLenL")}/${n("upperLenR")} mm, forearm ${n("foreLenL")}/${n("foreLenR")} mm, shoulders ${n("shoulderX")} mm from the middle`;
}
// the question on the way back: resolves "urdf", "custom", or null (stay)
function askLookSizes() {
  const dlg = $("lookAsk");
  const v = RIG.view;
  $("lookAskUrdf").textContent = lookSizeText(urdfLast.dims);
  $("lookAskMine").textContent = v.custom ? lookSizeText(v.custom) : "none kept yet: the URDF sizes, then change them in Rig setup";
  return new Promise(res => {
    const done = (x) => { dlg.close ? dlg.close() : dlg.removeAttribute("open"); res(x); };
    $("lookUseUrdf").onclick = () => done("urdf");
    $("lookUseMine").onclick = () => done("custom");
    $("lookStay").onclick = () => done(null);
    dlg.oncancel = (e) => { e.preventDefault(); done(null); };
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  });
}
