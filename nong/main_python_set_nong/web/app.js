/* Nong Studio — pose & keyframe editor for the nong humanoid.
 *
 * The robot: upper body, 2 arms, no fingers. Each arm has a universal joint
 * in the shoulder and one in the elbow; every universal joint is built from
 * 2 MG90S servos => 8 logical joints, same order as the firmware
 * (code/firmware/src/modules/nong/NongModule.h):
 *   1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P  8 R_EL_R
 * Angles are JOINT degrees (the physical joint angle), neutral 90, clamped to
 * each joint's [min,max] (a 2-servo universal joint can't reach 0..180).
 * The reduction gear (pinion:gear, e.g. 12:13) is applied ON THE ROBOT
 * (firmware converts joint->servo); the editor and commands stay in joint deg.
 * Each joint's rotation axis (roll X / pitch Y / yaw Z) is editable in Rig setup.
 */
"use strict";

const $ = (id) => document.getElementById(id);

// sidebar tabs: Movement (posing/robot, the main one) and Setup (rig + model)
// Four task tabs instead of Movement/Setup. Cards carry data-stab and are
// shown by it, so NOTHING moved in the DOM — every id, handler and QC driver
// works exactly as before, and only what is on screen at once changed.
// "move" is still accepted so any older link or habit keeps working.
const STAB_BTN = { pose: "tabBtnMove", sequence: "tabBtnSeq",
                   robot: "tabBtnRobot", setup: "tabBtnSetup" };
let sideTab = "pose";
function showTab(which) {
  if (which === "move") which = "pose";          // the old name
  if (!STAB_BTN[which]) which = "pose";
  sideTab = which;
  // both old containers stay visible; the cards inside decide for themselves
  $("tabMove").style.display = "";
  $("tabSetup").style.display = "";
  document.querySelectorAll("[data-stab]").forEach(el => {
    el.style.display = el.dataset.stab === which ? "" : "none";
  });
  Object.keys(STAB_BTN).forEach(k => {
    const b = $(STAB_BTN[k]);
    if (b) b.classList.toggle("on", k === which);
  });
}

// draggable divider: make the side panel wider or narrower (remembered)
function initSideDrag() {
  const side = $("side"), handle = $("sideDrag");
  const saved = +localStorage.getItem("nong_sidew");
  if (saved) side.style.width = Math.min(640, Math.max(240, saved)) + "px";
  // The panel has a width, so SAY so — a separator that announces its
  // position is one a screen reader can report and a keyboard can move.
  const MINW = 240, MAXW = 640, STEP = 16;
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", "vertical");
  handle.setAttribute("aria-label", "Resize the side panel");
  handle.setAttribute("tabindex", "0");
  const announce = () => {
    handle.setAttribute("aria-valuenow", parseInt(side.style.width) || 320);
    handle.setAttribute("aria-valuemin", MINW);
    handle.setAttribute("aria-valuemax", MAXW);
  };
  const setWidth = (w, remember) => {
    side.style.width = Math.min(MAXW, Math.max(MINW, w)) + "px";
    announce();
    resize();                       // keep the 3D canvas matched to the viewport
    if (remember) localStorage.setItem("nong_sidew", parseInt(side.style.width) || 320);
  };
  announce();

  // ARROW KEYS. Without this, someone who cannot hit the handle cannot resize
  // the panel at all — which is exactly what was reported on a laptop
  // touchpad. Home returns it to the default, so a panel dragged off-screen
  // is always recoverable.
  handle.addEventListener("keydown", (e) => {
    const now = parseInt(side.style.width) || 320;
    let w = null;
    if (e.key === "ArrowLeft")  w = now + STEP;     // panel grows leftwards
    else if (e.key === "ArrowRight") w = now - STEP;
    else if (e.key === "Home")  w = 320;            // the default
    else if (e.key === "PageUp") w = now + STEP * 4;
    else if (e.key === "PageDown") w = now - STEP * 4;
    if (w === null) return;
    e.preventDefault();
    setWidth(w, true);
  });

  // Double-click resets it, the shortcut people try first on a splitter.
  handle.addEventListener("dblclick", () => setWidth(320, true));

  let dragging = false;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    setWidth(window.innerWidth - e.clientX, false);
  });
  handle.addEventListener("pointerup", () => {
    dragging = false;
    localStorage.setItem("nong_sidew", parseInt(side.style.width) || 320);
  });
}

// ---------------------------------------------------------------- rig data
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
  // JOINT travel limits (deg). Arms: the 2-servo universal joint can't reach
  // the full 0..180 (default 30..150). WAIST turns the body a wide range;
  // SHRUG only lifts the shoulders a few degrees (87..93 = ~6 deg). The module
  // clamps to the same joint limits.
  min: [30, 30, 30, 30, 30, 30, 30, 30, 30, 87],
  max: [150, 150, 150, 150, 150, 150, 150, 150, 150, 93],
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
  ["zero", "min", "max", "axis", "invert", "neutral",
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
    $("limStat").textContent = r.ok
      ? "saved this rig as the factory default — every fresh browser now starts on it, "
        + "and Reset returns to it ✓"
      : "could not save: " + (r.error || "unknown");
  } catch (e) { $("limStat").textContent = "could not save: " + (e.message || e); }
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
    sel.innerHTML = hubs.length
      ? hubs.map(h => "<option value='" + h.ip + "'>" + h.ip +
          (h.name ? " — " + h.name : "") +
          (h.savedAt ? " (" + h.savedAt + ")" : "") + "</option>").join("")
      : "<option value=''>none found</option>";
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

// ---------------------------------------------------------------- state
// Start on the Neutral pose from Setup, not a flat 90 — RIG is already loaded
// above, so a tuned neutral (and the keyframe 0 that boot builds from this)
// matches the robot's own HOME instead of a pose the arm may not even hold.
// NOT RIG.zero: that is the angle at which a joint RENDERS straight, a model
// calibration, while neutral is the pose the robot rests at.
let pose = RIG.neutral.map((v, i) => clampJ(i, v)); // current joint angles, all 10
let keys = [];                           // [{pose:[10], t:ms, hold:ms}]
let selKey = 0;
let selPair = -1;                        // selected universal pair (gizmo)
let playing = false, playT = 0, lastFrame = 0, lastLiveSeg = -1;

// per-part visuals: STL file (empty = built-in shape) + its own transform
// (STL exports rarely share the robot's origin, so each part can be rotated,
// offset and scaled) + a color. Addons are extra STLs (clothes, hats, ...)
// layered ON TOP of any part — they never replace the skeleton.
const MESH_PARTS = ["torso", "head", "L_upper", "L_fore", "R_upper", "R_fore"];
const MESH_COLORS = { torso: "#3a4a5e", head: "#3a4a5e",
                      L_upper: "#4d7fd0", L_fore: "#4d7fd0",
                      R_upper: "#d0854d", R_fore: "#d0854d" };
function defMeshCfg(part) {
  return { file: "", tex: "", rot: [0, 0, 0], off: [0, 0, 0], scale: 1,
           color: MESH_COLORS[part] || "#8a94a6" };
}
let meshCfg = {};
MESH_PARTS.forEach(p => meshCfg[p] = defMeshCfg(p));
let addons = []; // [{file, part, rot, off, scale, color}]
// Read the stored mesh/STL assignments into meshCfg + addons. A function, not
// an inline block, because importing settings from another PC has to apply the
// same thing again — and two copies of this would drift.
function loadMeshes() {
  try {
    const mSaved = JSON.parse(localStorage.getItem("nong_meshes") || "null");
    if (!mSaved) return false;
    MESH_PARTS.forEach(p => meshCfg[p] = { ...defMeshCfg(p), ...(mSaved.meshCfg || {})[p] });
    addons = mSaved.addons || [];
    return true;
  } catch (e) { return false; }      // fresh, or a corrupt entry
}
loadMeshes();
function saveMeshes() {
  localStorage.setItem("nong_meshes", JSON.stringify({ meshCfg, addons }));
}
let modelFiles = []; // .stl files available in models/

const MIN_MOVE_MS = 80;                  // same floor as the firmware

// ---------------------------------------------------------------- scene
const viewport = $("viewport");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputEncoding = THREE.sRGBEncoding; // painted textures keep their colors
viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x10141a);
const camera = new THREE.PerspectiveCamera(50, 1, 1, 8000);
// A standard view (Front/Top/Left…) is only a true PLANE view in an
// ORTHOGRAPHIC projection. Under perspective the camera merely points at the
// plane: near parts still render bigger and parallel edges converge, so what
// you drag does not match what you see — which is why these never felt flat.
// Perspective stays for the iso/free view, where depth is the point.
const orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, -10000, 20000);
let usingOrtho = false;
function activeCam() { return usingOrtho ? orthoCam : camera; }
// Keep the ortho frustum showing the SAME amount of scene as the perspective
// camera does at its current distance, so switching projection never jumps.
function syncOrtho() {
  const dist = camera.position.distanceTo(controls ? controls.target : new THREE.Vector3()) || 700;
  const h = 2 * dist * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const w = h * (camera.aspect || 1);
  orthoCam.left = -w / 2; orthoCam.right = w / 2;
  orthoCam.top = h / 2;   orthoCam.bottom = -h / 2;
  orthoCam.position.copy(camera.position);
  orthoCam.up.copy(camera.up);
  orthoCam.quaternion.copy(camera.quaternion);
  orthoCam.updateProjectionMatrix();
}
function useProjection(ortho) {
  if (ortho === usingOrtho) { if (ortho) syncOrtho(); return; }
  usingOrtho = ortho;
  if (ortho) syncOrtho();
  else {                              // carry the ortho pose back to perspective
    camera.position.copy(orthoCam.position);
    camera.up.copy(orthoCam.up);
    camera.quaternion.copy(orthoCam.quaternion);
  }
  controls.object = activeCam();      // OrbitControls drives whichever is live
  controls.update();
}
camera.position.set(380, 240, 560);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(0, -20, 0);
controls.enableDamping = true;

// ---- standard views (like a Fusion/SolidWorks view cube) ----
// clicking a view snaps the camera to look straight at that plane AND sets the
// drag plane to match, so Shift+dragging a joint moves it in that flat plane.
const VIEWS = {
  front:  { dir: [0, 0, 1],  up: [0, 1, 0],  plane: "xy" },
  back:   { dir: [0, 0, -1], up: [0, 1, 0],  plane: "xy" },
  right:  { dir: [1, 0, 0],  up: [0, 1, 0],  plane: "yz" },
  left:   { dir: [-1, 0, 0], up: [0, 1, 0],  plane: "yz" },
  top:    { dir: [0, 1, 0],  up: [0, 0, -1], plane: "xz" },
  bottom: { dir: [0, -1, 0], up: [0, 0, 1],  plane: "xz" },
  iso:    { dir: [0.6, 0.42, 0.68], up: [0, 1, 0], plane: "cam" },
};
function setView(name) {
  const v = VIEWS[name];
  if (!v) return;
  const t = controls.target;
  const dist = camera.position.distanceTo(t) || 700;
  const dir = new THREE.Vector3(...v.dir).normalize();
  const p1 = t.clone().add(dir.multiplyScalar(dist));
  // snap the camera to look straight at the plane, then sync OrbitControls so
  // orbiting continues smoothly from here
  camera.up.set(...v.up);
  camera.position.copy(p1);
  camera.lookAt(t);
  // a named plane view is flat (orthographic); iso/free keeps perspective
  useProjection(v.plane !== "cam");
  controls.update();
  // drive the drag plane + its dropdown to match the view
  if ($("dragPlane")) $("dragPlane").value = v.plane;
  document.querySelectorAll("#viewCube button").forEach(b =>
    b.classList.toggle("on", b.dataset.view === name));
}
// the sidebar drag-plane dropdown -> move the camera to a matching view
function viewForPlane(plane) {
  setView({ cam: "iso", xy: "front", yz: "right", xz: "top" }[plane] || "iso");
}

scene.add(new THREE.HemisphereLight(0xbfd4ee, 0x24303e, 1.0));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(300, 500, 400);
scene.add(sun);

const grid = new THREE.GridHelper(1200, 24, 0x2a3442, 0x1c242f);
grid.position.y = -250;
scene.add(grid);

// materials
const matWrist = new THREE.MeshStandardMaterial({ color: 0x3ecf8e, emissive: 0x0e5c3a, roughness: 0.4 });
// joint balls + bone lines: the skeleton, ALWAYS visible (also under STLs)
// so joint positions and segment lengths stay readable
const matJoint = new THREE.MeshStandardMaterial({ color: 0xffd166, emissive: 0x4d3800, roughness: 0.45 });

// painted textures (PNG/JPG drawn by the user, e.g. a face for the head)
const texLoader = new THREE.TextureLoader();
const texCache = {};
function getTex(file) {
  if (!file) return null;
  if (!texCache[file]) {
    texCache[file] = texLoader.load("/models/" + encodeURIComponent(file));
    texCache[file].encoding = THREE.sRGBEncoding;
  }
  return texCache[file];
}
function partMat(part) {
  const cfg = meshCfg[part] || {};
  const tex = getTex(cfg.tex);
  return new THREE.MeshStandardMaterial({
    color: tex ? "#ffffff" : (cfg.color || "#8a94a6"),
    map: tex || null,
    roughness: 0.65,
  });
}

// ---------------------------------------------------------------- build rig
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

// ---------------------------------------------------------------- gizmo rings
const gizmo = new THREE.Group();
let rings = [];            // [{mesh, joint, localAxis}]
function clearGizmo() {
  rings.forEach(r => r.mesh.parent && r.mesh.parent.remove(r.mesh));
  rings = [];
}
function showGizmo(pairIdx) {
  clearGizmo();
  selPair = pairIdx;
  if (pairIdx < 0) { renderSliders(); return; }
  const pr = PAIRS[pairIdx];
  // rings sit just outside that joint's ball, so a bigger joint gets bigger rings
  const radius = Math.max(24, (RIG.jointR[pairIdx] || 16) * 2.7);
  pr.joints.forEach((jIdx, k) => {
    const axis = RIG.axis[jIdx];
    const color = axis === "x" ? 0xff5555 : (axis === "z" ? 0x55aaff : 0x55ff88);
    const tor = new THREE.Mesh(
      new THREE.TorusGeometry(radius + k * 8, 2.6, 10, 48),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85, depthTest: false }));
    tor.renderOrder = 10;
    // the torus hole-axis is local Z. Point it along the joint's REAL rotation
    // axis = tilt(roll/pitch/yaw) applied to the primary axis, so the ring
    // follows the orientation you set in Rig setup.
    tor.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), jointAxisVec(jIdx));
    tor.userData.joint = jIdx;
    pairRingParents[pairIdx][k].add(tor);
    rings.push({ mesh: tor, joint: jIdx, localAxis: axis });
  });
  renderSliders();
}

// ---------------------------------------------------------------- picking / drag
const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let drag = null; // {kind:'ring'|'ik', ...}

function setMouse(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
  ray.setFromCamera(mouse, activeCam());
}
function planeHit(point, normal) {
  const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(normal, point);
  const out = new THREE.Vector3();
  return ray.ray.intersectPlane(plane, out) ? out : null;
}
const AXV = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

const dragNormal = () => {
  const sel = $("dragPlane") ? $("dragPlane").value : "cam";
  return sel === "xy" ? new THREE.Vector3(0, 0, 1) :
         sel === "yz" ? new THREE.Vector3(1, 0, 0) :
         sel === "xz" ? new THREE.Vector3(0, 1, 0) :
         activeCam().getWorldDirection(new THREE.Vector3()).negate();
};

renderer.domElement.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  setMouse(e);

  // RINGS (the colored circles) are always draggable — you already clicked the
  // joint to show them, so grabbing a ring clearly means "rotate this servo".
  // No Shift needed.
  const ringHit = ray.intersectObjects(rings.map(r => r.mesh), false)[0];
  if (ringHit) {
    const r = rings.find(x => x.mesh === ringHit.object);
    // the ring's hole-axis (local Z) points along the tilted joint axis, so
    // its world Z is exactly the axis to rotate about
    const axis = new THREE.Vector3(0, 0, 1)
      .applyQuaternion(r.mesh.getWorldQuaternion(new THREE.Quaternion())).normalize();
    const center = r.mesh.getWorldPosition(new THREE.Vector3());
    const hit = planeHit(center, axis);
    if (!hit) return;
    drag = {
      kind: "ring", joint: r.joint, axis, center,
      ref: hit.clone().sub(center), start: pose[r.joint],
    };
    controls.enabled = false;
    return;
  }

  // The wrist/elbow IK balls need SHIFT held — otherwise a plain left-drag from
  // them orbits the camera (keeps orbiting and big arm moves from fighting).
  if (e.shiftKey) {
    const wristHit = ray.intersectObjects(wristBalls, false)[0];
    if (wristHit) {
      const arm = wristHit.object.userData.arm;
      const wp = wristHit.object.getWorldPosition(new THREE.Vector3());
      drag = { kind: "ik", arm, normal: dragNormal(), planePoint: wp };
      controls.enabled = false;
      return;
    }
    const elbowHit = ray.intersectObjects(elbowBalls, false)[0];
    if (elbowHit) {
      const arm = elbowHit.object.userData.arm;
      const ep = elbowHit.object.getWorldPosition(new THREE.Vector3());
      drag = { kind: "ikElbow", arm, normal: dragNormal(), planePoint: ep };
      controls.enabled = false;
      return;
    }
  }

  // plain click (no shift): select a joint's rings, or deselect on empty.
  // A plain drag from here just orbits (OrbitControls stays enabled).
  const meshHit = ray.intersectObjects(pickMeshes, true)[0];
  if (meshHit) { // clicking the same part again DESELECTS (rings disappear)
    const p = meshHit.object.userData.pair;
    showGizmo(p === selPair ? -1 : p);
    return;
  }
  bgDown = { x: e.clientX, y: e.clientY };
});

let bgDown = null;
renderer.domElement.addEventListener("pointerup", (e) => {
  if (bgDown && Math.hypot(e.clientX - bgDown.x, e.clientY - bgDown.y) < 6)
    showGizmo(-1);
  bgDown = null;
});
window.addEventListener("keydown", (e) => { if (e.key === "Escape") showGizmo(-1); });
renderer.domElement.addEventListener("dblclick", () => showGizmo(-1));

