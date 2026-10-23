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
let urdfTip = {};                  // "L"/"R" -> {link, tipLocal, mm, fromMesh}
let urdfArm = [];                  // per arm: its 4 URDF joints, shoulder first
let urdfLast = { dims: null, warn: [], error: "", fit: [null, null] };  // what the last build found
let urdfModelList = [];            // [{path, label}] offered in the box
const urdfGeo = {};                // mesh url -> BufferGeometry (kept across rebuilds)
let urdfBuildGen = 0;              // a mesh arriving after a rebuild is dropped
const urdfMissing = new Set();     // mesh names that were not found (said, not fetched again)

function urdfConfigReady(j) {
  URDF_CFG = j;
  viewFloor();                 // config can arrive after the simple shapes were built
  renderLookUI();
  urdfRefreshModels();
  if (lookKind() === "urdf") buildRobot();      // a saved URDF look waits for this
}
fetch("urdf_view.json").then(r => r.json()).then(urdfConfigReady).catch(() => {});

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
// One download per file: a rebuild while a big part is still coming joins
// the same download. Before, it started another and dropped the first, and
// the right forearm of the real nong (tens of MB) never arrived in time (PC
// run 2026-10-23: its tip fell back, its elbow was never fitted).
const urdfLoading = {};            // url -> [[cb, fail], ...] waiting for it
function urdfMesh(urls, cb, fail) {
  const u = urls[0];
  if (!u) { fail(); return; }
  if (urdfGeo[u]) { cb(urdfGeo[u]); return; }
  const next = () => urdfMesh(urls.slice(1), cb, fail);
  if (urdfLoading[u]) { urdfLoading[u].push([cb, next]); return; }
  urdfLoading[u] = [[cb, next]];
  const done = (geo) => {
    const w = urdfLoading[u] || [];
    delete urdfLoading[u];
    if (geo) urdfGeo[u] = geo;
    w.forEach(([ok, no]) => geo ? ok(geo) : no());
  };
  stlLoader.load(u, done, undefined, () => done(null));
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
  const c = rigChain(i - i % 4, [0, 0, 0, 0]);
  return _AXVEC[RIG.axis[i]].clone().applyQuaternion(c.pre[i % 4]).normalize();
}
// The shapes' arm chain for joint deltas d (deg, d[k] = joint b+k), in the
// body's frame: pre[k] = the frame joint b+k turns in (its tilt included),
// at[c] = the frame after the c-th joint from the body out (RIG.order).
// The same as applyPose builds, without touching the scene.
function rigChain(b, d) {
  const q = new THREE.Quaternion(), r = new THREE.Quaternion(), pre = [], at = [];
  RIG.order[b / 4].forEach((j, c) => {
    q.multiply(jointTiltQuat(j));
    pre[j - b] = q.clone();
    q.multiply(r.setFromAxisAngle(_AXVEC[RIG.axis[j]], THREE.MathUtils.degToRad(d[j - b]))).multiply(jointAfterQuat(j));
    at[c] = q.clone();
  });
  return { pre, at };
}
// the drawn hand on the CAD model: shown or not (RIG.view.handMarks, else the
// data's "handMarks"); the CAD hand already shows the palm. Facing still works.
function urdfHandMarksOn() {
  const v = RIG.view || {};
  return typeof v.handMarks === "boolean" ? v.handMarks : (URDF_CFG || {}).handMarks !== false;
}
function urdfSetHandMarks(on) {
  RIG.view.handMarks = !!on;
  saveRig();
  if (urdfOn) palmMarks.forEach(h => h.children.forEach(c => { if (c.isMesh) c.visible = !!on; }));
  renderLookUI();
}
// ---- the floor grid (user 2026-10-23: "can the grid be hidden, and the box
// lifted above it") -----------------------------------------------------------
// Shown or not: RIG.view.grid (else the data's floor.show). Its height: the
// shapes' floor (floor.shapesY), or on the CAD model the bottom of the file's
// root part + floor.gapMm (floor.cad "root"), so the base box stands on it.
// Only the grid moves: the robot and every position Studio sends stay put.
let urdfRootLink = "";
function viewFloorCfg() { return (URDF_CFG && URDF_CFG.floor) || {}; }
function viewGridOn() {
  const v = RIG.view || {};
  return typeof v.grid === "boolean" ? v.grid : viewFloorCfg().show !== false;
}
function viewFloor() {
  if (typeof grid === "undefined") return;
  const cfg = viewFloorCfg();
  grid.visible = viewGridOn();
  let y = Number.isFinite(cfg.shapesY) ? cfg.shapesY : -250;
  if (urdfRootLink && cfg.cad === "root" && robot) {
    robot.updateMatrixWorld(true);
    const box = new THREE.Box3();
    robot.traverse(o => { if (o.isMesh && o.userData.urdfLink === urdfRootLink) box.expandByObject(o); });
    if (!box.isEmpty()) y = box.min.y - (+cfg.gapMm || 0);
  }
  grid.position.y = y;
}
function viewSetGrid(on) {
  RIG.view.grid = !!on;
  saveRig();
  viewFloor();
}
function urdfJointCfg(i) { return ((URDF_CFG && URDF_CFG.joints) || {})[JOINT_NAMES[i]] || {}; }

