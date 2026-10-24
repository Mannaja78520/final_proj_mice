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
const STAB_BTN = { pose: "tabBtnMove", sequence: "tabBtnSeq", video: "tabBtnVideo", shows: "tabBtnShows",
                   robot: "tabBtnRobot", setup: "tabBtnSetup" };
let sideTab = "pose";
// --- notices ---
// A FAILURE HAS TO SURVIVE BEING LOOKED AWAY FROM. The per-card status lines
// are right for routine chatter and wrong for a failure, for two reasons that
// were both real in this file:
//
//   * the card belongs to ONE tab, so `USB disconnected` was written into the
//     Robot card while the operator was posing, and nobody saw it;
//   * the monitor loop rewrites robotStat on every poll, so even a message
//     somebody WAS looking at vanished within a second.
//
// So a failure also comes here: one line under the tab strip, visible on every
// tab, written only by this function and cleared only by hand or by the next
// notice. Routine status keeps going to the cards, because a line that shouts
// about everything is a line nobody reads.
// The SAME message, said again, is not news. The monitor loop polls every
// second and its failure branch says "monitor: no reply" every time, so
// without this a dismissed notice reappeared before the mouse had moved away -
// and a warning you cannot get rid of is one you learn to ignore. A DIFFERENT
// message always shows, dismissed or not: that is something new going wrong.
let noticeSaid = null;
function notice(text) {
  const box = $("notice"), t = $("noticeText");
  if (!box || !t || !text) return;
  if (text === noticeSaid && box.hidden) return;   // dismissed, and unchanged
  noticeSaid = text;
  t.textContent = text;
  box.hidden = false;
}

function clearNotice() {
  const box = $("notice");
  if (box) box.hidden = true;      // noticeSaid is kept: see notice()
}

function showTab(which) {
  if (which === "move") which = "pose";          // the old name
  if (!STAB_BTN[which]) which = "pose";
  sideTab = which;
  if (which === "shows" && typeof refreshShows === "function") refreshShows();   // saved elsewhere since
  if (which === "sequence" && typeof talkShown === "function") talkShown();      // A46-1: refit if the rig changed
  
  let renderWhich = which;
  if (!currentUser && (which === "robot" || which === "setup")) {
    renderWhich = "login";
  }
  
  // both old containers stay visible; the cards inside decide for themselves
  $("tabMove").style.display = "";
  $("tabSetup").style.display = "";
  document.querySelectorAll("[data-stab]").forEach(el => {
    el.style.display = el.dataset.stab === renderWhich ? "" : "none";
  });
  
  const userCard = $("userManageCard");
  if (userCard) {
    userCard.style.display = (currentUser === "super_admin" && renderWhich === "setup") ? "" : "none";
    if (userCard.style.display === "") populateUserList();
  }
  
  Object.keys(STAB_BTN).forEach(k => {
    const b = $(STAB_BTN[k]);
    if (b) b.classList.toggle("on", k === which);
  });
  if (typeof vidPage === "function") vidPage(which === "video");   // the Video page's stage
}

// THE TIMELINE HANDLE DRAGS TOO (user 2026-09-16: *timeline below has the
// drag but cannot drag to make it smaller or bigger ... like the right side,
// with a scroller*). #timeDrag had CSS and no code. Same rules as the side
// panel: remembered, keyboard, double-click resets; #timeline scrolls inside.
function initTimeDrag() {
  const tl = $("timeline"), handle = $("timeDrag");
  if (!tl || !handle) return;
  const MINH = 120, STEP = 24;
  const maxH = () => Math.max(MINH, Math.round(window.innerHeight * 0.8));
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-orientation", "horizontal");
  handle.setAttribute("aria-label", "Resize the timeline");
  handle.setAttribute("tabindex", "0");
  const setHeight = (h, remember) => {
    // a chosen height lifts style.css's default cap; a reset brings it back
    tl.style.maxHeight = h === null ? "" : "none";
    if (h === null) { tl.style.height = ""; localStorage.removeItem("nong_timeh"); }
    else tl.style.height = Math.min(maxH(), Math.max(MINH, Math.round(h))) + "px";
    handle.setAttribute("aria-valuenow", parseInt(tl.style.height) || 0);
    resize();                       // the 3D view gets the space back
    if (remember && h !== null) localStorage.setItem("nong_timeh", parseInt(tl.style.height));
  };
  const saved = +localStorage.getItem("nong_timeh");
  if (saved) setHeight(saved, false);
  const now = () => parseInt(tl.style.height) || tl.getBoundingClientRect().height;
  handle.addEventListener("keydown", (e) => {
    let h = null, hit = true;
    if (e.key === "ArrowUp") h = now() + STEP;        // timeline grows upwards
    else if (e.key === "ArrowDown") h = now() - STEP;
    else if (e.key === "PageUp") h = now() + STEP * 4;
    else if (e.key === "PageDown") h = now() - STEP * 4;
    else if (e.key === "Home") { setHeight(null, true); e.preventDefault(); return; }
    else hit = false;
    if (!hit) return;
    e.preventDefault();
    setHeight(h, true);
  });
  handle.addEventListener("dblclick", () => setHeight(null, true));
  let dragging = false, startY = 0, startH = 0;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true; startY = e.clientY; startH = now();
    try { handle.setPointerCapture(e.pointerId); } catch (_) { /* pointer already gone */ }
  });
  handle.addEventListener("pointermove", (e) => {
    if (dragging) setHeight(startH + (startY - e.clientY), false);
  });
  handle.addEventListener("pointerup", () => {
    if (!dragging) return;
    dragging = false;
    if (tl.style.height) localStorage.setItem("nong_timeh", parseInt(tl.style.height));
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

window.addEventListener('DOMContentLoaded', function(){
  var h = (location.hash || '').replace('#', '');
  if(h && typeof showTab === 'function') showTab(h);
});
window.addEventListener('hashchange', function(){
  var h = (location.hash || '').replace('#', '');
  if(h && typeof showTab === 'function') showTab(h);
});
// --- fold a side card to its title (A31-24) ---
// User 2026-09-24: *all card in the top right which tab is more than 1 card or
// hard to scroll down to setup can hide it like the POSE tab*. In a tab with
// two or more cards, the h2 folds its card. Setup starts folded (a list of
// titles); other tabs keep their first card open. The choice is kept per browser.
const FOLD_KEY = "nong_folded";
function initCardFold() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(FOLD_KEY)) || {}; } catch (e) {}
  const byTab = {};
  document.querySelectorAll("#side div.card[data-stab]").forEach(c => {
    (byTab[c.dataset.stab] = byTab[c.dataset.stab] || []).push(c);
  });
  Object.entries(byTab).forEach(([tab, cards]) => {
    if (cards.length < 2) return;
    cards.forEach((card, i) => {
      const h = card.querySelector(":scope > h2");
      if (!h) return;
      const key = tab + ":" + h.firstChild.textContent.trim();
      card.classList.add("foldable");
      h.tabIndex = 0;
      h.setAttribute("role", "button");
      const set = (folded, remember) => {
        card.classList.toggle("folded", folded);
        h.setAttribute("aria-expanded", String(!folded));
        if (!remember) return;
        saved[key] = folded;
        try { localStorage.setItem(FOLD_KEY, JSON.stringify(saved)); } catch (e) {}
      };
      set(key in saved ? saved[key] : (tab === "setup" || i > 0), false);
      const toggle = (e) => {
        // a switch inside the title (Robot link's technical-details box) is not a fold
        if (e.target.closest("label, input, button, select, a")) return;
        set(!card.classList.contains("folded"), true);
      };
      h.addEventListener("click", toggle);
      h.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(e); }
      });
    });
  });
}
initCardFold();
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

// ---- which side of each hand faces up (A44-1) ------------------------------
// User 2026-10-19: a hand-like part is fixed to each forearm, and whether the
// audience sees the PALM or the BACK of it on top changes how a move feels.
// The arm has no wrist roll, so the facing comes from the whole arm's shape:
// the same hand position can be reached with the forearm rolled one way or the
// other. RIG.palmTurn says where the palm sits around each forearm (0 = the
// forearm's own +Z); the 3D view draws it and facePalm() solves for it.
// This replaces A31-6's "front arm / back arm", which the user did not want.
const HANDS = [{ side: "L", label: "Left hand" }, { side: "R", label: "Right hand" }];

// The editable rig: body dimensions (mm, visual only — timing never depends
// on them) + per-joint calibration. "zero" = the servo angle at which that
// joint is straight (arm hanging along the body). If your real robot at
// all-90 holds the arms away from the body, set each joint's zero to the
// servo angle where the arm actually hangs — adjust it in the Rig setup
// card, never in code. Persisted in the browser + saved into projects.
const DEFAULT_RIG = {
  extraClearanceMm: 0,       // extra space BETWEEN parts, above the 4 mm base
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
  // A48-1 robot look (urdf_view.js / urdf_view.json): which look, which URDF,
  // whose sizes the simple shapes use ("urdf" or "custom"), your own sizes
  // kept while the URDF's are in use, and the URDF's last measured sizes.
  view: { look: "rig", model: "", sizes: "custom", custom: null, urdfDims: null, oldRig: null, cadAt: "" },
  zero: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
  axis: [...DEFAULT_AXIS],        // rotation axis per joint (roll/pitch/yaw)
  invert: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  neutral: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90], // the show's "Neutral pose" (Studio only)
  // Robot HOME: where the board goes on power-up and on Home (its NEUTRAL
  // command). Split from neutral on user request 2026-09-17.
  home: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
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
  // A48-6 (user 2026-10-23 "make it like the CAD"): what a CAD needs that the
  // tilts alone cannot say, filled by "Make the simple shapes match the CAD"
  // (rig_from_cad.js). after = a fixed turn AFTER each servo (roll/pitch/yaw
  // deg): a CAD bone need not be square to its joint's axis. mount = each
  // shoulder's offset (mm) from the symmetric spot. order = each arm's joints
  // from the body out, as the CAD chains them. Defaults change nothing.
  after: [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]],
  mount: { L: [0, 0, 0], R: [0, 0, 0] },
  order: [[0, 1, 2, 3], [4, 5, 6, 7]],
  // SIZES per universal joint / per bar, indexed like PAIRS:
  //   0 = L shoulder, 1 = L elbow, 2 = R shoulder, 3 = R elbow
  // bar hanging from it (0/1 = L upper arm / L forearm, 2/3 = R upper / R fore).
  // Scaled to the real spherical joints (~89 mm dia -> r ~42) and ~10 mm bars.
  jointR: [42, 40, 42, 40],
  barR:   [12, 10, 12, 10],
  // Where the palm sits around each forearm, degrees about the bar [L, R].
  // Set in Setup by turning the drawn hand until it matches the real one.
  palmTurn: [0, 0],
};
function mergeRig(saved) {
  const r = { ...JSON.parse(JSON.stringify(DEFAULT_RIG)), ...saved,
              dims: { ...DEFAULT_RIG.dims, ...(saved.dims || {}) },
              view: { ...DEFAULT_RIG.view, ...(saved.view || {}) } };
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
  // A rig saved before the split used neutral for both; keep that robot's home.
  if (!Array.isArray(r.home) && Array.isArray(r.neutral)) r.home = [...r.neutral];
  ["zero", "min", "max", "axis", "invert", "neutral", "home", "offset",
   "gearPinion", "gearGear", "pulseMin", "pulseMax", "servoMaxDps", "servoRange",
   "frameHz"].forEach(fixLen);
  // The SHRUG 4-bar calibration. An empty list means "not measured", which is
  // the old symmetric behaviour — so every rig saved before this keeps looking
  // exactly as it did until you actually measure the linkage.
  delete r.frontArm;                          // A31-6, replaced by palmTurn
  r.palmTurn = [0, 1].map(i => {
    const v = Array.isArray(r.palmTurn) ? +r.palmTurn[i] : 0;
    return isFinite(v) ? ((v % 360) + 360) % 360 : 0;
  });
  if (!Array.isArray(r.shrugCurve)) r.shrugCurve = [];
  r.shrugCurve = r.shrugCurve
    .filter(pt => pt && isFinite(+pt.j))
    .map(pt => ({ j: +pt.j, l: +pt.l || 0, r: +pt.r || 0 }));

  if (!Array.isArray(r.tilt)) r.tilt = JSON.parse(JSON.stringify(DEFAULT_RIG.tilt));
  r.tilt = DEFAULT_RIG.tilt.map((d, i) =>
    (Array.isArray(r.tilt[i]) && r.tilt[i].length === 3) ? r.tilt[i] : [...d]);
  r.after = DEFAULT_RIG.after.map((d, i) =>
    (Array.isArray(r.after) && Array.isArray(r.after[i]) && r.after[i].length === 3) ? r.after[i].map(v => +v || 0) : [...d]);
  const m3 = (v) => Array.isArray(v) && v.length === 3 ? v.map(x => +x || 0) : [0, 0, 0];
  r.mount = { L: m3((r.mount || {}).L), R: m3((r.mount || {}).R) };
  // an order only swaps WITHIN a pair (shoulder pair first, then the elbow pair)
  r.order = [0, 4].map((b, a) => {
    const o = Array.isArray(r.order) && Array.isArray(r.order[a]) ? r.order[a].map(Number) : [];
    const ok = o.length === 4 && [o[0], o[1]].sort().join() === [b, b + 1].join() && [o[2], o[3]].sort().join() === [b + 2, b + 3].join();
    return ok ? o : [b, b + 1, b + 2, b + 3];
  });
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
// A48-6: the parts taken from the CAD (rig_from_cad.js), pressed on ANY
// browser of this hub, are served as NONG_RIG_CAD = {at, parts} and adopted
// once per press; this browser's own rig is kept to come back to. parts null
// = put back. Only the geometry: never a servo number.
const RIG_CAD_KEYS = ["dims", "tilt", "after", "mount", "order"];
function rigCadAdopt(r, cad) {
  if (!cad || typeof cad !== "object" || typeof cad.at !== "string" || r.view.cadAt === cad.at) return false;
  const copy = (v) => JSON.parse(JSON.stringify(v));
  if (cad.parts && typeof cad.parts === "object") {
    if (!r.view.oldRig) r.view.oldRig = copy(RIG_CAD_KEYS.reduce((o, k) => (o[k] = r[k], o), {}));
    Object.assign(r.dims, cad.parts.dims || {});
    ["tilt", "after", "mount", "order"].forEach(k => { if (cad.parts[k]) r[k] = copy(cad.parts[k]); });
    r.view.sizes = "cad";
  } else if (r.view.oldRig) {
    RIG_CAD_KEYS.forEach(k => { if (r.view.oldRig[k] !== undefined) r[k] = copy(r.view.oldRig[k]); });
    r.view.oldRig = null;
    r.view.sizes = "custom";
  }
  r.view.cadAt = cad.at;
  return true;
}
try { if (rigCadAdopt(RIG, window.NONG_RIG_CAD)) { RIG = mergeRig(RIG); localStorage.setItem("nong_rig", JSON.stringify(RIG)); } }
catch (e) { console.warn("rig parts from the CAD ignored:", e); }
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
const SETTINGS_KEYS = ["nong_rig", "nong_rig_default", "nong_meshes", "nong_sidew",
                       "nong_ask_unsaved"];

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
// Safety cap on PEAK joint speed, firmware NONG_SAFE_DPS; the board's own
// value (INFO safe_dps) replaces it on connect so both sides time moves alike.
let SAFE_DPS = 60;
let boardSafeDpsMax = 0;    // from INFO max_dps; 0 means this board cannot be configured here
let boardSafePeer = 0;      // linked board needs the same cap for synchronized moves
let boardSafeIdentity = ""; // never save a persistent setting to a different board
// --- scene ---
const viewport = $("viewport");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputEncoding = THREE.sRGBEncoding; // painted textures keep their colors
viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim());
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
// Which flat plane the view is locked to, "" while the view is free 3D.
// Read by the drag code and by the status line, so one answer serves both.
let viewPlane = "";
function flatView() { return !!viewPlane; }
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
  // A PLANE VIEW STAYS FLAT. Orbiting is the only way to leave the plane, and
  // a plain left-drag orbits - so picking Front, taking hold of the arm and
  // pulling quietly turned the flat view back into a 3D one, and the drag
  // plane the person had chosen no longer matched what they were looking at
  // (user 2026-09-23: *i see in 2d but the arm when am drag it in 3d so i
  // cannot drag it in 2d anymore*). Pan and zoom stay; the 3D button is how
  // you come back out.
  viewPlane = v.plane === "cam" ? "" : v.plane;
  controls.enableRotate = !viewPlane;
  // drive the drag plane + its dropdown to match the view
  if ($("dragPlane")) $("dragPlane").value = v.plane;
  document.querySelectorAll("#viewCube button").forEach(b =>
    b.classList.toggle("on", b.dataset.view === name));
  viewCubeOpen(false);
}
// On a phone the view buttons covered half the 3D view (audit 2026-10-14), so
// there they fold behind one button and fold again once a view is picked.
// style.css shows that button only on a narrow screen; elsewhere this is moot.
function viewCubeOpen(open) {
  const cube = $("viewCube"), btn = $("viewCubeBtn");
  if (!cube) return;
  if (open === undefined) open = !cube.classList.contains("open");
  cube.classList.toggle("open", open);
  if (btn) btn.setAttribute("aria-expanded", String(open));
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
let palmMarks = [];     // the drawn hand per arm; its local +Z is the palm (A44-1)
const palmCache = new Map(); // "arm|pose" -> palm upness; emptied on every rebuild
let linkHolders = {};   // name -> group whose first child is the visual (STL-replaceable)
let urdfOn = false;     // A48-1: the handles above live in a URDF tree (urdf_view.js)
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
  const mt = RIG.mount[side > 0 ? "L" : "R"];
  anchor.position.set(side * d.shoulderX + mt[0], -(d.shrugPivot || 0) + mt[1], mt[2]);
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

  // the joints from the body out (RIG.order: a CAD may chain a pair the other
  // way round); the bars hang on the 2nd and 4th, whichever joints those are
  const ord = RIG.order[side > 0 ? 0 : 1];
  const shP = new THREE.Group(); anchor.add(shP);
  const shR = new THREE.Group(); shP.add(shR);
  jointGroups[ord[0]] = shP; jointGroups[ord[1]] = shR;

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

  const elP = new THREE.Group(); elAnchor.add(elP);
  const elR = new THREE.Group(); elP.add(elR);
  jointGroups[ord[2]] = elP; jointGroups[ord[3]] = elR;

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

  // The hand, drawn so the audience's view can be judged here (A44-1): skin
  // on the palm, grey on the back. Turned about the bar by RIG.palmTurn to sit
  // like the real one; its local +Z is the palm normal facePalm() works with.
  const hand = new THREE.Group();
  hand.position.set(0, -foreLen, 0);
  hand.rotation.y = THREE.MathUtils.degToRad(RIG.palmTurn[side > 0 ? 0 : 1] || 0);
  const back = new THREE.Mesh(new THREE.BoxGeometry(34, 46, 5),
                              new THREE.MeshStandardMaterial({ color: 0x7d8590 }));
  back.position.y = -30;
  const palm = new THREE.Mesh(new THREE.PlaneGeometry(30, 42),
                              new THREE.MeshStandardMaterial({ color: 0xf2b8a0 }));
  palm.position.set(0, -30, 2.6);
  back.userData.skel = palm.userData.skel = true;    // never hidden under an STL
  hand.add(back, palm);
  elR.add(hand);
  palmMarks.push(hand);
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
  jointGroups = []; pickMeshes = []; wristBalls = []; elbowBalls = []; palmMarks = []; linkHolders = {};
  palmCache.clear();
  // A48-1: the CAD model look builds the URDF's own tree and points every
  // handle into it (urdf_view.js); otherwise the simple shapes below.
  if (!urdfBuildInto(robot)) buildRigShapes();
  clearGizmo(); selPair = -1;
  applyMeshes();   // put assigned STLs back onto the fresh link holders
  applyPose();
}

// the old look: simple shapes sized by the Rig setup
function buildRigShapes() {
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
  // (each ring on its own joint's parent, so a swapped pair keeps them right)
  pairRingParents = [0, 2, 4, 6].map(i => [jointGroups[i].parent, jointGroups[i + 1].parent]);
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
// the fixed turn after joint i's servo (RIG.after, A48-6)
function jointAfterQuat(i, out) {
  const t = RIG.after[i] || [0, 0, 0];
  _eTilt.set(THREE.MathUtils.degToRad(t[0]), THREE.MathUtils.degToRad(t[1]),
             THREE.MathUtils.degToRad(t[2]), "XYZ");
  return (out || new THREE.Quaternion()).setFromEuler(_eTilt);
}
function jointAxisVec(i) {
  if (urdfOn) return urdfAxisVec(i);
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
  if (typeof markDirty3d === "function") markDirty3d(5);
  if (urdfOn) { urdfApplyPose(); return; }
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
    g.quaternion.multiply(jointAfterQuat(i, _qBase));
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
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY + RIG.mount.L[1] + rise.l;
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY + RIG.mount.R[1] + rise.r;
    } else {
      // Uncalibrated: the original symmetric see-saw, unchanged. SHRUG is a
      // ROLL about the front-back axis (Z) — one shoulder rises while the
      // other drops.
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY + RIG.mount.L[1];   // + its own height (A48-6)
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY + RIG.mount.R[1];
      // At the TRUE angle: it was drawn x3 so a small move would read, and 10
      // deg on the robot showed as 30 (user 2026-09-17, A26-45).
      shoulderMount.rotation.set(0, 0, THREE.MathUtils.degToRad(jointDelta(9)));
    }
  }
  if (typeof markDirty3d === "function") markDirty3d(5);
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
// only what is taken goes in the parts (another browser keeps its own rest)
function rigCadParts(m) {
  const p = { dims: m.dims };
  if (rigCadTakes("shoulders")) p.mount = m.mount;
  if (rigCadTakes("joints")) { p.tilt = m.tilt; p.after = m.after; p.order = m.order; }
  return p;
}
// every browser of this hub picks it up on its next load (rig_data.js)
async function rigCadShare(cad) {
  try {
    const r = await fetch("/api/rigcad", { method: "POST", body: JSON.stringify(cad) }).then(r => r.json());
    if (!r.ok) throw new Error(r.error || "no answer");
    return true;
  } catch (e) {
    rigCadLast += " Kept on this browser only: the hub did not take it (" + (e.message || e) + ").";
    renderRigCadUI();
    return false;
  }
}
// Make it: the old rig is kept (once: a second make keeps the hand-made one).
function rigFromCad() {
  const m = rigFromCadMeasure();
  if (m.error) { rigCadLast = "Cannot make the simple shapes from the CAD: " + m.error + "."; renderRigCadUI(); return false; }
  const cad = { at: new Date().toISOString(), parts: rigCadParts(m) };
  const before = rigHandsAt(RIG, RIG.home);
  rigCadAdopt(RIG, cad);
  const mv = rigHandsAt(RIG, RIG.home).map((p, a) => Math.round(p.distanceTo(before[a])));
  rigCadLast = (rigCadTakes("joints") ? "The simple shapes now match the CAD." : "The simple shapes now have the CAD's sizes and shoulder spots; your joints are kept.") + " At home the left hand moved " + mv[0] + " mm and the right " + mv[1] +
    " mm; the servo numbers did not change." + (m.warn.length ? " " + m.warn.join("; ") + "." : "");
  rigChanged();
  rigCadShare(cad);
  return true;
}
// Back to the rig kept before the first make, on every browser of this hub.
function rigOldBack() {
  if (!RIG.view.oldRig) return false;
  const cad = { at: new Date().toISOString(), parts: null };
  rigCadAdopt(RIG, cad);
  rigCadLast = "Your old simple shapes are back.";
  rigChanged();
  rigCadShare(cad);
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
// --- gizmo rings ---
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
// --- picking / drag ---
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
  // In a FLAT view there is nothing to orbit (setView turns rotation off), so
  // Shift is not needed there: picking Front and pulling the hand is the whole
  // gesture the 2D plane exists for.
  if (e.shiftKey || flatView()) {
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
    if (target) {
      solveIK(drag.arm, target, 16);
      holdSide(drag.arm, false);    // A45-28: keep the side picked on top
      askReach(drag.arm, target);
      poseChanged(true);
    }
  } else if (drag.kind === "ikElbow") {
    const target = planeHit(drag.planePoint, drag.normal);
    // move the elbow by rotating only the 2 shoulder servos
    if (target) { solveElbowIK(drag.arm, target); poseChanged(true); }
  }
});
window.addEventListener("pointerup", () => {
  if (!drag) return;
  // released: now the whole swing may be searched for the side kept on top
  if (drag.kind === "ik" && handHold[drag.arm]) {
    const t = reachAsk[drag.arm] && reachAsk[drag.arm].target;
    holdSide(drag.arm, true);
    if (t) askReach(drag.arm, t);
  }
  drag = null; controls.enabled = true; poseChanged(false);
});

function clampDeg(v) { return Math.min(180, Math.max(0, Math.round(v * 10) / 10)); }
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
// ---- the same shape on the other arm (A31-6) ------------------------------
// User 2026-09-23: a move picks which arm plays it, so the same move can be
// mirrored.
//
// Mirroring is NOT swapping the two blocks of four joint numbers. That is what
// it looked like, because the right arm is drawn as the left's mirror image -
// but the two arms do not carry the same `invert` flags in the shipped rig
// (L_EL_R is 0, R_EL_R is 1), so a copied elbow roll came out backwards and
// the hand landed 613 mm from where it should have been. Deriving the angles
// from zero/jdir/axis instead was worse: 528 mm, because that model ignores
// the mounting tilts and where each arm's base actually sits.
//
// So mirroring is done where the truth is - in the geometry. Reflect both the
// elbow and the wrist in the body's own x = 0 plane, then let the existing
// solvers put each arm there: the shoulders place the elbow, the elbow joints
// place the wrist. Both targets together leave no slack in a 4-joint arm, so
// the answer is the mirror and not merely a pose that reaches the same point.
// check_arm_mirror measures the hands afterwards, in world space.
// Reflect a world point in one of the body's OWN planes. "lr" is the plane
// between the two arms, "fb" is the one between front and back - and both are
// taken in the body's frame, so a turned waist does not tilt the mirror.
function mirrorAcrossBody(p, which) {
  const local = bodyGroup.worldToLocal(p.clone());
  if (which === "fb") local.z = -local.z; else local.x = -local.x;
  return bodyGroup.localToWorld(local);
}
// Returns the mirrored pose, or null if there is no rig on screen to mirror
// with. The two BODY joints keep the rule mirrorLR() has always used: the
// waist reflects about 90 (turning left becomes turning right) and the shrug
// is unchanged, because it lifts both shoulders about the centre line and a
// reflection leaves it alone.
function mirrorPose(p, which) {
  if (!bodyGroup || !wristBalls[0] || !wristBalls[1]) return null;
  const saved = pose.slice();
  try {
    pose = p.slice();
    applyPose();
    robot.updateMatrixWorld(true);
    const want = [0, 1].map(a => ({
      elbow: mirrorAcrossBody(elbowBalls[a].getWorldPosition(new THREE.Vector3()), which),
      wrist: mirrorAcrossBody(wristBalls[a].getWorldPosition(new THREE.Vector3()), which),
    }));
    for (const a of [0, 1]) {
      // LEFT/RIGHT swaps the arms - the left arm takes the right's shape.
      // FRONT/BACK does not: each arm stays on its own side of the body and
      // only its reach turns round, which is what "the same gesture, facing
      // the other way" means for a puppet.
      const t = which === "fb" ? want[a] : want[1 - a];
      solveElbowIK(a, t.elbow);
      ccdChain(a === 0 ? [2, 3] : [6, 7], wristBalls[a], t.wrist, 24);
    }
    applyPose();
    const out = pose.slice();
    // A reflection reverses a turn about the vertical, whichever plane it is
    // in, so the waist flips about its own neutral either way. The shrug rocks
    // about the centre line and a reflection leaves it alone.
    out[8] = clampJ(8, 180 - p[8]);
    out[9] = p[9];
    return out;
  } finally {
    pose = saved;
    applyPose();
  }
}
// ---- which side of the hand faces up (A44-1) ------------------------------
// The arm has four joints and a hand position needs three, so one freedom is
// left over: the elbow can swing round the shoulder-to-hand line and the hand
// stays put. Swinging it rolls the forearm, and with it the hand. facePalm()
// walks that swing both ways and keeps the shape whose palm (or back) points
// most nearly up, with the hand where it was. Joint limits still hold, so on
// some reaches the best it can do is "on edge"; the caller says so.
// How much the palm faces up right now: +1 straight up, -1 the back is up.
function palmUpness(arm) {
  robot.updateMatrixWorld(true);
  const q = palmMarks[arm].getWorldQuaternion(new THREE.Quaternion());
  return new THREE.Vector3(0, 0, 1).applyQuaternion(q).y;
}
// The same, for any pose; the pose on screen is left as it was. Cached, as
// the timeline asks it for every move on every redraw.
function palmUpnessOf(p, arm) {
  if (!palmMarks[arm]) return 0;
  const key = arm + "|" + p.join(",");
  if (palmCache.has(key)) return palmCache.get(key);
  const saved = pose;
  try { pose = p.slice(); applyPose(); palmCache.set(key, palmUpness(arm)); }
  finally { pose = saved; applyPose(); }
  return palmCache.get(key);
}
// "palm", "back" or "side": what the audience sees on top of that hand.
function palmWord(v) { return v > 0.5 ? "palm" : v < -0.5 ? "back" : "side"; }
// want +1 = palm up, -1 = back up. Returns { pose, upness } or null with no rig.
// opts (A45-28): range/step = how far round each way and in what steps (deg),
// small while a hand is dragged so the arm keeps its shape near where it was;
// safe = never pick a shape that hits the body or the other arm, unless the
// pose it started from already did (then there is nothing to keep).
function facePalm(p, arm, want, opts) {
  const o = opts || {}, range = o.range || 180, step = o.step || 5;
  if (!palmMarks[arm] || !wristBalls[arm]) return null;
  const sh = arm === 0 ? [0, 1] : [4, 5], el = arm === 0 ? [2, 3] : [6, 7];
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const saved = pose;
  try {
    pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
    const S = W(jointGroups[sh[0]]), hand = W(wristBalls[arm]);
    const elbow0 = W(elbowBalls[arm]);
    const axis = hand.clone().sub(S).normalize();
    const safe = o.safe && !collisionAt(p);
    let best = { score: want * palmUpness(arm), pose: p.slice() };
    for (const dir of [1, -1]) {
      pose = p.slice();
      for (let deg = step; deg <= range; deg += step) {
        const e = elbow0.clone().sub(S).applyAxisAngle(axis, dir * deg * Math.PI / 180).add(S);
        ccdChain(sh, elbowBalls[arm], e, 8);
        const miss = ccdChain(el, wristBalls[arm], hand, 12);
        applyPose();             // ccdChain leaves its last rejected try drawn
        if (miss > 4) continue;  // the hand moved: that shape is not an answer
        const sc = want * palmUpness(arm);
        if (sc > best.score + 1e-3 && !(safe && collisionAt(pose)))
          best = { score: sc, pose: pose.slice() };
      }
    }
    return { pose: best.pose, upness: want * best.score };
  } finally {
    pose = saved;
    applyPose();
  }
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
  const extra = RIG.extraClearanceMm ?? 0;
  if (!Number.isFinite(extra) || extra < 0) return "the extra safety gap is invalid";
  const clearance = CLEAR + extra;
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
      if (distToBox(pt, hx, hy, hz) < r + clearance) return s.n + " is too close to the body";
      if (pt.distanceTo(headC) < r + R_HEAD + clearance) return s.n + " is too close to the head";
    }
  }
  // left arm vs right arm (all segment pairs)
  const L = [segs[0], segs[1]], R = [segs[2], segs[3]];
  for (const sl of L)
    for (const sr of R)
      if (segSegDist(sl.a, sl.b, sr.a, sr.b) < sl.r + sr.r + clearance)
        return sl.n + " is too close to the " + sr.n;
  if (k.wrL.distanceTo(k.wrR) < 2 * R_WRIST + clearance) return "the hands are too close to each other";
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
// Preview can show a refused move, but the robot cannot bypass this gate.
// Match the model and clothing gap in Setup before asking for another route.
let crashForced = false;
let previewOnly = false;   // this run draws, but does not drive the arm

function crashGate(action) {
  const problems = checkCollisions(false);
  if (!problems.length) { crashForced = false; return true; }
  const shown = problems.slice(0, 6).join("\n") +
    (problems.length > 6 ? "\n…and " + (problems.length - 6) + " more" : "");
  crashForced = false;
  const st = $("tlStat");
  const message="Not sent: this movement does not keep the safety gap. Fix the red keyframes or adjust the rig/gap in Setup.\n"+shown;
  if (st) st.textContent = message;
  notice(message);
  return false;
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
// --- safe paths (A46-1) ---
// User 2026-10-22: the arm must not hit itself when it copies a person or
// gestures while talking. A move is a straight line in joint space (the board
// eases every joint together), so the fast answer is that line, checked with
// collisionAt() on THIS rig's sizes. Only when the line hits does a planner
// look for a way round: a quick RRT-Connect seed, then genuine RRT* parent
// selection and rewiring, followed by checked shortcuts. The choices are DATA in
// safe_path.json beside this page (planner, step, budgets); the long story is
// in qc/checks/check_safe_path.py.
let SAFE = {
  planner: "rrt-star",      // "straight" refuses; rrt-connect remains available
  checkDeg: 1,              // biggest joint change between two checked points
  stepDeg: 12,              // how far a tree grows per try
  goalBias: 0.2,
  budgetMs: 1500,           // planning in the editor (video, gestures)
  liveBudgetMs: 60,         // planning while following: miss it and the arm holds
  shortcuts: 60,
  seed: 1,
  seedBudgetMs: 40,
  optimizeMs: 80,
  sliceMs: 12,
  maxNodes: 2000,
  rewireFactor: 1.1,
};
let SAFE_ERROR = "";
function loadSafeSettings(j) {
  const bounds = { checkDeg: [0.05, 10], stepDeg: [0.1, 180], goalBias: [0, 1],
    budgetMs: [1, 30000], liveBudgetMs: [1, 5000], shortcuts: [0, 500],
    seed: [0, 4294967295], seedBudgetMs: [0, 100], optimizeMs: [0, 1000],
    sliceMs: [1, 50], maxNodes: [2, 10000], rewireFactor: [1, 5] };
  if (!j || typeof j !== "object") { SAFE_ERROR = "invalid path settings"; return false; }
  const next = { ...SAFE };
  for (const key of Object.keys(SAFE)) if (key in j) next[key] = j[key];
  if (!["straight", "rrt-connect", "rrt-star"].includes(next.planner)) {
    SAFE_ERROR = "unknown path planner"; return false;
  }
  for (const [key, [lo, hi]] of Object.entries(bounds)) {
    if (!Number.isFinite(next[key]) || next[key] < lo || next[key] > hi ||
        (["shortcuts", "seed", "maxNodes"].includes(key) && !Number.isInteger(next[key]))) {
      SAFE_ERROR = "invalid path setting: " + key; return false;
    }
  }
  Object.assign(SAFE, next); SAFE_ERROR = ""; return true;
}
fetch("safe_path.json").then(r => r.json()).then(loadSafeSettings).catch(() => {});
function safeRevision() { return JSON.stringify([SAFE, SAFE_ERROR, RIG]); }

// Seeded, so a plan made twice is the same plan (and QC can repeat it).
function safeRng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}
function safeGap(a, b) {   // the biggest joint change, deg
  let m = 0;
  for (let j = 0; j < NJ; j++) m = Math.max(m, Math.abs((b[j] ?? 90) - (a[j] ?? 90)));
  return m;
}
function safeLerp(a, b, f) { return a.map((v, j) => v + (b[j] - v) * f); }
// null when the pose is clear, else what hits (collisionAt's words)
function poseHit(p) { return collisionAt(p); }
// null when every checked point on the straight move a->b is clear
function pathHit(a, b) {
  if (SAFE_ERROR || !Number.isFinite(SAFE.checkDeg) || SAFE.checkDeg <= 0)
    return SAFE_ERROR || "invalid collision sampling distance";
  const n = Math.max(1, Math.ceil(safeGap(a, b) / Math.max(0.05, Math.min(1, SAFE.checkDeg))));
  for (let s = 0; s <= n; s++) {
    const hit = collisionAt(safeLerp(a, b, s / n));
    if (hit) return hit;
  }
  return null;
}
// a -> b without a hit. { path: [a, ..., b], how: "straight"|"around", ms }
// or { fail: why }. Both endpoints, including the source, must be valid.
function planSafe(a, b, budgetMs, seed) {
  const saved = pose;
  try {
    const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
    let result;
    do { result = search.next(); } while (!result.done);
    return result.value;
  } finally {
    pose = saved;
    applyPose();
  }
}
// Live search yields between iterations. sliceMs is a scheduling target;
// one geometry check and final path validation must finish before yielding.
async function planSafeAsync(a, b, budgetMs, seed, cancelled = () => false) {
  const revision = safeRevision();
  const stale = () => cancelled() || revision !== safeRevision();
  const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
  for (;;) {
    if (stale()) return { fail: "movement cancelled or safety settings changed", cancelled: true };
    const saved = pose, until = performance.now() + Math.max(1, SAFE.sliceMs);
    let result;
    try {
      do { result = search.next(); } while (!result.done && performance.now() < until);
    } finally { pose = saved; applyPose(); }
    if (result.done) return stale() ? { fail: "movement cancelled or safety settings changed", cancelled: true } : result.value;
    await new Promise(resolve => setTimeout(resolve, 0));
  }
}
function safePoseError(q) {
  if (SAFE_ERROR) return SAFE_ERROR;
  if (!Array.isArray(q) || q.length !== NJ) return "a pose needs all " + NJ + " joints";
  for (let j = 0; j < NJ; j++) {
    if (!Number.isFinite(RIG.min[j]) || !Number.isFinite(RIG.max[j]) || RIG.min[j] > RIG.max[j])
      return "the rig has invalid joint limits";
    if (!Number.isFinite(q[j])) return "a joint angle is not a number";
    if (q[j] < RIG.min[j] - 1e-6 || q[j] > RIG.max[j] + 1e-6)
      return "joint " + (j + 1) + " is outside the rig limits";
  }
  return poseHit(q);
}
function* safeSearch(a, b, budgetMs, seed) {
  const t0 = performance.now(), budget = Math.max(1, budgetMs ?? SAFE.budgetMs);
  for (const [label, q] of [["starting pose", a], ["destination", b]]) {
    const error = safePoseError(q);
    if (error) return { fail: label + ": " + error };
  }
  const stats = { rewires: 0, parentChoices: 0, improvements: 0 };
  let path, how = "straight";
  if (!pathHit(a, b)) path = [a.slice(), b.slice()];
  else {
    how = "around";
    if (SAFE.planner === "straight") return { fail: "the move goes through the body, and going round is off" };
    if (SAFE.planner === "rrt-connect") path = rrtConnect(a, b, budget, safeRng(seed ?? SAFE.seed), t0);
    else path = yield* rrtStar(a, b, budget, safeRng(seed ?? SAFE.seed), t0, stats);
    if (!path) return { fail: "no checked way round found in " + Math.round(budget) + " ms" };
    path = safeShortcut(path, safeRng((seed ?? SAFE.seed) + 7));
  }
  // Check what will actually go over the wire, after rounding/shortcuts.
  path = path.map((q, i) => i === 0 ? a.slice() : q.map(v => +fmtA(v)));
  for (let i = 0; i < path.length; i++) {
    if (safePoseError(path[i]) || (i && pathHit(path[i - 1], path[i])))
      return { fail: "the final rounded path is not clear; the robot will hold" };
  }
  return { path, how, planner: SAFE.planner, stats, ms: performance.now() - t0 };
}
// RRT*: minimum-cost checked parent, neighbor rewiring, descendant cost updates.
// A short connect search supplies an initial answer; rewiring can improve it.
function* rrtStar(a, b, budgetMs, rnd, t0, stats) {
  const end = t0 + budgetMs;
  const body = (q, f = 0.5) => q.concat([a[8] + (b[8] - a[8]) * f, a[9] + (b[9] - a[9]) * f]);
  const distance = (p, q) => Math.hypot(...p.map((v, j) => v - q[j]));
  const free = (p, q) => !pathHit(body(p), body(q));
  const goal = b.slice(0, ARMJ), nodes = [], goals = new Set();
  const add = (q, up) => {
    const n = { q, up, children: new Set(), cost: up < 0 ? 0 : nodes[up].cost + distance(nodes[up].q, q) };
    nodes.push(n);
    if (up >= 0) nodes[up].children.add(nodes.length - 1);
    return nodes.length - 1;
  };
  add(a.slice(0, ARMJ), -1);
  const seeded = rrtConnect(a, b, Math.min(budgetMs * 0.25, SAFE.seedBudgetMs), rnd, t0);
  if (seeded) for (let i = 1; i < seeded.length; i++) add(seeded[i].slice(0, ARMJ), nodes.length - 1);
  if (seeded) goals.add(nodes.length - 1);
  let best = seeded ? nodes.length - 1 : -1;
  let bestCost = best < 0 ? Infinity : nodes[best].cost;
  let improveUntil = seeded ? Math.min(end, performance.now() + SAFE.optimizeMs) : end;
  while (performance.now() < improveUntil && nodes.length < SAFE.maxNodes) {
    const sample = rnd() < SAFE.goalBias ? goal : RIG.min.slice(0, ARMJ).map((l, j) => l + rnd() * (RIG.max[j] - l));
    const ranked = nodes.map((n, i) => ({ i, d: distance(n.q, sample) })).sort((x, y) => x.d - y.d);
    const nearest = nodes[ranked[0].i].q;
    const gap = Math.max(...sample.map((v, j) => Math.abs(v - nearest[j])));
    if (gap < 1e-6) { yield; continue; }
    const q = nearest.map((v, j) => v + (sample[j] - v) * Math.min(1, SAFE.stepDeg / gap));
    const k = Math.min(nodes.length, Math.ceil(SAFE.rewireFactor * Math.E * (1 + 1 / ARMJ) * Math.log(nodes.length + 1)));
    const near = nodes.map((n, i) => ({ i, d: distance(n.q, q) })).sort((x, y) => x.d - y.d).slice(0, k);
    const parents = near.slice().sort((x, y) => nodes[x.i].cost + x.d - nodes[y.i].cost - y.d);
    let parent = -1;
    for (const n of parents) {
      if (performance.now() >= end) break;
      if (free(nodes[n.i].q, q)) { parent = n.i; break; }
    }
    if (parent < 0) { yield; continue; }
    if (parent !== ranked[0].i) stats.parentChoices++;
    const index = add(q, parent);
    for (const n of near) {
      if (performance.now() >= end) break;
      const newCost = nodes[index].cost + n.d;
      if (n.i === parent || newCost + 1e-7 >= nodes[n.i].cost || !free(q, nodes[n.i].q)) continue;
      const delta = newCost - nodes[n.i].cost;
      nodes[nodes[n.i].up].children.delete(n.i);
      nodes[n.i].up = index;
      nodes[index].children.add(n.i);
      const pending = [n.i];
      while (pending.length) { const child = pending.pop(); nodes[child].cost += delta; pending.push(...nodes[child].children); }
      stats.rewires++;
    }
    if (performance.now() < end && free(q, goal)) goals.add(index);
    for (const i of goals) {
      const cost = nodes[i].cost + distance(nodes[i].q, goal);
      if (cost + 1e-7 < bestCost) {
        if (best < 0) improveUntil = Math.min(end, performance.now() + SAFE.optimizeMs);
        else stats.improvements++;
        best = i; bestCost = cost;
      }
    }
    yield;
  }
  if (best < 0) return null;
  const qs = [goal];
  for (let i = best; i >= 0; i = nodes[i].up) if (distance(nodes[i].q, qs[qs.length - 1]) > 1e-7) qs.push(nodes[i].q);
  qs.reverse();
  return qs.map((q, i) => body(q, i / (qs.length - 1)));
}
// Two trees, one from each end, each try reaching for the other. Only the 8
// ARM joints are searched: the waist and shrug turn the body and arms
// together, so they cannot cause a hit (fkPoints holds them still) and they
// simply glide from a to b along the path.
function rrtConnect(a, b, budgetMs, rnd, t0) {
  const lo = RIG.min.slice(0, ARMJ), hi = RIG.max.slice(0, ARMJ);
  const body = (q, f) => q.concat([a[8] + (b[8] - a[8]) * f, a[9] + (b[9] - a[9]) * f]);
  const arm = p => p.slice(0, ARMJ);
  const free = (p, q) => !pathHit(body(p, 0.5), body(q, 0.5));
  const A = [{ q: arm(a), up: -1 }], B = [{ q: arm(b), up: -1 }];
  const near = (T, q) => {
    let best = 0, bd = Infinity;
    for (let i = 0; i < T.length; i++) {
      let d = 0;
      for (let j = 0; j < ARMJ; j++) d += (T[i].q[j] - q[j]) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  const steer = (from, to) => {
    const g = Math.max(...to.map((v, j) => Math.abs(v - from[j])));
    return g <= SAFE.stepDeg ? to.slice() : from.map((v, j) => v + (to[j] - v) * SAFE.stepDeg / g);
  };
  // grow T toward q by one step; the new node's index, or -1 when blocked
  const extend = (T, q) => {
    const n = near(T, q), s = steer(T[n].q, q);
    if (!free(T[n].q, s)) return -1;
    T.push({ q: s, up: n });
    return T.length - 1;
  };
  // keep growing T toward q until it gets there (the index) or is blocked
  const connect = (T, q) => {
    while (performance.now() - t0 < budgetMs) {
      const i = extend(T, q);
      if (i < 0) return -1;
      if (Math.max(...T[i].q.map((v, j) => Math.abs(v - q[j]))) < 1e-6) return i;
    }
    return -1;
  };
  const chain = (T, i) => { const out = []; for (; i >= 0; i = T[i].up) out.push(T[i].q); return out; };
  let X = A, Y = B;
  while (performance.now() - t0 < budgetMs) {
    const goal = rnd() < SAFE.goalBias ? Y[0].q : lo.map((l, j) => l + rnd() * (hi[j] - l));
    const i = extend(X, goal);
    if (i >= 0) {
      const k = connect(Y, X[i].q);
      if (k >= 0) {
        const fromA = X === A ? chain(X, i).reverse() : chain(Y, k).reverse();
        const toB = X === A ? chain(Y, k).slice(1) : chain(X, i).slice(1);
        const qs = fromA.concat(toB);
        return qs.map((q, n) => body(q, n / (qs.length - 1)));
      }
    }
    [X, Y] = [Y, X];
  }
  return null;
}
// Random shortcuts: any two points of the path that see each other directly
// lose everything between them. What is left is short and has few corners.
function safeShortcut(path, rnd) {
  let p = path.slice();
  for (let r = 0; r < SAFE.shortcuts && p.length > 2; r++) {
    const i = Math.floor(rnd() * (p.length - 2)), k = i + 2 + Math.floor(rnd() * (p.length - i - 2));
    if (k < p.length && !pathHit(p[i], p[k])) p = p.slice(0, i + 1).concat(p.slice(k));
  }
  return p;
}
// A list of timeline keys made safe in one pass (video, recording, gestures):
// a key whose pose hits is dropped (its time goes to the move before, so the
// rhythm stays), and a move that would go through the body gets in-between
// keys that go round. Each leg gets what the servos need (minTime) plus a
// share of the rest by distance. keepTime (a video's "stay with the music"):
// a way round that cannot fit in the move's own time is a fail, so the arm
// holds instead of falling behind the music. Returns
// { keys, dropped, around, failed } - failed moves are dropped too.
function safeKeys(K, budgetMs, keepTime) {
  const out = [], tally = { dropped: 0, around: 0, failed: 0 };
  for (const k0 of K) {
    const k = { ...k0, pose: k0.pose.map((v, j) => clampJ(j, v)) };
    const prev = out[out.length - 1];
    if (!prev) {
      if (poseHit(k.pose)) { tally.dropped++; continue; }
      out.push(k); continue;
    }
    const plan = planSafe(prev.pose, k.pose, budgetMs);
    if (plan.fail) {
      prev.hold = (prev.hold || 0) + (k.t || 0) + (k.hold || 0);
      tally[poseHit(k.pose) ? "dropped" : "failed"]++;
      continue;
    }
    if (plan.how === "around") {
      const legs = plan.path.slice(1).map((q, i) => safeGap(plan.path[i], q));
      const need = plan.path.slice(1).map((q, i) => Math.max(MIN_MOVE_MS, minTime(plan.path[i], q)));
      const all = legs.reduce((s, v) => s + v, 0) || 1;
      const spare = (k.t || 0) - need.reduce((s, v) => s + v, 0);
      if (keepTime && spare < 0) {
        prev.hold = (prev.hold || 0) + (k.t || 0) + (k.hold || 0);
        tally.failed++;
        continue;
      }
      tally.around++;
      const legT = i => Math.round(need[i] + Math.max(0, spare) * legs[i] / all);
      plan.path.slice(1, -1).forEach((q, i) => out.push({ pose: q, hold: 0, tset: k.tset, via: true, t: legT(i) }));
      k.t = legT(legs.length - 1);
    } else if (keepTime && minTime(prev.pose, k.pose) > (k.t || 0) + 1) {
      // a dropped pose before it made this move longer: go as far as the time
      // allows, along the line just checked clear (like vidReachSide)
      const f = Math.max(0, Math.min(1, ((k.t || 0) - 1) / minTime(prev.pose, k.pose)));
      k.pose = safeLerp(prev.pose, k.pose, f).map((v, j) => clampJ(j, v));
    }
    out.push(k);
  }
  return Object.assign({ keys: out }, tally);
}
// In words, for the status lines; "" when nothing needed changing.
function safeSay(r) {
  const bits = [];
  if (r.around) bits.push(r.around + " move" + (r.around > 1 ? "s" : "") + " go round the body instead of through it");
  if (r.dropped) bits.push(r.dropped + " pose" + (r.dropped > 1 ? "s" : "") + " would make the arm hit itself, so the arm holds instead");
  if (r.failed) bits.push(r.failed + " move" + (r.failed > 1 ? "s" : "") + " had no safe way round, so the arm holds instead");
  return bits.length ? "Safe path: " + bits.join("; ") + "." : "";
}
// One owner for Studio motion setup and individual checked waypoints.
let safeMotionEpoch = 0, safeGoalRevision = 0;
let safeMotionTail = Promise.resolve(), safeCancelTail = Promise.resolve(), lastSafeMove = Promise.resolve(true);
let safeTimelineCache = null, timelinePreparing = false;
let safeActiveDevice = null;
function safeDevice() { return {dev:moduleDev(), port:serialPort, bus:busId(), target:safeTarget()}; }
async function safeDeviceCmd(device,c) {
  if (device.dev) {
    const q=new URLSearchParams({dev:device.dev,c});
    const r=await fetch('/api/dev/cmd?'+q);
    if(!r.ok)throw new Error(await r.text());
    return (await r.text()).trim();
  }
  return serialCmd(c,{port:device.port,id:device.bus});
}
function withSafeMotion(work) {
  const result = safeMotionTail.catch(() => {}).then(async()=>{await safeCancelTail;return work();});
  safeMotionTail = result.catch(() => {});
  return result;
}
function safeTarget() { return moduleDev() + "|" + (boardSafeIdentity || ""); }
function safeMotionNote(text, warning = false) {
  if ($("robotStat")) $("robotStat").textContent = text;
  if ($("tlStat")) $("tlStat").textContent = text;
  if (warning) notice(text);
}
function cancelSafeMotion(reason) {
  const device=safeActiveDevice || (haveRobot() ? safeDevice() : null);
  liveAbort();
  if(reason!=='sequence takeover') {
    playing=false;entryHold=false;seekToken++;
    if($('playBtn'))$('playBtn').textContent='▶ Play';keepAwake(false);
  }
  if (!currentUser || !device) return Promise.resolve(false);
  const stop=safeCancelTail.catch(()=>{}).then(async () => {
    await hubStop();
    try { await safeDeviceCmd(device,"STOP"); } catch (e) { safeMotionNote("Could not confirm Stop: " + e.message, true); }
    return false;
  });
  safeCancelTail=stop;return stop;
}
function safeStale(epoch, device, revision) {
  return !currentUser || !haveRobot() || epoch !== safeMotionEpoch || device !== safeTarget() || revision !== safeRevision();
}
async function safeIdle(stale, expected, progress) {
  const deadline = performance.now() + 90000;
  while (!stale()) {
    const status = await getStatus();
    if (stale()) return null;
    const q = status.module && status.module.joints;
    if (!Array.isArray(q) || q.length !== NJ || q.some(v => !Number.isFinite(v)))
      throw new Error("the robot did not report its current pose");
    if(progress)progress(status);
    if(typeof status.module.moving!=='boolean' || !status.seq || typeof status.seq.running!=='boolean')
      throw new Error('the robot did not report whether it is moving');
    if (!status.module.moving && !status.seq.running) {
      if (expected && safeGap(q, expected) > 0.15)
        throw new Error("the robot stopped away from the checked waypoint; reconnect before retrying");
      return status;
    }
    if (performance.now() >= deadline) throw new Error("the robot did not confirm that movement finished");
    await new Promise(resolve => setTimeout(resolve, 60));
  }
  return null;
}
async function safeTakeover(stale) {
  if (stale()) return null;
  safeActiveDevice=safeDevice();
  await hubStop();
  if (stale()) return null;
  const reply = await rawCmd("STOP");
  if (!/^OK\b/.test(reply)) throw new Error(reply || "Stop was not acknowledged");
  const status = await safeIdle(stale);
  if (!status) return null;
  const m = status.module;
  if (boardSafeIdentity && String(status.chip || status.id || "") !== boardSafeIdentity)
    throw new Error("a different robot answered; reconnect first");
  for (let j = 0; j < NJ; j++) {
    if (!Array.isArray(m.min) || !Array.isArray(m.max) || !Number.isFinite(m.min[j]) || !Number.isFinite(m.max[j]) ||
        RIG.min[j] < m.min[j] - 0.01 || RIG.max[j] > m.max[j] + 0.01)
      throw new Error("Studio limits exceed the robot limits; match them in Setup before moving");
  }
  return status;
}
// Keep endpoint cues and holds on their original destination; onset cues start
// with the first detour leg. Each eased leg gets the physical minimum time.
function safeLegKeys(path, key) {
  const lengths = path.slice(1).map((q,i) => safeGap(path[i],q));
  const need = path.slice(1).map((q,i) => Math.ceil(Math.max(MIN_MOVE_MS,minTime(path[i],q))));
  const total = lengths.reduce((a,b)=>a+b,0) || 1;
  const spare = Math.max(0,(key.t || 0)-need.reduce((a,b)=>a+b,0));
  return path.slice(1).map((q,i) => ({...key,pose:q.slice(),
    t:Math.ceil(need[i]+spare*lengths[i]/total), hold:i===need.length-1 ? key.hold || 0 : 0,
    cues:i===0 ? (key.cues || []).slice() : [],
    cuesAfter:i===need.length-1 ? (key.cuesAfter || []).slice() : [],
    name:i===need.length-1 ? key.name || "" : "checked detour",via:i!==need.length-1}));
}
async function checkedPoseUnlocked(goal, requestedMs, epoch, goalRevision, initial, progress) {
  const device = safeTarget(), revision = safeRevision();
  const hardStale = () => safeStale(epoch,device,revision);
  const replaced = () => goalRevision !== null && goalRevision !== safeGoalRevision;
  const stale = () => hardStale() || replaced();
  const status = initial || await safeTakeover(hardStale);
  if (!status || hardStale()) return false;
  const source = status.module.joints.slice();
  const plan = await planSafeAsync(source,goal,SAFE.budgetMs,SAFE.seed,hardStale);
  if (hardStale()) return false;
  if (plan.fail) { safeMotionNote("Not moved: " + plan.fail,true); return false; }
  const duration = requestedMs || autoTime(source,goal,status.module.speed_dps || speedDps());
  const legs = safeLegKeys(plan.path,{t:duration,hold:0});
  if (plan.how === "around") safeMotionNote("RRT*: going around the body in " + legs.length +
    " checked moves; keeping an extra " + (RIG.extraClearanceMm || 0) + " mm gap.",true);
  let actual = source;
  for (let index=0;index<legs.length;index++) {
    const leg=legs[index];
    if (hardStale() || (index>0 && replaced())) return false;
    // Validate from the reported endpoint of the previous leg, not its target.
    if (safePoseError(actual) || pathHit(actual,leg.pose))
      throw new Error("the reported pose does not have a clear route to the next waypoint");
    const started = performance.now();
    const reply = await rawCmd("POSE " + leg.pose.map(fmtA).join(" ") + " T " + leg.t);
    liveRtt += ((performance.now()-started)-liveRtt)*0.25;
    if (!/^OK\b/.test(reply)) throw new Error(reply || "the robot refused the move");
    if (hardStale()) return false;
    // A newer drag finishes this checked leg, then replaces the remaining
    // route. Stop/Live-off/settings changes cancel immediately after an await.
    const arrived = await safeIdle(hardStale,leg.pose,progress);
    if (!arrived) return false;
    actual = arrived.module.joints.slice();
    if (entryHold) { pose=actual.slice();applyPose();renderSliders(); }
  }
  return !stale();
}
async function checkedPose(goal,ms,epoch,goalRevision,target) {
  return withSafeMotion(async () => {
    if(target!==safeTarget() || epoch!==safeMotionEpoch)return false;
    const device=safeDevice();
    try { return await checkedPoseUnlocked(goal,ms,epoch,goalRevision); }
    catch (e) {
      liveAbort();
      try { await safeDeviceCmd(device,"STOP"); } catch (_) {}
      safeMotionNote("Movement stopped: " + e.message,true);
      return false;
    }
  });
}
function safeTimelineSignature() { return keysSignature()+"|"+!!$("loopChk").checked+"|"+safeRevision(); }
function checkedTimeline() {
  return safeTimelineCache && safeTimelineCache.sig===safeTimelineSignature() ? safeTimelineCache.keys : null;
}
// A clock parked on the unchecked timeline (a keyframe click before Run) lands
// on a different move once times are raised or detours added: the same 80 ms
// park became "mid move 1" and Run replayed it. Re-find the same keyframe and
// the same share of its move or hold in the checked list.
function safeClockGroups(K) {
  const groups=[];let at=K.length ? K[0].hold || 0 : 0;
  for(let j=1;j<K.length;j++) {
    const id=K[j].loopReturn ? 'loop' : K[j].src;
    let g=groups[groups.length-1];
    if(!g || g.id!==id) {g={id,start:at,move:0,hold:0};groups.push(g);}
    g.move+=K[j].t || 0;g.hold+=K[j].hold || 0;at+=(K[j].t || 0)+(K[j].hold || 0);
  }
  return {first:K.length ? K[0].hold || 0 : 0,groups,total:at};
}
function safeRemapClock(ms, before, after) {
  const a=safeClockGroups(before), b=safeClockGroups(after);
  if(!(ms>0))return 0;
  if(ms<a.first)return a.first ? b.first*ms/a.first : 0;
  const g=a.groups.find(x=>ms<x.start+x.move+x.hold);
  const n=g && b.groups.find(x=>x.id===g.id);
  if(!n)return g ? Math.min(ms,b.total) : b.total;
  const offset=ms-g.start;
  if(offset<g.move)return n.start+(g.move ? n.move*offset/g.move : 0);
  return n.start+n.move+Math.min(n.hold,offset-g.move);
}
async function ensureSafeTimeline(cancelled = () => false) {
  const sig = safeTimelineSignature();
  if (checkedTimeline()) return true;
  const before = playKeys();
  const source = buildPlayKeys().map(k=>({...k,pose:k.pose.slice()}));
  if (!source.length) return false;
  const stale=()=>cancelled() || sig!==safeTimelineSignature();
  const error=safePoseError(source[0].pose);
  if (error) {safeMotionNote("Cannot play: starting pose "+error,true);return false;}
  const out=[source[0]], loop=!!$("loopChk").checked;
  const remaining=source.slice(1);
  if(loop && source.length>1) remaining.push({...source[0],hold:0,cues:[],cuesAfter:[],
    t:autoTime(source[source.length-1].pose,source[0].pose,speedDps()),loopReturn:true});
  let around=0;
  for(const key of remaining) {
    const plan=await planSafeAsync(out[out.length-1].pose,key.pose,SAFE.budgetMs,SAFE.seed,stale);
    if(stale())return false;
    if(plan.fail) {safeMotionNote("Cannot play: "+plan.fail+". Fix the highlighted pose or reduce the extra gap.",true);return false;}
    if(plan.how==='around')around++;
    out.push(...safeLegKeys(plan.path,key));
  }
  if(stale())return false;
  playT=safeRemapClock(playT,before,out);
  safeTimelineCache={sig,keys:out,loop};
  _pkCache=null;
  if(around) safeMotionNote("RRT*: "+around+" move(s) rerouted around the body. The preview and robot use these checked waypoints.",true);
  return true;
}
// Snapshot the validated show. Stop, target changes and edits during upload
// invalidate startup before any native MOVE can reach the board.
async function startCheckedSequence(fromMs, keepCopy = true) {
  const epoch=safeMotionEpoch, device=safeTarget(), revision=safeRevision();
  const sig=safeTimelineSignature();
  const stale=()=>safeStale(epoch,device,revision) || sig!==safeTimelineSignature();
  if(!(await ensureSafeTimeline(stale)) || stale())return null;
  const destination=poseAt(fromMs).slice();
  const {name,yaml}=buildYaml(fromMs);
  const part=fromMs>0 && keyIndexAtMs(fromMs)>0;
  const file=(part ? name+'.part' : name)+'.yaml';
  return withSafeMotion(async()=>{
    if(stale())return null;
    safeActiveDevice=safeDevice();
    // A partial file starts at its retained keyframe. Its original loop
    // closure belongs to the complete show, so a partial run plays once.
    const nativeYaml=part ? yaml.replace(/^loop:\s*true\s*$/m,'loop: false') : yaml;
    await sdUpload(file,nativeYaml);
    if(stale())return null;
    const kept=keepCopy ? await keepLastRun(nativeYaml,file) : '';
    if(stale())return null;
    const initial=await safeTakeover(stale);
    if(!initial || stale())return null;
    if(!(await checkedPoseUnlocked(destination,0,epoch,null,initial)) || stale())return null;
    const reply=await rawCmd('MOVE '+file);
    if(stale()) {await safeDeviceCmd(safeActiveDevice,'STOP');return null;}
    if(!/^OK\b/.test(reply))throw new Error(reply || 'the robot did not start the sequence');
    return {file,name,part,kept};
  });
}
// Direct Web Serial has no native hub clock. Advance one checked move at a
// time, including entry and holds, and draw the board's reported position.
async function directSafePlay(fromMs) {
  const epoch=safeMotionEpoch, device=safeTarget(), revision=safeRevision(),sig=safeTimelineSignature();
  const stale=()=>!playing || safeStale(epoch,device,revision) || sig!==safeTimelineSignature();
  const K=checkedTimeline().map(k=>({...k,pose:k.pose.slice()}));
  const phases=[];let at=0;
  const add=(key,ms,move)=>{if(ms>0)phases.push({key,start:at,end:at+ms,move});at+=ms;};
  add(K[0],K[0].hold || 0,false);
  K.slice(1).forEach(k=>{add(k,k.t,true);add(k,k.hold || 0,false);});
  const draw=(q,time)=>{
    pose=q.slice();playT=time;applyPose();renderSliders();
    $('scrub').value=at ? Math.round(time/at*1000) : 0;
    $('tlTime').textContent=(time/1000).toFixed(1)+'s / '+(at/1000).toFixed(1)+'s';
  };
  const hold=async(ms,update)=>{
    const start=performance.now();
    while(!stale() && performance.now()-start<ms) {
      if(update)update(performance.now()-start);
      await new Promise(r=>setTimeout(r,40));
    }
  };
  entryHold=true;
  return withSafeMotion(async()=>{try {
    let status=await safeTakeover(stale);
    if(!status || stale())return false;
    if(!(await checkedPoseUnlocked(poseAt(fromMs),0,epoch,null,status,s=>draw(s.module.joints,fromMs))) || stale())return false;
    let cursor=fromMs;
    do {
      for(const phase of phases) {
        if(phase.end<=cursor)continue;
        if(stale())return false;
        const start=Math.max(cursor,phase.start),duration=phase.end-start,clock=performance.now();
        if(phase.move) {
          status=await safeIdle(stale);
          if(!status || stale())return false;
          if(!(await checkedPoseUnlocked(phase.key.pose,duration,epoch,null,status,s=>
            draw(s.module.joints,Math.min(phase.end,start+performance.now()-clock)))) || stale())return false;
          await hold(Math.max(0,duration-(performance.now()-clock)));
        } else await hold(duration,elapsed=>draw(phase.key.pose,start+elapsed));
        if(stale())return false;
        draw(phase.key.pose,phase.end);cursor=phase.end;
      }
      cursor=0;
    }while($('loopChk').checked && !stale());
    return !stale();
  }catch(e){await cancelSafeMotion('direct playback failed');safeMotionNote('Playback stopped: '+e.message,true);return false;}
  finally {
    if(epoch===safeMotionEpoch) {playing=false;entryHold=false;$('playBtn').textContent='▶ Play';keepAwake(false);}
  }});
}
// --- sliders ---
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
  holdSide(arm, true);            // A45-28: the side kept on top, hand in place
  const got = fkPoints(pose)[wrKey];
  // the gap readout and the orange mark work in the 3D view's own space
  askReach(arm, wristPos(arm).add(t.clone().sub(got)));
  poseChanged(false);
  const err = Math.round(got.distanceTo(t));
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
    renderHands();
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
// Neutral is the SHOW's rest pose and stays in Studio; robot home is separate
// (user 2026-09-17: home = start position of the robot, neutral = the show's).
function neutralFromPose() {
  RIG.neutral = [...pose];
  saveRig();
  $("tlStat").textContent = "show neutral = " + RIG.neutral.map(Math.round).join(" ") +
    " — kept in Studio. The robot's start position is set with Keep this as robot home.";
}
async function homeFromPose() { // robot home: saved here AND on the robot
  RIG.home = [...pose];
  saveRig();
  renderRigUI();                      // the start° column shows the new numbers
  const shown = RIG.home.map(Math.round).join(" ");
  // Sent as ONE whole-pose line, not ten. Until 2026-09-10 this only ever saved
  // in the browser, so the editor and the robot disagreed about where home was
  // and nothing on the page said so.
  // Any link will do, exactly as "send rig" decides. liveLinked() was wrong
  // here: it also requires the live-follow tick, so with that off the button
  // saved in the browser and quietly sent the robot nothing.
  if (!haveRobot()) {
    $("robotStat").textContent = "robot home = " + shown +
      " — saved here. Connect the robot and press Send rig to give it these.";
    return;
  }
  try {
    const r = await rawCmd("NEUTRAL " + RIG.home.map(fmtA).join(" "));
    $("robotStat").textContent = /^ERR/i.test(r || "")
      ? "the robot did not take the home pose: " + r
      : "robot home = " + shown + " — the robot will start here from now on. "
        + "Press Home to move there.";
  } catch (e) {
    $("robotStat").textContent = "home saved here, but it did not reach the robot: "
      + (e.message || e);
  }
}
// The Pose tab's two mirror buttons. mirrorLR is kept as the name the page has
// always called, so nothing else has to change; mirrorFB is its front/back twin.
function mirrorFB() { mirrorLR("fb"); }
function mirrorLR(which) {
  // Swapping the two blocks of four joint numbers is what this did, and it was
  // not a mirror: the two arms do not carry the same `invert` flags, so the
  // hand came out 613 mm from where it belonged (measured 2026-09-23, A31-6).
  // mirrorPose() reflects the elbow and the hand in the body's own centre line
  // and solves the arms to reach them, and it is the ONE place that rule
  // lives - the timeline's ⇄ button calls the same function.
  const m = mirrorPose(pose, which);
  if (!m) {
    $("tlStat").textContent = "the robot is not on screen yet, so there is "
      + "nothing to mirror. Nothing was changed.";
    return;
  }
  pose = m;
  poseChanged(false);
  $("tlStat").textContent = which === "fb"
    ? "mirrored front to back — each arm reaches the other way, on its own side"
    : "mirrored left to right — each arm took the other's shape";
}

// ---- palm or back of the hand on top (A44-1) --------------------------------
// User 2026-10-19: hand-like parts are fixed to the arms, and which side the
// audience sees on top changes how a pose feels. One row per hand: what is on
// top now, and a button for each side. The hand stays where it is.
const FACING_TEXT = { palm: "palm on top", back: "back of the hand on top",
                      side: "on its edge" };
function renderHands() {
  const box = $("handsBox");
  if (!box || palmMarks.length < HANDS.length) return;
  if (!box.childElementCount) {
    HANDS.forEach((h, i) => {
      const row = document.createElement("div"); row.className = "row";
      const lbl = document.createElement("span"); lbl.className = "lbl";
      lbl.textContent = h.label;
      const up = document.createElement("button");
      up.textContent = "✋ Palm up";
      up.title = "turn the arm so the PALM of the " + h.label.toLowerCase()
               + " faces up; the hand stays where it is";
      up.onclick = () => turnPalm(i, 1);
      const back = document.createElement("button");
      back.textContent = "🤚 Back up";
      back.title = "turn the arm so the BACK of the " + h.label.toLowerCase()
                 + " faces up; the hand stays where it is";
      back.onclick = () => turnPalm(i, -1);
      const now = document.createElement("span");
      now.className = "mini"; now.id = "handNow" + i;
      row.append(lbl, up, back, now);
      // A45-28: keep a side on top while this hand is dragged or typed to
      const keep = document.createElement("div"); keep.className = "row";
      const kl = document.createElement("span"); kl.className = "mini";
      kl.textContent = "while moving it, keep:";
      const sel = document.createElement("select"); sel.id = "handHold" + i;
      [["0", "nothing — free"], ["1", "✋ palm on top"], ["-1", "🤚 back on top"]]
        .forEach(([v, t]) => sel.add(new Option(t, v)));
      sel.title = "dragging this hand or typing where its wrist goes keeps that side "
                + "on top as well as it can; the sliders always do exactly what you set";
      sel.onchange = () => setHold(i, +sel.value);
      keep.append(kl, sel);
      const reach = document.createElement("div");
      reach.className = "mini"; reach.id = "handReach" + i;
      box.append(row, keep, reach);
    });
    const save = document.createElement("div"); save.className = "row";
    const add = document.createElement("button");
    add.textContent = "＋ Save as a new move"; add.id = "handSaveNew";
    add.onclick = () => saveShownPose(true);
    const into = document.createElement("button");
    into.textContent = "Save into the selected move"; into.id = "handSaveInto";
    into.onclick = () => saveShownPose(false);
    save.append(add, into);
    box.appendChild(save);
  }
  HANDS.forEach((h, i) => {
    const el = $("handNow" + i);
    if (el) el.textContent = "now: " + FACING_TEXT[palmWord(palmUpness(i))] + " · " + sideText(i);
  });
  renderReach();
}
function turnPalm(arm, want) {
  const r = facePalm(pose, arm, want, { safe: HOLD.avoidSelfHit });
  if (!r) return;
  pose = r.pose;
  poseChanged(false);
  const h = HANDS[arm].label.toLowerCase();
  $("tlStat").textContent = want * r.upness > 0.5
    ? h + ": " + (want > 0 ? "the palm" : "the back of the hand") + " is on top now, "
      + "and the hand is where it was. Press Update selected to keep it in the move."
    : h + ": this is as far round as the joints let it turn with the hand here. "
      + "Move the hand a little and try again.";
  if (want * r.upness <= 0.5) notice($("tlStat").textContent);
}
// --- keep the palm or the back on top while a hand moves (A45-28) ---
// User 2026-10-22: picking palm up / back up after the fact hid what the arm
// can really do there, so the choice now holds WHILE you drag a hand or type
// where a wrist goes, and the Pose tab shows live what the arm reaches: the
// gap to where you pulled, how far the palm is from straight up, which joints
// sit at their stop, and whether it hits itself. What is shown is the joint
// angles the robot gets, so saving keeps exactly that. Settings are DATA in
// hand_side.json beside this page; the story is in qc/checks/check_palm_hold.py.
let HOLD = {
  dragRangeDeg: 30,   // while dragging: look this far round each way, no further
  stepDeg: 5,
  reachMm: 4,         // a gap this small counts as "the hand got there"
  stopDeg: 0.5,       // this close to a joint limit counts as "at its stop"
  avoidSelfHit: true, // never turn the arm into a shape that hits the body
};
fetch("hand_side.json").then(r => r.json()).then(j => {
  Object.keys(HOLD).forEach(k => { if (k in j) HOLD[k] = j[k]; });
}).catch(() => {});        // no file: the built-in values above

const handHold = HANDS.map(() => 0);     // per hand: 0 free, 1 palm on top, -1 back
const reachAsk = HANDS.map(() => null);  // per hand: { target (world), joints } last asked for
const reachMarks = [];                   // per hand: the asked-for point and a line to the hand

const armJoints = (arm) => arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
const armKey = (arm) => armJoints(arm).map(j => pose[j].toFixed(2)).join(",");

// Turn the arm to the held side, hand kept in place. full = the whole swing
// (a button, a typed position, the end of a drag); otherwise only near the
// shape it has, so a drag never flips the elbow to the far side mid-pull.
function holdSide(arm, full) {
  const want = handHold[arm];
  if (!want) return;
  const r = facePalm(pose, arm, want, full ? { safe: HOLD.avoidSelfHit }
    : { range: HOLD.dragRangeDeg, step: HOLD.stepDeg, safe: HOLD.avoidSelfHit });
  if (r) { pose = r.pose; applyPose(); }  // facePalm redraws the pose it was given
}
// Remember where this hand was asked to go (world space), for the gap readout
// and the 3D mark. It goes stale the moment that arm's joints change any other way.
function askReach(arm, target) {
  reachAsk[arm] = { target: target.clone(), joints: armKey(arm) };
  drawReach(arm);
}
function drawReach(arm) {
  if (!reachMarks[arm]) {
    const ball = new THREE.Mesh(new THREE.SphereGeometry(14, 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xff9f1c, transparent: true, opacity: 0.55 }));
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(
      [new THREE.Vector3(), new THREE.Vector3()]),
      new THREE.LineBasicMaterial({ color: 0xff9f1c }));
    scene.add(ball, line);
    reachMarks[arm] = { ball, line };
  }
  const m = reachMarks[arm], a = reachAsk[arm];
  const gap = reachGap(arm);
  m.ball.visible = m.line.visible = gap !== null && gap > HOLD.reachMm;
  if (!m.ball.visible) return;
  m.ball.position.copy(a.target);
  m.line.geometry.setFromPoints([a.target, wristPos(arm)]);
}
// mm between where the hand was asked to go and where it is; null = nothing asked
function reachGap(arm) {
  const a = reachAsk[arm];
  if (!a || !wristBalls[arm]) return null;
  if (a.joints !== armKey(arm)) { reachAsk[arm] = null; return null; }
  robot.updateMatrixWorld(true);
  return a.target.distanceTo(wristPos(arm));
}
// How far the side asked for (or the nearer one) is from straight up, in deg.
function sideText(arm) {
  const up = palmUpness(arm), want = handHold[arm] || (up >= 0 ? 1 : -1);
  const off = Math.round(THREE.MathUtils.radToDeg(Math.acos(Math.max(-1, Math.min(1, want * up)))));
  return (want > 0 ? "palm " : "back ") + off + "° from straight up";
}
// One plain line per hand under it: the gap, the joints at their stop, a
// self-hit. Built from the pose the robot gets.
function reachText(arm) {
  const out = [];
  const gap = reachGap(arm);
  if (gap !== null) out.push(gap <= HOLD.reachMm ? "reached where you put it"
    : Math.round(gap) + " mm short of where you put it (the orange mark)");
  if (handHold[arm] && handHold[arm] * palmUpness(arm) <= 0.5)
    out.push("the joints cannot turn it further with the hand here");
  const stops = armJoints(arm).filter(j => pose[j] <= RIG.min[j] + HOLD.stopDeg
                                         || pose[j] >= RIG.max[j] - HOLD.stopDeg);
  if (stops.length) out.push("at its stop: " + stops.map(j => JOINT_LABELS[j]).join(", "));
  const hit = collisionAt(pose);
  if (hit) out.push("⚠ " + hit);
  return out.join(" · ");
}
function renderReach() {
  HANDS.forEach((h, i) => {
    const el = $("handReach" + i);
    if (el) el.textContent = reachText(i);
    drawReach(i);
  });
}
function setHold(arm, want) {
  handHold[arm] = want;
  if (!want) return;
  holdSide(arm, true);
  poseChanged(false);
}
// Save the pose on screen: these are the joint angles the robot is sent, so the
// move plays exactly what you see, gap and all.
function saveShownPose(asNew) {
  if (asNew) addKey(); else if (keys[selKey]) updateKey(); else return;
  $("tlStat").textContent = (asNew ? "added as move " : "saved into move ") + selKey
    + " — exactly the pose shown, which is what the arm will do";
}
// --- timing ---
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
// The floor AND the reason for it. Typing a faster °/s did nothing and said
// nothing (user 2026-09-23: *when input the deg/s in sequence it not change
// the time for me anymore*) because the peak limit had already won: with the
// board's safe_dps at 60, pi/2 x delta / 60 floors every move at delta/38.2,
// so any speed above about 38 °/s produces the identical time. The number was
// never wrong; it was invisible. Every caller that shows a time to a person
// asks for the reason too.
function minTimeWhy(from, to) {
  // per joint (the slow WAIST servo counts too), the slowest joint wins
  let servo = 0, slowest = 0;
  for (let i = 0; i < NJ; i++) {
    const need = Math.abs(to[i] - from[i]) / jointMaxDps(i);
    if (need > servo) { servo = need; slowest = i; }
  }
  // safety floor, same as firmware nongmath::safeDuration (ease peaks at pi/2 x average)
  const peak = deltaDeg(from, to) * (Math.PI / 2) / Math.max(1, SAFE_DPS);
  const need = Math.max(servo, peak);
  const ms = Math.max(MIN_MOVE_MS, Math.ceil(need * 1000));
  let why = "the 80 ms shortest-move floor", fix = "";
  if (need * 1000 > MIN_MOVE_MS) {
    if (peak >= servo) {
      why = `the robot's peak speed limit, ${SAFE_DPS} °/s`;
      fix = `Above about ${flatDps()} °/s nothing gets faster. Raise ` +
            `Peak speed limit (Timing) to shorten it.`;
    } else {
      why = `${JOINT_LABELS[slowest] || ("joint " + (slowest + 1))} at its ` +
            `servo max, ${Math.round(jointMaxDps(slowest))} °/s`;
      fix = "Raise Servo max, or that joint's servo °/s in Setup > rig.";
    }
  }
  return { ms, why, fix };
}
function minTime(from, to) { return minTimeWhy(from, to).ms; }
// The show speed above which the peak limit decides every safety-limited move.
// pi/2 is the ease curve's peak-to-average ratio, the same one the firmware uses.
function flatDps() { return Math.floor(SAFE_DPS * 2 / Math.PI); }
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
// A speed the servos cannot hold used to be replaced in the box with no word
// said, so it read as *the number will not change*. Say what was kept and why.
// The fastest Show speed that DOES anything. Above the peak limit's flat point
// no move gets shorter, however large the number, so accepting a larger one is
// the box lying (user 2026-09-23: *the show speed can adjust in the save dps*).
// Raise the saved peak limit and this ceiling rises with it - measured on board
// 67: safe_dps 120 -> 76 °/s, safe_dps 190 -> 121 °/s.
function speedCeiling() { return Math.max(5, Math.min(slowestDps(), flatDps())); }
function speedChanged() {
  const asked = speedDps();
  let said = "";
  if (asked > speedCeiling()) {
    const cap = speedCeiling();
    $("speedDps").value = cap;
    said = flatDps() <= slowestDps()
      ? `Show speed kept at ${cap} °/s — above that, the robot's peak speed ` +
        `limit of ${SAFE_DPS} °/s decides every move and nothing gets faster. ` +
        "Raise Peak speed limit and Save to robot to go quicker."
      : `Show speed kept at ${cap} °/s — the slowest servo on this robot ` +
        "cannot go faster. Raise Servo max to allow more.";
  }
  recalcTimes();
  renderTimeline();
  $("tlStat").textContent = said || timingSummary();
}
// One sentence naming the limit that is actually deciding move times now, so
// the answer to *why did my number change nothing* is on the screen and not
// only in a tooltip.
function timingSummary() {
  let peak = 0, servo = 0, free = 0;
  for (let i = 1; i < keys.length; i++) {
    if (!keys[i - 1]) continue;
    const w = minTimeWhy(keys[i - 1].pose, keys[i].pose);
    const auto = Math.max(MIN_MOVE_MS,
      Math.round(deltaDeg(keys[i - 1].pose, keys[i].pose) / keyDps(i) * 1000));
    if (auto >= w.ms) free++;
    else if (w.why.indexOf("peak") >= 0) peak++;
    else servo++;
  }
  if (!peak && !servo) return `every move runs at the speed you set (${speedDps()} °/s)`;
  const bits = [];
  if (peak) bits.push(`${peak} held by the robot's peak speed limit (${SAFE_DPS} °/s — ` +
                      `above about ${flatDps()} °/s nothing gets faster)`);
  if (servo) bits.push(`${servo} held by a servo's own top speed`);
  return `${free} move(s) run at your speed; ` + bits.join(", ") +
         ". Change Peak speed limit or Servo max in Timing to shorten them.";
}
// The peak limit is the Studio's own planning number. It was locked until a
// board was connected, so away from the robot there was no way to make any
// move faster at all (user 2026-09-23: *max servo speed in show i cannot
// adjust anymore*). Editing it re-times the automatic moves here; SAVING it to
// the board is still a separate, connected-only step, because a Studio that
// plans faster than the robot allows would be lying about the show.
function safetyLimitChanged() {
  const want = Math.round(+$("safeDpsInput").value || 0);
  if (!(want >= 5)) { $("safeDpsInput").value = SAFE_DPS; return; }
  // A pinned time is never re-timed, even when it happens to equal the auto one.
  const wasAuto = keys.map((k, i) => i > 0 && keys[i - 1] && !timePinned(i) &&
    k.t === autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  SAFE_DPS = want;
  // Raising the limit raises what Show speed is allowed to be, so the two
  // boxes stay honest about each other. Capped BEFORE re-timing, or the moves
  // were timed at a speed the box no longer shows.
  if (speedDps() > speedCeiling()) $("speedDps").value = speedCeiling();
  for (let i = 1; i < keys.length; i++)
    if (wasAuto[i]) keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  bumpKeys();
  clampKeyTimes();
  renderTimeline();
  $("safeSpeedStat").textContent =
    `Planning at ${want} °/s, so Show speed can now go up to ${speedCeiling()} °/s. ` +
    (boardSafeDpsMax ? "Press Save to robot to make the robot use it too — it "
                       + "takes effect after the board restarts."
                     : "Not saved to any robot — connect first, then Save to robot.");
}
// INFO is the active board value. CFG only saves the NEXT boot's value, so do
// not change SAFE_DPS when the operator presses Save.
function adoptBoardSafety(module) {
  const safe = Number(module && module.safe_dps);
  const speeds = module && module.max_dps;
  const max = Array.isArray(speeds) && speeds.length === NJ
    ? Math.min(...speeds.map(Number)) : 0;
  const input = $("safeDpsInput"), button = $("saveSafeDps");
  if (!(safe >= 5) || !(max >= 5) || !Number.isFinite(max)) {
    boardSafeDpsMax = 0;
    boardSafePeer = 0;
    input.disabled = false;         // still the Studio's own planning number
    button.disabled = true;         // but there is nothing to save it to
    $("safeSpeedStat").textContent = "This board does not report its safety speed, so " +
      `nothing was changed on it. Studio still plans at ${SAFE_DPS} °/s — change it here ` +
      "to make the editor's times shorter.";
    return;
  }
  // Only automatically timed moves shorten. A hand-typed time is the user's
  // choice and must not be silently replaced after reconnecting to a board.
  const wasAuto = keys.map((k, i) => i > 0 && !timePinned(i) && k.t ===
    autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  const changed = safe !== SAFE_DPS;
  SAFE_DPS = safe;
  boardSafeDpsMax = max;
  boardSafePeer = module.link ? Number(module.peer) || 0 : 0;
  input.disabled = button.disabled = false;
  input.min = 5;
  input.max = Math.floor(max);
  input.value = String(safe);
  if (changed) {
    for (let i = 1; i < keys.length; i++)
      if (wasAuto[i]) keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
    clampKeyTimes();
    renderTimeline();
  }
  $("safeSpeedStat").textContent = `Active peak limit: ${safe} °/s. ` +
    `For safety-limited moves, Show speed above about ${flatDps()} °/s will not shorten ` +
    "them — raise this number and press Save to robot to go faster." +
    (boardSafePeer ? ` Linked board #${boardSafePeer} needs the same limit.` : "");
}
// A TIME TYPED BY HAND IS A DECISION, NOT A CACHE.
//
// User 2026-09-23: *when i already adjust to higer time and i change the move a
// little bit make the time it have the most not recreate the time of the rig
// because i need that move to that time when i change i change it everytime
// make me headace*. Nudging a pose ran the automatic timer over the top of the
// number they had set, so every small correction cost them the timing again.
//
// So a typed time is PINNED (`k.tset`). Nothing that re-times automatically may
// touch it, and nothing may make it shorter. Only clampKeyTimes may raise it,
// and only to the physical minimum - a move the servos cannot do in that time
// is not a choice anybody can make.
//
// Two ways out, both deliberate: type a °/s on that move, or press the pin on
// the time box. Both say "time this one for me again".
function timePinned(i) { return !!(keys[i] && keys[i].tset); }
function pinTime(i) { if (keys[i]) keys[i].tset = true; }
function unpinTime(i) { if (keys[i]) delete keys[i].tset; }
function recalcTimes() {   // keeps each keyframe's own speed override AND its pin
  bumpKeys();
  for (let i = 1; i < keys.length; i++)
    if (!timePinned(i))
      keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();         // a pinned time may still be raised to what is possible
}
// ONE keyframe's predecessor changed (delete / reorder): re-time only it.
// recalcTimes() would silently overwrite every hand-typed time on the line,
// and a typed time wins over the automatic one by design.
function retimeAt(i) {
  bumpKeys();
  if (i >= 1 && keys[i] && !timePinned(i))
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();
}
function clampKeyTimes() { // raise any hand-edited time that fell below the floor
  bumpKeys();
  for (let i = 0; i < keys.length; i++) keys[i].t = Math.max(keys[i].t, keyMin(i));
}
// --- timeline ---
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
  // A pinned time survives the edit. This line is where the headache was: a
  // small correction to a pose re-ran the automatic timer over a number the
  // operator had chosen, every single time (A31-12).
  if (selKey >= 1 && !timePinned(selKey))
    keys[selKey].t = autoTime(keys[selKey - 1].pose, keys[selKey].pose, keyDps(selKey));
  if (keys[selKey + 1] && !timePinned(selKey + 1))
    keys[selKey + 1].t = autoTime(keys[selKey].pose, keys[selKey + 1].pose, keyDps(selKey + 1));
  clampKeyTimes();          // only the physical minimum may raise a pinned time
  renderTimeline();
}
function dupKey() {
  if (!keys[selKey]) return;
  clearBadMarks();
  const copy = JSON.parse(JSON.stringify(keys[selKey]));
  // The copy is a pose, not a second music cue: keeping the cues restarted
  // the source's track (or stopped it) a second time at the copy.
  delete copy.cues; delete copy.cuesAfter;
  keys.splice(selKey + 1, 0, copy);
  bumpKeys();
  selKey++;
  // The copy keeps its source's time, which makes it a HOLD of that length:
  // the move into the copy covers zero distance (same pose as the keyframe
  // before it). No predecessor pose changed anywhere else on the line, so no
  // other time moves — recalcTimes() here used to wipe every hand-typed one.
  clampKeyTimes(); renderTimeline();
}
function delKey() {
  if (keys.length <= 1 || !keys[selKey]) return;
  clearBadMarks();
  const gone = selKey;
  keys.splice(selKey, 1);
  bumpKeys();
  selKey = Math.max(0, selKey - 1);
  // Only the keyframe that FOLLOWED the deleted one starts from a different
  // pose now; every hand-typed time further down must survive.
  retimeAt(gone); renderTimeline(); selectKey(selKey);
}
function moveKey(d) {
  const i = selKey, j = i + d;
  if (!keys[i] || !keys[j]) return;
  clearBadMarks();
  [keys[i], keys[j]] = [keys[j], keys[i]];
  bumpKeys();
  selKey = j;
  // Both swapped keyframes changed what they travel FROM, and so did the
  // keyframe AFTER them (it now follows the other of the pair).
  const last = Math.max(i, j);
  retimeAt(i); retimeAt(j);
  if (keys[last + 1]) retimeAt(last + 1);
  renderTimeline();
}
// How long the move INTO keyframe i takes, as the show would run it. Reads
// the played timeline, so a keyframe that follows a suspended one gets the
// re-timed value rather than the number stored against it.
function keyTravelMs(i) {
  const K = playKeys();
  const at = K.findIndex(k => k.src === i && !k.loopReturn);
  if (at > 0) {
    let travel=0;
    for(let n=at;n<K.length && K[n].src===i && !K[n].loopReturn;n++)
      travel+=K[n].t+(K[n].via ? K[n].hold || 0 : 0);
    return travel;                           // all checked detour legs into this destination
  }
  if (at === 0) return 0;                     // the start pose: nowhere to come from
  return keys[i] ? keys[i].t : 0;             // suspended: fall back to its own
}
// Where the show's clock sits when the move INTO keyframe i begins — the same
// walk totalMs() makes over the PLAYED list, holds counted. Selecting a
// keyframe parks the clock here, so Play carries on from the move on screen.
// A suspended keyframe has no move of its own: the show jumps the gap, so the
// clock lands where that jump begins (end of the show if none follows).
function keyStartMs(i) {
  const K = playKeys();
  let at = K.findIndex(k => k.src === i && !k.loopReturn);
  if (at < 0) {
    at = K.findIndex(k => k.src > i);
    if (at < 0) return totalMs();
  }
  if (at <= 0) return 0;
  let t = K[0].hold || 0;
  for (let j = 1; j < at; j++) t += K[j].t + (K[j].hold || 0);
  return t;
}

// Which PLAYED keyframe the clock at `ms` is standing on — keyStartMs() run
// backwards, and the same walk main.py's _play_once makes when the hub resumes
// a show. Inside a move: that move is the one to run. Inside a hold: the next
// one. The answer is an index into playKeys(), never into keys[].
function keyIndexAtMs(ms) {
  const K = playKeys();
  if (K.length < 2) return 0;
  let clock = K[0].hold || 0;
  if (ms <= clock) return 0;
  for (let i = 1; i < K.length; i++) {
    clock += K[i].t;
    if (ms < clock) return i;                       // part-way through its move
    clock += K[i].hold || 0;
    if (ms < clock) return Math.min(i + 1, K.length - 1);   // in its hold
  }
  return K.length - 1;
}

// CLICKING A MOVE WHILE IT PLAYS (user 2026-09-16): the clock was parked at
// the START of that move and play kept running, so the show went back to the
// pose before it and replayed the move - a sudden servo swing that can break
// the robot. Now: stop every clock, travel from where the arm IS to the
// clicked pose at the show's speed, park the clock where that pose is
// reached, and carry on from there once the arm has arrived.
let seekToken = 0;
function selectKey(i) {
  const was = playing;
  let token = ++seekToken;
  if (was) {
    playing = false; $("playBtn").textContent = "▶ Play";
    livePause(); stopRobotSequence(); keepAwake(false);
  }
  token=seekToken;
  selKey = i;
  let travel = 0;
  if (keys[i]) {
    const from = pose.slice();
    pose = [...keys[i].pose];
    // the move's own speed, and never faster than the show's speed allows
    // from where the arm stands now - the start pose has no move of its own
    travel = Math.max(keyTravelMs(i), autoTime(from, pose, keyDps(i)));
    poseChanged(false, travel);
  }
  // the clock follows the click: stopped, Play replays this move; playing,
  // the show continues AFTER it, since the arm is travelling there already
  playT = was ? keyStartMs(i) + keyTravelMs(i) : keyStartMs(i);
  if (was) {
    const epoch=safeMotionEpoch;
    const arrived=liveLinked() ? lastSafeMove : new Promise(r=>setTimeout(()=>r(true),travel));
    arrived.then(ok=>{if(ok && token===seekToken && epoch===safeMotionEpoch && !playing)togglePlay();});
  }
  const total = totalMs();
  $("scrub").value = total ? Math.round(playT / total * 1000) : 0;
  renderTimeline();
}
function totalMs() {
  const K = playKeys();
  let t = 0;
  for (let i = 1; i < K.length; i++) t += K[i].t + (K[i].hold || 0);
  t += K.length ? (K[0].hold || 0) : 0;
  return t + loopReturnMs();
}
// LOOP WRAP (user 2026-09-17): the arm has to travel from the last pose back to
// the first, which takes real time under the safety cap. The preview used to
// jump there at once and ran ahead of the robot. With loop on, that travel is a
// segment of its own: index K.length, pose K[0]. Never written to the file.
function loopReturnMs() {
  if (checkedTimeline() && safeTimelineCache.loop) return 0; // already a checked leg
  const K = playKeys();
  if (!$("loopChk") || !$("loopChk").checked || K.length < 2) return 0;
  return autoTime(K[K.length - 1].pose, K[0].pose, speedDps());
}
function renderTimeline() {
  const box = $("keys");
  $("timelineEmpty").hidden = keys.length > 0;
  box.innerHTML = "";
  keys.forEach((k, i) => {
    const el = document.createElement("div");
    // seqStart: the first keyframe of one sequence inside a whole show on the
    // bar. Without a line there, a 60-keyframe show is one undifferentiated
    // wall and there is no way to see where "wave" ends and "bow" begins.
    el.className = "key" + (i === selKey ? " sel" : "") + (k.off ? " off" : "")
                 + (k.seqStart && i > 0 ? " seqstart" : "");
    el.onclick = (e) => {
      // Not from a control: selecting re-renders the chip, which closed the music
      // list the moment it opened (A26-49, a SELECT was not in the old list).
      if (!e.target.closest("input,button,select,label,textarea")) selectKey(i);
    };
    // Clicking anywhere on the chip selects it, which is worth keeping for a
    // mouse - so the chip names the control that does the same job for the
    // keyboard. check_keyboard_only reads this: a clickable box that cannot
    // point at its own keyboard equivalent is counted as mouse-only.
    el.setAttribute("data-keyboard", ".kgo");
    const bar = document.createElement("div"); bar.className = "kbar";
    const idx = document.createElement("div"); idx.className = "kidx";
    // Number, then a name you can type. A timeline of "0 1 2 3 4 5" tells you
    // nothing about what the show does; "wave", "reach cup", "bow" does. The
    // number stays because it is what every message and error refers to.
    //
    // The number is a real BUTTON, not text: selecting a keyframe used to be
    // possible only by clicking the chip, so with a keyboard alone the
    // timeline could not be moved through at all (A9-3b, measured 2026-08-21).
    // Gemini Pro chose this over making the chip itself tabbable, because the
    // chip contains a text field and two number fields - a control that
    // contains controls is wrong for a screen reader and takes the focus its
    // own fields need.
    const go = document.createElement("button");
    go.className = "kgo";
    go.textContent = String(i);
    go.title = "go to move " + i + " and show that pose";
    go.setAttribute("aria-label", "go to move " + i + (k.name ? ": " + k.name : ""));
    go.setAttribute("aria-pressed", i === selKey ? "true" : "false");
    go.onclick = (e) => { e.stopPropagation(); selectKey(i); };
    idx.appendChild(go);
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
    // PALM OR BACK ON TOP, per hand (A44-1, user 2026-10-19). Read from the
    // move's own pose, never stored beside it, so it cannot go stale when the
    // pose is edited. Choosing turns that arm round with the hand kept in place.
    HANDS.forEach((h, arm) => {
      const now = palmWord(palmUpnessOf(k.pose, arm));
      const sel = document.createElement("select");
      sel.className = "kpalm";
      [["palm", h.side + " ✋ palm up"], ["back", h.side + " 🤚 back up"],
       ["side", h.side + " on edge"]].forEach(([v, label]) => {
        const o = document.createElement("option"); o.value = v; o.textContent = label;
        o.disabled = v === "side";       // a result, not something to ask for
        sel.appendChild(o);
      });
      sel.value = now;
      sel.title = "which side of the " + h.label.toLowerCase() + " the audience "
                + "sees on top in this move. Pick the other and the arm turns "
                + "round; the hand stays where it is.";
      sel.onclick = (e) => e.stopPropagation();
      sel.onchange = () => turnKeyPalm(i, arm, sel.value === "palm" ? 1 : -1);
      idx.appendChild(sel);
    });
    if (i > 0) {
      // Mirror: the same gesture on the other arm. The rule lives in
      // mirrorPose() (ik_4_dof_arm.js) and the Pose tab's Mirror button calls
      // the same function, so the two can never drift apart.
      // TWO mirrors, because a puppet has two (user 2026-09-23). Left/right
      // swaps the arms; front/back turns each arm's reach round and leaves it
      // on its own side. Separate buttons, not a mode: a mode you have to
      // remember is a button you press wrongly.
      [["⇄", "lr", "mirror LEFT and RIGHT: the same shape on the other arm"],
       ["⇅", "fb", "mirror FRONT and BACK: each arm reaches the other way and "
                   + "stays on its own side"]].forEach(([glyph, which, tip]) => {
        const mir = document.createElement("button");
        mir.className = "kmir";
        mir.textContent = glyph;
        mir.title = tip;
        mir.onclick = (e) => {
          e.stopPropagation();
          mirrorKeyArms(i, which);
        };
        idx.appendChild(mir);
      });
    }
    const pv = document.createElement("div"); pv.className = "kpose";
    pv.textContent = k.pose.map(a => Math.round(a)).join(" ");
    // The floor AND its reason, so a °/s that shortens nothing can say which
    // limit is holding the move (user 2026-09-23). i === 0 has no predecessor.
    const lim = i > 0 && keys[i - 1] ? minTimeWhy(keys[i - 1].pose, k.pose) : null;
    const kmin = lim ? lim.ms : MIN_MOVE_MS;
    const tr = document.createElement("div"); tr.className = "ktime";
    const tIn = document.createElement("input");
    tIn.type = "number"; tIn.value = k.t; tIn.min = kmin; tIn.step = 50;
    tIn.title = (i === 0 ? "entry time from wherever the robot is (ms)"
                         : "time from previous keyframe (ms)")
              + ` — minimum ${kmin} ms, set by ${lim ? lim.why : "the 80 ms floor"}`
              + "; longer is always allowed. Typing one PINS it: editing the pose "
              + "afterwards will not re-time this move.";
    if (k.tset) tIn.classList.add("pinned");
    tIn.onchange = () => {
      const want = Math.round(+tIn.value || 0);
      k.t = Math.max(kmin, want);
      delete k.dps;
      pinTime(i);             // typed BY HAND: nothing automatic may replace it
      bumpKeys();             // a typed time wins over a speed override
      if (want < kmin)
        $("tlStat").textContent = `time raised to ${kmin} ms — held by ${lim ? lim.why : "the 80 ms floor"}. ` +
          (lim && lim.fix ? lim.fix : "");
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
    tr.append(document.createTextNode("T"), tIn);
    // The pin is a BUTTON, not a state you can only read: a time that is held
    // and no way to let go of it is the same trap the other way round.
    if (i > 0) {
      const pin = document.createElement("button");
      pin.className = "kpin" + (k.tset ? " on" : "");
      pin.textContent = k.tset ? "📌" : "🕘";
      pin.setAttribute("aria-pressed", k.tset ? "true" : "false");
      pin.title = k.tset
        ? "this time is yours and is kept when you edit the pose. Click to let "
          + "Studio time this move again."
        : "Studio times this move from the pose and the speed. Click to keep the "
          + "time it has now, whatever you change afterwards.";
      pin.onclick = (e) => {
        e.stopPropagation();
        if (k.tset) {
          unpinTime(i);
          retimeAt(i);
          $("tlStat").textContent = `move ${i} is timed by Studio again: ${keys[i].t} ms.`;
        } else {
          pinTime(i);
          $("tlStat").textContent = `move ${i} is held at ${k.t} ms — editing the `
            + "pose will not change it. Only the servos' own minimum can raise it.";
        }
        bumpKeys();
        renderTimeline();
      };
      tr.appendChild(pin);
    }
    tr.append(document.createTextNode("hold"), hIn);
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
                  Math.round(speedDps()) + " °/s. Setting it re-times this move " +
                  "and hands the timing back to Studio; typing a time above pins " +
                  "it again. This move cannot go under " +
                  kmin + " ms: " + (lim ? lim.why : "the 80 ms floor") + ".";
      dIn.onchange = () => {
        const v = Math.round(+dIn.value || 0);
        const use = v >= 5 ? Math.min(v, slowestDps()) : speedDps();
        if (v >= 5) k.dps = use; else delete k.dps;
        // Asking for a SPEED is asking to be timed. It is the other way out of
        // a pinned time, and the symmetric opposite of typing a time.
        unpinTime(i);
        const free = Math.max(MIN_MOVE_MS,
          Math.round(deltaDeg(keys[i - 1].pose, k.pose) / use * 1000));
        k.t = autoTime(keys[i - 1].pose, k.pose, use);
        bumpKeys();
        renderTimeline();
        // Typing 200 where 38 is the ceiling used to change the box and nothing
        // else. Name the limit instead of leaving the number looking ignored.
        $("tlStat").textContent = (v >= 5 && v > use)
          ? `${v} °/s kept at ${use} °/s — no servo on this robot goes faster.`
          : (free < k.t
              ? `move ${i} stays ${k.t} ms — held by ${lim ? lim.why : "the 80 ms floor"}. ` +
                (lim && lim.fix ? lim.fix : "")
              : `move ${i} now takes ${k.t} ms at ${Math.round(use)} °/s.`);
      };
      // A move whose time no speed can shorten says so on its own line, where
      // the number is being typed — not only in a tooltip nobody hovers.
      const held = lim && Math.max(MIN_MOVE_MS,
        Math.round(deltaDeg(keys[i - 1].pose, k.pose) / keyDps(i) * 1000)) < lim.ms;
      const minTxt = document.createElement("span");
      minTxt.textContent = "min " + kmin + " · ";
      if (held) {
        minTxt.className = "statline";
        minTxt.textContent = "min " + kmin + " ⚑ · ";
        minTxt.title = "this move is already as short as it is allowed to be: " +
                       lim.why + ". " + lim.fix;
      }
      mn.append(minTxt, dIn, document.createTextNode("°/s"));
    }
    // ♪ lives on the existing speed line rather than in a row of its own:
    // most moves never carry music, and a row per keyframe for a rare thing
    // is how a timeline stops fitting on a laptop.
    const mus = document.createElement("button");
    mus.type = "button";
    mus.className = "kmus" + (keyCue(k, "play") ? " on" : "");
    mus.textContent = "♪";
    mus.setAttribute("aria-pressed", musOpen.has(i) ? "true" : "false");
    mus.title = keyCue(k, "play")
      ? "plays " + cueTrack(k) + (cueLoop(k) ? " on repeat" : "") + " from here"
      : "give this move a track from the robot's card";
    mus.onclick = () => {
      if (musOpen.has(i)) musOpen.delete(i); else musOpen.add(i);
      loadMusicList();
      renderTimeline();
    };
    mn.appendChild(mus);
    el.append(bar, idx, pv, tr, mn);
    if (musOpen.has(i) || keyCue(k, "play")) el.append(musicRow(k, i));
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
  renderTimeBar();
}

// The blocks and ruler under the time bar: a picture of the show, drawn from the
// SAME numbers playback uses (keyStartMs / keyTravelMs / totalMs), so the bar
// cannot disagree with what the robot does.
//
// Called from renderTimeline() only — never per frame. renderTimeline() rebuilds
// every chip with innerHTML="", so driving a playhead through it would do that
// sixty times a second; the playhead is the range's own thumb and moves by
// value alone (see playTick).
let tlZoom = 1;
function zoomTimeline(factor) {
  tlZoom = Math.max(0.5, Math.min(10, tlZoom * factor));
  const tr = $("tbTrack");
  const ru = $("tbRuler");
  if (tr) tr.style.width = (tlZoom * 100) + "%";
  if (ru) ru.style.width = (tlZoom * 100) + "%";
  renderTimeBar();
}

function renderTimeBar() {
  const box = $("tbBlocks"), ruler = $("tbRuler");
  if (!box) return;                      // an older page without the bar
  box.innerHTML = "";
  const K = playKeys(), total = totalMs();
  if (!total || K.length < 2) {
    const empty = document.createElement("div");
    empty.className = "tb-blk note";
    empty.style.left = "0"; empty.style.width = "100%";
    empty.textContent = K.length < 2 ? "add a second pose to make a movement"
                                     : "these poses are all the same";
    box.appendChild(empty);
    if (ruler) ruler.innerHTML = "";
    return;
  }
  const pct = ms => (ms / total * 100) + "%";
  // keyframe 0 has no move to arrive by, so only its hold occupies the start —
  // the same reason totalMs() counts K[0].hold but not K[0].t.
  const band = (left, width, cls, label, title) => {
    if (width <= 0) return;
    const d = document.createElement("div");
    d.className = "tb-blk" + (cls ? " " + cls : "");
    d.style.left = pct(left); d.style.width = pct(width);
    if (label && width / total > 0.06) d.textContent = label;
    d.title = title;
    box.appendChild(d);
  };
  if (K[0].hold) band(0, K[0].hold, "hold", "wait",
                      "waits " + (K[0].hold / 1000).toFixed(1) + "s before starting");
  for (let i = 1; i < K.length; i++) {
    const src = K[i].src, k = keys[src] || K[i];
    const start = keyStartMs(src), dur = keyTravelMs(src);
    const name = k.name || String(src);
    band(start, dur, (src === selKey ? "sel" : "") + (k.bad ? " bad" : ""), name,
         "move " + src + (k.name ? " (" + k.name + ")" : "") +
         " takes " + (dur / 1000).toFixed(1) + "s");
    if (K[i].hold) band(start + dur, K[i].hold, "hold", "wait",
                        "then waits " + (K[i].hold / 1000).toFixed(1) + "s");
  }
  if (!ruler) return;
  // Ticks in real seconds. The count comes from the bar's own width so a phone
  // gets two labels and a desktop gets eight, instead of a crowded smear.
  ruler.innerHTML = "";
  const w = ruler.getBoundingClientRect().width || 600;
  const steps = Math.max(2, Math.min(8, Math.floor(w / 90)));
  for (let s = 0; s <= steps; s++) {
    const t = total * s / steps;
    const tick = document.createElement("span");
    tick.className = "tb-tick" + (s === 0 ? " first" : s === steps ? " last" : "");
    tick.style.left = pct(t);
    tick.textContent = (t / 1000).toFixed(t < 10000 ? 1 : 0) + "s";
    ruler.appendChild(tick);
  }
}

// Back to start. Goes through scrubTo() rather than setting playT, because
// scrubTo is where the ONE-PLAYER discipline lives: it pauses the preview, ends
// the module's own sequence and lets the tab idle. Setting playT directly would
// leave the robot running its copy of the show from the old position.
function rewind() {
  scrubTo(0);
  $("scrub").value = 0;
  _lastScrub = 0;
  $("tlStat").textContent = "back at the start — press Play to run the whole show";
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
    s += ";" + (k.name || "") + "," + (k.tset ? 1 : 0) + "," +
         (k.off ? 1 : 0) + "," + k.t + "," + (k.hold || 0) + "," +
         (k.dps || 0) + "," + k.pose + "," + (k.cues || []).join("|") + "," +
         (k.cuesAfter || []).join("|");
  }
  return s;
}
function bumpKeys() {
  // the timeline changed: a "yes, run it anyway" given for the old one does
  // not carry over to this
  crashForced = false;
  if(playing && safeTimelineCache)cancelSafeMotion('timeline edited');
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
      // nothing to keep: too short, or identical to what is already on disk
      if (keys.length <= 1 || !isDirty()) { localStorage.removeItem(DRAFT_KEY); return; }
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        at: Date.now(),
        name: ($("projName") && $("projName").value) || "",
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
      // an older draft kept the name twice (name + seq): either one will do
      if ((d.name || d.seq) && $("projName")) $("projName").value = d.name || d.seq;
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
// Settings ▸ Saving can turn this off too; the draft still survives the close.
window.addEventListener("beforeunload", (e) => {
  if (!askUnsavedOn() || !isDirty()) return;
  e.preventDefault();
  e.returnValue = "";
});
function playKeys() {
  const checked = checkedTimeline();
  if (checked) return checked;
  const sig = keysSignature();
  if (_pkCache && _pkCache.sig === sig) return _pkCache.list;
  const list = buildPlayKeys();
  _pkCache = { sig, list };
  return list;
}
function buildPlayKeys() {
  const out = [];
  let gap = false;                 // was anything suspended since the last one?
  // Cues from suspended keyframes move to the next one that plays: suspending
  // a move must not silently delete the show's music from the exported file.
  let carry = [];
  keys.forEach((k, i) => {
    if (k.off) {
      gap = true;
      carry = carry.concat(k.cues || [], k.cuesAfter || []);
      return;
    }
    const prev = out.length ? out[out.length - 1] : null;
    const posed = k.pose;
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
      t = autoTime(prev.pose, posed, k.dps || speedDps());
    }
    // The name travels with the PLAYED move. buildYaml() writes from this
    // list, so a name left behind here never reaches the exported file.
    out.push({ pose: posed, hold: k.hold || 0, src: i, dps: k.dps || 0, t,
               name: k.name || "",
               // cues travel with the PLAYED move, like the name above: both
               // buildYaml and hubShowSteps read this list, so a cue left
               // behind here reaches neither the file nor the robot
               cues: carry.concat(k.cues || []),
               cuesAfter: (k.cuesAfter || []).slice() });
    carry = [];
    gap = false;
  });
  if (carry.length && out.length)
    out[out.length - 1].cuesAfter = out[out.length - 1].cuesAfter.concat(carry);
  return out;
}
function anySuspended() { return keys.some(k => k.off); }
// The same gesture, arms swapped (A31-6). The rule lives in mirrorPose()
// (rig_data.js) because it is made of rig numbers - each joint's zero, its
// direction and its axis - and this file should not hold a second opinion
// about them.
function mirrorKeyArms(i, which) {
  const k = keys[i];
  if (!k) return;
  const m = mirrorPose(k.pose, which);
  if (!m) {
    $("tlStat").textContent = "this rig's two arms are not set up as mirror "
      + "images (their rotation axes differ in Setup > rig), so there is no "
      + "mirror to take. Nothing was changed.";
    notice($("tlStat").textContent);
    return;
  }
  k.pose = m;
  bumpKeys();
  clearBadMarks();
  if (i === selKey) { pose = [...k.pose]; poseChanged(false); renderSliders(); }
  renderTimeline();
  $("tlStat").textContent = which === "fb"
    ? "move " + i + " mirrored front to back — each arm reaches the other way, "
      + "and stays on its own side"
    : "move " + i + " mirrored left to right — the same shape on the other arm";
}
// The timeline's palm picker (A44-1): the same facePalm() the Pose tab uses,
// on this move's pose. Timing is left alone, like a mirror: the hand does not
// move, so the move covers about the same ground.
function turnKeyPalm(i, arm, want) {
  const k = keys[i];
  if (!k) return;
  const r = facePalm(k.pose, arm, want);
  if (!r) return;
  k.pose = r.pose;
  bumpKeys();
  clearBadMarks();
  if (i === selKey) { pose = [...k.pose]; poseChanged(false); renderSliders(); }
  renderTimeline();
  const h = HANDS[arm].label.toLowerCase();
  $("tlStat").textContent = want * r.upness > 0.5
    ? "move " + i + ": " + h + " shows its " + (want > 0 ? "palm" : "back") + " on top now"
    : "move " + i + ": the joints cannot turn the " + h + " that far with the hand "
      + "where it is; this is the closest. Move the hand a little and try again.";
  if (want * r.upness <= 0.5) notice($("tlStat").textContent);
}

// ------- playback preview (cosine ease per segment — same as the firmware)
// The pose `ms` into the moves K: { pose }, or past the last one { pose, end }
// with end = when it ended. Shared with the video page (A44-8), which plays
// its made moves beside the video without putting them on the time bar.
function easeKeys(K, ms) {
  let t = K[0].hold || 0;
  if (ms <= t) return { pose: [...K[0].pose] };
  for (let i = 1; i < K.length; i++) {
    const seg = K[i].t;
    if (ms < t + seg) {
      const f = 0.5 - 0.5 * Math.cos(Math.PI * (ms - t) / seg);
      return { pose: K[i - 1].pose.map((a, j) => a + (K[i].pose[j] - a) * f) };
    }
    t += seg + (K[i].hold || 0);
    if (ms < t) return { pose: [...K[i].pose] };
  }
  return { pose: [...K[K.length - 1].pose], end: t };
}
function poseAt(ms) {
  const K = playKeys();
  if (!K.length) return pose;
  const e = easeKeys(K, ms);
  if (e.end == null) return e.pose;
  const t = e.end, ret = loopReturnMs(), last = K[K.length - 1].pose;
  if (ret && ms < t + ret) {
    const f = 0.5 - 0.5 * Math.cos(Math.PI * (ms - t) / ret);
    return last.map((a, j) => a + (K[0].pose[j] - a) * f);
  }
  return [...(ret ? K[0].pose : last)];
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
  if (K.length && ms < t + loopReturnMs()) return K.length;   // loop: back to the start
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

async function togglePlay() {
  if (timelinePreparing) { timelinePreparing=false;cancelSafeMotion("planning cancelled");return; }
  if (!playing) {
    const epoch=safeMotionEpoch;
    timelinePreparing=true;$("playBtn").textContent="⏹ Stop planning";
    let ready=false;
    try { ready=await ensureSafeTimeline(()=>epoch!==safeMotionEpoch); }
    finally { timelinePreparing=false;$("playBtn").textContent="▶ Play"; }
    if(epoch!==safeMotionEpoch)return;
    previewOnly=!ready;
  }
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
    previewOnly = !checkedTimeline();
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
  entryHold = false;
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
  if (hubDriven()) {
    // From the start the hub first TRAVELS to keyframe 0 (as long as the board
    // needs); the show clock starts after. Hold the preview until then, or it
    // runs ahead of the arm by the whole entry move (A26-50).
    entryHold = true;
    hubPlay(playT).then(ok => {if(ok)return waitEntry();entryHold=false;playing=false;$("playBtn").textContent="▶ Play";keepAwake(false);});
    return;
  }
  // A segment is the move INTO a keyframe, so segmentAt() starts at 1 and
  // keyframe 0 is never one of them. Put the robot on it first, or its first
  // move starts from wherever it happens to be standing instead of from the
  // start of the timeline. T is only a request: the firmware floors it per
  // joint, so a short one is stretched to what the servos can really do.
  if (liveLinked()) directSafePlay(playT);
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
  return $("liveChk").checked && haveRobot();
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
  const steps = K.map((k, i) => ({
    pose: k.pose.map(v => +fmtA(v)),
    t: i === 0 ? minTime(pose, K[0].pose) : k.t,
    hold: k.hold || 0,
    // the hub decides which cue is a command it may send (main.py cue_lines),
    // so the editor passes the file's own words straight through
    cues: k.cues || [],
    cues_after: k.cuesAfter || [],
  }));
  // loop: the travel back to the start is a step of its own, timed like the preview
  const ret = loopReturnMs();
  if (ret) steps.push({ pose: steps[0].pose.slice(), t: ret, hold: 0, cues: [], cues_after: [] });
  return steps;
}
async function hubPlay(fromMs) {
  const epoch=safeMotionEpoch, device=safeTarget(), revision=safeRevision();
  const goalRevision=safeGoalRevision;
  const sig=safeTimelineSignature();
  const stale=()=>safeStale(epoch,device,revision) || goalRevision!==safeGoalRevision || sig!==safeTimelineSignature();
  return withSafeMotion(async()=>{ try {
    if(stale() || !(await ensureSafeTimeline(stale)))return false;
    const steps=hubShowSteps();
    const destination=poseAt(fromMs || 0).slice();
    const loop=$("loopChk").checked, name=($("projName").value || "sequence").trim();
    const musicStop=showBarMusicStop();
    const initial=await safeTakeover(stale);
    if(!initial || stale())return false;
    if(!(await checkedPoseUnlocked(destination,0,epoch,goalRevision,initial)) || stale())return false;
    if (!steps || stale()) return false;
    if(!(fromMs>0))steps[0].t=MIN_MOVE_MS; // checked entry has already reached keyframe 0
    const r = await fetch("/api/play", {
      method: "POST",
      body: JSON.stringify({
        dev: moduleDev(), steps, loop,
        name, from_ms: Math.round(fromMs || 0),
        watch: !document.hidden,        // stop the arm if this page freezes (A26-46)
        music_stop_ms: musicStop,   // a show's track may outlive its moves
      }),
    }).then(r => r.json());
    if(stale()) {await hubStop();return false;}
    if (r.error) throw new Error(r.error);
    $("robotStat").textContent =
      "the HUB is playing this — it keeps going with this page closed or hidden. " +
      "Pause or Stop here ends it.";
    return true;
  } catch (e) {
    $("robotStat").textContent = "The hub could not start the show, so the robot "
      + "did not move. Check the hub is still running, then press Play again. "
      + (e.message || e);
    notice($("robotStat").textContent);
    playing=false;$("playBtn").textContent="▶ Play";keepAwake(false);
    return false;
  }});
}
let entryHold = false;       // true while the hub travels to keyframe 0
async function waitEntry() {
  while (entryHold && playing) {
    try {
      const st = await fetch("/api/play").then(r => r.json());
      if (!st.running || !st.entering) break;
    } catch (e) { break; }             // no answer: let the preview run
    await new Promise(r => setTimeout(r, 120));
  }
  entryHold = false;
  lastPlayMs = 0;                      // start the clock now, not at Play
}
// Heartbeat for a hub-played show: a FROZEN page cannot beat, so the hub stops
// the arm; a page that is hidden or closed says so first, and the show carries
// on by itself as it always has (A26-46).
setInterval(() => {
  if (playing && !document.hidden && hubDriven())
    fetch("/api/play/beat", { method: "POST", body: "{}" }).catch(() => {});
}, 1000);
function hubLeaving() {
  try { navigator.sendBeacon("/api/play/beat", JSON.stringify({ leaving: true })); } catch (e) { /* no beacon: the timeout decides */ }
}
document.addEventListener("visibilitychange", () => {
  if (!playing || !hubDriven()) return;
  if (document.hidden) hubLeaving();
  else fetch("/api/play/beat", { method: "POST", body: "{}" }).catch(() => {});
});
window.addEventListener("pagehide", () => { if (playing && hubDriven()) hubLeaving(); });
function hubStop() {
  return fetch("/api/play/stop", { method: "POST" }).catch(() => {});
}
function livePause() {
  // Stop the HUB's clock FIRST, whatever the link state: a show started while
  // Live was unticked is hub-driven, and an early return here left that clock
  // running — Pause stopped the drawing but the robot carried on.
  cancelSafeMotion("paused");
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
  const ret = loopReturnMs();
  if (ret && ms < t + ret) return Math.max(1, Math.round(t + ret - ms));
  return 0;
}
function scrubTo(v) {
  const was = playing;
  ++seekToken;                       // a scrub cancels a pending resume
  const from = pose.slice();
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
  // A JUMP along the bar is not a drag: sent at drag time (80-300 ms) the arm
  // swung across at full servo speed. Anything slower than a drag goes at
  // the show's speed from where the arm is (2026-09-16).
  if (liveLinked()) {
    const safe = autoTime(from, pose, speedDps());
    if (safe > LIVE_T_MAX) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + safe);
    else sendPoseLive();
  }
}
// --- YAML export ---
function fmtA(a) { return (Math.round(a * 10) / 10).toString(); }
// fromMs: where the show's clock is parked. A file built from a parked clock
// starts at THAT keyframe, not at the first one — the robot is already standing
// at the pose you clicked, and sending it back to keyframe 0 first is a long
// unplanned sweep across the rig. The user, 2026-08-28: *my body of robot will
// broke it hit other thing that i don't want if it warp to pose 1*.
// The skipped keyframes are still WALKED: `speed` is state, so a file that
// starts in the middle must carry the speed in force there, or the rest of the
// show runs at the wrong one.
function buildYaml(fromMs) {
  const name = ($("projName").value || "sequence").trim().replace(/[^\w.-]+/g, "_");
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
  const seqDps = Math.round(speedDps());
  const K0 = playKeys();
  // where this file starts. 0 (the whole show) unless a clock was handed in.
  const from = fromMs > 0 ? keyIndexAtMs(fromMs) : 0;
  // the speed in force at that point, which is what the leading step must be
  let cur = seqDps;
  for (let s = 0; s < from && s < K0.length; s++) cur = Math.round(K0[s].dps || seqDps);
  lines.push(`  - speed: ${cur}`);
  // suspended keyframes are left out entirely — the robot never sees them
  playKeys().forEach((k, i) => {
    if (i < from) return;      // walked for state above, never written as motion
    // a move with its own speed emits a speed step first, and the next move
    // without one puts the sequence speed back — so the file reads exactly as
    // the timeline runs, and the module's speed tracks it move by move.
    // No i>0 exemption: an override on the FIRST move must be written too,
    // or the robot plays it at the sequence speed the timeline never showed.
    const want = Math.round(k.dps || speedDps());
    if (want !== cur) { lines.push(`  - speed: ${want}`); cur = want; }
    // The name you gave the move, as a comment above it. A comment so
    // every existing player still reads the file unchanged — the
    // firmware ignores it, and a person opening the YAML can see what
    // each step was meant to be.
    if (k.name) lines.push(`  # ${k.name.replace(/[\r\n]/g, " ")}`);
    // The cues this keyframe carried in, written back where they came from —
    // before the move, the same order the file had them in. Without this an
    // edit-and-export silently threw the show's music away.
    (k.cues || []).forEach(c => lines.push(`  - ${c}`));
    // The FIRST move written is the only one whose starting point the file
    // cannot know — the robot is wherever it is standing, not where the
    // timeline says. Give it at least the time that distance really needs, so
    // a resumed show can never begin with a lunge. Never faster, only slower.
    const t = (i === from && from > 0) ? Math.max(k.t, minTime(pose, k.pose)) : k.t;
    lines.push(`  - pose: "${k.pose.map(fmtA).join(" ")} T ${t}"` +
               (i === 0 ? "    # start pose"
                        : i === from ? "    # resumed from here" : ""));
    if (k.hold > 0) lines.push(`  - wait: ${k.hold}`);
    (k.cuesAfter || []).forEach(c => lines.push(`  - ${c}`));
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
// opts.noAsk: saveAll() already asked. True when the file is on disk.
async function exportYaml(opts) {
  opts = opts || {};
  if (nothingToWrite("tlStat")) return false;
  const sig = workSig();                  // what THIS save writes, before any await
  const { name, yaml } = buildYaml();
  // SAVING OVER A FILE ASKS FIRST (user 2026-09-16: every save went to
  // my_move.yaml, because that is the name the box starts with).
  const have = [...$("seqList").options].map(o => o.value);
  if (!opts.noAsk && have.includes(name + ".yaml") &&
      !confirm(name + ".yaml is already saved. Replace it?\n\n" +
               "Cancel, then type a new name in the sequence name box to keep both.")) {
    $("tlStat").textContent = "not saved — " + name + ".yaml was left as it was";
    return false;
  }
  let ok = false;
  // Every failure path must SAY something: an unhandled rejection here left
  // the old status line standing, and a silent export reads as saved work.
  try {
    const r = await fetch("/api/export", {
      method: "POST", body: JSON.stringify({ name: name + ".yaml", yaml }),
    });
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error((j && j.error) || ("HTTP " + r.status));
    // j.file echoes a name that was typed into this page; as text, never
    // as markup.
    $("tlStat").textContent =
      `saved ${j.file} on this PC — voice answers and the other apps can use it now. ` +
      `Send to robot SD puts it on the board.`;
    ok = true;
    if (!opts.keepDraft) markSaved(sig, name, 0);
  } catch (e) {
    $("tlStat").textContent = "export failed — the hub is not answering, or "
      + "refused the name. Nothing was written. " + (e.message || e);
    notice($("tlStat").textContent);
  }
  await refreshSeqs();
  if (ok) seqsChanged();   // the Shows list and other tabs too, not just this list
  if (ok) $("seqList").value = name + ".yaml";   // the list shows what was just saved
  return ok;
}
// --- rig setup UI ---
const DIM_LABELS = {
  shoulderX: "shoulder ±X", shoulderY: "shoulder Y",
  upperLenL: "L upper arm", upperLenR: "R upper arm",
  foreLenL: "L forearm", foreLenR: "R forearm",
  torsoW: "torso W", torsoH: "torso H", torsoD: "torso D",
  shrugPivot: "shrug pivot ↑ (mm above shoulders)",
};
function renderRigUI() {
  if ($("extraClearanceMm")) $("extraClearanceMm").value = RIG.extraClearanceMm ?? 0;
  const jb = $("rigJoints");
  jb.innerHTML = "";
  // WHERE EACH PALM SITS (A44-1). The hand part can be fixed to the forearm
  // any way round; turn the drawn hand until its skin side matches the real
  // palm. Every "palm up / back up" in Pose and the timeline works from this.
  HANDS.forEach((h, i) => {
    const row = document.createElement("div"); row.className = "row";
    const lbl = document.createElement("span"); lbl.className = "lbl";
    lbl.textContent = h.label + " palm";
    const turn = document.createElement("button");
    turn.textContent = "↻ Turn the drawn hand";
    turn.title = "the skin-coloured side of the drawn hand is its palm. Turn it "
               + "until it faces the same way as the real hand's palm.";
    const at = document.createElement("span"); at.className = "mini";
    at.textContent = RIG.palmTurn[i] + "°";
    turn.onclick = () => {
      RIG.palmTurn[i] = (RIG.palmTurn[i] + 90) % 360;
      at.textContent = RIG.palmTurn[i] + "°";
      rigChanged();
      renderTimeline();          // what is on top of each move may have changed
    };
    row.append(lbl, turn, at);
    jb.appendChild(row);
  });
  // header
  const hdr = document.createElement("div"); hdr.className = "rigjrow";
  ["joint", "zero°", "start°", "min°", "max°", "axis", "inv"].forEach(t => {
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
    // START angle. Asked for 2026-09-10: *when start make can change position of
    // servo when start not only 90 can select own deg per joint*. Kept inside
    // this joint's own min/max, like `lo`/`hi` below and for the same reason —
    // a typed number goes straight past the min/max attributes, and this one is
    // written to the board and used on every boot.
    const neu = document.createElement("input");
    neu.type = "number"; neu.min = 0; neu.max = 180; neu.value = RIG.home[i];
    neu.title = "robot home: where this joint goes when the robot starts, and "
              + "when you press Home";
    neu.onchange = () => {
      RIG.home[i] = Math.max(RIG.min[i], Math.min(RIG.max[i],
                             clampDeg(+neu.value || 0)));
      neu.value = RIG.home[i];             // show what was actually accepted
      rigChanged();
    };
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
    row.append(name, zero, neu, lo, hi, ax, inv);
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
        // the board keeps WHOLE teeth (GEAR parses with toInt: 4.5 became 4),
        // so a fraction here would preview a ratio the robot never uses
        if (key === "gearPinion" || key === "gearGear") v = Math.round(v);
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
  // THE WHOLE BODY IN ONE CLICK. Asked 2026-09-18 (A26-72): the real robot's
  // measurements should be something you PICK, not numbers somebody types from
  // a drawing. The list is data (config/rig_presets.json) fetched from the hub,
  // so a second robot costs one entry and no code here.
  const bodyRow = document.createElement("div"); bodyRow.className = "jrow";
  const bl = document.createElement("span");
  bl.className = "jname"; bl.textContent = "body";
  const bsel = document.createElement("select");
  bsel.innerHTML = "<option value=''>use a measured body…</option>" +
    RIG_PRESETS.map(p => `<option value="${p.id}">${p.label}</option>`).join("");
  bsel.title = "sets every size below from a real robot; each one says where "
             + "its numbers come from";
  bsel.onchange = () => { if (bsel.value) { applyRigPreset(bsel.value); bsel.value = ""; } };
  const why = document.createElement("span");
  why.className = "hint"; why.style.fontSize = "11px";
  why.textContent = RIG_PRESETS.length
    ? "reach " + RIG_PRESETS[0].reach_mm + " mm"
    : "";
  bodyRow.append(bl, bsel, why);
  db.appendChild(bodyRow);
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
  // One call site rather than the eleven that reach renderRigUI, so the offset
  // rows cannot be left showing yesterday's numbers after a reset or a pull.
  renderOffsets();
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
// BODIES this rig can be set to (A26-72). Data, fetched from the hub; the one
// entry below is only a fallback for opening Studio with no hub, and it is the
// measured robot because that is the one somebody is standing next to.
let RIG_PRESETS = [
  { id: "nong_step_2026_09",
    label: "Nong, measured from the STEP file (Sep 2026)",
    source: "nong_assembly.STEP",
    dims: { shoulderX: 88, shoulderY: 110, upperLenL: 128.7, upperLenR: 128.7,
            foreLenL: 167.64, foreLenR: 167.64,
            torsoW: 100, torsoH: 250, torsoD: 70, shrugPivot: 68.1 },
    reach_mm: 296.34,
    note: "arm links and shoulder spacing measured; the torso box is still the "
        + "drawn stand-in" },
];
async function loadRigPresets() {
  try {
    const r = await fetch("/api/rigpresets").then(r => r.json());
    if (r && r.ok && Array.isArray(r.presets) && r.presets.length) {
      RIG_PRESETS = r.presets;
      if (typeof renderRigUI === "function") renderRigUI();
    }
  } catch (e) { /* no hub: the fallback above stands */ }
}
loadRigPresets();
function applyRigPreset(id) {
  const p = RIG_PRESETS.find(x => x.id === id);
  if (!p || !p.dims) return;
  // Only the sizes. Zeroes, limits, gears and offsets belong to the servos
  // fitted to THIS robot, and a body preset must never quietly rewrite them.
  Object.entries(p.dims).forEach(([k, v]) => {
    if (k in RIG.dims) RIG.dims[k] = +v;
  });
  // The servos measured with the body (A31-17: *load all from my step*) are
  // offered, never assumed: they rewrite what the fitted servos need.
  let servos = "";
  if (p.servos && confirm(
      "This body also knows its servos and gears from the STEP file:\n\n"
      + presetServoSummary(p) + "\n\n"
      + "OK — use them too\nCancel — keep the servo settings you have now"))
    servos = applyPresetServos(p);
  rigChanged(); renderRigUI(); buildRobot(); renderSliders();
  if (typeof notice === "function")
    notice(p.label + " — reach " + (p.reach_mm || "?") + " mm. "
      + (servos ? "Servos set: " + servos + ". Press “Send Studio's limits to the robot” to put them on the robot. " : "")
      + (p.note || ""));
}
function presetServoSummary(p) {
  return Object.entries(p.servos).map(([name, s]) => {
    const t = SERVO_TYPES[s.servo];
    return name + ": " + (t ? t.label : s.servo)
      + (s.gear ? ", gear " + s.gear[0] + ":" + s.gear[1] : "")
      + (s.min != null ? ", " + s.min + "–" + s.max + "°" : "");
  }).join("\n");
}
// Keyed by joint NAME in the file, so a reordered joint list cannot shift a
// gear onto the wrong servo. Returns which joints changed, for the notice.
function applyPresetServos(p) {
  try { localStorage.setItem("nong_rig_prev", JSON.stringify(RIG)); }
  catch (e) { /* storage full: the change still happens, just without undo */ }
  const done = [];
  Object.entries(p.servos).forEach(([name, s]) => {
    const i = JOINT_NAMES.indexOf(name);
    if (i < 0) return;
    const t = SERVO_TYPES[s.servo];
    if (t) {
      RIG.pulseMin[i] = t.min; RIG.pulseMax[i] = t.max;
      RIG.servoMaxDps[i] = t.dps; RIG.servoRange[i] = t.range; RIG.frameHz[i] = t.hz;
    }
    if (Array.isArray(s.gear) && s.gear.length === 2) {
      RIG.gearPinion[i] = Math.round(s.gear[0]); RIG.gearGear[i] = Math.round(s.gear[1]);
    }
    if (s.min != null && s.max != null) { RIG.min[i] = +s.min; RIG.max[i] = +s.max; }
    done.push(name);
  });
  saveRig();
  return done.join(", ");
}
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
  if (typeof cancelSafeMotion === "function") cancelSafeMotion("the rig or safety gap changed");
  saveRig();
  buildRobot();
  renderSliders();
}
function setSafetyClearance(raw) {
  const value = raw.trim() === "" ? NaN : Number(raw);
  const stat = $("clearanceStat");
  if (!Number.isFinite(value) || value < 0) {
    stat.textContent = "Enter a distance of zero or more millimetres.";
    $("extraClearanceMm").value = RIG.extraClearanceMm ?? 0;
    return false;
  }
  RIG.extraClearanceMm = value;
  rigChanged();
  stat.textContent = "Saved: keep at least " + (CLEAR + value) + " mm between parts. Existing paths will be checked again.";
  return true;
}

// ---- servo offset, one joint at a time -----------------------------------
//
// Asked for 2026-09-10: *make can set offset to servo because sometime i set it
// not exact 0 or 90*. A servo horn refits in whole teeth, so a joint lands a few
// degrees out; until now the only cure was Set zero, which rewrites all ten from
// the current pose and is behind a password.
//
// The number here is JOINT degrees — what a person can see on the arm. The board
// keeps it in servo degrees (`trim`) and does the conversion, so the same typed
// number moves every joint by the same visible amount whatever its gearing.
// It is NOT drawn in the 3D preview: the preview shows the pose the robot was
// asked for, and an offset is the difference between that and where the arm
// really is. Drawing it would hide the very error being corrected.
const OFFSET_STEP = 0.5;      // one press. Below this nothing is visible on the arm.
const OFFSET_MAX = 30;        // matches NONG_OFFSET_MAX_DEG on the board

function renderOffsets() {
  const box = $("trimUI");
  if (!box) return;
  box.innerHTML = "";
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "trow-t" + (Math.abs(RIG.offset[i]) > 0.01 ? " set" : "");
    const name = document.createElement("span");
    name.className = "t-lbl"; name.textContent = label;
    const val = document.createElement("input");
    val.type = "number"; val.className = "t-val";
    val.step = OFFSET_STEP; val.min = -OFFSET_MAX; val.max = OFFSET_MAX;
    val.value = RIG.offset[i];
    val.setAttribute("aria-label", "offset for " + label + ", in degrees");
    val.title = "how far this joint is corrected, in degrees on the arm";
    val.onchange = () => sendOffset(i, +val.value || 0);
    const step = (delta, text, hint) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "t-btn"; b.textContent = text;
      b.title = hint;
      b.onclick = () => sendOffset(i, RIG.offset[i] + delta);
      return b;
    };
    const zero = document.createElement("button");
    zero.type = "button"; zero.className = "t-btn"; zero.textContent = "0";
    zero.title = "clear this joint's offset";
    zero.onclick = () => sendOffset(i, 0);
    row.append(name,
               step(-OFFSET_STEP, "−", "move " + label + " back " + OFFSET_STEP + "°"),
               val,
               step(OFFSET_STEP, "+", "move " + label + " on " + OFFSET_STEP + "°"),
               zero);
    box.appendChild(row);
  });
}

// One joint, straight to the robot. Kept and shown even with nothing connected,
// so the offsets travel with the rig to another PC — but the status line says
// plainly that the robot has not been told.
async function sendOffset(i, deg) {
  const clamped = Math.max(-OFFSET_MAX, Math.min(OFFSET_MAX, Math.round(deg * 2) / 2));
  RIG.offset[i] = clamped;
  saveRig();
  renderOffsets();
  const st = $("trimStat");
  if (!haveRobot()) {
    if (st) st.textContent = JOINT_LABELS[i] + " offset " + clamped
      + "° — saved here. Connect the robot to move it.";
    return;
  }
  try {
    const r = await rawCmd("OFFSET " + (i + 1) + " " + clamped);
    if (st) st.textContent = /^ERR/i.test(r || "")
      ? "the robot refused it: " + r
      : JOINT_LABELS[i] + " is now corrected by " + clamped + "°";
  } catch (e) {
    if (st) st.textContent = "saved here, but it did not reach the robot: "
      + (e.message || e);
  }
}

async function pullOffsets() {
  const st = $("trimStat");
  if (!haveRobot()) {
    if (st) st.textContent = "connect to the robot first (Robot link card)";
    notice(st.textContent);
    return;
  }
  try {
    const j = JSON.parse(await rawCmd("LIMIT?"));
    if (Array.isArray(j.offset))
      RIG.offset = RIG.offset.map((d, i) =>
        (j.offset[i] !== undefined ? Number(j.offset[i]) : d));
    saveRig();
    renderOffsets();
    if (st) st.textContent = "read the offsets the robot is using ✓";
  } catch (e) {
    if (st) st.textContent = "read failed: " + (e.message || e);
    notice($("trimStat").textContent);
  }
}

async function clearOffsets() {
  RIG.offset = RIG.offset.map(() => 0);
  saveRig();
  renderOffsets();
  const st = $("trimStat");
  if (!haveRobot()) {
    if (st) st.textContent = "every offset cleared here — the robot still has its own";
    return;
  }
  try {
    await rawCmd("OFFSET ALL 0");
    if (st) st.textContent = "every joint's offset cleared, here and on the robot ✓";
  } catch (e) {
    if (st) st.textContent = "cleared here, but the robot was not told: " + (e.message || e);
  }
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
  if (!haveRobot()) { $("limStat").textContent = "connect to the robot first (Robot link card)"; notice($("limStat").textContent); return; }
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
      const neu = Math.round(RIG.home[i]);          // the board's NEUTRAL = robot home
      const off = Math.round(RIG.offset[i] * 2) / 2;   // half a degree, as the buttons step
      const parts = [];
      if (!(same("min", i, mn) && same("max", i, mx)))
        parts.push(`LIMIT ${i + 1} ${mn} ${mx}`);
      if (!(same("gear_pinion", i, RIG.gearPinion[i]) && same("gear_gear", i, RIG.gearGear[i])))
        parts.push(`GEAR ${i + 1} ${RIG.gearPinion[i]} ${RIG.gearGear[i]}`);
      if (!(same("pulse_min", i, pmin) && same("pulse_max", i, pmax) && same("max_dps", i, dps)))
        parts.push(`PULSE ${i + 1} ${pmin} ${pmax} ${dps}`);
      if (!same("servo_range", i, rng)) parts.push(`RANGE ${i + 1} ${rng}`);
      if (!same("frame_hz", i, hz)) parts.push(`RATE ${i + 1} ${hz}`);
      if (!same("neutral", i, neu)) parts.push(`NEUTRAL ${i + 1} ${neu}`);
      // The offset stays OUT of the JCFG batch on purpose: JCFG collapses the
      // five fields set together when a servo is configured, while an offset is
      // nudged on its own — and keeping it out leaves that batch's positional
      // contract alone. It therefore rides in `always`, NOT in `parts`: the batch
      // path does `continue` past parts, so a line put there would have been
      // silently dropped on every board that understands JCFG.
      const always = same("offset", i, off) ? [] : [`OFFSET ${i + 1} ${off}`];
      if (!parts.length && !always.length) continue;
      jobs.push({
        joint: i + 1, parts, always,
        // neutral is APPENDED, never inserted: an older board ignores the extra
        // token, and QC reads the first nine values by position.
        batch: `JCFG ${i + 1} ${RIG.gearPinion[i]} ${RIG.gearGear[i]} ${pmin} ${pmax} ` +
               `${dps} ${rng} ${hz} ${mn} ${mx} ${neu}`,
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
      // whatever the batch cannot carry goes first, so it is sent either way
      for (const c of job.always) { await rawCmd(c); sent++; }
      if (useBatch && job.parts.length) {
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
      `${jobs.length > 1 ? "s" : ""} (limits, gear, pulse, travel, frame rate, ` +
      `start angle, offset)` +
      (useBatch ? "" : " — this board is older than JCFG, so each setting went separately") +
      (have ? "" : " — could not read the robot first, so everything was sent") + " ✓";
  } catch (e) { $("limStat").textContent = "send failed: " + (e.message || e); notice($("limStat").textContent); }
}
// read the module's current limits + gear back into the rig
async function pullLimits() {
  if (!haveRobot()) { $("limStat").textContent = "connect to the robot first"; notice($("limStat").textContent); return; }
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
    pull(j.neutral, "home");
    pull(j.offset, "offset");
    saveRig(); renderRigUI(); buildRobot(); renderSliders();
    $("limStat").textContent =
      "read limits, gear, start angles and offsets from the robot ✓";
  } catch (e) { $("limStat").textContent = "read failed: " + (e.message || e); notice($("limStat").textContent); }
}
// --- edit existing sequences ---
// Parse a /moves YAML (the format this editor exports and the firmware plays)
// back into timeline keyframes, so any saved sequence can be re-edited.
// --- shows: saved sequences in series ---
// User 2026-09-17: mix and match sequences (greeting, then byebye). A show is a
// list of sequence NAMES saved by the hub in shows/*.json (main_python/shows.py);
// the hub plays it as one run, so it works over WiFi or the cable.
// join_dps/join_ms: how fast the move BETWEEN sequences may be (0 = off);
// music: the show's own track on the robot's card (user 2026-09-27).
function blankShow() {
  return { name: "", loop: false, items: [], join_dps: 0, join_ms: 0,
           music: "", music_vol: -1, music_loop: false, music_end: "", music_secs: 0 };
}
let showDraft = blankShow();
let showOnBar = "";      // the show currently drawn on the time bar, "" = none
let showBar = { keys: null, musicStopMs: null };
function showBarMusicStop() { return showBar.keys === keys ? showBar.musicStopMs : null; }
// The robot's speed limits as THIS page plans with them. The hub times every
// move of the show to at least what the board will take (shows.move_floor),
// so the time bar, the preview and the robot run on one clock - without them
// the board stretched the joins and a 49 s mark was reached at 52 s.
function showLimits() {
  const max = [];
  for (let i = 0; i < NJ; i++) max.push(jointMaxDps(i));
  return { safe_dps: SAFE_DPS, max_dps: max };
}

async function refreshShows() {
  try {
    const [s, q] = await Promise.all([
      fetch("/api/shows").then(r => r.json()),
      fetch("/api/list?kind=sequences").then(r => r.json())]);
    const sel = $("showList"), add = $("showAddSeq");
    if (!sel || !add) return;
    sel.innerHTML = "<option value=''>Open saved show…</option>";
    (s.shows || []).forEach(n => { const o = document.createElement("option"); o.value = o.textContent = n; sel.appendChild(o); });
    if (showDraft.name && (s.shows || []).includes(showDraft.name)) sel.value = showDraft.name;
    const keep = add.value;   // a refresh must not drop what was being picked
    add.innerHTML = "<option value=''>Add a saved sequence…</option>";
    (q.files || []).filter(f => f.endsWith(".yaml")).forEach(f => {
      const o = document.createElement("option"); o.value = o.textContent = f; add.appendChild(o);
    });
    if (keep && (q.files || []).includes(keep)) add.value = keep;
  } catch (e) { /* Studio opened without the hub: nothing to list */ }
}
// User 2026-09-27: a sequence saved in Studio did not show in the Show list
// until the page was reloaded. seqsChanged() is called after every save or
// delete (the caller has already refreshed the Timeline list, and set its
// pick): it refreshes the Shows list and tells other Studio tabs in this
// browser. Other PCs and phones pick the change up when their tab comes back
// into view or the Shows tab is opened.
const seqChan = ("BroadcastChannel" in window) ? new BroadcastChannel("mice-seqs") : null;
function seqsChanged() {
  refreshShows();
  if (seqChan) seqChan.postMessage("changed");
}
if (seqChan) seqChan.onmessage = () => { refreshSeqs().catch(() => {}); refreshShows(); };
document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshShows(); });
window.addEventListener("focus", () => refreshShows());
// The track list is the robot's own /music folder (music_on_a_keyframe.js),
// so only files really on the card are offered; a set track is kept even
// while the robot is not connected.
function renderShowMusic() {
  const sel = $("showMusic");
  if (!sel) return;
  const cur = showDraft.music || "";
  const names = musicList ? musicList.slice() : [];
  if (cur && names.indexOf(cur) < 0) names.push(cur);
  sel.innerHTML = "";
  [["", "no music"]].concat(names.map(n => [n, n])).forEach(([v, label]) => {
    const o = document.createElement("option"); o.value = v; o.textContent = label; sel.appendChild(o);
  });
  sel.value = cur;
  sel.title = musicList ? "a track on the robot's card, played from the start of the show to its end"
                        : (musicNote || "connect the robot to choose a track");
  $("showMusicVol").value = showDraft.music_vol >= 0 ? showDraft.music_vol : "";
  $("showMusicVol").disabled = !cur;
  $("showMusicLoop").checked = !!showDraft.music_loop;
  $("showMusicLoop").disabled = !cur;
  // how long the track plays: with the moves, N s after, or N s in all
  $("showMusicEndRow").style.display = cur ? "" : "none";
  $("showMusicEnd").value = showDraft.music_end || "";
  $("showMusicSecs").value = showDraft.music_end ? showDraft.music_secs : "";
  $("showMusicSecs").style.display = showDraft.music_end ? "" : "none";
  if (!musicList && robotLinked()) loadMusicList().then(() => { if (musicList) renderShowMusic(); });
}
// A track from THIS PC becomes the show's music (user 2026-09-27: *in show
// make can add music from pc*). It goes onto the robot's card the same way a
// keyframe's track does (uploadMusicFile), then is picked here.
function addShowMusicFromPc() {
  if (!robotLinked()) {
    // said in a popup too: the status line sits far below this button, so
    // the click looked like it did nothing (user 2026-09-27)
    $("showStat").textContent = "Connect the robot first (Robot tab) — the track " +
      "goes onto the robot's card, so it needs the robot.";
    notice($("showStat").textContent);
    return;
  }
  const pick = (name, whyNot, renamed) => {
    if (!name) { $("showStat").textContent = whyNot; notice(whyNot); return; }
    showDraft.music = name;
    renderShowMusic();
    showChanged();
    $("showStat").textContent = name + " is on the robot's card and is now this " +
      "show's music" + (renamed || "") + ". Save the show to keep it.";
  };
  pick.busy = msg => { $("showStat").textContent = msg; };   // a long upload is visible
  pickMusicFile(null, pick);
  $("showStat").textContent = "choose a track (.mp3 or .wav) on this computer…";
}
function showSettingChanged() {
  readShowForm();
  renderShowMusic();
  showChanged();
}
function renderShow() {
  const box = $("showItems");
  if (!box) return;
  $("showName").value = showDraft.name;
  $("showLoop").checked = showDraft.loop;
  $("showJoinDps").value = showDraft.join_dps > 0 ? showDraft.join_dps : "";
  $("showJoinS").value = showDraft.join_ms > 0 ? showDraft.join_ms / 1000 : "";
  renderShowMusic();
  box.innerHTML = "";
  if (!showDraft.items.length) {
    box.innerHTML = "<div class='mini'>No sequences yet — add one above.</div>";
    return;
  }
  showDraft.items.forEach((it, i) => {
    const row = document.createElement("div"); row.className = "row";
    const n = document.createElement("span"); n.className = "lbl"; n.textContent = (i + 1) + ".";
    const name = document.createElement("span"); name.style.flex = "1"; name.textContent = it.seq;
    const hold = document.createElement("input");
    hold.type = "number"; hold.min = 0; hold.step = 100; hold.value = it.hold || 0; hold.style.width = "80px";
    hold.title = "stand still for this long AFTER this sequence, in ms. 0 = run straight on into the next one.";
    hold.onchange = () => { it.hold = Math.max(0, +hold.value || 0); showChanged(); };
    // REPEAT, in the operator's two ways of saying it (user 2026-09-23: *loop
    // for how many time like 60S or 30S or make it loop for 4 time 3 time*).
    // The mode picks which unit the one number is in, so there is never a
    // count and a duration both set and only one of them obeyed.
    const mode = document.createElement("select");
    mode.style.width = "110px";
    mode.title = "play this sequence again: a number of times, or for a number of seconds";
    [["", "play once"], ["times", "repeat × times"],
     ["seconds", "repeat for seconds"], ["exact", "run for exactly … s"]]
      .forEach(([v, label]) => {
        const o = document.createElement("option"); o.value = v; o.textContent = label; mode.appendChild(o);
      });
    mode.value = it.repeat_mode || "";
    const rep = document.createElement("input");
    rep.type = "number";
    rep.min = mode.value === "times" ? 2 : (mode.value === "exact" ? 0.1 : 1);
    rep.step = mode.value === "seconds" ? 5 : 1;
    rep.style.width = "70px";
    rep.value = it.repeat || "";
    rep.style.display = mode.value ? "" : "none";
    rep.title = mode.value === "seconds"
      ? "keep repeating until this many seconds have passed. A pass is never cut in half, so the last one finishes and the item runs a little over."
      : mode.value === "exact"
        ? "this sequence gets exactly this many seconds and no more. It is cut "
          + "wherever it has got to, and the move into the next sequence's first "
          + "pose is timed to arrive right on the deadline — so the show keeps to "
          + "its timetable and the join is not visible."
        : "how many times this sequence plays in a row";
    mode.onchange = () => {
      it.repeat_mode = mode.value;
      if (!mode.value) it.repeat = 0;
      else if (!(it.repeat > 0)) it.repeat = mode.value === "times" ? 2 : 30;
      if (mode.value === "exact" && it.repeat < 0.1) it.repeat = 30;
      renderShow(); showChanged();
    };
    rep.onchange = () => {
      it.repeat = Math.max(mode.value === "times" ? 2 : 0.1, +rep.value || 0);
      renderShow(); showChanged();
    };
    const unit = document.createElement("span"); unit.className = "mini";
    unit.textContent = mode.value === "times" ? "×" : (mode.value ? "s" : "");
    const btn = (label, title, fn) => { const b = document.createElement("button"); b.textContent = label; b.title = title; b.onclick = fn; return b; };
    // Speed in THIS show only, % of the sequence's saved timing (user
    // 2026-09-27). The time bar is redrawn from the hub, so it follows.
    const spd = document.createElement("input");
    spd.type = "number"; spd.min = 10; spd.max = 400; spd.step = 10;
    spd.style.width = "64px";
    spd.value = it.speed_pct || 100;
    spd.setAttribute("aria-label", "speed of " + it.seq + " in this show, percent");
    spd.title = "how fast this sequence runs in this show: 100 = as saved, 50 = half " +
      "speed, 200 = twice as fast. Pauses keep their length, and a move is never " +
      "faster than the robot allows.";
    spd.onchange = () => {
      it.speed_pct = Math.max(10, Math.min(400, Math.round(+spd.value || 100)));
      spd.value = it.speed_pct; showChanged();
    };
    row.append(n, name, mode, rep, unit, document.createTextNode("speed"), spd,
      document.createTextNode("%"), document.createTextNode("pause"), hold,
      btn("▲", "play earlier", () => { moveShowItem(i, -1); showChanged(); }),
      btn("▼", "play later", () => { moveShowItem(i, 1); showChanged(); }),
      btn("✕", "take out of this show", () => { showDraft.items.splice(i, 1); renderShow(); showChanged(); }));
    box.appendChild(row);
  });
}
// The show on the time bar is redrawn whenever the show changes, but ONLY if
// it is already on it: loading a show over keyframes somebody is editing,
// because they typed a pause, would be the edit disappearing under them.
function showChanged() { if (showOnBar) showOnTimeline(true); }
function readShowForm() {
  showDraft.name = $("showName").value.trim();
  showDraft.loop = $("showLoop").checked;
  showDraft.join_dps = Math.max(0, +$("showJoinDps").value || 0);
  showDraft.join_ms = Math.max(0, Math.round((+$("showJoinS").value || 0) * 1000));
  showDraft.music = $("showMusic").value;
  const v = $("showMusicVol").value;
  showDraft.music_vol = showDraft.music && v !== ""
    ? Math.max(0, Math.min(100, Math.round(+v || 0))) : -1;
  showDraft.music_loop = !!showDraft.music && $("showMusicLoop").checked;
  showDraft.music_end = showDraft.music ? $("showMusicEnd").value : "";
  let secs = Math.max(0, +$("showMusicSecs").value || 0);
  // a mode just picked starts from a number that does something
  if (showDraft.music_end && $("showMusicSecs").value === "")
    secs = showDraft.music_end === "total" ? 60 : 5;
  showDraft.music_secs = showDraft.music_end ? secs : 0;
  return showDraft;
}
function newShow() { showDraft = blankShow(); renderShow(); $("showStat").textContent = "new show — add sequences, then Save."; }
function addShowItem() {
  const f = $("showAddSeq").value;
  if (!f) { $("showStat").textContent = "pick a saved sequence to add first."; return; }
  showDraft.items.push({ seq: f, hold: 0 });
  renderShow();
}
function moveShowItem(i, d) {
  const j = i + d, it = showDraft.items;
  if (j < 0 || j >= it.length) return;
  [it[i], it[j]] = [it[j], it[i]];
  renderShow();
}
async function openShow() {
  const n = $("showList").value;
  if (!n) return;
  const r = await fetch("/api/show?name=" + encodeURIComponent(n)).then(r => r.json());
  if (!r.ok) { $("showStat").textContent = "cannot open " + n + ": " + (r.error || "not found"); notice($("showStat").textContent); return; }
  showDraft = Object.assign(blankShow(), r.show); showDraft.name = showDraft.name || n;
  renderShow();
  $("showStat").textContent = "opened " + n + " (" + showDraft.items.length + " sequences).";
  // User 2026-09-23: *when click in show and we have the all sequence show all
  // of it in nong studio too in series*. Opening a show IS the click, so the
  // whole chain goes on the time bar - asking first only when the bar holds
  // unsaved keyframes, which are somebody's work.
  await showOnTimeline(false, true);
}
// Every sequence of the show on ONE timeline, end to end, as the robot runs it.
// The steps come from the HUB (/api/show/steps), not from re-reading the yaml
// here: the chaining rule and the repeats live in main_python/shows.py, and a
// second copy in JavaScript would drift until the editor showed a run the
// robot does not perform.
async function showOnTimeline(quiet, onlyIfSafe) {
  const s = readShowForm();
  if (!s.items.length) {
    if (!quiet) $("showStat").textContent = "add at least one sequence first.";
    return false;
  }
  // The same question every other loader asks (A31-18/A31-19). A quiet redraw
  // (a pause typed in the show) never pops a dialog: with unsaved edits on
  // the bar it just leaves them and says so.
  if (quiet && isDirty()) {
    $("showStat").textContent = "the time bar has edits that are not saved, so the "
      + "show was not redrawn over them. Press ⇣ Show on the time bar to redraw it.";
    return false;
  }
  if (!quiet && !(await askUnsaved("put " + (s.name || "this show") + " on the time bar"))) {
    $("showStat").textContent = (onlyIfSafe ? "opened " + (s.name || "this show") + " — " : "")
      + "the time bar was left as it was.";
    return false;
  }
  try {
    const j = await showPost("/api/show/steps", { show: s, limits: showLimits() });
    const steps = j.steps || [], marks = j.marks || [];
    if (steps.length < 2) throw new Error("this show has fewer than two poses");
    const startOf = {}, travel = {}, taken = new Set(marks.map(m => m.step));
    let prev = "";
    marks.forEach(m => {
      // pass 1 of an item is where its NAME goes; later passes say which pass
      const name = m.pass > 1
        ? m.seq.replace(/\.yaml$/, "") + " ×" + m.pass
        : m.seq.replace(/\.yaml$/, "");
      // After an "exactly N s" item the move into this pose is paid from THAT
      // item's seconds. Drawn under the new name, the new sequence seemed to
      // start early (user 2026-09-23, 42 s item). The move stays with the cut
      // item; the new name goes on the next pose, which starts on the deadline.
      if (m.handover && m.step + 1 < steps.length && !taken.has(m.step + 1)) {
        travel[m.step] = prev + " → " + name;
        startOf[m.step + 1] = name;
      } else startOf[m.step] = name;
      prev = m.seq.replace(/\.yaml$/, "");
    });
    keys = steps.map((st, i) => {
      const k = { pose: st.pose.map(Number), t: Math.round(st.t || 0),
                  hold: Math.round(st.hold || 0) };
      if (travel[i] !== undefined) k.name = travel[i];
      if (startOf[i] !== undefined) { k.name = startOf[i]; k.seqStart = true; }
      // the file's own cue lines ride along so a preview plays the same music
      if (st.cues && st.cues.length) k.cues = st.cues.slice();
      // the hub's wire name is cues_after; Studio's own field is cuesAfter
      if (st.cues_after && st.cues_after.length) k.cuesAfter = st.cues_after.slice();
      return k;
    });
    // when the show's track stops, for ▶ on the time bar too - tied to THIS
    // key list, so a sequence loaded over the bar later does not inherit it
    showBar = { keys, musicStopMs: j.music_stop_ms == null ? null : j.music_stop_ms };
    selKey = 0;
    playT = 0;
    bumpKeys();
    clearBadMarks();
    renderTimeline();
    // drawn from saved files, so nothing on the bar is unsaved work yet; it is
    // no file's own moves either, so saving it still asks before replacing one
    markSaved(workSig(), "", 0);
    showOnBar = s.name || "(unsaved show)";
    // the bar's own length: keyframe 0's t is the walk TO the show, not on it
    // (said 93.2 s for a 90.0 s run on nong 67, 2026-10-12)
    const secs = (totalMs() / 1000).toFixed(1);
    $("showStat").textContent = `${showOnBar} is on the time bar: ${marks.length} ` +
      `sequence pass(es), ${keys.length} keyframes, ${secs}s. Saving a SEQUENCE ` +
      "from here would save the whole show as one file.";
    return true;
  } catch (e) {
    $("showStat").textContent = "could not draw the show: " + (e.message || e);
    notice($("showStat").textContent);
    return false;
  }
}
async function showPost(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.ok === false || j.error) throw new Error(j.need_login ? "log in first" : (j.error || "HTTP " + r.status));
  return j;
}
async function saveShow() {
  const s = readShowForm();
  if (!s.name) { $("showStat").textContent = "give the show a name first."; return; }
  try {
    const j = await showPost("/api/show/save", { show: s });
    $("showStat").textContent = (j.replaced ? "saved over " : "saved ") + s.name + ".";
    refreshShows();
  } catch (e) { $("showStat").textContent = "not saved: " + (e.message || e); notice($("showStat").textContent); }
}
async function deleteShow() {
  const n = $("showList").value || readShowForm().name;
  if (!n) { $("showStat").textContent = "open a show to delete first."; return; }
  if (!confirm("Delete the show " + n + "?\n\nIt is moved to shows/.deleted, not erased. Its sequences stay.")) return;
  try {
    await showPost("/api/show/delete", { name: n });
    newShow(); refreshShows();
    $("showStat").textContent = n + " deleted (kept in shows/.deleted).";
  } catch (e) { $("showStat").textContent = "not deleted: " + (e.message || e); notice($("showStat").textContent); }
}
async function playShow() {
  const s = readShowForm();
  const dev = moduleDev();
  if (!dev) { $("showStat").textContent = "connect to the robot first (Robot tab)."; notice($("showStat").textContent); return; }
  if (!s.items.length) { $("showStat").textContent = "add at least one sequence first."; return; }
  // The hub plays a show step by step, so nothing of it is on the robot unless
  // it is written there first (A44-2): the same file Save to robot writes.
  let kept = "";
  if (keepRunOn() && haveRobot()) {
    $("showStat").textContent = "keeping a copy of " + (s.name || "this show") + " on the robot…";
    try {
      const j = await showPost("/api/show/yaml", { show: s, limits: showLimits() });
      kept = await keepLastRun(j.yaml, j.file);
    } catch (e) { kept = "the copy as " + LAST_RUN_FILE + " was not kept: " + (e.message || e); }
  }
  try {
    await showPost("/api/show/play", { dev, show: s, limits: showLimits() });
    $("showStat").textContent = "the hub is running " + (s.name || "this show") +
      " — it keeps going with this page closed. ⏹ Stop ends it." +
      (kept ? " Note: " + kept : keepRunOn() && haveRobot()
        ? " A copy is on the robot as " + LAST_RUN_FILE + ", to play from its own page." : "");
    if (kept) notice(kept);
  } catch (e) { $("showStat").textContent = "did not start: " + (e.message || e); notice($("showStat").textContent); }
}
// The show ONTO the robot's card (user 2026-10-12: *in shows is there upload to
// the robot? now only run and save to the PC*). The hub writes the file from the
// same step list ▶ Run plays (shows.robot_yaml); sdUpload sends it over whatever
// link is up. The robot then plays it alone, with the hub and this PC off.
async function sendShowToRobot() {
  const s = readShowForm();
  if (!haveRobot()) { $("showStat").textContent = "connect to the robot first (Robot tab)."; notice($("showStat").textContent); return; }
  if (!s.items.length) { $("showStat").textContent = "add at least one sequence first."; return; }
  try {
    $("showStat").textContent = "sending " + (s.name || "this show") + " to the robot…";
    const j = await showPost("/api/show/yaml", { show: s, limits: showLimits() });
    await sdUpload(j.file, j.yaml);
    $("showStat").textContent = j.file + " is saved on the robot. The robot can play it " +
      "by itself now: pick it in the robot's list (Sequence tab, or the robot's own page).";
    refreshSd();
  } catch (e) { $("showStat").textContent = "not sent: " + (e.message || e); notice($("showStat").textContent); }
}
async function stopShow() {
  try { await fetch("/api/play/stop", { method: "POST" }); $("showStat").textContent = "stopped."; }
  catch (e) { $("showStat").textContent = "the hub did not answer the stop."; }
}
// --- music on a keyframe ---
//
// A move's music is a cue the FILE already carries: `play: song.mp3` before
// the keyframe, `vol: 80` for the level (main.py cue_lines turns them into
// commands). Everything about playing them already works - the editor's job
// is only to make the two clickable, because a value somebody has to type
// into a YAML file is a bug on a screen made for designers.
//
// The track list is read from the ROBOT (its /music folder), so the picker
// can only ever offer files that are really on the card.
let musicList = null;        // null = never read, [] = card has no tracks
let musicNote = "";          // why the list is not usable, in plain words
let musicBusy = false;
function robotLinked() { return haveRobot(); }
const musOpen = new Set();   // which keyframes have the picker open

function keyCue(k, key) {
  const c = (k.cues || []).find(x => x.toLowerCase().startsWith(key + ":"));
  return c ? c.slice(c.indexOf(":") + 1).trim() : "";
}
function setKeyCue(k, key, val) {
  // other cue lines (rgb:, effect:, a step this editor does not know) are
  // kept exactly as they came in - this only ever rewrites the one key
  const rest = (k.cues || []).filter(x => !x.toLowerCase().startsWith(key + ":"));
  k.cues = val === "" ? rest : rest.concat(key + ": " + val);
  if (!k.cues.length) delete k.cues;
  bumpKeys();
}
// A play cue is `play: song.mp3` or `play: song.mp3 LOOP` — the file's own
// words, kept verbatim, so the repeat travels with the sequence and every way of
// running it obeys (the hub, the module's page, Run on robot). These two read the
// halves apart; a track name may contain spaces, so only a trailing LOOP counts.
function cueTrack(k) {
  return keyCue(k, "play").replace(/\s+LOOP$/i, "");
}
function cueLoop(k) {
  return /\s+LOOP$/i.test(keyCue(k, "play"));
}
function setCueTrack(k, track, loop) {
  setKeyCue(k, "play", track ? track + (loop ? " LOOP" : "") : "");
}
async function loadMusicList() {
  if (musicBusy || musicList) return;
  musicBusy = true;
  musicNote = "reading the robot's music folder…";
  try {
    // Any link will do. liveLinked() also needs the live tick, so with it off the
    // picker stayed locked and the volume with it (A26-49).
    if (!robotLinked()) throw new Error("offline");
    const r = await fetch("/api/dev/files?dir=/music&dev="
                          + encodeURIComponent(moduleDev()));
    const list = await r.json();
    musicList = list.map(f => f.n).filter(n => /\.(mp3|wav)$/i.test(n));
    musicNote = musicList.length ? "" :
      "no tracks on the robot's card yet — add one in the hub: " +
      "Modules ▸ Open module ▸ Files ▸ /music";
  } catch (e) {
    musicList = null;
    musicNote = "connect the robot to choose a track — it reads the /music "
              + "folder on its own card. What is already set is kept.";
  }
  musicBusy = false;
  renderTimeline();
}
// Put a track from THIS PC onto the robot's card, then choose it. Music is
// binary, so it cannot go through sdUpload() (that one encodes text) - it
// goes as raw bytes through the hub, which already knows how to reach this
// module over WiFi or down a cable. A browser holding the cable itself
// (Web Serial) has no hub path, and says so rather than failing quietly.
// `pick(name, whyNot)` chooses the track once it is on the card; by default it
// goes on keyframe k. A failed upload calls it with no name and the reason. The Shows tab passes its own, so a show's track comes the same way.
async function pickMusicFile(k, pick) {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = ".mp3,.wav,audio/mpeg,audio/wav";
  inp.onchange = () => {
    const f = inp.files && inp.files[0];
    if (f) uploadMusicFile(k, f, pick);
  };
  inp.click();
}
// The upload itself, given a file: separate from the dialog because a file
// picker cannot be opened by a script, and an upload path no check can reach
// is an upload path nothing guards.
// The robot's card takes a track name of English letters, digits, space, dot,
// _ and - only (the hub's SAFE_NAME, and the firmware's command line). A Thai
// name was refused, so it is renamed here and the new name is said out loud
// (user 2026-09-27, ฟอนลองแมปง.mp3). What is left of the name is kept; a name
// with nothing left becomes track-<month><day>-<hour><minute>.
function robotTrackName(name) {
  const ok = /^[A-Za-z0-9._ -]{1,80}$/;
  if (ok.test(name) && name[0] !== ".") return name;
  const dot = name.lastIndexOf(".");
  const ext = dot > 0 ? name.slice(dot).replace(/[^A-Za-z0-9.]/g, "") : "";
  let base = (dot > 0 ? name.slice(0, dot) : name).replace(/[^A-Za-z0-9._ -]+/g, "")
    .replace(/^[ ._-]+|[ .]+$/g, "");
  if (!/[A-Za-z0-9]/.test(base)) {
    const d = new Date(), two = n => String(n).padStart(2, "0");
    base = "track-" + two(d.getMonth() + 1) + two(d.getDate()) + "-" + two(d.getHours()) + two(d.getMinutes());
  }
  return (base.slice(0, 80 - ext.length) + ext);
}
async function uploadMusicFile(k, f, pick) {
  if (usbDirect()) {
    musicNote = "this browser is holding the cable itself, so the hub cannot "
              + "send the file. Connect through the hub, or add the track on "
              + "the module website: Files ▸ /music.";
    if (pick) pick("", musicNote);
    renderTimeline();
    return;
  }
  const stop = why => { musicNote = why; if (pick) pick("", why); renderTimeline(); };
  // LOGGED OUT BY A HUB RESTART. Sessions live in the hub's memory, so a
  // restarted hub refuses the upload - and a refused body over 4 MB is not
  // read (DRAIN_LIMIT), so the browser only saw "Failed to fetch" instead of
  // the reason (user 2026-09-27, a 4.2 MB mp3). Ask first, say it plainly.
  try {
    const w = await fetch("/api/whoami").then(r => r.json());
    if (!w.authed) {
      currentUser = null;              // the page still thought it was logged in
      showTab("robot");                // which opens the login card
      return stop("log in again first — the hub was restarted or your login ran "
        + "out. Log in on the card that just opened, then add the track again.");
    }
  } catch (e) { /* no answer: let the upload itself say what is wrong */ }
  const name = robotTrackName(f.name);
  const renamed = name !== f.name ? " (saved on the robot as " + name + " — its card "
    + "only takes English letters and numbers in a name)" : "";
  musicNote = "sending " + f.name + " to the robot…";
  if (pick && pick.busy) pick.busy(musicNote);
  renderTimeline();
  try {
    // The HUB sends it, on its own thread (background=1), and this page
    // watches /api/upload/progress. Over a cable a song is tens of thousands
    // of 120-byte commands; one request held open that long does not survive.
    const r = await fetch("/api/dev/upload?background=1&dir=/music&name="
                          + encodeURIComponent(name) + "&dev="
                          + encodeURIComponent(moduleDev()),
                          { method: "POST", body: await f.arrayBuffer() });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.error || j.ok === false)
      throw new Error(j.need_login ? "log in first" : (j.error || "HTTP " + r.status));
    const end = await watchUpload(name);
    if (end.error) throw new Error(end.error);
    musicList = null;                   // the card has one more file on it now
    await loadMusicList();
    if (pick) pick(name, "", renamed); else setKeyCue(k, "play", name);
    musicNote = name + " is on the robot's card — press ▶ to hear it" + renamed;
  } catch (e) {
    musicNote = "the track did not reach the robot: " + (e.message || e);
    if (pick) pick("", musicNote);
  }
  renderTimeline();
}
// The wheel. A modal <dialog> over the whole page (user 2026-09-27: *show the
// wheel, how many percent, and say nothing else can be done - only send*):
// the robot's line is busy with the file, so anything clicked meanwhile would
// only queue behind it. Cancel is the one way out; the hub then removes the
// half-written file so a cut-off song is never left on the card.
function watchUpload(name) {
  let dlg = $("uploadDlg");
  if (!dlg) {
    dlg = document.createElement("dialog");
    dlg.id = "uploadDlg"; dlg.className = "askdlg updlg";
    dlg.setAttribute("aria-labelledby", "uploadTitle");
    dlg.innerHTML = '<h2 id="uploadTitle">Sending music to the robot</h2>'
      + '<div class="upwheel" id="uploadWheel" role="progressbar" aria-valuemin="0" '
      + 'aria-valuemax="100"><span id="uploadPct">0%</span></div>'
      + '<p class="mini" id="uploadText"></p>'
      + '<p class="mini">Please wait. Nothing else can be done until it is sent — '
      + 'the robot is busy taking the file.</p>'
      + '<div class="row"><button id="uploadCancel">Cancel sending</button></div>';
    document.body.appendChild(dlg);
  }
  const mb = n => (n / 1048576).toFixed(1) + " MB";
  return new Promise(resolve => {
    let done = false;
    const finish = s => { if (done) return; done = true; clearInterval(t); dlg.close(); resolve(s); };
    $("uploadCancel").disabled = false;
    $("uploadCancel").onclick = () => {
      $("uploadCancel").disabled = true;
      $("uploadText").textContent = "cancelling — taking the half-sent file back off the card…";
      fetch("/api/upload/cancel", { method: "POST" }).catch(() => {});
    };
    dlg.oncancel = e => e.preventDefault();          // Escape does not hide it
    const tick = async () => {
      let s;
      try { s = await fetch("/api/upload/progress").then(r => r.json()); }
      catch (e) { return; }                          // one missed poll is not an error
      const pct = s.total ? Math.floor(100 * s.sent / s.total) : 0;
      $("uploadWheel").style.setProperty("--p", pct);
      $("uploadWheel").setAttribute("aria-valuenow", pct);
      $("uploadPct").textContent = pct + "%";
      // time left from the speed so far - only once there is a speed to go on
      const secs = (Date.now() / 1000) - (s.started || 0);
      const left = s.sent > 0 && secs > 2 ? (s.total - s.sent) / (s.sent / secs) : 0;
      if (!$("uploadCancel").disabled)
        $("uploadText").textContent = name + " — " + mb(s.sent) + " of " + mb(s.total)
          + (left ? ", about " + (left >= 90 ? Math.round(left / 60) + " min" : Math.round(left) + " s") + " left" : "");
      if (!s.running) finish(s);
    };
    const t = setInterval(tick, 500);
    dlg.showModal();
    tick();
  });
}

// The picker for one keyframe: a track and a level, or plain words about why
// the list is not there. Shown when the ♪ is pressed, and whenever the move
// already has music - a show's sound must be visible without hunting for it.
function musicRow(k, i) {
  const row = document.createElement("div");
  row.className = "ktime kmusrow";
  const cur = cueTrack(k);
  const sel = document.createElement("select");
  sel.className = "kmustrack";
  sel.setAttribute("aria-label", "music for move " + (i + 1));
  const names = musicList ? musicList.slice() : [];
  if (cur && names.indexOf(cur) < 0) names.push(cur);   // keep what is set
  [["", "no music"]].concat(names.map(n => [n, n])).forEach(([v, label]) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = label;
    if (v === cur) o.selected = true;
    sel.appendChild(o);
  });
  sel.disabled = !musicList && !cur;
  sel.title = musicList ? "the tracks on the robot's card"
                        : "the robot's track list could not be read";
  sel.onchange = () => {
    // keep the repeat when only the track changes, or ticking it then picking a
    // different song would quietly untick it again
    setCueTrack(k, sel.value, cueLoop(k));
    if (!sel.value) setKeyCue(k, "vol", "");   // no track, no level
    renderTimeline();
  };
  const vol = document.createElement("input");
  vol.type = "number"; vol.min = 0; vol.max = 100; vol.step = 5;
  vol.className = "kmusvol";
  vol.value = keyCue(k, "vol");
  vol.placeholder = "vol";
  vol.disabled = !cur;
  vol.title = cur ? "volume for this track, 0-100"
                  : "choose a track first, then set its volume";
  vol.onchange = () => {
    const v = vol.value === "" ? "" : String(Math.max(0, Math.min(100, Math.round(+vol.value || 0))));
    setKeyCue(k, "vol", v);
    renderTimeline();
  };
  // Repeat. Asked for 2026-09-10: *make can loop the music of that sequence
  // when select that sequence to run*. It is written into the sequence FILE, so
  // it holds however the show is started.
  const rep = document.createElement("label");
  rep.className = "kmusloop";
  const repChk = document.createElement("input");
  repChk.type = "checkbox";
  repChk.checked = cueLoop(k);
  repChk.disabled = !cur;
  rep.title = cur ? "Keep playing this track again and again until the show "
                    + "ends or you press Stop. It restarts in a blink, not as a "
                    + "seamless join."
                  : "choose a track first, then it can repeat";
  repChk.onchange = () => { setCueTrack(k, cur, repChk.checked); renderTimeline(); };
  rep.append(repChk, document.createTextNode(" repeat"));
  // Hear it, and add one — both from here, because the two things a person
  // wants while choosing music are to LISTEN to it and to put a new track on
  // the robot, and neither was worth walking to another page for.
  const play = document.createElement("button");
  play.type = "button"; play.className = "kmusbtn"; play.textContent = "▶";
  play.disabled = !cur || !robotLinked();
  play.title = !robotLinked() ? "connect the robot to hear it"
             : cur ? "play " + cur + " on the robot now, once through"
                   : "choose a track first";
  play.onclick = async () => {
    const v = keyCue(k, "vol");
    try {
      if (v !== "") await rawCmd("VOL " + v);
      musicNote = await rawCmd("PLAY " + cur);
    } catch (e) { musicNote = "the robot did not take it: " + (e.message || e); }
    renderTimeline();
  };
  const stop = document.createElement("button");
  stop.type = "button"; stop.className = "kmusbtn"; stop.textContent = "■";
  stop.disabled = !robotLinked();
  stop.title = "stop the sound";
  stop.onclick = async () => {
    try { musicNote = await rawCmd("PLAY STOP"); } catch (e) { musicNote = String(e.message || e); }
    renderTimeline();
  };
  const add = document.createElement("button");
  add.type = "button"; add.className = "kmusbtn"; add.textContent = "＋";
  add.disabled = !robotLinked();
  add.title = robotLinked() ? "put a track from this PC onto the robot's card"
                           : "connect the robot to add a track";
  add.onclick = () => pickMusicFile(k);
  row.append(document.createTextNode("♪"), sel, vol, rep, play, stop, add);
  if (musicNote) {
    const n = document.createElement("span");
    n.className = "kmusnote";
    n.textContent = musicNote;
    row.appendChild(n);
  }
  return row;
}

function parseSeqYaml(text) {
  const out = { name: "", loop: false, next: "", speed: 0, keys: [], skipped: 0, cues: 0 };
  let curSpeed = 0;             // the speed in force at this point in the file
  // Non-pose steps (`play:`, `vol:`, `rgb:`) are CUES: kept in the editor's
  // own words and handed back to the file and to the hub, so a show edited
  // here keeps its music instead of losing it on the way through (A24-22).
  let pend = [];
  // buildYaml writes a move's name as an indented comment line above it. It
  // was thrown away with every other comment, so reopening a saved YAML lost
  // every move name. File-level comments (column 0) are not names.
  let pendName = "";
  for (const raw of text.split(/\r?\n/)) {
    const nm = raw.match(/^\s+#\s*(.*?)\s*$/);
    if (nm) { pendName = nm[1]; continue; }
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
        // A time from the FILE is deliberately NOT pinned. Pinning it was
        // tried on 2026-09-23 and broke the thing every sequence relies on:
        // changing Show speed re-times a loaded sequence, which is what makes
        // a re-edit follow the new pace (check_sequences, "leaves its
        // neighbours alone"). A pin is for a time THIS person typed or pinned
        // in THIS session - that is what was asked for, and no more. Anyone
        // who wants a loaded time held presses the pin on it, once.
        // a speed step before this pose that differs from the sequence speed is
        // that MOVE's own speed, so it survives a round trip through the file
        if (curSpeed && curSpeed !== out.speed) k.dps = curSpeed;
        if (pend.length) { k.cues = pend; out.cues += pend.length; pend = []; }
        if (pendName) k.name = pendName;
        pendName = "";
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
    } else if ((m = line.match(/^\s*-\s*([A-Za-z_][\w-]*):\s*"?(.*?)"?\s*$/))) {
      pend.push((m[1].toLowerCase() + ": " + m[2]).trim());
    } else if (/^\s*-\s/.test(line)) out.skipped++;   // not a step we can read
  }
  // cues after the last pose belong to the end of the show
  if (pend.length && out.keys.length) {
    out.keys[out.keys.length - 1].cuesAfter = pend;
    out.cues += pend.length;
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
  if (p.name) $("projName").value = p.name;
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  $("tlStat").textContent = `loaded ${keys.length} keyframes from ${sourceLabel}` +
    (p.speed >= 5 ? ` at its own ${Math.round(p.speed)} °/s` : "") +
    (p.cues ? ` with ${p.cues} music/light step(s), which play with the show and are written back on export` : "") +
    (p.skipped ? ` (${p.skipped} step(s) this editor does not read — kept only in the original file)` : "") +
    " — edit, then Save";
  // Just opened = matches the file. From the robot's SD it is not a file on
  // this PC, so saving it here still asks before replacing one.
  const local = sourceLabel.startsWith("sequences/")
    ? sourceLabel.slice(10).replace(/\.yaml$/, "") : "";
  markSaved(workSig(), local, p.skipped || 0);
}
async function editLocalSeq() {
  const f = $("seqList").value;
  if (!f) return;
  if (!(await askUnsaved("open " + f))) return;
  // A missing file must say so: its 404 body parsed as YAML reported
  // "no pose steps found", which reads like an empty sequence, not a wrong one.
  const r = await fetch("/api/loadseq?name=" + encodeURIComponent(f));
  if (!r.ok) {
    $("tlStat").textContent = "cannot read sequences/" + f + " — the hub answered "
      + r.status + ". Pick it in the list again, or refresh.";
    notice($("tlStat").textContent);
    return;
  }
  loadParsedSeq(parseSeqYaml(await r.text()), "sequences/" + f);
}
async function editSdSeq(fname) {
  if (!(await askUnsaved("open " + fname + " from the robot"))) return;
  try {
    const text = await sdDownload(fname);
    loadParsedSeq(parseSeqYaml(text), "robot SD " + fname);
  } catch (e) { $("tlStat").textContent = "cannot read " + fname + ": " + (e.message || e); notice($("tlStat").textContent); }
}
// Play a SAVED sequence without first loading it for editing: the same
// loader Edit uses, then the same Play button — so it plays exactly like an
// edited sequence, through whichever clock applies (hub when hub-driven).
async function playSavedSeq(sourceLabel, getText) {
  const stat = $("tlStat");
  stat.textContent = "loading " + sourceLabel + "…";
  let text;
  try { text = await getText(); }
  catch (e) {
    stat.textContent = "cannot read " + sourceLabel + ": " + (e.message || e);
    notice(stat.textContent);
    return;
  }
  if (!(await askUnsaved("play " + sourceLabel))) { stat.textContent = ""; return; }
  if (playing) togglePlay();          // swap timelines only while stopped
  const before = keys;
  loadParsedSeq(parseSeqYaml(text), sourceLabel);
  if (keys === before) return;        // nothing loaded — its message is shown
  playT = 0;                          // a fresh show starts at the top
  $("scrub").value = 0;
  togglePlay();
}
async function playLocalSeq() {
  const f = $("seqList").value;
  if (!f) { $("tlStat").textContent = "pick a saved sequence in the list first."; return; }
  await playSavedSeq("sequences/" + f, async () => {
    const r = await fetch("/api/loadseq?name=" + encodeURIComponent(f));
    if (!r.ok) throw new Error("the hub answered HTTP " + r.status
      + " — is sequences/" + f + " still there?");
    return r.text();
  });
}
async function playSdSeq(fname) {
  await playSavedSeq("robot SD " + fname, () => sdDownload(fname));
}
// Delete a saved YAML (user 2026-09-17). The hub moves it to
// sequences/.deleted/, so a mis-click can still be undone by hand.
// The picked PC file onto the robot, as it is (A44-3, user 2026-10-19: make
// sending or updating moves on the nong easy). No timeline is opened, so
// nothing unsaved is at risk; the same name on the robot is replaced.
async function putLocalSeqOnRobot() {
  const f = $("seqList").value;
  if (!f) { $("tlStat").textContent = "pick a saved YAML in the list first."; return; }
  if (!haveRobot()) {
    $("tlStat").textContent = "connect to the robot first (Robot tab).";
    notice($("tlStat").textContent);
    return;
  }
  try {
    const r = await fetch("/api/loadseq?name=" + encodeURIComponent(f));
    if (!r.ok) throw new Error("cannot read sequences/" + f + " (the hub answered " + r.status + ")");
    $("tlStat").textContent = "saving " + f + " on the robot…";
    await sdUpload(f, await r.text());
    $("tlStat").textContent = f + " is saved on the robot. It can play it by itself now, "
      + "from the robot's list here or on its own page.";
    refreshSd();
  } catch (e) {
    $("tlStat").textContent = f + " was not saved on the robot: " + (e.message || e);
    notice($("tlStat").textContent);
  }
}
async function deleteLocalSeq() {
  const f = $("seqList").value;
  if (!f) { $("tlStat").textContent = "pick a saved YAML in the list first."; return; }
  if (!confirm("Delete " + f + "?\n\nIt is moved to sequences/.deleted on this PC, not erased.")) return;
  try {
    const r = await fetch("/api/seqdelete", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: f }) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.ok) throw new Error(j.need_login ? "log in first" : (j.error || "HTTP " + r.status));
    $("tlStat").textContent = f + " deleted (kept in sequences/.deleted).";
    await refreshSeqs();
    seqsChanged();
  } catch (e) {
    $("tlStat").textContent = "could not delete " + f + ": " + (e.message || e);
    notice($("tlStat").textContent);
  }
}
async function refreshSeqs() {
  const r = await fetch("/api/list?kind=sequences").then(r => r.json());
  const sel = $("seqList");
  sel.innerHTML = "<option value=''>Open saved YAML…</option>";
  (r.files || []).filter(f => f.endsWith(".yaml")).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}
// --- project save/load ---
// opts.keepDraft: saveAll() clears the draft itself, only once BOTH files are
// on disk. Returns true when the project reached the disk.
async function saveProject(opts) {
  opts = opts || {};
  const name = ($("projName").value || "project").trim();
  const sig = workSig();                  // what THIS save writes, before any await
  const project = {
    keys, speedDps: speedDps(), maxDps: maxDps(), loop: $("loopChk").checked,
    // The planning peak limit rides with the project: without it, reopening a
    // project re-times every automatic move against a different 60 °/s default
    // and the show quietly got slower (A31-4).
    safeDps: SAFE_DPS,
    meshes: meshCfg, addons,
    robotIp: $("robotIp").value, seqName: $("projName").value,   // kept: older Studios read it
    // The chain is part of the show: a project saved with one and reopened
    // without it exported a different sequence than the one saved.
    seqNext: ($("seqNext").value || "").trim(),
    rig: RIG,
    // The video the moves were made from, and how (A44-8); null if none.
    video: vidSettings(),
  };
  // The draft is NOT cleared on a failure: the work is still only in this
  // browser. Mice.Api never throws, and words both "no answer" and "said no".
  const a = await Mice.Api.post("/api/save", { name, project });
  if (!a.ok) {
    $("tlStat").textContent = (a.status
      ? "could not save: " + a.says + ". Your work is still here."
      : "could not save — the hub is not answering. Your work is still here, "
        + "and is kept in this browser.");
    notice($("tlStat").textContent);
    return false;
  }
  const r = a.data;
  // Safely on disk now, so the unsaved-work draft has done its job.
  if (!opts.keepDraft) markSaved(sig, name);
  $("tlStat").textContent = r.replaced
    ? "saved over the existing " + r.file + " (the previous version is kept as "
      + r.file + ".bak)"
    : "project saved: " + r.file;
  refreshProjects();
  return true;
}
async function loadProject(file) {
  if (!file) return;
  if (!(await askUnsaved("open " + file))) {
    if ($("projList")) $("projList").value = "";
    return;
  }
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
  const a = await Mice.Api.get("/api/load?name=" + encodeURIComponent(file));
  if (!a.ok) {
    const st = $("tlStat");
    if (st) st.textContent = "could not load " + file + " — " + a.says
      + ". Nothing on screen was changed.";
    return;                              // the timeline stays exactly as it was
  }
  const p = a.data;
  if (!Array.isArray(p.keys)) {
    const st = $("tlStat");
    if (st) st.textContent = file + " has no keyframes in it, so nothing was loaded.";
    return;
  }
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
  // The rig is swapped BEFORE the poses are clamped: clamping first cut every
  // pose to the OLD rig's limits, so taking a project's wider rig still
  // opened a project whose moves had been silently shortened.
  if (p.rig && takeRig) {
    // Keep one step back. The rig is the most expensive thing in this editor
    // to rebuild, so replacing it always leaves a copy to return to.
    try { localStorage.setItem("nong_rig_prev", JSON.stringify(RIG)); }
    catch (e) { /* storage full: the swap still happens, just without undo */ }
    RIG = mergeRig(p.rig);
    saveRig();
  }
  // Repair the poses BEFORE they reach anything: pad short ones to NJ, drop
  // non-numbers, and clamp to each joint's real travel. A missing or broken
  // time or hold becomes 0 (clampKeyTimes raises it to the floor), never NaN,
  // which would reach the robot as "T NaN".
  const loaded = p.keys.filter(k => k && Array.isArray(k.pose)).map(k => {
    const q = k.pose.slice(0, NJ).map(Number);
    while (q.length < NJ) q.push(90);    // pre-WAIST/SHRUG project: neutral
    const t = Number(k.t), hold = Number(k.hold);
    return { ...k, pose: q.map((v, i) => clampJ(i, Number.isFinite(v) ? v : 90)),
             t: Number.isFinite(t) ? Math.max(0, Math.round(t)) : 0,
             hold: Number.isFinite(hold) ? Math.max(0, Math.round(hold)) : 0 };
  });
  keys = loaded;
  bumpKeys();
  $("speedDps").value = p.speedDps || 120;
  $("maxDps").value = p.maxDps || 400;
  // A connected board's own limit still wins: adoptBoardSafety runs on connect
  // and overwrites this. Saved projects only decide what Studio plans with
  // while no robot is telling it otherwise.
  if (p.safeDps >= 5 && !boardSafeDpsMax) {
    SAFE_DPS = Math.round(p.safeDps);
    $("safeDpsInput").value = String(SAFE_DPS);
  }
  clampKeyTimes();
  $("loopChk").checked = !!p.loop;
  $("robotIp").value = p.robotIp || "";
  // ONE name for both files (A31-18): the project and its YAML now save
  // together, under the project's name.
  const pname = file.replace(/\.json$/, "");
  const oldSeq = (p.seqName || "").trim();
  setWorkName(pname);
  // The chain rides with the project; an older project without one clears the
  // field rather than keeping a chain this project never had.
  $("seqNext").value = p.seqNext || "";
  vidApplySettings(p.video);
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
  // What was opened, taken before the awaits below: an edit made while the
  // models load is the person's new work, never "saved".
  const openedSig = workSig();
  await refreshModels();
  renderRigUI();
  buildRobot(); // re-applies meshes + rig in one pass
  selKey = 0;
  if (keys.length) { pose = [...keys[0].pose]; }
  poseChanged(false); renderTimeline();
  // Only a project whose YAML already had its own name owns NAME.yaml; for any
  // other, Save still asks before replacing a NAME.yaml that is somebody else's.
  markSaved(openedSig, oldSeq === pname ? pname : "", 0);
  if (oldSeq && oldSeq !== pname)
    $("tlStat").textContent = "opened " + file + ". It used to save its moves as "
      + oldSeq + ".yaml; Save now writes " + pname + ".json and " + pname + ".yaml together.";
}

// ---- one Save, and a question before unsaved work is replaced (A31-18) ----
//
// User 2026-09-23: *why we not make it same thing* - the project (.json: the
// editable work + rig) and the sequence (.yaml: what the robot plays) had two
// buttons and two name boxes, so one was always behind the other. And opening
// another file replaced the timeline without a word: *i loss it a lot of time*.
// Now: one name, one Save that writes both, and every loader asks first.
// Settings ▸ Saving switches the question off.
let savedSig = null;       // workSig() of what is on disk; null until boot ends
let savedName = "";        // the file the timeline came from or last went to
let loadedSkipped = 0;     // steps that file holds which this editor cannot read
function workSig() {
  return keysSignature() + "|" + (($("loopChk") && $("loopChk").checked) ? 1 : 0)
    + "|" + (($("seqNext") && $("seqNext").value) || "").trim();
}
// The page now matches a file on disk. markClean leaves an earlier session's
// draft alone; only a real save or load (markSaved) retires it.
function markClean(sig, name) {
  savedSig = sig;
  if (name != null) savedName = name;
}
function markSaved(sig, name, skipped) {
  markClean(sig, name);
  if (skipped != null) loadedSkipped = skipped;
  // an edit made while the save was on the wire is still unsaved
  try { if (workSig() === sig) localStorage.removeItem(DRAFT_KEY); }
  catch (e) { /* nothing to do */ }
}
function isDirty() {
  if (savedSig === null || !keys.length) return false;   // nothing to lose
  return workSig() !== savedSig;
}
const ASK_UNSAVED_KEY = "nong_ask_unsaved";
function askUnsavedOn() {
  try { return localStorage.getItem(ASK_UNSAVED_KEY) !== "0"; }
  catch (e) { return true; }
}
function setAskUnsaved(on) {
  try { localStorage.setItem(ASK_UNSAVED_KEY, on ? "1" : "0"); }
  catch (e) { /* kept for this visit only */ }
}
function cleanName(v) { return (v || "").trim().replace(/[^\w.-]+/g, "_"); }
function setWorkName(v) {
  const n = cleanName(v);
  if ($("projName")) $("projName").value = n;
}
// Save = the project (.json) AND the robot's file (.yaml), under one name.
// True only when everything that should be on disk is.
async function saveAll() {
  const name = cleanName($("projName").value || "my_move");
  setWorkName(name);
  const sig = workSig();
  const writeYaml = playKeys().length > 0;
  // Every question comes BEFORE the first write, so Cancel leaves both files
  // exactly as they were.
  const have = [...$("seqList").options].map(o => o.value);
  if (writeYaml && name !== savedName && have.includes(name + ".yaml") &&
      !confirm(name + ".yaml is already saved. Replace it?\n\n" +
               "Cancel, then type a new name to keep both.")) {
    $("tlStat").textContent = "not saved — " + name + ".yaml was left as it was";
    return false;
  }
  if (writeYaml && name === savedName && loadedSkipped > 0 &&
      !confirm(name + ".yaml has " + loadedSkipped + " step(s) this editor cannot "
               + "read. Saving over it removes them.\n\nOK — save anyway\n"
               + "Cancel — keep the file; type a new name to save a copy")) {
    $("tlStat").textContent = "not saved — " + name + ".yaml was left as it was";
    return false;
  }
  // The name cannot change between the two writes: typing while the first
  // was on the wire sent the .yaml over a file nobody was asked about.
  const boxes = [$("projName")].filter(Boolean);
  boxes.forEach(b => { b.readOnly = true; });
  let ok = false;
  try {
    ok = (await saveProject({ keepDraft: true })) &&
         (!writeYaml || (await exportYaml({ noAsk: true, keepDraft: true })));
  } finally {
    boxes.forEach(b => { b.readOnly = false; });
  }
  if (!ok) return false;
  markSaved(sig, name, 0);
  $("tlStat").textContent = "saved " + name + " — " + name + ".json (to edit later)"
    + (writeYaml ? " and " + name + ".yaml (what the robot plays)"
                 : ". No .yaml: every move is suspended, so there is nothing to play");
  return true;
}
// Asks before something replaces the timeline. Resolves true to go ahead.
function askUnsaved(what) {
  if (!askUnsavedOn() || !isDirty()) return Promise.resolve(true);
  return new Promise(resolve => {
    let dlg = $("unsavedDlg");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.id = "unsavedDlg"; dlg.className = "askdlg";
      dlg.setAttribute("aria-labelledby", "unsavedTitle");
      dlg.innerHTML = '<h2 id="unsavedTitle">Save your changes first?</h2>'
        + '<p class="mini" id="unsavedText"></p>'
        + '<div class="row"><button class="primary" id="unsavedSave">Save, then continue</button>'
        + '<button class="danger" id="unsavedDrop">Don’t save</button>'
        + '<button id="unsavedCancel">Cancel</button></div>';
      // No "don't ask again" box here (user 2026-09-24): the switch lives
      // only in Settings ▸ Saving.
      document.body.appendChild(dlg);
    }
    $("unsavedText").textContent = "The moves on the time bar have changes that are "
      + "not saved" + (savedName ? " to " + savedName : "") + ". If you " + what
      + " now, they are replaced.";
    const done = async (how) => {
      dlg.close();
      resolve(how === "save" ? await saveAll() : how === "drop");
    };
    $("unsavedSave").onclick = () => done("save");
    $("unsavedDrop").onclick = () => done("drop");
    $("unsavedCancel").onclick = () => done("cancel");
    dlg.oncancel = (e) => { e.preventDefault(); done("cancel"); };   // Escape
    dlg.showModal();
    $("unsavedCancel").focus();          // the safe answer is the default
  });
}
function syncAskUnsavedBox() {
  const box = $("askUnsavedChk");
  if (box) box.checked = askUnsavedOn();
}
syncAskUnsavedBox();
async function refreshProjects() {
  const a = await Mice.Api.get("/api/list?kind=projects");
  if (!a.ok) return;                     // keep the list it already shows
  const r = a.data;
  const sel = $("projList");
  sel.innerHTML = "<option value=''>Load…</option>";
  (r.files || []).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}
// --- the head's status line (A41-4) ---
// Whether the moves on screen are on disk, in the one status line every hub
// page has (Mice.Status, docs/web_style.md). Save and load still write their
// detail to the timeline's own line; this says only saved / not saved.
// Read once a second: isDirty() is one string compare, and the line is only
// rewritten when its words change, so a screen reader is not told every tick.
const headStat = new Mice.Status("stat");
let headSaid = "";
function showSaveState() {
  let kind, says, tech = "";
  if (savedSig === null) { kind = "loading"; says = "opening…"; }
  else if (isDirty()) { kind = "warn"; says = "not saved"; }
  else if (savedName) {
    kind = "ready"; says = "saved";
    tech = savedName + ".json + " + savedName + ".yaml";
  } else { kind = "empty"; says = keys.length > 1 ? "not saved" : "nothing to save yet"; }
  const now = kind + says + tech;
  if (now === headSaid) return;
  headSaid = now;
  headStat[kind](says, tech);
}
showSaveState();
setInterval(showSaveState, 1000);
// --- STL meshes ---
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
    () => { $("tlStat").textContent = "cannot load models/" + file; notice($("tlStat").textContent); });
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
// --- URDF import ---
//
// User 2026-09-23: *we already have all step file when i drag it cannot be as
// my aspect make can use urdf too*.
//
// A STEP file is a solid-modelling format. A browser cannot open one, and an
// STL dragged in on its own carries no origin at all - so every part landed at
// the middle of the robot and had to be rotated, offset and scaled by hand
// until it looked right. That is what "cannot be as my aspect" was.
//
// A URDF carries exactly the numbers that were missing: where each part sits,
// which way it is turned, how big it is, and which part hangs off which. So
// importing one fills the boxes in instead of leaving them to be guessed.
//
// WHAT IS SETTABLE, BECAUSE NO TWO EXPORTS AGREE:
//   * units. URDF is metres; Studio is millimetres. SolidWorks' sw2urdf writes
//     its STL meshes in metres too, so the default is x1000 for both.
//   * which way is up. URDF/ROS is Z-up X-forward; this editor is Y-up
//     Z-forward. The default mapping is that one, and it can be changed
//     without editing code - a CAD export that was built Y-up already would
//     otherwise arrive lying on its side with no way to say so.
//   * which link is which part. An export names links after SolidWorks
//     components, so the names are guessed and then shown for correction.
// None of it is hidden: the import says what it matched, what it could not,
// and what it changed.

const URDF_DEF = { mm: 1000, up: "z" };
let urdfDoc = null;         // the parsed file, kept so a re-map costs no re-read
let urdfMap = {};           // link name -> Studio part ("" = not used)
let urdfName = "";

// Guesses a Studio part from a link name. DATA, not code: the next naming
// habit is one more row here and nothing else.
const URDF_GUESS = [
  [/(^|[_\- ])(l|left)([_\- ]|$).*(upper|shoulder|humerus)/i, "L_upper"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(upper|shoulder|humerus)/i, "R_upper"],
  [/(^|[_\- ])(l|left)([_\- ]|$).*(fore|lower|elbow|radius)/i, "L_fore"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(fore|lower|elbow|radius)/i, "R_fore"],
  [/head|skull|face/i, "head"],
  [/torso|body|chest|trunk|base/i, "torso"],
];
function urdfGuessPart(link) {
  for (const [re, part] of URDF_GUESS) if (re.test(link)) return part;
  return "";
}

function urdfNums(el, attr, fallback) {
  const raw = el && el.getAttribute(attr);
  if (!raw) return fallback.slice();
  const n = raw.trim().split(/\s+/).map(Number);
  return n.length === 3 && n.every(Number.isFinite) ? n : fallback.slice();
}

// URDF axes -> this editor's axes. ROS is Z-up X-forward; three.js here is
// Y-up Z-forward, so (x, y, z) becomes (y, z, x) - a cyclic swap, which keeps
// the handedness and therefore keeps every rotation turning the same way.
function urdfToStudioXYZ(v, up) {
  return up === "y" ? [v[0], v[1], v[2]] : [v[1], v[2], v[0]];
}
// The same swap for roll-pitch-yaw. URDF fixed-axis rpy is Rz(yaw)*Ry(pitch)*
// Rx(roll), which is THREE's Euler order "ZYX" with the SAME three numbers -
// so the only thing to do is move each number onto the axis it now turns
// about, and hand the result back in degrees, which is what meshCfg holds.
function urdfToStudioRPY(rpy, up) {
  const s = urdfToStudioXYZ(rpy, up);
  return s.map(r => Math.round(THREE.MathUtils.radToDeg(r) * 10) / 10);
}

// The one visual of a link, as {file, rot, off, scale}, or null when the link
// has no mesh (a URDF has plenty: bearings, frames, fasteners).
function urdfVisual(link, opt) {
  const vis = link.querySelector("visual");
  const mesh = vis && vis.querySelector("geometry mesh");
  if (!mesh) return null;
  const file = (mesh.getAttribute("filename") || "").split(/[\\/]/).pop();
  if (!file) return null;
  const org = vis.querySelector("origin");
  const off = urdfToStudioXYZ(urdfNums(org, "xyz", [0, 0, 0]), opt.up)
    .map(v => Math.round(v * opt.mm * 10) / 10);
  const rot = urdfToStudioRPY(urdfNums(org, "rpy", [0, 0, 0]), opt.up);
  // <mesh scale> is a per-axis scale; this editor has one number, so a mesh
  // scaled differently per axis is reported rather than silently flattened.
  const ms = urdfNums(mesh, "scale", [1, 1, 1]);
  const even = Math.abs(ms[0] - ms[1]) < 1e-9 && Math.abs(ms[1] - ms[2]) < 1e-9;
  return { file, off, rot, scale: ms[0] * opt.mm, even };
}

// Parse, and say what is in it. Never touches the rig: reading a file and
// changing the robot are two different decisions, and one button that does
// both cannot be undone halfway.
function urdfParse(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror"))
    throw new Error("this file is not valid XML, so it cannot be a URDF");
  const robot = doc.querySelector("robot");
  if (!robot) throw new Error("no <robot> in this file - is it a URDF?");
  const links = [...doc.querySelectorAll("robot > link")];
  if (!links.length) throw new Error("this URDF has no links in it");
  return { doc, robot, links,
           joints: [...doc.querySelectorAll("robot > joint")] };
}

// How long each mapped part's bar is, in mm. This is the number that makes an
// imported robot the right SIZE and not merely the right shape.
//
// A joint's origin is measured in its PARENT link's frame, so the length of a
// bar is the origin of the joint LEAVING it - the elbow's origin is the upper
// arm's length. Reading the joint that ARRIVES at a link instead gives the
// offset of the bar before it, which for this robot is the shoulder's own
// (0, 0, 0) - every arm then measured zero.
//
// Zero-length joints are skipped on purpose: a shoulder and an elbow are each
// two servos stacked at one origin, so half the joints in this tree carry no
// distance at all. A leaf link has no outgoing joint and so has no length
// here; its mesh is the only thing that says how long it is.
function urdfJointLengths(parsed, opt) {
  const out = {};
  parsed.joints.forEach(j => {
    const parent = j.querySelector("parent");
    if (!parent) return;
    const part = urdfMap[parent.getAttribute("link")];
    if (!part || out[part]) return;
    const v = urdfNums(j.querySelector("origin"), "xyz", [0, 0, 0]);
    const len = Math.round(Math.hypot(v[0], v[1], v[2]) * opt.mm * 10) / 10;
    if (len > 0) out[part] = len;
  });
  return out;
}

// ---- the screen -----------------------------------------------------------
async function importUrdf() {
  const f = $("urdfFile").files[0];
  if (!f) {
    $("urdfStat").textContent = "choose a .urdf file first. Its .stl meshes " +
      "must be imported too (Models > Import), or the parts have nothing to draw.";
    return;
  }
  try {
    const parsed = urdfParse(await f.text());
    urdfDoc = parsed;
    urdfName = f.name;
    urdfMap = {};
    parsed.links.forEach(l => {
      const name = l.getAttribute("name") || "";
      urdfMap[name] = urdfGuessPart(name);
    });
    renderUrdfUI();
    const matched = Object.values(urdfMap).filter(Boolean).length;
    $("urdfStat").textContent = `${f.name}: ${parsed.links.length} links, ` +
      `${parsed.joints.length} joints. ${matched} matched to a body part by ` +
      "name — check them below, then press Use this URDF.";
  } catch (e) {
    $("urdfStat").textContent = "could not read it: " + (e.message || e);
    notice($("urdfStat").textContent);
  }
}
function urdfOptions() {
  return { mm: +$("urdfMm").value || URDF_DEF.mm,
           up: $("urdfUp").value || URDF_DEF.up };
}
function renderUrdfUI() {
  const box = $("urdfLinks");
  if (!box) return;
  box.innerHTML = "";
  if (!urdfDoc) {
    box.innerHTML = "<div class='mini'>No URDF loaded yet.</div>";
    return;
  }
  const opt = urdfOptions();
  urdfDoc.links.forEach(l => {
    const name = l.getAttribute("name") || "";
    const vis = urdfVisual(l, opt);
    const row = document.createElement("div"); row.className = "row";
    const nm = document.createElement("span");
    nm.style.flex = "1"; nm.textContent = name;
    nm.title = vis ? "mesh: " + vis.file : "this link has no mesh to draw";
    const sel = document.createElement("select");
    sel.innerHTML = "<option value=''>(not used)</option>";
    MESH_PARTS.forEach(p => {
      const o = document.createElement("option"); o.value = o.textContent = p;
      if (urdfMap[name] === p) o.selected = true;
      sel.appendChild(o);
    });
    sel.disabled = !vis;
    sel.onchange = () => { urdfMap[name] = sel.value; };
    const note = document.createElement("span");
    note.className = "mini";
    note.textContent = vis ? (vis.even ? vis.file : vis.file + " ⚠ uneven scale")
                           : "no mesh";
    row.append(nm, sel, note);
    box.appendChild(row);
  });
}
// Apply it. Separate from reading the file on purpose: this is the step that
// changes what is on screen, and it says exactly what it changed.
function useUrdf() {
  if (!urdfDoc) { $("urdfStat").textContent = "load a .urdf file first."; return; }
  const opt = urdfOptions();
  const done = [], missing = [], uneven = [];
  urdfDoc.links.forEach(l => {
    const name = l.getAttribute("name") || "";
    const part = urdfMap[name];
    if (!part) return;
    const vis = urdfVisual(l, opt);
    if (!vis) return;
    if (!vis.even) uneven.push(vis.file);
    // The mesh file has to be in models/ already: a URDF names its meshes, it
    // does not carry them. Say which ones are absent instead of drawing
    // nothing and letting it read as a broken import.
    if (!modelFiles.some(f => f.toLowerCase() === vis.file.toLowerCase()))
      missing.push(vis.file);
    meshCfg[part] = { ...defMeshCfg(part), file: vis.file,
                      rot: vis.rot, off: vis.off, scale: vis.scale,
                      color: meshCfg[part].color };
    done.push(part);
  });
  if (!done.length) {
    $("urdfStat").textContent = "nothing was changed: no link is matched to a " +
      "body part yet. Pick a part beside a link above.";
    return;
  }
  // The joint origins are the real bar lengths. They are offered, not forced:
  // a rig that somebody measured by hand must not be overwritten by a CAD file
  // without being asked.
  const lens = urdfJointLengths(urdfDoc, opt);
  const dimOf = { L_upper: "upperLenL", R_upper: "upperLenR",
                  L_fore: "foreLenL", R_fore: "foreLenR" };
  const offer = Object.keys(lens).filter(p => dimOf[p] && lens[p] > 1);
  let sized = 0;
  if (offer.length && confirm(
      "Also set the arm lengths from this URDF?\n\n" +
      offer.map(p => "  " + dimOf[p] + ": " + RIG.dims[dimOf[p]] + " → " + lens[p] + " mm").join("\n") +
      "\n\nOK sets them. Cancel keeps the lengths you have.")) {
    offer.forEach(p => { RIG.dims[dimOf[p]] = lens[p]; sized++; });
  }
  saveMeshes();
  if (sized) rigChanged(); else buildRobot();
  renderModelsUI();
  $("urdfStat").textContent =
    `${urdfName}: placed ${done.length} part(s) — ${done.join(", ")}` +
    (sized ? `, and set ${sized} arm length(s)` : "") + ". " +
    (missing.length ? `Import these meshes too (Models > Import): ${missing.join(", ")}. ` : "") +
    (uneven.length ? `${uneven.join(", ")} is scaled differently on each axis; ` +
                     "this editor has one scale, so the first was used. " : "") +
    "Nothing else in the rig was touched.";
}
// --- robot link ---
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
  else if (direct && !("serial" in navigator)) {
    $("robotStat").textContent = "This browser cannot open a USB port by itself. "
      + "Pick “+ USB (shared)” instead — the hub opens the cable and shares it — "
      + "or connect over WiFi. (Web Serial works in Chrome and Edge.)";
    notice($("robotStat").textContent);
  }
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
// Studio and the robot must agree on joint limits, or a pose drawn at 25 deg
// is clamped to 30 on the arm and the two no longer match (user 2026-09-17).
// Says so on connect and offers both ways to fix it; which is right is the user's call.
async function checkLimitsMatch() {
  const box = $("limMismatch");
  if (!box) return;
  try {
    const j = JSON.parse(await rawCmd("LIMIT?"));
    const diff = [];
    for (let i = 0; i < NJ; i++) {
      const rmin = Array.isArray(j.min) ? Math.round(+j.min[i]) : null;
      const rmax = Array.isArray(j.max) ? Math.round(+j.max[i]) : null;
      if (rmin === null || rmax === null || isNaN(rmin) || isNaN(rmax)) continue;
      if (rmin !== Math.round(RIG.min[i]) || rmax !== Math.round(RIG.max[i]))
        diff.push(`${JOINT_LABELS[i]}: Studio ${Math.round(RIG.min[i])}–${Math.round(RIG.max[i])}°, robot ${rmin}–${rmax}°`);
    }
    box.hidden = !diff.length;
    $("limMismatchText").textContent = diff.length
      ? "Studio and the robot allow different joint angles, so the arm will not match the preview. " + diff.join(" · ")
      : "";
  } catch (e) { box.hidden = true; }            // an old board without LIMIT?: say nothing
}
// A USB-RS485 adapter has no board of its own: the nong answers only when
// addressed by its bus id. The id box is technical detail (hidden), so fill it
// from the hub's cable probe (user 2026-09-17: "no reply from COM12").
// The hub's cached answer first (instant while the cable is in use), the full
// bus census (~4.3 s on COM21, 2026-09-27) only when that knows no nong.
async function findBusId(port) {
  for (const full of [0, 1]) {
    try {
      const r = await fetch(`/api/scanusb?full=${full}&port=` + encodeURIComponent(port)).then(r => r.json());
      const u = (r.usb || [])[0] || {};
      if (u.module) return false;                            // a board on this cable itself
      const nongs = (u.rs485 || []).filter(m => m.type === "nong");
      if (!nongs.length) continue;
      $("busId").value = nongs[0].id;
      return true;
    } catch (e) { return false; }                            // no hub probe: id stays as typed
  }
  return false;
}
// The last bus id that answered on each port. Without it every page load
// started with the empty id: two unaddressed INFOs that an RS485 adapter can
// never answer, then the census - ~9 s before Connect worked (2026-09-27).
const BUS_KEY = "nongBusId:";
function rememberBusId(port) {
  try { if (port) localStorage.setItem(BUS_KEY + port, String(busId() || "")); } catch (e) {}
}
function recallBusId(port) {
  if (busId() || !port) return;
  try { const v = localStorage.getItem(BUS_KEY + port); if (v) $("busId").value = v; } catch (e) {}
}
async function hubUsbCmd(c) {
  if (!hubPort && !(window.HUB_PEER || window.HUB_VIA))
    throw new Error("the USB link is closed - press Connect again");
  // With a peer, the command has to go to the module behind the plugged-in
  // one's hotspot, and only the unified endpoint understands that: the hub
  // turns dev=usb:COM7@far-nong into REACH far-nong <command> down the cable.
  // Without a peer this stays on the endpoint it always used, so nothing about
  // the ordinary cable path changes.
  // /api/usb/cmd only ever means a port on THIS PC. A peer or another hub
  // needs the unified endpoint, which understands the whole dev string.
  const url = (window.HUB_PEER || window.HUB_VIA)
    ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/usb/cmd?port=${encodeURIComponent(hubPort)}` +
      `&id=${busId()}&c=${encodeURIComponent(c)}`;
  // Never wait forever: a request stuck behind a busy cable held one of the
  // browser's six connections to the hub, and six of them froze every other
  // fetch on the page.
  const r = await fetch(url, window.AbortSignal && AbortSignal.timeout
    ? { signal: AbortSignal.timeout(15000) } : {});
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
  notice($("robotStat").textContent);
}
// ONE command on the wire at a time. Two overlapping calls used to throw
// "WritableStream is locked" on the second getWriter(), leaving its waiter in
// the queue to swallow the FIRST command's reply - every later reply then
// went to the wrong caller. Replies carry no id, so order is the only match.
let serialChain = Promise.resolve();
function serialCmd(c, connection = {port:serialPort,id:busId()}) {
  const epoch=safeMotionEpoch;
  const run = serialChain.then(() => /^POSE\s/i.test(c) && epoch!==safeMotionEpoch
    ? 'ERR movement cancelled' : serialCmdNow(c,connection));
  serialChain = run.catch(() => {});
  return run;
}
function serialCmdNow(c, connection = {port:serialPort,id:busId()}) {
  return new Promise((res, rej) => {
    const port=connection.port;
    if (!port || !port.writable) return rej(new Error("USB not connected"));
    const id = connection.id;
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
    const drop = (e) => {
      const k = serialWaiters.indexOf(w);
      if (k >= 0) serialWaiters.splice(k, 1);
      rej(e);
    };
    try {
      const writer = port.writable.getWriter();
      writer.write(new TextEncoder().encode(framed + "\n"))
        .catch(drop).finally(() => writer.releaseLock());
    } catch (e) { drop(e); }
  });
}

// Transports are NOT exclusive: WiFi and USB/RS485 can be connected at the
// same time. Commands take the cable when it is open (lowest latency, works
// without any network) and WiFi otherwise; bulk SD file transfer prefers
// WiFi and falls back to the cable.
function usbDirect() { return !!(serialPort && serialPort.writable); }
function haveUsb() { return usbDirect() || !!hubPort; }
function haveWifi() { return !!robotIp(); }
function haveAuto() { return !!window.HUB_AUTO; }
function haveRobot() { return haveAuto() || haveUsb() || haveWifi(); }
// one call for "send this over the cable", whichever USB mode is connected
function cableCmd(c) { return usbDirect() ? serialCmd(c) : hubUsbCmd(c); }
async function autoFetch(what, params, options) {
  const q = new URLSearchParams(Object.assign({ dev: window.HUB_AUTO }, params || {}));
  const r = await fetch(`/api/dev/${what}?${q}`, options);
  if (!r.ok) {
    const body = await r.text();
    let msg = body;
    try { msg = JSON.parse(body).error || body; } catch (e) { /* plain text error */ }
    throw new Error(msg);
  }
  return r;
}
async function autoCmd(c) {
  return (await (await autoFetch("cmd", { c })).text()).trim();
}
async function httpCmd(c) {
  // Same over WiFi: wifi:<ip>@peer reaches a module on that board's hotspot.
  const url = (window.HUB_PEER || window.HUB_VIA)
    ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/robot/cmd?ip=${encodeURIComponent(robotIp())}&c=${encodeURIComponent(c)}`;
  return fetch(url).then(r => r.text());
}
async function rawCmd(c) { // reply text or throws
  if (haveAuto()) return autoCmd(c);
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
  if (haveAuto()) return window.HUB_AUTO;
  // The peer rides along. Without it this link opened the website of the
  // board on the CABLE while every command went to the module behind that
  // board's hotspot — two different robots, one screen, no warning.
  const at = window.HUB_PEER ? "@" + window.HUB_PEER : "";
  // The hub prefix goes back on FIRST: hub:<ip>/usb:COM7 is that port on the
  // other PC. Without it the same string names a local port and drives
  // whatever is plugged in here.
  const via = window.HUB_VIA || "";
  if (hubPort) return via + "usb:" + hubPort + (busId() ? ":" + busId() : "") + at;
  if (haveWifi()) return via + "wifi:" + robotIp() + at;
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
  const ip = document.getElementById("robotIp");
  const bus = document.getElementById("busId");
  if (port) port.addEventListener("change", () => clearHubTarget("you picked another cable"));
  if (mode) mode.addEventListener("change", () => clearHubTarget("you changed the connection"));
  if (ip) ip.addEventListener("input", () => clearHubTarget("you typed another WiFi address"));
  if (bus) bus.addEventListener("input", () => clearHubTarget("you typed another bus id"));
});

function clearHubTarget(why) {
  cancelSafeMotion(why);
  const hadAuto = window.HUB_AUTO;
  clearPeer(why);
  window.HUB_AUTO = "";
  if (hadAuto) routeNote("using the route you picked: " + why);
}
function clearPeer(why) {
  if (!window.HUB_PEER) return;
  window.HUB_PEER = "";
  routeNote("no longer aiming at the module behind the other one: " + why);
}
// Studio has no `log()`: these notes were written for one that never existed,
// so the typeof guard kept them silent. The Robot card's line is where every
// other route message goes; routine, so it is not a notice().
function routeNote(text) {
  const st = $("robotStat");
  if (st) st.textContent = "(" + text + ")";
}
function openModule() {
  if (!currentUser) {
    showTab("robot");
    $("loginStat").textContent = "Log in to configure the module.";
    return;
  }
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
    notice($("robotStat").textContent);
    return;
  }
  $("robotStat").textContent = "connect first — pick a USB port or find a module on WiFi";
  notice($("robotStat").textContent);
}
async function robotCmd(c) {
  if (!currentUser) return "";
  if (/^POSE\s/i.test(c)) return (await liveSend(c)) ? "OK checked movement finished" : "";
  if (/^(?:MOVE\s+)?STOP\s*$/i.test(c)) { await cancelSafeMotion("Stop"); return "OK stopped"; }
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
  if (haveAuto()) return (await autoFetch("status")).json();
  if (haveUsb()) {
    try { return JSON.parse(await cableCmd("INFO")); }
    catch (e) {
      // Ask again only when the board restarted mid-answer. "No reply" does
      // not get better by asking: it cost 2 s more per Connect on an adapter.
      if (!/restart|JSON|Unexpected/i.test(e.message || "")) throw e;
      return JSON.parse(await cableCmd("INFO"));
    }
  }
  if (haveWifi())
    return fetch("/api/robot/status?ip=" + encodeURIComponent(robotIp())).then(r => r.json());
  throw new Error("not connected");
}
async function saveSafetySpeed() {
  const stat = $("safeSpeedStat");
  const want = Number($("safeDpsInput").value);
  if (!Number.isInteger(want) || want < 5 || want > boardSafeDpsMax) {
    stat.textContent = `Enter a whole number from 5 to ${Math.floor(boardSafeDpsMax)} °/s.`;
    notice(stat.textContent);
    return;
  }
  try {
    // The route or board may have changed since Connect. Check the live board
    // again before saving a limit that will survive its next restart.
    const s = await getStatus();
    const m = s && s.module;
    const speeds = m && m.max_dps;
    const ceiling = Array.isArray(speeds) && speeds.length === NJ
      ? Math.min(...speeds.map(Number)) : 0;
    if (!s || s.type !== "nong" || !m || !(+m.safe_dps >= 5) || !(ceiling >= want))
      throw new Error("This board cannot use that limit. Reconnect and check its settings.");
    if (String(s.chip || s.id || "") !== boardSafeIdentity)
      throw new Error("The connected board changed. Reconnect before saving.");
    if (+m.safe_dps !== SAFE_DPS || ceiling !== boardSafeDpsMax) {
      adoptBoardSafety(m);
      throw new Error("Board settings changed. Review the active limit before saving.");
    }
    if (want === SAFE_DPS) {
      stat.textContent = `Already active at ${SAFE_DPS} °/s. No board setting changed.`;
      return;
    }
    const warning = `Save peak speed limit ${want} °/s to this board? ` +
      `It takes effect only after you restart the board. ` +
      (want > SAFE_DPS ? "Higher speed can cause harder impacts. " : "") +
      (boardSafePeer ? `Linked board #${boardSafePeer} must be set to the same limit before synchronized playback. ` : "") +
      "Check that every joint holds under load before running a show.";
    if (!confirm(warning)) return;
    const reply = await rawCmd(`CFG safe_dps ${want}`);
    if (!/^OK safe_dps=/.test(reply)) throw new Error(reply || "board did not confirm the setting");
    stat.textContent = `Saved ${want} °/s for next boot. Active limit is still ` +
      `${SAFE_DPS} °/s. Restart the board, then reconnect Studio to confirm.` +
      (boardSafePeer ? ` Set linked board #${boardSafePeer} to the same limit.` : "");
  } catch (e) {
    stat.textContent = "Safety speed not saved: " + (e.message || e);
    notice(stat.textContent);
  }
}
function linkBadge() { // shown in robotStat so you see every open channel
  const parts = [], bus = busId() ? "→RS485 #" + busId() : "";
  if (haveAuto()) parts.push("fastest route (hub) ✓");
  if (usbDirect()) parts.push("USB direct" + bus + " ✓");
  else if (hubPort) parts.push("USB " + hubPort + bus + " (shared) ✓");
  if (haveWifi()) parts.push("WiFi " + robotIp());
  if (parts.length) return parts.join(" + ");
  // NOT CONNECTED IS NOT AN ANSWER. It says what the operator already knows and
  // nothing about what to do, and the same two words were used by three
  // different screens for three different situations. window.miceLink is the
  // one list, shared with the hub page and the board's own website - see
  // shared/web/mice.js. It is optional here only because Studio can be opened
  // from a file with no hub serving that script.
  if (window.miceLink) {
    const s = window.miceLink.read({ cable: false, wifi: false, viaHub: false,
                                     everHeard: false });
    return s.says + (s.next ? "  " + s.next : "");
  }
  return "not connected";
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
  clearHubTarget("you picked another WiFi module");
  $("connSel").value = "wifi";
  connModeChanged();
  $("robotIp").value = ip;
  connectRobot();
}
let connecting = false;   // one Connect at a time: repeated presses stacked probes on one cable
async function connectRobot() {
  if (!currentUser) {
    showTab("robot"); // This will actually show the login card since they aren't logged in
    $("loginStat").textContent = "Log in to connect to the robot.";
    if (!pendingConnect) {
      pendingConnect = {};
      pendingConnect.promise = new Promise((resolve, reject) => {
        pendingConnect.resolve = resolve; pendingConnect.reject = reject;
      });
    }
    return pendingConnect.promise;
  }
  if (connecting) return;
  connecting = true;
  try { await connectLink(); } finally { connecting = false; }
}
async function connectLink() {
  const t = transport(), had = hubPort;
  try {
    if (t === "usb") {
      if (!$("usbPort").dataset.loaded) await loadPorts();
      hubPort = $("usbPort").value;
      if (!hubPort) throw new Error("pick the USB port the module is plugged into " +
        "(⟳ to rescan)");
      recallBusId(hubPort);
    } else if (t === "serial" && !usbDirect()) {
      await serialConnect();
    }
    let s;
    try { s = await getStatus(); }
    catch (e) {
      // WIFI PICKED, CABLE GONE. The cable wins while it is open, so a robot
      // unplugged and carried elsewhere kept every Connect on the dead port
      // (user 2026-09-28: WiFi picked, nong found at 10.139.24.70, error was
      // "could not open port 'COM21'"). Drop the cable and ask over WiFi.
      if (t === "wifi" && hubPort && haveWifi()) {
        hubPort = "";
        s = await getStatus();
      } else {
      // silent cable: maybe an RS485 adapter, or the remembered bus id is now
      // another board - ask the hub who is behind it
      const tried = busId();
      if (t !== "usb" || !(await findBusId(hubPort)) || busId() === tried) throw e;
      s = await getStatus();
      }
    }
    if (t === "usb") rememberBusId(hubPort);
    checkLimitsMatch();                   // not awaited: connecting must not wait on it
    boardSafeIdentity = String(s.chip || s.id || "");
    adoptBoardSafety(s.module);
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
    boardSafeIdentity = "";
    $("safeDpsInput").disabled = $("saveSafeDps").disabled = true;
    $("safeSpeedStat").textContent = "Disconnected. Reconnect to read the active safety limit.";
    notice($("safeSpeedStat").textContent);
    $("robotStat").textContent = "Could not reach the robot. Check it is powered "
      + "and on the same network or cable, then try again. " + (e.message || e);
    notice($("robotStat").textContent);
  }
}
function sendPose(quiet) {
  return quiet ? sendPoseLive() : liveSend("POSE " + pose.map(fmtA).join(" "));
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
function liveSend(c) {
  if (!currentUser) return Promise.resolve(false);
  if (/^(?:MOVE\s+)?STOP\s*$/i.test(c)) return cancelSafeMotion("Stop");
  const p = /^POSE\s+(.+)$/i.exec(c);
  const work = { c, epoch:safeMotionEpoch, target:safeTarget(), goal:null, ms:0, revision:null };
  if (p) {
    const bits=p[1].trim().split(/\s+/), at=bits.findIndex(v=>v.toUpperCase()==='T');
    work.goal=(at<0 ? bits : bits.slice(0,at)).map(Number);
    work.ms=at<0 ? 0 : Number(bits[at+1]);
    if(work.goal.length!==NJ || work.goal.some(v=>!Number.isFinite(v)) ||
      !Number.isFinite(work.ms) || work.ms<0 || (at>=0 && at+2!==bits.length)) {
      safeMotionNote('Not moved: invalid pose or duration',true);return Promise.resolve(false);
    }
  }
  const result=new Promise(resolve=>{work.resolve=resolve;});
  if(work.goal && !playing) {
    if(livePending && livePending.resolve)livePending.resolve(false);
    work.revision=++safeGoalRevision;livePending=work;
  } else liveQueue.push(work);
  if(work.goal)lastSafeMove=result;
  livePump();return result;
}
function sendPoseLive() { return liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + liveT()); }
function liveAbort() {
  safeMotionEpoch++;safeGoalRevision++;
  liveQueue.forEach(work=>{if(work.resolve)work.resolve(false);});
  if(livePending && livePending.resolve)livePending.resolve(false);
  liveQueue=[];livePending=null;
}
function livePump() {
  if (liveBusy) return;
  liveBusy = true;
  (async () => {
    try {
      for (;;) {
        let work = null;
        if (liveQueue.length) {
          work = liveQueue.shift();                 // ordered work comes first
        } else if (livePending) {
          work = livePending;
          livePending = null;                    // only ever the newest pose
        }
        if (!work) break;
        const c=work.c;
        if(work.epoch!==safeMotionEpoch || work.target!==safeTarget()){work.resolve(false);continue;}
        try {
          if(work.goal) {
            const ok=await checkedPose(work.goal,work.ms,work.epoch,work.revision,work.target);
            work.resolve(ok);continue;
          }
          const t0 = performance.now();
          const r = await rawCmd(c);
          // Measure the link from the traffic itself — no probing, and it
          // follows a link that changes (USB pulled, WiFi gone slow).
          liveRtt += ((performance.now() - t0) - liveRtt) * 0.25;
          $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + r.slice(0, 80);
          work.resolve(true);
        } catch (e) {
          work.resolve(false);liveAbort();
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
  if (haveAuto()) {
    const body = (await (await autoFetch("upload", { dir: "/moves", name: fname }, {
      method: "POST", body: new TextEncoder().encode(text),
    })).text()).trim();
    if (body.startsWith("ERR")) throw new Error(body);
    return;
  }
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
  if (haveAuto())
    return (await autoFetch("download", { path: "/moves/" + fname })).text();
  if (haveWifi()) {
    try {
      // A 404/502 body is not a sequence: read as YAML it said "no pose steps".
      const r = await fetch(`/api/robot/download?ip=${encodeURIComponent(robotIp())}` +
                            `&path=${encodeURIComponent("/moves/" + fname)}`);
      const text = await r.text();
      if (!r.ok) throw new Error(text.trim() || ("the robot answered " + r.status));
      return text;
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (haveUsb()) return sdDownloadSerial(fname);
  throw new Error("connect first (WiFi or USB)");
}
async function sdDelete(fname) {
  if (haveAuto()) {
    const body = (await (await autoFetch("delete", { path: "/moves/" + fname })).text()).trim();
    if (body.startsWith("ERR")) throw new Error(body);
    return;
  }
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
    if (haveAuto()) {
      files = await (await autoFetch("files", { dir: "/moves" })).json();
    } else if (haveWifi()) {
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
      const play = document.createElement("button");
      play.textContent = "▶ Preview";
      play.title = "load this sequence into the timeline and play it here, in Studio";
      play.onclick = () => playSdSeq(f.n);
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
      row.append(name, run, play, edit, del);
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
  if (!(await ensureSafeTimeline())) return;
  if (!crashGate("UPLOAD it")) return;
  const { name, yaml } = buildYaml();
  try {
    await sdUpload(name + ".yaml", yaml);
    $("sdStat").textContent =
      `saved ${name}.yaml on the robot — press its ▶ Run button here, or pick it on the robot's own page`;
    refreshSd();
  } catch (e) { $("sdStat").textContent = "upload failed: " + (e.message || e); notice($("sdStat").textContent); }
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
  if (!haveRobot()) return;
  try { cancelSafeMotion('sequence takeover'); } catch (e) {}
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
  if (!haveRobot()) return;                  // nothing to hand off TO
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
    // Hand over from where the show HAS GOT TO, not from the top. Hiding the
    // tab half way through used to send the arm back to keyframe 0 first —
    // the same sweep as Run, but nobody pressed anything to cause it.
    const fromMs=playT;
    await cancelSafeMotion('handover');
    entryHold=true;
    const started=await startCheckedSequence(fromMs,false);
    if(!started) {handedOff=false;return;}
    // stop being the clock: the module owns the show now
    playing = false;
    keepAwake(false);
    $("playBtn").textContent = "▶ Play";
    const st = $("sdStat");
    if (st) st.textContent = "the module is running this sequence on its own — "
      + "it keeps going with this page closed. Press Stop to end it.";
  } catch (e) {
    handedOff = false;                       // it did not take: keep previewing
    safeMotionNote('Could not hand over: '+e.message,true);
  } finally {entryHold=false;}
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

// ---- every Run leaves a copy on the robot (A44-2) --------------------------
// User 2026-10-19: keep what was sent to run on the robot, so it can be played
// again from the robot's own page with no hub and no Studio. last.yaml is
// always the last thing run; the robot's page offers it first. Settings turns
// it off (a second upload costs time on a slow cable).
const LAST_RUN_FILE = "last.yaml";
const KEEP_RUN_KEY = "nong_keep_last_run";
function keepRunOn() {
  try { return localStorage.getItem(KEEP_RUN_KEY) !== "0"; }
  catch (e) { return true; }
}
function setKeepRun(on) {
  try { localStorage.setItem(KEEP_RUN_KEY, on ? "1" : "0"); }
  catch (e) { /* kept for this visit only */ }
}
// Returns "" when kept (or not wanted), else why not: a copy that failed must
// not stop the run, but it must be said.
async function keepLastRun(yaml, file) {
  if (!keepRunOn() || file === LAST_RUN_FILE) return "";
  try { await sdUpload(LAST_RUN_FILE, yaml); return ""; }
  catch (e) { return "the copy as " + LAST_RUN_FILE + " was not kept: " + (e.message || e); }
}

// Send the sequence, THEN play it. This used to send only `MOVE <name>.yaml`,
// so the module ran whatever copy of that name was already on its SD card while
// the crash check had just approved the timeline on screen. Edit a pose to fix
// a collision, press Run, and the robot performed the old crashing version —
// the safety check and the motion were looking at different data. Uploading
// first is what makes the check mean anything.
async function robotRun() {
  if (nothingToWrite("sdStat")) return;     // a file with no moves does nothing
  if (!(await ensureSafeTimeline())) return;
  if (!crashGate("RUN it on the robot")) return;
  // Run from where the clock is parked. Clicking a keyframe parks it there, so
  // Run continues the show from the pose on screen instead of sweeping back to
  // the first one — which is what the robot's arm would have to travel through.
  // A partial run is written under its own name: <name>.yaml stays the whole
  // show, so running part of it never overwrites the saved sequence.
  const st = $("sdStat");
  if (st) st.textContent = "checking and sending the sequence to the robot…";
  let started;
  try {
    started=await startCheckedSequence(playT);
  } catch (e) {
    cancelSafeMotion('sequence start failed');
    if (st) st.textContent = "could not start the sequence — "
      + (e && e.message ? e.message : e);
    return;
  }
  if(!started) {if(st)st.textContent='Start cancelled; check the current settings and try again.';return;}
  const {file,name,part,kept}=started;
  if (st) st.textContent = (part
    ? "the robot is running the checked remainder once, including any checked loop return. "
      + "The whole show is still saved as " + name + ".yaml."
    : "the robot is running " + file + " on its own.")
    + (kept ? " Note: " + kept : keepRunOn() ? " A copy is kept on it as " + LAST_RUN_FILE + "." : "");
  if (kept) notice(kept);
}

// ---- zero-position calibration (locked behind the HUB login) ----
// Checked by the hub, not against a password kept in this browser: that one
// (manny/12345678) refused admin/admin123 while the hub accepted it (A26-43).
async function zeroUnlock() {
  const u = $("zUser").value.trim(), p = $("zPass").value;
  let ok = false, why = "";
  try {
    const r = await fetch("/api/login", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: u, password: p }) });
    const j = await r.json().catch(() => ({}));
    ok = r.ok && !!j.ok;
    if (j.locked_for > 0) why = `Too many tries. Wait ${j.locked_for} seconds.`;
  } catch (e) {
    const acc = getAccounts();                 // no hub: Studio's own accounts
    ok = !!(acc[u] && acc[u] === p);
  }
  $("zPass").value = "";
  if (ok) {
    $("zeroLocked").style.display = "none";
    $("zeroPanel").style.display = "";
    $("zStat").textContent = "";
  } else {
    // Which of the two is wrong is deliberately not revealed.
    $("zStat").textContent = why || "That user name and password do not match. "
      + "Use your hub login and try again.";
  }
}
function zeroLock() { $("zeroPanel").style.display = "none"; $("zeroLocked").style.display = ""; }
async function robotZeroSet() {
  if (!haveRobot()) { $("zStat2").textContent = "connect to the robot first"; notice($("zStat2").textContent); return; }
  const r = await robotCmd("SETZERO");
  $("zStat2").textContent = r.startsWith("OK")
    ? "zero set — this pose is now the robot's home. Your start angles are unchanged."
    : ("failed: " + r);
  if (!r.startsWith("OK")) notice($("zStat2").textContent);
}

// ------- monitor mode: the 3D model follows the REAL robot
// (poll status; module.joints drives the rig, seq shows what's playing)
let monTimer = null;
function liveChanged() {
  if ($("liveChk").checked) { $("monChk").checked = false; monitorChanged(); }
  else cancelSafeMotion("Live turned off");
}
function monitorChanged() {
  if ($("monChk").checked) {
    $("liveChk").checked = false;
    // Same trap as livePause: a show started while Live was ticked belongs to
    // the HUB's clock, and switching this page to watching must end it.
    cancelSafeMotion('monitoring');
    playing = false; $("playBtn").textContent = "▶ Play";
    $("robotStat").textContent = "monitoring…";
    // Watching needs a link. Ticked before Connect (or after a first try that
    // timed out while the hub opened the port) it said "not connected" forever
    // although the cable worked (A26-42). So connect first, once.
    const start = () => { if ($("monChk").checked && !monTimer) monTimer = setInterval(monitorTick, 350); };
    if (haveRobot()) start();
    else Promise.resolve(connectRobot()).then(() => {
      if (haveRobot()) return start();
      $("monChk").checked = false;
      $("robotStat").textContent = "monitor needs the robot connected — pick the cable or "
        + "WiFi above and press Connect, then tick monitor again.";
      notice($("robotStat").textContent);
    });
  } else {
    clearInterval(monTimer); monTimer = null;
  }
}
let monBusy = false;
async function monitorTick() {
  // One status request at a time. Over RS485 a reply can take longer than the
  // 350 ms tick, and piling requests onto one shared cable made them fail.
  if (monBusy) return;
  monBusy = true;
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
    notice($("robotStat").textContent);
  } finally {
    monBusy = false;
  }
}
// --- the robot's own settings, from Setup (A44-3) ---
// User 2026-10-19: the robot's device settings should be set from Studio's
// settings too. Each row is a setting the firmware already has, written with
// the commands it already understands, and saved ON the robot (CFG keeps it
// over a restart). A new setting is one entry here, nothing else.
//   read  where it sits in the robot's status (INFO / /api/status)
//   send  the commands that set it now and keep it
//   ask   a question first, for a change with side effects
const ROBOT_SETTINGS = [
  { id: "name", label: "Name", type: "text", hint: "letters, digits and -",
    ok: v => /^[A-Za-z0-9-]{1,24}$/.test(v),
    read: s => s.name,
    send: v => ["SET NAME " + v],
    ask: v => "Rename the robot to " + v + "?\n\nIts WiFi name and its address ("
              + v + ".local) change too, so connect again afterwards." },
  { id: "speed", label: "Speed when a pose has no time", type: "number",
    unit: "°/s", min: 5, max: 600,
    read: s => s.module && s.module.speed_dps,
    send: v => ["SPEED " + v, "CFG speed_dps " + v] },
  { id: "volume", label: "Volume", type: "number", unit: "0 to 100", min: 0, max: 100,
    read: s => s.module && s.module.audio && s.module.audio.vol,
    send: v => ["VOL " + v, "CFG volume " + v] },
];
function renderRobotSettings() {
  const box = $("robotSettings");
  if (!box || box.childElementCount) return;
  ROBOT_SETTINGS.forEach(def => {
    const row = document.createElement("div"); row.className = "row";
    const lbl = document.createElement("label"); lbl.className = "lbl";
    lbl.htmlFor = "rs_" + def.id; lbl.textContent = def.label;
    const inp = document.createElement("input");
    inp.id = "rs_" + def.id; inp.type = def.type;
    if (def.type === "number") { inp.min = def.min; inp.max = def.max; inp.style.width = "80px"; }
    else inp.style.flex = "1";
    inp.placeholder = def.hint || "";
    const unit = document.createElement("span"); unit.className = "mini";
    unit.textContent = def.unit || "";
    const save = document.createElement("button");
    save.textContent = "Save to robot";
    save.onclick = () => saveRobotSetting(def);
    row.append(lbl, inp, unit, save);
    box.appendChild(row);
  });
  const keep = $("keepRunChk");
  if (keep) keep.checked = keepRunOn();
}
async function readRobotSettings() {
  const stat = $("robotSetStat");
  try {
    const s = await getStatus();
    ROBOT_SETTINGS.forEach(def => {
      const v = def.read(s || {});
      if (v !== undefined && v !== null) $("rs_" + def.id).value = v;
    });
    stat.textContent = "These are the robot's settings now. Change one and press its Save to robot.";
  } catch (e) {
    stat.textContent = "Could not read the robot. Connect it on the Robot tab first.";
    notice(stat.textContent);
  }
}
async function saveRobotSetting(def) {
  const stat = $("robotSetStat");
  const raw = $("rs_" + def.id).value.trim();
  const v = def.type === "number" ? Number(raw) : raw;
  const fine = def.type === "number"
    ? raw !== "" && Number.isFinite(v) && v >= def.min && v <= def.max
    : def.ok(v);
  if (!fine) {
    stat.textContent = def.label + ": " + (def.type === "number"
      ? "type a number from " + def.min + " to " + def.max + "."
      : "use " + def.hint + " only.");
    notice(stat.textContent);
    return;
  }
  if (def.ask && !confirm(def.ask(v))) return;
  try {
    for (const c of def.send(v)) {
      const r = await rawCmd(c);
      if (!/^OK/i.test(r || "")) throw new Error(r || "no answer");
    }
    stat.textContent = def.label + " is " + v + (def.unit ? " " + def.unit : "")
      + " on the robot now, and it keeps it after a restart.";
  } catch (e) {
    stat.textContent = def.label + " was not saved on the robot: " + (e.message || e);
    notice(stat.textContent);
  }
}
renderRobotSettings();
// --- moves from a video of a person (A44-4) ---
// User 2026-10-19: make the robot's moves from a video of a person, as close
// as the robot's joints allow. The browser finds the person's skeleton in each
// frame (MediaPipe Pose). Each arm is then placed by the rig's own solvers: the
// person's upper-arm and forearm DIRECTIONS, at the robot's own bone lengths,
// give an elbow and a hand target - the two-target fit mirrorPose() uses, so
// mounting tilts and joint limits hold and a shape out of reach lands on the
// closest one. The video is read in this browser and never uploaded.
const VID_LIB = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35";
const VID_MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                + "pose_landmarker_full/float16/1/pose_landmarker_full.task";
// MediaPipe's 33-point body: shoulder, elbow, wrist of the person's own L, R.
const VID_PTS = { sh: [11, 12], el: [13, 14], wr: [15, 16] };
const VID_FPS = 10;        // frames read per second of video; the fit is warm-started from the last
const VID_SMOOTH = 2;      // frames each side averaged: tracking jitters ~1-2 cm a frame
const VID_SEEN = 0.5;      // a point MediaPipe is less sure of than this is a guess, not a sighting
// How closely the moves follow the video, in joint degrees off the straight
// line between two kept moves. Every move eases to a stop (as the firmware
// does), so more moves is closer but stop-start. One entry = one choice.
const VID_DETAIL = [
  { id: "smooth", label: "Smooth — fewer moves", tol: 14 },
  { id: "normal", label: "Normal", tol: 8 },
  { id: "close", label: "Close — more moves", tol: 4 },
];
// "always" (A44-6, user 2026-10-19): show that side even where the hand has to
// move for it, as close to the person's pose as the joints allow.
const VID_HAND = [
  { id: "video", label: "as in the video" },
  { id: "palm", label: "palm on top", want: 1 },
  { id: "back", label: "back of the hand on top", want: -1 },
  { id: "palm-force", label: "palm on top, always (the hand may move)", want: 1, force: true },
  { id: "back-force", label: "back on top, always (the hand may move)", want: -1, force: true },
];
// What each made move can become before it goes on the time bar (A44-6).
const VID_USE = [
  { id: "keep", label: "Keep" },
  { id: "force", label: "Keep, hand side forced" },
  { id: "moment", label: "Use another moment…" },
  { id: "drop", label: "Leave out" },
];
let vidLib = null, vidFrames = null, vidMade = null, vidStop = false, vidBusy = false;
let vidFit = null, vidPicks = null;   // fitted frames, and the moves made from them

// The person's skeleton finder. Loaded the first time it is used; the model
// file is then kept in the browser's own store, as its server lets a cache
// hold it for only an hour and the hub must not need the internet every time.
async function vidLoadLib() {
  if (vidLib) return vidLib;
  const mp = await import(VID_LIB + "/vision_bundle.mjs");
  let model = null;
  try {
    const store = await caches.open("mice-pose-model");
    let r = await store.match(VID_MODEL);
    if (!r) { await store.add(VID_MODEL); r = await store.match(VID_MODEL); }
    if (r) model = new Uint8Array(await r.arrayBuffer());
  } catch (e) { model = null; }      // no store here (a phone over plain http): fetch each time
  const files = await mp.FilesetResolver.forVisionTasks(VID_LIB + "/wasm");
  const base = model ? { modelAssetBuffer: model } : { modelAssetPath: VID_MODEL };
  const make = (delegate) => mp.PoseLandmarker.createFromOptions(files, {
    baseOptions: { ...base, delegate }, runningMode: "VIDEO", numPoses: 1 });
  // Some graphics drivers refuse the GPU path; the CPU one is slower, not wrong.
  try { vidLib = await make("GPU"); } catch (e) { vidLib = await make("CPU"); }
  return vidLib;
}

function vidSay(text, bad) {
  $("vidStat").textContent = text;
  if (bad) notice(text);
}
function vidOpts() {
  const det = VID_DETAIL.find(d => d.id === $("vidDetail").value) || VID_DETAIL[1];
  const h = [0, 1].map(a => VID_HAND.find(x => x.id === $("vidHand" + a).value) || {});
  return { tol: det.tol, mirror: $("vidMirror").checked, waist: $("vidWaist").checked,
           hand: h.map(x => x.want || 0), force: h.map(x => !!x.force),
           music: $("vidMusic").checked };
}
function vidFill() {        // the choices are built from the lists above
  const fill = (sel, list, pick) => {
    if (!sel || sel.options.length) return;
    list.forEach(o => sel.add(new Option(o.label, o.id, false, o.id === pick)));
  };
  fill($("vidDetail"), VID_DETAIL, "normal");
  HANDS.forEach((h, a) => {
    const lbl = $("vidHandLbl" + a);
    if (lbl) lbl.textContent = h.label;
    fill($("vidHand" + a), VID_HAND, "video");
  });
}

// A picked file goes on the stage like a fetched link (video_page.js).
function vidPick(file) {
  vidFill();
  if (!file) return;
  vidSetSrc(URL.createObjectURL(file), { kind: "file", name: file.name, file });
}

// Seek through the video and find the person in each frame. Seeking, not
// playing, so every frame is read however slow the PC is.
async function vidRead() {
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration)) { vidSay("Pick a video first.", true); return null; }
  vidSay("Loading the body finder (the first time needs the internet)…");
  let lib;
  try { lib = await vidLoadLib(); }
  catch (e) {
    vidSay("Could not load the body finder. It needs the internet the first time; "
           + "check the connection and press Make moves again.", true);
    $("vidTech").textContent = String(e && e.message || e);
    return null;
  }
  const from = Math.max(0, +$("vidFrom").value || 0);
  const to = Math.min(v.duration, +$("vidTo").value || v.duration);
  const frames = [];
  v.pause();
  for (let t = from; t <= to + 1e-6 && !vidStop; t += 1 / VID_FPS) {
    await new Promise(res => { v.onseeked = res; v.currentTime = Math.min(t, v.duration - 0.001); });
    // timestamps must only grow, also on a second read of the same video
    const r = lib.detectForVideo(v, performance.now());
    const w = r.worldLandmarks && r.worldLandmarks[0], s = r.landmarks && r.landmarks[0];
    // p: the same points on the picture, so the skeleton plays along later
    frames.push({ t: t - from, w: w ? w.map(p => ({ x: p.x, y: p.y, z: p.z, v: p.visibility })) : null,
                  p: s ? s.map(p => ({ x: p.x, y: p.y, v: p.visibility })) : null });
    vidDraw(frames[frames.length - 1].p);
    vidSay("Reading the video: " + Math.round(100 * (t - from) / Math.max(0.1, to - from)) + "%");
  }
  return frames;
}
// The skeleton over the video, so it is plain whether the person was found.
// Points are fractions of the PICTURE, which the player letterboxes inside its
// box: they are placed on the picture, not on the box.
const VID_BONES = [[11, 12], [11, 23], [12, 24], [23, 24],
                   [11, 13], [13, 15], [12, 14], [14, 16]];
function vidDraw(pts) {
  const v = $("vidPlayer"), c = $("vidOverlay");
  c.width = v.clientWidth; c.height = v.clientHeight;
  c.style.left = v.offsetLeft + "px"; c.style.top = v.offsetTop + "px";
  const g = c.getContext("2d");
  g.clearRect(0, 0, c.width, c.height);
  if (!pts || !v.videoWidth) return;
  const k = Math.min(c.width / v.videoWidth, c.height / v.videoHeight);
  const w = v.videoWidth * k, h = v.videoHeight * k, ox = (c.width - w) / 2, oy = (c.height - h) / 2;
  const css = getComputedStyle(document.documentElement);
  g.strokeStyle = g.fillStyle = css.getPropertyValue("--acc").trim() || "currentColor";
  g.lineWidth = 3;
  const P = i => [ox + pts[i].x * w, oy + pts[i].y * h];
  const seen = i => pts[i] && (pts[i].v == null || pts[i].v >= VID_SEEN);
  g.beginPath();
  for (const [a, b] of VID_BONES) if (seen(a) && seen(b)) { g.moveTo(...P(a)); g.lineTo(...P(b)); }
  g.stroke();
  for (const i of [11, 12, 13, 14, 15, 16]) if (seen(i)) {
    g.beginPath(); g.arc(...P(i), 4, 0, 2 * Math.PI); g.fill();
  }
}

// ---- skeleton -> the robot's two bone directions per arm --------------------
// MediaPipe's world points are metres, x right in the picture, y down, z away
// from the camera. Turned to y up and z toward the camera, a person facing the
// camera has the robot's own axes: +x their left, +y up, +z their front. The
// person's frame turns with their shoulder line, so a person standing at an
// angle still drives the arms as if facing the robot's front.
function vidBodyFrame(w, mirror) {
  const pt = (i) => {
    // A mirror swaps the person's sides and flips the picture: the robot then
    // moves like their reflection, which is how an audience in front sees it.
    const j = mirror ? (i % 2 ? i + 1 : i - 1) : i;
    const p = w[j];
    return { at: new THREE.Vector3(mirror ? -p.x : p.x, -p.y, -p.z), seen: (p.v == null ? 1 : p.v) };
  };
  const L = pt(VID_PTS.sh[0]), R = pt(VID_PTS.sh[1]);
  const left = L.at.clone().sub(R.at); left.y = 0;
  if (left.length() < 1e-4) return null;
  left.normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const front = left.clone().cross(up);
  const toBody = (d) => new THREE.Vector3(d.dot(left), d.dot(up), d.dot(front)).normalize();
  const arms = [0, 1].map(a => {
    const S = pt(VID_PTS.sh[a]), E = pt(VID_PTS.el[a]), W = pt(VID_PTS.wr[a]);
    const ok = Math.min(S.seen, E.seen, W.seen) >= VID_SEEN;
    return { ok, upper: toBody(E.at.clone().sub(S.at)), fore: toBody(W.at.clone().sub(E.at)) };
  });
  // yaw: 0 facing the camera, + turned toward their own left
  return { arms, yaw: Math.atan2(front.x, front.z) };
}
// One sample per frame: bone directions per arm, unseen frames filled from the
// nearest seen one, then averaged over a few frames each side.
function vidBones(frames, mirror) {
  const raw = frames.map(f => (f.w ? vidBodyFrame(f.w, mirror) : null));
  const out = frames.map((f, i) => ({ t: f.t, yaw: raw[i] ? raw[i].yaw : null, arms: [null, null] }));
  for (const a of [0, 1]) {
    const seen = raw.map((r, i) => (r && r.arms[a].ok ? i : -1)).filter(i => i >= 0);
    if (!seen.length) continue;
    for (let i = 0, k = 0; i < raw.length; i++) {
      while (k + 1 < seen.length && Math.abs(seen[k + 1] - i) <= Math.abs(seen[k] - i)) k++;
      out[i].arms[a] = raw[seen[k]].arms[a];
    }
  }
  const smooth = (get) => out.map((_, i) => {
    const s = new THREE.Vector3();
    for (let j = Math.max(0, i - VID_SMOOTH); j <= Math.min(out.length - 1, i + VID_SMOOTH); j++) {
      const v = get(j); if (v) s.add(v);
    }
    return s.lengthSq() > 1e-9 ? s.normalize() : null;
  });
  const res = out.map(o => ({ t: o.t, yaw: o.yaw, arms: [null, null] }));
  for (const a of [0, 1]) {
    const up = smooth(j => out[j].arms[a] && out[j].arms[a].upper);
    const fo = smooth(j => out[j].arms[a] && out[j].arms[a].fore);
    res.forEach((r, i) => { if (up[i] && fo[i]) r.arms[a] = { upper: up[i], fore: fo[i] }; });
  }
  return res;
}

// ---- directions -> joint angles --------------------------------------------
// The waist value that turns the body by `yaw`, found by trying them on the
// rig: the joint's sense and zero are rig data, not a sign to guess here.
function vidWaistTable() {
  const tbl = [];
  for (let v = RIG.min[8]; v <= RIG.max[8]; v += 1) {
    pose[8] = v; applyPose(); robot.updateMatrixWorld(true);
    // world turn: with the CAD look (A48-1) bodyGroup sits inside the URDF tree
    const d = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.getWorldQuaternion(new THREE.Quaternion()));
    tbl.push({ v, yaw: Math.atan2(d.x, d.z) });
  }
  return tbl;
}
// Put one arm where the person's arm points: elbow by the two shoulder joints,
// hand by the two elbow joints. `first` walks there from afar (solveElbowIK);
// later frames start from the last fit and are a few degrees away.
function vidFitArm(arm, bones, first) {
  const sh = arm === 0 ? [0, 1] : [4, 5], el = arm === 0 ? [2, 3] : [6, 7];
  robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const S = W(jointGroups[sh[0]]), E0 = W(elbowBalls[arm]), H0 = W(wristBalls[arm]);
  const upperLen = E0.distanceTo(S), foreLen = H0.distanceTo(E0);
  const s = bodyGroup.worldToLocal(S.clone());
  const e = s.clone().addScaledVector(bones.upper, upperLen);
  const h = e.clone().addScaledVector(bones.fore, foreLen);
  const eW = bodyGroup.localToWorld(e), hW = bodyGroup.localToWorld(h);
  if (first) solveElbowIK(arm, eW);
  else if (ccdChain(sh, elbowBalls[arm], eW, 6) > 15) solveElbowIK(arm, eW);
  ccdChain(el, wristBalls[arm], hW, first ? 24 : 8);
  applyPose();             // ccdChain leaves its last rejected try drawn
}
// Douglas-Peucker on the joint angles: keep the frame that strays furthest from
// the straight line between two kept ones, until none strays more than `tol`.
function vidThin(times, poses, tol) {
  const keep = new Set([0, poses.length - 1]);
  const off = (a, b, i) => {
    const f = (times[i] - times[a]) / Math.max(1e-6, times[b] - times[a]);
    let m = 0;
    for (let j = 0; j < NJ; j++)
      m = Math.max(m, Math.abs(poses[a][j] + (poses[b][j] - poses[a][j]) * f - poses[i][j]));
    return m;
  };
  const stack = [[0, poses.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let worst = -1, far = tol;
    for (let i = a + 1; i < b; i++) { const d = off(a, b, i); if (d > far) { far = d; worst = i; } }
    if (worst >= 0) { keep.add(worst); stack.push([a, worst], [worst, b]); }
  }
  return [...keep].sort((x, y) => x - y);
}
// ---- frames -> moves, in three steps (A44-6) --------------------------------
// 1. Fit every frame: the slow part, done again only when Mirror or Waist change.
function vidFitFrames(frames, opts) {
  const bones = vidBones(frames, opts.mirror);
  if (!bones.some(b => b.arms[0] || b.arms[1])) return null;
  const saved = pose;
  const poses = [];
  try {
    pose = RIG.neutral.map((v, i) => clampJ(i, v));
    const waist = opts.waist ? vidWaistTable() : null;
    bones.forEach((b, i) => {
      if (waist && b.yaw != null) {
        let best = waist[0];
        for (const w of waist) if (Math.abs(w.yaw - b.yaw) < Math.abs(best.yaw - b.yaw)) best = w;
        pose[8] = best.v;
      } else pose[8] = clampJ(8, RIG.neutral[8]);
      applyPose();
      for (const a of [0, 1]) if (b.arms[a]) vidFitArm(a, b.arms[a], i === 0);
      poses.push(pose.map(v => Math.round(v * 10) / 10));
    });
  } finally { pose = saved; applyPose(); }
  const times = bones.map(b => b.t * 1000);
  return { times, poses, mirror: opts.mirror, waist: opts.waist,
           videoMs: Math.round(times[times.length - 1] || 0) };
}
// 2. Which frames become moves. Each can then be kept, left out, or filled
// with another moment of the video - its place on the video's clock stays.
function vidPicksFor(fit, tol) {
  return vidThin(fit.times, fit.poses, tol).map(i => ({ i, use: "keep", at: fit.times[i] }));
}
function vidPoseAt(fit, ms) {    // the fitted pose nearest a moment of the video
  let best = 0;
  fit.times.forEach((t, i) => { if (Math.abs(t - ms) < Math.abs(fit.times[best] - ms)) best = i; });
  return fit.poses[best];
}
// One side of a hand on top even where the hand must move for it: from
// facePalm's best shape, the least hand travel that shows that side. Returns
// facePalm's shape: { pose, upness } (+1 palm up, -1 back up).
// near: start from p itself, not facePalm's shape - the smallest nudge, for a
// move that has only so much time (facePalm may pick a far shape).
function vidForceHand(p, arm, want, near) {
  const r = near ? { pose: p, upness: palmUpnessOf(p, arm) } : facePalm(p, arm, want);
  if (!r || want * r.upness > 0.5) return r;
  const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
  const saved = pose;
  try {
    pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
    const h0 = wristBalls[arm].getWorldPosition(new THREE.Vector3());
    // 1 mm of hand travel against the side shown: not showing it costs as much
    // as moving the hand two metres, so the side always wins when it can.
    const cost = () => {
      applyPose(); robot.updateMatrixWorld(true);
      return wristBalls[arm].getWorldPosition(new THREE.Vector3()).distanceTo(h0)
           + 2000 * Math.max(0, 0.6 - want * palmUpness(arm));
    };
    pose = r.pose.slice();
    let best = cost();
    for (let round = 0; round < 40; round++) {
      let better = false;
      for (const j of idx) for (const step of [20, 8, 3, 1]) for (const dir of [1, -1]) {
        const old = pose[j], nv = clampJ(j, old + dir * step);
        if (nv === old) continue;
        pose[j] = nv;
        const c = cost();
        if (c < best - 0.01) { best = c; better = true; } else pose[j] = old;
      }
      if (!better) break;
    }
    applyPose();
    return { pose: pose.slice(), upness: palmUpness(arm) };
  } finally { pose = saved; applyPose(); }
}
// The furthest a move gets toward `to` in `ms`: all the way if the servos can,
// else part of the way - so it still ends on its beat and the show stays with
// the music (user 2026-10-19).
function vidReachIn(from, to, ms) {
  if (minTime(from, to) <= ms) return to;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  let lo = 0, hi = 1;
  for (let k = 0; k < 14; k++) {
    const m = (lo + hi) / 2;
    if (minTime(from, at(m)) <= ms) lo = m; else hi = m;
  }
  return at(lo);
}
// The asked hand side on a pose: { pose, miss: [L, R] } (miss = that hand
// still not showing it). upness is +1 palm up, -1 back up, whichever was asked.
// near: for a part-way move - a hand already showing it stays put, else it
// gets the smallest nudge; facePalm goes for the MOST upness, which can be a
// big jump the time left cannot pay for.
function vidSide(p, pk, opts, near) {
  const miss = [false, false];
  for (const a of [0, 1]) if (opts.hand[a]) {
    const force = opts.force[a] || pk.use === "force";
    const r = near ? vidForceHand(p, a, opts.hand[a], true)
      : force ? vidForceHand(p, a, opts.hand[a]) : facePalm(p, a, opts.hand[a]);
    if (r) p = r.pose.map(v => Math.round(v * 10) / 10);
    // A near-straight arm cannot roll its hand (the elbow sits on the
    // turning line); it stayed on its edge with nothing said (browser test
    // 2026-10-19).
    if (!r || opts.hand[a] * r.upness <= 0.5) miss[a] = true;
  }
  return { pose: p, miss };
}
// Part of the way in `ms` AND a forced hand side kept. A plain part-way pose
// is a joint blend, and a blend of two back-up shapes can pass the hand's edge
// (PC 2026-10-19: back forced, music on, upness up to +0.10 with no miss
// said). So the side goes on each try and the furthest try in time wins; at
// worst the robot stays where it is for that beat, still showing the side.
function vidReachSide(from, to, ms, pk, opts) {
  const forced = [0, 1].filter(a => opts.hand[a] && (opts.force[a] || pk.use === "force"));
  const fits = (s) => minTime(from, s.pose) <= ms && forced.every(a => !s.miss[a]);
  const plain = vidReachIn(from, to, ms), near = vidSide(plain, pk, opts, true);
  if (fits(near)) return near;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  const still = vidSide(from, pk, opts, true);
  let lo = 0, hi = 1, best = fits(still) ? still : null;
  for (let k = 0; k < 8; k++) {
    const m = (lo + hi) / 2, s = vidSide(at(m), pk, opts, true);
    if (fits(s)) { lo = m; best = s; } else hi = m;
  }
  // The last move already lost the side: keep the beat and say so.
  return best || { pose: plain, miss: [0, 1].map(a => !!opts.hand[a]
    && opts.hand[a] * palmUpnessOf(plain, a) <= 0.5) };
}
// 3. The moves, from the picks and the choices.
function vidBuild(fit, picks, opts) {
  const out = [], handMiss = [0, 0];
  let kept = 0, partial = 0, last = 0, start = 0;
  for (const pk of picks) {
    pk.missHand = [false, false];
    if (pk.use === "drop") continue;
    let s = vidSide(pk.use === "moment" ? vidPoseAt(fit, pk.at) : fit.poses[pk.i], pk, opts);
    kept++;
    const t = fit.times[pk.i];       // its place on the video's clock
    const prev = out[out.length - 1];
    const gap = t - last;
    last = t;
    if (!prev) { out.push({ pose: s.pose, t: 1000, hold: 0 }); start = t; }
    // the same pose again is a pause on the last move, not a move of no length
    else if (deltaDeg(prev.pose, s.pose) < 1) prev.hold += gap;
    else {
      if (opts.music && minTime(prev.pose, s.pose) > gap) {
        s = vidReachSide(prev.pose, s.pose, gap, pk, opts);
        partial++;
      }
      // Pinned, so Show speed does not re-time the video's rhythm. Without
      // "stay with the music" a move too fast for the servos is slowed instead.
      if (deltaDeg(prev.pose, s.pose) < 1) prev.hold += gap;
      else out.push({ pose: s.pose, t: Math.round(gap), hold: 0, tset: true });
    }
    // counted on the pose that went on the bar, after any part-way cut
    for (const a of [0, 1]) if (s.miss[a]) { handMiss[a]++; pk.missHand[a] = true; }
  }
  out.forEach(k => { k.hold = Math.round(k.hold); });
  // A46-1: a person's arm passes where the robot's cannot (through its own
  // body). safeKeys() drops a pose that hits and sends a hitting move round,
  // on this rig's sizes; each move keeps its time, so the music still fits.
  const safe = safeKeys(out, undefined, opts.music);
  // start: the first kept move's moment, where these moves meet the video
  return { keys: safe.keys, videoMs: fit.videoMs, handMiss, kept, partial, start, safe };
}
// frames -> timeline keys in one go. No video needed, so QC hands it a skeleton.
// opts: { tol, mirror, waist, hand: [want L, R] (0 = as in the video),
//         force: [L, R], music }
function movesFromFrames(frames, opts) {
  const fit = vidFitFrames(frames, opts);
  if (!fit) return null;
  const o = { force: [false, false], music: false, ...opts };
  return vidBuild(fit, vidPicksFor(fit, o.tol), o);
}

// What the choices could not do, in words; empty when everything worked.
function vidHandNote(made) {
  const opts = vidOpts();
  return [0, 1].filter(a => opts.hand[a] && made.handMiss[a]).map(a =>
    " The " + HANDS[a].label.toLowerCase() + " could not show its "
    + (opts.hand[a] > 0 ? "palm" : "back") + " on top in " + made.handMiss[a] + " of "
    + made.kept + " moves" + (opts.force[a]
      ? ": the joints cannot turn it that far even with the hand moved."
      : ": the arm is almost straight there. Pick “always” for that hand, or "
        + "“Keep, hand side forced” on those moves below, and the hand moves "
        + "just enough to show it.")).join("");
}
function vidSummary() {
  const m = vidMade, opts = vidOpts();
  return m.keys.length + " moves from " + (m.videoMs / 1000).toFixed(1) + " s of video."
    + (m.safe && safeSay(m.safe) ? " " + safeSay(m.safe) : "")
    + (opts.music && m.partial
      ? " To stay with the music, " + m.partial + " of them go only part of the way: "
        + "the person moved faster than the robot can."
      : "")
    + vidHandNote(m) + " Choose what to keep below, then put them on the time bar:";
}
// One row per made move: its moment (click to see it), what it becomes, and
// what could not be done for it.
function vidList() {
  const box = $("vidList");
  box.innerHTML = "";
  if (!vidPicks) return;
  const opts = vidOpts(), anyHand = opts.hand.some(Boolean);
  vidPicks.forEach((pk, n) => {
    const row = document.createElement("div");
    row.className = "row vidrow";
    const see = document.createElement("button");
    see.type = "button";
    see.textContent = (n + 1) + " · " + (vidFit.times[pk.i] / 1000).toFixed(1) + " s";
    see.title = "see this moment of the video and the robot's pose for it";
    see.onclick = () => vidSee(pk);
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "move " + (n + 1));
    VID_USE.filter(u => u.id !== "force" || anyHand)
      .forEach(u => sel.add(new Option(u.label, u.id, false, u.id === pk.use)));
    const at = document.createElement("input");
    at.type = "number"; at.step = "0.1"; at.min = "0";
    at.value = (pk.at / 1000).toFixed(1);
    at.hidden = pk.use !== "moment";
    at.title = "the moment of the video (s) whose pose fills this move; it keeps its own place in time";
    at.setAttribute("aria-label", "moment for move " + (n + 1));
    sel.onchange = () => { pk.use = sel.value; at.hidden = pk.use !== "moment"; vidRebuild(); };
    at.onchange = () => { pk.at = Math.max(0, +at.value || 0) * 1000; vidRebuild(); vidSee(pk); };
    row.append(see, sel, at);
    const miss = HANDS.filter((h, a) => pk.missHand && pk.missHand[a]).map(h => h.side);
    if (miss.length) {
      const w = document.createElement("span");
      w.className = "mini";
      w.textContent = miss.join(" ") + " hand on its edge";
      row.appendChild(w);
    }
    box.appendChild(row);
  });
}
function vidSee(pk) {
  const v = $("vidPlayer");
  const ms = pk.use === "moment" ? pk.at : vidFit.times[pk.i];
  if (v.src && isFinite(v.duration)) {
    v.pause();
    v.currentTime = Math.min(v.duration, (+$("vidFrom").value || 0) + ms / 1000);
  }
  pose = vidPoseAt(vidFit, ms).slice();
  poseChanged(false);
}
// One step (user 2026-10-22: *drop a video, the robot does it*): make the
// moves, put them on the time bar and save them under the video's name. The
// safety pass is in vidBuild, so what is saved is what was checked.
async function vidMakeAndSave() {
  if (vidBusy) return;
  await vidMake();
  if (!vidMade || vidMade.keys.length < 2) return;
  const base = ((vidSrc && (vidSrc.name || vidSrc.url)) || "video").split(/[\\/?#]/).filter(Boolean).pop();
  setWorkName("video_" + base.replace(/\.[^.]*$/, ""));
  if (!(await vidUse("replace"))) return;
  if (await saveAll()) vidSay($("tlStat").textContent);
}
async function vidMake() {
  if (vidBusy) { vidStop = true; return; }
  vidBusy = true; vidStop = false;
  $("vidGo").textContent = "■ Stop";
  $("vidUseBox").hidden = true;
  try {
    const frames = await vidRead();
    if (!frames) return;
    if (!frames.some(f => f.w)) {
      vidSay("No person was found in the video. Use a video where one person's "
             + "upper body and arms are in the picture.", true);
      return;
    }
    vidFrames = frames;
    vidSay("Fitting the robot's arms…");
    await new Promise(r => setTimeout(r, 30));      // let the line paint first
    vidRemake("fit");
    if (!vidMade || vidMade.keys.length < 2) {
      vidSay("The arms were not seen clearly enough to make moves. Try a video "
             + "where the arms are in the picture and not hidden.", true);
      vidMade = null;
      return;
    }
    const seen = frames.filter(f => f.w).length;
    vidSay("The person was found in " + Math.round(100 * seen / frames.length)
           + "% of the video. " + vidSummary());
  } finally {
    vidBusy = false;
    $("vidGo").textContent = "▶ Make moves";
  }
}
// A choice changed: redo only what it touches. "fit" (Mirror, Waist) fits the
// frames again, "pick" (Follow) chooses the moves again and resets each move's
// own choice, anything else (hands, music, a move's row) just rebuilds.
function vidRemake(step) {
  if (!vidFrames || (vidBusy && step !== "fit")) return;
  const opts = vidOpts();
  if (step === "fit" || !vidFit) vidFit = vidFitFrames(vidFrames, opts);
  if (!vidFit) { vidMade = null; vidPicks = null; vidList(); return; }
  if (step === "fit" || step === "pick" || !vidPicks) vidPicks = vidPicksFor(vidFit, opts.tol);
  vidRebuild();
}
function vidRebuild() {
  vidMade = vidBuild(vidFit, vidPicks, vidOpts());
  vidList();
  $("vidUseBox").hidden = !(vidMade && vidMade.keys.length >= 2);
  vidSay(vidSummary());
}
async function vidUse(how) {
  if (!vidMade) return false;
  const add = JSON.parse(JSON.stringify(vidMade.keys));
  if (how === "replace") {
    if (!(await askUnsaved("replace the time bar with the moves from the video"))) return false;
    keys = add;
  } else {
    // the first video pose is a move like any other once it follows a move
    add[0].t = autoTime(keys[keys.length - 1].pose, add[0].pose, keyDps(keys.length));
    keys = keys.concat(add);
  }
  bumpKeys();
  clearBadMarks();
  clampKeyTimes();
  selKey = how === "replace" ? 0 : keys.length - add.length;
  vidOnBar(selKey);
  pose = [...keys[selKey].pose];
  poseChanged(false);
  renderTimeline();
  const robotMs = keys.slice(selKey).reduce((s, k, i) => s + (i ? k.t : 0) + (k.hold || 0), 0);
  $("tlStat").textContent = add.length + " moves from the video are on the time bar. "
    + (robotMs > vidMade.videoMs * 1.15
      ? "The robot needs " + (robotMs / 1000).toFixed(1) + " s for " + (vidMade.videoMs / 1000).toFixed(1)
        + " s of video: the person moved faster than its servos and speed limit allow. "
        + "Tick “Stay with the music” to keep the video's timing instead. "
      : "")
    + "Press Play to watch, edit any move, then Save or Save to robot.";
  vidSay($("tlStat").textContent);
  return true;
}
vidFill();
// --- the Video page (A44-8) ---
// User 2026-10-19: a page of its own for moves from a video - the person with
// their music, the skeleton found on them and the robot moving beside them,
// in step - that takes YouTube, Google Drive and other links too, and whose
// moves and choices are Studio's own (the same time bar, the same saved file).
// It is the Video tab: while it is open the person shares the screen with the
// 3D view. The robot beside the video is a PREVIEW: nothing is sent to a board
// until the moves are on the time bar and played from there.
// Links are fetched by the hub (main_python/hub_video.py): a browser cannot
// read the picture of a video another site plays.
let vidSrc = null;          // what is on the stage: { kind: "file"|"link", name, url, id, file }
let vidFetchId = null, vidLinkBusy = false;
let vidHeld = null;         // the editor's pose, given back when the page closes
let vidView = "iso";        // the 3D view it had, given back too
let vidLastMs = -1, vidOn = false, vidFirstKey = -1;
let vidSaved = null;        // the video choices the open project was saved with
const VID_LOGIN = "Log in first (the Robot tab has the login): a link is fetched onto this PC.";

function vidPage(on) {
  if (on === vidOn) return;
  vidOn = on;
  document.body.classList.toggle("vidpage", on);
  const v = $("vidPlayer");
  if (on) {
    vidFill();
    vidHeld = pose.slice();
    vidLastMs = -1;
    // From the front the robot faces you as the person faces the camera, so
    // the two read the same way round.
    const cur = document.querySelector("#viewCube [data-view].on");
    vidView = cur ? cur.dataset.view : "iso";
    setView("front");
    requestAnimationFrame(vidTick);
    return;
  }
  if (v && !v.paused) v.pause();
  // The page drew the video's poses on the editor's robot; give it back.
  if (vidHeld) { pose = vidHeld; applyPose(); renderSliders(); }
  vidHeld = null;
  setView(vidView);
}

// A video for the stage, from a file or a fetched link.
function vidSetSrc(url, src) {
  const v = $("vidPlayer");
  if (v.src && v.src.startsWith("blob:")) URL.revokeObjectURL(v.src);
  vidSrc = src;
  v.src = url;
  v.hidden = false;
  $("vidEmpty").hidden = true;
  vidFrames = null; vidMade = null; vidFit = null; vidPicks = null;
  vidList();
  vidDraw(null);
  $("vidUseBox").hidden = true;
  $("vidSoundBox").hidden = true;
  $("vidGo").disabled = false;
  $("vidGoSave").disabled = false;
  $("vidPlayBtn").disabled = false;
  $("vidTech").textContent = "";
  vidLastMs = -1;
  v.onloadedmetadata = () => {
    // a reopened project's part of the video is kept; a new video uses all of it
    const keep = vidSaved && vidSaved.src && src.url && vidSaved.src.url === src.url;
    $("vidFrom").value = keep ? String(vidSaved.from || 0) : "0";
    $("vidTo").value = keep && vidSaved.to ? String(vidSaved.to) : v.duration.toFixed(1);
    vidSay("Ready: " + v.duration.toFixed(1) + " s of video. Press Make moves.");
  };
  v.onerror = () => vidSay("This browser cannot play that video. Try an MP4 or WEBM file.", true);
  v.onended = v.onpause = () => { $("vidPlayBtn").textContent = "▶ Play person and robot"; };
  v.onplay = () => { $("vidPlayBtn").textContent = "❚❚ Pause"; };
}

// A link: the hub fetches it onto this PC and says how far it has got.
async function vidFetch() {
  if (vidLinkBusy) {                      // the button is Stop while it fetches
    if (vidFetchId) await Mice.Api.post("/api/video/fetch", { cancel: vidFetchId });
    return;
  }
  const url = $("vidLink").value.trim();
  if (!/^https?:\/\/\S+$/i.test(url)) {
    vidSay("Paste a whole link, starting with https://", true);
    return;
  }
  vidLinkBusy = true;
  $("vidFetchBtn").textContent = "■ Stop";
  $("vidTech").textContent = "";
  try {
    vidSay("Asking this PC to fetch the video…");
    let a = await Mice.Api.post("/api/video/fetch", { url });
    if (!a.ok) {
      vidSay(a.needLogin ? VID_LOGIN : "The link could not be fetched: " + a.says, true);
      $("vidTech").textContent = a.tech || "";
      return;
    }
    vidFetchId = a.data.id;
    let st = a.data;
    while (st.state === "working") {
      vidSay("Fetching the video onto this PC" + (st.how ? " (" + st.how + ")" : "")
             + ": " + (st.pct || 0) + "%" + (st.title ? " · " + st.title : ""));
      await new Promise(r => setTimeout(r, 700));
      a = await Mice.Api.get("/api/video/fetch?id=" + encodeURIComponent(vidFetchId));
      if (!a.ok) { vidSay(a.says, true); return; }
      st = a.data;
    }
    if (st.state !== "done") {
      vidSay(st.error || "The link could not be fetched.", st.error !== "Stopped.");
      $("vidTech").textContent = st.tech || "";
      return;
    }
    vidSetSrc("/api/video/file?id=" + encodeURIComponent(vidFetchId),
              { kind: "link", url, id: vidFetchId, name: st.title || "video" });
  } finally {
    vidLinkBusy = false;
    $("vidFetchBtn").textContent = "Fetch";
  }
}

// ---- the person and the robot, in step ------------------------------------
function vidPlayBoth() {
  const v = $("vidPlayer");
  if (!v.src) return;
  if (!v.paused) { v.pause(); return; }
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (v.currentTime < from || v.currentTime >= to - 0.05) v.currentTime = from;
  v.muted = false;
  v.play().catch(e => vidSay("The video would not play: " + (e.message || e), true));
}
// Every frame while the page is open: the robot takes the made moves' pose at
// the video's moment and the skeleton its frame, whether the video plays or
// is dragged along. Nothing changes while the video stands still, so a click
// on a move's row (vidSee) is not overwritten.
function vidTick() {
  if (!vidOn) return;
  requestAnimationFrame(vidTick);
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration) || vidBusy || playing) return;
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (!v.paused && v.currentTime >= to) v.pause();
  const ms = Math.round((v.currentTime - from) * 1000);
  if (ms === vidLastMs) return;
  vidLastMs = ms;
  vidShowAt(ms);
}
function vidShowAt(ms) {
  if (vidFrames && vidFrames.length) {
    const f = vidFrames[Math.max(0, Math.min(vidFrames.length - 1, Math.round(ms * VID_FPS / 1000)))];
    vidDraw($("vidSkel").checked && ms >= 0 ? f.p : null);
  }
  if (vidMade && vidMade.keys.length && ms >= 0) {
    pose = easeKeys(vidMade.keys, Math.max(0, ms - vidMade.start)).pose;
    applyPose();
  }
  $("vidClock").textContent = ms >= 0 ? (ms / 1000).toFixed(1) + " s" : "";
}

// ---- after "Use as new moves": the moves are Studio's own ------------------
function vidOnBar(first) {
  vidFirstKey = first;
  vidHeld = null;                 // the time bar's pose is the editor's now
  $("vidSoundBox").hidden = !vidSrc;
}
// The video's sound as the music of the first video move: the hub cuts the
// same part the moves were made from (ffmpeg) and it goes onto the robot's
// card the way any track does (uploadMusicFile). A picked file is copied to
// the hub first; a link is already there.
async function vidSound() {
  const k = keys[vidFirstKey];
  if (!vidSrc || !k) return;
  if (!haveRobot()) {
    vidSay("Connect the robot first (Robot tab): the music goes onto its card.", true);
    return;
  }
  const btn = $("vidSoundBtn");
  btn.disabled = true;
  try {
    if (!vidSrc.id && vidSrc.file) {
      vidSay("Copying the video to this PC's hub for its sound…");
      const r = await fetch("/api/video/put?name=" + encodeURIComponent(vidSrc.name),
                            { method: "POST", body: vidSrc.file }).catch(() => null);
      const j = r ? await r.json().catch(() => ({})) : {};
      if (!r || !j.ok) {
        vidSay(j.need_login ? VID_LOGIN : "The video could not be copied: "
               + (j.error || "the hub is not answering"), true);
        return;
      }
      vidSrc.id = j.id;
    }
    vidSay("Taking the sound out of the video…");
    const from = (+$("vidFrom").value || 0) + (vidMade ? vidMade.start / 1000 : 0);
    const a = await Mice.Api.post("/api/video/sound",
                                  { id: vidSrc.id, from, to: +$("vidTo").value || 0 });
    if (!a.ok) { vidSay(a.needLogin ? VID_LOGIN : a.says, true); return; }
    const r = await fetch("/api/video/file?kind=sound&id=" + encodeURIComponent(vidSrc.id));
    if (!r.ok) { vidSay("The sound was made but could not be read back.", true); return; }
    const name = robotTrackName((vidSrc.name || "video").replace(/\.[^.]*$/, "").slice(0, 40) + ".mp3");
    await uploadMusicFile(k, new File([await r.blob()], name, { type: "audio/mpeg" }), Object.assign(
      (track, why, renamed) => {
        if (!track) { vidSay("The sound did not reach the robot: " + why, true); return; }
        setCueTrack(k, track, false);
        renderTimeline();
        vidSay("♪ " + track + " is on the robot's card and plays with the first video move"
               + (renamed || "") + ". Save to keep it.");
      }, { busy: (t) => vidSay(t) }));
  } finally { btn.disabled = false; }
}

// ---- the choices ride in the project file -----------------------------------
// Saved with the moves, so a reopened project knows its video and how its
// moves were made; the video itself is not saved (a link is fetched again).
function vidSettings() {
  if (!vidSrc) return vidSaved;
  return { src: { kind: vidSrc.kind, name: vidSrc.name, url: vidSrc.url || "" },
           detail: $("vidDetail").value, mirror: $("vidMirror").checked,
           music: $("vidMusic").checked, waist: $("vidWaist").checked,
           hand: [$("vidHand0").value, $("vidHand1").value],
           from: +$("vidFrom").value || 0, to: +$("vidTo").value || 0 };
}
function vidApplySettings(s) {
  vidSaved = s && typeof s === "object" ? s : null;
  if (!vidSaved) return;
  vidFill();
  const pick = (sel, id) => { if (sel && [...sel.options].some(o => o.value === id)) sel.value = id; };
  pick($("vidDetail"), s.detail);
  (s.hand || []).forEach((h, a) => pick($("vidHand" + a), h));
  $("vidMirror").checked = !!s.mirror;
  $("vidMusic").checked = s.music !== false;
  $("vidWaist").checked = !!s.waist;
  $("vidFrom").value = String(s.from || 0);
  if (s.to) $("vidTo").value = String(s.to);
  if (s.src && s.src.url) $("vidLink").value = s.src.url;
  if (s.src) vidSay("These moves were made from " + (s.src.url ? "a link: press Fetch to see it again."
    : "the file " + s.src.name + ": pick it again to see it."));
}
// --- dummy link ---
// The dummy is a hand-posed copy of the robot: the same 10 joints, a pot on
// each instead of a servo (firmware type "dummy", COMMANDS.md). It is its OWN
// module with its own link, separate from the robot's: usually the same RS485
// dongle with a different bus id, but it can be on another cable or on WiFi.
// It answers POSE? exactly like the robot, so its pose drops straight into
// `pose` and every path that already works for a pose (keyframes, live send)
// works for it unchanged.
// "Simulated" is a dummy made of sliders on this page, so every mode can be
// tried with no dummy built yet. It answers through the same parser as a real
// one, so what it proves about the rest of the page is real.
let dummySim = null;          // simulated pot angles, or null when not simulating
let dummyFollowOn = false;    // the follow loop is running
let dummyLast = null;         // the last pose read, for "did it move"
let dummySafePose = null;     // the last pose the ROBOT was sent that was clear (A46-1)
let dummyRobotFollowing=false;
let dummyHeld = "";           // why the robot is holding, until a safe send
let dummyRec = null;          // while recording: [{ pose, ms }]

function dummySource() { return $("dummySrc").value; }
function dummyBus() { const v = $("dummyBus").value.trim(); return v ? parseInt(v, 10) : 0; }

function dummySrcChanged(boot) {
  const s = dummySource();
  $("dummyPort").style.display = s === "usb" ? "" : "none";
  $("dummyRescan").style.display = s === "usb" ? "" : "none";
  $("dummyBusWrap").style.display = s === "usb" ? "" : "none";
  $("dummyIpWrap").style.display = s === "wifi" ? "" : "none";
  $("dummySimBox").style.display = s === "sim" ? "" : "none";
  // Not on page load: the port list is asked for when someone uses this card.
  if (s === "usb" && !boot && !$("dummyPort").dataset.loaded) dummyLoadPorts();
  if (s === "sim") dummyBuildSim();
}

async function dummyLoadPorts() {
  const sel = $("dummyPort");
  try {
    const r = await fetch("/api/ports").then(r => r.json());
    const ps = (r.ports || []).filter(p => !p.bt);
    sel.innerHTML = "<option value=''>pick the USB port…</option>";
    ps.forEach(p => {
      const o = document.createElement("option");
      o.value = p.port;
      o.textContent = p.port + (p.who ? " — " + p.who : (p.desc ? " — " + p.desc : ""));
      sel.appendChild(o);
    });
    // The dummy usually hangs on the robot's own RS485 dongle: offer that one.
    const robotPort = $("usbPort") ? $("usbPort").value : "";
    if (robotPort && ps.some(p => p.port === robotPort)) sel.value = robotPort;
    else if (ps.length === 1) sel.value = ps[0].port;
    sel.dataset.loaded = "1";
  } catch (e) {
    sel.innerHTML = "<option value=''>the port list needs the hub</option>";
  }
}

// One command to the dummy, on its own link. Reply text, or throws.
async function dummyCmd(c) {
  const s = dummySource();
  if (s === "sim") {
    if (c.toUpperCase() !== "POSE?") return "OK";
    return dummySim.map(v => (v === null ? "-" : fmtA(v))).join(" ");
  }
  let url;
  if (s === "usb") {
    const port = $("dummyPort").value;
    if (!port) throw new Error("pick the USB port the dummy is on");
    url = `/api/usb/cmd?port=${encodeURIComponent(port)}&id=${dummyBus()}&c=${encodeURIComponent(c)}`;
  } else {
    const ip = $("dummyIp").value.trim();
    if (!ip) throw new Error("type the dummy's address");
    url = `/api/robot/cmd?ip=${encodeURIComponent(ip)}&c=${encodeURIComponent(c)}`;
  }
  const r = await fetch(url);
  const t = (await r.text()).trim();
  if (!r.ok) {
    let msg = t;
    try { msg = JSON.parse(t).error || t; } catch (e) { /* plain text */ }
    throw new Error(msg);
  }
  return t;
}

// "90.0 45.5 - ..." -> [90, 45.5, null, ...]. '-' is a joint with no pot: it
// is left where it is, the same rule the robot's POSE applies to '-'.
function parseDummyPose(text) {
  const tok = String(text || "").trim().split(/\s+/);
  if (tok.length < ARMJ || tok.some(t => t !== "-" && !isFinite(parseFloat(t))))
    throw new Error("the dummy did not answer with a pose (" + String(text).slice(0, 40) + ")");
  return Array.from({ length: NJ }, (_, i) =>
    (tok[i] === undefined || tok[i] === "-") ? null : parseFloat(tok[i]));
}

async function dummyRead() {
  const vals = parseDummyPose(await dummyCmd("POSE?"));
  dummyLast = vals;
  return vals;
}

// Put the dummy's pose into the editor. The robot model's limits apply, so a
// dummy bent further than the robot may go shows (and sends) the limit.
function dummyApply(vals) {
  pose = pose.map((cur, i) => (vals[i] === null ? cur : clampJ(i, vals[i])));
  applyPose(); renderSliders();
}

async function dummyConnect() {
  try {
    const v = await dummyRead();
    const n = v.filter(x => x !== null).length;
    $("dummyStat").textContent = "dummy answers ✓ — " + n + " of " + NJ + " joints have a pot";
  } catch (e) {
    $("dummyStat").textContent = "no answer from the dummy: " + (e.message || e);
    notice($("dummyStat").textContent);
  }
}

// ---- follow: Studio (and optionally the robot) copies the dummy ------------
// One read in flight at a time, like sendPoseLive: the loop paces itself to
// the link, and a slow bus cannot pile up requests.
function dummyFollowChanged() {
  const mode = $("dummyFollow").value;
  if(dummyRobotFollowing && mode!=='robot')cancelSafeMotion('dummy follow stopped');
  dummyRobotFollowing=mode==='robot';
  if(mode==='robot')dummySafePose=null; // first sample must reach the robot even if already displayed
  if (mode !== "off") {
    if (mode === "robot" && !(haveUsb() || haveWifi())) {
      $("dummyStat").textContent = "connect the robot first (Robot link above), then pick this again";
      notice($("dummyStat").textContent);
      $("dummyFollow").value = "studio";
    }
    // Two things steering the editor at once would fight: stop the monitor
    // (editor follows robot) and any playback.
    if ($("monChk").checked) { $("monChk").checked = false; monitorChanged(); }
    if (playing) togglePlay();
    if (!dummyFollowOn) { dummyFollowOn = true; dummyFollowTick(); }
  } else {
    dummyFollowOn = false;
    dummySafePose = null;      // the next follow starts from wherever the arm is
    dummyHeld = "";
  }
}
// The robot copies the dummy only along a way that misses its own body
// (A46-1, user 2026-10-22). The straight move is checked first; a hit gets a
// way round, planned within liveBudgetMs so the follow stays live. Nothing in
// time, or a dummy pose the robot's body cannot take: the robot HOLDS its last
// safe pose and the line says so. Studio still shows the dummy as it is.
function dummySafeSend() {
  const want = pose.slice();
  const plan = planSafe(dummySafePose || want, want, SAFE.liveBudgetMs);
  if (plan.fail) {
    dummyHeld = "robot holds its last safe pose: " + plan.fail;
    return false;
  }
  dummyHeld = "";
  // The shared dispatcher replans from the reported pose. Sending preview
  // waypoints separately would let newest-goal coalescing drop them.
  sendPoseLive();
  dummySafePose = want;
  return true;
}
// ---- record what the dummy does, then keep it as a saved move -------------
function dummyRecToggle() {
  if (!dummyRec) {
    if ($("dummyFollow").value === "off") { $("dummyFollow").value = "studio"; dummyFollowChanged(); }
    dummyRec = [{ pose: pose.slice(), ms: performance.now() }];   // where it starts
    $("dummyRecBtn").textContent = "■ Stop and save";
    $("dummyStat").textContent = "recording the dummy: move it, then press Stop and save";
    return;
  }
  const rec = dummyRec;
  dummyRec = null;
  $("dummyRecBtn").textContent = "● Record the dummy";
  return dummyRecSave(rec);
}
// One key per real change (2 deg or more), timed as it was done, then the
// same safety pass as a video; on the time bar and saved under one name.
async function dummyRecSave(rec) {
  const K = [];
  for (const r of rec) {
    const prev = K[K.length - 1];
    if (!prev) { K.push({ pose: r.pose, t: 1000, hold: 0, ms: r.ms }); continue; }
    if (deltaDeg(prev.pose, r.pose) < 2) continue;
    K.push({ pose: r.pose, t: Math.max(MIN_MOVE_MS, Math.round(r.ms - prev.ms)), hold: 0, tset: true, ms: r.ms });
  }
  if (K.length < 2) { $("dummyStat").textContent = "nothing to keep: the dummy did not move"; return false; }
  const safe = safeKeys(K.map(({ ms, ...k }) => k));
  if (safe.keys.length < 2) { $("dummyStat").textContent = "nothing to keep: every pose would make the robot hit itself"; return false; }
  if (!(await askUnsaved("replace the time bar with the recording"))) return false;
  keys = safe.keys; bumpKeys(); clearBadMarks(); clampKeyTimes();
  selKey = 0; pose = [...keys[0].pose]; poseChanged(false); renderTimeline();
  setWorkName("dummy_" + new Date().toISOString().slice(0, 16).replace(/[-:T]/g, ""));
  const ok = await saveAll();
  $("dummyStat").textContent = keys.length + " moves recorded. " + safeSay(safe) + " " + $("tlStat").textContent;
  return ok;
}
async function dummyFollowTick() {
  if (!dummyFollowOn) return;
  const mode = $("dummyFollow").value;
  try {
    const prev = dummyLast;
    const v = await dummyRead();
    const moved = (mode==='robot' && !dummySafePose) || !prev || v.some((x, i) => (x === null) !== (prev[i] === null) ||
                                       (x !== null && Math.abs(x - prev[i]) >= 0.2));
    if (moved && dummyFollowOn && mode===$("dummyFollow").value) {
      dummyApply(v);
      if (dummyRec) dummyRec.push({ pose: pose.slice(), ms: performance.now() });
      // The robot gets the pose through the same live path a slider drag
      // uses: its timing comes from the link, and the robot's own LIMIT and
      // max_dps still decide how far and how fast it really goes.
      if (mode === "robot") dummySafeSend();
    }
    $("dummyStat").textContent = mode === "robot" && dummyHeld ? dummyHeld
      : (mode === "robot" ? "robot + Studio follow" : "Studio follows") + " the dummy"
        + (dummyRec ? " (recording)" : "");
  } catch (e) {
    $("dummyStat").textContent = "dummy: no answer (" + (e.message || e) + ") — still trying";
  }
  if (dummyFollowOn) setTimeout(dummyFollowTick, 80);
}

// ---- the dummy and the sequence -------------------------------------------
async function dummyToNewKey() {
  try { dummyApply(await dummyRead()); addKey(); $("dummyStat").textContent = "dummy pose saved as move " + selKey; }
  catch (e) { $("dummyStat").textContent = "" + (e.message || e); }
}
async function dummyToSelectedKey() {
  if (!keys[selKey]) { $("dummyStat").textContent = "select a move in the timeline first"; return; }
  try { dummyApply(await dummyRead()); updateKey(); $("dummyStat").textContent = "move " + selKey + " now holds the dummy pose"; }
  catch (e) { $("dummyStat").textContent = "" + (e.message || e); }
}
// Send the REAL robot to the selected move, at that move's own speed.
function robotToSelectedKey() {
  const k = keys[selKey];
  if (!k) { $("dummyStat").textContent = "select a move in the timeline first"; return; }
  if (!(haveUsb() || haveWifi())) { $("dummyStat").textContent = "connect the robot first (Robot link above)"; return; }
  if ($("dummyFollow").value !== "off") { $("dummyFollow").value = "off"; dummyFollowChanged(); }
  const from = pose.slice();
  const tgt = k.pose.map((v, i) => clampJ(i, v));
  const ms = Math.max(keyTravelMs(selKey), autoTime(from, tgt, keyDps(selKey)), MIN_MOVE_MS);
  selectKey(selKey);           // the model goes there too; with live on it also sends
  if (!$("liveChk").checked) robotCmd("POSE " + tgt.map(fmtA).join(" ") + " T " + Math.round(ms));
  $("dummyStat").textContent = "robot moving to move " + selKey;
}

// ---- simulated dummy: sliders standing in for the pots ---------------------
function dummyBuildSim() {
  const box = $("dummySimRows");
  if (!dummySim) dummySim = pose.slice();
  if (box.dataset.built) return;
  box.dataset.built = "1";
  for (let i = 0; i < NJ; i++) {
    const r = document.createElement("div"); r.className = "row";
    const l = document.createElement("span"); l.className = "lbl"; l.textContent = JOINT_LABELS[i];
    const s = document.createElement("input"); s.type = "range"; s.min = 0; s.max = 180; s.step = 0.5;
    s.value = dummySim[i]; s.style.flex = "1"; s.id = "dsim" + i;
    const v = document.createElement("span"); v.className = "mini"; v.style.minWidth = "40px";
    v.textContent = fmtA(dummySim[i]) + "°";
    s.oninput = () => { dummySim[i] = parseFloat(s.value); v.textContent = fmtA(dummySim[i]) + "°"; };
    r.append(l, s, v); box.appendChild(r);
  }
}

window.addEventListener("DOMContentLoaded", function () {
  if (!document.getElementById("dummySrc")) return;
  dummySrcChanged(true);
  $("dummyPort").addEventListener("focus", () => {
    if (!$("dummyPort").dataset.loaded) dummyLoadPorts();
  });
});
// --- freeze watch ---
// User 2026-09-17: the whole Studio page freezes, while playing, dragging, in
// live mode, and sometimes doing nothing. It did not reproduce headless (0 long
// tasks, fake robot), so the page records it where it happens: a frame gap over
// FREEZE_MS while the tab is visible sends one report to the hub (/api/report)
// with what was running and the slowest recent hub calls.
const FREEZE_MS = 1500;
const _fw = { last: 0, hiddenSince: 0, sentAt: -1e9, calls: [], longs: [] };
(function () {
  const realFetch = window.fetch.bind(window);
  window.fetch = function (url, opts) {            // remember how long hub calls take
    const t0 = performance.now(), u = String(url && url.url || url).slice(0, 90);
    const done = () => {
      _fw.calls.push({ u, ms: Math.round(performance.now() - t0), at: Math.round(t0) });
      if (_fw.calls.length > 40) _fw.calls.shift();
    };
    const p = realFetch(url, opts);
    p.then(done, done);
    return p;
  };
  try {
    new PerformanceObserver(l => l.getEntries().forEach(e => {
      _fw.longs.push({ ms: Math.round(e.duration), at: Math.round(e.startTime) });
      if (_fw.longs.length > 20) _fw.longs.shift();
    })).observe({ entryTypes: ["longtask"] });
  } catch (e) { /* older browser: frame gaps still count */ }
  document.addEventListener("visibilitychange", () => {
    _fw.hiddenSince = document.hidden ? performance.now() : 0;
    _fw.last = 0;                                  // a hidden tab is not a freeze
  });
})();
function freezeCheck(now) {
  const gap = _fw.last ? now - _fw.last : 0;
  _fw.last = now;
  if (gap < FREEZE_MS || document.hidden || now - _fw.sentAt < 30000) return;
  _fw.sentAt = now;
  const gi = (renderer && renderer.info) || {};
  const state = {
    gapMs: Math.round(gap), playing: typeof playing !== "undefined" && playing,
    live: !!($("liveChk") && $("liveChk").checked),
    monitor: !!($("monChk") && $("monChk").checked),
    auto: haveAuto(), usb: haveUsb(), wifi: haveWifi(), keys: keys.length,
    gpu: { geometries: gi.memory && gi.memory.geometries, textures: gi.memory && gi.memory.textures,
           programs: gi.programs && gi.programs.length },
    heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
    longTasks: _fw.longs.filter(x => x.at > now - gap - 2000),
    slowCalls: _fw.calls.filter(c => c.ms > 300 || c.at > now - gap - 2000).slice(-15),
  };
  fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: "STUDIO FREEZE " + JSON.stringify(state), page: "studio",
                           time: new Date().toISOString(), attachDiag: false }) }).catch(() => {});
}
// --- distances in the 3D view (A26-44) ---
//
// User 2026-09-17: *see the distance between the point that i need to know in
// robot ... elbow and hand or elbow -> elbow ... hold that key or can click*.
// Click Distances (or hold D) to see dashed lines with the length in mm.
// User 2026-10-21 added shoulder->elbow and shoulder->hand on each side. The
// pairs are DATA in distances.json: a new pair is an entry there, not code.
let distPairs = null;        // null = not read yet, [] = none listed
let distOn = false;          // switched on by the button
let distHeld = false;        // on while D is held
let distLines = [];
const distLayer = document.createElement("div");
distLayer.id = "distLayer";
distLayer.hidden = true;
viewport.appendChild(distLayer);

// The points a pair may name, as L_<part> or R_<part>; a new kind of point is
// one entry here. shoulder = the shrug anchor both shoulder servos turn about
// (buildArm hangs joint groups 0/4 on it), so shoulder->elbow is upperLen.
// Live world positions only: fkPoints() moves WAIST/SHRUG while it measures.
const DIST_POINTS = {
  shoulder: side => shrugAnchors[side],
  elbow: side => elbowBalls[side === "L" ? 0 : 1],   // arm 0 is the robot's left (+X)
  hand: side => wristBalls[side === "L" ? 0 : 1],
};
function distPoint(name) {   // world position of a named point, or null
  const m = /^([LR])_([a-z]+)$/.exec(name || "");
  const pick = m && Object.prototype.hasOwnProperty.call(DIST_POINTS, m[2]) ? DIST_POINTS[m[2]] : null;
  const obj = pick ? pick(m[1]) : null;
  return obj ? obj.getWorldPosition(new THREE.Vector3()) : null;
}
async function distLoad() {
  if (distPairs) return;
  try {
    const j = await fetch("distances.json").then(r => r.json());
    distPairs = (j.pairs || []).filter(p => p && p.from && p.to);
  } catch (e) {
    distPairs = [];
    distLayer.dataset.note = "the list of distances (distances.json) could not be read";
  }
}
function distShown() { return distOn || distHeld; }
function distSet(on) {
  distOn = on;
  const b = $("distBtn");
  if (b) { b.classList.toggle("on", on); b.setAttribute("aria-pressed", on ? "true" : "false"); }
  distLoad().then(distDraw);
}
function distClear() {
  distLines.forEach(l => { scene.remove(l); l.geometry.dispose(); l.material.dispose(); });
  distLines = [];
  distLayer.textContent = "";
}
// Called every frame from tick(); does nothing while switched off.
function distDraw() {
  if (!distShown() || !distPairs) {
    if (distLines.length || !distLayer.hidden) { distClear(); distLayer.hidden = true; }
    return;
  }
  distClear();
  distLayer.hidden = false;
  scene.updateMatrixWorld();
  const cam = activeCam(), rect = renderer.domElement.getBoundingClientRect();
  const color = getComputedStyle(document.documentElement).getPropertyValue("--acc").trim() || "#4ea1ff";
  let drawn = 0;
  distPairs.forEach(p => {
    const a = distPoint(p.from), b = distPoint(p.to);
    if (!a || !b) return;
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    const line = new THREE.Line(g, new THREE.LineDashedMaterial(
      { color: new THREE.Color(color), dashSize: 8, gapSize: 6, depthTest: false }));
    line.computeLineDistances();
    line.renderOrder = 30;
    scene.add(line);
    distLines.push(line);
    const mid = a.clone().add(b).multiplyScalar(0.5).project(cam);
    if (mid.z > 1) return;                      // behind the camera
    const tag = document.createElement("span");
    tag.className = "distTag";
    tag.textContent = Math.round(a.distanceTo(b)) + " mm";
    tag.title = p.label || (p.from + " to " + p.to);
    tag.style.left = ((mid.x + 1) / 2 * rect.width) + "px";
    tag.style.top = ((1 - mid.y) / 2 * rect.height) + "px";
    distLayer.appendChild(tag);
    drawn++;
  });
  if (!drawn) {
    const n = document.createElement("span");
    n.className = "distNote";
    n.textContent = distLayer.dataset.note || "no distances to show — the robot model is not built yet";
    distLayer.appendChild(n);
  }
}
window.addEventListener("keydown", (e) => {
  if (e.key !== "d" && e.key !== "D") return;
  const t = e.target;
  if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;  // typing a "d"
  if (!distHeld) { distHeld = true; distLoad().then(distDraw); }
});
window.addEventListener("keyup", (e) => { if (e.key === "d" || e.key === "D") distHeld = false; });
window.addEventListener("blur", () => { distHeld = false; });
// --- moves while talking (A46-1) ---
// User 2026-10-22: gestures that fit the words, made with the robot's own size
// and shared between the Voice page and Studio. The library is
// config/gestures.json on the hub (plus this PC's own, saved by this card);
// Studio is where the body lives, so Studio FITS it: hand targets -> joint
// angles by IK on this rig, every pose and every move checked by safe_path.js,
// and the result posted to the hub, which only times and plays it. A fit is
// redone when the rig or a gesture changes: when the Sequence tab opens, or
// after the page has been left alone a while (TALK_IDLE_MS).
let TALK = { lib: null, fit: null, busy: false, hub: false };
const TALK_IDLE_MS = 20000;
let talkIdleAt = performance.now();
["pointerdown", "keydown", "wheel"].forEach(e => window.addEventListener(e, () => { talkIdleAt = performance.now(); }, true));

function talkSay(s) { if ($("talkStat")) $("talkStat").textContent = s; }
// The rig as it shapes a gesture: sizes, calibration and limits. A change to
// any of it changes where a hand lands, so it is part of what was fitted.
function talkRigSnap() {
  const r = JSON.parse(JSON.stringify(RIG));
  return { dims: r.dims, zero: r.zero, axis: r.axis, invert: r.invert, offset: r.offset,
           tilt: r.tilt, min: r.min, max: r.max, home: r.home, palmTurn: r.palmTurn };
}
async function talkLoad() {
  try {
    const j = await fetch("/api/gestures").then(r => r.json());
    if (!j.ok) throw new Error(j.error || "no answer");
    if (TALK.character !== j.character) TALK.events = null;
    TALK.character = j.character || ""; TALK.revision = j.gestureRevision || ""; TALK.readOnly = !!j.readOnly;
    TALK.lib = j.lib; TALK.fit = j.fit || {}; TALK.hub = true;
  } catch (e) {
    TALK.hub = false;                 // Studio on its own server: no hub, no card
  }
  talkRender();
  return TALK.hub;
}
function talkStale() {
  const L = TALK.lib, F = TALK.fit || {};
  if (!L) return false;
  if (JSON.stringify(F.rigFull || null) !== JSON.stringify(talkRigSnap())) return true;
  if (JSON.stringify(F.restDef || null) !== JSON.stringify((L.rest || {}).keys || null)) return true;
  const defs = F.defs || {};
  return Object.keys(L.gestures || {}).some(id => JSON.stringify(defs[id] || null) !== JSON.stringify(L.gestures[id].keys || null))
    || Object.keys(defs).some(id => !(L.gestures || {})[id]);
}
// One key of the library -> a pose on this rig. `from` is where the arms come
// from (IK starts there, so a gesture flows), `restArm` holds a hand left out.
function talkKeyPose(k, from, restArm, mirror) {
  const p = from.slice();
  const sideOf = a => (a === 0 ? 1 : -1);
  const tgt = [mirror ? k.R : k.L, mirror ? k.L : k.R];
  const palm = [mirror ? k.palmR : k.palmL, mirror ? k.palmL : k.palmR];
  if (k.pose) return k.pose.map((v, j) => clampJ(j, v));          // a pose made on the time bar
  p[8] = clampJ(8, RIG.home[8] + (mirror ? -1 : 1) * (k.waist || 0));
  p[9] = clampJ(9, RIG.home[9] + (k.shrug || 0));
  for (const a of [0, 1]) {
    const idx = a === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    if (!tgt[a]) { idx.forEach(j => { p[j] = restArm[j]; }); continue; }
    pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
    const S = bodyGroup.worldToLocal(jointGroups[idx[0]].parent.getWorldPosition(new THREE.Vector3()));
    const d = RIG.dims, reach = a === 0 ? d.upperLenL + d.foreLenL : d.upperLenR + d.foreLenR;
    const v = tgt[a];
    const local = new THREE.Vector3(S.x + sideOf(a) * v[0] * reach, S.y + v[1] * reach, S.z + v[2] * reach);
    solveIK(a, bodyGroup.localToWorld(local), 24);
    let q = pose.slice();
    if (palm[a] === "up" || palm[a] === "down") {
      const f = facePalm(q, a, palm[a] === "up" ? 1 : -1);
      if (f) q = f.pose;
    }
    idx.forEach(j => { p[j] = clampJ(j, q[j]); });
  }
  return p;
}
// A gesture's keys from `start`, made safe: { keys, in, out } or { bad }
function talkFitOne(def, mirror, restPose) {
  const raw = [];
  let from = restPose;
  for (const k of def) {
    const p = talkKeyPose(k, from, restPose, mirror);
    const hit = poseHit(p);
    if (hit) return { bad: hit };
    raw.push({ pose: p, t: k.t || 400, hold: k.hold || 0 });
    from = p;
  }
  // inside the gesture: a hitting move gets in-between keys (marked via)
  const inner = safeKeys(raw);
  if (inner.failed || inner.dropped) return { bad: "a move inside it has no safe way" };
  const leg = (a, b) => {
    const r = planSafe(a, b);
    return r.fail ? null : r.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true }));
  };
  const ins = leg(restPose, inner.keys[0].pose), outs = leg(inner.keys[inner.keys.length - 1].pose, restPose);
  if (!ins || !outs) return { bad: "no safe way from the resting hands" };
  return { keys: inner.keys.map(k => ({ pose: k.pose, t: k.t, hold: k.hold || 0, via: !!k.via })), in: ins, out: outs };
}
// The whole library, a gesture per tick so the page stays live.
async function talkFit() {
  if (TALK.busy || !TALK.lib || !robot) return false;
  TALK.busy = true;
  const saved = pose.slice();
  const L = TALK.lib, fit = { rig: { min: RIG.min.slice(), max: RIG.max.slice(), home: RIG.home.slice() },
    rigFull: talkRigSnap(), restDef: (L.rest || {}).keys || [], defs: {}, gestures: {}, bad: {}, direct: [],
    at: new Date().toISOString() };
  try {
    talkSay("Fitting the gestures to this robot…");
    const home = RIG.home.map((v, j) => clampJ(j, v));
    const restDef = (L.rest || {}).keys || [];
    const restKeys = [];
    let from = home;
    for (const k of restDef) { const p = talkKeyPose(k, from, home, false); restKeys.push({ pose: p, t: k.t || 600, hold: k.hold || 0 }); from = p; }
    if (!restKeys.length || poseHit(restKeys[restKeys.length - 1].pose)) throw new Error("the resting hands hit the body on this robot");
    const restPose = restKeys[restKeys.length - 1].pose;
    const rIn = planSafe(home, restKeys[0].pose), rOut = planSafe(restPose, home);
    if (rIn.fail || rOut.fail) throw new Error("no safe way from home to the resting hands");
    fit.rest = { keys: restKeys,
                 in: rIn.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true })),
                 out: rOut.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true })) };
    for (const [id, g] of Object.entries(L.gestures || {})) {
      await new Promise(r => setTimeout(r, 0));
      fit.defs[id] = g.keys || [];
      for (const m of g.mirror && !(g.keys || []).some(k => k.pose) ? [false, true] : [false]) {
        const vid = id + (m ? "~m" : "");
        const one = talkFitOne(g.keys || [], m, restPose);
        if (one.bad) fit.bad[vid] = one.bad; else fit.gestures[vid] = one;
      }
      pose = saved.slice(); applyPose();
    }
    // which gesture may flow straight into which, without resting between
    const ids = Object.keys(fit.gestures);
    for (const a of ids) for (const b of ids) {
      const ka = fit.gestures[a].keys, kb = fit.gestures[b].keys;
      if (a !== b && !pathHit(ka[ka.length - 1].pose, kb[0].pose)) fit.direct.push(a + ">" + b);
    }
    const r = await fetch("/api/gestures/fit", { method: "POST", body: JSON.stringify({...fit, character:TALK.character, gestureRevision:TALK.revision}) }).then(x => x.json());
    if (!r.ok) throw new Error(r.error || "the hub did not keep it");
    TALK.fit = fit; TALK.revision = r.gestureRevision || TALK.revision;
    talkRender();
    return true;
  } catch (e) {
    talkSay("The gestures could not be fitted: " + (e.message || e));
    return false;
  } finally {
    pose = saved; applyPose();
    TALK.busy = false;
  }
}
async function talkCheckFit() {
  if (!TALK.lib && !(await talkLoad())) return;
  if (talkStale()) await talkFit();
}
// The Sequence tab opened (showTab), or the page sat still long enough.
function talkShown() { talkCheckFit(); }
setInterval(() => {
  if (!TALK.busy && !document.hidden && performance.now() - talkIdleAt > TALK_IDLE_MS && typeof robot !== "undefined" && robot) {
    talkIdleAt = performance.now();
    talkCheckFit();
  }
}, 5000);

// ---- the card ----------------------------------------------------------------
function talkRender() {
  const card = $("talkCard");
  if (!card) return;
  card.hidden = !TALK.hub;
  if (!TALK.hub) return;
  const L = TALK.lib, F = TALK.fit || {};
  $("talkOn").checked = L.on !== false;
  const sel = $("talkManner"), keep = sel.value;
  sel.textContent = "";
  Object.keys(L.manners || {}).filter(m => m !== "_default").forEach(m => {
    const o = document.createElement("option"); o.value = o.textContent = m; sel.appendChild(o);
  });
  sel.value = keep || "friendly";
  const n = Object.keys(F.gestures || {}).length, bad = Object.keys(F.bad || {});
  talkSay(talkStale() ? "The gestures are not fitted to this robot as it is now. They will be in a moment."
    : n + " gestures fitted to this robot and kept clear of its body."
      + (bad.length ? " Left out on this robot: " + bad.map(b => talkName(b) + " (" + F.bad[b] + ")").join(", ") + "." : ""));
  const list = $("talkList");
  list.textContent = "";
  Object.entries(L.gestures || {}).forEach(([id, g]) => {
    const row = document.createElement("div"); row.className = "row";
    const name = document.createElement("span"); name.className = "lbl"; name.textContent = g.label || id;
    const words = document.createElement("input");
    words.style.flex = "1"; words.style.minWidth = "0";
    words.title = "Words that bring this gesture, a comma between. Any language.";
    words.value = [].concat(...Object.values(g.words || {})).join(", ");
    words.onchange = () => talkSave({ gestures: { [id]: { words: { any: words.value.split(",").map(s => s.trim()).filter(Boolean) } } } });
    const show = document.createElement("button");
    show.textContent = "▶"; show.title = "Put this gesture on the time bar, fitted to this robot";
    show.onclick = () => talkShowOne(id);
    row.append(name, words, show);
    if (g.mine) {
      const del = document.createElement("button");
      del.textContent = "✕"; del.title = "Remove this gesture";
      del.onclick = () => talkSave({ gestures: { [id]: null } });
      row.append(del);
    }
    list.appendChild(row);
  });
  talkEvents();
}
function talkName(vid) {
  const g = ((TALK.lib || {}).gestures || {})[vid.replace(/~m$/, "")] || {};
  return (g.label || vid) + (vid.endsWith("~m") ? " (other arm)" : "");
}
async function talkSave(change) {
  try {
    const j = await fetch("/api/gestures", { method: "POST", body: JSON.stringify({...change, character: TALK.character, gestureRevision: TALK.revision}) }).then(r => r.json());
    if (!j.ok) throw new Error(j.error || "not saved");
    TALK.lib = j.lib; TALK.revision = j.gestureRevision || TALK.revision;
    talkRender();
    talkCheckFit();
  } catch (e) { talkSay("Not saved: " + (e.message || e)); notice($("talkStat").textContent); }
}
function talkSaveSwitch() { talkSave({ on: $("talkOn").checked }); }
// The events are the Voice page's scenarios: one switch each.
async function talkEvents() {
  const box = $("talkEvents");
  if (!box) return;
  if (!TALK.events) {            // asked once: the voice helper may be far away or off
    TALK.events = [];
    try { TALK.events = ((await fetch("/api/voice/config").then(r => r.json())).config?.scenarios || []).map(s => s.name).filter(Boolean); }
    catch (e) { /* no voice settings here: no events to list */ }
  }
  const names = TALK.events;
  box.textContent = "";
  if (!names.length) { box.textContent = "No events are set up on the Voice page yet."; return; }
  names.forEach(n => {
    const lab = document.createElement("label"); lab.className = "row";
    const c = document.createElement("input"); c.type = "checkbox";
    c.checked = ((TALK.lib.events || {})[n] || {}).on !== false;
    c.onchange = () => talkSave({ events: { [n]: Object.assign({}, (TALK.lib.events || {})[n], { on: c.checked }) } });
    lab.append(c, document.createTextNode(" " + n));
    box.appendChild(lab);
  });
}
// Steps from the hub (or a fit) -> the time bar, pinned to their own times.
async function talkToBar(steps, what) {
  if (!(await askUnsaved(what))) return false;
  keys = steps.map((s, i) => ({ pose: s.pose.map((v, j) => clampJ(j, v)), t: i ? s.t : 1000, hold: s.hold || 0, tset: i > 0 }));
  bumpKeys(); clearBadMarks();
  selKey = 0; pose = [...keys[0].pose]; poseChanged(false); renderTimeline();
  return true;
}
async function talkTry() {
  const text = $("talkText").value.trim();
  if (!text) { talkSay("Type something the robot might say."); return; }
  await talkCheckFit();
  const j = await fetch("/api/gestures/plan", { method: "POST", body: JSON.stringify({
    text, manner: $("talkManner").value, seed: Math.floor(Math.random() * 1e9) }) }).then(r => r.json()).catch(e => ({ why: String(e) }));
  if (!j.ok) { talkSay(j.why || j.error || "No gestures for that."); return; }
  if (!(await talkToBar(j.steps, "put these gestures on the time bar"))) return;
  $("talkPicks").textContent = j.picks.length
    ? j.picks.map(p => (p.at / 1000).toFixed(1) + " s " + p.label + (p.mirrored ? " (other arm)" : "") + (p.word ? " ← “" + p.word + "”" : "")).join(" · ")
    : "No word asked for a gesture and no beat fitted.";
  $("tlStat").textContent = "Gestures for " + (j.ms / 1000).toFixed(1) + " s of talk are on the time bar. Press Play to watch; press Show again for another random pick.";
}
async function talkShowOne(id) {
  await talkCheckFit();
  const F = TALK.fit || {}, g = (F.gestures || {})[id], rest = F.rest;
  if (!g || !rest) { talkSay(talkName(id) + " is not fitted to this robot: " + ((F.bad || {})[id] || "fit it first")); return; }
  const steps = [{ pose: rest.keys[rest.keys.length - 1].pose, t: 0, hold: 300 }]
    .concat(g.in, g.keys, g.out, [{ pose: rest.keys[rest.keys.length - 1].pose, t: 500, hold: 0 }]);
  if (await talkToBar(steps, "show this gesture on the time bar")) $("tlStat").textContent = talkName(id) + " is on the time bar. Press Play to watch.";
}
// The time bar as a new gesture: its poses as they are (made on this robot),
// checked like every other gesture when it is fitted.
async function talkAddFromBar() {
  const name = $("talkNewName").value.trim();
  if (!name) { talkSay("Give the gesture a name first."); return; }
  const K = playKeys();
  if (K.length < 1) { talkSay("Put at least one move on the time bar first."); return; }
  const id = "mine_" + name.toLowerCase().replace(/[^\w]+/g, "_");
  await talkSave({ gestures: { [id]: { label: name, mine: true,
    words: { any: $("talkNewWords").value.split(",").map(s => s.trim()).filter(Boolean) },
    keys: K.map(k => ({ pose: k.pose.map(v => Math.round(v * 10) / 10), t: Math.round(k.t || 400), hold: Math.round(k.hold || 0) })) } } });
  talkSay(name + " is kept as a gesture. It is fitted and checked next, then the Voice page can use it.");
}
window.addEventListener("load", () => setTimeout(talkLoad, 800));
// --- main loop ---
function resize() {
  const w = viewport.clientWidth, h = viewport.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  syncOrtho();                    // the ortho frustum follows the new aspect
  viewport.classList.toggle("short", h < 260);
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
  if (entryHold) { lastPlayMs = 0; return; }   // the arm is still travelling to keyframe 0
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
      // seg === K.length is the loop's travel back to the start pose
      const to = seg === K.length ? { pose: K[0].pose, t: loopReturnMs() } : K[seg];
      const tt = to.t - rem <= 50 ? to.t : rem;
      liveSend("POSE " + to.pose.map(fmtA).join(" ") + " T " + tt);
    }
  }
}

let _dirty3d = 60;
function markDirty3d(n) { _dirty3d = Math.max(_dirty3d, n || 10); }
if (typeof controls !== "undefined" && controls && controls.addEventListener) {
  controls.addEventListener("change", function () { markDirty3d(5); });
}

function tick(now) {
  requestAnimationFrame(tick);
  freezeCheck(now);
  _drawing = true;         // this pass may paint; the interval's may not
  playTick();               // no-op when the interval already advanced it
  _drawing = false;
  lastFrame = now;
  distDraw();              // distances follow the pose and the camera (A26-44)
  const inMotion = controls ? controls.update() : false;
  const needRender = playing || inMotion || (typeof distShown === "function" && distShown()) || _dirty3d > 0;
  if (needRender) {
    if (!playing && !inMotion && (!distShown || !distShown()) && _dirty3d > 0) _dirty3d--;
    renderer.render(scene, activeCam());
  }
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
refreshShows(); renderShow();
refreshModels();
connModeChanged();
initSideDrag();
initTimeDrag();
// Boot is over: from here a change to the timeline is real work, so start
// keeping a draft of it, and offer back anything a previous session lost.
draftArmed = true;
markClean(workSig(), "");   // the untouched start is not unsaved work
offerDraft();
resize();
requestAnimationFrame((t) => { lastFrame = t; tick(t); });
// opened from the hub ("Studio + monitor" on a module): connect by itself,
// and with monitor=1 the 3D model immediately simulates the real robot.
//   ?ip=<addr>            WiFi
//   ?dev=wifi:<ip>        same, hub's dev syntax
//   ?dev=usb:COM7[:<id>]  the cable, SHARED through the hub — the module
//                         website can stay open on that same port
//   ?dev=auto:<board>      ask the hub for the fastest route on every call
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
  window.HUB_AUTO = inner.indexOf("auto:") === 0 ? inner : "";

  if (window.HUB_AUTO) {
    connectRobot().then(startMonitor);
  } else if (inner.indexOf("usb:") === 0) {
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
// The login is the HUB's login (user 2026-09-17). Studio used to check a
// local-only account list, so it opened while the hub still answered every
// robot command with "log in before doing that". Local accounts are used only
// when there is no hub at all (Studio opened from a file).
function loggedIn(u) {
  currentUser = u;
  $("loginStat").textContent = "";
  showTab(sideTab);
  window.dispatchEvent(new Event('resize'));
  if (pendingConnect) {
    const pending = pendingConnect;
    pendingConnect = null;
    connectRobot().then(pending.resolve, pending.reject);
  }
}
async function appLogin() {
  const u = $("loginUser").value.trim();
  const p = $("loginPass").value;
  let ok = false, why = "";
  try {
    const r = await fetch("/api/login", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: u, password: p }) });
    const j = await r.json().catch(() => ({}));
    ok = r.ok && !!j.ok;
    why = j.locked_for > 0 ? `Too many tries. Wait ${j.locked_for} seconds.` : "";
  } catch (e) {
    const acc = getAccounts();                 // no hub: local accounts only
    ok = !!(acc[u] && acc[u] === p);
  }
  if (ok) {
    $("loginPass").value = "";
    localStorage.removeItem("nongZeroCred");   // old copy of a password; the zero lock asks the hub now
    loggedIn(u);
  } else {
    $("loginStat").textContent = why || "Wrong username or password.";
  }
}
// Logged in on the hub page (or another tab)? Then Studio is logged in too.
async function syncHubLogin() {
  if (currentUser) return;
  try {
    const j = await fetch("/api/whoami").then(r => r.json());
    if (j.authed && !currentUser) loggedIn(j.user || "user");
  } catch (e) { /* no hub: the login card stays */ }
}
window.addEventListener("load", syncHubLogin);
window.addEventListener("focus", syncHubLogin);
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