window.addEventListener("pointermove", (e) => {
  if (!drag) return;
  setMouse(e);

  if (drag.kind === "ring") {
    const hit = planeHit(drag.center, drag.axis);
    if (!hit) return;
    const v = hit.clone().sub(drag.center);
    const ang = Math.atan2(drag.axis.dot(new THREE.Vector3().crossVectors(drag.ref, v)),
                           drag.ref.dot(v));
    const j = drag.joint;
    // dragging turns the joint directly (joint degrees; gear is on the robot)
    pose[j] = clampJ(j, drag.start + jdir(j) * THREE.MathUtils.radToDeg(ang));
    poseChanged(true);
  } else if (drag.kind === "ik") {
    const target = planeHit(drag.planePoint, drag.normal);
    // strong IK per frame so the whole arm (shoulder + elbow together)
    // follows the wrist to wherever it can reach within the joint limits
    if (target) { solveIK(drag.arm, target, 16); poseChanged(true); }
  } else if (drag.kind === "ikElbow") {
    const target = planeHit(drag.planePoint, drag.normal);
    // move the elbow by rotating only the 2 shoulder servos
    if (target) { solveElbowIK(drag.arm, target); poseChanged(true); }
  }
});
window.addEventListener("pointerup", () => {
  if (drag) { drag = null; controls.enabled = true; poseChanged(false); }
});

function clampDeg(v) { return Math.min(180, Math.max(0, Math.round(v * 10) / 10)); }

// ---------------------------------------------------------------- IK (4-DOF arm)
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

// ---------------------------------------------------------------- collisions
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

// ---------------------------------------------------------------- sliders
function renderSliders() {
  const box = $("sliders");
  if (!box.dataset.built) {
    box.dataset.built = 1;
    JOINT_LABELS.forEach((label, i) => {
      const row = document.createElement("div");
      row.className = "jrow"; row.id = "jrow" + i;
      const name = document.createElement("span");
      name.className = "jname"; name.textContent = label;
      const slider = document.createElement("input");
      slider.type = "range"; slider.min = 0; slider.max = 180; slider.step = 0.5;
      slider.id = "js" + i;
      const num = document.createElement("input");
      num.type = "number"; num.min = 0; num.max = 180; num.id = "jn" + i;
      slider.oninput = () => { pose[i] = clampJ(i, +slider.value); poseChanged(true); };
      slider.onchange = () => poseChanged(false);
      num.onchange = () => { pose[i] = clampJ(i, +num.value); poseChanged(false); };
      row.append(name, slider, num);
      box.appendChild(row);
    });
  }
  // Only write what actually CHANGED. This runs on every frame of playback,
  // and it used to set six properties per joint every time — sixty DOM writes
  // a frame, of which the min/max were the same numbers as the frame before.
  // Setting min/max on a range input makes the browser re-validate and clamp
  // its value, so those were the expensive ones. At ~76 ticks a second that
  // was roughly 4500 writes a second, and it is why playback felt heavy and
  // the page froze when it had anything else to do.
  const sel = selPair >= 0 ? PAIRS[selPair].joints : [];
  for (let i = 0; i < NJ; i++) {
    const js = $("js" + i), jn = $("jn" + i);
    const inPair = sel.includes(i);
    if (_lastSel[i] !== inPair) {
      _lastSel[i] = inPair;
      $("jrow" + i).classList.toggle("sel", inPair);
    }
    if (_lastMin[i] !== RIG.min[i]) { _lastMin[i] = js.min = jn.min = RIG.min[i]; }
    if (_lastMax[i] !== RIG.max[i]) { _lastMax[i] = js.max = jn.max = RIG.max[i]; }
    // one decimal is all a servo can act on, and it keeps this from writing
    // on every frame while a value creeps by a thousandth of a degree
    const v = Math.round(pose[i] * 10) / 10;
    if (_lastVal[i] !== v) {
      _lastVal[i] = v;
      if (document.activeElement !== js) js.value = v;
      if (document.activeElement !== jn) jn.value = v;
    }
  }
}
// what the slider row is currently showing, so an unchanged value is not
// written again. Rig edits and rebuilds clear these through renderSliders().
const _lastVal = new Array(NJ).fill(NaN);
const _lastMin = new Array(NJ).fill(NaN);
const _lastMax = new Array(NJ).fill(NaN);
const _lastSel = new Array(NJ).fill(null);

// XYZ readout of the important joints (mm, robot frame: origin torso center)
// vertical layout so long numbers never overflow the card
function renderXyz() {
  const k = fkPoints(pose);
  const f = (p) => `(${Math.round(p.x)}, ${Math.round(p.y)}, ${Math.round(p.z)})`;
  $("jointXyz").textContent =
    "Left:\n" +
    "  shoulder " + f(k.shL) + "\n" +
    "  elbow    " + f(k.elL) + "\n" +
    "  wrist    " + f(k.wrL) + "\n" +
    "Right:\n" +
    "  shoulder " + f(k.shR) + "\n" +
    "  elbow    " + f(k.elR) + "\n" +
    "  wrist    " + f(k.wrR);
  // keep the editable wrist-target boxes in sync while not being typed in
  [["L", k.wrL], ["R", k.wrR]].forEach(([s, p]) => {
    ["x", "y", "z"].forEach(ax => {
      const el = $("tgt" + s + ax);
      if (el && document.activeElement !== el) el.value = Math.round(p[ax]);
    });
  });
}

// type a wrist target XYZ -> IK moves the whole arm there (then Add keyframe
// to put it into the sequence).
// The solver is a local tracker (that is why dragging works so well: the
// target only ever moves a little). So for a typed target we WALK the
// target from the current wrist position in small steps — same as a drag —
// instead of jumping, which strands the solver in a dead end.
function gotoXyz(arm) {
  const s = arm === 0 ? "L" : "R";
  const t = new THREE.Vector3(+$("tgt" + s + "x").value || 0,
                              +$("tgt" + s + "y").value || 0,
                              +$("tgt" + s + "z").value || 0);
  const wrKey = arm === 0 ? "wrL" : "wrR";
  let best = [...pose], bestErr = Infinity;
  const tryWalk = () => {
    const start = fkPoints(pose)[wrKey];
    const steps = Math.min(60, Math.max(6, Math.ceil(start.distanceTo(t) / 12)));
    for (let i = 1; i <= steps; i++)
      solveIK(arm, start.clone().lerp(t, i / steps), 6);
    solveIK(arm, t, 25); // final polish
    const err = fkPoints(pose)[wrKey].distanceTo(t);
    if (err < bestErr) { bestErr = err; best = [...pose]; }
    return err;
  };
  if (tryWalk() > 10) {
    // stuck? retry once from the neutral pose (different basin)
    const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    idx.forEach(j => pose[j] = RIG.neutral[j]);
    tryWalk();
  }
  pose = best;
  poseChanged(false);
  const got = fkPoints(pose)[wrKey];
  const err = Math.round(bestErr);
  $("tlStat").textContent = (arm === 0 ? "left" : "right") +
    ` wrist moved to (${Math.round(got.x)}, ${Math.round(got.y)}, ${Math.round(got.z)})` +
    (err > 10 ? ` — target is ${err} mm out of reach, this is the closest pose` : " ✓");
}

let liveTimer = 0, colTimer = 0;
function poseChanged(throttled, liveMs) {
  applyPose();
  renderSliders();
  const now = performance.now();
  if (!throttled || now - colTimer > 150) { // live crash warning + XYZ readout
    colTimer = now;
    $("collideWarn").style.display = collisionAt(pose) ? "block" : "none";
    renderXyz();
  }
  // No time throttle here: sendPoseLive() keeps one command in flight and
  // always carries the newest pose, so it paces itself to the link AND cannot
  // drop the value the drag ended on. See sendPoseLive().
  // Two different jobs, two different times.
  //
  // A DRAG follows your hand: sendPoseLive() carries a time measured from the
  // link's own round trip so the arm keeps up with the slider.
  //
  // Clicking a MOVE in the timeline is not that. It should travel the way the
  // move travels — at the speed set for that move, or the sequence's — so what
  // you see is what the show will do. Sending it down the drag path made the
  // arm snap there at full speed however slow the move was set to be.
  if ($("liveChk").checked) {
    if (liveMs > 0) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + Math.round(liveMs));
    else sendPoseLive();
  }
}

function setNeutral() { pose = [...RIG.neutral]; poseChanged(false); }
function neutralFromPose() { // editable neutral: saved in the rig + projects
  RIG.neutral = [...pose];
  saveRig();
  $("tlStat").textContent = "neutral pose = " + RIG.neutral.map(Math.round).join(" ") +
    " (used by the Neutral pose button; the robot's own HOME pose is 'neutral' in module.yaml)";
}
function mirrorLR() {
  // swap the arms; flip the waist to the other side (reflect about 90); the
  // shrug lifts both shoulders equally so it is unchanged.
  pose = [pose[4], pose[5], pose[6], pose[7], pose[0], pose[1], pose[2], pose[3],
          clampJ(8, 180 - pose[8]), pose[9]];
  poseChanged(false);
}

// ---------------------------------------------------------------- timing
// Show speed sets the automatic time; servo max speed sets the PHYSICAL
// floor: a keyframe time can always be made longer, never shorter than
// biggest-delta / max — otherwise the real arm can't reach the pose before
// the next move starts. The firmware applies the same rule (max_dps).
function speedDps() { return Math.max(5, +$("speedDps").value || 120); }
function maxDps() { return Math.max(30, +$("maxDps").value || 400); }
// Each joint can carry a different servo (Setup > rig), so the floor is the
// SLOWEST joint on this move, not one number for the whole arm. The project's
// max °/s field still caps every joint, so it can only make moves safer.
function jointMaxDps(i) {
  return Math.max(30, Math.min(maxDps(), RIG.servoMaxDps[i] || maxDps()));
}
function slowestDps() {
  let s = maxDps();
  for (let i = 0; i < NJ; i++) s = Math.min(s, jointMaxDps(i));
  return s;
}
function deltaDeg(from, to) {
  let dmax = 0;
  for (let i = 0; i < NJ; i++) dmax = Math.max(dmax, Math.abs(to[i] - from[i]));
  return dmax;
}
function minTime(from, to) {
  // per joint (the slow WAIST servo counts too), the slowest joint wins
  let need = 0;
  for (let i = 0; i < NJ; i++)
    need = Math.max(need, Math.abs(to[i] - from[i]) / jointMaxDps(i));
  return Math.max(MIN_MOVE_MS, Math.ceil(need * 1000));
}
// A move runs at the sequence's speed unless that keyframe overrides it, so one
// gesture can be slower or snappier than the rest of the show without hand-
// computing its time. Speed and time are two views of the SAME thing: set a
// speed and the time follows; type a time and the override is dropped.
function keyDps(i) {
  const k = keys[i];
  return k && k.dps ? Math.min(k.dps, slowestDps()) : speedDps();
}
function autoTime(from, to, dps) {
  const v = dps || speedDps();
  const t = Math.max(MIN_MOVE_MS, Math.round(deltaDeg(from, to) / v * 1000));
  return Math.max(t, minTime(from, to));
}
function keyMin(i) { // physical minimum for keyframe i (0 = entry, unknown start)
  return i > 0 && keys[i - 1] ? minTime(keys[i - 1].pose, keys[i].pose) : MIN_MOVE_MS;
}
function speedChanged() {
  if (speedDps() > slowestDps()) $("speedDps").value = slowestDps();
  recalcTimes();
  renderTimeline();
}
function recalcTimes() {   // keeps each keyframe's own speed override
  bumpKeys();
  for (let i = 1; i < keys.length; i++)
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
}
function clampKeyTimes() { // raise any hand-edited time that fell below the floor
  bumpKeys();
  for (let i = 0; i < keys.length; i++) keys[i].t = Math.max(keys[i].t, keyMin(i));
}

// ---------------------------------------------------------------- timeline
function addKey() {
  clearBadMarks(); // poses changed: collision marks are stale until re-checked
  const k = { pose: [...pose], t: 1000, hold: 0 };
  if (keys.length) k.t = autoTime(keys[keys.length - 1].pose, k.pose, keyDps(keys.length));
  keys.push(k);
  bumpKeys();
  selKey = keys.length - 1;
  renderTimeline();
}
function updateKey() {
  if (!keys[selKey]) return;
  clearBadMarks();
  keys[selKey].pose = [...pose];
  bumpKeys();
  if (selKey >= 1) keys[selKey].t = autoTime(keys[selKey - 1].pose, keys[selKey].pose, keyDps(selKey));
  if (keys[selKey + 1]) keys[selKey + 1].t = autoTime(keys[selKey].pose, keys[selKey + 1].pose, keyDps(selKey + 1));
  clampKeyTimes();
  renderTimeline();
}
function dupKey() {
  if (!keys[selKey]) return;
  clearBadMarks();
  keys.splice(selKey + 1, 0, JSON.parse(JSON.stringify(keys[selKey])));
  bumpKeys();
  selKey++;
  recalcTimes(); renderTimeline();
}
function delKey() {
  if (keys.length <= 1 || !keys[selKey]) return;
  clearBadMarks();
  keys.splice(selKey, 1);
  bumpKeys();
  selKey = Math.max(0, selKey - 1);
  recalcTimes(); renderTimeline(); selectKey(selKey);
}
function moveKey(d) {
  const i = selKey, j = i + d;
  if (!keys[i] || !keys[j]) return;
  clearBadMarks();
  [keys[i], keys[j]] = [keys[j], keys[i]];
  bumpKeys();
  selKey = j;
  recalcTimes(); renderTimeline();
}
// How long the move INTO keyframe i takes, as the show would run it. Reads
// the played timeline, so a keyframe that follows a suspended one gets the
// re-timed value rather than the number stored against it.
function keyTravelMs(i) {
  const K = playKeys();
  const at = K.findIndex(k => k.src === i);
  if (at > 0) return K[at].t;                 // its move, as played
  if (at === 0) return 0;                     // the start pose: nowhere to come from
  return keys[i] ? keys[i].t : 0;             // suspended: fall back to its own
}

function selectKey(i) {
  selKey = i;
  if (keys[i]) {
    pose = [...keys[i].pose];
    // travel there at the move's own speed, not at drag speed
    poseChanged(false, keyTravelMs(i));
  }
  renderTimeline();
}
function totalMs() {
  const K = playKeys();
  let t = 0;
  for (let i = 1; i < K.length; i++) t += K[i].t + (K[i].hold || 0);
  t += K.length ? (K[0].hold || 0) : 0;
  return t;
}
function renderTimeline() {
  const box = $("keys");
  box.innerHTML = "";
  keys.forEach((k, i) => {
    const el = document.createElement("div");
    el.className = "key" + (i === selKey ? " sel" : "") + (k.off ? " off" : "");
    el.onclick = (e) => {
      if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") selectKey(i);
    };
    const bar = document.createElement("div"); bar.className = "kbar";
    const idx = document.createElement("div"); idx.className = "kidx";
    // Number, then a name you can type. A timeline of "0 1 2 3 4 5" tells you
    // nothing about what the show does; "wave", "reach cup", "bow" does. The
    // number stays because it is what every message and error refers to.
    idx.textContent = String(i);
    if (i === 0) {
      const st = document.createElement("small");
      st.textContent = " start pose";
      idx.appendChild(st);
    }
    const nm = document.createElement("input");
    nm.className = "kname";
    nm.value = k.name || "";
    nm.placeholder = i === 0 ? "start" : "name this move";
    nm.title = "what this move is, in your words. Saved with the project and "
             + "written into the exported file as a comment.";
    nm.onclick = (e) => e.stopPropagation();      // typing must not re-select
    nm.onchange = () => {
      const v = nm.value.trim();
      if (v) k.name = v; else delete k.name;
      bumpKeys();
      renderTimeline();
    };
    idx.appendChild(nm);
    // Suspend: keep the keyframe but leave it out of the run. For trying a
    // move without deleting the rest, and it never reaches the robot or the
    // exported file until you switch it back on.
    const sk = document.createElement("button");
    sk.className = "kskip";
    sk.textContent = k.off ? "○" : "●";
    sk.title = k.off ? "suspended — click to put this keyframe back in the run"
                     : "suspend: skip this keyframe when playing, exporting and uploading";
    sk.onclick = (e) => {
      e.stopPropagation();
      k.off = !k.off;
      bumpKeys();
      clearBadMarks();          // the moves either side of it just changed
      playT = 0;
      renderTimeline();
      $("tlStat").textContent = anySuspended()
        ? keys.filter(x => x.off).length + " keyframe(s) suspended — they are skipped " +
          "when playing, exporting and uploading"
        : "all keyframes active";
    };
    idx.appendChild(sk);
    const pv = document.createElement("div"); pv.className = "kpose";
    pv.textContent = k.pose.map(a => Math.round(a)).join(" ");
    const kmin = keyMin(i);
    const tr = document.createElement("div"); tr.className = "ktime";
    const tIn = document.createElement("input");
    tIn.type = "number"; tIn.value = k.t; tIn.min = kmin; tIn.step = 50;
    tIn.title = (i === 0 ? "entry time from wherever the robot is (ms)"
                         : "time from previous keyframe (ms)")
              + ` — minimum ${kmin} ms (servo max speed); longer is always allowed`;
    tIn.onchange = () => {
      const want = Math.round(+tIn.value || 0);
      k.t = Math.max(kmin, want);
      delete k.dps;
      bumpKeys();             // a typed time wins over a speed override
      if (want < kmin)
        $("tlStat").textContent = `time raised to ${kmin} ms — the servos can't move that far faster (slowest joint on this move: ${slowestDps()} °/s)`;
      renderTimeline();
    };
    // A move that follows a SUSPENDED keyframe no longer starts where its
    // stored time was written for — it begins from an earlier pose, covers
    // more ground, and is re-timed for real in buildPlayKeys(). The box kept
    // showing the number you typed while the move actually took longer, so
    // the timeline and the robot disagreed with no way to see why. Say what
    // it really runs at, without touching what you set.
    let reNote = null;
    const eff = playKeys().find(x => x.src === i);
    if (eff && Math.round(eff.t) !== Math.round(k.t)) {
      const re = document.createElement("span");
      re.className = "statline";
      re.style.marginLeft = "6px";
      re.textContent = "runs " + Math.round(eff.t) + "ms";
      re.title = "a keyframe before this one is suspended, so this move runs "
               + "between different poses and is re-timed. Your "
               + Math.round(k.t) + " ms comes back when you un-suspend.";
      reNote = re;
    }

    const hIn = document.createElement("input");
    hIn.type = "number"; hIn.value = k.hold || 0; hIn.min = 0; hIn.step = 100;
    hIn.title = "hold this pose (ms) before the next move";
    hIn.onchange = () => { k.hold = Math.max(0, Math.round(+hIn.value || 0)); bumpKeys(); renderTimeline(); };
    tr.append(document.createTextNode("T"), tIn, document.createTextNode("hold"), hIn);
    if (reNote) tr.appendChild(reNote);
    const mn = document.createElement("div");
    mn.className = "ktime";
    if (i === 0) {
      mn.textContent = "min " + kmin + " ms";
    } else {
      // this move's own speed: blank = run at the sequence's speed
      const dIn = document.createElement("input");
      dIn.type = "number"; dIn.min = 5; dIn.max = 600; dIn.step = 5;
      dIn.className = "kdps";
      dIn.value = k.dps ? Math.round(k.dps) : "";
      dIn.placeholder = Math.round(speedDps());
      dIn.title = "this move's own speed (°/s). Empty = the sequence's " +
                  Math.round(speedDps()) + " °/s. Setting it re-times this move; " +
                  "typing a time above clears it again.";
      dIn.onchange = () => {
        const v = Math.round(+dIn.value || 0);
        if (v >= 5) { k.dps = Math.min(v, slowestDps()); k.t = autoTime(keys[i - 1].pose, k.pose, k.dps); }
        else { delete k.dps; k.t = autoTime(keys[i - 1].pose, k.pose, speedDps()); }
        bumpKeys();
        renderTimeline();
      };
      mn.append(document.createTextNode("min " + kmin + " · "), dIn,
                document.createTextNode("°/s"));
    }
    el.append(bar, idx, pv, tr, mn);
    if (k.bad) { // collision found by checkCollisions(): mark the chip red
      el.classList.add("bad");
      const b = document.createElement("div");
      b.className = "kbad";
      b.textContent = "⚠ " + k.bad;
      el.append(b);
    }
    box.appendChild(el);
  });
  $("tlTime").textContent = (playT / 1000).toFixed(1) + "s / " + (totalMs() / 1000).toFixed(1) + "s";
}

