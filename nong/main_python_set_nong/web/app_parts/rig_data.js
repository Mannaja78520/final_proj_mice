// --- rig data ---
// 10 logical joints: 8 arm (2 arms x universal shoulder+elbow) then the two
// BODY joints — WAIST (yaws the whole upper body left/right) and SHRUG (lifts
// both shoulders a little). ARMJ = the arm joints only (IK / arm FK use these);
// NJ = all joints (poses, sliders, timing, servo config).
const ARMJ = 8, NJ = 10;
const JOINT_NAMES = ["L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
                     "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R", "WAIST", "SHRUG"];
const JOINT_LABELS = ["L shoulder pitch", "L shoulder roll", "L elbow pitch", "L elbow roll",
                      "R shoulder pitch", "R shoulder roll", "R elbow pitch", "R elbow roll",
                      "Waist (turn L/R)", "Shrug (rock: L up / R down)"];

// rotation axis per joint is EDITABLE in the Rig setup (RIG.axis) — roll = X,
// pitch = Y, yaw = Z. These are only the built-in defaults. WAIST turns about
// the vertical (yaw = Y here since the body's up axis is Y); SHRUG is a small
// pitch of the shoulder mount.
const DEFAULT_AXIS = ["x", "z", "x", "z", "x", "z", "x", "z", "y", "x"];
const AXIS_LABEL = { x: "roll (X)", y: "pitch (Y)", z: "yaw (Z)" };
// base rotation sense per joint (mirrors right arm); "inv" in the rig flips it
const BASE_DIR = [-1, +1, -1, +1, -1, -1, -1, -1, +1, +1];