// Builds the file's tree into `root` and points every handle into it.
// Returns false (nothing built) when the look is not URDF or not ready yet.
function urdfBuildInto(root) {
  urdfOn = false;
  urdfRootLink = "";
  viewFloor();
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
  urdfRootLink = f.root;
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
    let depth = 0;
    for (let n = hit.j.child; jointOf[n]; n = jointOf[n].j.parent) depth++;
    urdfJ[i] = { name: hit.j.name, axis: new THREE.Vector3(...hit.j.axis).normalize(), mov: hit.mov, org: hit.org,
                 depth, named: i, sign: 1, off: 0, quality: 1, cfgSign: c.sign, cfgOff: c.offsetDeg };
  }
  // each arm's four joints in the order they hang (shoulder pair, then elbow)
  urdfArm = [0, 4].map(b => urdfJ.slice(b, b + 4).slice().sort((x, y) => x.depth - y.depth));
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
      else if (urdfMissing.has(f.path + "|" + v.mesh)) warn.push("the shape " + v.mesh.split(/[\\/]/).pop() + " is missing");
      else urdfMesh(urdfMeshUrls(v.mesh, f.path), geo => {
        if (gen !== urdfBuildGen || holder.parent !== linkG[name]) return;   // a rebuild came first
        put(geo, v.scale.map(s => s * U));
        if (name === urdfRootLink) viewFloor();
        urdfMeshArrived(name);
      }, () => {
        urdfMissing.add(f.path + "|" + v.mesh);
        if (gen === urdfBuildGen) { urdfLast.warn.push("the shape " + v.mesh.split(/[\\/]/).pop() + " is missing"); renderLookUI(); }
      });
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
    urdfArm[arm][2].org.add(elbowBall); elbowBalls.push(elbowBall);
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
    back.visible = palm.visible = urdfHandMarksOn();
    urdfTip[side] = { link: URDF_CFG.hands[side].link, fore, wrist, hand, mm: 0, fromMesh: false, tipLocal: null };
  });
  urdfOn = true;
  urdfSettle(base, warn);         // may re-pair joints (the fit), so the rings come after
  viewFloor();
  pairRingParents = [0, 2, 4, 6].map(i => [jointGroups[i].parent, jointGroups[i + 1].parent]);
  return true;
}