// ------- the timeline AS IT PLAYS
// `keys` is the edit list — everything you see in the timeline, including the
// keyframes you have suspended. This is what actually runs: suspended
// keyframes dropped, and the move time into each survivor raised when skipping
// made the jump bigger than its stored time allowed for (suspend the middle of
// 1-2-3 and the move 1->3 is longer than the one 2->3 was timed for).
// `src` maps back to the edit list so warnings land on the right chip.
// Everything about playback, export and collision checking reads THIS.
// tick() asks for the play list up to four times a frame (poseAt, segmentAt,
// segRemaining, the live-follow send). Rebuilding it each time re-runs minTime
// over every joint of every keyframe, so it is cached and thrown away whenever
// the timeline changes. bumpKeys() is the ONE way to invalidate it — anything
// that edits `keys` must call it, or the editor shows a stale run.
// A hand-invalidated cache goes stale silently — one forgotten call and the
// editor shows a run the robot will not perform. So the cache validates itself
// against a cheap signature of exactly the fields buildPlayKeys() reads.
// Reading five numbers per keyframe is far cheaper than re-running minTime over
// ten joints per keyframe, and it CANNOT be wrong: change anything that matters
// and the signature changes with it.
let _pkCache = null;
function keysSignature() {
  let s = keys.length + "|" + speedDps();
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    s += ";" + (k.name || "") + "," + (k.off ? 1 : 0) + "," + k.t + "," + (k.hold || 0) + "," +
         (k.dps || 0) + "," + k.pose;
  }
  return s;
}
function bumpKeys() {
  // the timeline changed: a "yes, run it anyway" given for the old one does
  // not carry over to this
  crashForced = false;
  _pkCache = null;                          // kept for explicit invalidation
  saveDraft();                              // and it is no longer only in RAM
}

// ---- the timeline survives the tab closing -------------------------------
//
// `keys` lived ONLY in memory until someone pressed Save. F5, Ctrl+W, a closed
// lid, or this GPU-heavy three.js page losing its tab took every keyframe with
// it, with no copy anywhere. Hours of posing, gone to a mis-hit key.
//
// The draft is deliberately its OWN localStorage key, never a project file: it
// can therefore never overwrite something the user deliberately saved. It is
// offered back on the next load, and the user chooses.
const DRAFT_KEY = "nong_timeline_draft";
let draftTimer = null;
// Boot builds keyframe 0 itself, and that is not work anybody would mourn.
// Without this the page saved a draft of the untouched default the moment it
// opened, and then warned about "unsaved work" on every single close.
let draftArmed = false;
function saveDraft() {
  if (!draftArmed) return;
  clearTimeout(draftTimer);                 // coalesce a drag into one write
  draftTimer = setTimeout(() => {
    try {
      if (keys.length <= 1) { localStorage.removeItem(DRAFT_KEY); return; }
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        at: Date.now(),
        name: ($("projName") && $("projName").value) || "",
        seq: ($("seqName") && $("seqName").value) || "",
        keys: keys,
      }));
    } catch (e) {
      // storage full or blocked: the draft is a safety net, never a blocker
    }
  }, 400);
}
function offerDraft() {
  let d = null;
  try { d = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); }
  catch (e) { d = null; }
  if (!d || !Array.isArray(d.keys) || d.keys.length <= 1) return;
  if (keys.length > 1) return;              // real work is already on screen
  const when = new Date(d.at || Date.now()).toLocaleString();
  const st = $("tlStat");
  if (st) {
    st.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "There is unsaved work from " + when
      + " (" + d.keys.length + " keyframes). ";
    const yes = document.createElement("button");
    yes.textContent = "Restore it";
    yes.onclick = () => {
      keys = d.keys;
      if (d.name && $("projName")) $("projName").value = d.name;
      if (d.seq && $("seqName")) $("seqName").value = d.seq;
      selKey = 0;
      if (keys.length) pose = [...keys[0].pose];
      bumpKeys(); poseChanged(false); renderTimeline(); renderSliders();
      st.textContent = "Restored the unsaved timeline. Save it to keep it.";
    };
    const no = document.createElement("button");
    no.textContent = "Discard";
    no.onclick = () => {
      try { localStorage.removeItem(DRAFT_KEY); } catch (e) { /* nothing to do */ }
      st.textContent = "";
    };
    st.append(msg, yes, document.createTextNode(" "), no);
  }
}
// Closing with unsaved keyframes asks first. The browser shows its own wording;
// all a page can do is say that there IS something to lose.
window.addEventListener("beforeunload", (e) => {
  if (keys.length <= 1) return;
  let unsaved = false;
  try { unsaved = !!localStorage.getItem(DRAFT_KEY); } catch (err) { unsaved = false; }
  if (!unsaved) return;                     // saveProject() cleared it
  e.preventDefault();
  e.returnValue = "";
});
function playKeys() {
  const sig = keysSignature();
  if (_pkCache && _pkCache.sig === sig) return _pkCache.list;
  const list = buildPlayKeys();
  _pkCache = { sig, list };
  return list;
}
function buildPlayKeys() {
  const out = [];
  let gap = false;                 // was anything suspended since the last one?
  keys.forEach((k, i) => {
    if (k.off) { gap = true; return; }
    const prev = out.length ? out[out.length - 1] : null;
    let t = k.t;
    if (prev && gap) {
      // This move is NOT the one its stored time was written for. With the
      // keyframe before it suspended it now runs between DIFFERENT poses, so
      // the stored number no longer describes anything real — it belongs to a
      // move that is not in the sequence any more.
      //
      // Re-time it at the SPEED that applies (this keyframe's own °/s, else
      // the sequence's). autoTime already floors the result at MIN_MOVE_MS
      // and at the per-joint physical limit, so this can never become a
      // full-speed lunge.
      //
      // It must NOT be max()'d with the stored time. Suspend the middle of
      // home -> somewhere -> home and the remaining move is home -> home:
      // it needs the minimum, but max() held it at the old 400 ms and the arm
      // sat still for 400 ms going nowhere. Re-timing has to be able to
      // shorten a move as well as lengthen it.
      t = autoTime(prev.pose, k.pose, k.dps || speedDps());
    }
    // The name travels with the PLAYED move. buildYaml() writes from this
    // list, so a name left behind here never reaches the exported file.
    out.push({ pose: k.pose, hold: k.hold || 0, src: i, dps: k.dps || 0, t,
               name: k.name || "" });
    gap = false;
  });
  return out;
}
function anySuspended() { return keys.some(k => k.off); }

// ------- playback preview (cosine ease per segment — same as the firmware)
function poseAt(ms) {
  const K = playKeys();
  if (!K.length) return pose;
  let t = K[0].hold || 0;
  if (ms <= t) return [...K[0].pose];
  for (let i = 1; i < K.length; i++) {
    const seg = K[i].t;
    if (ms < t + seg) {
      const f = 0.5 - 0.5 * Math.cos(Math.PI * (ms - t) / seg);
      return K[i - 1].pose.map((a, j) => a + (K[i].pose[j] - a) * f);
    }
    t += seg + (K[i].hold || 0);
    if (ms < t) return [...K[i].pose];
  }
  return [...K[K.length - 1].pose];
}
// Which MOVE is running at ms, or -1 when nothing is moving. The phases mirror
// poseAt() exactly: hold at keyframe 0, move into 1, hold at 1, move into 2 …
// The "in a hold" branch is what makes a hold real on the robot — without it
// this fell through to the NEXT segment the instant a hold began, so the arm
// started its next move immediately, finished early and stood still for the
// rest of the timeline. The pause then looked like it happened at the END
// instead of between the moves.
function segmentAt(ms) {
  const K = playKeys();
  let t = K.length ? (K[0].hold || 0) : 0;
  if (ms <= t) return -1;                      // holding on keyframe 0
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return i;             // moving into keyframe i
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return -1;                     // holding on keyframe i
  }
  return -1;
}
// ---- keeping playback alive when the tab is not in front -------------
// YouTube keeps going in a background tab because a <video> decodes on the
// browser's own media pipeline. Our playback is JavaScript: requestAnimationFrame
// STOPS in a hidden tab and timers are throttled to about once a minute, so a
// live-driven show freezes the moment you click away.
//
// Chrome exempts a page that is PLAYING AUDIO from that throttling, so we hold a
// silent looping track while a sequence is playing, and drive the live sends
// from a timer rather than from the animation frame. That gets browser-driven
// playback most of the way to YouTube behaviour.
//
// It is still best-effort — a browser may throttle anyway, and a phone that
// sleeps will stop regardless. For a SHOW, send the sequence to the robot and
// press Run: the module then plays it from its own clock and the browser can be
// closed entirely. That path is not just more robust, it is more accurate.
// One tick may never advance the show by more than a few frames — see
// playTick(). 120ms is a very slow frame; anything longer is a gap the
// browser took away from us, not time the robot actually spent moving.
const MAX_TICK_MS = 120;
let keepAwakeEl = null, playClock = null;   // NOT liveTimer - that name is already taken by the collision throttle
function keepAwake(on) {
  try {
    if (on) {
      if (!keepAwakeEl) {
        // a one-sample silent wav, inline — no file, no network
        keepAwakeEl = new Audio(
          "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=");
        keepAwakeEl.loop = true;
        keepAwakeEl.volume = 0.0001;   // silent, but genuinely "playing"
      }
      keepAwakeEl.play().catch(() => {});   // blocked before a click: fine
      if (!playClock) playClock = setInterval(playTick, 60);
    } else {
      if (keepAwakeEl) keepAwakeEl.pause();
      if (playClock) { clearInterval(playClock); playClock = null; }
    }
  } catch (e) { /* never let this break playback */ }
}

function togglePlay() {
  const K = playKeys();
  if (K.length < 2) {
    $("tlStat").textContent = keys.length >= 2
      ? "only " + K.length + " keyframe(s) are active — un-suspend some to play"
      : "add at least 2 keyframes to play";
    return;
  }
  // A crashing movement may always be PREVIEWED — watching where it goes wrong
  // is how you fix it. Whether it also reaches the robot is a separate
  // question, and it is asked only when something is actually connected.
  if (!playing) {
    previewOnly = false;
    if (checkCollisions(false).length && (liveLinked() || hubDriven())) {
      previewOnly = !crashGate("PLAY it on the robot");
      if (previewOnly) {
        const st = $("tlStat");
        if (st) st.textContent = "playing the PREVIEW only — the robot is not "
          + "being driven, because this movement crashes";
      }
    }
  }
  playing = !playing;
  $("playBtn").textContent = playing ? "❚❚ Pause" : "▶ Play";
  lastFrame = performance.now();
  lastPlayMs = 0;                 // fresh clock, so a pause never leaps forward
  keepAwake(playing);             // keep the tab off the throttling list
  lastLiveSeg = -1;
  if (playing && playT >= totalMs()) playT = 0;

  // THERE IS ONLY EVER ONE PLAYER.
  //
  // The module keeps a sequence in memory and plays it on its own clock — that
  // is what makes a show survive this page being closed. But it means the
  // module can still be running when you come back, and if this preview then
  // starts streaming poses too, BOTH are driving the same servos: the arm
  // fights itself, and Stop here only stopped the browser, so the module
  // carried on moving on its own.
  //
  // So: taking control here always stops the module first, and giving up
  // control always stops the module too. Never two clocks on one robot.
  stopRobotSequence();
  if (!playing) { livePause(); return; }
  // The HUB plays it when the link goes through the hub: a native process,
  // never throttled, so the show survives this page being hidden or closed —
  // which is the whole reason it exists. This preview keeps drawing, and sends
  // nothing (playTick skips its live sends while hubDriven()).
  if (previewOnly) return;          // refused at the crash gate: draw only
  if (hubDriven()) { hubPlay(playT); return; }
  // A segment is the move INTO a keyframe, so segmentAt() starts at 1 and
  // keyframe 0 is never one of them. Put the robot on it first, or its first
  // move starts from wherever it happens to be standing instead of from the
  // start of the timeline. T is only a request: the firmware floors it per
  // joint, so a short one is stretched to what the servos can really do.
  if (playT === 0 && K.length && liveLinked())
    liveSend("POSE " + K[0].pose.map(fmtA).join(" ") +
             " T " + minTime(pose, K[0].pose));
}
// A segment is handed to the module as one whole move (POSE ... T <ms>) and
// the firmware interpolates it on its own — that is what keeps the motion
// smooth and lets linked boards stay in step. So pausing the editor does NOT
// stop the robot by itself: the module is already carrying out the move and
// runs it to the end. STOP freezes it at the pose it has reached right now.
//
// STOP is a MOTION command, so the firmware also ends any sequence the module
// was playing on its own clock (config/commands.json `"motion": true`). That
// matters here: Pause used to stop only the browser, and a module that was
// mid-show carried on moving — the thing that looked like two shows running
// over each other, because it was.
function liveLinked() {
  return $("liveChk").checked && (haveUsb() || haveWifi());
}
// ---- who holds the clock -------------------------------------------------
//
// THREE CLOCKS, and only one of them may run at a time:
//
//   the module   Run on robot (MOVE)   survives the PC being switched off
//   THE HUB      python main.py        survives this page being closed
//   this browser rAF preview           survives nothing
//
// A hidden tab has rAF stopped and its timers throttled to about once a
// minute — browser policy, not something JavaScript can opt out of. So while a
// link goes THROUGH the hub, the hub plays the show and this page only draws
// it. Web Serial (USB direct) is the exception: the browser holds the port
// itself, so the hub cannot reach the robot and the old browser clock stands.
function hubDriven() {
  return liveLinked() && !usbDirect();
}
// What the hub is asked to play: the same keyframes this preview runs, with
// the same times. `t` on the first one is how long the robot may take to reach
// the start pose from wherever it is standing.
function hubShowSteps() {
  const K = playKeys();
  if (K.length < 2) return null;
  return K.map((k, i) => ({
    pose: k.pose.map(v => +fmtA(v)),
    t: i === 0 ? minTime(pose, K[0].pose) : k.t,
    hold: k.hold || 0,
  }));
}
async function hubPlay(fromMs) {
  const steps = hubShowSteps();
  if (!steps) return false;
  try {
    const r = await fetch("/api/play", {
      method: "POST",
      body: JSON.stringify({
        dev: moduleDev(), steps, loop: $("loopChk").checked,
        name: ($("seqName").value || "sequence").trim(), from_ms: Math.round(fromMs || 0),
      }),
    }).then(r => r.json());
    if (r.error) throw new Error(r.error);
    $("robotStat").textContent =
      "the HUB is playing this — it keeps going with this page closed or hidden. " +
      "Pause or Stop here ends it.";
    return true;
  } catch (e) {
    $("robotStat").textContent = "The hub could not start the show, so the robot "
      + "did not move. Check the hub is still running, then press Play again. "
      + (e.message || e);
    return false;
  }
}
function hubStop() {
  return fetch("/api/play/stop", { method: "POST" }).catch(() => {});
}
function livePause() {
  if (!liveLinked()) return;
  hubStop();          // whichever clock is running, this ends it
  liveAbort();        // drop moves not yet sent — pausing cancels them
  liveSend("STOP");
  lastLiveSeg = -1;   // resume re-sends the segment, with the time still left
}
// ms left in the segment playT is inside — what a resume must ask for, or the
// robot would replay the whole segment while the editor plays only its tail.
function segRemaining(ms) {
  const K = playKeys();
  let t = K.length ? (K[0].hold || 0) : 0;
  if (ms <= t) return 0;
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return Math.max(1, Math.round(t + K[i].t - ms));
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return 0;                      // in a hold, nothing is running
  }
  return 0;
}
function scrubTo(v) {
  const was = playing;
  playing = false; $("playBtn").textContent = "▶ Play";
  // Every other stop path releases the keep-awake; this one did not, so
  // scrubbing during playback left playClock firing every 60 ms and the silent
  // <audio> element "playing" for the life of the page. Nothing looked wrong —
  // playTick returns immediately while !playing — it just burned CPU and
  // battery forever, and kept the tab permanently exempt from throttling.
  if (was) { livePause(); stopRobotSequence(); keepAwake(false); }
  playT = totalMs() * (+v / 1000);
  pose = poseAt(playT).map((v,i)=>clampJ(i,v));
  applyPose(); renderSliders(); renderTimeline();
  // Take the ARM there too. Scrubbing is how you check a move without playing
  // the whole show - a preview that moves while the robot stays put is the one
  // thing you cannot check against. Uses the same path a slider drag does, so
  // it carries the link's own round-trip timing rather than letting the module
  // ease at its SPEED setting.
  if (liveLinked()) sendPoseLive();
}

