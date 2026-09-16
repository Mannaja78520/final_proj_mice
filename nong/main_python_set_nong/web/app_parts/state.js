let currentUser = null;
let pendingConnect = null;
// --- state ---
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