// Everything that depends on the zero pose: each joint's sense and zero, where
// the shoulders sit, the tips, the body and hand frames, and the file's sizes.
function urdfSettle(base, warn) {
  const keep = pose;
  pose = RIG.zero.slice();
  base.position.set(0, 0, 0);
  const num = (v) => typeof v === "number" && Number.isFinite(v);
  urdfJ.forEach(b => { if (b) { b.sign = 1; b.off = num(b.cfgOff) ? THREE.MathUtils.degToRad(b.cfgOff) : 0; } });
  applyPose(); robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const wq = (o) => o.getWorldQuaternion(new THREE.Quaternion());
  const fitOn = (URDF_CFG.fit || {}).on !== false;
  urdfJ.forEach((b, i) => {
    if (!b) return;
    const a = b.axis.clone().applyQuaternion(wq(b.org));
    const dot = a.dot(rigRestAxis(i));
    b.quality = Math.abs(dot);
    b.sign = b.cfgSign === 1 || b.cfgSign === -1 ? b.cfgSign : (dot < 0 ? -1 : 1);
    if (b.cfgSign === "auto" && b.quality < 0.7 && (i >= ARMJ || !fitOn))
      warn.push(JOINT_LABELS[i] + " turns about a different axis than the simple shapes");
  });
  // shoulders where the simple shapes have them, so the camera, the torso
  // box and the old saved views still line up
  // (the shapes' own middle: RIG.mount moves each shoulder off the symmetric spot)
  const mid = W(urdfArm[0][0].org).add(W(urdfArm[1][0].org)).multiplyScalar(0.5);
  const mm = new THREE.Vector3().fromArray(RIG.mount.L).add(new THREE.Vector3().fromArray(RIG.mount.R)).multiplyScalar(0.5);
  base.position.set(mm.x - mid.x, (RIG.dims.shoulderY || 0) + mm.y - mid.y, mm.z - mid.z);
  applyPose(); robot.updateMatrixWorld(true);
  urdfLast.fit = [null, null];
  ["L", "R"].forEach((side, arm) => {
    urdfMeshTip(side, arm);
    if (fitOn) urdfFitArm(arm, warn);
    urdfPlaceHand(side, arm);
  });
  bodyGroup.quaternion.copy(wq(bodyGroup.parent).invert());
  robot.updateMatrixWorld(true);
  urdfLast.dims = urdfSizes();
  urdfLast.warn = warn;
  urdfLast.error = "";
  pose = keep;
  applyPose();
  renderLookUI();
}
// The hand's tip from the forearm part itself (tip "mesh"): the middle of its
// far end from the elbow, and how far the part reaches that way. In the
// forearm's own frame, so it holds at any pose.
function urdfMeshTip(side, arm) {
  const t = urdfTip[side];
  t.fromMesh = false; t.tipLocal = null;
  if (((URDF_CFG.hands || {})[side] || {}).tip !== "mesh") return;
  robot.updateMatrixWorld(true);
  const el = t.fore.worldToLocal(urdfArm[arm][2].org.getWorldPosition(new THREE.Vector3()));
  const toFore = new THREE.Matrix4().copy(t.fore.matrixWorld).invert();
  const pts = [], m4 = new THREE.Matrix4();
  t.fore.traverse(o => {
    if (!o.isMesh || o.userData.urdfLink !== t.link) return;
    const pos = o.geometry.attributes.position;
    m4.multiplyMatrices(toFore, o.matrixWorld);
    const step = Math.max(1, Math.floor(pos.count / 60000));
    for (let k = 0; k < pos.count; k += step) pts.push(new THREE.Vector3().fromBufferAttribute(pos, k).applyMatrix4(m4).sub(el));
  });
  if (!pts.length) return;
  const far = Math.max(...pts.map(v => v.length()));
  if (far < 1) return;
  // each corner once: an STL repeats a vertex in every triangle it touches
  const end = new THREE.Vector3(), seen = new Set(); let n = 0;
  pts.forEach(v => {
    const key = v.toArray().map(x => Math.round(x * 100)).join();
    if (v.length() > far * 0.97 && !seen.has(key)) { seen.add(key); end.add(v); n++; }
  });
  const dir = end.divideScalar(n).normalize();
  t.mm = Math.max(...pts.map(v => v.dot(dir)));
  t.tipLocal = el.clone().addScaledVector(dir, t.mm);
  t.fromMesh = true;
  t.wrist.position.copy(t.tipLocal);
  t.palmN = urdfMeshPalm(side, pts, dir, t.mm);
}
// The CAD hand's own plane (user 2026-10-23: "why is the palm tilted, not in
// the plane of the hand"): the drawn hand turned by RIG.palmTurn sat across
// the CAD hand. The far part of the forearm mesh (urdf_view.json palm.from of
// its length) is spread wide one way across the forearm and thin the other:
// the thin way is the palm's normal. Not flat enough (palm.flat) = no plane.
function urdfMeshPalm(side, pts, dir, mm) {
  const cfg = URDF_CFG.palm || {};
  if (((URDF_CFG.hands || {})[side] || {}).palm !== "mesh") return null;
  const u = new THREE.Vector3(1, 0, 0);
  if (Math.abs(u.dot(dir)) > 0.9) u.set(0, 1, 0);
  u.addScaledVector(dir, -u.dot(dir)).normalize();
  const w = dir.clone().cross(u);
  let n = 0, su = 0, sw = 0, suu = 0, sww = 0, suw = 0;
  const seen = new Set();
  pts.forEach(v => {
    if (v.dot(dir) < mm * (cfg.from || 0.6)) return;
    const key = v.toArray().map(x => Math.round(x * 100)).join();
    if (seen.has(key)) return;
    seen.add(key);
    const a = v.dot(u), b = v.dot(w);
    n++; su += a; sw += b; suu += a * a; sww += b * b; suw += a * b;
  });
  if (n < 4) return null;
  const cuu = suu / n - (su / n) ** 2, cww = sww / n - (sw / n) ** 2, cuw = suw / n - (su / n) * (sw / n);
  // the 2x2 spread across the forearm: its thin axis is the palm normal
  const tr = cuu + cww, det = cuu * cww - cuw * cuw, gap = Math.sqrt(Math.max(0, tr * tr / 4 - det));
  const lo = tr / 2 - gap, hi = tr / 2 + gap;
  if (!(hi > 0) || lo / hi > (cfg.flat || 0.35)) return null;
  const th = 0.5 * Math.atan2(2 * cuw, cuu - cww);          // the wide axis
  const wide = u.clone().multiplyScalar(Math.cos(th)).addScaledVector(w, Math.sin(th));
  return dir.clone().cross(wide).normalize();
}
// Without a forearm part: the forearm length along the shapes' forearm at
// zero. Then the hand frame of the shapes at zero (tilt chain + palmTurn),
// its -Y laid exactly along this forearm.
function urdfPlaceHand(side, arm) {
  const t = urdfTip[side], b = arm * 4;
  const keep = pose;
  pose = RIG.zero.slice(); applyPose(); robot.updateMatrixWorld(true);
  const inv = t.fore.getWorldQuaternion(new THREE.Quaternion()).invert();
  const el = t.fore.worldToLocal(urdfArm[arm][2].org.getWorldPosition(new THREE.Vector3()));
  const q = rigChain(b, [0, 0, 0, 0]).at[3];
  if (!t.fromMesh) {
    t.mm = side === "L" ? RIG.dims.foreLenL : RIG.dims.foreLenR;
    const dirW = new THREE.Vector3(0, -1, 0).applyQuaternion(q);
    t.tipLocal = el.clone().addScaledVector(dirW.applyQuaternion(inv), t.mm);
  }
  t.wrist.position.copy(t.tipLocal);
  t.hand.position.copy(t.tipLocal);
  const dir = t.tipLocal.clone().sub(el).normalize();
  q.multiply(new THREE.Quaternion().setFromAxisAngle(_AXVEC.y, THREE.MathUtils.degToRad(RIG.palmTurn[arm] || 0)));
  const local = inv.clone().multiply(q);
  const down = new THREE.Vector3(0, -1, 0).applyQuaternion(local);
  t.hand.quaternion.copy(new THREE.Quaternion().setFromUnitVectors(down, dir).multiply(local));
  if (t.fromMesh && t.palmN) {
    // turned about the forearm into the CAD hand's plane; of its two faces,
    // the one nearest the Rig setup's palm (the mesh cannot say which is which)
    const z = new THREE.Vector3(0, 0, 1).applyQuaternion(t.hand.quaternion);
    const n = t.palmN.clone().multiplyScalar(t.palmN.dot(z) < 0 ? -1 : 1);
    const zf = z.addScaledVector(dir, -z.dot(dir)).normalize();
    const phi = Math.atan2(zf.clone().cross(n).dot(dir), zf.dot(n));
    if (Number.isFinite(phi)) t.hand.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(dir, phi));
  }
  palmCache.clear();
  pose = keep; applyPose();
}