// ---------------------------------------------------------------- YAML export
function fmtA(a) { return (Math.round(a * 10) / 10).toString(); }
function buildYaml() {
  const name = ($("seqName").value || "sequence").trim().replace(/[^\w.-]+/g, "_");
  const lines = [
    "# generated by Nong Studio (code/nong/main_python_set_nong)",
    "# pose order: " + JOINT_NAMES.join(" ") + "  (joint deg, T = ms)",
    "name: " + name,
    "loop: " + ($("loopChk").checked ? "true" : "false"),
    "steps:",
  ];
  // The show speed belongs to the SEQUENCE, not to the editor: it is written
  // as the first step so the module applies it when this file starts. That
  // also makes a chain deterministic — sequence B sets its own speed instead
  // of inheriting whatever A happened to leave the module on.
  // One source of truth: the editor reads this step back when re-editing.
  let cur = Math.round(speedDps());
  lines.push(`  - speed: ${cur}`);
  // suspended keyframes are left out entirely — the robot never sees them
  playKeys().forEach((k, i) => {
    // a move with its own speed emits a speed step first, and the next move
    // without one puts the sequence speed back — so the file reads exactly as
    // the timeline runs, and the module's speed tracks it move by move
    const want = Math.round(k.dps || speedDps());
    if (i > 0 && want !== cur) { lines.push(`  - speed: ${want}`); cur = want; }
    // The name you gave the move, as a comment above it. A comment so
    // every existing player still reads the file unchanged — the
    // firmware ignores it, and a person opening the YAML can see what
    // each step was meant to be.
    if (k.name) lines.push(`  # ${k.name.replace(/[\r\n]/g, " ")}`);
    lines.push(`  - pose: "${k.pose.map(fmtA).join(" ")} T ${k.t}"` +
               (i === 0 ? "    # start pose" : ""));
    if (k.hold > 0) lines.push(`  - wait: ${k.hold}`);
  });
  const next = ($("seqNext").value || "").trim().replace(/[^\w.-]+/g, "");
  if (next) {
    // chain: when this sequence ends the module starts that one, so a show can
    // be built from short files instead of one long one
    lines.splice(4, 0, "next: " + (next.endsWith(".yaml") ? next : next + ".yaml"));
  }
  return { name, yaml: lines.join("\n") + "\n" };
}
// Guard on what will actually be WRITTEN, not on how many keyframes exist:
// with everything suspended the timeline is full but the file would carry no
// moves at all, and the robot would "run" a sequence that does nothing.
function nothingToWrite(where) {
  if (playKeys().length) return false;
  $(where).textContent = keys.length
    ? "every keyframe is suspended — un-suspend at least one to export or upload"
    : "no keyframes yet";
  return true;
}
async function exportYaml() {
  if (nothingToWrite("tlStat")) return;
  const { name, yaml } = buildYaml();
  const r = await fetch("/api/export", {
    method: "POST", body: JSON.stringify({ name: name + ".yaml", yaml }),
  }).then(r => r.json());
  $("tlStat").innerHTML = r.ok
    ? `saved <b>${r.file}</b> in the sequences/ folder — copy it to the SD card /moves/, ` +
      `then pick it on the module website (Sequences card) or send: MOVE ${r.file}`
    : "export failed: " + r.error;
  refreshSeqs();
}

// ---------------------------------------------------------------- rig setup UI
const DIM_LABELS = {
  shoulderX: "shoulder ±X", shoulderY: "shoulder Y",
  upperLenL: "L upper arm", upperLenR: "R upper arm",
  foreLenL: "L forearm", foreLenR: "R forearm",
  torsoW: "torso W", torsoH: "torso H", torsoD: "torso D",
  shrugPivot: "shrug pivot ↑ (mm above shoulders)",
};
function renderRigUI() {
  const jb = $("rigJoints");
  jb.innerHTML = "";
  // header
  const hdr = document.createElement("div"); hdr.className = "rigjrow";
  ["joint", "zero°", "min°", "max°", "axis", "inv"].forEach(t => {
    const s = document.createElement("span"); s.className = "mini"; s.textContent = t;
    hdr.appendChild(s);
  });
  jb.appendChild(hdr);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div"); row.className = "rigjrow";
    const name = document.createElement("span"); name.className = "jname"; name.textContent = label;
    const zero = document.createElement("input");
    zero.type = "number"; zero.min = 0; zero.max = 180; zero.value = RIG.zero[i];
    zero.title = "zero deg: joint angle where this joint is straight (arm along the body)";
    zero.onchange = () => { RIG.zero[i] = clampDeg(+zero.value); rigChanged(); };
    const lo = document.createElement("input");
    lo.type = "number"; lo.min = 0; lo.max = 180; lo.value = RIG.min[i];
    lo.title = "minimum JOINT angle this joint can reach";
    // clampDeg, like `zero` two lines up. The min="0" max="180" attributes only
    // bound the spinner arrows — a TYPED value goes straight through. So
    // "-500" became this joint's minimum, was written to the robot's SD card by
    // "Send limits + gear to robot" as LIMIT <j> -500 150, and from then on
    // clampJ allowed poses far outside the joint's real travel. A typo in the
    // editor should not become a persistent hardware setting.
    lo.onchange = () => {
      RIG.min[i] = Math.min(clampDeg(+lo.value || 0), RIG.max[i] - 1);
      lo.value = RIG.min[i];               // show what was actually accepted
      rigChanged();
    };
    const hi = document.createElement("input");
    hi.type = "number"; hi.min = 0; hi.max = 180; hi.value = RIG.max[i];
    hi.title = "maximum JOINT angle this joint can reach";
    hi.onchange = () => {
      RIG.max[i] = Math.max(clampDeg(+hi.value || 0), RIG.min[i] + 1);
      hi.value = RIG.max[i];
      rigChanged();
    };
    const ax = document.createElement("select");
    ax.title = "which way this joint rotates: roll (X), pitch (Y) or yaw (Z)";
    ["x", "y", "z"].forEach(v => {
      const o = document.createElement("option"); o.value = v; o.textContent = AXIS_LABEL[v];
      if (RIG.axis[i] === v) o.selected = true;
      ax.appendChild(o);
    });
    ax.onchange = () => { RIG.axis[i] = ax.value; rigChanged(); };
    const inv = document.createElement("label"); inv.style.justifySelf = "center";
    const chk = document.createElement("input");
    chk.type = "checkbox"; chk.checked = !!RIG.invert[i];
    chk.onchange = () => { RIG.invert[i] = chk.checked ? 1 : 0; rigChanged(); };
    inv.append(chk);
    row.append(name, zero, lo, hi, ax, inv);
    jb.appendChild(row);
  });
  // PER-JOINT servo + gear (each joint can use a different servo)
  const svh = document.createElement("div"); svh.className = "tlabel";
  svh.style.marginTop = "8px";
  svh.textContent = "servo & gear per joint (pinion:gear, pulse µs, max °/s, travel°, Hz):";
  jb.appendChild(svh);
  const presetRow = document.createElement("div"); presetRow.className = "row";
  const pl = document.createElement("span"); pl.className = "lbl"; pl.textContent = "preset";
  const psel = document.createElement("select");
  psel.innerHTML = "<option value=''>apply a servo to…</option>" +
    Object.keys(SERVO_TYPES).map(t => {
      const s = SERVO_TYPES[t];
      const nm = s.label + " (" + s.range + "°)";
      return `<option value="${t}|sh">${nm} → shoulders</option>` +
             `<option value="${t}|el">${nm} → elbows</option>` +
             `<option value="${t}|waist">${nm} → waist</option>` +
             `<option value="${t}|shrug">${nm} → shrug</option>` +
             `<option value="${t}|all">${nm} → all</option>`;
    }).join("");
  psel.onchange = () => { if (psel.value) { applyServoPreset(psel.value); psel.value = ""; } };
  presetRow.append(pl, psel);
  jb.appendChild(presetRow);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div"); row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 38px 38px 50px 50px 44px 44px 44px";
    const name = document.createElement("span");
    name.className = "jname"; name.textContent = label;
    row.appendChild(name);
    const mk = (key, min, title, max) => {
      const inp = document.createElement("input");
      inp.type = "number"; inp.min = min; inp.value = RIG[key][i]; inp.title = title;
      if (max) inp.max = max;
      inp.onchange = () => {
        let v = +inp.value || RIG[key][i];
        v = Math.max(min, max ? Math.min(max, v) : v);
        RIG[key][i] = v; inp.value = v;
        rigChanged(); renderRigUI();   // the travel warning may have changed
      };
      row.appendChild(inp);
    };
    mk("gearPinion", 1, "pinion teeth (on the servo)");
    mk("gearGear", 1, "gear teeth (on the joint)");
    mk("pulseMin", 100, "servo pulse minimum (µs)");
    mk("pulseMax", 200, "servo pulse maximum (µs)");
    mk("servoMaxDps", 30, "this servo's physical speed limit (°/s of the joint)");
    mk("servoRange", 60,
       "SERVO travel: how far this servo turns end to end. 180 = normal hobby " +
       "servo, 270 = wide-angle. NOT the joint's range (that is min°/max° above).",
       360);
    mk("frameHz", 40,
       "SERVO frame rate (Hz). 50 = normal hobby servo; the PDI-1181MG is a " +
       "330 Hz digital servo. A wrong rate can make a digital servo cut torque.",
       400);
    jb.appendChild(row);
    // does the servo have enough travel for the joint limits asked of it?
    const w = travelWarning(i);
    if (w) {
      const warn = document.createElement("div");
      warn.className = "mini"; warn.style.color = "var(--warn)";
      warn.style.margin = "0 0 4px 78px";
      warn.textContent = "⚠ " + w;
      jb.appendChild(warn);
    }
  });
  const gm = document.createElement("div"); gm.className = "mini";
  gm.textContent = "columns: pinion : gear · pulse min · pulse max · max °/s · servo travel°. " +
    "The robot converts joint→servo with each joint's own ratio and travel, so a 270° " +
    "shoulder and a 180° elbow both drive correctly. Fitting a wider servo later = " +
    "change travel° (and the pulse range) on that joint — every saved pose still works, " +
    "because poses are joint degrees. Push with the button below.";
  jb.appendChild(gm);

  // per-joint / per-bar SIZES (each joint ball and each bar can differ)
  const sh2 = document.createElement("div"); sh2.className = "tlabel";
  sh2.style.marginTop = "8px";
  sh2.textContent = "sizes (mm radius) — joint ball / bar thickness:";
  jb.appendChild(sh2);
  const SIZE_LABELS = ["L shoulder", "L elbow", "R shoulder", "R elbow"];
  const BAR_LABELS = ["L upper arm", "L forearm", "R upper arm", "R forearm"];
  SIZE_LABELS.forEach((label, i) => {
    const row = document.createElement("div"); row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 1fr 1fr";
    const name = document.createElement("span");
    name.className = "jname"; name.textContent = label;
    const jr = document.createElement("input");
    jr.type = "number"; jr.min = 2; jr.max = 200; jr.value = RIG.jointR[i];
    jr.title = "radius of the " + label + " joint ball (mm)";
    jr.onchange = () => { RIG.jointR[i] = Math.max(2, +jr.value || RIG.jointR[i]); rigChanged(); };
    const br = document.createElement("input");
    br.type = "number"; br.min = 1; br.max = 200; br.value = RIG.barR[i];
    br.title = "thickness (radius) of the " + BAR_LABELS[i] + " bar (mm)";
    br.onchange = () => { RIG.barR[i] = Math.max(1, +br.value || RIG.barR[i]); rigChanged(); };
    row.append(name, jr, br);
    jb.appendChild(row);
  });
  const sizeHint = document.createElement("div");
  sizeHint.className = "mini";
  sizeHint.textContent = "left box = joint ball, right box = the bar below it " +
    "(L shoulder→upper arm, L elbow→forearm, …). Bar lengths are in the sizes list below.";
  jb.appendChild(sizeHint);

  // per-joint axis TILT (roll/pitch/yaw deg) — for joints not exactly at 90°
  const th = document.createElement("div"); th.className = "tlabel";
  th.style.marginTop = "8px";
  th.textContent = "axis tilt (° roll/pitch/yaw) — for joints not exactly at 90°:";
  jb.appendChild(th);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div"); row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 1fr 1fr 1fr";
    const name = document.createElement("span"); name.className = "jname"; name.textContent = label;
    row.appendChild(name);
    ["roll", "pitch", "yaw"].forEach((axName, k) => {
      const inp = document.createElement("input");
      inp.type = "number"; inp.step = 1; inp.value = RIG.tilt[i][k];
      inp.title = axName + " tilt of this joint's axis (deg)";
      inp.onchange = () => { RIG.tilt[i][k] = +inp.value || 0; rigChanged(); };
      row.appendChild(inp);
    });
    jb.appendChild(row);
  });

  renderShrugCurve();

  const db = $("rigDims");
  db.innerHTML = "";
  Object.entries(DIM_LABELS).forEach(([k, label]) => {
    const row = document.createElement("div"); row.className = "jrow";
    const name = document.createElement("span"); name.className = "jname"; name.textContent = label;
    const lo = (k === "shrugPivot") ? 0 : 5;   // pivot may sit on the shoulder line (0)
    const inp = document.createElement("input");
    inp.type = "number"; inp.min = lo; inp.max = 1000; inp.value = RIG.dims[k];
    inp.onchange = () => { RIG.dims[k] = Math.max(lo, +inp.value || 0); rigChanged(); };
    row.append(name, inp, document.createElement("span"));
    db.appendChild(row);
  });
}
// known servos — pulse range, physical speed and TRAVEL (how far the servo
// itself turns end to end: 180 for a normal hobby servo, 270 for a wide-angle
// one). Add more here, or just type the numbers on the joint's row.
// Keep this table in step with the firmware's SERVO command (NongModule.cpp).
// Servo presets come from the ONE shared table (firmware/config/servos.json),
// fetched from the hub at startup — the firmware compiles the same file into a
// header, so adding a servo is one edit and the two sides cannot drift.
// The literals below are only a fallback for opening this page without the hub.
let SERVO_TYPES = {
  mg90s:      { label: "MG90S",      min: 500, max: 2400, dps: 400, range: 180, hz: 50 },
  pdi1181mg:  { label: "PDI-1181MG", min: 500, max: 2500, dps: 375, range: 270, hz: 50 },
  tiankong35: { label: "TianKongRC 35kg", min: 500, max: 2500, dps: 250, range: 270, hz: 50 },
  generic180: { label: "generic 180", min: 500, max: 2500, dps: 300, range: 180, hz: 50 },
  generic270: { label: "generic 270", min: 500, max: 2500, dps: 300, range: 270, hz: 50 },
};
async function loadServoTypes() {
  try {
    const r = await fetch("/api/servos").then(r => r.json());
    if (r && r.ok && r.servos && Object.keys(r.servos).length) {
      SERVO_TYPES = r.servos;
      if (typeof renderRigUI === "function") renderRigUI();   // redraw the dropdown
    }
  } catch (e) { /* no hub: the fallback above stands */ }
}
loadServoTypes();
// joints 0,1,4,5 = shoulders; 2,3,6,7 = elbows; 8 = WAIST; 9 = SHRUG
function isShoulderJoint(i) { return i === 0 || i === 1 || i === 4 || i === 5; }
function isElbowJoint(i) { return i === 2 || i === 3 || i === 6 || i === 7; }
function applyServoPreset(val) {
  const [type, where] = val.split("|");
  const s = SERVO_TYPES[type];
  if (!s) return;
  const hit = i => where === "all" ||
    (where === "sh" && isShoulderJoint(i)) ||
    (where === "el" && isElbowJoint(i)) ||
    (where === "waist" && i === 8) ||
    (where === "shrug" && i === 9);
  for (let i = 0; i < NJ; i++) {
    if (!hit(i)) continue;
    RIG.pulseMin[i] = s.min; RIG.pulseMax[i] = s.max;
    RIG.servoMaxDps[i] = s.dps; RIG.servoRange[i] = s.range;
    RIG.frameHz[i] = s.hz;
  }
  rigChanged();
  renderRigUI();
  const wLabel = { sh: "the shoulders", el: "the elbows", waist: "the waist",
                   shrug: "the shrug", all: "all joints" }[where] || where;
  $("limStat").textContent = s.label + " applied to " + wLabel +
    " — press “Send limits + gear to robot” to push it";
}
// A joint asks the servo for (joint travel from neutral) × gear/pinion degrees
// of SERVO travel. Warn when that is more than the servo physically has: the
// robot clamps, so the joint would silently stop short of its limit.
function travelWarning(i) {
  const range = RIG.servoRange[i] || 180;
  const ratio = (RIG.gearGear[i] || 1) / (RIG.gearPinion[i] || 1);
  const need = Math.max(90 - RIG.min[i], RIG.max[i] - 90) * ratio;  // deg from centre
  const have = range / 2;
  if (need <= have + 0.01) return null;
  const reach = 90 + have / ratio;      // joint deg actually reachable
  return `this joint needs ±${need.toFixed(0)}° of servo travel but a ${range}° ` +
         `servo only gives ±${have.toFixed(0)}° — it will stop at about ` +
         `${(180 - reach).toFixed(0)}°–${reach.toFixed(0)}°. ` +
         `Use a wider servo (270°), a smaller gear ratio, or tighter min°/max°.`;
}
function rigChanged() {
  saveRig();
  buildRobot();
  renderSliders();
}
function resetRig() {
  // Reset returns to YOUR saved default if you set one, else the factory rig.
  const mine = loadRigDefault();
  if (mine) {
    RIG = mine;
  } else {
    if (!confirm("Reset the rig to the factory defaults? (You haven't saved a " +
                 "default of your own — use “★ Save current as default” to keep " +
                 "your tuning.)")) return;
    RIG = JSON.parse(JSON.stringify(DEFAULT_RIG));
  }
  saveRig();
  renderRigUI();
  buildRobot();
}
// send the per-joint limits + gear to the connected module (LIMIT/GEAR
// commands — the module clamps to them and saves to its SD card)
// Send the rig to the robot. 5 commands x 10 joints is 50 round trips, so ask
// the robot what it already has (LIMIT? returns every field in one reply) and
// send only the lines that differ — pushing again after a small edit is then a
// couple of commands instead of fifty.
async function pushLimits() {
  if (!haveUsb() && !haveWifi()) { $("limStat").textContent = "connect to the robot first (Robot link card)"; return; }
  try {
    let have = null;
    $("limStat").textContent = "reading what the robot has…";
    try { have = JSON.parse(await rawCmd("LIMIT?")); } catch (e) { have = null; }
    const at = (key, i) => {
      const a = have && have[key];
      return Array.isArray(a) && a[i] !== undefined ? Number(a[i]) : null;
    };
    const same = (key, i, v) => at(key, i) !== null && at(key, i) === v;

    // One line per joint that differs, not one per FIELD. JCFG carries a
    // joint's whole setup, so "send rig" is at most 10 commands instead of up
    // to 50 — about 1.6 s down to 0.3 s. `parts` keeps the individual commands
    // ready in case the board is older than JCFG.
    const jobs = [];
    for (let i = 0; i < NJ; i++) {
      const mn = Math.round(RIG.min[i]), mx = Math.round(RIG.max[i]);
      const pmin = RIG.pulseMin[i], pmax = RIG.pulseMax[i];
      const dps = Math.round(RIG.servoMaxDps[i]);
      const rng = Math.round(RIG.servoRange[i]), hz = Math.round(RIG.frameHz[i]);
      const parts = [];
      if (!(same("min", i, mn) && same("max", i, mx)))
        parts.push(`LIMIT ${i + 1} ${mn} ${mx}`);
      if (!(same("gear_pinion", i, RIG.gearPinion[i]) && same("gear_gear", i, RIG.gearGear[i])))
        parts.push(`GEAR ${i + 1} ${RIG.gearPinion[i]} ${RIG.gearGear[i]}`);
      if (!(same("pulse_min", i, pmin) && same("pulse_max", i, pmax) && same("max_dps", i, dps)))
        parts.push(`PULSE ${i + 1} ${pmin} ${pmax} ${dps}`);
      if (!same("servo_range", i, rng)) parts.push(`RANGE ${i + 1} ${rng}`);
      if (!same("frame_hz", i, hz)) parts.push(`RATE ${i + 1} ${hz}`);
      if (!parts.length) continue;
      jobs.push({
        joint: i + 1, parts,
        batch: `JCFG ${i + 1} ${RIG.gearPinion[i]} ${RIG.gearGear[i]} ${pmin} ${pmax} ` +
               `${dps} ${rng} ${hz} ${mn} ${mx}`,
      });
    }
    if (!jobs.length) {
      $("limStat").textContent = "robot already matches this rig — nothing to send ✓";
      return;
    }

    let useBatch = true, sent = 0;
    for (let k = 0; k < jobs.length; k++) {
      const job = jobs[k];
      $("limStat").textContent = `sending joint ${job.joint} (${k + 1}/${jobs.length})…`;
      if (useBatch) {
        const r = await rawCmd(job.batch);
        sent++;
        // an older board does not know JCFG — drop to the individual commands
        // for this joint and every one after it
        if (/unknown cmd|ERR usage/i.test(r || "")) { useBatch = false; sent--; }
        else continue;
      }
      for (const c of job.parts) { await rawCmd(c); sent++; }
    }
    $("limStat").textContent =
      `sent ${sent} command${sent > 1 ? "s" : ""} for ${jobs.length} joint` +
      `${jobs.length > 1 ? "s" : ""} (limits, gear, pulse, travel, frame rate)` +
      (useBatch ? "" : " — this board is older than JCFG, so each setting went separately") +
      (have ? "" : " — could not read the robot first, so everything was sent") + " ✓";
  } catch (e) { $("limStat").textContent = "send failed: " + (e.message || e); }
}
// read the module's current limits + gear back into the rig
async function pullLimits() {
  if (!haveUsb() && !haveWifi()) { $("limStat").textContent = "connect to the robot first"; return; }
  try {
    const t = await rawCmd("LIMIT?");
    const j = JSON.parse(t);
    // accept 8-joint (old firmware) or 10-joint replies: keep what the robot
    // sends and fill any joint it omits from the current rig, so a shorter
    // reply never wipes the WAIST/SHRUG settings.
    const pull = (src, key) => {
      if (Array.isArray(src)) RIG[key] = RIG[key].map((d, i) =>
        (src[i] !== undefined ? Number(src[i]) : d));
      else if (typeof src === "number") RIG[key] = new Array(NJ).fill(+src);
    };
    pull(j.min, "min");
    pull(j.max, "max");
    pull(j.gear_pinion, "gearPinion");
    pull(j.gear_gear, "gearGear");
    pull(j.pulse_min, "pulseMin");
    pull(j.pulse_max, "pulseMax");
    pull(j.max_dps, "servoMaxDps");
    pull(j.servo_range, "servoRange");
    pull(j.frame_hz, "frameHz");
    saveRig(); renderRigUI(); buildRobot(); renderSliders();
    $("limStat").textContent = "read limits + gear from the robot ✓";
  } catch (e) { $("limStat").textContent = "read failed: " + (e.message || e); }
}

