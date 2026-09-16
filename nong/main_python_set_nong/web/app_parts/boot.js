// --- boot ---
renderRigUI();
buildRobot();
showTab("pose");   // open on what you do first, not on setup
addKey();               // keyframe 0 = start pose (neutral)
renderSliders();
renderTimeline();
poseChanged(false);     // also primes the live collision banner
refreshProjects();
refreshSeqs();
refreshModels();
connModeChanged();
initSideDrag();
initTimeDrag();
// Boot is over: from here a change to the timeline is real work, so start
// keeping a draft of it, and offer back anything a previous session lost.
draftArmed = true;
offerDraft();
resize();
requestAnimationFrame((t) => { lastFrame = t; tick(t); });
// opened from the hub ("Studio + monitor" on a module): connect by itself,
// and with monitor=1 the 3D model immediately simulates the real robot.
//   ?ip=<addr>            WiFi
//   ?dev=wifi:<ip>        same, hub's dev syntax
//   ?dev=usb:COM7[:<id>]  the cable, SHARED through the hub — the module
//                         website can stay open on that same port
{
  const qp = new URLSearchParams(location.search);
  const dev = qp.get("dev") || "";
  const startMonitor = () => {
    if (qp.get("monitor") === "1") { $("monChk").checked = true; monitorChanged(); }
  };
  // A dev can carry a PEER: usb:COM7@far-nong means the module called
  // far-nong, on the hotspot of the board plugged into COM7. Split that off
  // first — it used to stay glued to the port name, so Studio went looking for
  // a serial port literally called COM7@far-nong and failed to reach a module
  // that was perfectly reachable.
  const at = dev.indexOf("@");
  const peer = at >= 0 ? dev.slice(at + 1) : "";
  const addr = at >= 0 ? dev.slice(0, at) : dev;
  window.HUB_PEER = peer;          // every command adds it back on

  // A dev can also name ANOTHER PC: hub:10.0.0.5/usb:COM7 is COM7 on that
  // machine, not this one. Split the prefix off the same way the peer is, or
  // the tests below never match and Studio drives a LOCAL port with the same
  // name — the wrong robot, silently.
  let via = "";
  let inner = addr;
  if (inner.indexOf("hub:") === 0) {
    const slash = inner.indexOf("/");
    if (slash > 0) { via = inner.slice(0, slash + 1); inner = inner.slice(slash + 1); }
  }
  window.HUB_VIA = via;            // every command puts it back on

  if (inner.indexOf("usb:") === 0) {
    const bits = inner.slice(4).split(":");
    $("connSel").value = "usb";
    if (bits[1]) $("busId").value = bits[1];
    connModeChanged();
    loadPorts(bits[0]).then(() => {
      const sel = $("usbPort");
      if (sel.value !== bits[0]) {          // not listed (renamed/unplugged): offer it anyway
        const o = document.createElement("option");
        o.value = o.textContent = bits[0];
        sel.appendChild(o); sel.value = bits[0];
      }
      return connectRobot();
    }).then(startMonitor);
  } else if (qp.get("ip") || inner.indexOf("wifi:") === 0) {
    $("robotIp").value = qp.get("ip") || inner.slice(5);
    connectRobot().then(startMonitor);
  }
  // IK self-test (open with ?selftest=ik): drives the SAME solver that
  // dragging the wrist uses toward several offsets and checks the wrist
  // reaches them while BOTH shoulder and elbow adjust. Report via the title.
  if (qp.get("selftest") === "ik") setTimeout(runIkSelfTest, 400);
  if (qp.get("selftest") === "gimbal") setTimeout(runGimbalSelfTest, 400);
  if (qp.get("selftest") === "elbow") setTimeout(runElbowSelfTest, 400);
  if (qp.get("selftest") === "view") setTimeout(runViewSelfTest, 400);
  if (qp.get("selftest") === "servo") setTimeout(runServoSelfTest, 400);
  if (qp.get("selftest") === "migrate") setTimeout(runMigrateSelfTest, 400);
}