// ---- which URDF joint is which Studio joint, its sense and its zero --------
// A CAD export names and zeroes its joints its own way: the real nong's file
// turns its first shoulder joint about the front axis where the shapes turn
// theirs about a tilted side axis, and its zero is the pose it was drawn in
// (PC run 2026-10-23: every arm axis "perpendicular"). So, per arm, the
// pairing inside each joint pair, the sense and the zero are FITTED: the
// upper arm and the forearm must point where the shapes point them over
// many poses. urdf_view.json "fit" turns it off; a number in "sign" or
// "offsetDeg" is kept as given. The story is in check_urdf_look.
const _fQ = new THREE.Quaternion(), _fV = new THREE.Vector3();
function urdfArmModel(arm) {
  const ch = urdfArm[arm];
  pose = RIG.zero.slice(); applyPose();
  ch.forEach(c => c.mov.quaternion.identity());
  robot.updateMatrixWorld(true);
  const Wq = ch.map(c => c.org.getWorldQuaternion(new THREE.Quaternion()));
  const P = ch.map(c => c.org.getWorldPosition(new THREE.Vector3()));
  const C = [null], T = [null];
  for (let k = 1; k < 4; k++) {
    const inv = Wq[k - 1].clone().invert();
    C[k] = inv.clone().multiply(Wq[k]);
    T[k] = P[k].clone().sub(P[k - 1]).applyQuaternion(inv);
  }
  const tipW = wristBalls[arm].getWorldPosition(new THREE.Vector3());
  const tipT = tipW.sub(P[3]).applyQuaternion(Wq[3].clone().invert());
  applyPose();
  return { W1: Wq[0], C, T, tipT, axes: ch.map(c => c.axis) };
}
// upper-arm and forearm directions for chain angles th (rad); fore only if asked
function urdfArmDirs(m, th, fore) {
  const M = m.W1.clone().multiply(_fQ.setFromAxisAngle(m.axes[0], th[0]));
  const P2 = m.T[1].clone().applyQuaternion(M);
  M.multiply(m.C[1]).multiply(_fQ.setFromAxisAngle(m.axes[1], th[1]));
  const P3 = P2.add(m.T[2].clone().applyQuaternion(M));
  const up = P3.clone().normalize(), qu = M.clone();
  if (!fore) return { up, qu };
  M.multiply(m.C[2]).multiply(_fQ.setFromAxisAngle(m.axes[2], th[2]));
  const P4 = P3.clone().add(m.T[3].clone().applyQuaternion(M));
  M.multiply(m.C[3]).multiply(_fQ.setFromAxisAngle(m.axes[3], th[3]));
  const tip = P4.add(m.tipT.clone().applyQuaternion(M));
  return { up, qu, fore: tip.sub(P3).normalize(), qf: M };
}
// the shapes' upper-arm and forearm directions for joint deltas d (deg)
function rigArmDirs(b, d) {
  const c = rigChain(b, d), qu = c.at[1], qf = c.at[3];
  return { up: new THREE.Vector3(0, -1, 0).applyQuaternion(qu), qu, fore: new THREE.Vector3(0, -1, 0).applyQuaternion(qf), qf };
}
function urdfFitArm(arm, warn) {
  const cfg = URDF_CFG.fit || {}, b = arm * 4, ch = urdfArm[arm];
  const m = urdfArmModel(arm);
  const withFore = urdfTip[arm ? "R" : "L"].fromMesh;
  let seed = 4801 + arm;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const S = [];
  for (let n = 0; n < (cfg.samples || 12); n++) {
    const d = [0, 1, 2, 3].map(k => {
      const j = b + k, v = RIG.min[j] + (RIG.max[j] - RIG.min[j]) * rnd();
      return (v - RIG.zero[j]) * jdir(j);
    });
    S.push({ d, ...rigArmDirs(b, d) });
  }
  // HOME is the reference for how each part TURNS (not only where it points):
  // from home to every pose the upper arm and forearm must turn alike. That
  // pins the roll about a bone, which directions alone leave free.
  const dH = [0, 1, 2, 3].map(k => (RIG.home[b + k] - RIG.zero[b + k]) * jdir(b + k));
  const H = { d: dH, ...rigArmDirs(b, dH) };
  S.forEach(x => {
    x.tu = x.qu.clone().multiply(H.qu.clone().invert());
    x.tf = x.qf.clone().multiply(H.qf.clone().invert());
  });
  // how much the turn counts against where the bones point (true = 1): a
  // CAD unlike the rig pays for a full weight in pointing (real nong
  // 2026-10-23: right arm 20 deg at 1, 15 deg at 0.5)
  const fw = cfg.frames === false ? 0 : cfg.frames === true || cfg.frames == null ? 1 : +cfg.frames || 0;
  const frames = fw > 0;
  const qAng = (a, c) => 2 * Math.acos(Math.min(1, Math.abs(a.dot(c))));
  const D2R = Math.PI / 180, num = (v) => typeof v === "number" && Number.isFinite(v);
  // studio joint of chain slot k, per pairing choice
  const slot = (swapSh, swapEl) => [swapSh ? b + 1 : b, swapSh ? b : b + 1, swapEl ? b + 3 : b + 2, swapEl ? b + 2 : b + 3];
  const cost = (map, sg, of, fore, dirsOnly) => {
    let c = 0;
    const th = [0, 0, 0, 0];
    const at = (x) => { for (let k = 0; k < 4; k++) th[k] = sg[k] * x.d[map[k] - b] * D2R + of[k]; return urdfArmDirs(m, th, fore); };
    const h = frames && !dirsOnly ? at(H) : null;
    const hu = h && h.qu.clone().invert(), hf = h && fore && h.qf.clone().invert();
    for (const s of S) {
      const r = at(s);
      c += r.up.angleTo(s.up) + (fore ? r.fore.angleTo(s.fore) : 0);
      if (h) c += fw * (qAng(r.qu.multiply(hu), s.tu) + (fore ? qAng(r.qf.multiply(hf), s.tf) : 0));
    }
    c /= (h ? 1 + fw : 1);
    // a universal joint has twin answers (one zero turned half round, the
    // other sense flipped) that move the arm the same: a hair's weight on
    // the zeros picks the one nearest the file's own zero, every time
    const tie = of.reduce((a, o) => a + Math.abs(Math.atan2(Math.sin(o), Math.cos(o))), 0) * 1e-4;
    return c / S.length / (fore ? 2 : 1) / D2R + tie;
  };
  // what the data fixes: a numeric sign or offset of the Studio joint
  const fixedSign = (j) => { const v = urdfJointCfg(j).sign; return v === 1 || v === -1 ? [v] : [1, -1]; };
  const fixedOff = (j) => { const v = urdfJointCfg(j).offsetDeg; return num(v) ? v * D2R : null; };
  // fit.anchor "home": at HOME every joint sits as the CAD was drawn (zero =
  // home), so only which-is-which and the sense are fitted. Pointing alone
  // leaves a twist free: the real nong's shoulder blocks came out turned
  // 45-135 deg, the two sides no longer mirror images (user 2026-10-23).
  const anchored = cfg.anchor === "home";
  const homeOff = (j, s) => -s * dH[j - b] * D2R;
  const swaps = cfg.swap === false ? [false] : [false, true];
  const grid = cfg.gridDeg || 15;
  // search one pair (k0 = 0 shoulder, 2 elbow) with the other fixed
  const best = { map: slot(false, false), sg: [1, 1, 1, 1], of: [0, 0, 0, 0], c: Infinity };
  const searchPair = (k0, fore) => {
    let top = { c: Infinity };
    for (const sw of swaps) {
      const map = k0 === 0 ? slot(sw, best.map[2] === b + 3) : slot(best.map[0] === b + 1, sw);
      for (const s0 of fixedSign(map[k0])) for (const s1 of fixedSign(map[k0 + 1])) {
        const sg = best.sg.slice(); sg[k0] = s0; sg[k0 + 1] = s1;
        let f0 = fixedOff(map[k0]), f1 = fixedOff(map[k0 + 1]);
        const free0 = f0 === null && !anchored, free1 = f1 === null && !anchored;
        if (anchored) { if (f0 === null) f0 = homeOff(map[k0], s0); if (f1 === null) f1 = homeOff(map[k0 + 1], s1); }
        const g = (f) => f !== null ? [f] : Array.from({ length: Math.round(360 / grid) }, (_, i) => (i * grid - 180) * D2R);
        for (const o0 of g(f0)) for (const o1 of g(f1)) {
          const of = best.of.slice(); of[k0] = o0; of[k0 + 1] = o1;
          const c = cost(map, sg, of, fore);
          if (c < top.c) top = { map, sg, of, c, free: [free0, free1] };
        }
      }
    }
    // polish the two zeros, down to 0.01 degree
    for (const st of [5, 1, 0.25, 0.05, 0.01]) for (let it = 0; it < 8; it++) {
      let moved = false;
      for (let k = 0; k < 2; k++) {
        if (!top.free[k]) continue;
        for (const dd of [-st, st]) {
          const of = top.of.slice(); of[k0 + k] += dd * D2R;
          const c = cost(top.map, top.sg, of, fore);
          if (c < top.c - 1e-9) { top = { ...top, of, c }; moved = true; }
        }
      }
      if (!moved) break;
    }
    Object.assign(best, { map: top.map, sg: top.sg, of: top.of, c: top.c });
  };
  searchPair(0, false);
  if (withFore) {
    searchPair(2, true);
    // then all four zeros together: the shoulder was fitted before the forearm was seen
    let c0 = cost(best.map, best.sg, best.of, true);
    const free = [0, 1, 2, 3].map(k => fixedOff(best.map[k]) === null && !anchored);
    for (const st of [2, 0.5, 0.1, 0.02]) for (let it = 0; it < 10; it++) {
      let moved = false;
      for (let k = 0; k < 4; k++) {
        if (!free[k]) continue;
        for (const dd of [-st, st]) {
          const of = best.of.slice(); of[k] += dd * D2R;
          const c = cost(best.map, best.sg, of, true);
          if (c < c0 - 1e-9) { best.of = of; c0 = c; moved = true; }
        }
      }
      if (!moved) break;
    }
  }
  // how far off it still points (directions only: what the eye sees)
  const upDeg = cost(best.map, best.sg, best.of, false, true);
  const allDeg = withFore ? cost(best.map, best.sg, best.of, true, true) : upDeg;
  // hand the fitted pairing, senses and zeros to the Studio joints
  const fitted = withFore ? 4 : 2;
  const entries = ch.slice();
  for (let k = 0; k < fitted; k++) {
    const j = best.map[k], e = entries[k];
    urdfJ[j] = Object.assign(e, { sign: best.sg[k], off: best.of[k], fitted: true });
    jointGroups[j] = e.mov;
  }
  // Missing/loading forearm meshes skip its fit, but HOME must still leave
  // every CAD joint as drawn. Explicit offsets remain authoritative.
  for (let k = fitted; k < 4; k++) {
    const e = entries[k], j = e.named;
    const choices = fixedSign(j), sign = choices.length === 1 ? choices[0] : e.sign, off = fixedOff(j);
    urdfJ[j] = Object.assign(e, { sign, off: off !== null ? off : anchored ? homeOff(j, sign) : 0, fitted: false });
    jointGroups[j] = e.mov;
  }
  urdfLast.fit[arm] = { deg: Math.round(allDeg * 10) / 10, upDeg: Math.round(upDeg * 10) / 10,
                        // swapped = against the file's own names
                        swapSh: urdfJ[b].named !== b, swapEl: withFore && urdfJ[b + 2].named !== b + 2, fore: withFore };
  const side = arm ? "right" : "left";
  if (allDeg > (cfg.warnDeg || 5))
    warn.push("the " + side + " arm of the CAD model points up to " + Math.round(allDeg) + "° away from the simple shapes");
  pose = RIG.zero.slice(); applyPose(); robot.updateMatrixWorld(true);
}
// a forearm part arrived: tip, fit and hand all depend on it, so settle again
// (a rebuild: the cached meshes come back at once)
function urdfMeshArrived(link) {
  if (!urdfOn) return;             // still building (a cached mesh): urdfSettle measures it
  if (!["L", "R"].some(side => urdfTip[side] && urdfTip[side].link === link)) return;
  buildRobot();
  if (lookKind() === "urdf") { urdfUseSizes(); renderRigUI(); }
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
  if (typeof renderRigCadUI === "function") renderRigCadUI();
  if ($("viewGrid")) $("viewGrid").checked = viewGridOn();
  if ($("lookHandMarks")) { $("lookHandMarks").checked = urdfHandMarksOn(); $("lookHandMarksRow").hidden = !urdfOn; }
  if (lookKind() !== "urdf") { stat.textContent = ""; tech.textContent = ""; return; }
  stat.textContent = urdfLast.error ? "Cannot show the CAD model: " + urdfLast.error + ". The simple shapes are shown."
    : !urdfOn ? "Opening the CAD model…"
    : urdfLast.warn.length ? urdfLast.warn.join("; ") : "CAD model at its real sizes.";
  const fitTxt = (urdfLast.fit || []).map((f, a) => f ? (a ? " R" : " L") + " arm fit " + f.deg + "°" +
    (f.swapSh ? " shoulder pair swapped" : "") + (f.swapEl ? " elbow pair swapped" : "") + (f.fore ? "" : " (upper arm only)") : "").join(",");
  tech.textContent = urdfOn ? (v.model + " ·" + fitTxt + " · " + urdfJ.map((b, i) => b ? JOINT_NAMES[i] + "→" + b.name +
    (b.sign < 0 ? " (-)" : "") + (b.off ? " " + Math.round(THREE.MathUtils.radToDeg(b.off)) + "°" : "") + (b.quality < 0.7 && !b.fitted ? " (axis " + b.quality.toFixed(2) + ")" : "") : JOINT_NAMES[i] + "→none").join(", ")) : (v.model || "");
}
// another file: opened first, so a broken one never replaces what is shown
async function urdfPickModel(path) {
  const f = await urdfLoad(path);
  if (f.error) {
    $("lookModel").value = RIG.view.model;
    $("lookStat").textContent = "Cannot open that CAD model: " + f.error + ". Still showing the last one.";
    notice($("lookStat").textContent);
    return;
  }
  RIG.view.model = path;
  urdfLast.error = "";
  await setLook(RIG.view.look, true);
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
  if (!wasUrdf) { v.look = id; rigChanged(); renderLookUI(); return; }
  const pick = await askLookSizes();
  if (!pick) { renderLookUI(); return; }
  if (pick === "cad") {
    // measured on the CAD still shown, then the shapes are built from it
    if (!rigFromCad()) { renderLookUI(); return; }
    v.look = id;
    rigChanged();
    renderLookUI();
    return;
  }
  const keys = Object.keys(URDF_CFG.sizes || {});
  if (pick === "urdf") Object.assign(RIG.dims, urdfDimsOf(keys, urdfLast.dims || {}));
  else Object.assign(RIG.dims, urdfDimsOf(keys, v.custom || {}));
  v.sizes = pick;
  v.look = id;
  rigChanged();
  renderLookUI();                  // the box shows the shapes, not the CAD's last words
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
    $("lookUseCad").onclick = () => done("cad");
    $("lookUseUrdf").onclick = () => done("urdf");
    $("lookUseMine").onclick = () => done("custom");
    $("lookStay").onclick = () => done(null);
    dlg.oncancel = (e) => { e.preventDefault(); done(null); };
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  });
}