// ---------------------------------------------------------------- edit existing sequences
// Parse a /moves YAML (the format this editor exports and the firmware plays)
// back into timeline keyframes, so any saved sequence can be re-edited.
function parseSeqYaml(text) {
  const out = { name: "", loop: false, next: "", speed: 0, keys: [], skipped: 0 };
  let curSpeed = 0;             // the speed in force at this point in the file
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, "").trimEnd();
    let m;
    if ((m = line.match(/^name:\s*(.+)$/))) out.name = m[1].trim();
    else if ((m = line.match(/^next:\s*(.+)$/))) out.next = m[1].trim();
    else if ((m = line.match(/^loop:\s*(true|false)/))) out.loop = m[1] === "true";
    else if ((m = line.match(/^\s*-\s*pose:\s*"?([\d.\s]+?)(?:\s+T\s+(\d+))?"?\s*$/))) {
      const nums = m[1].trim().split(/\s+/).map(Number);
      // 8 = an OLD arms-only pose (before WAIST/SHRUG) — pad the two body
      // joints with 90 (neutral) so it still loads; 10 = a current pose.
      if ((nums.length === ARMJ || nums.length === NJ) && nums.every(n => !isNaN(n))) {
        while (nums.length < NJ) nums.push(90);
        const k = { pose: nums.map((v,i)=>clampJ(i,v)), t: m[2] ? +m[2] : 0, hold: 0 };
        // a speed step before this pose that differs from the sequence speed is
        // that MOVE's own speed, so it survives a round trip through the file
        if (curSpeed && curSpeed !== out.speed) k.dps = curSpeed;
        out.keys.push(k);
      } else out.skipped++;
    } else if ((m = line.match(/^\s*-\s*wait:\s*(\d+)/))) {
      if (out.keys.length) out.keys[out.keys.length - 1].hold = +m[1];
      else out.skipped++;
    } else if ((m = line.match(/^\s*-\s*speed:\s*([\d.]+)/))) {
      // the FIRST speed step is the sequence's own speed; later ones belong to
      // the move that follows them. Neither is an unsupported step.
      curSpeed = +m[1];
      if (!out.speed) out.speed = curSpeed;
    } else if (/^\s*-\s*\w+:/.test(line)) out.skipped++; // rgb/play/... steps
  }
  return out;
}
function loadParsedSeq(p, sourceLabel) {
  if (!p.keys.length) {
    $("tlStat").textContent = "no pose steps found in " + sourceLabel;
    return;
  }
  keys = p.keys;
  bumpKeys();
  // The file's own speed comes back with it. Set it BEFORE filling in any
  // missing times (autoTime reads it), and never re-time the keyframes that
  // already carry a T — the times in the file are what the show was built on.
  if (p.speed >= 5) $("speedDps").value = Math.min(p.speed, slowestDps());
  for (let i = 0; i < keys.length; i++)
    if (!keys[i].t) keys[i].t = i ? autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i)) : 1000;
  clampKeyTimes();
  $("loopChk").checked = p.loop;
  $("seqNext").value = p.next || "";   // keep the chain when re-editing
  if (p.name) { $("seqName").value = p.name; $("projName").value = p.name; }
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  $("tlStat").textContent = `loaded ${keys.length} keyframes from ${sourceLabel}` +
    (p.speed >= 5 ? ` at its own ${Math.round(p.speed)} °/s` : "") +
    (p.skipped ? ` (${p.skipped} non-pose steps skipped — rgb/music steps are kept only in the original file)` : "") +
    " — edit, then Export / Upload again";
}
async function editLocalSeq() {
  const f = $("seqList").value;
  if (!f) return;
  const text = await fetch("/api/loadseq?name=" + encodeURIComponent(f)).then(r => r.text());
  loadParsedSeq(parseSeqYaml(text), "sequences/" + f);
}
async function editSdSeq(fname) {
  try {
    const text = await sdDownload(fname);
    loadParsedSeq(parseSeqYaml(text), "robot SD " + fname);
  } catch (e) { $("tlStat").textContent = "cannot read " + fname + ": " + (e.message || e); }
}
async function refreshSeqs() {
  const r = await fetch("/api/list?kind=sequences").then(r => r.json());
  const sel = $("seqList");
  sel.innerHTML = "<option value=''>Edit saved…</option>";
  (r.files || []).filter(f => f.endsWith(".yaml")).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}

// ---------------------------------------------------------------- project save/load
async function saveProject() {
  const name = ($("projName").value || "project").trim();
  const project = {
    keys, speedDps: speedDps(), maxDps: maxDps(), loop: $("loopChk").checked,
    meshes: meshCfg, addons,
    robotIp: $("robotIp").value, seqName: $("seqName").value,
    rig: RIG,
  };
  let r;
  try {
    r = await fetch("/api/save", {
      method: "POST", body: JSON.stringify({ name, project }),
    }).then(r => r.json());
  } catch (e) {
    // The draft is NOT cleared here: the work is still only in this browser.
    $("tlStat").textContent = "could not save — the hub is not answering. Your "
      + "work is still here, and is kept in this browser. " + (e.message || e);
    return;
  }
  if (!r || !r.ok) {
    $("tlStat").textContent = "could not save: " + ((r && r.error) || "unknown")
      + ". Your work is still here.";
    return;
  }
  // Safely on disk now, so the unsaved-work draft has done its job.
  try { localStorage.removeItem(DRAFT_KEY); } catch (e) { /* nothing to do */ }
  $("tlStat").textContent = r.replaced
    ? "saved over the existing " + r.file + " (the previous version is kept as "
      + r.file + ".bak)"
    : "project saved: " + r.file;
  refreshProjects();
}
async function loadProject(file) {
  if (!file) return;
  // NOTHING is replaced until the whole file has been read and understood.
  //
  // Three ways this used to destroy work, all from assigning as it went:
  //   * a 404 or a renamed file still parses as JSON (the hub answers
  //     {"ok":false,...} and fetch does not reject), so `p.keys || []` wiped
  //     the timeline to empty and said nothing. Pressing Save afterwards wrote
  //     the empty version over a real project.
  //   * a project from before WAIST and SHRUG carries 8-value poses. minTime()
  //     then subtracted two undefined values, and the NaN it produced was
  //     written into EVERY keyframe time by clampKeyTimes() — so the export
  //     carried "T NaN" and that went down the cable to the robot.
  //   * the project's rig replaced the live rig outright. Hours of tuning
  //     (zero, tilt, dims, jointR, neutral, invert, shrugCurve exist nowhere
  //     else) vanished with no prompt and no undo.
  let p;
  try {
    const r = await fetch("/api/load?name=" + encodeURIComponent(file));
    p = await r.json();
    if (!r.ok || p.ok === false) throw new Error(p.error || ("could not read " + file));
  } catch (e) {
    const st = $("tlStat");
    if (st) st.textContent = "could not load " + file + " — " + (e.message || e)
      + ". Nothing on screen was changed.";
    return;                              // the timeline stays exactly as it was
  }
  if (!Array.isArray(p.keys)) {
    const st = $("tlStat");
    if (st) st.textContent = file + " has no keyframes in it, so nothing was loaded.";
    return;
  }
  // Repair the poses BEFORE they reach anything: pad short ones to NJ, drop
  // non-numbers, and clamp to each joint's real travel.
  const loaded = p.keys.filter(k => k && Array.isArray(k.pose)).map(k => {
    const q = k.pose.slice(0, NJ).map(Number);
    while (q.length < NJ) q.push(90);    // pre-WAIST/SHRUG project: neutral
    return { ...k, pose: q.map((v, i) => clampJ(i, Number.isFinite(v) ? v : 90)) };
  });
  // A project carries the rig it was built with. That is worth having, but it
  // is not worth losing today's tuning to — so ask, and default to keeping
  // what is on screen.
  let takeRig = false;
  if (p.rig) {
    takeRig = confirm(
      "This project was saved with its own robot setup (joint limits, gears, "
      + "pulse ranges, zero offsets).\n\n"
      + "OK  — use the project's setup\n"
      + "Cancel — keep the setup you have now (recommended)");
  }
  keys = loaded;
  bumpKeys();
  $("speedDps").value = p.speedDps || 120;
  $("maxDps").value = p.maxDps || 400;
  clampKeyTimes();
  $("loopChk").checked = !!p.loop;
  $("robotIp").value = p.robotIp || "";
  $("seqName").value = p.seqName || file.replace(/\.json$/, "");
  $("projName").value = file.replace(/\.json$/, "");
  if (p.meshes) {
    MESH_PARTS.forEach(part => {
      const v = p.meshes[part];
      if (v === undefined) return;
      // old projects stored just the filename; new ones store the full config
      meshCfg[part] = typeof v === "string"
        ? { ...defMeshCfg(part), file: v, scale: p.stlScale || 1 }
        : { ...defMeshCfg(part), ...v };
    });
  }
  addons = p.addons || addons;
  saveMeshes();
  if (p.rig && takeRig) {
    // Keep one step back. The rig is the most expensive thing in this editor
    // to rebuild, so replacing it always leaves a copy to return to.
    try { localStorage.setItem("nong_rig_prev", JSON.stringify(RIG)); }
    catch (e) { /* storage full: the swap still happens, just without undo */ }
    RIG = mergeRig(p.rig);
    saveRig();
  }
  await refreshModels();
  renderRigUI();
  buildRobot(); // re-applies meshes + rig in one pass
  selKey = 0;
  if (keys.length) { pose = [...keys[0].pose]; }
  poseChanged(false); renderTimeline();
}
async function refreshProjects() {
  const r = await fetch("/api/list?kind=projects").then(r => r.json());
  const sel = $("projList");
  sel.innerHTML = "<option value=''>Load…</option>";
  (r.files || []).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}

// ---------------------------------------------------------------- STL meshes
// Each part keeps its SKELETON (joint ball + bone) visible even with an STL,
// so joint positions and lengths always stay readable. Every STL has its own
// rotation / offset / scale (exports rarely share the robot's origin), and
// assigning an STL measures its size to set the rig lengths automatically.
const stlLoader = new THREE.STLLoader();
const stlCache = {};   // file -> BufferGeometry
let meshGen = 0;       // invalidates async STL loads after a rebuild
const PART_PAIR = { L_upper: 0, L_fore: 1, R_upper: 2, R_fore: 3 };