// Regression for the "cannot see any model" bug: an OLD saved rig has length-8
// per-joint arrays (arms only). mergeRig must extend EVERY per-joint array to
// 10 — including "zero" — or applyPose feeds NaN into the WAIST/SHRUG body
// rotation and the whole robot (all under bodyGroup) vanishes.
function runMigrateSelfTest() {
  const fails = [];
  const old = {                    // a pre-waist/shrug saved rig
    dims: { shoulderX: 105, shoulderY: 95, upperLen: 115, foreLen: 105 },
    zero: [90,90,90,90,90,90,90,90], min: [30,30,30,30,30,30,30,30],
    max: [150,150,150,150,150,150,150,150], axis: ["x","z","x","z","x","z","x","z"],
    invert: [0,0,0,0,0,0,0,0], neutral: [90,90,90,90,90,90,90,90],
    gearPinion: [15,15,12,12,15,15,12,12], gearGear: [18,18,13,13,18,18,13,13],
    tilt: [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
    jointR: [17,15,17,15], barR: [13,11,13,11],
  };
  const m = mergeRig(old);
  ["zero","min","max","axis","invert","neutral","gearPinion","gearGear",
   "pulseMin","pulseMax","servoMaxDps","servoRange","tilt"].forEach(k => {
    if (!Array.isArray(m[k]) || m[k].length !== NJ)
      fails.push(`${k} not length ${NJ} (got ${Array.isArray(m[k]) ? m[k].length : typeof m[k]})`);
  });
  // apply the migrated rig and confirm the body transforms stay finite
  const savedRig = RIG, savedPose = pose;
  RIG = m; pose = new Array(NJ).fill(90); buildRobot();
  const finite = o => o && Number.isFinite(o.rotation.x) && Number.isFinite(o.rotation.y) && Number.isFinite(o.rotation.z);
  if (!finite(bodyGroup)) fails.push("bodyGroup rotation NaN (waist)");
  if (!finite(shoulderMount)) fails.push("shoulderMount rotation NaN (shrug)");
  // and the arm joint groups (the ones an old rig used to drive)
  for (let i = 0; i < ARMJ; i++)
    if (jointGroups[i] && !Number.isFinite(jointGroups[i].quaternion.x))
      { fails.push(`joint ${i} quaternion NaN`); break; }
  RIG = savedRig; pose = savedPose; buildRobot();
  document.title = fails.length
    ? "MIGRATE FAIL " + fails.join(" | ")
    : `MIGRATE PASS old-8-joint rig -> all length ${NJ}, body transforms finite`;
  console.log(document.title);
}

function ikTo(arm, target) { // the wrist-drag / gotoXyz solver, headless-callable
  const wrKey = arm === 0 ? "wrL" : "wrR";
  const start = fkPoints(pose)[wrKey].clone();
  const steps = Math.min(60, Math.max(6, Math.ceil(start.distanceTo(target) / 12)));
  for (let s = 1; s <= steps; s++) solveIK(arm, start.clone().lerp(target, s / steps), 8);
  solveIK(arm, target, 25);
  return fkPoints(pose)[wrKey];
}
function runIkSelfTest() {
  const arm = 0, idxSh = [0, 1], idxEl = [2, 3];
  // targets are the wrist of a KNOWN reachable pose (sh_p, sh_r, el_p, el_r),
  // so a failure means the solver stalled, not an unreachable point
  const poses = [[110, 100, 95, 90], [70, 90, 120, 90],
                 [90, 110, 90, 110], [130, 80, 115, 100], [60, 120, 130, 80]];
  let pass = 0, worst = 0, shOK = true, elOK = true, errs = [];
  // tolerance scales with the arm: ~4% of reach (bigger robot -> bigger mm for
  // the same relative accuracy). reach = upper + fore of this side.
  const reach = (RIG.dims.upperLenL || 115) + (RIG.dims.foreLenL || 105);
  const tol = Math.max(8, reach * 0.045);
  poses.forEach(tp => {
    pose = [...RIG.neutral];
    for (let k = 0; k < 4; k++) pose[idxSh[0] + k] = clampJ(idxSh[0] + k, tp[k]);
    applyPose(); robot.updateMatrixWorld(true);
    const target = fkPoints(pose).wrL.clone();      // reachable by construction
    pose = [...RIG.neutral];                         // start fresh, solve back
    const before = [...pose];
    ikTo(arm, target);
    const err = fkPoints(pose).wrL.distanceTo(target);
    errs.push(err.toFixed(0));
    worst = Math.max(worst, err);
    if (err < tol) pass++;
    if (Math.abs(pose[0] - before[0]) + Math.abs(pose[1] - before[1]) < 0.3) shOK = false;
    if (Math.abs(pose[2] - before[2]) + Math.abs(pose[3] - before[3]) < 0.3) elOK = false;
  });
  pose = [...RIG.neutral]; poseChanged(false);
  const ok = pass === poses.length && shOK && elOK;
  const msg = `IKTEST ${ok ? "PASS" : "FAIL"} reached ${pass}/${poses.length} worst=${worst.toFixed(1)}mm tol=${tol.toFixed(1)}mm errs=[${errs}] shoulderMoves=${shOK} elbowMoves=${elOK}`;
  document.title = msg;
  $("tlStat").textContent = msg;
}
// does the SECOND ring of a pair follow when the FIRST joint (pitch) rotates?
// (the gimbal test: shoulder must behave like elbow)
function ringFollows(pairIdx, pitchJoint) {
  pose = [...RIG.neutral]; applyPose(); robot.updateMatrixWorld(true);
  showGizmo(pairIdx);
  const second = rings[1].mesh;                  // the roll (inner) ring
  const q0 = second.getWorldQuaternion(new THREE.Quaternion());
  pose[pitchJoint] = clampJ(pitchJoint, 130);    // rotate the pitch a lot
  applyPose(); robot.updateMatrixWorld(true);
  const q1 = second.getWorldQuaternion(new THREE.Quaternion());
  showGizmo(-1);
  return q0.angleTo(q1) * 180 / Math.PI;         // degrees the inner ring turned
}
function runGimbalSelfTest() {
  const sh = ringFollows(0, 0);     // shoulder: inner ring vs shoulder pitch
  const el = ringFollows(1, 2);     // elbow: inner ring vs elbow pitch
  pose = [...RIG.neutral]; poseChanged(false);
  const ok = sh > 10 && el > 10 && Math.abs(sh - el) < 3;
  document.title = `GIMBAL ${ok ? "PASS" : "FAIL"} shoulderInnerTurned=${sh.toFixed(1)}deg elbowInnerTurned=${el.toFixed(1)}deg`;
}
function runViewSelfTest() {
  const t = controls.target;
  const checks = [
    ["front", "z", 1, "xy"], ["back", "z", -1, "xy"],
    ["right", "x", 1, "yz"], ["left", "x", -1, "yz"],
    ["top", "y", 1, "xz"], ["bottom", "y", -1, "xz"],
  ];
  let i = 0, fails = [], dbg = "";
  const step = () => {
    if (i >= checks.length) {
      document.title = "VIEW " + (fails.length ? "FAIL " + fails.join(",") : "PASS all 6") + " | " + dbg;
      return;
    }
    const [name, ax, sign, plane] = checks[i++];
    setView(name);
    setTimeout(() => {
      const d = activeCam().position.clone().sub(t);
      const comps = [Math.abs(d.x), Math.abs(d.y), Math.abs(d.z)];
      const okSide = Math.sign(d[ax]) === sign && Math.abs(d[ax]) >= Math.max(...comps) - 1;
      const okPlane = $("dragPlane").value === plane;
      if (!okSide || !okPlane) fails.push(name);
      if (name === "front") dbg = `front cam=(${d.x.toFixed(0)},${d.y.toFixed(0)},${d.z.toFixed(0)}) plane=${$("dragPlane").value}`;
      step();
    }, 600);
  };
  step();
}
function runElbowSelfTest() {
  // drag the elbow to a reachable spot using ONLY the shoulder servos
  const arm = 0;
  pose = [...RIG.neutral];
  pose[0] = 120; pose[1] = 115;                  // a known shoulder pose
  applyPose(); robot.updateMatrixWorld(true);
  const target = elbowBalls[arm].getWorldPosition(new THREE.Vector3());
  pose = [...RIG.neutral];
  const before = [...pose];
  solveElbowIK(arm, target);
  const err = elbowBalls[arm].getWorldPosition(new THREE.Vector3()).distanceTo(target);
  const shMoved = Math.abs(pose[0] - before[0]) + Math.abs(pose[1] - before[1]) > 1;
  const elbowUntouched = Math.abs(pose[2] - before[2]) + Math.abs(pose[3] - before[3]) < 0.1;
  pose = [...RIG.neutral]; poseChanged(false);
  document.title = `ELBOW ${err < 8 && shMoved && elbowUntouched ? "PASS" : "FAIL"} err=${err.toFixed(1)}mm shoulderMoved=${shMoved} elbowJointsUntouched=${elbowUntouched}`;
}

// ---- Login Overlay System ----
function getAccounts() {
  try {
    const acc = JSON.parse(localStorage.getItem('nongAccounts'));
    if (acc && typeof acc === 'object') return acc;
  } catch (e) {}
  return { 'super_admin': 'admin123', 'admin': 'admin123' };
}
function saveAccounts(acc) {
  localStorage.setItem('nongAccounts', JSON.stringify(acc));
}
function appLogin() {
  const u = $("loginUser").value.trim();
  const p = $("loginPass").value;
  const acc = getAccounts();
  if (acc[u] && acc[u] === p) {
    currentUser = u;
    $("loginPass").value = "";
    $("loginStat").textContent = "";
    showTab(sideTab);
    localStorage.setItem("nongZeroCred", JSON.stringify({ user: u, pass: p }));
    window.dispatchEvent(new Event('resize'));
    if (pendingConnect) {
      const pending = pendingConnect;
      pendingConnect = null;
      connectRobot().then(pending.resolve, pending.reject);
    }
  } else {
    $("loginStat").textContent = "Invalid username or password.";
  }
}
function populateUserList() {
  const list = $("muList");
  if (!list) return;
  list.innerHTML = '<option value="">New User...</option>';
  const acc = getAccounts();
  for (const u in acc) {
    const opt = document.createElement("option");
    opt.value = u;
    opt.textContent = u;
    list.appendChild(opt);
  }
}
function muSelect() {
  const u = $("muList").value;
  $("muUser").value = u;
  $("muPass").value = "";
  $("muStat").textContent = "";
}
function muSave() {
  const u = $("muUser").value.trim();
  const p = $("muPass").value;
  if (!u) { $("muStat").textContent = "Username required."; return; }
  const acc = getAccounts();
  if (p) {
    acc[u] = p;
  } else if (!acc[u]) {
    $("muStat").textContent = "Password required for new user."; return;
  }
  saveAccounts(acc);
  $("muStat").textContent = "User saved.";
  populateUserList();
  $("muList").value = u;
}
function muDelete() {
  const u = $("muUser").value.trim();
  if (!u) return;
  if (u === "super_admin") { $("muStat").textContent = "Cannot delete super_admin."; notice("Cannot delete super_admin."); return; }
  const acc = getAccounts();
  if (acc[u]) {
    delete acc[u];
    saveAccounts(acc);
    $("muStat").textContent = "User deleted.";
    populateUserList();
    $("muUser").value = "";
    $("muPass").value = "";
  }
}