// The editable rig: body dimensions (mm, visual only — timing never depends
// on them) + per-joint calibration. "zero" = the servo angle at which that
// joint is straight (arm hanging along the body). If your real robot at
// all-90 holds the arms away from the body, set each joint's zero to the
// servo angle where the arm actually hangs — adjust it in the Rig setup
// card, never in code. Persisted in the browser + saved into projects.
const DEFAULT_RIG = {
  // left and right arm lengths are separate — an STL on one side never
  // changes the other side.
  // DEFAULTS SCALED TO THE REAL ROBOT (measured from nong_assembly.STEP, mm):
  //   spherical shoulder/elbow joints ~89 mm (ball r ~42), shrug yoke ~260 mm
  //   wide, upper-arm bar 52 mm, forearm bar 96 mm, spine (body_shaft) 250 mm.
  //   Central "torso" here stands in for the slim spine + shrug yoke.
  dims: { shoulderX: 120, shoulderY: 110,
          upperLenL: 110, upperLenR: 110, foreLenL: 130, foreLenR: 130,
          torsoW: 100, torsoH: 250, torsoD: 70,
          // SHRUG see-saw pivot: the bearing it rocks about sits ABOVE the
          // shoulder line (not on the servo). mm measured up from the shoulder
          // line. 0 = rock about the shoulder line itself.
          shrugPivot: 60 },
  zero: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
  axis: [...DEFAULT_AXIS],        // rotation axis per joint (roll/pitch/yaw)
  invert: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  neutral: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90], // editable "Neutral pose"
  // Mounting correction per joint, in JOINT degrees — a servo horn refitted a
  // tooth out. The BOARD stores it in servo degrees as `trim`; the conversion is
  // its job, so nothing here has to know a gear ratio.
  offset: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  // JOINT travel limits (deg). Arms: the 2-servo universal joint can't reach
  // the full 0..180 (default 30..150). WAIST turns the body a wide range;
  // SHRUG swings 77..103 = 26 deg (90 +-13), measured on the 4-bar linkage
  // fitted 2026-08-19. It was 87..93 while the shoulder bar was a see-saw.
  // The module
  // clamps to the same joint limits.
  min: [30, 30, 30, 30, 30, 30, 30, 30, 30, 77],
  max: [150, 150, 150, 150, 150, 150, 150, 150, 150, 103],
  // PER-JOINT reduction gear + servo pulse. Each joint can use a different
  // servo: as built the SHOULDERS are PDI-1181MG (270 deg) through 15:18, the
  // ELBOWS are MG90S (180 deg) through 12:13, WAIST is a TianKongRC 35kg 270
  // deg direct 1:1, SHRUG an MG90S 180 deg direct 1:1. Applied ON THE ROBOT
  // (the firmware converts joint->servo with each joint's own ratio+travel);
  // the editor works in joint degrees and just pushes these to the module.
  gearPinion: [15, 15, 12, 12, 15, 15, 12, 12, 1, 1],
  gearGear:   [18, 18, 13, 13, 18, 18, 13, 13, 1, 1],
  pulseMin:   [500, 500, 500, 500, 500, 500, 500, 500, 500, 500],
  pulseMax:   [2500, 2500, 2400, 2400, 2500, 2500, 2400, 2400, 2500, 2400],
  servoMaxDps:[375, 375, 400, 400, 375, 375, 400, 400, 200, 400],
  // SERVO travel per joint: how far the SERVO turns end to end. 180 for a
  // normal hobby servo, 270 for a wide-angle one. This is NOT the joint's
  // range (that is min/max above) — fitting a 270 servo is this one number,
  // and every saved pose/sequence keeps working because they are all in
  // JOINT degrees. 270 servos: the 4 shoulders (PDI-1181MG) + WAIST.
  servoRange: [270, 270, 180, 180, 270, 270, 180, 180, 270, 180],
  // SERVO FRAME RATE per joint (Hz). DEFAULT 50 everywhere — the rate the robot
  // ran at before, and it works. The PDI-1181MG datasheet says 330 Hz and it's
  // available (the Hz box / RATE command), but driving the shoulders at 330 Hz
  // made a marginal unit over-current on a move and cut out, so 50 is default.
  frameHz: [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
  // per-joint axis TILT (roll/pitch/yaw deg) — the real universal joint's
  // axes aren't exactly aligned to X/Y/Z / 90°, so this rotates each joint's
  // rotation axis to match. Visual/rig only. Default no tilt.
  tilt: [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
  // SIZES per universal joint / per bar, indexed like PAIRS:
  //   0 = L shoulder, 1 = L elbow, 2 = R shoulder, 3 = R elbow
  // bar hanging from it (0/1 = L upper arm / L forearm, 2/3 = R upper / R fore).
  // Scaled to the real spherical joints (~89 mm dia -> r ~42) and ~10 mm bars.
  jointR: [42, 40, 42, 40],
  barR:   [12, 10, 12, 10],
};
function mergeRig(saved) {
  const r = { ...JSON.parse(JSON.stringify(DEFAULT_RIG)), ...saved,
              dims: { ...DEFAULT_RIG.dims, ...(saved.dims || {}) } };
  // migrate old single-length rigs
  if (saved.dims && saved.dims.upperLen !== undefined) {
    r.dims.upperLenL = r.dims.upperLenR = saved.dims.upperLen;
    delete r.dims.upperLen;
  }
  if (saved.dims && saved.dims.foreLen !== undefined) {
    r.dims.foreLenL = r.dims.foreLenR = saved.dims.foreLen;
    delete r.dims.foreLen;
  }
  // Bring every per-joint array to NJ (10) WITHOUT losing tuned values: keep
  // whatever the saved rig had (old rigs are length 8 = arms only) and fill the
  // two new BODY joints (WAIST, SHRUG) from the defaults. A stray scalar (the
  // very old single gear ratio) fills every joint.
  const fixLen = (k) => {
    const def = DEFAULT_RIG[k];
    if (typeof r[k] === "number") r[k] = new Array(NJ).fill(r[k]);
    if (!Array.isArray(r[k])) { r[k] = [...def]; return; }
    r[k] = def.map((d, i) => (r[k][i] !== undefined ? r[k][i] : d));
  };
  // NOTE: "zero" MUST be here — if it stays length 8, RIG.zero[8/9] is
  // undefined, applyPose computes NaN for the WAIST/SHRUG body rotation, and
  // the whole robot (torso+head+arms all live under bodyGroup) renders at NaN
  // = invisible. Any per-joint array read by applyPose/buildRobot belongs here.
  ["zero", "min", "max", "axis", "invert", "neutral", "offset",
   "gearPinion", "gearGear", "pulseMin", "pulseMax", "servoMaxDps", "servoRange",
   "frameHz"].forEach(fixLen);
  // The SHRUG 4-bar calibration. An empty list means "not measured", which is
  // the old symmetric behaviour — so every rig saved before this keeps looking
  // exactly as it did until you actually measure the linkage.
  if (!Array.isArray(r.shrugCurve)) r.shrugCurve = [];
  r.shrugCurve = r.shrugCurve
    .filter(pt => pt && isFinite(+pt.j))
    .map(pt => ({ j: +pt.j, l: +pt.l || 0, r: +pt.r || 0 }));

  if (!Array.isArray(r.tilt)) r.tilt = JSON.parse(JSON.stringify(DEFAULT_RIG.tilt));
  r.tilt = DEFAULT_RIG.tilt.map((d, i) =>
    (Array.isArray(r.tilt[i]) && r.tilt[i].length === 3) ? r.tilt[i] : [...d]);
  if (!Array.isArray(r.jointR) || r.jointR.length !== 4) r.jointR = [...DEFAULT_RIG.jointR];
  if (!Array.isArray(r.barR) || r.barR.length !== 4) r.barR = [...DEFAULT_RIG.barR];
  return r;
}
// The rig tuned against the REAL robot ships with the app: /rig_default.js is
// written by "Make this the factory default" below and loaded before this
// file, so a fresh browser — or anyone pressing Reset — starts on the numbers
// that match the built robot instead of the original factory guesses.
// Absent or malformed, the built-in constants below still stand on their own.
if (window.NONG_RIG_DEFAULT && typeof window.NONG_RIG_DEFAULT === "object") {
  try {
    Object.assign(DEFAULT_RIG, mergeRig(JSON.parse(JSON.stringify(window.NONG_RIG_DEFAULT))));
  } catch (e) { console.warn("shipped rig_default ignored:", e); }
}
let RIG = JSON.parse(JSON.stringify(DEFAULT_RIG));
try {
  const saved = JSON.parse(localStorage.getItem("nong_rig") || "null");
  if (saved) RIG = mergeRig(saved);
} catch (e) { /* fresh rig */ }
function saveRig() { localStorage.setItem("nong_rig", JSON.stringify(RIG)); }
// "My default": once you have tuned the rig you can lock the CURRENT rig in as
// your default, so Reset returns to YOUR tuned rig (not the factory scale) and
// the tune is kept in a separate, protected slot. Stored per browser.
function saveRigDefault() {
  localStorage.setItem("nong_rig_default", JSON.stringify(RIG));
  if (typeof $ === "function" && $("limStat"))
    $("limStat").textContent = "saved the current rig as your default — Reset now returns to this ✓";
}
// Per-browser "my default" is saveRigDefault(). THIS writes the rig into the
// project so every browser gets it — the live rig only exists here, so the
// browser has to hand it over.
async function shipRigDefault() {
  try {
    const r = await fetch("/api/rigdefault", {
      method: "POST", body: JSON.stringify({ rig: RIG }),
    }).then(r => r.json());
    if (r.ok) {
      $("limStat").textContent = "saved this rig as the factory default — every fresh "
        + "browser now starts on it, and Reset returns to it ✓";
    } else {
      // Only a FAILURE reaches the global banner; good news stays on its card.
      $("limStat").textContent = "could not save: " + (r.error || "unknown");
      notice($("limStat").textContent);
    }
  } catch (e) { $("limStat").textContent = "could not save: " + (e.message || e); notice($("limStat").textContent); }
}
function loadRigDefault() {
  try {
    const d = JSON.parse(localStorage.getItem("nong_rig_default") || "null");
    return d ? mergeRig(d) : null;
  } catch (e) { return null; }
}
function hasRigDefault() { return !!localStorage.getItem("nong_rig_default"); }

// ---- moving your whole setup between PCs --------------------------------
//
// Everything Studio remembers lives in localStorage, which is per browser AND
// per machine. Tuning a rig on the workshop PC and then finding the show
// laptop knows nothing about it is the problem this solves.
//
// One bundle carries the lot: the working rig, your saved default, the mesh /
// STL assignments, and the panel width. Sequences and projects are NOT in
// here — those already live on the hub as files and travel with it.
const SETTINGS_KEYS = ["nong_rig", "nong_rig_default", "nong_meshes", "nong_sidew"];

function collectSettings() {
  const b = { kind: "mice-studio-settings", version: 1, rig: RIG, keys: {} };
  SETTINGS_KEYS.forEach(k => {
    const v = localStorage.getItem(k);
    if (v !== null) b.keys[k] = v;
  });
  return b;
}

// Put a bundle into this browser. Deliberately does NOT touch the zero
// calibration credentials — those are a per-machine login, not a setting, and
// carrying them between PCs would be a surprise.
function applySettings(b, where) {
  if (!b || b.kind !== "mice-studio-settings")
    throw new Error("that file is not a Studio settings export");
  const keys = b.keys || {};
  let n = 0;
  SETTINGS_KEYS.forEach(k => {
    if (typeof keys[k] === "string") { localStorage.setItem(k, keys[k]); n++; }
  });
  // the rig is applied live as well as stored, so the change is visible at
  // once instead of only after a reload
  if (b.rig) { RIG = mergeRig(b.rig); saveRig(); }
  loadMeshes();                       // STL assignments came with the bundle
  rigChanged();
  setSettingsStat("loaded " + n + " setting(s) from " + where +
                  (b.savedBy ? " (" + b.savedBy + ")" : "") +
                  (b.savedAt ? " saved " + b.savedAt : "") +
                  " — kept in this browser's cache ✓");
  return n;
}

function setSettingsStat(msg) {
  const el = $("setStat");
  if (el) el.textContent = msg;
}

// ---- 1. a file you can carry ------------------------------------------
function exportSettings() {
  const blob = new Blob([JSON.stringify(collectSettings(), null, 1)],
                        { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mice-studio-settings.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  setSettingsStat("exported — copy this file to the other PC and use Import ✓");
}

function importSettingsFile(input) {
  const f = input.files && input.files[0];
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try { applySettings(JSON.parse(rd.result), f.name); }
    catch (e) { setSettingsStat("could not import: " + (e.message || e)); }
    input.value = "";                 // so the same file can be picked again
  };
  rd.readAsText(f);
}

// ---- 2. straight over the network -------------------------------------
// Share puts the bundle on THIS hub; the other PC pulls it. The pull goes
// through the local hub rather than straight from the browser, because a page
// served by one hub is not allowed to read another hub's response.
async function shareSettings() {
  try {
    const r = await fetch("/api/settings", {
      method: "POST", body: JSON.stringify({ bundle: collectSettings() }),
    }).then(r => r.json());
    setSettingsStat(r.ok
      ? "shared from this PC ✓ — on the other PC open Studio, press Find PCs, and Get"
      : "could not share: " + (r.error || "unknown"));
  } catch (e) { setSettingsStat("could not share: " + (e.message || e)); }
}

async function findHubs() {
  const sel = $("hubList");
  if (!sel) return;
  setSettingsStat("looking for other PCs on this network…");
  sel.innerHTML = "<option value=''>looking…</option>";
  try {
    const r = await fetch("/api/hubs?force=1").then(r => r.json());
    const hubs = (r.hubs || []).filter(h => h.has);
    // h.name comes off the network (the other PC's own report) - it goes in
    // as TEXT, never as markup, so a hostile name cannot write HTML here.
    sel.innerHTML = "";
    hubs.forEach(h => {
      const o = document.createElement("option");
      o.value = h.ip;
      o.textContent = h.ip + (h.name ? " — " + h.name : "") +
        (h.savedAt ? " (" + h.savedAt + ")" : "");
      sel.appendChild(o);
    });
    if (!hubs.length) sel.innerHTML = "<option value=''>none found</option>";
    setSettingsStat(hubs.length
      ? hubs.length + " PC(s) have shared settings — pick one and press Get"
      : "no other PC on this network has shared settings yet. On that PC, "
        + "open Studio and press Share.");
  } catch (e) {
    sel.innerHTML = "<option value=''>search failed</option>";
    setSettingsStat("could not search: " + (e.message || e));
  }
}

async function getSettingsFrom() {
  const host = ($("hubList") && $("hubList").value) || ($("hubHost") && $("hubHost").value) || "";
  if (!host) { setSettingsStat("pick a PC first, or type its address"); return; }
  try {
    const b = await fetch("/api/settings/peer?host=" + encodeURIComponent(host))
      .then(r => r.json());
    if (b.error) { setSettingsStat("could not get it: " + b.error); return; }
    applySettings(b, host);
  } catch (e) { setSettingsStat("could not get it: " + (e.message || e)); }
}
function jdir(i) { return BASE_DIR[i] * (RIG.invert[i] ? -1 : 1); }
// clamp a servo angle to that joint's own [min,max] (the universal joint
// can't reach 0..180) — used everywhere a joint angle is set
function clampJ(i, v) {
  return Math.min(RIG.max[i], Math.max(RIG.min[i], Math.round(v * 10) / 10));
}

// universal-joint pairs for selection/gizmos: [first joint index, anchor name]
const PAIRS = [
  { joints: [0, 1], label: "L shoulder" },
  { joints: [2, 3], label: "L elbow" },
  { joints: [4, 5], label: "R shoulder" },
  { joints: [6, 7], label: "R elbow" },
];