function getGeo(file, cb) {
  if (stlCache[file]) { cb(stlCache[file]); return; }
  stlLoader.load("/models/" + encodeURIComponent(file),
    (geo) => { stlCache[file] = geo; cb(geo); },
    undefined,
    () => { $("tlStat").textContent = "cannot load models/" + file; });
}
// STL files carry no texture coordinates — project simple UVs from the two
// largest bounding-box axes so a painted PNG/JPG can be shown on them
function ensureUVs(geo) {
  if (geo.attributes.uv) return geo;
  geo.computeBoundingBox();
  const bb = geo.boundingBox, size = new THREE.Vector3();
  bb.getSize(size);
  const comps = ["x", "y", "z"].sort((a, b) => size[b] - size[a]); // widest first
  const [ua, va] = comps;
  const pos = geo.attributes.position;
  const uv = new Float32Array(pos.count * 2);
  const get = { x: (i) => pos.getX(i), y: (i) => pos.getY(i), z: (i) => pos.getZ(i) };
  for (let i = 0; i < pos.count; i++) {
    uv[i * 2] = (get[ua](i) - bb.min[ua]) / (size[ua] || 1);
    uv[i * 2 + 1] = (get[va](i) - bb.min[va]) / (size[va] || 1);
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  return geo;
}
function cfgMesh(geo, cfg, part) {
  const tex = getTex(cfg.tex);
  if (tex) ensureUVs(geo);
  const mat = new THREE.MeshStandardMaterial({
    color: tex ? "#ffffff" : (cfg.color || "#8a94a6"),
    map: tex || null,
    roughness: 0.65,
  });
  const m = new THREE.Mesh(geo, mat);
  const r = cfg.rot || [0, 0, 0], o = cfg.off || [0, 0, 0];
  m.rotation.set(THREE.MathUtils.degToRad(+r[0] || 0),
                 THREE.MathUtils.degToRad(+r[1] || 0),
                 THREE.MathUtils.degToRad(+r[2] || 0));
  m.position.set(+o[0] || 0, +o[1] || 0, +o[2] || 0);
  m.scale.setScalar(+cfg.scale || 1);
  const pair = PART_PAIR[part];
  if (pair !== undefined) { m.userData.pair = pair; pickMeshes.push(m); }
  return m;
}
function applyMeshes() {
  const gen = ++meshGen;
  MESH_PARTS.forEach(part => {
    const cfg = meshCfg[part];
    const holder = linkHolders[part];
    if (!holder) return;
    // default shape: hide the "flesh" when an STL is assigned — the skeleton
    // (userData.skel) is never hidden
    holder.children[0].traverse(o => {
      if (o.isMesh && !o.userData.skel) o.visible = !cfg.file;
    });
    while (holder.children.length > 1) holder.remove(holder.children[holder.children.length - 1]);
    if (cfg.file) getGeo(cfg.file, geo => {
      if (gen !== meshGen || linkHolders[part] !== holder) return;
      holder.add(cfgMesh(geo, cfg, part));
    });
  });
  addons.forEach(ad => { // clothes & extra parts: layered on top, never replace
    const holder = linkHolders[ad.part];
    if (!holder || !ad.file) return;
    getGeo(ad.file, geo => {
      if (gen !== meshGen || linkHolders[ad.part] !== holder) return;
      holder.add(cfgMesh(geo, ad, ad.part));
    });
  });
}

// measure the (rotated, scaled) STL and take the rig lengths from it — the
// STL brings its own real dimensions, the rig follows them
function measureFromStl(part) {
  const cfg = meshCfg[part];
  if (!cfg.file) return;
  getGeo(cfg.file, geo => {
    const g = geo.clone();
    const r = cfg.rot || [0, 0, 0];
    g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(
      THREE.MathUtils.degToRad(+r[0] || 0),
      THREE.MathUtils.degToRad(+r[1] || 0),
      THREE.MathUtils.degToRad(+r[2] || 0))));
    g.computeBoundingBox();
    const size = new THREE.Vector3();
    g.boundingBox.getSize(size);
    size.multiplyScalar(+cfg.scale || 1);
    g.dispose();
    let msg = "";
    const rd = (v) => Math.max(5, Math.round(v));
    if (part === "L_upper") {           // left/right lengths stay independent
      RIG.dims.upperLenL = rd(size.y);
      msg = "LEFT upper arm length = " + RIG.dims.upperLenL + " mm (from the STL)";
    } else if (part === "R_upper") {
      RIG.dims.upperLenR = rd(size.y);
      msg = "RIGHT upper arm length = " + RIG.dims.upperLenR + " mm (from the STL)";
    } else if (part === "L_fore") {
      RIG.dims.foreLenL = rd(size.y);
      msg = "LEFT forearm length = " + RIG.dims.foreLenL + " mm (from the STL)";
    } else if (part === "R_fore") {
      RIG.dims.foreLenR = rd(size.y);
      msg = "RIGHT forearm length = " + RIG.dims.foreLenR + " mm (from the STL)";
    } else if (part === "torso") {
      RIG.dims.torsoW = rd(size.x); RIG.dims.torsoH = rd(size.y); RIG.dims.torsoD = rd(size.z);
      msg = `torso from the STL: ${RIG.dims.torsoW}×${RIG.dims.torsoH}×${RIG.dims.torsoD} mm`;
    }
    saveRig();
    renderRigUI();
    buildRobot();
    if (msg) $("tlStat").textContent = msg + " — fine-tune in Rig setup if needed";
  });
}

// back to (built-in): that part's rig lengths return to the defaults
function revertDims(part) {
  const D = DEFAULT_RIG.dims;
  if (part === "L_upper") RIG.dims.upperLenL = D.upperLenL;
  else if (part === "R_upper") RIG.dims.upperLenR = D.upperLenR;
  else if (part === "L_fore") RIG.dims.foreLenL = D.foreLenL;
  else if (part === "R_fore") RIG.dims.foreLenR = D.foreLenR;
  else if (part === "torso") {
    RIG.dims.torsoW = D.torsoW; RIG.dims.torsoH = D.torsoH; RIG.dims.torsoD = D.torsoD;
  } else return;
  saveRig();
  renderRigUI();
}

// ---- Model card UI: per-part file/color + rotation/offset/scale, addons ----
// one labelled block per transform:  rotate: / roll pitch yaw,  offset: /
// x y z,  scale: / scale — each on its own line so nothing overlaps
function vecBlock(cfg, key, title, subLabels, step, onchange) {
  const wrap = document.createElement("div");
  wrap.className = "tblock";
  const head = document.createElement("div");
  head.className = "tlabel";
  head.textContent = title + ":";
  wrap.appendChild(head);
  const row = document.createElement("div");
  row.className = "trow";
  for (let i = 0; i < 3; i++) {
    const cell = document.createElement("label");
    cell.className = "tcell";
    const inp = document.createElement("input");
    inp.type = "number"; inp.step = step;
    inp.value = (cfg[key] || [0, 0, 0])[i];
    inp.onchange = () => {
      if (!cfg[key]) cfg[key] = [0, 0, 0];
      cfg[key][i] = +inp.value || 0;
      onchange();
    };
    cell.append(inp, document.createTextNode(subLabels[i]));
    row.appendChild(cell);
  }
  wrap.appendChild(row);
  return wrap;
}
function transformRows(cfg, box, onchange) {
  box.appendChild(vecBlock(cfg, "rot", "rotate (deg)", ["roll X", "pitch Y", "yaw Z"], 15, onchange));
  box.appendChild(vecBlock(cfg, "off", "offset (mm)", ["x", "y", "z"], 5, onchange));
  const wrap = document.createElement("div");
  wrap.className = "tblock";
  const head = document.createElement("div");
  head.className = "tlabel";
  head.textContent = "scale:";
  const row = document.createElement("div");
  row.className = "trow";
  const cell = document.createElement("label");
  cell.className = "tcell";
  const sc = document.createElement("input");
  sc.type = "number"; sc.step = 0.1; sc.min = 0.01; sc.value = cfg.scale || 1;
  sc.onchange = () => { cfg.scale = +sc.value || 1; onchange(); };
  cell.append(sc, document.createTextNode("×"));
  row.appendChild(cell);
  wrap.append(head, row);
  box.appendChild(wrap);
}
const isImg = (f) => /\.(png|jpe?g|bmp|gif)$/i.test(f);
const isStl = (f) => /\.stl$/i.test(f);
function fileSelect(cfg, onpick) {
  const sel = document.createElement("select");
  sel.style.flex = "1";
  sel.innerHTML = "<option value=''>(built-in)</option>";
  modelFiles.filter(isStl).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f;
    if (cfg.file === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => { cfg.file = sel.value; onpick(); };
  return sel;
}
function texSelect(cfg, onpick) { // painted PNG/JPG applied onto the part
  const sel = document.createElement("select");
  sel.style.flex = "1";
  sel.title = "texture image (draw it in any paint program, Import it, pick it here)";
  sel.innerHTML = "<option value=''>(no texture)</option>";
  modelFiles.filter(isImg).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f;
    if (cfg.tex === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => { cfg.tex = sel.value; onpick(); };
  return sel;
}
function renderModelsUI() {
  const box = $("meshAssign");
  box.innerHTML = "";
  MESH_PARTS.forEach(part => {
    const cfg = meshCfg[part];
    const row = document.createElement("div"); row.className = "row";
    const lbl = document.createElement("span"); lbl.className = "lbl"; lbl.textContent = part;
    const sel = fileSelect(cfg, () => {
      saveMeshes();
      renderModelsUI(); // the rot/offset/scale boxes appear immediately
      if (cfg.file) measureFromStl(part);        // STL size -> rig lengths
      else { revertDims(part); buildRobot(); }   // built-in again
    });
    const col = document.createElement("input");
    col.type = "color"; col.value = cfg.color || "#8a94a6";
    col.title = "color of this part (ignored while a texture is set)";
    col.onchange = () => { cfg.color = col.value; saveMeshes(); buildRobot(); };
    row.append(lbl, sel, col);
    box.appendChild(row);
    const texRow = document.createElement("div"); texRow.className = "row";
    const texLbl = document.createElement("span");
    texLbl.className = "lbl"; texLbl.textContent = "└ texture";
    texRow.append(texLbl, texSelect(cfg, () => { saveMeshes(); buildRobot(); }));
    box.appendChild(texRow);
    if (cfg.file) { // the STL rarely shares the robot's origin: adjust here
      const sub = document.createElement("div");
      sub.style.margin = "0 0 8px 12px";
      transformRows(cfg, sub, () => { saveMeshes(); measureFromStl(part); });
      box.appendChild(sub);
    }
  });
  renderAddonsUI();
}
function renderAddonsUI() {
  const box = $("addonList");
  box.innerHTML = "";
  addons.forEach((ad, i) => {
    const row = document.createElement("div"); row.className = "row";
    const sel = fileSelect(ad, () => { saveMeshes(); buildRobot(); });
    const at = document.createElement("select");
    MESH_PARTS.forEach(p => {
      const o = document.createElement("option"); o.value = o.textContent = p;
      if (ad.part === p) o.selected = true;
      at.appendChild(o);
    });
    at.title = "which body part this piece follows";
    at.onchange = () => { ad.part = at.value; saveMeshes(); buildRobot(); };
    const col = document.createElement("input");
    col.type = "color"; col.value = ad.color || "#7a5cc4";
    col.onchange = () => { ad.color = col.value; saveMeshes(); buildRobot(); };
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => { addons.splice(i, 1); saveMeshes(); renderModelsUI(); buildRobot(); };
    row.append(sel, at, col, del);
    box.appendChild(row);
    const sub = document.createElement("div");
    sub.style.margin = "0 0 8px 12px";
    transformRows(ad, sub, () => { saveMeshes(); buildRobot(); });
    box.appendChild(sub);
  });
}
function addAddon() {
  addons.push({ file: "", part: "torso", rot: [0, 0, 0], off: [0, 0, 0], scale: 1, color: "#7a5cc4" });
  saveMeshes();
  renderModelsUI();
}
async function importStl() {
  const f = $("stlFile").files[0];
  if (!f) { alert("choose a file first: .stl shape (mm) or a painted .png/.jpg texture"); return; }
  const r = await fetch("/api/model/upload?name=" + encodeURIComponent(f.name), {
    method: "POST", body: await f.arrayBuffer(),
  }).then(r => r.json());
  if (!r.ok) { alert("import failed: " + r.error); return; }
  delete stlCache[r.file]; // re-imported file: drop the stale geometry/texture
  delete texCache[r.file];
  await refreshModels();
  $("tlStat").textContent = "imported " + r.file + " — assign it below (" +
    (isImg(r.file) ? "as a texture on a part" : "as a body part or add-on") + ")";
}
async function refreshModels() {
  const r = await fetch("/api/list?kind=models").then(r => r.json());
  modelFiles = (r.files || []).filter(f => isStl(f) || isImg(f));
  renderModelsUI();
}

// ---------------------------------------------------------------- robot link
// Transports, one command language (see firmware COMMANDS.md):
//   wifi   — HTTP through the local python proxy (/api/robot/*)
//   usb    — the cable, THROUGH THE HUB (/api/usb/cmd?port=..&id=..). This is
//            the default: a COM port can only be opened by one program, and
//            the hub is that one owner. It shares the port between all of its
//            pages, so the module website (/mod?dev=usb:COMx) and Nong Studio
//            can drive the SAME cable at the same time — no more
//            "serial port already in use" when both are open. It also works
//            from a phone/laptop on the LAN, where Web Serial does not exist.
//   serial — optional DIRECT Web Serial from this browser. Lowest latency and
//            works with no hub, but it OWNS the port exclusively: while it is
//            connected nothing else (module website, hub probe) can use that
//            cable. Chrome/Edge on the host PC only.
// With an empty "bus id" the cable goes straight into the nong module's USB.
// With a bus id set, every command is framed "#<id> ..." and replies
// "@<id> ..." — the RS485 wire protocol, so the same mode covers BOTH a
// USB-RS485 dongle on the bus AND reaching the nong through any other
// module's USB port (modules bridge '#' lines onto the bus).
// Every text command AND SD file transfer works on all transports (see the
// sdUpload/sdDownload/sdDelete helpers below).
function robotIp() { return $("robotIp").value.trim(); }
function transport() { return $("connSel").value; }
function busId() { const v = $("busId").value.trim(); return v ? parseInt(v, 10) : 0; }

let serialPort = null;    // direct Web Serial handle (exclusive mode)
let serialWaiters = [];   // [{filter(line)->string|null, res, rej}]
let hubPort = "";         // COM port driven through the hub (shared mode)

function connModeChanged() {
  const t = transport(), usb = t === "usb", direct = t === "serial";
  $("robotIp").style.display = (usb || direct) ? "none" : "";
  $("busId").style.display = (usb || direct) ? "" : "none";
  $("usbPort").style.display = usb ? "" : "none";
  $("usbRescan").style.display = usb ? "" : "none";
  $("connBtn").textContent = direct && !serialPort ? "Connect USB" : "Connect";
  if (usb) { if (!$("usbPort").dataset.loaded) loadPorts(); }
  else if (direct && !("serial" in navigator))
    $("robotStat").textContent = "This browser cannot open a USB port by itself. "
      + "Pick “+ USB (shared)” instead — the hub opens the cable and shares it — "
      + "or connect over WiFi. (Web Serial works in Chrome and Edge.)";
}

// ------- shared USB: the hub owns the port, we send commands through it
// The hub serialises every command per port, so this page and the module
// website can hold the same cable at once.
async function loadPorts(keepSel) {
  const sel = $("usbPort"), want = keepSel || sel.value;
  sel.innerHTML = "<option value=''>looking for USB ports…</option>";
  try {
    const r = await fetch("/api/ports").then(r => r.json());
    const ps = (r.ports || []).filter(p => !p.bt);
    sel.innerHTML = "<option value=''>pick the USB port…</option>";
    ps.forEach(p => {
      const o = document.createElement("option");
      o.value = p.port;
      o.textContent = p.port + (p.who ? " — " + p.who : (p.desc ? " — " + p.desc : "")) +
        (p.inuse ? " · in use (shared)" : "");
      sel.appendChild(o);
    });
    if (!ps.length) sel.innerHTML = "<option value=''>no USB port found — cable plugged in?</option>";
    sel.dataset.loaded = "1";
    if (want && ps.some(p => p.port === want)) sel.value = want;
    else if (ps.length === 1) sel.value = ps[0].port;
  } catch (e) {
    sel.innerHTML = "<option value=''>the port list needs the hub (python main.py)</option>";
  }
}
function usbPortChanged() {   // picking another port drops the old link
  if (hubPort && hubPort !== $("usbPort").value) hubPort = "";
  $("robotStat").textContent = linkBadge();
}
async function hubUsbCmd(c) {
  // With a peer, the command has to go to the module behind the plugged-in
  // one's hotspot, and only the unified endpoint understands that: the hub
  // turns dev=usb:COM7@far-nong into REACH far-nong <command> down the cable.
  // Without a peer this stays on the endpoint it always used, so nothing about
  // the ordinary cable path changes.
  const url = window.HUB_PEER
    ? `/api/dev/cmd?dev=${encodeURIComponent(
        "usb:" + hubPort + (busId() ? ":" + busId() : "") + "@" + window.HUB_PEER)}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/usb/cmd?port=${encodeURIComponent(hubPort)}` +
      `&id=${busId()}&c=${encodeURIComponent(c)}`;
  const r = await fetch(url);
  const t = await r.text();
  if (!r.ok) {
    let msg = t;
    try { msg = JSON.parse(t).error || t; } catch (e) { /* plain text error */ }
    throw new Error(msg);
  }
  return t.trim();
}

async function serialConnect() {
  if (!("serial" in navigator))
    throw new Error("no Web Serial here — USB works only in Chrome/Edge on the " +
      "host PC at http://127.0.0.1:8642 (not from the LAN address or other devices); " +
      "use WiFi mode instead");
  serialPort = await navigator.serial.requestPort();
  await serialPort.open({ baudRate: 115200 });
  // release the ESP32 strap lines: asserted DTR/RTS can hold the board in
  // reset/bootloader through the USB-UART chip
  try { await serialPort.setSignals({ dataTerminalReady: false, requestToSend: false }); }
  catch (e) { /* some adapters don't support it */ }
  serialReadLoop();
  await new Promise(r => setTimeout(r, 400)); // let boot/log noise pass
}
async function serialReadLoop() {
  try {
    const decoder = new TextDecoderStream();
    serialPort.readable.pipeTo(decoder.writable).catch(() => {});
    const reader = decoder.readable.getReader();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        // Skip blank lines and firmware LOG lines only. A log line is a bracket
        // TAG — "[wifi] …", "[sd] …", "[  1234][I]…". A JSON ARRAY reply
        // (PIN VALID → "[{…}]", FILES → "[\"…\"]") also starts with "[" and must
        // NOT be skipped (that made pin config say "unsupported" over USB).
        if (!line || /^\[[\w ]*\]/.test(line)) continue;
        const w = serialWaiters[0];
        if (!w) continue;                            // unsolicited bus chatter
        const out = w.filter(line);
        if (out !== null) { serialWaiters.shift(); w.res(out); }
        // out === null: not the reply we wait for (e.g. "-> sent, ..." bridge
        // note, or another module's traffic on the bus) — keep waiting
      }
    }
  } catch (e) { /* port closed / unplugged */ }
  serialPort = null;
  $("robotStat").textContent = "USB disconnected";
}
function serialCmd(c) {
  return new Promise((res, rej) => {
    if (!serialPort || !serialPort.writable) return rej(new Error("USB not connected"));
    const id = busId();
    // direct USB: any reply line. bus mode: only "@<id> ..." from our module
    const filter = id
      ? (line) => (line.startsWith("@" + id + " ") ? line.slice(String(id).length + 2) : null)
      : (line) => line;
    const w = { filter, res, rej };
    serialWaiters.push(w);
    setTimeout(() => {
      const k = serialWaiters.indexOf(w);
      if (k >= 0) { serialWaiters.splice(k, 1); rej(new Error("timeout (bus id right?)")); }
    }, 2500);
    const framed = id ? "#" + id + " " + c : c;      // RS485 frame when addressed
    const writer = serialPort.writable.getWriter();
    writer.write(new TextEncoder().encode(framed + "\n")).finally(() => writer.releaseLock());
  });
}

// Transports are NOT exclusive: WiFi and USB/RS485 can be connected at the
// same time. Commands take the cable when it is open (lowest latency, works
// without any network) and WiFi otherwise; bulk SD file transfer prefers
// WiFi and falls back to the cable.
function usbDirect() { return !!(serialPort && serialPort.writable); }
function haveUsb() { return usbDirect() || !!hubPort; }
function haveWifi() { return !!robotIp(); }
// one call for "send this over the cable", whichever USB mode is connected
function cableCmd(c) { return usbDirect() ? serialCmd(c) : hubUsbCmd(c); }
async function httpCmd(c) {
  // Same over WiFi: wifi:<ip>@peer reaches a module on that board's hotspot.
  const url = window.HUB_PEER
    ? `/api/dev/cmd?dev=${encodeURIComponent("wifi:" + robotIp() + "@" + window.HUB_PEER)}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/robot/cmd?ip=${encodeURIComponent(robotIp())}&c=${encodeURIComponent(c)}`;
  return fetch(url).then(r => r.text());
}
async function rawCmd(c) { // reply text or throws
  if (haveUsb()) return cableCmd(c);
  if (haveWifi()) return httpCmd(c);
  throw new Error("connect first — 🔍 Find modules (WiFi) or pick a USB port");
}

// ------- open the module's own website for the board we are talking to
// The hub serves that site for any transport as /mod?dev=..., so the config
// (pins, users, WiFi, servo type, SD files) is one click away from here and
// points at the SAME board the commands go to — hence the same precedence as
// rawCmd: cable first, WiFi otherwise.
function moduleDev() {
  // The peer rides along. Without it this link opened the website of the
  // board on the CABLE while every command went to the module behind that
  // board's hotspot — two different robots, one screen, no warning.
  const at = window.HUB_PEER ? "@" + window.HUB_PEER : "";
  if (hubPort) return "usb:" + hubPort + (busId() ? ":" + busId() : "") + at;
  if (haveWifi()) return "wifi:" + robotIp() + at;
  return "";     // direct Web Serial: see openModule()
}

// Forget the peer the moment the person aims at something else by hand.
// HUB_PEER comes from the ?dev= the page was opened with; it describes THAT
// module, and keeping it after the cable or the address changes sends
// commands to a board nobody chose.
// A PERSON changing the target drops the peer. Deliberately on the events and
// not inside usbPortChanged/connModeChanged: those are also called during boot
// — the ?dev= handler calls connModeChanged() to set the connection up — so
// doing it there threw the peer away the moment the page opened with one.
// Setting a value from code fires no change event; choosing one by hand does.
window.addEventListener("DOMContentLoaded", function () {
  const port = document.getElementById("usbPort");
  const mode = document.getElementById("connSel");
  if (port) port.addEventListener("change", () => clearPeer("you picked another cable"));
  if (mode) mode.addEventListener("change", () => clearPeer("you changed the connection"));
});

function clearPeer(why) {
  if (!window.HUB_PEER) return;
  window.HUB_PEER = "";
  if (typeof log === "function") log("(no longer aiming at a peer module: " + why + ")");
}
function openModule() {
  const dev = moduleDev();
  if (dev) {
    // The hub shares the cable, so the module site and this editor can both
    // stay open on one USB port.
    window.open("/mod?dev=" + encodeURIComponent(dev), "_blank");
    return;
  }
  if (usbDirect()) {
    $("robotStat").textContent = "direct Web Serial owns this cable, so the module " +
      "site cannot share it — switch the link to “+ USB (shared)” and connect again, " +
      "then this button works with both open at once.";
    return;
  }
  $("robotStat").textContent = "connect first — pick a USB port or find a module on WiFi";
}
async function robotCmd(c) {
  try {
    const t = await rawCmd(c);
    $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + t.slice(0, 120);
    return t;
  } catch (e) {
    $("robotStat").textContent = "" + (e.message || e);
    return "";
  }
}
async function getStatus() { // full status JSON on whichever link is up
  if (haveUsb()) {
    try { return JSON.parse(await cableCmd("INFO")); }
    catch (e) { return JSON.parse(await cableCmd("INFO")); } // boot noise: retry once
  }
  if (haveWifi())
    return fetch("/api/robot/status?ip=" + encodeURIComponent(robotIp())).then(r => r.json());
  throw new Error("not connected");
}
function linkBadge() { // shown in robotStat so you see every open channel
  const parts = [], bus = busId() ? "→RS485 #" + busId() : "";
  if (usbDirect()) parts.push("USB direct" + bus + " ✓");
  else if (hubPort) parts.push("USB " + hubPort + bus + " (shared) ✓");
  if (haveWifi()) parts.push("WiFi " + robotIp());
  return parts.join(" + ") || "not connected";
}

// ------- auto-discovery: the hub server scans the WiFi — just click one
async function scanModules() {
  const sel = $("foundSel");
  sel.innerHTML = "<option value=''>scanning the WiFi… (a few seconds)</option>";
  try {
    const r = await fetch("/api/scan?force=1").then(r => r.json());
    sel.innerHTML = "<option value=''>found: pick one…</option>";
    (r.modules || []).forEach(m => {
      const o = document.createElement("option");
      o.value = m.ip;
      o.textContent = `${m.name} (${m.type}) — ${m.ip}`;
      sel.appendChild(o);
    });
    if (!(r.modules || []).length)
      sel.innerHTML = "<option value=''>no modules found — same WiFi? rescan</option>";
  } catch (e) {
    sel.innerHTML = "<option value=''>scan needs the hub server (python main.py)</option>";
  }
}
function pickFound(ip) {
  if (!ip) return;
  $("connSel").value = "wifi";
  connModeChanged();
  $("robotIp").value = ip;
  connectRobot();
}
async function connectRobot() {
  const t = transport(), had = hubPort;
  try {
    if (t === "usb") {
      if (!$("usbPort").dataset.loaded) await loadPorts();
      hubPort = $("usbPort").value;
      if (!hubPort) throw new Error("pick the USB port the module is plugged into " +
        "(⟳ to rescan)");
    } else if (t === "serial" && !usbDirect()) {
      await serialConnect();
    }
    const s = await getStatus();
    // If the module is playing a sequence on its OWN clock, say so here. It is
    // the moment the question "why is the robot moving by itself?" gets asked —
    // it happens after a hand-off, or when the board was left running from an
    // earlier session, and the answer used to be invisible.
    const own = (s.seq && s.seq.running)
      ? ` — the module is PLAYING ${s.seq.file || "a sequence"} on its own; ` +
        "Play or Stop here takes over" : "";
    $("robotStat").textContent =
      `[${linkBadge()}] ${s.name} (id ${s.id}, type ${s.type})` +
      (s.type !== "nong" ? " — WARNING: type is not nong" : "") +
      (s.sd ? ", SD ok" : ", no SD card") + own;
    refreshSd();
  } catch (e) {
    if (t === "usb" && !had) hubPort = "";   // never show a link that isn't there
    $("robotStat").textContent = "Could not reach the robot. Check it is powered "
      + "and on the same network or cable, then try again. " + (e.message || e);
  }
}
function sendPose(quiet) {
  const c = "POSE " + pose.map(fmtA).join(" "); // no T: firmware uses its speed setting
  if (quiet) { sendPoseLive(); return; }
  robotCmd(c);
}

// Live sending: ONE command in flight at a time, newest pose wins.
//
// Fire-and-forget sends are NOT ordered. Dragging a slider fast put several
// fetches in the air at once, and whichever the module happened to serve last
// won — so the arm could settle on an older pose while the number on screen
// showed the value you released at. A plain time throttle made it worse: if
// the final update landed inside the throttle window it was dropped outright
// and the last position was never sent at all.
//
// Holding exactly one request open fixes both: replies come back in order, and
// `livePending` always holds the NEWEST pose, so the loop cannot exit without
// having sent the value the user finished on. It also self-tunes — a fast link
// sends more often, a slow one less, with no magic interval to keep in step
// with the transport.
// Two kinds of live traffic share the ONE channel, which is what keeps them in
// order relative to each other:
//   liveQueue   — commands that must all be sent, in order (playback segments,
//                 the keyframe-0 send, STOP). Sending these as separate
//                 fetches raced: Play could deliver segment 1 BEFORE the
//                 keyframe-0 pose and start the arm from the wrong place.
//   livePending — the newest pose from a drag. Superseded, never queued.
let liveBusy = false, livePending = null, liveQueue = [];
// How long a dragged pose should take, in ms — and why it is not left to the
// board to decide.
//
// A drag used to send `POSE …` with no T, so the module fell back to its SPEED
// setting: at 120°/s a 20° slider move takes 166 ms, the next update arrives
// before that finishes, and the arm is permanently easing towards where your
// hand WAS. It reads as lag, and no amount of sending faster fixes it, because
// each command asks for a slow move.
//
// So a live pose asks for the time it actually has: the measured round trip to
// this module, which self-tunes to the link (~25 ms on USB, ~100 ms over WiFi).
// The firmware floors T per joint at what the servos can really do, so asking
// for less than is possible is safe — it is a request, not a promise.
let liveRtt = 120;                      // ms, smoothed
const LIVE_T_MIN = 80, LIVE_T_MAX = 300;
function liveT() {
  return Math.max(LIVE_T_MIN, Math.min(LIVE_T_MAX, Math.round(liveRtt * 1.3)));
}
function liveSend(c) { liveQueue.push(c); livePump(); }
function sendPoseLive() { livePending = pose.slice(); livePump(); }
function liveAbort() { liveQueue = []; livePending = null; }
function livePump() {
  if (liveBusy) return;
  liveBusy = true;
  (async () => {
    try {
      for (;;) {
        let c = null;
        if (liveQueue.length) {
          c = liveQueue.shift();                 // ordered work comes first
        } else if (livePending) {
          // ...with the time it has, not the module's default easing speed
          c = "POSE " + livePending.map(fmtA).join(" ") + " T " + liveT();
          livePending = null;                    // only ever the newest pose
        }
        if (!c) break;
        try {
          const t0 = performance.now();
          const r = await rawCmd(c);
          // Measure the link from the traffic itself — no probing, and it
          // follows a link that changes (USB pulled, WiFi gone slow).
          liveRtt += ((performance.now() - t0) - liveRtt) * 0.25;
          $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + r.slice(0, 80);
        } catch (e) {
          $("robotStat").textContent = "" + (e.message || e);
        }
      }
    } finally { liveBusy = false; }
  })();
}

// ------- SD file access on ANY transport
// wifi: the module's HTTP file API through the python proxy.
// usb/rs485: the firmware's FBEGIN/FDATA/FEND/FREAD/FDEL text commands
// (base64 chunks small enough for one RS485 frame) — so the SD card can be
// managed over every channel, not only WiFi.
async function sdUploadSerial(fname, text) {
  const bytes = new TextEncoder().encode(text);
  // direct USB can take bigger chunks; 120 bytes only when framed for the
  // RS485 bus (its frames are limited to ~250 chars)
  const CH = busId() ? 120 : 180;
  let r = await cableCmd("FBEGIN " + fname);
  if (!r.startsWith("OK")) throw new Error(r);
  for (let o = 0; o < bytes.length; o += CH) {
    const chunk = bytes.subarray(o, Math.min(o + CH, bytes.length));
    r = await cableCmd("FDATA " + btoa(String.fromCharCode(...chunk)));
    if (!r.startsWith("OK")) throw new Error(r);
    $("sdStat").textContent = `uploading ${fname}: ${Math.min(o + CH, bytes.length)}/${bytes.length} bytes`;
  }
  r = await cableCmd("FEND");
  if (!r.startsWith("OK")) throw new Error(r);
}
async function sdUpload(fname, text) {
  if (haveWifi()) { // fastest for whole files; fall back to the cable
    try {
      const r = await fetch("/api/robot/upload", {
        method: "POST", body: JSON.stringify({ ip: robotIp(), name: fname, yaml: text }),
      }).then(r => r.json());
      if (!r.ok) throw new Error(JSON.stringify(r));
      return;
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (haveUsb()) return sdUploadSerial(fname, text);
  throw new Error("connect first (WiFi or USB)");
}
async function sdDownloadSerial(fname) {
  const parts = [];
  for (let off = 0; ; ) {
    const r = await cableCmd(`FREAD ${fname} ${off} 120`);
    if (r === "EOF") break;
    if (r.startsWith("ERR")) throw new Error(r);
    const bin = atob(r);
    parts.push(bin);
    off += bin.length;
    $("sdStat").textContent = `reading ${fname}: ${off} bytes`;
  }
  const all = parts.join("");
  return new TextDecoder().decode(Uint8Array.from(all, c => c.charCodeAt(0)));
}
async function sdDownload(fname) {
  if (haveWifi()) {
    try {
      return await fetch(`/api/robot/download?ip=${encodeURIComponent(robotIp())}` +
                         `&path=${encodeURIComponent("/moves/" + fname)}`).then(r => r.text());
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (haveUsb()) return sdDownloadSerial(fname);
  throw new Error("connect first (WiFi or USB)");
}
async function sdDelete(fname) {
  if (haveWifi()) {
    try {
      // READ the reply. fetch does not throw on 404 or 502, and the firmware
      // answers 200 with the body "ERR delete failed" — so this branch used to
      // report success for a file that is still sitting on the card, and the
      // caller then removed it from the list. The cable branch below has always
      // checked; only this one did not.
      const res = await fetch(`/api/robot/delete?ip=${encodeURIComponent(robotIp())}` +
                  `&path=${encodeURIComponent("/moves/" + fname)}`);
      const body = (await res.text()).trim();
      if (!res.ok || body.startsWith("ERR")) {
        throw new Error(body || ("the robot answered " + res.status));
      }
      return;
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (!haveUsb()) throw new Error("connect first (WiFi or USB)");
  const r = await cableCmd("FDEL " + fname);
  if (!r.startsWith("OK")) throw new Error(r);
}

// ------- SD card manager: list /moves, run/edit/delete a sequence
async function refreshSd() {
  const box = $("sdList");
  // A loading state, so the panel is never a blank hole while a cable round
  // trip runs — over USB with a peer this can take several seconds.
  box.textContent = "Reading the robot's card…";
  try {
    let files;
    if (haveWifi()) {
      files = await fetch(`/api/robot/files?ip=${encodeURIComponent(robotIp())}&dir=/moves`)
        .then(r => r.json());
    } else if (haveUsb()) {
      files = JSON.parse(await cableCmd("FILES /moves"));
    } else {
      // An empty state says what goes here and names the ONE action that fills
      // it, rather than a bare instruction with no subject.
      box.textContent = "Not connected to a robot yet, so there is no card to "
        + "read. Press 🔍 Find modules, or pick a USB cable above.";
      return;
    }
    box.innerHTML = "";
    if (!files.length) {
      box.textContent = "This robot's card has no sequences on it yet. Build a "
        + "timeline, then press “Send to robot” to put one there.";
    }
    // the "then run…" chain box offers the files that are really on the card
    const dl = $("seqNextList");
    if (dl) {
      dl.innerHTML = "";
      files.forEach(f => {
        const o = document.createElement("option");
        o.value = f.n;
        dl.appendChild(o);
      });
    }
    files.forEach(f => {
      const row = document.createElement("div"); row.className = "row";
      const name = document.createElement("span");
      name.style.flex = "1"; name.textContent = f.n + "  (" + (f.s / 1024).toFixed(1) + " kB)";
      const run = document.createElement("button");
      run.textContent = "▶ Run"; run.className = "primary";
      run.onclick = () => robotCmd("MOVE " + f.n);
      const edit = document.createElement("button");
      edit.textContent = "✎ Edit";
      edit.title = "load this sequence from the SD card into the timeline";
      edit.onclick = () => editSdSeq(f.n);
      const del = document.createElement("button");
      del.textContent = "✕"; del.title = "delete from SD";
      del.onclick = async () => {
        if (!confirm("Delete " + f.n + " from the robot SD card?")) return;
        try { await sdDelete(f.n); } catch (e) { $("sdStat").textContent = "" + e; }
        refreshSd();
      };
      row.append(name, run, edit, del);
      box.appendChild(row);
    });
    $("sdStat").textContent = "";
  } catch (e) {
    // An error says what to DO next, and offers the control that does it.
    box.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "Could not read the robot's card. It may have gone off the "
      + "network, or it has no card fitted. ";
    const why = document.createElement("span");
    why.className = "hint";                 // the raw reason, demoted
    why.textContent = e.message || String(e);
    const again = document.createElement("button");
    again.textContent = "Try again";
    again.onclick = () => refreshSd();
    box.append(msg, why, document.createTextNode(" "), again);
  }
}
async function uploadYaml() {
  if (nothingToWrite("sdStat")) return;
  if (!crashGate("UPLOAD it")) return;
  const { name, yaml } = buildYaml();
  try {
    await sdUpload(name + ".yaml", yaml);
    $("sdStat").textContent =
      `uploaded ${name}.yaml to /moves — press its ▶ Run button (or pick it on the module website)`;
    refreshSd();
  } catch (e) { $("sdStat").textContent = "upload failed: " + (e.message || e); }
}
// Stop any sequence the MODULE is playing on its own.
//
// Safe to call when nothing is running: the firmware answers "OK move stopped"
// either way, and it costs one command. Calling it too often is harmless;
// calling it too seldom leaves two things driving the servos at once.
//
// Since the firmware learned to preempt (any MOTION command from outside stops
// the module's own sequence), this is no longer the only thing standing between
// you and two clocks on one robot — a stray slider drag is now safe too. It
// stays because saying so EXPLICITLY is what makes the arm start the show from
// keyframe 0 instead of from wherever the interrupted sequence left it, and
// because a board on older firmware still needs it.
function stopRobotSequence() {
  handedOff = false;
  if (!haveUsb() && !haveWifi()) return;
  try { robotCmd("MOVE STOP"); } catch (e) {}
}

// ---- keeping a show running when you leave the page --------------------
//
// The browser clock CANNOT be made reliable in the background. A hidden tab
// has requestAnimationFrame stopped and its timers throttled to roughly once a
// minute, and no amount of silent-audio trickery changes that on every browser
// and every platform. Symptoms seen: the sequence ran at the wrong speed, or
// simply stopped and sat still until the page was looked at again.
//
// So the fix is not to fight the browser — it is to stop being the clock. When
// a show is playing and the page goes away, hand the whole sequence to the
// MODULE and let it play on its own 50 Hz timer. That path already exists
// (Run on robot), it survives closing the browser entirely, and the module
// interpolates with the same formulas this preview uses, so the motion is
// identical rather than merely similar.
let handedOff = false;

async function handOffToRobot() {
  if (handedOff || !playing) return;
  if (!haveUsb() && !haveWifi()) return;     // nothing to hand off TO
  // Hand off only what was ALREADY driving the arm. Two ways this used to move
  // a robot nobody asked to move:
  //   previewOnly — the crash gate said this movement collides and the user
  //     pressed Cancel. `playing` stays true so the preview still draws, so
  //     hiding the tab uploaded and ran the very movement that was refused.
  //   live unchecked — `haveWifi()` is only "an IP is typed in the box", not
  //     "connected". Previewing a show with the live box OFF and then switching
  //     window started the arm.
  // In both cases the preview is a drawing, and a drawing must never become
  // motion just because the tab lost focus.
  if (previewOnly) return;
  if (!liveLinked()) return;
  // Nothing to rescue when the HUB is the clock: it is a native process and
  // this page going away does not touch it. Handing the show to the module as
  // well would put two clocks on one robot — the thing all of this prevents.
  if (hubDriven()) return;
  handedOff = true;
  try {
    const { name, yaml } = buildYaml();
    await sdUpload(name + ".yaml", yaml);    // falls back to module memory with no SD
    await robotCmd("MOVE " + name + ".yaml");
    // stop being the clock: the module owns the show now
    playing = false;
    keepAwake(false);
    $("playBtn").textContent = "▶ Play";
    const st = $("sdStat");
    if (st) st.textContent = "the module is running this sequence on its own — "
      + "it keeps going with this page closed. Press Stop to end it.";
  } catch (e) {
    handedOff = false;                       // it did not take: keep previewing
  }
}

document.addEventListener("visibilitychange", function () {
  if (document.hidden) { handOffToRobot(); return; }
  handedOff = false;                         // back on the page: allow it again
  // While the hub was the clock the ROBOT kept moving and this preview did
  // not (a hidden tab stops rAF and throttles timers). So do not resume where
  // the picture stopped — ask the hub where the show actually is and jump the
  // play head there, or the preview stays permanently behind the arm.
  if (!hubDriven() || !playing) return;
  fetch("/api/play").then(r => r.json()).then(s => {
    if (!s.running) { playing = false; $("playBtn").textContent = "▶ Play"; keepAwake(false); return; }
    playT = Math.min(s.at_ms || 0, totalMs());
    lastPlayMs = 0;                          // fresh clock, no catch-up burst
    pose = poseAt(playT).map((v, i) => clampJ(i, v));
    applyPose(); renderSliders();
  }).catch(() => {});
});

// Send the sequence, THEN play it. This used to send only `MOVE <name>.yaml`,
// so the module ran whatever copy of that name was already on its SD card while
// the crash check had just approved the timeline on screen. Edit a pose to fix
// a collision, press Run, and the robot performed the old crashing version —
// the safety check and the motion were looking at different data. Uploading
// first is what makes the check mean anything.
async function robotRun() {
  if (nothingToWrite("sdStat")) return;     // a file with no moves does nothing
  if (!crashGate("RUN it on the robot")) return;
  const { name, yaml } = buildYaml();
  const st = $("sdStat");
  if (st) st.textContent = "sending " + name + ".yaml to the robot…";
  try {
    await sdUpload(name + ".yaml", yaml);
  } catch (e) {
    if (st) st.textContent = "could not send the sequence, so nothing was run — "
      + (e && e.message ? e.message : e);
    return;
  }
  await robotCmd("MOVE " + name + ".yaml");
  if (st) st.textContent = "the robot is running " + name + ".yaml on its own.";
}

// ---- zero-position calibration (password-gated; default manny/12345678) ----
function zeroCred() { try { return JSON.parse(localStorage.getItem("nongZeroCred")) || null; } catch (e) { return null; } }
function zeroCredOr() { return zeroCred() || { user: "manny", pass: "12345678" }; }
function zeroUnlock() {
  const c = zeroCredOr();
  if ($("zUser").value === c.user && $("zPass").value === c.pass) {
    $("zeroLocked").style.display = "none";
    $("zeroPanel").style.display = "";
    $("zPass").value = "";
  } else {
    // Say what to do, and never imply the reader is at fault. Which of the two
    // is wrong is deliberately not revealed.
    $("zStat").textContent = "That user name and password do not match. "
      + "Check them and try again.";
  }
}
function zeroLock() { $("zeroPanel").style.display = "none"; $("zeroLocked").style.display = ""; }
function zeroChangeCred() {
  const u = $("zNewUser").value.trim(), p = $("zNewPass").value;
  if (!u || !p) { $("zStat2").textContent = "enter a new user and password"; return; }
  localStorage.setItem("nongZeroCred", JSON.stringify({ user: u, pass: p }));
  $("zNewUser").value = ""; $("zNewPass").value = "";
  $("zStat2").textContent = "login changed (this browser)";
}
async function robotZeroSet() {
  if (!haveUsb() && !haveWifi()) { $("zStat2").textContent = "connect to the robot first"; return; }
  const r = await robotCmd("SETZERO");
  $("zStat2").textContent = r.startsWith("OK")
    ? "zero set — this pose is now the robot's home (90° per joint)"
    : ("failed: " + r);
}

// ------- monitor mode: the 3D model follows the REAL robot
// (poll status; module.joints drives the rig, seq shows what's playing)
let monTimer = null;
function liveChanged() {
  if ($("liveChk").checked) { $("monChk").checked = false; monitorChanged(); }
}
function monitorChanged() {
  if ($("monChk").checked) {
    $("liveChk").checked = false;
    playing = false; $("playBtn").textContent = "▶ Play";
    monTimer = setInterval(monitorTick, 350);
    $("robotStat").textContent = "monitoring…";
  } else {
    clearInterval(monTimer); monTimer = null;
  }
}
async function monitorTick() {
  try {
    const s = await getStatus();
    const m = s.module || {};
    // 10 joints now (8 arm + WAIST + SHRUG); an old 8-joint board leaves the
    // two body joints at their current value.
    if (Array.isArray(m.joints) && m.joints.length >= ARMJ) {
      pose = pose.map((cur, i) => (m.joints[i] !== undefined ? clampJ(i, m.joints[i]) : cur));
      applyPose(); renderSliders();
    }
    const seq = s.seq || {};
    $("robotStat").textContent =
      `MONITOR ${s.name}: ` +
      (seq.running ? `playing ${seq.file}` : "no sequence running") +
      (m.moving ? ` | moving (${m.move_left || 0} ms left)` : " | idle") +
      (m.attached === false ? " | relaxed" : "");
  } catch (e) {
    $("robotStat").textContent = "monitor: no reply (" + (e.message || e) + ")";
  }
}

// ---------------------------------------------------------------- main loop
function resize() {
  const w = viewport.clientWidth, h = viewport.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  syncOrtho();                    // the ortho frustum follows the new aspect
}
window.addEventListener("resize", resize);
// The viewport also changes size WITHOUT the window changing: dragging the
// side-panel splitter, a tab whose content is wider, a scrollbar appearing.
// The window resize event says nothing about any of those, so the canvas kept
// its old size and spilled over the settings panel. Watch the element itself.
if (window.ResizeObserver) {
  // Only act on a REAL size change. resize() sets the canvas size, and a
  // canvas inside the observed element can feed the change straight back —
  // an observer that re-triggers itself spins the CPU for as long as the page
  // is open, which looks exactly like the machine hanging.
  let lastW = 0, lastH = 0;
  new ResizeObserver(function () {
    const w = viewport.clientWidth, h = viewport.clientHeight;
    if (w === lastW && h === lastH) return;
    lastW = w; lastH = h;
    resize();
  }).observe(viewport);
}

// Advancing the show is separate from DRAWING it, because the two run at
// different times: the animation frame stops in a hidden tab, the interval in
// keepAwake() does not. Both call this, and it works out its own elapsed time
// from the clock — so whichever fires, time advances exactly once and never
// twice.
// NOTE — polling the hub for the play head does NOT work, and was removed.
//
// While the hub drives, this page kept its own clock and I tried correcting it
// once a second from GET /api/play. That broke playback outright: the check
// "the robot walks the whole timeline in order" saw 90,60,120,60,120,90 for a
// four-move timeline, and the hold between moves collapsed from 2200 ms to
// 1565 ms. Reading the player a second while it is running disturbs the thing
// being read.
//
// If the preview and the arm need tying together properly, the page must stop
// keeping a clock at all while the hub drives and simply draw the position the
// hub reports — not run a second clock and snap it. That is a bigger change
// than a poll and is not attempted here.
let lastPlayMs = 0;
let _drawing = false;          // true only inside the animation frame
let _lastScrub = -1, _lastTime = "";
function playTick() {
  if (!playing) { lastPlayMs = 0; return; }
  const now = performance.now();
  if (!lastPlayMs) { lastPlayMs = now; return; }
  // Clamp the step. A hidden tab has its timers throttled (to about once a
  // minute) and rAF stopped altogether, so coming back after 30 s gave a dt of
  // 30000: the play head teleported, the pose jumped across the whole show in
  // one tick, and every joint was re-sent at once — which is what made the
  // page hang for a moment on return.
  //
  // Clamping is also the CORRECT answer, not just a safe one. While the tab
  // was hidden nothing was being sent, so the robot did not advance either.
  // Advancing the preview by the wall-clock gap would put the preview ahead of
  // the real arm. Both simply continue from where they were.
  //
  // When the HUB is the clock that reasoning flips — the robot DID keep
  // moving — so the visibilitychange handler asks the hub where the show got
  // to and moves the play head there. Clamping still applies in between.
  const dt = Math.min(now - lastPlayMs, MAX_TICK_MS);
  lastPlayMs = now;
  if (dt <= 0) return;

  playT += dt;
  const total = totalMs();
  if (playT >= total) {
    if ($("loopChk").checked) { playT = 0; lastLiveSeg = -1; }  // re-send seg 1
    else {
      playT = total; playing = false;
      $("playBtn").textContent = "▶ Play";
      keepAwake(false);                    // the show is over: let the tab idle
    }
  }
  pose = poseAt(playT).map((v, i) => clampJ(i, v));
  // DRAW only from the animation frame. Both rAF and the keep-awake interval
  // call this, so the picture was being redrawn ~76 times a second when the
  // screen can only show 60 — the extra passes were pure cost. Time still
  // advances on whichever fires (that is what keeps a hidden tab moving);
  // only the painting is limited to the frame.
  if (_drawing) {
    applyPose(); renderSliders();
    const scrub = total ? Math.round(playT / total * 1000) : 0;
    if (_lastScrub !== scrub) { _lastScrub = scrub; $("scrub").value = scrub; }
    const lbl = (playT / 1000).toFixed(1) + "s / " + (total / 1000).toFixed(1) + "s";
    if (_lastTime !== lbl) { _lastTime = lbl; $("tlTime").textContent = lbl; }
  }
  // live-follow: push each segment to the robot with its exact duration.
  // Any open link counts — this used to test robotIp(), so Play moved the
  // robot over WiFi but silently did nothing over USB/RS485.
  //
  // ...unless the HUB is the clock. Then the hub is already sending these
  // exact commands from a process no browser can throttle, and this preview is
  // only a picture: sending from here as well would be the second clock all
  // over again. See hubDriven().
  if (liveLinked() && !hubDriven() && !previewOnly) {
    const seg = segmentAt(playT);
    if (seg !== -1 && seg !== lastLiveSeg) {
      lastLiveSeg = seg;
      // exact T at the head of a segment (a whole playthrough sends the
      // same numbers the YAML holds); after a pause, only what is left
      const K = playKeys();
      const rem = segRemaining(playT);
      const tt = K[seg].t - rem <= 50 ? K[seg].t : rem;
      liveSend("POSE " + K[seg].pose.map(fmtA).join(" ") + " T " + tt);
    }
  }
}

function tick(now) {
  requestAnimationFrame(tick);
  _drawing = true;          // this pass may paint; the interval's may not
  playTick();               // no-op when the interval already advanced it
  _drawing = false;
  lastFrame = now;
  controls.update();
  renderer.render(scene, activeCam());
}

// Per-joint servo self-test (?selftest=servo): a slow servo on ONE joint must
// stretch the minimum time for a move that turns that joint, and must NOT
// affect a move that leaves it alone — the same rule the firmware applies.
function runServoSelfTest() {
  const save = { dps: RIG.servoMaxDps.slice(), lo: RIG.pulseMin.slice(),
                 hi: RIG.pulseMax.slice(), rng: RIG.servoRange.slice(),
                 mn: RIG.min.slice(), mx: RIG.max.slice(),
                 gp: RIG.gearPinion.slice(), gg: RIG.gearGear.slice(),
                 hz: RIG.frameHz.slice() };
  const fails = [];
  const flat = new Array(NJ).fill(90);
  RIG.servoMaxDps = new Array(NJ).fill(400);
  const a = flat.slice(); a[2] = 130;              // 40 deg on joint 3 (L_EL_P)
  const fastElbow = minTime(flat, a);
  const b = flat.slice(); b[0] = 130;              // 40 deg on joint 1 (L_SH_P)
  const fastSh = minTime(flat, b);
  RIG.servoMaxDps[2] = 100;                        // slow servo on joint 3 only
  const slowElbow = minTime(flat, a);
  const shAfter = minTime(flat, b);
  if (!(slowElbow > fastElbow * 3.5))
    fails.push(`slow joint did not stretch its move (${fastElbow}->${slowElbow}ms)`);
  if (shAfter !== fastSh)
    fails.push(`slow joint changed an unrelated move (${fastSh}->${shAfter}ms)`);
  // preset must hit only the joints it names
  RIG.servoMaxDps = new Array(NJ).fill(1);
  RIG.pulseMin = new Array(NJ).fill(1); RIG.pulseMax = new Array(NJ).fill(1);
  RIG.servoRange = new Array(NJ).fill(1);
  applyServoPreset("pdi1181mg|sh");
  const shIdx = [0, 1, 4, 5], elIdx = [2, 3, 6, 7];
  if (!shIdx.every(i => RIG.pulseMax[i] === 2500 && RIG.servoMaxDps[i] === 375 && RIG.servoRange[i] === 270))
    fails.push("shoulder preset did not reach every shoulder joint (with 270 travel)");
  if (!elIdx.every(i => RIG.pulseMax[i] === 1))
    fails.push("shoulder preset leaked into the elbows");
  if (RIG.pulseMax[8] === 2500 || RIG.pulseMax[9] === 2500)
    fails.push("shoulder preset leaked into the body joints");
  applyServoPreset("mg90s|el");
  if (!elIdx.every(i => RIG.pulseMax[i] === 2400 && RIG.servoMaxDps[i] === 400))
    fails.push("elbow preset did not reach every elbow joint");
  if (!shIdx.every(i => RIG.pulseMax[i] === 2500))
    fails.push("elbow preset overwrote the shoulders");
  // WAIST + SHRUG presets target exactly their one joint (idx 8 / 9)
  applyServoPreset("tiankong35|waist");
  if (!(RIG.servoRange[8] === 270 && RIG.pulseMax[8] === 2500 && RIG.servoMaxDps[8] === 250))
    fails.push("tiankong35 waist preset did not set the WAIST joint");
  if (RIG.servoRange[9] === 270) fails.push("waist preset leaked into the shrug");
  applyServoPreset("mg90s|shrug");
  if (!(RIG.servoRange[9] === 180 && RIG.pulseMax[9] === 2400))
    fails.push("mg90s shrug preset did not set the SHRUG joint");
  // servo TRAVEL: a 180 servo through 1.2:1 cannot reach a wide joint range,
  // a 270 servo can — and the preset must carry the travel with it.
  RIG.gearPinion = new Array(NJ).fill(15); RIG.gearGear = new Array(NJ).fill(18);
  RIG.min = new Array(NJ).fill(10); RIG.max = new Array(NJ).fill(170);
  RIG.servoRange = new Array(NJ).fill(180);
  const w180 = travelWarning(0);
  RIG.servoRange = new Array(NJ).fill(270);
  const w270 = travelWarning(0);
  if (!w180) fails.push("180 deg servo not flagged as too narrow for a 10-170 joint");
  if (w270) fails.push("270 deg servo wrongly flagged as too narrow: " + w270);
  RIG.min = new Array(NJ).fill(60); RIG.max = new Array(NJ).fill(120);
  RIG.servoRange = new Array(NJ).fill(180);
  if (travelWarning(0)) fails.push("180 deg servo wrongly flagged on a narrow joint");
  applyServoPreset("generic270|sh");
  if (!(RIG.servoRange[0] === 270 && RIG.servoRange[4] === 270))
    fails.push("generic270 preset did not set the shoulders' travel");
  if (RIG.servoRange[2] !== 180)
    fails.push("generic270 preset leaked travel into the elbows");
  // FRAME RATE: presets carry a rate (default 50 Hz for all types now) and a
  // RATE change must hit only its group, not leak elsewhere.
  RIG.frameHz = new Array(NJ).fill(111);
  applyServoPreset("pdi1181mg|sh");
  if (!shIdx.every(i => RIG.frameHz[i] === 50))
    fails.push("pdi1181mg preset did not set 50 Hz on the shoulders");
  if (!elIdx.every(i => RIG.frameHz[i] === 111))
    fails.push("pdi1181mg preset changed the elbows' frame rate");

  RIG.servoMaxDps = save.dps; RIG.pulseMin = save.lo; RIG.pulseMax = save.hi;
  RIG.servoRange = save.rng; RIG.min = save.mn; RIG.max = save.mx;
  RIG.gearPinion = save.gp; RIG.gearGear = save.gg; RIG.frameHz = save.hz;
  rigChanged(); renderRigUI();
  document.title = fails.length
    ? "SERVO FAIL " + fails.join(" | ")
    : `SERVO PASS slowJointStretched=${fastElbow}->${slowElbow}ms otherMoveUnchanged=${shAfter}ms presets=perGroup travel=ok frameRate=default50`;
  console.log(document.title);
}

// ---------------------------------------------------------------- boot
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

  if (addr.indexOf("usb:") === 0) {
    const bits = addr.slice(4).split(":");
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
  } else if (qp.get("ip") || addr.indexOf("wifi:") === 0) {
    $("robotIp").value = qp.get("ip") || addr.slice(5);
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
