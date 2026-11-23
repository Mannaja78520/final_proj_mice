"use strict";
const $ = (id) => document.getElementById(id);
const STAB_BTN = {
  pose: "tabBtnMove",
  sequence: "tabBtnSeq",
  video: "tabBtnVideo",
  shows: "tabBtnShows",
  robot: "tabBtnRobot",
  setup: "tabBtnSetup"
};
let sideTab = "pose";
let noticeSaid = null;
function notice(text, ask) {
  const box = $("notice"), t = $("noticeText");
  if (!box || !t || !text) return;
  if (text === noticeSaid && box.hidden) return;
  noticeSaid = text;
  t.textContent = text;
  box.className = ask ? "banner warn" : "banner err";
  if (ask) (ask.actions || []).forEach((a) => {
    const b = document.createElement("button");
    b.textContent = a.label;
    if (a.id) b.id = a.id;
    b.onclick = () => {
      a.run();
      clearNotice();
    };
    t.append(document.createTextNode(" "), b);
  });
  box.hidden = false;
}
function clearNotice() {
  const box = $("notice");
  if (box) box.hidden = true;
}
let OPEN_WITHOUT_LOGIN = [];
fetch("settings_open.json").then((r) => r.json()).then((j) => {
  OPEN_WITHOUT_LOGIN = Array.isArray(j.open) ? j.open : [];
  if (!currentUser) showTab(sideTab);
}).catch(() => {
});
function showTab(which) {
  if (which === "move") which = "pose";
  if (!STAB_BTN[which]) which = "pose";
  sideTab = which;
  if (which === "shows" && typeof refreshShows === "function") refreshShows();
  if (which === "sequence" && typeof talkShown === "function") talkShown();
  let renderWhich = which;
  if (!currentUser && (which === "robot" || which === "setup")) {
    renderWhich = "login";
  }
  $("tabMove").style.display = "";
  $("tabSetup").style.display = "";
  document.querySelectorAll("[data-stab]").forEach((el) => {
    const tab = el.classList.contains("floating") ? el.dataset.stab : which;
    const shows = !currentUser && (tab === "robot" || tab === "setup") ? "login" : tab;
    const open = shows === "login" && el.dataset.stab === tab && OPEN_WITHOUT_LOGIN.includes(el.id);
    el.style.display = el.dataset.stab === (el.classList.contains("floating") ? shows : renderWhich) || open ? "" : "none";
  });
  const userCard = $("userManageCard");
  if (userCard) {
    userCard.style.display = currentUser === "super_admin" && renderWhich === "setup" ? "" : "none";
    if (userCard.style.display === "") populateUserList();
  }
  Object.keys(STAB_BTN).forEach((k) => {
    const b = $(STAB_BTN[k]);
    if (b) b.classList.toggle("on", k === which);
  });
  if (typeof vidPage === "function") vidPage(which === "video");
}
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[id^=tabBtn]");
  if (!b || window.innerWidth > 860 || !$("side")) return;
  setTimeout(() => $("side").scrollIntoView({ behavior: "smooth", block: "start" }), 50);
});
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
    tl.style.maxHeight = h === null ? "" : "none";
    if (h === null) {
      tl.style.height = "";
      localStorage.removeItem("nong_timeh");
    } else tl.style.height = Math.min(maxH(), Math.max(MINH, Math.round(h))) + "px";
    handle.setAttribute("aria-valuenow", parseInt(tl.style.height) || 0);
    resize();
    if (remember && h !== null) localStorage.setItem("nong_timeh", parseInt(tl.style.height));
  };
  const saved = +localStorage.getItem("nong_timeh");
  if (saved) setHeight(saved, false);
  const now = () => parseInt(tl.style.height) || tl.getBoundingClientRect().height;
  handle.addEventListener("keydown", (e) => {
    let h = null, hit = true;
    if (e.key === "ArrowUp") h = now() + STEP;
    else if (e.key === "ArrowDown") h = now() - STEP;
    else if (e.key === "PageUp") h = now() + STEP * 4;
    else if (e.key === "PageDown") h = now() - STEP * 4;
    else if (e.key === "Home") {
      setHeight(null, true);
      e.preventDefault();
      return;
    } else hit = false;
    if (!hit) return;
    e.preventDefault();
    setHeight(h, true);
  });
  handle.addEventListener("dblclick", () => setHeight(null, true));
  let dragging = false, startY = 0, startH = 0;
  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    startY = e.clientY;
    startH = now();
    try {
      handle.setPointerCapture(e.pointerId);
    } catch (_) {
    }
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
function initSideDrag() {
  const side = $("side"), handle = $("sideDrag");
  const saved = +localStorage.getItem("nong_sidew");
  if (saved) side.style.width = Math.min(640, Math.max(240, saved)) + "px";
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
    resize();
    if (remember) localStorage.setItem("nong_sidew", parseInt(side.style.width) || 320);
  };
  announce();
  handle.addEventListener("keydown", (e) => {
    const now = parseInt(side.style.width) || 320;
    let w = null;
    if (e.key === "ArrowLeft") w = now + STEP;
    else if (e.key === "ArrowRight") w = now - STEP;
    else if (e.key === "Home") w = 320;
    else if (e.key === "PageUp") w = now + STEP * 4;
    else if (e.key === "PageDown") w = now - STEP * 4;
    if (w === null) return;
    e.preventDefault();
    setWidth(w, true);
  });
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
window.addEventListener("DOMContentLoaded", function() {
  var h = (location.hash || "").replace("#", "");
  if (h && typeof showTab === "function") showTab(h);
});
window.addEventListener("hashchange", function() {
  var h = (location.hash || "").replace("#", "");
  if (h && typeof showTab === "function") showTab(h);
});
const FOLD_KEY = "nong_folded";
function initCardFold() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(FOLD_KEY)) || {};
  } catch (e) {
  }
  const byTab = {};
  document.querySelectorAll("#side div.card[data-stab]").forEach((c) => {
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
        try {
          localStorage.setItem(FOLD_KEY, JSON.stringify(saved));
        } catch (e) {
        }
      };
      set(key in saved ? saved[key] : tab === "setup" || i > 0, false);
      const toggle = (e) => {
        if (e.target.closest("label, input, button, select, a")) return;
        set(!card.classList.contains("folded"), true);
      };
      h.addEventListener("click", toggle);
      h.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle(e);
        }
      });
    });
  });
}
initCardFold();
const ARMJ = 8, NJ = 10;
const JOINT_NAMES = [
  "L_SH_P",
  "L_SH_R",
  "L_EL_P",
  "L_EL_R",
  "R_SH_P",
  "R_SH_R",
  "R_EL_P",
  "R_EL_R",
  "WAIST",
  "SHRUG"
];
const JOINT_LABELS = [
  "L shoulder pitch",
  "L shoulder roll",
  "L elbow pitch",
  "L elbow roll",
  "R shoulder pitch",
  "R shoulder roll",
  "R elbow pitch",
  "R elbow roll",
  "Waist (turn L/R)",
  "Shrug (rock: L up / R down)"
];
const DEFAULT_AXIS = ["x", "z", "x", "z", "x", "z", "x", "z", "y", "x"];
const AXIS_LABEL = { x: "roll (X)", y: "pitch (Y)", z: "yaw (Z)" };
const BASE_DIR = [-1, 1, -1, 1, -1, -1, -1, -1, 1, 1];
const HANDS = [{ side: "L", label: "Left hand" }, { side: "R", label: "Right hand" }];
const DEFAULT_RIG = {
  extraClearanceMm: 0,
  // extra space BETWEEN parts, above the 4 mm base
  // left and right arm lengths are separate — an STL on one side never
  // changes the other side.
  // DEFAULTS SCALED TO THE REAL ROBOT (measured from nong_assembly.STEP, mm):
  //   spherical shoulder/elbow joints ~89 mm (ball r ~42), shrug yoke ~260 mm
  //   wide, upper-arm bar 52 mm, forearm bar 96 mm, spine (body_shaft) 250 mm.
  //   Central "torso" here stands in for the slim spine + shrug yoke.
  dims: {
    shoulderX: 120,
    shoulderY: 110,
    upperLenL: 110,
    upperLenR: 110,
    foreLenL: 130,
    foreLenR: 130,
    torsoW: 100,
    torsoH: 250,
    torsoD: 70,
    // SHRUG see-saw pivot: the bearing it rocks about sits ABOVE the
    // shoulder line (not on the servo). mm measured up from the shoulder
    // line. 0 = rock about the shoulder line itself.
    shrugPivot: 60
  },
  // A48-1 robot look (urdf_view.js / urdf_view.json): which look, which URDF,
  // whose sizes the simple shapes use ("urdf" or "custom"), your own sizes
  // kept while the URDF's are in use, and the URDF's last measured sizes.
  view: { look: "rig", model: "", sizes: "custom", custom: null, urdfDims: null, oldRig: null, cadAt: "" },
  zero: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
  axis: [...DEFAULT_AXIS],
  // rotation axis per joint (roll/pitch/yaw)
  invert: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  neutral: [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
  // the show's "Neutral pose" (Studio only)
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
  gearGear: [18, 18, 13, 13, 18, 18, 13, 13, 1, 1],
  pulseMin: [500, 500, 500, 500, 500, 500, 500, 500, 500, 500],
  pulseMax: [2500, 2500, 2400, 2400, 2500, 2500, 2400, 2400, 2500, 2400],
  servoMaxDps: [375, 375, 400, 400, 375, 375, 400, 400, 200, 400],
  // How the horn FOLLOWS a target (servo_follow.js, A48-24): its answer delay
  // in ms and its acceleration in °/s² of the joint. Guesses until measured on
  // the bench (lab-day.md); they only change Studio's picture and the sim.
  servoLagMs: [40, 40, 40, 40, 40, 40, 40, 40, 60, 40],
  servoAccel: [3e3, 3e3, 4e3, 4e3, 3e3, 3e3, 4e3, 4e3, 1500, 4e3],
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
  tilt: [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
  // A48-6 (user 2026-10-23 "make it like the CAD"): what a CAD needs that the
  // tilts alone cannot say, filled by "Make the simple shapes match the CAD"
  // (rig_from_cad.js). after = a fixed turn AFTER each servo (roll/pitch/yaw
  // deg): a CAD bone need not be square to its joint's axis. mount = each
  // shoulder's offset (mm) from the symmetric spot. order = each arm's joints
  // from the body out, as the CAD chains them. Defaults change nothing.
  after: [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
  mount: { L: [0, 0, 0], R: [0, 0, 0] },
  order: [[0, 1, 2, 3], [4, 5, 6, 7]],
  // SIZES per universal joint / per bar, indexed like PAIRS:
  //   0 = L shoulder, 1 = L elbow, 2 = R shoulder, 3 = R elbow
  // bar hanging from it (0/1 = L upper arm / L forearm, 2/3 = R upper / R fore).
  // Scaled to the real spherical joints (~89 mm dia -> r ~42) and ~10 mm bars.
  jointR: [42, 40, 42, 40],
  barR: [12, 10, 12, 10],
  // Where the palm sits around each forearm, degrees about the bar [L, R].
  // Set in Setup by turning the drawn hand until it matches the real one.
  palmTurn: [0, 0]
};
function mergeRig(saved) {
  const r = {
    ...JSON.parse(JSON.stringify(DEFAULT_RIG)),
    ...saved,
    dims: { ...DEFAULT_RIG.dims, ...saved.dims || {} },
    view: { ...DEFAULT_RIG.view, ...saved.view || {} }
  };
  if (saved.dims && saved.dims.upperLen !== void 0) {
    r.dims.upperLenL = r.dims.upperLenR = saved.dims.upperLen;
    delete r.dims.upperLen;
  }
  if (saved.dims && saved.dims.foreLen !== void 0) {
    r.dims.foreLenL = r.dims.foreLenR = saved.dims.foreLen;
    delete r.dims.foreLen;
  }
  const fixLen = (k) => {
    const def = DEFAULT_RIG[k];
    if (typeof r[k] === "number") r[k] = new Array(NJ).fill(r[k]);
    if (!Array.isArray(r[k])) {
      r[k] = [...def];
      return;
    }
    r[k] = def.map((d, i) => r[k][i] !== void 0 ? r[k][i] : d);
  };
  if (!Array.isArray(r.home) && Array.isArray(r.neutral)) r.home = [...r.neutral];
  [
    "zero",
    "min",
    "max",
    "axis",
    "invert",
    "neutral",
    "home",
    "offset",
    "gearPinion",
    "gearGear",
    "pulseMin",
    "pulseMax",
    "servoMaxDps",
    "servoRange",
    "frameHz",
    "servoLagMs",
    "servoAccel"
  ].forEach(fixLen);
  delete r.frontArm;
  r.palmTurn = [0, 1].map((i) => {
    const v = Array.isArray(r.palmTurn) ? +r.palmTurn[i] : 0;
    return isFinite(v) ? (v % 360 + 360) % 360 : 0;
  });
  if (!Array.isArray(r.shrugCurve)) r.shrugCurve = [];
  r.shrugCurve = r.shrugCurve.filter((pt) => pt && isFinite(+pt.j)).map((pt) => ({ j: +pt.j, l: +pt.l || 0, r: +pt.r || 0 }));
  if (!Array.isArray(r.tilt)) r.tilt = JSON.parse(JSON.stringify(DEFAULT_RIG.tilt));
  r.tilt = DEFAULT_RIG.tilt.map((d, i) => Array.isArray(r.tilt[i]) && r.tilt[i].length === 3 ? r.tilt[i] : [...d]);
  r.after = DEFAULT_RIG.after.map((d, i) => Array.isArray(r.after) && Array.isArray(r.after[i]) && r.after[i].length === 3 ? r.after[i].map((v) => +v || 0) : [...d]);
  const m3 = (v) => Array.isArray(v) && v.length === 3 ? v.map((x) => +x || 0) : [0, 0, 0];
  r.mount = { L: m3((r.mount || {}).L), R: m3((r.mount || {}).R) };
  r.order = [0, 4].map((b, a) => {
    const o = Array.isArray(r.order) && Array.isArray(r.order[a]) ? r.order[a].map(Number) : [];
    const ok = o.length === 4 && [o[0], o[1]].sort().join() === [b, b + 1].join() && [o[2], o[3]].sort().join() === [b + 2, b + 3].join();
    return ok ? o : [b, b + 1, b + 2, b + 3];
  });
  if (!Array.isArray(r.jointR) || r.jointR.length !== 4) r.jointR = [...DEFAULT_RIG.jointR];
  if (!Array.isArray(r.barR) || r.barR.length !== 4) r.barR = [...DEFAULT_RIG.barR];
  return r;
}
if (window.NONG_RIG_DEFAULT && typeof window.NONG_RIG_DEFAULT === "object") {
  try {
    Object.assign(DEFAULT_RIG, mergeRig(JSON.parse(JSON.stringify(window.NONG_RIG_DEFAULT))));
  } catch (e) {
    console.warn("shipped rig_default ignored:", e);
  }
}
let RIG = JSON.parse(JSON.stringify(DEFAULT_RIG));
try {
  const saved = JSON.parse(localStorage.getItem("nong_rig") || "null");
  if (saved) RIG = mergeRig(saved);
} catch (e) {
}
const RIG_CAD_KEYS = ["dims", "tilt", "after", "mount", "order"];
function rigCadAdopt(r, cad) {
  if (!cad || typeof cad !== "object" || typeof cad.at !== "string" || r.view.cadAt === cad.at) return false;
  const copy = (v) => JSON.parse(JSON.stringify(v));
  if (cad.parts && typeof cad.parts === "object") {
    if (!r.view.oldRig) r.view.oldRig = copy(RIG_CAD_KEYS.reduce((o, k) => (o[k] = r[k], o), {}));
    Object.assign(r.dims, cad.parts.dims || {});
    ["tilt", "after", "mount", "order"].forEach((k) => {
      if (cad.parts[k]) r[k] = copy(cad.parts[k]);
    });
    r.view.sizes = "cad";
  } else if (r.view.oldRig) {
    RIG_CAD_KEYS.forEach((k) => {
      if (r.view.oldRig[k] !== void 0) r[k] = copy(r.view.oldRig[k]);
    });
    r.view.oldRig = null;
    r.view.sizes = "custom";
  }
  r.view.cadAt = cad.at;
  return true;
}
try {
  if (rigCadAdopt(RIG, window.NONG_RIG_CAD)) {
    RIG = mergeRig(RIG);
    localStorage.setItem("nong_rig", JSON.stringify(RIG));
  }
} catch (e) {
  console.warn("rig parts from the CAD ignored:", e);
}
function saveRig() {
  localStorage.setItem("nong_rig", JSON.stringify(RIG));
}
function saveRigDefault() {
  localStorage.setItem("nong_rig_default", JSON.stringify(RIG));
  if (typeof $ === "function" && $("limStat"))
    $("limStat").textContent = "saved the current rig as your default — Reset now returns to this ✓";
}
async function shipRigDefault() {
  try {
    const r = await fetch("/api/rigdefault", {
      method: "POST",
      body: JSON.stringify({ rig: RIG })
    }).then((r2) => r2.json());
    if (r.ok) {
      $("limStat").textContent = "saved this rig as the factory default — every fresh browser now starts on it, and Reset returns to it ✓";
    } else {
      $("limStat").textContent = "could not save: " + (r.error || "unknown");
      notice($("limStat").textContent);
    }
  } catch (e) {
    notice(Mice.fail($("limStat"), "could not save", e));
  }
}
function loadRigDefault() {
  try {
    const d = JSON.parse(localStorage.getItem("nong_rig_default") || "null");
    return d ? mergeRig(d) : null;
  } catch (e) {
    return null;
  }
}
function hasRigDefault() {
  return !!localStorage.getItem("nong_rig_default");
}
const SETTINGS_KEYS = [
  "nong_rig",
  "nong_rig_default",
  "nong_meshes",
  "nong_sidew",
  "nong_ask_unsaved"
];
function collectSettings() {
  const b = { kind: "mice-studio-settings", version: 1, rig: RIG, keys: {} };
  SETTINGS_KEYS.forEach((k) => {
    const v = localStorage.getItem(k);
    if (v !== null) b.keys[k] = v;
  });
  return b;
}
function applySettings(b, where) {
  if (!b || b.kind !== "mice-studio-settings")
    throw new Error("that file is not a Studio settings export");
  const keys2 = b.keys || {};
  let n = 0;
  SETTINGS_KEYS.forEach((k) => {
    if (typeof keys2[k] === "string") {
      localStorage.setItem(k, keys2[k]);
      n++;
    }
  });
  if (b.rig) {
    RIG = mergeRig(b.rig);
    saveRig();
  }
  loadMeshes();
  rigChanged();
  setSettingsStat("loaded " + n + " setting(s) from " + where + (b.savedBy ? " (" + b.savedBy + ")" : "") + (b.savedAt ? " saved " + b.savedAt : "") + " — kept in this browser's cache ✓");
  return n;
}
function setSettingsStat(msg) {
  const el = $("setStat");
  if (el) el.textContent = msg;
}
function exportSettings() {
  const blob = new Blob(
    [JSON.stringify(collectSettings(), null, 1)],
    { type: "application/json" }
  );
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mice-studio-settings.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5e3);
  setSettingsStat("exported — copy this file to the other PC and use Import ✓");
}
function importSettingsFile(input) {
  const f = input.files && input.files[0];
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try {
      applySettings(JSON.parse(rd.result), f.name);
    } catch (e) {
      setSettingsStat("could not import: " + Mice.Words.plain(e).says);
    }
    input.value = "";
  };
  rd.readAsText(f);
}
async function shareSettings() {
  try {
    const r = await fetch("/api/settings", {
      method: "POST",
      body: JSON.stringify({ bundle: collectSettings() })
    }).then((r2) => r2.json());
    setSettingsStat(r.ok ? "shared from this PC ✓ — on the other PC open Studio, press Find PCs, and Get" : "could not share: " + (r.error || "unknown"));
  } catch (e) {
    setSettingsStat("could not share: " + Mice.Words.plain(e).says);
  }
}
async function findHubs() {
  const sel = $("hubList");
  if (!sel) return;
  setSettingsStat("looking for other PCs on this network…");
  sel.innerHTML = "<option value=''>looking…</option>";
  try {
    const r = await fetch("/api/hubs?force=1").then((r2) => r2.json());
    const hubs = (r.hubs || []).filter((h) => h.has);
    sel.innerHTML = "";
    hubs.forEach((h) => {
      const o = document.createElement("option");
      o.value = h.ip;
      o.textContent = h.ip + (h.name ? " — " + h.name : "") + (h.savedAt ? " (" + h.savedAt + ")" : "");
      sel.appendChild(o);
    });
    if (!hubs.length) sel.innerHTML = "<option value=''>none found</option>";
    setSettingsStat(hubs.length ? hubs.length + " PC(s) have shared settings — pick one and press Get" : "no other PC on this network has shared settings yet. On that PC, open Studio and press Share.");
  } catch (e) {
    sel.innerHTML = "<option value=''>search failed</option>";
    setSettingsStat("could not search: " + Mice.Words.plain(e).says);
  }
}
async function getSettingsFrom() {
  const host = $("hubList") && $("hubList").value || $("hubHost") && $("hubHost").value || "";
  if (!host) {
    setSettingsStat("pick a PC first, or type its address");
    return;
  }
  try {
    const b = await fetch("/api/settings/peer?host=" + encodeURIComponent(host)).then((r) => r.json());
    if (b.error) {
      setSettingsStat("could not get it: " + b.error);
      return;
    }
    applySettings(b, host);
  } catch (e) {
    setSettingsStat("could not get it: " + Mice.Words.plain(e).says);
  }
}
function jdir(i) {
  return BASE_DIR[i] * (RIG.invert[i] ? -1 : 1);
}
function clampJ(i, v) {
  return Math.min(RIG.max[i], Math.max(RIG.min[i], Math.round(v * 10) / 10));
}
const PAIRS = [
  { joints: [0, 1], label: "L shoulder" },
  { joints: [2, 3], label: "L elbow" },
  { joints: [4, 5], label: "R shoulder" },
  { joints: [6, 7], label: "R elbow" }
];
let currentUser = null;
let pendingConnect = null;
let pose = RIG.neutral.map((v, i) => clampJ(i, v));
let keys = [];
let selKey = 0;
let selPair = -1;
let playing = false, playT = 0, lastFrame = 0, lastLiveSeg = -1;
const MESH_PARTS = ["torso", "head", "L_upper", "L_fore", "R_upper", "R_fore"];
const MESH_COLORS = {
  torso: "#3a4a5e",
  head: "#3a4a5e",
  L_upper: "#4d7fd0",
  L_fore: "#4d7fd0",
  R_upper: "#d0854d",
  R_fore: "#d0854d"
};
function defMeshCfg(part) {
  return {
    file: "",
    tex: "",
    rot: [0, 0, 0],
    off: [0, 0, 0],
    scale: 1,
    color: MESH_COLORS[part] || "#8a94a6"
  };
}
let meshCfg = {};
MESH_PARTS.forEach((p) => meshCfg[p] = defMeshCfg(p));
let addons = [];
function loadMeshes() {
  try {
    const mSaved = JSON.parse(localStorage.getItem("nong_meshes") || "null");
    if (!mSaved) return false;
    MESH_PARTS.forEach((p) => meshCfg[p] = { ...defMeshCfg(p), ...(mSaved.meshCfg || {})[p] });
    addons = mSaved.addons || [];
    return true;
  } catch (e) {
    return false;
  }
}
loadMeshes();
function saveMeshes() {
  localStorage.setItem("nong_meshes", JSON.stringify({ meshCfg, addons }));
}
let modelFiles = [];
const MIN_MOVE_MS = 80;
let SAFE_DPS = 60;
let MUSIC_DPS = 0;
let PACE_OVERRIDE = null;
let SEQ_MUSIC_DPS = null;
let boardSafeDpsMax = 0;
let boardSafePeer = 0;
let boardSafeIdentity = "";
const viewport = $("viewport");
const displayPolicy = window.MiceResources;
function makeRenderer() {
  try {
    return new THREE.WebGLRenderer({ antialias: displayPolicy ? displayPolicy.display().antialias : true });
  } catch (e) {
    const note = document.createElement("div");
    note.className = "no3d";
    note.style.cssText = "padding:24px;text-align:center;color:var(--mut,#667);font-size:15px;line-height:1.5";
    note.textContent = "This device cannot draw the 3D robot. The sliders, the timeline and playing on the robot still work. For the 3D view, open Studio in a newer browser or on a newer computer.";
    return { noWebGL: true, domElement: note, info: {}, setPixelRatio() {
    }, setSize() {
    }, render() {
    } };
  }
}
const renderer = makeRenderer();
if (displayPolicy) displayPolicy.applyRenderer(renderer, window.devicePixelRatio);
else renderer.setPixelRatio(window.devicePixelRatio);
window.addEventListener("mice-resource-change", function() {
  if (displayPolicy) displayPolicy.applyRenderer(renderer, window.devicePixelRatio);
  if (typeof markDirty3d === "function") markDirty3d(10);
});
renderer.outputEncoding = THREE.sRGBEncoding;
viewport.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim());
const camera = new THREE.PerspectiveCamera(50, 1, 1, 8e3);
const orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, -1e4, 2e4);
let usingOrtho = false;
function activeCam() {
  return usingOrtho ? orthoCam : camera;
}
function syncOrtho() {
  const dist = camera.position.distanceTo(controls ? controls.target : new THREE.Vector3()) || 700;
  const h = 2 * dist * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
  const w = h * (camera.aspect || 1);
  orthoCam.left = -w / 2;
  orthoCam.right = w / 2;
  orthoCam.top = h / 2;
  orthoCam.bottom = -h / 2;
  orthoCam.position.copy(camera.position);
  orthoCam.up.copy(camera.up);
  orthoCam.quaternion.copy(camera.quaternion);
  orthoCam.updateProjectionMatrix();
}
function useProjection(ortho) {
  if (ortho === usingOrtho) {
    if (ortho) syncOrtho();
    return;
  }
  usingOrtho = ortho;
  if (ortho) syncOrtho();
  else {
    camera.position.copy(orthoCam.position);
    camera.up.copy(orthoCam.up);
    camera.quaternion.copy(orthoCam.quaternion);
  }
  controls.object = activeCam();
  controls.update();
}
camera.position.set(380, 240, 560);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(0, -20, 0);
controls.enableDamping = true;
const VIEWS = {
  front: { dir: [0, 0, 1], up: [0, 1, 0], plane: "xy" },
  back: { dir: [0, 0, -1], up: [0, 1, 0], plane: "xy" },
  right: { dir: [1, 0, 0], up: [0, 1, 0], plane: "yz" },
  left: { dir: [-1, 0, 0], up: [0, 1, 0], plane: "yz" },
  top: { dir: [0, 1, 0], up: [0, 0, -1], plane: "xz" },
  bottom: { dir: [0, -1, 0], up: [0, 0, 1], plane: "xz" },
  iso: { dir: [0.6, 0.42, 0.68], up: [0, 1, 0], plane: "cam" }
};
let viewPlane = "";
function flatView() {
  return !!viewPlane;
}
function setView(name) {
  const v = VIEWS[name];
  if (!v) return;
  const t = controls.target;
  const dist = camera.position.distanceTo(t) || 700;
  const dir = new THREE.Vector3(...v.dir).normalize();
  const p1 = t.clone().add(dir.multiplyScalar(dist));
  camera.up.set(...v.up);
  camera.position.copy(p1);
  camera.lookAt(t);
  useProjection(v.plane !== "cam");
  controls.update();
  viewPlane = v.plane === "cam" ? "" : v.plane;
  controls.enableRotate = !viewPlane;
  if ($("dragPlane")) $("dragPlane").value = v.plane;
  document.querySelectorAll("#viewCube button").forEach((b) => b.classList.toggle("on", b.dataset.view === name));
  viewCubeOpen(false);
}
function viewCubeOpen(open) {
  const cube = $("viewCube"), btn = $("viewCubeBtn");
  if (!cube) return;
  if (open === void 0) open = !cube.classList.contains("open");
  cube.classList.toggle("open", open);
  if (btn) btn.setAttribute("aria-expanded", String(open));
}
function viewForPlane(plane) {
  setView({ cam: "iso", xy: "front", yz: "right", xz: "top" }[plane] || "iso");
}
scene.add(new THREE.HemisphereLight(12571886, 2371646, 1));
const sun = new THREE.DirectionalLight(16777215, 0.9);
sun.position.set(300, 500, 400);
scene.add(sun);
const grid = new THREE.GridHelper(1200, 24, 2765890, 1844271);
grid.position.y = -250;
scene.add(grid);
const matWrist = new THREE.MeshStandardMaterial({ color: 4116366, emissive: 941114, roughness: 0.4 });
const matJoint = new THREE.MeshStandardMaterial({ color: 16765286, emissive: 5060608, roughness: 0.45 });
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
    color: tex ? "#ffffff" : cfg.color || "#8a94a6",
    map: tex || null,
    roughness: 0.65
  });
}
let robot = null;
let bodyGroup = null;
let shoulderMount = null;
const shrugAnchors = { L: null, R: null };
let shrugBaseY = 0;
let jointGroups = [];
let pickMeshes = [];
let wristBalls = [];
let elbowBalls = [];
let palmMarks = [];
const palmCache = /* @__PURE__ */ new Map();
let linkHolders = {};
let urdfOn = false;
let pairRingParents = [];
function linkVisual(name, defaultMesh) {
  const holder = new THREE.Group();
  holder.name = "link_" + name;
  holder.add(defaultMesh);
  linkHolders[name] = holder;
  return holder;
}
function armSegment(len, barR, jointR, mat, pairIdx) {
  const g = new THREE.Group();
  const ball = new THREE.Mesh(new THREE.SphereGeometry(jointR, 20, 14), matJoint);
  ball.userData.skel = true;
  const boneR = Math.max(1.5, Math.min(3, barR * 0.25));
  const bone = new THREE.Mesh(new THREE.CylinderGeometry(boneR, boneR, len, 8), matJoint);
  bone.position.y = -len / 2;
  bone.userData.skel = true;
  const tube = new THREE.Mesh(new THREE.CylinderGeometry(barR, barR * 0.82, len, 14), mat);
  tube.position.y = -len / 2;
  ball.userData.pair = bone.userData.pair = tube.userData.pair = pairIdx;
  pickMeshes.push(ball, bone, tube);
  g.add(ball, bone, tube);
  return g;
}
function buildArm(side) {
  const d = RIG.dims;
  const base = side > 0 ? 0 : 4;
  const pairSh = side > 0 ? 0 : 2, pairEl = side > 0 ? 1 : 3;
  const anchor = new THREE.Group();
  const mt = RIG.mount[side > 0 ? "L" : "R"];
  anchor.position.set(side * d.shoulderX + mt[0], -(d.shrugPivot || 0) + mt[1], mt[2]);
  shoulderMount.add(anchor);
  shrugAnchors[side > 0 ? "L" : "R"] = anchor;
  shrugBaseY = -(d.shrugPivot || 0);
  const ord = RIG.order[side > 0 ? 0 : 1];
  const shP = new THREE.Group();
  anchor.add(shP);
  const shR = new THREE.Group();
  shP.add(shR);
  jointGroups[ord[0]] = shP;
  jointGroups[ord[1]] = shR;
  const upperLen = side > 0 ? d.upperLenL : d.upperLenR;
  const foreLen = side > 0 ? d.foreLenL : d.foreLenR;
  const upperName = side > 0 ? "L_upper" : "R_upper";
  shR.add(linkVisual(upperName, armSegment(
    upperLen,
    RIG.barR[pairSh],
    RIG.jointR[pairSh],
    partMat(upperName),
    pairSh
  )));
  const elAnchor = new THREE.Group();
  elAnchor.position.set(0, -upperLen, 0);
  shR.add(elAnchor);
  const elbowMat = new THREE.MeshBasicMaterial({ color: 16750916, depthTest: false });
  const elbowBall = new THREE.Mesh(new THREE.SphereGeometry(12, 18, 12), elbowMat);
  elbowBall.userData.arm = side > 0 ? 0 : 1;
  elbowBall.renderOrder = 19;
  elAnchor.add(elbowBall);
  elbowBalls.push(elbowBall);
  const elP = new THREE.Group();
  elAnchor.add(elP);
  const elR = new THREE.Group();
  elP.add(elR);
  jointGroups[ord[2]] = elP;
  jointGroups[ord[3]] = elR;
  const foreName = side > 0 ? "L_fore" : "R_fore";
  elR.add(linkVisual(foreName, armSegment(
    foreLen,
    RIG.barR[pairEl],
    RIG.jointR[pairEl],
    partMat(foreName),
    pairEl
  )));
  const handleMat = new THREE.MeshBasicMaterial({ color: 4116366, depthTest: false });
  const wrist = new THREE.Mesh(new THREE.SphereGeometry(14, 20, 14), handleMat);
  wrist.position.set(0, -foreLen, 0);
  wrist.userData.arm = side > 0 ? 0 : 1;
  wrist.renderOrder = 20;
  elR.add(wrist);
  wristBalls.push(wrist);
  const hand = new THREE.Group();
  hand.position.set(0, -foreLen, 0);
  hand.rotation.y = THREE.MathUtils.degToRad(RIG.palmTurn[side > 0 ? 0 : 1] || 0);
  const back = new THREE.Mesh(
    new THREE.BoxGeometry(34, 46, 5),
    new THREE.MeshStandardMaterial({ color: 8226192 })
  );
  back.position.y = -30;
  const palm = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 42),
    new THREE.MeshStandardMaterial({ color: 15906976 })
  );
  palm.position.set(0, -30, 2.6);
  back.userData.skel = palm.userData.skel = true;
  hand.add(back, palm);
  elR.add(hand);
  palmMarks.push(hand);
  return { anchor, shP, elAnchor, elP };
}
function buildRobot() {
  if (robot) {
    scene.remove(robot);
    robot.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      const m = o.material;
      if (!m) return;
      (Array.isArray(m) ? m : [m]).forEach((x) => {
        if (x && x.dispose) x.dispose();
      });
    });
  }
  robot = new THREE.Group();
  scene.add(robot);
  jointGroups = [];
  pickMeshes = [];
  wristBalls = [];
  elbowBalls = [];
  palmMarks = [];
  linkHolders = {};
  palmCache.clear();
  if (!urdfBuildInto(robot)) buildRigShapes();
  clearGizmo();
  selPair = -1;
  applyMeshes();
  applyPose();
}
function buildRigShapes() {
  bodyGroup = new THREE.Group();
  robot.add(bodyGroup);
  const d = RIG.dims;
  shoulderMount = new THREE.Group();
  shoulderMount.position.set(0, d.shoulderY + (d.shrugPivot || 0), 0);
  bodyGroup.add(shoulderMount);
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
  const armL = buildArm(1);
  const armR = buildArm(-1);
  pairRingParents = [0, 2, 4, 6].map((i) => [jointGroups[i].parent, jointGroups[i + 1].parent]);
}
const _AXVEC = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };
const _qBase = new THREE.Quaternion(), _qAxis = new THREE.Quaternion(), _eTilt = new THREE.Euler();
function jointTiltQuat(i, out) {
  const t = RIG.tilt[i] || [0, 0, 0];
  _eTilt.set(
    THREE.MathUtils.degToRad(t[0]),
    THREE.MathUtils.degToRad(t[1]),
    THREE.MathUtils.degToRad(t[2]),
    "XYZ"
  );
  return (out || new THREE.Quaternion()).setFromEuler(_eTilt);
}
function jointAfterQuat(i, out) {
  const t = RIG.after[i] || [0, 0, 0];
  _eTilt.set(
    THREE.MathUtils.degToRad(t[0]),
    THREE.MathUtils.degToRad(t[1]),
    THREE.MathUtils.degToRad(t[2]),
    "XYZ"
  );
  return (out || new THREE.Quaternion()).setFromEuler(_eTilt);
}
function jointAxisVec(i) {
  if (urdfOn) return urdfAxisVec(i);
  return _AXVEC[RIG.axis[i]].clone().applyQuaternion(jointTiltQuat(i)).normalize();
}
function jointDelta(i) {
  const p = pose[i], z = RIG.zero[i];
  const v = (Number.isFinite(p) ? p : 90) - (Number.isFinite(z) ? z : 90);
  return v * jdir(i);
}
function applyPose() {
  if (typeof markDirty3d === "function") markDirty3d(5);
  if (urdfOn) {
    urdfApplyPose();
    return;
  }
  for (let i = 0; i < ARMJ; i++) {
    const g = jointGroups[i];
    if (!g) continue;
    const ax = RIG.axis[i];
    const v = jointDelta(i);
    const t = RIG.tilt[i] || [0, 0, 0];
    _eTilt.set(
      THREE.MathUtils.degToRad(t[0]),
      THREE.MathUtils.degToRad(t[1]),
      THREE.MathUtils.degToRad(t[2]),
      "XYZ"
    );
    _qBase.setFromEuler(_eTilt);
    _qAxis.setFromAxisAngle(_AXVEC[ax], THREE.MathUtils.degToRad(v));
    g.quaternion.copy(_qBase).multiply(_qAxis);
    g.quaternion.multiply(jointAfterQuat(i, _qBase));
  }
  if (bodyGroup)
    bodyGroup.rotation.set(0, THREE.MathUtils.degToRad(jointDelta(8)), 0);
  if (shoulderMount) {
    const rise = shrugRise(pose[9]);
    if (rise) {
      shoulderMount.rotation.set(0, 0, 0);
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY + RIG.mount.L[1] + rise.l;
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY + RIG.mount.R[1] + rise.r;
    } else {
      if (shrugAnchors.L) shrugAnchors.L.position.y = shrugBaseY + RIG.mount.L[1];
      if (shrugAnchors.R) shrugAnchors.R.position.y = shrugBaseY + RIG.mount.R[1];
      shoulderMount.rotation.set(0, 0, THREE.MathUtils.degToRad(jointDelta(9)));
    }
  }
}
function renderShrugCurve() {
  const box = $("shrugCurve");
  if (!box) return;
  const c = RIG.shrugCurve || (RIG.shrugCurve = []);
  box.innerHTML = "";
  const head = document.createElement("div");
  head.className = "jrow";
  head.innerHTML = '<span class="jname mini">SHRUG&deg;</span><span class="mini">left rise mm</span><span class="mini">right rise mm</span><span></span>';
  box.appendChild(head);
  c.forEach((pt, i) => {
    const row = document.createElement("div");
    row.className = "jrow";
    const mk = (key, w) => {
      const el = document.createElement("input");
      el.type = "number";
      el.step = key === "j" ? 1 : 0.5;
      el.value = pt[key];
      el.style.width = w;
      el.onchange = () => {
        pt[key] = +el.value || 0;
        rigChanged();
        renderShrugCurve();
      };
      return el;
    };
    const nm = document.createElement("span");
    nm.className = "jname";
    nm.appendChild(mk("j", "62px"));
    row.appendChild(nm);
    row.appendChild(mk("l", "70px"));
    row.appendChild(mk("r", "70px"));
    const del = document.createElement("button");
    del.textContent = "✕";
    del.title = "remove this measurement";
    del.onclick = () => {
      c.splice(i, 1);
      rigChanged();
      renderShrugCurve();
    };
    row.appendChild(del);
    box.appendChild(row);
  });
  const add = document.createElement("button");
  add.textContent = "+ add a measurement";
  add.onclick = () => {
    const last = c.length ? c[c.length - 1].j : 87;
    c.push({ j: Math.round(last) + 3, l: 0, r: 0 });
    rigChanged();
    renderShrugCurve();
  };
  box.appendChild(add);
  const note = document.createElement("div");
  note.className = "mini";
  note.textContent = c.length >= 2 ? c.length + " measurements — the preview now moves each shoulder by its own amount" : "fewer than 2 measurements: the preview still uses the old symmetric rock";
  box.appendChild(note);
}
function shrugRise(j) {
  const c = (RIG.shrugCurve || []).filter((p) => p && isFinite(p.j));
  if (c.length < 2) return null;
  const pts = c.slice().sort((a, b) => a.j - b.j);
  if (j <= pts[0].j) return { l: +pts[0].l || 0, r: +pts[0].r || 0 };
  const last = pts[pts.length - 1];
  if (j >= last.j) return { l: +last.l || 0, r: +last.r || 0 };
  for (let i = 1; i < pts.length; i++) {
    if (j > pts[i].j) continue;
    const a = pts[i - 1], b = pts[i];
    const span = b.j - a.j;
    const f = span > 1e-9 ? (j - a.j) / span : 0;
    return {
      l: (+a.l || 0) + ((+b.l || 0) - (+a.l || 0)) * f,
      r: (+a.r || 0) + ((+b.r || 0) - (+a.r || 0)) * f
    };
  }
  return { l: +last.l || 0, r: +last.r || 0 };
}
let URDF_CFG = null;
const urdfFiles = {};
let urdfJ = [];
let urdfTip = {};
let urdfArm = [];
let urdfLast = { dims: null, warn: [], error: "", fit: [null, null] };
let urdfModelList = [];
const urdfGeo = {};
let urdfBuildGen = 0;
const urdfMissing = /* @__PURE__ */ new Set();
function urdfConfigReady(j) {
  URDF_CFG = j;
  viewFloor();
  renderLookUI();
  urdfRefreshModels();
  if (lookKind() === "urdf") buildRobot();
}
fetch("urdf_view.json").then((r) => r.json()).then(urdfConfigReady).catch(() => {
});
function lookOf(id) {
  const looks = URDF_CFG && URDF_CFG.looks || [];
  return looks.find((l) => l.id === id) || null;
}
function lookKind() {
  const v = RIG.view || {};
  const l = lookOf(v.look);
  return l ? l.kind : v.look === "urdf" ? "urdf" : "rig";
}
function urdfRootQuat() {
  const up = (URDF_CFG && URDF_CFG.frame || {}).up || "z";
  const q = new THREE.Quaternion();
  if (up === "z")
    q.setFromRotationMatrix(new THREE.Matrix4().set(0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1));
  return q;
}
function urdfUnit() {
  return +(URDF_CFG && URDF_CFG.frame || {}).unitMm || 1e3;
}
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
function urdfRead(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror")) throw new Error("the file is not readable XML");
  const top = doc.querySelector("robot");
  if (!top) throw new Error("the file has no <robot>");
  const links = {}, joints = [];
  top.querySelectorAll(":scope > link").forEach((l) => {
    const visuals = [];
    l.querySelectorAll(":scope > visual").forEach((v) => {
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
  top.querySelectorAll(":scope > joint").forEach((j) => {
    const lim = j.querySelector("limit");
    joints.push({
      name: j.getAttribute("name"),
      type: j.getAttribute("type") || "fixed",
      parent: (j.querySelector("parent") || { getAttribute: () => "" }).getAttribute("link"),
      child: (j.querySelector("child") || { getAttribute: () => "" }).getAttribute("link"),
      ...urdfOrigin(j),
      axis: urdfNumList(j.querySelector("axis"), "xyz", [1, 0, 0]),
      lower: lim ? +lim.getAttribute("lower") : NaN,
      upper: lim ? +lim.getAttribute("upper") : NaN
    });
  });
  const kids = /* @__PURE__ */ new Set();
  for (const j of joints) {
    if (!links[j.parent] || !links[j.child]) throw new Error("joint " + j.name + " names a part the file does not have");
    if (kids.has(j.child)) throw new Error("part " + j.child + " hangs from two joints");
    kids.add(j.child);
  }
  const roots = Object.keys(links).filter((n) => !kids.has(n));
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
function urdfMeshUrls(fn, urdfPath) {
  const dir = urdfPath.split("/").slice(0, -1);
  const out = [];
  const m = /^package:\/\/([^/]+)\/(.*)$/.exec(fn);
  if (m) {
    const k = dir.lastIndexOf(m[1]);
    out.push((k >= 0 ? dir.slice(0, k + 1) : [m[1]]).concat(m[2].split("/")));
  } else if (!/^[a-z]+:\/\//i.test(fn) && !/^[\\/]|^[a-z]:/i.test(fn)) {
    const p = dir.slice();
    fn.split("/").forEach((s) => {
      if (s === "..") p.pop();
      else if (s && s !== ".") p.push(s);
    });
    out.push(p);
  }
  out.push([fn.split(/[\\/]/).pop()]);
  return out.map((p) => "/models/" + p.map(encodeURIComponent).join("/"));
}
const urdfLoading = {};
function urdfMesh(urls, cb, fail) {
  const u = urls[0];
  if (!u) {
    fail();
    return;
  }
  if (urdfGeo[u]) {
    cb(urdfGeo[u]);
    return;
  }
  const next = () => urdfMesh(urls.slice(1), cb, fail);
  if (urdfLoading[u]) {
    urdfLoading[u].push([cb, next]);
    return;
  }
  urdfLoading[u] = [[cb, next]];
  const done = (geo) => {
    const w = urdfLoading[u] || [];
    delete urdfLoading[u];
    if (geo) urdfGeo[u] = geo;
    w.forEach(([ok, no]) => geo ? ok(geo) : no());
  };
  stlLoader.load(u, done, void 0, () => done(null));
}
const _uQ = new THREE.Quaternion(), _uE = new THREE.Euler();
function urdfRpyQuat(rpy, out) {
  return (out || new THREE.Quaternion()).setFromEuler(_uE.set(rpy[0], rpy[1], rpy[2], "ZYX"));
}
function rigRestAxis(i) {
  if (i === 8) return new THREE.Vector3(0, 1, 0);
  if (i === 9) return new THREE.Vector3(0, 0, 1);
  const c = rigChain(i - i % 4, [0, 0, 0, 0]);
  return _AXVEC[RIG.axis[i]].clone().applyQuaternion(c.pre[i % 4]).normalize();
}
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
function urdfHandMarksOn() {
  const v = RIG.view || {};
  return typeof v.handMarks === "boolean" ? v.handMarks : (URDF_CFG || {}).handMarks !== false;
}
function urdfSetHandMarks(on) {
  RIG.view.handMarks = !!on;
  saveRig();
  if (urdfOn) palmMarks.forEach((h) => h.children.forEach((c) => {
    if (c.isMesh) c.visible = !!on;
  }));
  if (typeof markDirty3d === "function") markDirty3d(5);
  renderLookUI();
}
let urdfRootLink = "";
function viewFloorCfg() {
  return URDF_CFG && URDF_CFG.floor || {};
}
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
    robot.traverse((o) => {
      if (o.isMesh && o.userData.urdfLink === urdfRootLink) box.expandByObject(o);
    });
    if (!box.isEmpty()) y = box.min.y - (+cfg.gapMm || 0);
  }
  grid.position.y = y;
  if (typeof markDirty3d === "function") markDirty3d(5);
}
function viewSetGrid(on) {
  RIG.view.grid = !!on;
  saveRig();
  viewFloor();
}
function urdfJointCfg(i) {
  return (URDF_CFG && URDF_CFG.joints || {})[JOINT_NAMES[i]] || {};
}
function urdfBuildInto(root) {
  urdfOn = false;
  urdfRootLink = "";
  viewFloor();
  if (lookKind() !== "urdf" || !URDF_CFG) return false;
  const path = (RIG.view || {}).model;
  if (!path) return false;
  const f = urdfFiles[path];
  if (!f) {
    urdfLoad(path).then(() => {
      if ((RIG.view || {}).model === path) buildRobot();
    });
    return false;
  }
  if (f.error) {
    urdfLast.error = f.error;
    renderLookUI();
    return false;
  }
  const U = urdfUnit(), warn = [];
  const base = new THREE.Group();
  base.name = "urdf_root";
  base.quaternion.copy(urdfRootQuat());
  root.add(base);
  const linkG = {}, jointOf = {};
  linkG[f.root] = new THREE.Group();
  base.add(linkG[f.root]);
  urdfRootLink = f.root;
  const byParent = {};
  f.joints.forEach((j) => (byParent[j.parent] = byParent[j.parent] || []).push(j));
  const walk = (name) => (byParent[name] || []).forEach((j) => {
    const org = new THREE.Group();
    org.name = "joint_" + j.name;
    org.position.set(j.xyz[0] * U, j.xyz[1] * U, j.xyz[2] * U);
    urdfRpyQuat(j.rpy, org.quaternion);
    const mov = new THREE.Group();
    org.add(mov);
    linkG[j.parent].add(org);
    linkG[j.child] = mov;
    jointOf[j.child] = { j, org, mov };
    walk(j.child);
  });
  walk(f.root);
  const byName = {};
  f.joints.forEach((j) => {
    byName[j.name] = j;
  });
  const movOf = {};
  Object.values(jointOf).forEach((o) => {
    movOf[o.j.name] = o;
  });
  urdfJ = [];
  for (let i = 0; i < NJ; i++) {
    const c = urdfJointCfg(i);
    const hit = (c.urdf || [JOINT_NAMES[i]]).map((n) => movOf[n]).find(Boolean);
    if (!hit || !/^(revolute|continuous)$/.test(hit.j.type)) {
      urdfJ[i] = null;
      if (i < ARMJ) {
        urdfLast.error = "the file has no turning joint for " + JOINT_LABELS[i];
        root.remove(base);
        renderLookUI();
        return false;
      }
      warn.push(JOINT_LABELS[i] + " is not in the file and does not move here");
      continue;
    }
    jointGroups[i] = hit.mov;
    let depth = 0;
    for (let n = hit.j.child; jointOf[n]; n = jointOf[n].j.parent) depth++;
    urdfJ[i] = {
      name: hit.j.name,
      axis: new THREE.Vector3(...hit.j.axis).normalize(),
      mov: hit.mov,
      org: hit.org,
      depth,
      named: i,
      sign: 1,
      off: 0,
      quality: 1,
      cfgSign: c.sign,
      cfgOff: c.offsetDeg
    };
  }
  urdfArm = [0, 4].map((b) => urdfJ.slice(b, b + 4).slice().sort((x, y) => x.depth - y.depth));
  for (const side of ["L", "R"]) {
    const h = (URDF_CFG.hands || {})[side] || {};
    if (!linkG[h.link]) {
      urdfLast.error = "the file has no part " + (h.link || "?") + " for the " + (side === "L" ? "left" : "right") + " hand";
      root.remove(base);
      renderLookUI();
      return false;
    }
  }
  const pairOfLink = (name) => {
    for (let n = name; jointOf[n]; n = jointOf[n].j.parent) {
      const i = urdfJ.findIndex((b) => b && b.name === jointOf[n].j.name);
      if (i >= 0 && i < ARMJ) return Math.floor(i / 2);
    }
    return -1;
  };
  const PAIR_PART = ["L_upper", "L_fore", "R_upper", "R_fore"];
  const matOf = (pair) => partMat(pair >= 0 ? PAIR_PART[pair] : "torso");
  const gen = ++urdfBuildGen;
  const linkZero = {};
  root.updateMatrixWorld(true);
  Object.keys(linkG).forEach((n) => {
    linkZero[n] = linkG[n].matrixWorld.clone();
  });
  const meshPut = [], piecesOn = urdfPiecesOn();
  let meshWant = 0, meshLate = 0, meshGone = 0;
  const meshDone = () => {
    if (piecesOn && (meshLate || meshGone) && meshPut.length + meshGone === meshWant && gen === urdfBuildGen) buildRobot();
  };
  Object.entries(f.links).forEach(([name, l]) => {
    const pair = pairOfLink(name);
    l.visuals.forEach((v) => {
      const holder = new THREE.Group();
      holder.position.set(v.xyz[0] * U, v.xyz[1] * U, v.xyz[2] * U);
      urdfRpyQuat(v.rpy, holder.quaternion);
      linkG[name].add(holder);
      holder.updateMatrixWorld(true);
      holder.userData.zero = holder.matrixWorld.clone();
      const mat = matOf(pair);
      const put = (geo, sc) => {
        const m = new THREE.Mesh(geo, mat);
        m.scale.set(sc[0], sc[1], sc[2]);
        m.userData.pair = pair;
        m.userData.urdfLink = name;
        if (pair >= 0) pickMeshes.push(m);
        holder.add(m);
        return m;
      };
      if (v.box) put(new THREE.BoxGeometry(...v.box), [U, U, U]);
      else if (v.cyl) put(new THREE.CylinderGeometry(v.cyl[0], v.cyl[0], v.cyl[1], 20), [U, U, U]).rotation.x = Math.PI / 2;
      else if (v.sphere) put(new THREE.SphereGeometry(v.sphere, 20, 14), [U, U, U]);
      else if (urdfMissing.has(f.path + "|" + v.mesh)) warn.push("the shape " + v.mesh.split(/[\\/]/).pop() + " is missing");
      else {
        meshWant++;
        let sync = true;
        urdfMesh(urdfMeshUrls(v.mesh, f.path), (geo) => {
          if (gen !== urdfBuildGen || holder.parent !== linkG[name]) return;
          meshPut.push({ name, holder, mesh: put(geo, v.scale.map((s) => s * U)) });
          if (!sync) meshLate++;
          if (typeof markDirty3d === "function") markDirty3d(5);
          if (name === urdfRootLink) viewFloor();
          if (!sync) {
            urdfMeshArrived(name);
            meshDone();
          }
        }, () => {
          urdfMissing.add(f.path + "|" + v.mesh);
          meshGone++;
          if (gen === urdfBuildGen) {
            urdfLast.warn.push("the shape " + v.mesh.split(/[\\/]/).pop() + " is missing");
            renderLookUI();
            meshDone();
          }
        });
        sync = false;
      }
    });
  });
  if (piecesOn && meshPut.length === meshWant) urdfPieces(meshPut, linkG, linkZero, matOf, pairOfLink);
  for (let i = 0; i < ARMJ; i++) {
    const ball = new THREE.Mesh(new THREE.SphereGeometry((RIG.jointR[Math.floor(i / 2)] || 16) * 0.5, 16, 10), matJoint);
    ball.userData.skel = true;
    ball.userData.pair = Math.floor(i / 2);
    jointGroups[i].parent.add(ball);
    pickMeshes.push(ball);
  }
  bodyGroup = new THREE.Group();
  bodyGroup.name = "urdf_body";
  (urdfJ[8] ? jointGroups[8] : linkG[f.root]).add(bodyGroup);
  shoulderMount = urdfJ[9] ? jointGroups[9] : new THREE.Group();
  shrugAnchors.L = shrugAnchors.R = null;
  ["L", "R"].forEach((side, arm) => {
    const b = arm * 4;
    const elbowBall = new THREE.Mesh(
      new THREE.SphereGeometry(12, 18, 12),
      new THREE.MeshBasicMaterial({ color: 16750916, depthTest: false })
    );
    elbowBall.userData.arm = arm;
    elbowBall.renderOrder = 19;
    urdfArm[arm][2].org.add(elbowBall);
    elbowBalls.push(elbowBall);
    const fore = linkG[URDF_CFG.hands[side].link];
    const wrist = new THREE.Mesh(
      new THREE.SphereGeometry(14, 20, 14),
      new THREE.MeshBasicMaterial({ color: 4116366, depthTest: false })
    );
    wrist.userData.arm = arm;
    wrist.renderOrder = 20;
    fore.add(wrist);
    wristBalls.push(wrist);
    const hand = new THREE.Group();
    const back = new THREE.Mesh(new THREE.BoxGeometry(34, 46, 5), new THREE.MeshStandardMaterial({ color: 8226192 }));
    back.position.y = -30;
    const palm = new THREE.Mesh(new THREE.PlaneGeometry(30, 42), new THREE.MeshStandardMaterial({ color: 15906976 }));
    palm.position.set(0, -30, 2.6);
    back.userData.skel = palm.userData.skel = true;
    hand.add(back, palm);
    fore.add(hand);
    palmMarks.push(hand);
    back.visible = palm.visible = urdfHandMarksOn();
    urdfTip[side] = { link: URDF_CFG.hands[side].link, fore, wrist, hand, mm: 0, fromMesh: false, tipLocal: null };
  });
  urdfOn = true;
  urdfSettle(base, warn);
  viewFloor();
  pairRingParents = [0, 2, 4, 6].map((i) => [jointGroups[i].parent, jointGroups[i + 1].parent]);
  return true;
}
function urdfSettle(base, warn) {
  const keep = pose;
  pose = RIG.zero.slice();
  base.position.set(0, 0, 0);
  const num = (v) => typeof v === "number" && Number.isFinite(v);
  urdfJ.forEach((b) => {
    if (b) {
      b.sign = 1;
      b.off = num(b.cfgOff) ? THREE.MathUtils.degToRad(b.cfgOff) : 0;
    }
  });
  applyPose();
  robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const wq = (o) => o.getWorldQuaternion(new THREE.Quaternion());
  const fitOn = (URDF_CFG.fit || {}).on !== false;
  urdfJ.forEach((b, i) => {
    if (!b) return;
    const a = b.axis.clone().applyQuaternion(wq(b.org));
    const dot = a.dot(rigRestAxis(i));
    b.quality = Math.abs(dot);
    b.sign = b.cfgSign === 1 || b.cfgSign === -1 ? b.cfgSign : dot < 0 ? -1 : 1;
    if (b.cfgSign === "auto" && b.quality < 0.7 && (i >= ARMJ || !fitOn))
      warn.push(JOINT_LABELS[i] + " turns about a different axis than the simple shapes");
  });
  const mid = W(urdfArm[0][0].org).add(W(urdfArm[1][0].org)).multiplyScalar(0.5);
  const mm = new THREE.Vector3().fromArray(RIG.mount.L).add(new THREE.Vector3().fromArray(RIG.mount.R)).multiplyScalar(0.5);
  base.position.set(mm.x - mid.x, (RIG.dims.shoulderY || 0) + mm.y - mid.y, mm.z - mid.z);
  applyPose();
  robot.updateMatrixWorld(true);
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
function urdfFarEnd(pts) {
  let far = 0;
  for (const v of pts) far = Math.max(far, v.length());
  if (far < 1) return null;
  const end = new THREE.Vector3(), seen = /* @__PURE__ */ new Set();
  let n = 0;
  pts.forEach((v) => {
    const key = v.toArray().map((x) => Math.round(x * 100)).join();
    if (v.length() > far * 0.97 && !seen.has(key)) {
      seen.add(key);
      end.add(v);
      n++;
    }
  });
  const dir = end.divideScalar(n).normalize();
  let mm = -Infinity;
  for (const v of pts) mm = Math.max(mm, v.dot(dir));
  return { dir, mm };
}
function urdfMeshTip(side, arm) {
  const t = urdfTip[side];
  t.fromMesh = false;
  t.tipLocal = null;
  if (((URDF_CFG.hands || {})[side] || {}).tip !== "mesh") return;
  robot.updateMatrixWorld(true);
  const el = t.fore.worldToLocal(urdfArm[arm][2].org.getWorldPosition(new THREE.Vector3()));
  const toFore = new THREE.Matrix4().copy(t.fore.matrixWorld).invert();
  const pts = [], m4 = new THREE.Matrix4();
  t.fore.traverse((o) => {
    if (!o.isMesh || o.userData.urdfLink !== t.link) return;
    const pos = o.geometry.attributes.position;
    m4.multiplyMatrices(toFore, o.matrixWorld);
    const step = Math.max(1, Math.floor(pos.count / 6e4));
    for (let k = 0; k < pos.count; k += step) pts.push(new THREE.Vector3().fromBufferAttribute(pos, k).applyMatrix4(m4).sub(el));
  });
  if (!pts.length) return;
  const end = urdfFarEnd(pts);
  if (!end) return;
  const dir = end.dir;
  t.mm = end.mm;
  t.tipLocal = el.clone().addScaledVector(dir, t.mm);
  t.fromMesh = true;
  t.wrist.position.copy(t.tipLocal);
  t.palmN = urdfMeshPalm(side, pts, dir, t.mm);
}
function urdfMeshPalm(side, pts, dir, mm) {
  const cfg = URDF_CFG.palm || {};
  if (((URDF_CFG.hands || {})[side] || {}).palm !== "mesh") return null;
  const u = new THREE.Vector3(1, 0, 0);
  if (Math.abs(u.dot(dir)) > 0.9) u.set(0, 1, 0);
  u.addScaledVector(dir, -u.dot(dir)).normalize();
  const w = dir.clone().cross(u);
  let n = 0, su = 0, sw = 0, suu = 0, sww = 0, suw = 0;
  const seen = /* @__PURE__ */ new Set();
  pts.forEach((v) => {
    if (v.dot(dir) < mm * (cfg.from || 0.6)) return;
    const key = v.toArray().map((x) => Math.round(x * 100)).join();
    if (seen.has(key)) return;
    seen.add(key);
    const a = v.dot(u), b = v.dot(w);
    n++;
    su += a;
    sw += b;
    suu += a * a;
    sww += b * b;
    suw += a * b;
  });
  if (n < 4) return null;
  const cuu = suu / n - (su / n) ** 2, cww = sww / n - (sw / n) ** 2, cuw = suw / n - su / n * (sw / n);
  const tr = cuu + cww, det = cuu * cww - cuw * cuw, gap = Math.sqrt(Math.max(0, tr * tr / 4 - det));
  const lo = tr / 2 - gap, hi = tr / 2 + gap;
  if (!(hi > 0) || lo / hi > (cfg.flat || 0.35)) return null;
  const th = 0.5 * Math.atan2(2 * cuw, cuu - cww);
  const wide = u.clone().multiplyScalar(Math.cos(th)).addScaledVector(w, Math.sin(th));
  return dir.clone().cross(wide).normalize();
}
function urdfPlaceHand(side, arm) {
  const t = urdfTip[side], b = arm * 4;
  const keep = pose;
  pose = RIG.zero.slice();
  applyPose();
  robot.updateMatrixWorld(true);
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
    const z = new THREE.Vector3(0, 0, 1).applyQuaternion(t.hand.quaternion);
    const n = t.palmN.clone().multiplyScalar(t.palmN.dot(z) < 0 ? -1 : 1);
    const zf = z.addScaledVector(dir, -z.dot(dir)).normalize();
    const phi = Math.atan2(zf.clone().cross(n).dot(dir), zf.dot(n));
    if (Number.isFinite(phi)) t.hand.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(dir, phi));
  }
  palmCache.clear();
  pose = keep;
  applyPose();
}
const _fQ = new THREE.Quaternion(), _fV = new THREE.Vector3();
function urdfArmModel(arm) {
  const ch = urdfArm[arm];
  pose = RIG.zero.slice();
  applyPose();
  ch.forEach((c) => c.mov.quaternion.identity());
  robot.updateMatrixWorld(true);
  const Wq = ch.map((c) => c.org.getWorldQuaternion(new THREE.Quaternion()));
  const P = ch.map((c) => c.org.getWorldPosition(new THREE.Vector3()));
  const C = [null], T = [null];
  for (let k = 1; k < 4; k++) {
    const inv = Wq[k - 1].clone().invert();
    C[k] = inv.clone().multiply(Wq[k]);
    T[k] = P[k].clone().sub(P[k - 1]).applyQuaternion(inv);
  }
  const tipW = wristBalls[arm].getWorldPosition(new THREE.Vector3());
  const tipT = tipW.sub(P[3]).applyQuaternion(Wq[3].clone().invert());
  applyPose();
  return { W1: Wq[0], C, T, tipT, axes: ch.map((c) => c.axis) };
}
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
function rigArmDirs(b, d) {
  const c = rigChain(b, d), qu = c.at[1], qf = c.at[3];
  return { up: new THREE.Vector3(0, -1, 0).applyQuaternion(qu), qu, fore: new THREE.Vector3(0, -1, 0).applyQuaternion(qf), qf };
}
function urdfFitArm(arm, warn) {
  const cfg = URDF_CFG.fit || {}, b = arm * 4, ch = urdfArm[arm];
  const m = urdfArmModel(arm);
  const withFore = urdfTip[arm ? "R" : "L"].fromMesh;
  let seed = 4801 + arm;
  const rnd = () => (seed = seed * 16807 % 2147483647) / 2147483647;
  const S = [];
  for (let n = 0; n < (cfg.samples || 12); n++) {
    const d = [0, 1, 2, 3].map((k) => {
      const j = b + k, v = RIG.min[j] + (RIG.max[j] - RIG.min[j]) * rnd();
      return (v - RIG.zero[j]) * jdir(j);
    });
    S.push({ d, ...rigArmDirs(b, d) });
  }
  const dH = [0, 1, 2, 3].map((k) => (RIG.home[b + k] - RIG.zero[b + k]) * jdir(b + k));
  const H = { d: dH, ...rigArmDirs(b, dH) };
  S.forEach((x) => {
    x.tu = x.qu.clone().multiply(H.qu.clone().invert());
    x.tf = x.qf.clone().multiply(H.qf.clone().invert());
  });
  const fw = cfg.frames === false ? 0 : cfg.frames === true || cfg.frames == null ? 1 : +cfg.frames || 0;
  const frames = fw > 0;
  const qAng = (a, c) => 2 * Math.acos(Math.min(1, Math.abs(a.dot(c))));
  const D2R = Math.PI / 180, num = (v) => typeof v === "number" && Number.isFinite(v);
  const slot = (swapSh, swapEl) => [swapSh ? b + 1 : b, swapSh ? b : b + 1, swapEl ? b + 3 : b + 2, swapEl ? b + 2 : b + 3];
  const cost = (map, sg, of, fore, dirsOnly) => {
    let c = 0;
    const th = [0, 0, 0, 0];
    const at = (x) => {
      for (let k = 0; k < 4; k++) th[k] = sg[k] * x.d[map[k] - b] * D2R + of[k];
      return urdfArmDirs(m, th, fore);
    };
    const h = frames && !dirsOnly ? at(H) : null;
    const hu = h && h.qu.clone().invert(), hf = h && fore && h.qf.clone().invert();
    for (const s of S) {
      const r = at(s);
      c += r.up.angleTo(s.up) + (fore ? r.fore.angleTo(s.fore) : 0);
      if (h) c += fw * (qAng(r.qu.multiply(hu), s.tu) + (fore ? qAng(r.qf.multiply(hf), s.tf) : 0));
    }
    c /= h ? 1 + fw : 1;
    const tie = of.reduce((a, o) => a + Math.abs(Math.atan2(Math.sin(o), Math.cos(o))), 0) * 1e-4;
    return c / S.length / (fore ? 2 : 1) / D2R + tie;
  };
  const fixedSign = (j) => {
    const v = urdfJointCfg(j).sign;
    return v === 1 || v === -1 ? [v] : [1, -1];
  };
  const fixedOff = (j) => {
    const v = urdfJointCfg(j).offsetDeg;
    return num(v) ? v * D2R : null;
  };
  const anchored = cfg.anchor === "home";
  const homeOff = (j, s) => -s * dH[j - b] * D2R;
  const swaps = cfg.swap === false ? [false] : [false, true];
  const grid2 = cfg.gridDeg || 15;
  const best = { map: slot(false, false), sg: [1, 1, 1, 1], of: [0, 0, 0, 0], c: Infinity };
  const searchPair = (k0, fore) => {
    let top = { c: Infinity };
    for (const sw of swaps) {
      const map = k0 === 0 ? slot(sw, best.map[2] === b + 3) : slot(best.map[0] === b + 1, sw);
      for (const s0 of fixedSign(map[k0])) for (const s1 of fixedSign(map[k0 + 1])) {
        const sg = best.sg.slice();
        sg[k0] = s0;
        sg[k0 + 1] = s1;
        let f0 = fixedOff(map[k0]), f1 = fixedOff(map[k0 + 1]);
        const free0 = f0 === null && !anchored, free1 = f1 === null && !anchored;
        if (anchored) {
          if (f0 === null) f0 = homeOff(map[k0], s0);
          if (f1 === null) f1 = homeOff(map[k0 + 1], s1);
        }
        const g = (f) => f !== null ? [f] : Array.from({ length: Math.round(360 / grid2) }, (_, i) => (i * grid2 - 180) * D2R);
        for (const o0 of g(f0)) for (const o1 of g(f1)) {
          const of = best.of.slice();
          of[k0] = o0;
          of[k0 + 1] = o1;
          const c = cost(map, sg, of, fore);
          if (c < top.c) top = { map, sg, of, c, free: [free0, free1] };
        }
      }
    }
    for (const st of [5, 1, 0.25, 0.05, 0.01]) for (let it = 0; it < 8; it++) {
      let moved = false;
      for (let k = 0; k < 2; k++) {
        if (!top.free[k]) continue;
        for (const dd of [-st, st]) {
          const of = top.of.slice();
          of[k0 + k] += dd * D2R;
          const c = cost(top.map, top.sg, of, fore);
          if (c < top.c - 1e-9) {
            top = { ...top, of, c };
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
    Object.assign(best, { map: top.map, sg: top.sg, of: top.of, c: top.c });
  };
  searchPair(0, false);
  if (withFore) {
    searchPair(2, true);
    let c0 = cost(best.map, best.sg, best.of, true);
    const free = [0, 1, 2, 3].map((k) => fixedOff(best.map[k]) === null && !anchored);
    for (const st of [2, 0.5, 0.1, 0.02]) for (let it = 0; it < 10; it++) {
      let moved = false;
      for (let k = 0; k < 4; k++) {
        if (!free[k]) continue;
        for (const dd of [-st, st]) {
          const of = best.of.slice();
          of[k] += dd * D2R;
          const c = cost(best.map, best.sg, of, true);
          if (c < c0 - 1e-9) {
            best.of = of;
            c0 = c;
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
  }
  const upDeg = cost(best.map, best.sg, best.of, false, true);
  const allDeg = withFore ? cost(best.map, best.sg, best.of, true, true) : upDeg;
  const fitted = withFore ? 4 : 2;
  const entries = ch.slice();
  for (let k = 0; k < fitted; k++) {
    const j = best.map[k], e = entries[k];
    urdfJ[j] = Object.assign(e, { sign: best.sg[k], off: best.of[k], fitted: true });
    jointGroups[j] = e.mov;
  }
  for (let k = fitted; k < 4; k++) {
    const e = entries[k], j = e.named;
    const choices = fixedSign(j), sign = choices.length === 1 ? choices[0] : e.sign, off = fixedOff(j);
    urdfJ[j] = Object.assign(e, { sign, off: off !== null ? off : anchored ? homeOff(j, sign) : 0, fitted: false });
    jointGroups[j] = e.mov;
  }
  urdfLast.fit[arm] = {
    deg: Math.round(allDeg * 10) / 10,
    upDeg: Math.round(upDeg * 10) / 10,
    // swapped = against the file's own names
    swapSh: urdfJ[b].named !== b,
    swapEl: withFore && urdfJ[b + 2].named !== b + 2,
    fore: withFore
  };
  const side = arm ? "right" : "left";
  if (allDeg > (cfg.warnDeg || 5))
    warn.push("the " + side + " arm of the CAD model points up to " + Math.round(allDeg) + "° away from the simple shapes");
  pose = RIG.zero.slice();
  applyPose();
  robot.updateMatrixWorld(true);
}
function urdfMeshArrived(link) {
  if (!urdfOn) return;
  if (!["L", "R"].some((side) => urdfTip[side] && urdfTip[side].link === link)) return;
  buildRobot();
  if (lookKind() === "urdf") {
    urdfUseSizes();
    renderRigUI();
  }
}
function urdfSizes() {
  if (!urdfOn) return urdfLast.dims;
  const keep = pose;
  pose = RIG.zero.slice();
  applyPose();
  robot.updateMatrixWorld(true);
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
  pose = keep;
  applyPose();
  return out;
}
function urdfUseSizes() {
  const d = urdfLast.dims || {};
  let changed = false;
  Object.entries(d).forEach(([k, v]) => {
    if (RIG.dims[k] !== v) {
      RIG.dims[k] = v;
      changed = true;
    }
  });
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
function urdfAxisVec(i) {
  const b = urdfJ[i];
  return b ? b.axis.clone().multiplyScalar(b.sign) : _AXVEC[RIG.axis[i]].clone();
}
function urdfDimsOf(keys2, src) {
  const o = {};
  keys2.forEach((k) => {
    if (Number.isFinite(src[k])) o[k] = src[k];
  });
  return o;
}
function sameDims(a, b) {
  return Object.keys(a || {}).every((k) => Math.abs((a[k] || 0) - ((b || {})[k] || 0)) < 0.05);
}
async function urdfRefreshModels() {
  const known = (URDF_CFG && URDF_CFG.models || []).slice();
  let found = null;
  try {
    const r = await fetch("/api/list?kind=models&deep=1").then((r2) => r2.json());
    found = (r.files || []).filter((f) => /\.urdf$/i.test(f));
  } catch (e) {
  }
  urdfModelList = (found ? known.filter((m) => found.includes(m.path)) : known).concat((found || []).filter((p) => !known.some((m) => m.path === p)).map((p) => ({ path: p, label: p.split("/").pop() })));
  renderLookUI();
}
function renderLookUI() {
  const sel = $("lookSel"), msel = $("lookModel"), stat = $("lookStat");
  if (!sel || !URDF_CFG) return;
  const v = RIG.view || {};
  sel.innerHTML = "";
  URDF_CFG.looks.forEach((l) => {
    const o = document.createElement("option");
    o.value = l.id;
    o.textContent = l.label;
    sel.appendChild(o);
  });
  sel.value = lookOf(v.look) ? v.look : URDF_CFG.default;
  msel.innerHTML = "";
  urdfModelList.forEach((m) => {
    const o = document.createElement("option");
    o.value = m.path;
    o.textContent = m.label;
    msel.appendChild(o);
  });
  if (v.model) msel.value = v.model;
  msel.hidden = lookKind() !== "urdf" || urdfModelList.length < 2;
  const tech = $("lookTech");
  if (typeof renderRigCadUI === "function") renderRigCadUI();
  if ($("viewGrid")) $("viewGrid").checked = viewGridOn();
  if ($("lookHandMarks")) {
    $("lookHandMarks").checked = urdfHandMarksOn();
    $("lookHandMarksRow").hidden = !urdfOn;
  }
  if (lookKind() !== "urdf") {
    stat.textContent = "";
    tech.textContent = "";
    return;
  }
  stat.textContent = urdfLast.error ? "Cannot show the CAD model: " + urdfLast.error + ". The simple shapes are shown." : !urdfOn ? "Opening the CAD model…" : urdfLast.warn.length ? urdfLast.warn.join("; ") : "CAD model at its real sizes.";
  const fitTxt = (urdfLast.fit || []).map((f, a) => f ? (a ? " R" : " L") + " arm fit " + f.deg + "°" + (f.swapSh ? " shoulder pair swapped" : "") + (f.swapEl ? " elbow pair swapped" : "") + (f.fore ? "" : " (upper arm only)") : "").join(",");
  tech.textContent = urdfOn ? v.model + " ·" + fitTxt + " · " + urdfJ.map((b, i) => b ? JOINT_NAMES[i] + "→" + b.name + (b.sign < 0 ? " (-)" : "") + (b.off ? " " + Math.round(THREE.MathUtils.radToDeg(b.off)) + "°" : "") + (b.quality < 0.7 && !b.fitted ? " (axis " + b.quality.toFixed(2) + ")" : "") : JOINT_NAMES[i] + "→none").join(", ") : v.model || "";
}
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
    const keys3 = Object.keys(URDF_CFG.sizes || {});
    const mine = urdfDimsOf(keys3, RIG.dims);
    if (!wasUrdf && (v.sizes === "custom" || !sameDims(mine, v.urdfDims))) v.custom = mine;
    v.look = id;
    rigChanged();
    if (urdfOn) {
      urdfUseSizes();
      renderRigUI();
    }
    return;
  }
  if (!wasUrdf) {
    v.look = id;
    rigChanged();
    renderLookUI();
    return;
  }
  const pick = await askLookSizes();
  if (!pick) {
    renderLookUI();
    return;
  }
  if (pick === "cad") {
    if (!rigFromCad()) {
      renderLookUI();
      return;
    }
    v.look = id;
    rigChanged();
    renderLookUI();
    return;
  }
  const keys2 = Object.keys(URDF_CFG.sizes || {});
  if (pick === "urdf") Object.assign(RIG.dims, urdfDimsOf(keys2, urdfLast.dims || {}));
  else Object.assign(RIG.dims, urdfDimsOf(keys2, v.custom || {}));
  v.sizes = pick;
  v.look = id;
  rigChanged();
  renderLookUI();
}
function lookSizeText(d) {
  if (!d || !Object.keys(d).length) return "";
  const n = (k) => Number.isFinite(d[k]) ? Math.round(d[k]) : "?";
  return `upper arm ${n("upperLenL")}/${n("upperLenR")} mm, forearm ${n("foreLenL")}/${n("foreLenR")} mm, shoulders ${n("shoulderX")} mm from the middle`;
}
function askLookSizes() {
  const dlg = $("lookAsk");
  const v = RIG.view;
  $("lookAskUrdf").textContent = lookSizeText(urdfLast.dims);
  $("lookAskMine").textContent = v.custom ? lookSizeText(v.custom) : "none kept yet: the URDF sizes, then change them in Rig setup";
  return new Promise((res) => {
    const done = (x) => {
      dlg.close ? dlg.close() : dlg.removeAttribute("open");
      res(x);
    };
    $("lookUseCad").onclick = () => done("cad");
    $("lookUseUrdf").onclick = () => done("urdf");
    $("lookUseMine").onclick = () => done("custom");
    $("lookStay").onclick = () => done(null);
    dlg.oncancel = (e) => {
      e.preventDefault();
      done(null);
    };
    if (dlg.showModal) dlg.showModal();
    else dlg.setAttribute("open", "");
  });
}
const urdfSplitDone = /* @__PURE__ */ new WeakMap();
let urdfPieceInfo = null;
function urdfPiecesCfg() {
  return URDF_CFG && URDF_CFG.pieces || null;
}
function urdfPiecesOn() {
  const c = urdfPiecesCfg();
  return !!c && (!!(c.links || []).length || !!(c.pick || []).length || (c.lock || {}).on !== false);
}
function urdfSplit(geo, mm, q) {
  const key = mm + "|" + q, had = urdfSplitDone.get(geo);
  if (had && had.key === key) return had.pieces;
  const pos = geo.attributes.position.array, nt = Math.floor(pos.length / 9);
  const ids = /* @__PURE__ */ new Map(), par = [], first = new Int32Array(nt);
  const find = (x) => {
    while (par[x] !== x) {
      par[x] = par[par[x]];
      x = par[x];
    }
    return x;
  };
  const r = (v) => Math.floor(v * mm / q + 0.5);
  for (let t = 0; t < nt; t++) {
    let a = -1;
    for (let c = 0; c < 3; c++) {
      const o = t * 9 + c * 3, k = r(pos[o]) + "," + r(pos[o + 1]) + "," + r(pos[o + 2]);
      let n = ids.get(k);
      if (n === void 0) {
        n = par.length;
        par.push(n);
        ids.set(k, n);
      }
      if (c === 0) {
        first[t] = n;
        a = find(n);
      } else {
        const b = find(n);
        if (a !== b) par[b] = a;
      }
    }
  }
  const groups = /* @__PURE__ */ new Map();
  for (let t = 0; t < nt; t++) {
    const g = find(first[t]);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(t);
  }
  const pieces = [...groups.values()].sort((x, y) => y.length - x.length);
  urdfSplitDone.set(geo, { key, pieces });
  return pieces;
}
const _pA = new THREE.Vector3(), _pB = new THREE.Vector3(), _pC = new THREE.Vector3(), _pT = new THREE.Triangle();
function urdfTriDist(p, t) {
  _pT.set(_pA.fromArray(t, 0), _pB.fromArray(t, 3), _pC.fromArray(t, 6));
  return _pT.closestPointToPoint(p, new THREE.Vector3()).distanceTo(p);
}
function urdfAssign(P, cfg) {
  const owner = P.map((pc) => pc.link);
  (cfg.links || []).forEach((r) => P.forEach((pc, k) => {
    if (pc.link === r.link) owner[k] = r.to;
  }));
  const lock = cfg.lock || {};
  if (lock.on !== false) {
    const smallMm = +lock.smallMm || 12, touch = +lock.touchMm || 0.3, nPts = +lock.points || 120, cell = +lock.cellMm || 4;
    const size = (pc) => Math.max(pc.hi[0] - pc.lo[0], pc.hi[1] - pc.lo[1], pc.hi[2] - pc.lo[2]);
    const big = P.map((pc, k) => k).filter((k) => size(P[k]) > smallMm);
    const grids = {};
    const cellOf = (x, y, z) => Math.floor(x / cell) + "," + Math.floor(y / cell) + "," + Math.floor(z / cell);
    const grid2 = (k) => {
      if (grids[k]) return grids[k];
      const g = /* @__PURE__ */ new Map(), w = P[k].w;
      for (let o = 0; o < w.length; o += 9) {
        const t = w.subarray(o, o + 9);
        const lo = [0, 1, 2].map((a) => Math.floor((Math.min(t[a], t[a + 3], t[a + 6]) - touch) / cell));
        const hi = [0, 1, 2].map((a) => Math.floor((Math.max(t[a], t[a + 3], t[a + 6]) + touch) / cell));
        for (let x = lo[0]; x <= hi[0]; x++) for (let y = lo[1]; y <= hi[1]; y++) for (let z = lo[2]; z <= hi[2]; z++) {
          const c = x + "," + y + "," + z;
          if (!g.has(c)) g.set(c, []);
          g.get(c).push(t);
        }
      }
      return grids[k] = g;
    };
    const p = new THREE.Vector3();
    P.forEach((s, si) => {
      if (size(s) > smallMm) return;
      const nv = s.w.length / 3, step = Math.max(1, Math.floor(nv / nPts));
      let best = -1, score = 0;
      big.forEach((bk) => {
        const b = P[bk];
        for (let a = 0; a < 3; a++) if (s.lo[a] > b.hi[a] + touch || s.hi[a] < b.lo[a] - touch) return;
        const g = grid2(bk);
        let n = 0;
        for (let v = 0; v < nv; v += step) {
          p.fromArray(s.w, v * 3);
          const near = g.get(cellOf(p.x, p.y, p.z));
          if (near && near.some((t) => urdfTriDist(p, t) <= touch)) n++;
        }
        if (n > score || n === score && n && owner[bk] === owner[si]) {
          best = bk;
          score = n;
        }
      });
      s.touch = best >= 0 ? [P[best].link, P[best].i, score] : null;
      if (best >= 0) owner[si] = owner[best];
    });
  }
  (cfg.pick || []).forEach((r) => P.forEach((pc, k) => {
    if (pc.link === r.link && (r.pieces || []).includes(pc.i)) owner[k] = r.to;
  }));
  return owner;
}
function urdfPieces(put, linkG, linkZero, matOf, pairOf) {
  urdfPieceInfo = null;
  const cfg = urdfPiecesCfg();
  if (!urdfPiecesOn() || !put.length) return;
  const q = +(cfg.lock || {}).weldMm || 0.01;
  const P = [], perLink = {};
  put.forEach((u, vi) => {
    const geo = u.mesh.geometry, mm = u.mesh.scale.x;
    const M = new THREE.Matrix4().copy(u.holder.userData.zero).multiply(new THREE.Matrix4().makeScale(u.mesh.scale.x, u.mesh.scale.y, u.mesh.scale.z));
    const pos = geo.attributes.position.array;
    urdfSplit(geo, mm, q).forEach((tris) => {
      const w = new Float32Array(tris.length * 9), v = new THREE.Vector3();
      const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
      tris.forEach((t, j) => {
        for (let c = 0; c < 3; c++) {
          v.fromArray(pos, t * 9 + c * 3).applyMatrix4(M).toArray(w, j * 9 + c * 3);
          for (let a = 0; a < 3; a++) {
            lo[a] = Math.min(lo[a], w[j * 9 + c * 3 + a]);
            hi[a] = Math.max(hi[a], w[j * 9 + c * 3 + a]);
          }
        }
      });
      perLink[u.name] = perLink[u.name] || 0;
      P.push({ link: u.name, i: perLink[u.name]++, vi, tris, w, lo, hi });
    });
  });
  const owner = urdfAssign(P, cfg);
  const moved = [];
  put.forEach((u, vi) => {
    const src = u.mesh.geometry, pos = src.attributes.position.array, nor = src.attributes.normal && src.attributes.normal.array;
    const byOwner = {};
    P.forEach((pc, k) => {
      if (pc.vi === vi) (byOwner[owner[k]] = byOwner[owner[k]] || []).push(pc);
    });
    if (Object.keys(byOwner).length === 1 && byOwner[u.name]) return;
    u.holder.remove(u.mesh);
    const at = pickMeshes.indexOf(u.mesh);
    if (at >= 0) pickMeshes.splice(at, 1);
    Object.entries(byOwner).forEach(([to, pcs]) => {
      if (!linkG[to]) to = u.name;
      const n = pcs.reduce((s, pc) => s + pc.tris.length, 0);
      const ps = new Float32Array(n * 9), ns = nor ? new Float32Array(n * 9) : null;
      let o = 0;
      pcs.forEach((pc) => pc.tris.forEach((t) => {
        ps.set(pos.subarray(t * 9, t * 9 + 9), o);
        if (ns) ns.set(nor.subarray(t * 9, t * 9 + 9), o);
        o += 9;
      }));
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(ps, 3));
      if (ns) g.setAttribute("normal", new THREE.BufferAttribute(ns, 3));
      else g.computeVertexNormals();
      const pair = pairOf(to);
      const m = new THREE.Mesh(g, matOf(pair));
      m.scale.copy(u.mesh.scale);
      m.userData.pair = pair;
      m.userData.urdfLink = to;
      m.userData.urdfFrom = u.name;
      if (pair >= 0) pickMeshes.push(m);
      if (to === u.name) {
        u.holder.add(m);
        return;
      }
      const h = new THREE.Group();
      h.name = "pieces_from_" + u.name;
      new THREE.Matrix4().copy(linkZero[to]).invert().multiply(u.holder.userData.zero).decompose(h.position, h.quaternion, h.scale);
      h.add(m);
      linkG[to].add(h);
      pcs.forEach((pc) => moved.push(u.name + "#" + pc.i + "->" + to));
    });
  });
  urdfPieceInfo = { pieces: P.map((pc, k) => ({
    link: pc.link,
    i: pc.i,
    to: owner[k],
    touch: pc.touch || null,
    lo: pc.lo,
    hi: pc.hi
  })), moved };
}
let rigCadLast = "";
function rigCadCfg() {
  return URDF_CFG && URDF_CFG.rigFromCad || {};
}
function rigCadTakes(part) {
  return (rigCadCfg().take || ["sizes", "shoulders", "shrugPivot"]).includes(part);
}
function rigCadLabel() {
  return rigCadCfg().label || (rigCadTakes("joints") ? "Make the simple shapes match the CAD" : "Use the CAD's sizes and shoulder spots");
}
function rigFromCadMeasure() {
  if (!urdfOn) return { error: "the CAD model is not shown" };
  const cfg = rigCadCfg(), dp = Math.pow(10, cfg.round == null ? 4 : cfg.round);
  const rd = (v) => Math.round(v * dp) / dp;
  for (const side of ["L", "R"])
    if (((URDF_CFG.hands || {})[side] || {}).tip === "mesh" && !urdfTip[side].fromMesh)
      return { error: "the " + (side === "L" ? "left" : "right") + " forearm part has not arrived yet" };
  const keep = pose;
  pose = RIG.zero.slice();
  applyPose();
  robot.updateMatrixWorld(true);
  try {
    const rq = robot.getWorldQuaternion(new THREE.Quaternion()).invert();
    const at = (o) => robot.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const w0 = urdfJ[8] ? at(urdfJ[8].org) : new THREE.Vector3();
    const P = (o) => {
      const v = at(o);
      v.x -= w0.x;
      v.z -= w0.z;
      return v;
    };
    const out = {
      dims: {},
      tilt: RIG.tilt.map((t) => t.slice()),
      after: RIG.after.map((t) => t.slice()),
      mount: { L: RIG.mount.L.slice(), R: RIG.mount.R.slice() },
      order: RIG.order.map((o) => o.slice()),
      warn: []
    };
    const eul = (q) => {
      const e = new THREE.Euler().setFromQuaternion(q, "XYZ");
      return [e.x, e.y, e.z].map((v) => rd(THREE.MathUtils.radToDeg(v)));
    };
    const S = [], E = [], T = [];
    for (let a = 0; a < 2; a++) {
      const b = a * 4, ch = urdfArm[a];
      S[a] = P(ch[0].org);
      E[a] = P(ch[2].org);
      T[a] = P(wristBalls[a]);
      if (P(ch[1].org).distanceTo(S[a]) > (cfg.colocatedMm || 1) || P(ch[3].org).distanceTo(E[a]) > (cfg.colocatedMm || 1))
        out.warn.push("a joint pair of the " + (a ? "right" : "left") + " arm is not at one point in the CAD");
      const ord = [b, b + 1, b + 2, b + 3].sort((x, y) => urdfJ[x].depth - urdfJ[y].depth);
      if ([ord[0], ord[1]].sort().join() !== [b, b + 1].join()) return { error: "the CAD chains the " + (a ? "right" : "left") + " arm in an order the shapes cannot follow" };
      let Wp = new THREE.Quaternion();
      const tilt = [], after = [];
      ord.forEach((j, c) => {
        const e = urdfJ[j];
        const aw = e.axis.clone().applyQuaternion(e.mov.getWorldQuaternion(new THREE.Quaternion())).applyQuaternion(rq).multiplyScalar(e.sign).normalize();
        const T0 = new THREE.Quaternion().setFromUnitVectors(_AXVEC[RIG.axis[j]], aw.applyQuaternion(Wp.clone().invert()));
        let Wn = Wp.clone().multiply(T0), U = new THREE.Quaternion();
        if (c === 1 || c === 3) {
          const bone = (c === 1 ? E[a].clone().sub(S[a]) : T[a].clone().sub(E[a])).normalize();
          const R = c === 3 ? rq.clone().multiply(urdfTip[a ? "R" : "L"].hand.getWorldQuaternion(new THREE.Quaternion())).multiply(new THREE.Quaternion().setFromAxisAngle(_AXVEC.y, -THREE.MathUtils.degToRad(RIG.palmTurn[a] || 0))).multiply(Wn.clone().invert()) : new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, -1, 0).applyQuaternion(Wn), bone);
          const W2 = R.multiply(Wn);
          U = Wn.clone().invert().multiply(W2);
          Wn = W2;
        }
        tilt[j] = eul(T0);
        after[j] = eul(U);
        Wp = Wn;
      });
      if (rigCadTakes("joints")) {
        out.order[a] = ord;
        ord.forEach((j) => {
          out.tilt[j] = tilt[j];
          out.after[j] = after[j];
        });
      }
    }
    const sx = (S[0].x - S[1].x) / 2, sy = RIG.dims.shoulderY || 0;
    if (rigCadTakes("shoulders")) {
      out.dims.shoulderX = rd(sx);
      out.mount.L = [S[0].x - sx, S[0].y - sy, S[0].z].map(rd);
      out.mount.R = [S[1].x + sx, S[1].y - sy, S[1].z].map(rd);
    }
    if (rigCadTakes("sizes")) {
      out.dims.upperLenL = rd(E[0].distanceTo(S[0]));
      out.dims.upperLenR = rd(E[1].distanceTo(S[1]));
      out.dims.foreLenL = rd(T[0].distanceTo(E[0]));
      out.dims.foreLenR = rd(T[1].distanceTo(E[1]));
    }
    if (rigCadTakes("shrugPivot") && urdfJ[9])
      out.dims.shrugPivot = rd(P(urdfJ[9].org).y - (S[0].y + S[1].y) / 2);
    return out;
  } finally {
    pose = keep;
    applyPose();
  }
}
function rigHandsAt(r, p) {
  const keep = RIG;
  RIG = r;
  try {
    return [0, 1].map((a) => {
      const b = a * 4, d = [0, 1, 2, 3].map((k) => (p[b + k] - RIG.zero[b + k]) * jdir(b + k));
      const c = rigChain(b, d), side = a ? -1 : 1, D = RIG.dims, m = RIG.mount[a ? "R" : "L"];
      return new THREE.Vector3(side * D.shoulderX + m[0], D.shoulderY + m[1], m[2]).addScaledVector(new THREE.Vector3(0, -1, 0).applyQuaternion(c.at[1]), a ? D.upperLenR : D.upperLenL).addScaledVector(new THREE.Vector3(0, -1, 0).applyQuaternion(c.at[3]), a ? D.foreLenR : D.foreLenL);
    });
  } finally {
    RIG = keep;
  }
}
function rigCadParts(m) {
  const p = { dims: m.dims };
  if (rigCadTakes("shoulders")) p.mount = m.mount;
  if (rigCadTakes("joints")) {
    p.tilt = m.tilt;
    p.after = m.after;
    p.order = m.order;
  }
  return p;
}
async function rigCadShare(cad) {
  try {
    const r = await fetch("/api/rigcad", { method: "POST", body: JSON.stringify(cad) }).then((r2) => r2.json());
    if (!r.ok) throw new Error(r.error || "no answer");
    return true;
  } catch (e) {
    rigCadLast += " Kept on this browser only: the hub did not take it (" + Mice.Words.plain(e).says + ").";
    renderRigCadUI();
    return false;
  }
}
function rigFromCad() {
  const m = rigFromCadMeasure();
  if (m.error) {
    rigCadLast = "Cannot make the simple shapes from the CAD: " + m.error + ".";
    renderRigCadUI();
    return false;
  }
  const cad = { at: (/* @__PURE__ */ new Date()).toISOString(), parts: rigCadParts(m) };
  const before = rigHandsAt(RIG, RIG.home);
  rigCadAdopt(RIG, cad);
  const mv = rigHandsAt(RIG, RIG.home).map((p, a) => Math.round(p.distanceTo(before[a])));
  rigCadLast = (rigCadTakes("joints") ? "The simple shapes now match the CAD." : "The simple shapes now have the CAD's sizes and shoulder spots; your joints are kept.") + " At home the left hand moved " + mv[0] + " mm and the right " + mv[1] + " mm; the servo numbers did not change." + (m.warn.length ? " " + m.warn.join("; ") + "." : "");
  rigChanged();
  rigCadShare(cad);
  return true;
}
function rigOldBack() {
  if (!RIG.view.oldRig) return false;
  const cad = { at: (/* @__PURE__ */ new Date()).toISOString(), parts: null };
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
const gizmo = new THREE.Group();
let rings = [];
function clearGizmo() {
  rings.forEach((r) => {
    if (r.mesh.parent) r.mesh.parent.remove(r.mesh);
    r.mesh.geometry.dispose();
    r.mesh.material.dispose();
  });
  rings = [];
}
function showGizmo(pairIdx) {
  clearGizmo();
  selPair = pairIdx;
  if (pairIdx < 0) {
    renderSliders();
    return;
  }
  const pr = PAIRS[pairIdx];
  const radius = Math.max(24, (RIG.jointR[pairIdx] || 16) * 2.7);
  pr.joints.forEach((jIdx, k) => {
    const axis = RIG.axis[jIdx];
    const color = axis === "x" ? 16733525 : axis === "z" ? 5614335 : 5635976;
    const tor = new THREE.Mesh(
      new THREE.TorusGeometry(radius + k * 8, 2.6, 10, 48),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.85, depthTest: false })
    );
    tor.renderOrder = 10;
    tor.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), jointAxisVec(jIdx));
    tor.userData.joint = jIdx;
    pairRingParents[pairIdx][k].add(tor);
    rings.push({ mesh: tor, joint: jIdx, localAxis: axis });
  });
  renderSliders();
}
const ray = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let drag = null;
function setMouse(e) {
  const r = renderer.domElement.getBoundingClientRect();
  mouse.x = (e.clientX - r.left) / r.width * 2 - 1;
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
  return sel === "xy" ? new THREE.Vector3(0, 0, 1) : sel === "yz" ? new THREE.Vector3(1, 0, 0) : sel === "xz" ? new THREE.Vector3(0, 1, 0) : activeCam().getWorldDirection(new THREE.Vector3()).negate();
};
renderer.domElement.addEventListener("pointerdown", (e) => {
  if (e.button !== 0) return;
  setMouse(e);
  const ringHit = ray.intersectObjects(rings.map((r) => r.mesh), false)[0];
  if (ringHit) {
    const r = rings.find((x) => x.mesh === ringHit.object);
    const axis = new THREE.Vector3(0, 0, 1).applyQuaternion(r.mesh.getWorldQuaternion(new THREE.Quaternion())).normalize();
    const center = r.mesh.getWorldPosition(new THREE.Vector3());
    const hit = planeHit(center, axis);
    if (!hit) return;
    drag = {
      kind: "ring",
      joint: r.joint,
      axis,
      center,
      ref: hit.clone().sub(center),
      start: pose[r.joint]
    };
    controls.enabled = false;
    return;
  }
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
  const meshHit = ray.intersectObjects(pickMeshes, true)[0];
  if (meshHit) {
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
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") showGizmo(-1);
});
renderer.domElement.addEventListener("dblclick", () => showGizmo(-1));
window.addEventListener("pointermove", (e) => {
  if (!drag) return;
  setMouse(e);
  if (drag.kind === "ring") {
    const hit = planeHit(drag.center, drag.axis);
    if (!hit) return;
    const v = hit.clone().sub(drag.center);
    const ang = Math.atan2(
      drag.axis.dot(new THREE.Vector3().crossVectors(drag.ref, v)),
      drag.ref.dot(v)
    );
    const j = drag.joint;
    pose[j] = clampJ(j, drag.start + jdir(j) * THREE.MathUtils.radToDeg(ang));
    poseChanged(true);
  } else if (drag.kind === "ik") {
    const target = planeHit(drag.planePoint, drag.normal);
    if (target) {
      solveIK(drag.arm, target, 16);
      holdSide(drag.arm, false);
      askReach(drag.arm, target);
      poseChanged(true);
    }
  } else if (drag.kind === "ikElbow") {
    const target = planeHit(drag.planePoint, drag.normal);
    if (target) {
      solveElbowIK(drag.arm, target);
      poseChanged(true);
    }
  }
});
window.addEventListener("pointerup", () => {
  if (!drag) return;
  if (drag.kind === "ik" && handHold[drag.arm]) {
    const t = reachAsk[drag.arm] && reachAsk[drag.arm].target;
    holdSide(drag.arm, true);
    if (t) askReach(drag.arm, t);
  }
  drag = null;
  controls.enabled = true;
  poseChanged(false);
});
function clampDeg(v) {
  return Math.min(180, Math.max(0, Math.round(v * 10) / 10));
}
function wristPos(arm, out) {
  return wristBalls[arm].getWorldPosition(out || new THREE.Vector3());
}
function solveIK(arm, target, iters = 8) {
  const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
  const EPS = 0.6, LAMBDA2 = 4;
  const tmp = new THREE.Vector3();
  for (let iter = 0; iter < iters; iter++) {
    applyPose();
    robot.updateMatrixWorld(true);
    const p = wristPos(arm);
    const e = target.clone().sub(p);
    if (e.length() < 1) break;
    if (e.length() > 120) e.setLength(120);
    const J = [];
    for (let c = 0; c < 4; c++) {
      const j = idx[c], old = pose[j];
      pose[j] = clampJ(j, old + EPS);
      applyPose();
      robot.updateMatrixWorld(true);
      wristPos(arm, tmp);
      J.push(tmp.clone().sub(p).divideScalar(pose[j] - old || EPS));
      pose[j] = old;
    }
    const A = [[LAMBDA2, 0, 0], [0, LAMBDA2, 0], [0, 0, LAMBDA2]];
    const comp = (v, k) => k === 0 ? v.x : k === 1 ? v.y : v.z;
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
  ccdPolish(arm, target, 12);
  applyPose();
}
function ccdChain(idx, endBall, target, rounds) {
  const dist = () => {
    applyPose();
    robot.updateMatrixWorld(true);
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
          if (d < best - 0.02) {
            best = d;
            improved = true;
          } else pose[j] = old;
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
function solveElbowIK(arm, target) {
  const idx = arm === 0 ? [0, 1] : [4, 5];
  const eb = elbowBalls[arm];
  const start = eb.getWorldPosition(new THREE.Vector3());
  const steps = Math.min(30, Math.max(4, Math.ceil(start.distanceTo(target) / 15)));
  for (let s = 1; s <= steps; s++) ccdChain(idx, eb, start.clone().lerp(target, s / steps), 4);
  ccdChain(idx, eb, target, 20);
  applyPose();
}
function mirrorAcrossBody(p, which) {
  const local = bodyGroup.worldToLocal(p.clone());
  if (which === "fb") local.z = -local.z;
  else local.x = -local.x;
  return bodyGroup.localToWorld(local);
}
function mirrorPose(p, which) {
  if (!bodyGroup || !wristBalls[0] || !wristBalls[1]) return null;
  const saved = pose.slice();
  try {
    pose = p.slice();
    applyPose();
    robot.updateMatrixWorld(true);
    const want = [0, 1].map((a) => ({
      elbow: mirrorAcrossBody(elbowBalls[a].getWorldPosition(new THREE.Vector3()), which),
      wrist: mirrorAcrossBody(wristBalls[a].getWorldPosition(new THREE.Vector3()), which)
    }));
    for (const a of [0, 1]) {
      const t = which === "fb" ? want[a] : want[1 - a];
      solveElbowIK(a, t.elbow);
      ccdChain(a === 0 ? [2, 3] : [6, 7], wristBalls[a], t.wrist, 24);
    }
    applyPose();
    const out = pose.slice();
    out[8] = clampJ(8, 180 - p[8]);
    out[9] = p[9];
    return out;
  } finally {
    pose = saved;
    applyPose();
  }
}
function palmUpness(arm) {
  robot.updateMatrixWorld(true);
  const q = palmMarks[arm].getWorldQuaternion(new THREE.Quaternion());
  return new THREE.Vector3(0, 0, 1).applyQuaternion(q).y;
}
function palmUpnessOf(p, arm) {
  if (!palmMarks[arm]) return 0;
  const key = arm + "|" + p.join(",");
  if (palmCache.has(key)) return palmCache.get(key);
  const saved = pose;
  try {
    pose = p.slice();
    applyPose();
    palmCache.set(key, palmUpness(arm));
  } finally {
    pose = saved;
    applyPose();
  }
  return palmCache.get(key);
}
function palmWord(v) {
  return v > 0.5 ? "palm" : v < -0.5 ? "back" : "side";
}
function facePalm(p, arm, want, opts) {
  const o = opts || {}, range = o.range || 180, step = o.step || 5;
  if (!palmMarks[arm] || !wristBalls[arm]) return null;
  const sh = arm === 0 ? [0, 1] : [4, 5], el = arm === 0 ? [2, 3] : [6, 7];
  const W = (o2) => o2.getWorldPosition(new THREE.Vector3());
  const saved = pose;
  try {
    pose = p.slice();
    applyPose();
    robot.updateMatrixWorld(true);
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
        applyPose();
        if (miss > 4) continue;
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
function solve3(A, b) {
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
class StudioCollisionGeometry {
  static clamp(x, a, b) {
    return Math.max(a, Math.min(b, x));
  }
  static box(center, axes, half, name, arm = -1) {
    return { center, axes, half, name, arm };
  }
  static local(p, box) {
    const d = p.clone().sub(box.center);
    return box.axes.map((a) => d.dot(a));
  }
  static pointBox(p, box) {
    return Math.hypot(...this.local(p, box).map((v, i) => Math.max(0, Math.abs(v) - box.half[i])));
  }
  // Exact minimum on the piecewise-quadratic segment-to-AABB distance.
  static segmentBox(a, b, box) {
    const p = this.local(a, box), q = this.local(b, box), d = q.map((v, i) => v - p[i]);
    const ts = [0, 1];
    for (let i = 0; i < 3; i++) if (Math.abs(d[i]) > 1e-10)
      for (const sign of [-1, 1]) {
        const t = (sign * box.half[i] - p[i]) / d[i];
        if (t > 0 && t < 1) ts.push(t);
      }
    ts.sort((x, y) => x - y);
    const sq = (t) => p.reduce((s, v, i) => s + Math.max(0, Math.abs(v + d[i] * t) - box.half[i]) ** 2, 0);
    let best = Math.min(sq(0), sq(1));
    for (let k = 1; k < ts.length; k++) {
      const lo = ts[k - 1], hi = ts[k], mid = (lo + hi) / 2;
      let aa = 0, bb = 0;
      for (let i = 0; i < 3; i++) {
        const v = p[i] + d[i] * mid;
        if (Math.abs(v) > box.half[i]) {
          aa += d[i] ** 2;
          bb += d[i] * (p[i] - Math.sign(v) * box.half[i]);
        }
      }
      const t = aa ? this.clamp(-bb / aa, lo, hi) : mid;
      best = Math.min(best, sq(lo), sq(hi), sq(t));
    }
    return Math.sqrt(best);
  }
  static boxesHit(a, b, gap) {
    const axes = [...a.axes, ...b.axes];
    for (const x of a.axes) for (const y of b.axes) {
      const c = x.clone().cross(y);
      if (c.lengthSq() > 1e-12) axes.push(c.normalize());
    }
    const delta = b.center.clone().sub(a.center);
    for (const axis of axes) {
      const ra = a.axes.reduce((s, x, i) => s + (a.half[i] + gap / 2) * Math.abs(axis.dot(x)), 0);
      const rb = b.axes.reduce((s, x, i) => s + (b.half[i] + gap / 2) * Math.abs(axis.dot(x)), 0);
      if (Math.abs(delta.dot(axis)) >= ra + rb) return false;
    }
    return true;
  }
  static snapshot(p) {
    const saved = pose;
    try {
      pose = p.slice();
      applyPose();
      robot.updateMatrixWorld(true);
      const inv = bodyGroup.matrixWorld.clone().invert();
      const at = (o) => o.getWorldPosition(new THREE.Vector3()).applyMatrix4(inv);
      const basis = [new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 1)];
      const d = RIG.dims;
      const torso = this.box(new THREE.Vector3(), basis, [d.torsoW / 2, d.torsoH / 2, d.torsoD / 2], "body");
      const head = { at: new THREE.Vector3(0, d.torsoH / 2 + 68, 0), r: R_HEAD, name: "head" };
      const arms = [0, 1].map((arm) => {
        const label = arm ? "right" : "left", j = arm * 4;
        const s = at(jointGroups[j]), e = at(elbowBalls[arm]), w = at(wristBalls[arm]);
        const sr = RIG.jointR[arm * 2], er = RIG.jointR[arm * 2 + 1];
        const start = segPoint(s, e, Math.min(0.8, (sr + CLEAR) / Math.max(1, s.distanceTo(e))));
        const bars = [
          { a: start, b: e, r: RIG.barR[arm * 2], name: label + " upper arm" },
          { a: e, b: w, r: RIG.barR[arm * 2 + 1], name: label + " forearm" }
        ];
        let hand = null;
        palmMarks[arm].traverse((o) => {
          if (hand || !o.geometry || o.geometry.type !== "BoxGeometry") return;
          o.geometry.computeBoundingBox();
          const bb = o.geometry.boundingBox;
          const matrix = inv.clone().multiply(o.matrixWorld), el = matrix.elements;
          const center = bb.getCenter(new THREE.Vector3()).applyMatrix4(matrix);
          const axes = [new THREE.Vector3(el[0], el[1], el[2]), new THREE.Vector3(el[4], el[5], el[6]), new THREE.Vector3(el[8], el[9], el[10])];
          const size = bb.getSize(new THREE.Vector3()).toArray();
          const half = axes.map((a, i) => size[i] * a.length() / 2);
          axes.forEach((a) => a.normalize());
          hand = this.box(center, axes, half, label + " hand", arm);
        });
        return { s, e, w, sr, er, bars, hand, label };
      });
      return { torso, head, arms };
    } finally {
      pose = saved;
      applyPose();
      robot.updateMatrixWorld(true);
    }
  }
  static hit(p) {
    var _a;
    if (!Array.isArray(p) || p.length !== NJ || !p.every(Number.isFinite)) return "the pose is invalid";
    if (![...RIG.jointR, ...RIG.barR, RIG.dims.torsoW, RIG.dims.torsoH, RIG.dims.torsoD].every((v) => Number.isFinite(v) && v > 0))
      return "the physical collision sizes are invalid";
    const extra = (_a = RIG.extraClearanceMm) != null ? _a : 0;
    if (!Number.isFinite(extra) || extra < 0) return "the extra safety gap is invalid";
    const gap = CLEAR + extra + (planPace() === "music" ? SAFE.musicGapMm : 0), { torso, head, arms } = this.snapshot(p);
    const sphereBox = (s, box) => this.pointBox(s.at, box) < s.r + gap;
    const sphereBar = (s, bar) => segSegDist(s.at, s.at, bar.a, bar.b) < s.r + bar.r + gap;
    for (const a of arms) {
      if (sphereBar({ at: a.s, r: a.sr }, a.bars[1])) return a.label + " forearm is too close to its shoulder joint";
      const upper = a.bars[0], fore = a.bars[1];
      const upperEnd = segPoint(a.e, upper.a, Math.min(1, (a.er + upper.r + gap) / Math.max(1, a.e.distanceTo(upper.a))));
      const foreStart = segPoint(a.e, a.w, Math.min(1, (a.er + fore.r + gap) / Math.max(1, a.e.distanceTo(a.w))));
      if (segSegDist(upper.a, upperEnd, foreStart, a.w) < upper.r + fore.r + gap)
        return a.label + " forearm is too close to its upper arm";
      if (a.s.distanceTo(head.at) < a.sr + head.r + gap) return a.label + " shoulder joint is too close to the head";
      for (const bar of a.bars) {
        if (this.segmentBox(bar.a, bar.b, torso) < bar.r + gap) return bar.name + " is too close to the body";
        if (sphereBar(head, bar)) return bar.name + " is too close to the head";
      }
      const elbow = { at: a.e, r: a.er };
      if (sphereBox(elbow, torso)) return a.label + " elbow joint is too close to the body";
      if (a.e.distanceTo(head.at) < a.er + head.r + gap) return a.label + " elbow joint is too close to the head";
      if (a.hand) {
        if (this.pointBox(a.e, a.hand) < a.er + gap) return a.hand.name + " is too close to its elbow joint";
        if (this.boxesHit(a.hand, torso, gap)) return a.hand.name + " is too close to the body";
        if (sphereBox(head, a.hand)) return a.hand.name + " is too close to the head";
        if (this.segmentBox(a.bars[0].a, a.bars[0].b, a.hand) < a.bars[0].r + gap)
          return a.hand.name + " is too close to its upper arm";
        if (this.pointBox(a.s, a.hand) < a.sr + gap) return a.hand.name + " is too close to its shoulder joint";
      }
    }
    const [l, r] = arms;
    for (const a of [l, r]) {
      const other = a === l ? r : l;
      for (const bar of a.bars) {
        for (const ob of other.bars)
          if (segSegDist(bar.a, bar.b, ob.a, ob.b) < bar.r + ob.r + gap) return bar.name + " is too close to the opposite arm";
        for (const s of [{ at: other.s, r: other.sr }, { at: other.e, r: other.er }])
          if (sphereBar(s, bar)) return bar.name + " is too close to the opposite joint";
        if (other.hand && this.segmentBox(bar.a, bar.b, other.hand) < bar.r + gap)
          return bar.name + " is too close to the opposite hand";
      }
      if (a.hand) {
        for (const s of [{ at: other.s, r: other.sr }, { at: other.e, r: other.er }])
          if (sphereBox(s, a.hand)) return a.hand.name + " is too close to the opposite joint";
      }
    }
    for (const a of [{ at: l.s, r: l.sr }, { at: l.e, r: l.er }])
      for (const b of [{ at: r.s, r: r.sr }, { at: r.e, r: r.er }])
        if (a.at.distanceTo(b.at) < a.r + b.r + gap) return "the opposite joint balls are too close";
    if (l.hand && r.hand && this.boxesHit(l.hand, r.hand, gap)) return "the hands are too close to each other";
    return null;
  }
}
let CLEAR = 10;
const R_ARM = 14, R_WRIST = 16, R_HEAD = 46;
function distToBox(p, hx, hy, hz) {
  const dx = Math.max(Math.abs(p.x) - hx, 0);
  const dy = Math.max(Math.abs(p.y) - hy, 0);
  const dz = Math.max(Math.abs(p.z) - hz, 0);
  return Math.hypot(dx, dy, dz);
}
function segPoint(a, b, t) {
  return new THREE.Vector3(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t);
}
function segSegDist(p1, q1, p2, q2) {
  const d1 = q1.clone().sub(p1), d2 = q2.clone().sub(p2), r = p1.clone().sub(p2);
  const a = d1.dot(d1), e = d2.dot(d2), f = d2.dot(r);
  let s, t;
  if (a <= 1e-8 && e <= 1e-8) return r.length();
  if (a <= 1e-8) {
    s = 0;
    t = Math.min(1, Math.max(0, f / e));
  } else {
    const c = d1.dot(r);
    if (e <= 1e-8) {
      t = 0;
      s = Math.min(1, Math.max(0, -c / a));
    } else {
      const b = d1.dot(d2), den = a * e - b * b;
      s = den > 1e-8 ? Math.min(1, Math.max(0, (b * f - c * e) / den)) : 0;
      t = (b * s + f) / e;
      if (t < 0) {
        t = 0;
        s = Math.min(1, Math.max(0, -c / a));
      } else if (t > 1) {
        t = 1;
        s = Math.min(1, Math.max(0, (b - c) / a));
      }
    }
  }
  return segPoint(p1, q1, s).sub(segPoint(p2, q2, t)).length();
}
function fkPoints(p) {
  const saved = pose;
  pose = p.slice();
  pose[8] = RIG.zero[8];
  pose[9] = RIG.zero[9];
  applyPose();
  robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const out = {
    shL: W(jointGroups[0].parent),
    elL: W(jointGroups[2].parent),
    wrL: W(wristBalls[0]),
    shR: W(jointGroups[4].parent),
    elR: W(jointGroups[6].parent),
    wrR: W(wristBalls[1])
  };
  pose = saved;
  applyPose();
  return out;
}
function collisionAt(p) {
  return StudioCollisionGeometry.hit(p);
}
function clearBadMarks() {
  keys.forEach((k) => delete k.bad);
}
let crashForced = false;
let previewOnly = false;
function crashGate(action) {
  const problems = checkCollisions(false);
  if (!problems.length) {
    crashForced = false;
    return true;
  }
  const shown = problems.slice(0, 6).join("\n") + (problems.length > 6 ? "\n…and " + (problems.length - 6) + " more" : "");
  crashForced = false;
  const st = $("tlStat");
  const message = "Not sent: this movement does not keep the safety gap. Fix the red keyframes or adjust the rig/gap in Setup.\n" + shown;
  if (st) st.textContent = message;
  notice(message);
  return false;
}
function checkCollisions(showAlert) {
  clearBadMarks();
  const problems = [];
  const K = playKeys();
  if (K.length) {
    const c0 = collisionAt(K[0].pose);
    if (c0) {
      keys[K[0].src].bad = c0;
      problems.push("keyframe " + K[0].src + " (start pose): " + c0);
    }
  }
  for (let i = 1; i < K.length; i++) {
    for (let s = 1; s <= 12; s++) {
      const f = 0.5 - 0.5 * Math.cos(Math.PI * s / 12);
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
      alert("CAN'T RUN — the robot will crash:\n\n" + problems.join("\n") + "\n\nThe bad keyframes are marked RED in the timeline. Fix the pose (or add an in-between keyframe that goes around) and check again.");
    else
      $("tlStat").textContent = "collision check passed — the sequence is safe ✓";
  }
  return problems;
}
let SAFE = {
  planner: "rrt-star",
  // "straight" refuses; rrt-connect remains available
  clearMm: 10,
  // every check: closer than this is a hit (CLEAR)
  musicGapMm: 7,
  // extra gap at the music pace: fast moves cut corners (nong_sim)
  checkDeg: 1,
  // biggest joint change between two checked points
  stepDeg: 12,
  // how far a tree grows per try
  goalBias: 0.2,
  budgetMs: 1500,
  // planning in the editor (video, gestures)
  liveBudgetMs: 60,
  // planning while following: miss it and the arm holds
  shortcuts: 60,
  seed: 1,
  seedBudgetMs: 40,
  optimizeMs: 80,
  sliceMs: 12,
  maxNodes: 2e3,
  rewireFactor: 1.1
};
let SAFE_ERROR = "";
function loadSafeSettings(j) {
  const bounds = {
    checkDeg: [0.05, 10],
    stepDeg: [0.1, 180],
    goalBias: [0, 1],
    budgetMs: [1, 3e4],
    liveBudgetMs: [1, 5e3],
    shortcuts: [0, 500],
    seed: [0, 4294967295],
    seedBudgetMs: [0, 100],
    optimizeMs: [0, 1e3],
    sliceMs: [1, 50],
    maxNodes: [2, 1e4],
    rewireFactor: [1, 5],
    musicGapMm: [0, 100],
    clearMm: [0, 50]
  };
  if (!j || typeof j !== "object") {
    SAFE_ERROR = "invalid path settings";
    return false;
  }
  const next = { ...SAFE };
  for (const key of Object.keys(SAFE)) if (key in j) next[key] = j[key];
  if (!["straight", "rrt-connect", "rrt-star"].includes(next.planner)) {
    SAFE_ERROR = "unknown path planner";
    return false;
  }
  for (const [key, [lo, hi]] of Object.entries(bounds)) {
    if (!Number.isFinite(next[key]) || next[key] < lo || next[key] > hi || ["shortcuts", "seed", "maxNodes"].includes(key) && !Number.isInteger(next[key])) {
      SAFE_ERROR = "invalid path setting: " + key;
      return false;
    }
  }
  Object.assign(SAFE, next);
  SAFE_ERROR = "";
  CLEAR = SAFE.clearMm;
  return true;
}
fetch("safe_path.json").then((r) => r.json()).then(loadSafeSettings).catch(() => {
});
function safeRevision() {
  return JSON.stringify([SAFE, SAFE_ERROR, RIG]);
}
function safeRng(seed) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
}
function safeGap(a, b) {
  var _a, _b;
  let m = 0;
  for (let j = 0; j < NJ; j++) m = Math.max(m, Math.abs(((_a = b[j]) != null ? _a : 90) - ((_b = a[j]) != null ? _b : 90)));
  return m;
}
function safeLerp(a, b, f) {
  return a.map((v, j) => v + (b[j] - v) * f);
}
function poseHit(p) {
  return collisionAt(p);
}
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
function planSafe(a, b, budgetMs, seed) {
  const saved = pose;
  try {
    const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
    let result;
    do {
      result = search.next();
    } while (!result.done);
    return result.value;
  } finally {
    pose = saved;
    applyPose();
  }
}
async function planSafeAsync(a, b, budgetMs, seed, cancelled = () => false) {
  const revision = safeRevision();
  const stale = () => cancelled() || revision !== safeRevision();
  const search = safeSearch(Array.isArray(a) ? a.slice() : a, Array.isArray(b) ? b.slice() : b, budgetMs, seed);
  for (; ; ) {
    if (stale()) return { fail: "movement cancelled or safety settings changed", cancelled: true };
    const saved = pose, until = performance.now() + Math.max(1, SAFE.sliceMs);
    let result;
    try {
      do {
        result = search.next();
      } while (!result.done && performance.now() < until);
    } finally {
      pose = saved;
      applyPose();
    }
    if (result.done) return stale() ? { fail: "movement cancelled or safety settings changed", cancelled: true } : result.value;
    await new Promise((resolve) => setTimeout(resolve, 0));
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
  const t0 = performance.now(), budget = Math.max(1, budgetMs != null ? budgetMs : SAFE.budgetMs);
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
    if (SAFE.planner === "rrt-connect") path = rrtConnect(a, b, budget, safeRng(seed != null ? seed : SAFE.seed), t0);
    else path = yield* rrtStar(a, b, budget, safeRng(seed != null ? seed : SAFE.seed), t0, stats);
    if (!path) return { fail: "no checked way round found in " + Math.round(budget) + " ms" };
    path = safeShortcut(path, safeRng((seed != null ? seed : SAFE.seed) + 7));
  }
  path = path.map((q, i) => i === 0 ? a.slice() : q.map((v) => +fmtA(v)));
  for (let i = 0; i < path.length; i++) {
    if (safePoseError(path[i]) || i && pathHit(path[i - 1], path[i]))
      return { fail: "the final rounded path is not clear; the robot will hold" };
  }
  return { path, how, planner: SAFE.planner, stats, ms: performance.now() - t0 };
}
function* rrtStar(a, b, budgetMs, rnd, t0, stats) {
  const end = t0 + budgetMs;
  const body = (q) => q.slice();
  const distance = (p, q) => Math.hypot(...p.map((v, j) => v - q[j]));
  const free = (p, q) => !pathHit(body(p), body(q));
  const goal = b.slice(0, NJ), nodes = [], goals = /* @__PURE__ */ new Set();
  const add = (q, up) => {
    const n = { q, up, children: /* @__PURE__ */ new Set(), cost: up < 0 ? 0 : nodes[up].cost + distance(nodes[up].q, q) };
    nodes.push(n);
    if (up >= 0) nodes[up].children.add(nodes.length - 1);
    return nodes.length - 1;
  };
  add(a.slice(0, NJ), -1);
  const seeded = rrtConnect(a, b, Math.min(budgetMs * 0.25, SAFE.seedBudgetMs), rnd, t0);
  if (seeded) for (let i = 1; i < seeded.length; i++) add(seeded[i].slice(0, NJ), nodes.length - 1);
  if (seeded) goals.add(nodes.length - 1);
  let best = seeded ? nodes.length - 1 : -1;
  let bestCost = best < 0 ? Infinity : nodes[best].cost;
  let improveUntil = seeded ? Math.min(end, performance.now() + SAFE.optimizeMs) : end;
  while (performance.now() < improveUntil && nodes.length < SAFE.maxNodes) {
    const sample = rnd() < SAFE.goalBias ? goal : RIG.min.slice(0, NJ).map((l, j) => l + rnd() * (RIG.max[j] - l));
    const ranked = nodes.map((n, i) => ({ i, d: distance(n.q, sample) })).sort((x, y) => x.d - y.d);
    const nearest = nodes[ranked[0].i].q;
    const gap = Math.max(...sample.map((v, j) => Math.abs(v - nearest[j])));
    if (gap < 1e-6) {
      yield;
      continue;
    }
    const q = nearest.map((v, j) => v + (sample[j] - v) * Math.min(1, SAFE.stepDeg / gap));
    const k = Math.min(nodes.length, Math.ceil(SAFE.rewireFactor * Math.E * (1 + 1 / NJ) * Math.log(nodes.length + 1)));
    const near = nodes.map((n, i) => ({ i, d: distance(n.q, q) })).sort((x, y) => x.d - y.d).slice(0, k);
    const parents = near.slice().sort((x, y) => nodes[x.i].cost + x.d - nodes[y.i].cost - y.d);
    let parent = -1;
    for (const n of parents) {
      if (performance.now() >= end) break;
      if (free(nodes[n.i].q, q)) {
        parent = n.i;
        break;
      }
    }
    if (parent < 0) {
      yield;
      continue;
    }
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
      while (pending.length) {
        const child = pending.pop();
        nodes[child].cost += delta;
        pending.push(...nodes[child].children);
      }
      stats.rewires++;
    }
    if (performance.now() < end && free(q, goal)) goals.add(index);
    for (const i of goals) {
      const cost = nodes[i].cost + distance(nodes[i].q, goal);
      if (cost + 1e-7 < bestCost) {
        if (best < 0) improveUntil = Math.min(end, performance.now() + SAFE.optimizeMs);
        else stats.improvements++;
        best = i;
        bestCost = cost;
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
function rrtConnect(a, b, budgetMs, rnd, t0) {
  const lo = RIG.min.slice(0, NJ), hi = RIG.max.slice(0, NJ);
  const body = (q) => q.slice();
  const arm = (p) => p.slice(0, NJ);
  const free = (p, q) => !pathHit(body(p, 0.5), body(q, 0.5));
  const A = [{ q: arm(a), up: -1 }], B = [{ q: arm(b), up: -1 }];
  const near = (T, q) => {
    let best = 0, bd = Infinity;
    for (let i = 0; i < T.length; i++) {
      let d = 0;
      for (let j = 0; j < NJ; j++) d += (T[i].q[j] - q[j]) ** 2;
      if (d < bd) {
        bd = d;
        best = i;
      }
    }
    return best;
  };
  const steer = (from, to) => {
    const g = Math.max(...to.map((v, j) => Math.abs(v - from[j])));
    return g <= SAFE.stepDeg ? to.slice() : from.map((v, j) => v + (to[j] - v) * SAFE.stepDeg / g);
  };
  const extend = (T, q) => {
    const n = near(T, q), s = steer(T[n].q, q);
    if (!free(T[n].q, s)) return -1;
    T.push({ q: s, up: n });
    return T.length - 1;
  };
  const connect = (T, q) => {
    while (performance.now() - t0 < budgetMs) {
      const i = extend(T, q);
      if (i < 0) return -1;
      if (Math.max(...T[i].q.map((v, j) => Math.abs(v - q[j]))) < 1e-6) return i;
    }
    return -1;
  };
  const chain = (T, i) => {
    const out = [];
    for (; i >= 0; i = T[i].up) out.push(T[i].q);
    return out;
  };
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
function safeShortcut(path, rnd) {
  let p = path.slice();
  for (let r = 0; r < SAFE.shortcuts && p.length > 2; r++) {
    const i = Math.floor(rnd() * (p.length - 2)), k = i + 2 + Math.floor(rnd() * (p.length - i - 2));
    if (k < p.length && !pathHit(p[i], p[k])) p = p.slice(0, i + 1).concat(p.slice(k));
  }
  return p;
}
function safeKeys(K, budgetMs, keepTime) {
  var _a, _b, _c, _d;
  const out = [], tally = { dropped: 0, around: 0, failed: 0 };
  for (const k0 of K) {
    const k = { ...k0, pose: k0.pose.map((v, j) => clampJ(j, v)) };
    const prev = out[out.length - 1];
    if (!prev) {
      if (poseHit(k.pose)) {
        tally.dropped++;
        continue;
      }
      out.push(k);
      continue;
    }
    const plan = planSafe(prev.pose, k.pose, budgetMs);
    if (plan.fail) {
      prev.hold = (prev.hold || 0) + (k.t || 0) + (k.hold || 0);
      if (Number.isFinite(k.sourceMs)) prev.sourceHoldEnd = (_a = k.sourceHoldEnd) != null ? _a : k.sourceMs;
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
        if (Number.isFinite(k.sourceMs)) prev.sourceHoldEnd = (_b = k.sourceHoldEnd) != null ? _b : k.sourceMs;
        tally.failed++;
        continue;
      }
      tally.around++;
      const legT = (i) => Math.round(need[i] + Math.max(0, spare) * legs[i] / all);
      const total = legs.reduce((s, _, i) => s + legT(i), 0), sourceFrom = (_c = prev.sourceHoldEnd) != null ? _c : prev.sourceMs;
      let elapsed = 0;
      plan.path.slice(1, -1).forEach((q, i) => {
        elapsed += legT(i);
        const sourceMs = Number.isFinite(k.sourceMs) ? sourceFrom + (k.sourceMs - sourceFrom) * elapsed / total : void 0;
        out.push({ pose: q, hold: 0, tset: k.tset, via: true, t: legT(i), sourceMs, sourceHoldEnd: sourceMs });
      });
      k.t = legT(legs.length - 1);
    } else if (keepTime && minTime(prev.pose, k.pose) > (k.t || 0) + 1) {
      const f = Math.max(0, Math.min(1, ((k.t || 0) - 1) / minTime(prev.pose, k.pose)));
      k.pose = safeLerp(prev.pose, k.pose, f).map((v, j) => clampJ(j, v));
    }
    const actualPrev = out[out.length - 1];
    if (!keepTime) k.t = Math.max(k.t || 0, minTime(actualPrev.pose, k.pose));
    if (keepTime && minTime(actualPrev.pose, k.pose) > k.t) {
      const target = k.pose.slice();
      let lo = 0, hi = 1, best = actualPrev.pose.slice();
      for (let z = 0; z < 18; z++) {
        const f = (lo + hi) / 2, q = safeLerp(actualPrev.pose, target, f).map((v, j) => clampJ(j, v));
        if (minTime(actualPrev.pose, q) <= k.t) {
          best = q;
          lo = f;
        } else hi = f;
      }
      k.pose = best;
    }
    if (poseHit(k.pose) || pathHit(actualPrev.pose, k.pose)) {
      actualPrev.hold = (actualPrev.hold || 0) + (k.t || 0) + (k.hold || 0);
      if (Number.isFinite(k.sourceMs)) actualPrev.sourceHoldEnd = (_d = k.sourceHoldEnd) != null ? _d : k.sourceMs;
      tally.failed++;
      continue;
    }
    out.push(k);
  }
  return Object.assign({ keys: out }, tally);
}
function safeSay(r) {
  const bits = [];
  if (r.around) bits.push(r.around + " move" + (r.around > 1 ? "s" : "") + " go round the body instead of through it");
  if (r.dropped) bits.push(r.dropped + " pose" + (r.dropped > 1 ? "s" : "") + " would make the arm hit itself, so the arm holds instead");
  if (r.failed) bits.push(r.failed + " move" + (r.failed > 1 ? "s" : "") + " had no safe way round, so the arm holds instead");
  return bits.length ? "Safe path: " + bits.join("; ") + "." : "";
}
let safeMotionEpoch = 0, safeGoalRevision = 0;
let safeMotionTail = Promise.resolve(), safeCancelTail = Promise.resolve(), lastSafeMove = Promise.resolve(true);
let safeTimelineCache = null, timelinePreparing = false;
let safeActiveDevice = null;
function safeDevice() {
  return { dev: moduleDev(), port: serialPort, bus: busId(), target: safeTarget() };
}
async function safeDeviceCmd(device, c) {
  if (device.dev) {
    const q = new URLSearchParams({ dev: device.dev, c });
    const r = await fetch("/api/dev/cmd?" + q);
    if (!r.ok) throw new Error(await r.text());
    return (await r.text()).trim();
  }
  return serialCmd(c, { port: device.port, id: device.bus });
}
function withSafeMotion(work) {
  const result = safeMotionTail.catch(() => {
  }).then(async () => {
    await safeCancelTail;
    return work();
  });
  safeMotionTail = result.catch(() => {
  });
  return result;
}
function safeTarget() {
  return moduleDev() + "|" + (boardSafeIdentity || "");
}
function safeMotionNote(text, warning = false) {
  if ($("robotStat")) $("robotStat").textContent = text;
  if ($("tlStat")) $("tlStat").textContent = text;
  if (warning) notice(text);
}
function cancelSafeMotion(reason, opts = {}) {
  if (opts.previewOnly) {
    safeMotionEpoch++;
    playing = false;
    entryHold = false;
    seekToken++;
    if (typeof sequenceAudio !== "undefined") sequenceAudio.pausePreview();
    if ($("playBtn")) $("playBtn").textContent = "▶ Play";
    keepAwake(false);
    return Promise.resolve(false);
  }
  const device = safeActiveDevice || (haveRobot() ? safeDevice() : null);
  liveAbort();
  if (reason !== "sequence takeover") {
    playing = false;
    entryHold = false;
    seekToken++;
    if ($("playBtn")) $("playBtn").textContent = "▶ Play";
    keepAwake(false);
  }
  if (!currentUser || !device) return Promise.resolve(false);
  const stop = safeCancelTail.catch(() => {
  }).then(async () => {
    await hubStop();
    try {
      await safeDeviceCmd(device, "STOP");
    } catch (e) {
      safeMotionNote("Could not confirm Stop: " + e.message, true);
    }
    return false;
  });
  safeCancelTail = stop;
  return stop;
}
function safeStale(epoch, device, revision) {
  return !currentUser || !haveRobot() || epoch !== safeMotionEpoch || device !== safeTarget() || revision !== safeRevision();
}
async function safeIdle(stale, expected, progress) {
  const deadline = performance.now() + 9e4;
  while (!stale()) {
    const status = await getStatus();
    if (stale()) return null;
    const q = status.module && status.module.joints;
    if (!Array.isArray(q) || q.length !== NJ || q.some((v) => !Number.isFinite(v)))
      throw new Error("the robot did not report its current pose");
    if (progress) progress(status);
    if (typeof status.module.moving !== "boolean" || !status.seq || typeof status.seq.running !== "boolean")
      throw new Error("the robot did not report whether it is moving");
    if (!status.module.moving && !status.seq.running) {
      if (expected && safeGap(q, expected) > 0.15)
        throw new Error("the robot stopped away from the checked waypoint; reconnect before retrying");
      return status;
    }
    if (performance.now() >= deadline) throw new Error("the robot did not confirm that movement finished");
    await new Promise((resolve) => setTimeout(resolve, 60));
  }
  return null;
}
async function safeTakeover(stale) {
  if (stale()) return null;
  safeActiveDevice = safeDevice();
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
    if (!Array.isArray(m.min) || !Array.isArray(m.max) || !Number.isFinite(m.min[j]) || !Number.isFinite(m.max[j]) || RIG.min[j] < m.min[j] - 0.01 || RIG.max[j] > m.max[j] + 0.01)
      throw new Error("Studio limits exceed the robot limits; match them in Setup before moving");
  }
  return status;
}
function safeLegKeys(path, key) {
  const lengths = path.slice(1).map((q, i) => safeGap(path[i], q));
  const need = path.slice(1).map((q, i) => Math.ceil(Math.max(MIN_MOVE_MS, minTime(path[i], q))));
  const total = lengths.reduce((a, b) => a + b, 0) || 1;
  const spare = Math.max(0, (key.t || 0) - need.reduce((a, b) => a + b, 0));
  return path.slice(1).map((q, i) => ({
    ...key,
    pose: q.slice(),
    t: Math.ceil(need[i] + spare * lengths[i] / total),
    hold: i === need.length - 1 ? key.hold || 0 : 0,
    cues: i === 0 ? (key.cues || []).slice() : [],
    cuesAfter: i === need.length - 1 ? (key.cuesAfter || []).slice() : [],
    name: i === need.length - 1 ? key.name || "" : "checked detour",
    via: i !== need.length - 1
  }));
}
async function checkedPoseUnlocked(goal, requestedMs, epoch, goalRevision, initial, progress) {
  const device = safeTarget(), revision = safeRevision();
  const hardStale = () => safeStale(epoch, device, revision);
  const replaced = () => goalRevision !== null && goalRevision !== safeGoalRevision;
  const stale = () => hardStale() || replaced();
  const status = initial || await safeTakeover(hardStale);
  if (!status || hardStale()) return false;
  const source = status.module.joints.slice();
  const plan = await planSafeAsync(source, goal, SAFE.budgetMs, SAFE.seed, hardStale);
  if (hardStale()) return false;
  if (plan.fail) {
    safeMotionNote("Not moved: " + plan.fail, true);
    return false;
  }
  const duration = requestedMs || autoTime(source, goal, status.module.speed_dps || speedDps());
  const legs = safeLegKeys(plan.path, { t: duration, hold: 0 });
  if (plan.how === "around") safeMotionNote("RRT*: going around the body in " + legs.length + " checked moves; keeping an extra " + (RIG.extraClearanceMm || 0) + " mm gap.", true);
  let actual = source;
  for (let index = 0; index < legs.length; index++) {
    const leg = legs[index];
    if (hardStale() || index > 0 && replaced()) return false;
    if (safePoseError(actual) || pathHit(actual, leg.pose))
      throw new Error("the reported pose does not have a clear route to the next waypoint");
    const started = performance.now();
    const reply = await rawCmd("POSE " + leg.pose.map(fmtA).join(" ") + " T " + leg.t);
    liveRtt += (performance.now() - started - liveRtt) * 0.25;
    if (!/^OK\b/.test(reply)) throw new Error(reply || "the robot refused the move");
    if (hardStale()) return false;
    const arrived = await safeIdle(hardStale, leg.pose, progress);
    if (!arrived) return false;
    actual = arrived.module.joints.slice();
    if (entryHold) {
      pose = actual.slice();
      applyPose();
      renderSliders();
    }
  }
  return !stale();
}
async function checkedPose(goal, ms, epoch, goalRevision, target) {
  return withSafeMotion(async () => {
    if (target !== safeTarget() || epoch !== safeMotionEpoch) return false;
    const device = safeDevice();
    try {
      return await checkedPoseUnlocked(goal, ms, epoch, goalRevision);
    } catch (e) {
      liveAbort();
      try {
        await safeDeviceCmd(device, "STOP");
      } catch (_) {
      }
      safeMotionNote("Movement stopped: " + Mice.Words.plain(e).says, true);
      return false;
    }
  });
}
function safeTimelineSignature() {
  return keysSignature() + "|" + !!$("loopChk").checked + "|" + safeRevision();
}
function checkedTimeline() {
  return safeTimelineCache && safeTimelineCache.sig === safeTimelineSignature() ? safeTimelineCache.keys : null;
}
function safeClockGroups(K) {
  const groups = [];
  let at = K.length ? K[0].hold || 0 : 0;
  for (let j = 1; j < K.length; j++) {
    const id = K[j].loopReturn ? "loop" : K[j].src;
    let g = groups[groups.length - 1];
    if (!g || g.id !== id) {
      g = { id, start: at, move: 0, hold: 0 };
      groups.push(g);
    }
    g.move += K[j].t || 0;
    g.hold += K[j].hold || 0;
    at += (K[j].t || 0) + (K[j].hold || 0);
  }
  return { first: K.length ? K[0].hold || 0 : 0, groups, total: at };
}
function safeRemapClock(ms, before, after) {
  const a = safeClockGroups(before), b = safeClockGroups(after);
  if (!(ms > 0)) return 0;
  if (ms < a.first) return a.first ? b.first * ms / a.first : 0;
  const g = a.groups.find((x) => ms < x.start + x.move + x.hold);
  const n = g && b.groups.find((x) => x.id === g.id);
  if (!n) return g ? Math.min(ms, b.total) : b.total;
  const offset = ms - g.start;
  if (offset < g.move) return n.start + (g.move ? n.move * offset / g.move : 0);
  return n.start + n.move + Math.min(n.hold, offset - g.move);
}
async function ensureSafeTimeline(cancelled = () => false) {
  const sig = safeTimelineSignature();
  if (checkedTimeline()) return true;
  const before = playKeys();
  const source = buildPlayKeys().map((k) => ({ ...k, pose: k.pose.slice() }));
  if (!source.length) return false;
  const stale = () => cancelled() || sig !== safeTimelineSignature();
  const error = safePoseError(source[0].pose);
  if (error) {
    safeMotionNote("Cannot play: starting pose " + error, true);
    return false;
  }
  const out = [source[0]], loop = !!$("loopChk").checked;
  const remaining = source.slice(1);
  if (loop && source.length > 1) remaining.push({
    ...source[0],
    hold: 0,
    cues: [],
    cuesAfter: [],
    t: autoTime(source[source.length - 1].pose, source[0].pose, speedDps()),
    loopReturn: true
  });
  let around = 0;
  for (const key of remaining) {
    const plan = await planSafeAsync(out[out.length - 1].pose, key.pose, SAFE.budgetMs, SAFE.seed, stale);
    if (stale()) return false;
    if (plan.fail) {
      safeMotionNote("Cannot play: " + plan.fail + ". Fix the highlighted pose or reduce the extra gap.", true);
      return false;
    }
    if (plan.how === "around") around++;
    out.push(...safeLegKeys(plan.path, key));
  }
  if (stale()) return false;
  playT = safeRemapClock(playT, before, out);
  safeTimelineCache = { sig, keys: out, loop };
  _pkCache = null;
  if (around) safeMotionNote("RRT*: " + around + " move(s) rerouted around the body. The preview and robot use these checked waypoints.", true);
  return true;
}
async function startCheckedSequence(fromMs, keepCopy = true) {
  const epoch = safeMotionEpoch, device = safeTarget(), revision = safeRevision();
  const sig = safeTimelineSignature();
  const stale = () => safeStale(epoch, device, revision) || sig !== safeTimelineSignature();
  if (!await ensureSafeTimeline(stale) || stale()) return null;
  const destination = poseAt(fromMs).slice();
  const { name, yaml } = buildYaml(fromMs);
  const part = fromMs > 0 && keyIndexAtMs(fromMs) > 0;
  const file = (part ? name + ".part" : name) + ".yaml";
  return withSafeMotion(async () => {
    if (stale()) return null;
    safeActiveDevice = safeDevice();
    const nativeYaml = part ? yaml.replace(/^loop:\s*true\s*$/m, "loop: false") : yaml;
    await sdUpload(file, nativeYaml);
    if (stale()) return null;
    const kept = keepCopy ? await keepLastRun(nativeYaml, file) : "";
    if (stale()) return null;
    const initial = await safeTakeover(stale);
    if (!initial || stale()) return null;
    if (!await checkedPoseUnlocked(destination, 0, epoch, null, initial) || stale()) return null;
    const reply = await rawCmd("MOVE " + file);
    if (stale()) {
      await safeDeviceCmd(safeActiveDevice, "STOP");
      return null;
    }
    if (!/^OK\b/.test(reply)) throw new Error(reply || "the robot did not start the sequence");
    return { file, name, part, kept };
  });
}
async function directSafePlay(fromMs) {
  const epoch = safeMotionEpoch, device = safeTarget(), revision = safeRevision(), sig = safeTimelineSignature();
  const stale = () => !playing || safeStale(epoch, device, revision) || sig !== safeTimelineSignature();
  const K = checkedTimeline().map((k) => ({ ...k, pose: k.pose.slice() }));
  const phases = [];
  let at = 0;
  const add = (key, ms, move) => {
    if (ms > 0) phases.push({ key, start: at, end: at + ms, move });
    at += ms;
  };
  add(K[0], K[0].hold || 0, false);
  K.slice(1).forEach((k) => {
    add(k, k.t, true);
    add(k, k.hold || 0, false);
  });
  const draw = (q, time) => {
    pose = q.slice();
    playT = time;
    applyPose();
    renderSliders();
    $("scrub").value = at ? Math.round(time / at * 1e3) : 0;
    $("tlTime").textContent = (time / 1e3).toFixed(1) + "s / " + (at / 1e3).toFixed(1) + "s";
  };
  const hold = async (ms, update) => {
    const start = performance.now();
    while (!stale() && performance.now() - start < ms) {
      if (update) update(performance.now() - start);
      await new Promise((r) => setTimeout(r, 40));
    }
  };
  entryHold = true;
  const music = planPace(K) === "music";
  return withSafeMotion(async () => {
    try {
      let status = await safeTakeover(stale);
      if (!status || stale()) return false;
      if (music) await rawCmd("PACE " + musicPace.cue().replace(/^pace:\s*/i, "").toUpperCase()).catch(() => "");
      if (!await checkedPoseUnlocked(poseAt(fromMs), 0, epoch, null, status, (s) => draw(s.module.joints, fromMs)) || stale()) return false;
      let cursor = fromMs;
      do {
        for (const phase of phases) {
          if (phase.end <= cursor) continue;
          if (stale()) return false;
          const start = Math.max(cursor, phase.start), duration = phase.end - start, clock = performance.now();
          if (phase.move) {
            status = await safeIdle(stale);
            if (!status || stale()) return false;
            if (!await checkedPoseUnlocked(phase.key.pose, duration, epoch, null, status, (s) => draw(s.module.joints, Math.min(phase.end, start + performance.now() - clock))) || stale()) return false;
            await hold(Math.max(0, duration - (performance.now() - clock)));
          } else await hold(duration, (elapsed) => draw(phase.key.pose, start + elapsed));
          if (stale()) return false;
          draw(phase.key.pose, phase.end);
          cursor = phase.end;
        }
        cursor = 0;
      } while ($("loopChk").checked && !stale());
      return !stale();
    } catch (e) {
      await cancelSafeMotion("direct playback failed");
      safeMotionNote("Playback stopped: " + e.message, true);
      return false;
    } finally {
      if (music) await rawCmd("PACE NORMAL").catch(() => "");
      if (epoch === safeMotionEpoch) {
        playing = false;
        entryHold = false;
        $("playBtn").textContent = "▶ Play";
        keepAwake(false);
      }
    }
  });
}
function renderSliders() {
  const box = $("sliders");
  if (!box.dataset.built) {
    box.dataset.built = 1;
    JOINT_LABELS.forEach((label, i) => {
      const row = document.createElement("div");
      row.className = "jrow";
      row.id = "jrow" + i;
      const name = document.createElement("span");
      name.className = "jname";
      name.textContent = label;
      const slider = document.createElement("input");
      slider.type = "range";
      slider.min = 0;
      slider.max = 180;
      slider.step = 0.5;
      slider.id = "js" + i;
      const num = document.createElement("input");
      num.type = "number";
      num.min = 0;
      num.max = 180;
      num.id = "jn" + i;
      slider.oninput = () => {
        pose[i] = clampJ(i, +slider.value);
        poseChanged(true);
      };
      slider.onchange = () => poseChanged(false);
      num.onchange = () => {
        pose[i] = clampJ(i, +num.value);
        poseChanged(false);
      };
      row.append(name, slider, num);
      box.appendChild(row);
    });
  }
  const sel = selPair >= 0 ? PAIRS[selPair].joints : [];
  for (let i = 0; i < NJ; i++) {
    const js = $("js" + i), jn = $("jn" + i);
    const inPair = sel.includes(i);
    if (_lastSel[i] !== inPair) {
      _lastSel[i] = inPair;
      $("jrow" + i).classList.toggle("sel", inPair);
    }
    if (_lastMin[i] !== RIG.min[i]) {
      _lastMin[i] = js.min = jn.min = RIG.min[i];
    }
    if (_lastMax[i] !== RIG.max[i]) {
      _lastMax[i] = js.max = jn.max = RIG.max[i];
    }
    const v = Math.round(pose[i] * 10) / 10;
    if (_lastVal[i] !== v) {
      _lastVal[i] = v;
      if (document.activeElement !== js) js.value = v;
      if (document.activeElement !== jn) jn.value = v;
    }
  }
}
const _lastVal = new Array(NJ).fill(NaN);
const _lastMin = new Array(NJ).fill(NaN);
const _lastMax = new Array(NJ).fill(NaN);
const _lastSel = new Array(NJ).fill(null);
function renderXyz() {
  const k = fkPoints(pose);
  const f = (p) => `(${Math.round(p.x)}, ${Math.round(p.y)}, ${Math.round(p.z)})`;
  $("jointXyz").textContent = "Left:\n  shoulder " + f(k.shL) + "\n  elbow    " + f(k.elL) + "\n  wrist    " + f(k.wrL) + "\nRight:\n  shoulder " + f(k.shR) + "\n  elbow    " + f(k.elR) + "\n  wrist    " + f(k.wrR);
  [["L", k.wrL], ["R", k.wrR]].forEach(([s, p]) => {
    ["x", "y", "z"].forEach((ax) => {
      const el = $("tgt" + s + ax);
      if (el && document.activeElement !== el) el.value = Math.round(p[ax]);
    });
  });
}
function gotoXyz(arm) {
  const s = arm === 0 ? "L" : "R";
  const t = new THREE.Vector3(
    +$("tgt" + s + "x").value || 0,
    +$("tgt" + s + "y").value || 0,
    +$("tgt" + s + "z").value || 0
  );
  const wrKey = arm === 0 ? "wrL" : "wrR";
  let best = [...pose], bestErr = Infinity;
  const tryWalk = () => {
    const start = fkPoints(pose)[wrKey];
    const steps = Math.min(60, Math.max(6, Math.ceil(start.distanceTo(t) / 12)));
    for (let i = 1; i <= steps; i++)
      solveIK(arm, start.clone().lerp(t, i / steps), 6);
    solveIK(arm, t, 25);
    const err2 = fkPoints(pose)[wrKey].distanceTo(t);
    if (err2 < bestErr) {
      bestErr = err2;
      best = [...pose];
    }
    return err2;
  };
  if (tryWalk() > 10) {
    const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    idx.forEach((j) => pose[j] = RIG.neutral[j]);
    tryWalk();
  }
  pose = best;
  holdSide(arm, true);
  const got = fkPoints(pose)[wrKey];
  askReach(arm, wristPos(arm).add(t.clone().sub(got)));
  poseChanged(false);
  const err = Math.round(got.distanceTo(t));
  $("tlStat").textContent = (arm === 0 ? "left" : "right") + ` wrist moved to (${Math.round(got.x)}, ${Math.round(got.y)}, ${Math.round(got.z)})` + (err > 10 ? ` — target is ${err} mm out of reach, this is the closest pose` : " ✓");
}
let liveTimer = 0, colTimer = 0;
function poseChanged(throttled, liveMs, opts = {}) {
  applyPose();
  renderSliders();
  const now = performance.now();
  if (!throttled || now - colTimer > 150) {
    colTimer = now;
    $("collideWarn").style.display = collisionAt(pose) ? "block" : "none";
    renderXyz();
    renderHands();
  }
  if ($("liveChk").checked && !opts.previewOnly) {
    if (liveMs > 0) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + Math.round(liveMs));
    else sendPoseLive();
  }
}
function setNeutral() {
  pose = [...RIG.neutral];
  poseChanged(false);
}
function neutralFromPose() {
  RIG.neutral = [...pose];
  saveRig();
  $("tlStat").textContent = "show neutral = " + RIG.neutral.map(Math.round).join(" ") + " — kept in Studio. The robot's start position is set with Keep this as robot home.";
}
async function homeFromPose() {
  RIG.home = [...pose];
  saveRig();
  renderRigUI();
  const shown = RIG.home.map(Math.round).join(" ");
  if (!haveRobot()) {
    $("robotStat").textContent = "robot home = " + shown + " — saved here. Connect the robot and press Send rig to give it these.";
    return;
  }
  try {
    const r = await rawCmd("NEUTRAL " + RIG.home.map(fmtA).join(" "));
    $("robotStat").textContent = /^ERR/i.test(r || "") ? "the robot did not take the home pose: " + r : "robot home = " + shown + " — the robot will start here from now on. Press Home to move there.";
  } catch (e) {
    $("robotStat").textContent = "home saved here, but it did not reach the robot: " + Mice.Words.plain(e).says;
  }
}
function mirrorFB() {
  mirrorLR("fb");
}
function mirrorLR(which) {
  const m = mirrorPose(pose, which);
  if (!m) {
    $("tlStat").textContent = "the robot is not on screen yet, so there is nothing to mirror. Nothing was changed.";
    return;
  }
  pose = m;
  poseChanged(false);
  $("tlStat").textContent = which === "fb" ? "mirrored front to back — each arm reaches the other way, on its own side" : "mirrored left to right — each arm took the other's shape";
}
const FACING_TEXT = {
  palm: "palm on top",
  back: "back of the hand on top",
  side: "on its edge"
};
function renderHands() {
  const box = $("handsBox");
  if (!box || palmMarks.length < HANDS.length) return;
  if (!box.childElementCount) {
    HANDS.forEach((h, i) => {
      const row = document.createElement("div");
      row.className = "row";
      const lbl = document.createElement("span");
      lbl.className = "lbl";
      lbl.textContent = h.label;
      const up = document.createElement("button");
      up.textContent = "✋ Palm up";
      up.title = "turn the arm so the PALM of the " + h.label.toLowerCase() + " faces up; the hand stays where it is";
      up.onclick = () => turnPalm(i, 1);
      const back = document.createElement("button");
      back.textContent = "🤚 Back up";
      back.title = "turn the arm so the BACK of the " + h.label.toLowerCase() + " faces up; the hand stays where it is";
      back.onclick = () => turnPalm(i, -1);
      const now = document.createElement("span");
      now.className = "mini";
      now.id = "handNow" + i;
      row.append(lbl, up, back, now);
      const keep = document.createElement("div");
      keep.className = "row";
      const kl = document.createElement("span");
      kl.className = "mini";
      kl.textContent = "while moving it, keep:";
      const sel = document.createElement("select");
      sel.id = "handHold" + i;
      [["0", "nothing — free"], ["1", "✋ palm on top"], ["-1", "🤚 back on top"]].forEach(([v, t]) => sel.add(new Option(t, v)));
      sel.title = "dragging this hand or typing where its wrist goes keeps that side on top as well as it can; the sliders always do exactly what you set";
      sel.onchange = () => setHold(i, +sel.value);
      keep.append(kl, sel);
      const reach = document.createElement("div");
      reach.className = "mini";
      reach.id = "handReach" + i;
      box.append(row, keep, reach);
    });
    const save = document.createElement("div");
    save.className = "row";
    const add = document.createElement("button");
    add.textContent = "＋ Save as a new move";
    add.id = "handSaveNew";
    add.onclick = () => saveShownPose(true);
    const into = document.createElement("button");
    into.textContent = "Save into the selected move";
    into.id = "handSaveInto";
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
  $("tlStat").textContent = want * r.upness > 0.5 ? h + ": " + (want > 0 ? "the palm" : "the back of the hand") + " is on top now, and the hand is where it was. Press Update selected to keep it in the move." : h + ": this is as far round as the joints let it turn with the hand here. Move the hand a little and try again.";
  if (want * r.upness <= 0.5) notice($("tlStat").textContent);
}
let HOLD = {
  dragRangeDeg: 30,
  // while dragging: look this far round each way, no further
  stepDeg: 5,
  reachMm: 4,
  // a gap this small counts as "the hand got there"
  stopDeg: 0.5,
  // this close to a joint limit counts as "at its stop"
  avoidSelfHit: true
  // never turn the arm into a shape that hits the body
};
fetch("hand_side.json").then((r) => r.json()).then((j) => {
  Object.keys(HOLD).forEach((k) => {
    if (k in j) HOLD[k] = j[k];
  });
}).catch(() => {
});
const handHold = HANDS.map(() => 0);
const reachAsk = HANDS.map(() => null);
const reachMarks = [];
const armJoints = (arm) => arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
const armKey = (arm) => armJoints(arm).map((j) => pose[j].toFixed(2)).join(",");
function holdSide(arm, full) {
  const want = handHold[arm];
  if (!want) return;
  const r = facePalm(pose, arm, want, full ? { safe: HOLD.avoidSelfHit } : { range: HOLD.dragRangeDeg, step: HOLD.stepDeg, safe: HOLD.avoidSelfHit });
  if (r) {
    pose = r.pose;
    applyPose();
  }
}
function askReach(arm, target) {
  reachAsk[arm] = { target: target.clone(), joints: armKey(arm) };
  drawReach(arm);
}
function drawReach(arm) {
  if (!reachMarks[arm]) {
    const ball = new THREE.Mesh(
      new THREE.SphereGeometry(14, 16, 12),
      new THREE.MeshBasicMaterial({ color: 16752412, transparent: true, opacity: 0.55 })
    );
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(
        [new THREE.Vector3(), new THREE.Vector3()]
      ),
      new THREE.LineBasicMaterial({ color: 16752412 })
    );
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
function reachGap(arm) {
  const a = reachAsk[arm];
  if (!a || !wristBalls[arm]) return null;
  if (a.joints !== armKey(arm)) {
    reachAsk[arm] = null;
    return null;
  }
  robot.updateMatrixWorld(true);
  return a.target.distanceTo(wristPos(arm));
}
function sideText(arm) {
  const up = palmUpness(arm), want = handHold[arm] || (up >= 0 ? 1 : -1);
  const off = Math.round(THREE.MathUtils.radToDeg(Math.acos(Math.max(-1, Math.min(1, want * up)))));
  return (want > 0 ? "palm " : "back ") + off + "° from straight up";
}
function reachText(arm) {
  const out = [];
  const gap = reachGap(arm);
  if (gap !== null) out.push(gap <= HOLD.reachMm ? "reached where you put it" : Math.round(gap) + " mm short of where you put it (the orange mark)");
  if (handHold[arm] && handHold[arm] * palmUpness(arm) <= 0.5)
    out.push("the joints cannot turn it further with the hand here");
  const stops = armJoints(arm).filter((j) => pose[j] <= RIG.min[j] + HOLD.stopDeg || pose[j] >= RIG.max[j] - HOLD.stopDeg);
  if (stops.length) out.push("at its stop: " + stops.map((j) => JOINT_LABELS[j]).join(", "));
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
function saveShownPose(asNew) {
  if (asNew) addKey();
  else if (keys[selKey]) updateKey();
  else return;
  $("tlStat").textContent = (asNew ? "added as move " : "saved into move ") + selKey + " — exactly the pose shown, which is what the arm will do";
}
function speedDps() {
  return Math.max(5, +$("speedDps").value || 120);
}
function maxDps() {
  return Math.max(30, +$("maxDps").value || 400);
}
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
function planPace(K = keys) {
  if (PACE_OVERRIDE) return PACE_OVERRIDE;
  return K.some((k) => keyCue(k, "play") || /^music\b/i.test(keyCue(k, "pace") || "")) ? "music" : "normal";
}
function paceCapDps(pace = planPace()) {
  return pace === "music" ? musicPace.cap() : SAFE_DPS;
}
function minTimeWhy(from, to, atPace) {
  let servo = 0, slowest = 0;
  for (let i = 0; i < NJ; i++) {
    const need2 = Math.abs(to[i] - from[i]) / jointMaxDps(i);
    if (need2 > servo) {
      servo = need2;
      slowest = i;
    }
  }
  const pace = atPace || planPace(), cap = paceCapDps(pace);
  const peak = cap > 0 ? deltaDeg(from, to) * (Math.PI / 2) / Math.max(1, cap) : 0;
  const need = Math.max(servo, peak);
  const ms = Math.max(MIN_MOVE_MS, Math.ceil(need * 1e3));
  let why = "the 80 ms shortest-move floor", fix = "";
  if (need * 1e3 > MIN_MOVE_MS) {
    if (peak >= servo) {
      why = pace === "music" ? `the speed limit with music, ${cap} °/s` : `the robot's peak speed limit, ${SAFE_DPS} °/s`;
      fix = pace === "music" ? "Raise Speed limit with music (Timing), or 0 for the servos' top speed." : `Above about ${flatDps()} °/s nothing gets faster. Raise Peak speed limit (Timing) to shorten it.`;
    } else {
      why = `${JOINT_LABELS[slowest] || "joint " + (slowest + 1)} at its servo max, ${Math.round(jointMaxDps(slowest))} °/s`;
      fix = "Raise Servo max, or that joint's servo °/s in Setup > rig.";
    }
  }
  return { ms, why, fix };
}
function minTime(from, to, atPace) {
  return minTimeWhy(from, to, atPace).ms;
}
function flatDps() {
  return Math.floor(SAFE_DPS * 2 / Math.PI);
}
function keyDps(i) {
  const k = keys[i];
  return k && k.dps ? Math.min(k.dps, slowestDps()) : speedDps();
}
function autoTime(from, to, dps) {
  const v = dps || speedDps();
  const t = Math.max(MIN_MOVE_MS, Math.round(deltaDeg(from, to) / v * 1e3));
  return Math.max(t, minTime(from, to));
}
function keyMin(i) {
  return i > 0 && keys[i - 1] ? minTime(keys[i - 1].pose, keys[i].pose) : MIN_MOVE_MS;
}
function speedCeiling() {
  return Math.max(5, Math.min(slowestDps(), flatDps()));
}
function speedChanged() {
  const asked = speedDps();
  let said = "";
  if (asked > speedCeiling()) {
    const cap = speedCeiling();
    $("speedDps").value = cap;
    said = flatDps() <= slowestDps() ? `Show speed kept at ${cap} °/s — above that, the robot's peak speed limit of ${SAFE_DPS} °/s decides every move and nothing gets faster. Raise Peak speed limit and Save to robot to go quicker.` : `Show speed kept at ${cap} °/s — the slowest servo on this robot cannot go faster. Raise Servo max to allow more.`;
  }
  recalcTimes();
  renderTimeline();
  $("tlStat").textContent = said || timingSummary();
}
function timingSummary() {
  let peak = 0, servo = 0, free = 0;
  for (let i = 1; i < keys.length; i++) {
    if (!keys[i - 1]) continue;
    const w = minTimeWhy(keys[i - 1].pose, keys[i].pose);
    const auto = Math.max(
      MIN_MOVE_MS,
      Math.round(deltaDeg(keys[i - 1].pose, keys[i].pose) / keyDps(i) * 1e3)
    );
    if (auto >= w.ms) free++;
    else if (w.why.indexOf("peak") >= 0) peak++;
    else servo++;
  }
  if (!peak && !servo) return `every move runs at the speed you set (${speedDps()} °/s)`;
  const bits = [];
  if (peak) bits.push(`${peak} held by the robot's peak speed limit (${SAFE_DPS} °/s — above about ${flatDps()} °/s nothing gets faster)`);
  if (servo) bits.push(`${servo} held by a servo's own top speed`);
  return `${free} move(s) run at your speed; ` + bits.join(", ") + ". Change Peak speed limit or Servo max in Timing to shorten them.";
}
function safetyLimitChanged() {
  const want = Math.round(+$("safeDpsInput").value || 0);
  if (!(want >= 5)) {
    $("safeDpsInput").value = SAFE_DPS;
    return;
  }
  const wasAuto = keys.map((k, i) => i > 0 && keys[i - 1] && !timePinned(i) && k.t === autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  SAFE_DPS = want;
  if (speedDps() > speedCeiling()) $("speedDps").value = speedCeiling();
  for (let i = 1; i < keys.length; i++)
    if (wasAuto[i]) keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  bumpKeys();
  clampKeyTimes();
  renderTimeline();
  $("safeSpeedStat").textContent = `Planning at ${want} °/s, so Show speed can now go up to ${speedCeiling()} °/s. ` + (boardSafeDpsMax ? "Press Save to robot to make the robot use it too — it takes effect after the board restarts." : "Not saved to any robot — connect first, then Save to robot.");
}
function adoptBoardSafety(module) {
  const safe = Number(module && module.safe_dps);
  const speeds = module && module.max_dps;
  const max = Array.isArray(speeds) && speeds.length === NJ ? Math.min(...speeds.map(Number)) : 0;
  const input = $("safeDpsInput"), button = $("saveSafeDps");
  if (!(safe >= 5) || !(max >= 5) || !Number.isFinite(max)) {
    boardSafeDpsMax = 0;
    boardSafePeer = 0;
    input.disabled = false;
    button.disabled = true;
    $("safeSpeedStat").textContent = `This board does not report its safety speed, so nothing was changed on it. Studio still plans at ${SAFE_DPS} °/s — change it here to make the editor's times shorter.`;
    return;
  }
  const wasAuto = keys.map((k, i) => i > 0 && !timePinned(i) && k.t === autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  const music = Number(module.music_dps);
  const changed = safe !== SAFE_DPS || Number.isFinite(music) && music !== MUSIC_DPS;
  SAFE_DPS = safe;
  if (Number.isFinite(music) && music >= 0) MUSIC_DPS = music;
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
  $("safeSpeedStat").textContent = `Active peak limit: ${safe} °/s. For safety-limited moves, Show speed above about ${flatDps()} °/s will not shorten them — raise this number and press Save to robot to go faster.` + (boardSafePeer ? ` Linked board #${boardSafePeer} needs the same limit.` : "");
}
function timePinned(i) {
  return !!(keys[i] && keys[i].tset);
}
function pinTime(i) {
  if (keys[i]) keys[i].tset = true;
}
function unpinTime(i) {
  if (keys[i]) delete keys[i].tset;
}
function recalcTimes() {
  bumpKeys();
  for (let i = 1; i < keys.length; i++)
    if (!timePinned(i))
      keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();
}
function retimeAt(i) {
  bumpKeys();
  if (i >= 1 && keys[i] && !timePinned(i))
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();
}
function clampKeyTimes() {
  bumpKeys();
  for (let i = 0; i < keys.length; i++) keys[i].t = Math.max(keys[i].t, keyMin(i));
}
const musicPace = {
  // the cap a list K follows its music at
  cap(K = keys) {
    const own = this.own(K);
    return own != null ? own : MUSIC_DPS;
  },
  // the sequence's own number: the box, else a file's `pace: music N`; null = the robot's
  own(K = keys) {
    if (SEQ_MUSIC_DPS != null) return SEQ_MUSIC_DPS;
    for (const k of K) {
      const m = /^music\s+(\d+(?:\.\d+)?)/i.exec(keyCue(k, "pace") || "");
      if (m) return +m[1];
    }
    return null;
  },
  cue(K = keys) {
    const own = this.own(K);
    return "pace: music" + (own != null ? " " + own : "");
  },
  // the value in the box, then every pace cue and every music-timed move follow it
  changed() {
    const raw = ($("musicDpsSeq").value || "").trim(), v = Math.round(+raw);
    SEQ_MUSIC_DPS = raw === "" || !(v >= 0) ? null : v > 0 && v < 5 ? 5 : Math.min(v, Math.round(slowestDps()));
    $("musicDpsSeq").value = SEQ_MUSIC_DPS == null ? "" : SEQ_MUSIC_DPS;
    keys.forEach((k) => {
      if (k.cues) k.cues = k.cues.map((c) => /^pace:\s*music/i.test(c) ? this.cue() : c);
    });
    this.retime();
    renderTimeline();
  },
  // A move timed by the song gets back the song's time when the cap allows
  // it, and only as much more as the servos need when it does not.
  retime() {
    bumpKeys();
    keys.forEach((k, i) => {
      if (k.musicMs > 0) {
        delete k.servoMs;
        k.t = Math.max(k.musicMs, keyMin(i));
      }
    });
    if (planPace() === "music") ServoFollow.settle(keys.filter((k) => !k.off));
  },
  // the moves that cannot keep up at this cap: [{i, behindMs, why}]
  late() {
    if (planPace() !== "music") return [];
    const out = [];
    keys.forEach((k, i) => {
      if (k.off || !(i > 0)) return;
      const want = k.musicMs > 0 ? k.musicMs : null;
      if (want == null) return;
      const w = minTimeWhy(keys[i - 1].pose, k.pose);
      if (k.servoMs > Math.max(want, w.ms) + 10)
        out.push({ i, behindMs: k.servoMs - want, why: "the real servos: at full speed the hands would touch" });
      else if (w.ms > want + 10) out.push({ i, behindMs: w.ms - want, why: w.why });
    });
    return out;
  },
  render() {
    const row = $("musicPaceRow");
    if (!row) return;
    const music = planPace() === "music";
    row.hidden = !music;
    $("musicFitStat").hidden = !music;
    const list = $("musicFitList");
    list.innerHTML = "";
    if (!music) return;
    if (document.activeElement !== $("musicDpsSeq"))
      $("musicDpsSeq").value = SEQ_MUSIC_DPS == null ? "" : SEQ_MUSIC_DPS;
    $("musicDpsSeq").placeholder = MUSIC_DPS > 0 ? String(MUSIC_DPS) : "robot";
    const cap = this.cap(), late = this.late();
    const at = cap > 0 ? `${cap} °/s` : "the servos' top speed";
    if (!late.length) {
      $("musicFitStat").textContent = `Every move keeps up with the song at ${at}.`;
      return;
    }
    const behind = late.reduce((s, x) => s + x.behindMs, 0);
    $("musicFitStat").textContent = `${late.length} move(s) fall behind the song at ${at}; the show ends ${(behind / 1e3).toFixed(1)} s after the music. Raise the limit, or click a move to shorten, change or remove it.`;
    late.slice(0, 40).forEach((x) => {
      const b = document.createElement("button");
      b.className = "secondary mini";
      b.textContent = `${keys[x.i].name || "move " + x.i} +${(x.behindMs / 1e3).toFixed(2)} s`;
      b.title = "held back by " + x.why;
      b.onclick = () => selectKey(x.i);
      list.appendChild(b);
    });
  }
};
let SERVO_VIEW = { frameMs: 20, warnDeg: 8, badDeg: 20 };
fetch("servo_follow.json").then((r) => r.json()).then((j) => {
  for (const k of Object.keys(SERVO_VIEW)) if (Number.isFinite(j[k]) && j[k] > 0) SERVO_VIEW[k] = j[k];
}).catch(() => {
});
class ServoFollow {
  constructor(start) {
    this.reset(start);
  }
  reset(start) {
    this.pos = [...start];
    this.aim = [...start];
    this.vel = new Array(NJ).fill(0);
  }
  // one step of dt ms toward target; returns where the horns are
  step(target, dt) {
    const s = dt / 1e3;
    for (let j = 0; j < NJ; j++) {
      const lag = Math.max(0.1, +RIG.servoLagMs[j] || 0) / 1e3;
      this.aim[j] += (target[j] - this.aim[j]) * (1 - Math.exp(-s / lag));
      const top = jointMaxDps(j), acc = Math.max(1, +RIG.servoAccel[j] || 1);
      const err = this.aim[j] - this.pos[j];
      const want = Math.sign(err) * Math.min(top, Math.sqrt(2 * acc * Math.abs(err)), Math.abs(err) / s);
      const dv = Math.max(-acc * s, Math.min(acc * s, want - this.vel[j]));
      this.vel[j] += dv;
      this.pos[j] += this.vel[j] * s;
    }
    return this.pos;
  }
  // The whole list K played at the board's frame: for every move, how far the
  // horns trailed the timeline at worst, and on which joint.
  // opts.hits: also check the HORNS' pose for touching (every other frame,
  // ~0.3 ms a check): the plan can be clear while the lagging arm is not.
  static trace(K, opts = {}) {
    if (!K.length) return { moves: [], worst: null };
    const f = new ServoFollow(K[0].pose), dt = SERVO_VIEW.frameMs;
    const end = easeKeys(K, Infinity).end || 0, starts = [];
    let t = K[0].hold || 0;
    for (let i = 1; i < K.length; i++) {
      starts.push(t);
      t += K[i].t + (K[i].hold || 0);
    }
    const moves = K.map(() => ({ deg: 0, joint: -1 }));
    let worst = null, m = 0;
    for (let ms = 0; ms <= end + 500; ms += dt) {
      while (m < starts.length - 1 && ms >= starts[m + 1]) m++;
      const want = easeKeys(K, ms).pose, got = f.step(want, dt);
      for (let j = 0; j < NJ; j++) {
        const e = Math.abs(want[j] - got[j]), mv2 = moves[Math.min(m + 1, K.length - 1)];
        if (e > mv2.deg) {
          mv2.deg = e;
          mv2.joint = j;
        }
        if (!worst || e > worst.deg) worst = { deg: e, joint: j, move: m + 1, ms };
      }
      const mv = moves[Math.min(m + 1, K.length - 1)];
      if (opts.hits && !mv.hitMs && ms / dt % 2 === 0 && collisionAt(got)) mv.hitMs = ms;
    }
    return { moves, worst };
  }
  // A show that follows its song may move faster than the real arm can follow
  // without its hands meeting (nong_sim found 0-4 touches per cheer dance,
  // 2026-10-27). Lengthen each move where the HORNS touch, a little at a
  // time, until none does; k.servoMs keeps that floor so later re-timing
  // (music_pace.js) honours it. Returns how many moves it lengthened.
  static settle(K, tries = 6) {
    const longer = /* @__PURE__ */ new Set();
    for (let n = 0; n < tries; n++) {
      const hit = ServoFollow.trace(K, { hits: true }).moves.map((mv, i) => mv.hitMs ? i : -1).filter((i) => i > 0);
      if (!hit.length) break;
      for (const i of hit) {
        K[i].t = Math.round(K[i].t * 1.3);
        K[i].servoMs = K[i].t;
        longer.add(i);
      }
    }
    return longer.size;
  }
}
const servoLag = {
  sig: "",
  res: null,
  of() {
    const sig = keysSignature() + "|" + RIG.servoLagMs + "|" + RIG.servoAccel + "|" + RIG.servoMaxDps + "|" + maxDps();
    if (sig !== this.sig) {
      this.sig = sig;
      this.res = ServoFollow.trace(playKeys());
    }
    return this.res;
  },
  // for bar chip i: {deg, joint, level: "" | "warn" | "bad"}; a suspended
  // chip is not played, so the played list counts only the others
  forKey(i) {
    if (!keys[i] || keys[i].off) return null;
    let p = 0;
    for (let n = 0; n < i; n++) if (!keys[n].off) p++;
    const mv = this.of().moves[p];
    if (!p || !mv) return null;
    const level = mv.deg >= SERVO_VIEW.badDeg ? "bad" : mv.deg >= SERVO_VIEW.warnDeg ? "warn" : "";
    return { ...mv, level };
  },
  summary() {
    const w = this.of().worst;
    if (!w || w.deg < SERVO_VIEW.warnDeg) return "The real servos keep up with every move.";
    return `The real servos fall up to ${Math.round(w.deg)}° behind (${JOINT_LABELS[w.joint] || "joint " + (w.joint + 1)}, move ${w.move}). Marked moves on the bar; slow them or tick “Play like the real servos” to watch it.`;
  }
};
let servoPlay = null;
function servoPlayPose(target, dt) {
  if (!$("servoView") || !$("servoView").checked) {
    servoPlay = null;
    return target;
  }
  if (!servoPlay) servoPlay = new ServoFollow(target);
  return [...servoPlay.step(target, dt)];
}
let SMOOTH = { on: false, sources: {} };
fetch("motion_smooth.json").then((r) => r.json()).then((j) => {
  SMOOTH = j;
  motionSmooth.forget();
}).catch(() => {
});
class MotionSmooth {
  // the curve of one joint, s 0..1 of a move T seconds long: cosine rest to
  // rest (as before), else a Hermite through the two pass speeds (deg/s)
  static curve(q0, q1, v0, v1, T, s) {
    s = s <= 0 ? 0 : s >= 1 ? 1 : s;
    if (v0 === 0 && v1 === 0) return q0 + (q1 - q0) * (0.5 - 0.5 * Math.cos(Math.PI * s));
    const s2 = s * s, s3 = s2 * s;
    return q0 + (q1 - q0) * (3 * s2 - 2 * s3) + T * (v0 * (s3 - 2 * s2 + s) + v1 * (s3 - s2));
  }
  // [speed deg/s, speed-up deg/s2] at s
  static curveD(q0, q1, v0, v1, T, s) {
    const d = q1 - q0;
    if (v0 === 0 && v1 === 0)
      return [d * Math.PI / 2 * Math.sin(Math.PI * s) / T, d * Math.PI * Math.PI / 2 * Math.cos(Math.PI * s) / (T * T)];
    return [
      d * (6 * s - 6 * s * s) / T + v0 * (3 * s * s - 4 * s + 1) + v1 * (3 * s * s - 2 * s),
      (d * (6 - 12 * s) / T + v0 * (6 * s - 4) + v1 * (6 * s - 2)) / T
    ];
  }
  // PASS for the move INTO key i: start speeds then end speeds (2 x joints),
  // null when it rests at both ends. The board plays the curve only when the
  // arm really moves at the start speeds, else the old cosine from rest.
  static passFor(V, i) {
    if (!V || i <= 0 || !(V[i - 1].some((v) => v) || V[i].some((v) => v))) return null;
    return [...V[i - 1], ...V[i]];
  }
  static pose(a, b, va, vb, ms, s) {
    return a.map((q, j) => MotionSmooth.curve(q, b[j], va[j], vb[j], ms / 1e3, s));
  }
  // opts: cfg (motion_smooth.json), maxDps[] and acc[] per joint (the rig),
  // cap (a peak speed cap in force, 0 = none), touches(pose) -> truthy,
  // rest(key) -> true where the arm must stop anyway
  constructor(opts) {
    this.cfg = opts.cfg || {};
    this.maxDps = opts.maxDps || [];
    this.acc = opts.acc || [];
    this.cap = +opts.cap || 0;
    this.touches = opts.touches || null;
    this.rest = opts.rest || null;
    this.memo = opts.memo || null;
    this.off = +(this.touches ? this.cfg.maxOffLineDeg : this.cfg.uncheckedOffLineDeg) || 1;
  }
  num(k, d) {
    const v = this.cfg[k];
    return Number.isFinite(+v) && v !== null && v !== "" ? +v : d;
  }
  top(j) {
    let t = +this.maxDps[j] || 400;
    if (this.cap > 0) t = Math.min(t, this.cap);
    return t;
  }
  vmax(j) {
    return this.top(j) * this.num("velScale", 0.85);
  }
  amax(j) {
    const a = +this.acc[j] || 0;
    return a > 0 ? a * this.num("accScale", 1) : Infinity;
  }
  // monotone tangents (Fritsch-Carlson, uneven spacing); 0 where a joint
  // turns back, holds, stands still and at both ends
  firstGuess(K) {
    const n = K.length, nj = K[0].pose.length, floor = this.num("minViaDps", 2);
    const V = K.map(() => new Array(nj).fill(0));
    for (let i = 1; i < n - 1; i++) {
      if ((K[i].hold || 0) > 0 || this.rest && this.rest(K[i])) continue;
      const h0 = K[i].t / 1e3, h1 = K[i + 1].t / 1e3;
      if (!(h0 > 0) || !(h1 > 0)) continue;
      for (let j = 0; j < nj; j++) {
        const d0 = (K[i].pose[j] - K[i - 1].pose[j]) / h0, d1 = (K[i + 1].pose[j] - K[i].pose[j]) / h1;
        if (d0 * d1 <= 0) continue;
        const w1 = 2 * h1 + h0, w2 = h1 + 2 * h0;
        let v = (w1 + w2) / (w1 / d0 + w2 / d1);
        v = Math.sign(v) * Math.min(Math.abs(v), this.vmax(j));
        V[i][j] = Math.abs(v) >= floor ? v : 0;
      }
    }
    return V;
  }
  // the board lengthens a move under its floor and plays it rest to rest
  tooShort(a, b, T) {
    if (T * 1e3 < this.num("minMoveMs", 80)) return true;
    let big = 0;
    for (let j = 0; j < a.length; j++) {
      if (Math.abs(b[j] - a[j]) / (+this.maxDps[j] || 400) > T) return true;
      big = Math.max(big, Math.abs(b[j] - a[j]));
    }
    return this.cap > 0 && big * Math.PI / 2 / this.cap > T;
  }
  // past a key, off the line, over the servo speed, or more speed-up than allowed?
  bad(a, b, va, vb, T) {
    const nj = a.length, ns = this.num("samples", 24), u = b.map((x, j) => x - a[j]);
    const uu = u.reduce((s, x) => s + x * x, 0);
    for (let k = 1; k < ns; k++) {
      const s = k / ns, p = new Array(nj);
      for (let j = 0; j < nj; j++) {
        p[j] = MotionSmooth.curve(a[j], b[j], va[j], vb[j], T, s);
        if (p[j] < Math.min(a[j], b[j]) - 1e-6 || p[j] > Math.max(a[j], b[j]) + 1e-6) return true;
        const [vel, acc] = MotionSmooth.curveD(a[j], b[j], va[j], vb[j], T, s);
        if (Math.abs(vel) > this.top(j) + 1e-6 && (va[j] || vb[j])) return true;
        const plain = 4.935 * Math.abs(b[j] - a[j]) / (T * T);
        if (Math.abs(acc) > Math.max(this.amax(j), plain) + 1e-6) return true;
      }
      if (uu > 0) {
        let w = 0;
        for (let j = 0; j < nj; j++) w += (p[j] - a[j]) * u[j];
        w = Math.min(1, Math.max(0, w / uu));
        let dist = 0;
        for (let j = 0; j < nj; j++) dist += (p[j] - a[j] - w * u[j]) ** 2;
        if (Math.sqrt(dist) > this.off) return true;
      }
    }
    return false;
  }
  // collision check on the smoothed path, as finely as Studio's straight
  // checks (SAFE.checkDeg), never coarser than `samples`
  touching(a, b, va, vb, T) {
    const key = this.memo && a.join() + "|" + b.join() + "|" + va.join() + "|" + vb.join() + "|" + T;
    if (key && this.memo.has(key)) return this.memo.get(key);
    const hit = this.touchingNow(a, b, va, vb, T);
    if (key) {
      if (this.memo.size > 2e4) this.memo.clear();
      this.memo.set(key, hit);
    }
    return hit;
  }
  touchingNow(a, b, va, vb, T) {
    let big = 0;
    for (let j = 0; j < a.length; j++) big = Math.max(big, Math.abs(b[j] - a[j]));
    const step = Math.max(0.05, Math.min(1, +this.cfg.checkDeg || 1));
    const ns = Math.max(this.num("samples", 24), Math.ceil(big / step));
    for (let k = 1; k < ns; k++)
      if (this.touches(MotionSmooth.pose(a, b, va, vb, T * 1e3, k / ns))) return true;
    return false;
  }
  // per keyframe, per joint: the speed (deg/s) the arm passes it with
  vias(K) {
    if (!K.length) return [];
    if (K.length < 3) return K.map((k) => new Array(k.pose.length).fill(0));
    const V = this.firstGuess(K), shrink = this.num("shrink", 0.5), tries = this.num("tries", 6);
    const used = new Array(K.length).fill(0), any = (r) => r.some((v) => v !== 0);
    let changed = true;
    while (changed) {
      changed = false;
      for (let i = 1; i < K.length; i++) {
        if (!any(V[i - 1]) && !any(V[i])) continue;
        const T = K[i].t / 1e3, a = K[i - 1].pose, b = K[i].pose;
        if (T > 0 && this.tooShort(a, b, T)) used[i] = tries;
        else if (T > 0 && !this.bad(a, b, V[i - 1], V[i], T)) {
          if (!(this.touches && this.touching(a, b, V[i - 1], V[i], T))) continue;
          used[i] = tries;
        }
        used[i]++;
        const f = T > 0 && used[i] < tries ? shrink : 0;
        V[i - 1] = V[i - 1].map((v) => v * f);
        V[i] = V[i].map((v) => v * f);
        changed = true;
      }
    }
    if (this.cfg.jerkGuard !== false) this.guard(K, V, shrink, tries);
    return V.map((r) => r.map((v) => Math.round(v * 10) / 10 || 0));
  }
  // Never rougher than the plain cosine on the same keys (motion_smooth.py
  // _guard, 2026-10-30: a cubic's speed-up jumps at every key). Per key, the
  // jerk over the two moves it joins vs the cosine's; then the whole dance.
  guard(K, V, shrink, tries) {
    const frame = this.num("jerkFrameMs", 20), base = MotionSmooth.moveJerk(K, null, frame);
    const used = new Array(K.length).fill(0), worse = (a, b) => a > b * (1 + 1e-9) + 1e-9;
    let changed = true;
    while (changed) {
      changed = false;
      const got = MotionSmooth.moveJerk(K, V, frame);
      for (let i = 1; i < K.length - 1; i++) {
        if (!V[i].some((v) => v !== 0) || !worse(got[i] + got[i + 1], base[i] + base[i + 1])) continue;
        used[i]++;
        const f = used[i] < tries ? shrink : 0;
        V[i] = V[i].map((v) => v * f);
        changed = true;
      }
    }
    const sum = (a) => a.reduce((x, y) => x + y, 0);
    for (let k = 0; k <= tries; k++) {
      if (!worse(sum(MotionSmooth.moveJerk(K, V, frame)), sum(base))) return;
      const f = k < tries ? shrink : 0;
      for (let i = 0; i < V.length; i++) V[i] = V[i].map((v) => v * f);
    }
  }
  // Per move (index of the key it goes into): sum of squared jerk of every
  // joint at the frames of that move and the hold after it. V null = cosine.
  static moveJerk(K, V, frameMs) {
    const n = K.length, starts = new Array(n).fill(0);
    let t = +K[0].hold || 0;
    for (let i2 = 1; i2 < n; i2++) {
      starts[i2] = t;
      t += +K[i2].t + (+K[i2].hold || 0);
    }
    const out = new Array(n).fill(0), P = [], nj = K[0].pose.length;
    let i = 1;
    for (let k = 0; k < Math.floor(t / frameMs) + 2; k++) {
      const ms = k * frameMs;
      while (i + 1 < n && ms >= starts[i + 1]) i++;
      const seg = +K[i].t, s = seg > 0 ? (ms - starts[i]) / seg : 1;
      let p;
      if (s < 0) p = K[0].pose;
      else if (s >= 1) p = K[i].pose;
      else if (!V) {
        const e = 0.5 - 0.5 * Math.cos(Math.PI * s);
        p = K[i - 1].pose.map((x, j) => x + (K[i].pose[j] - x) * e);
      } else p = MotionSmooth.pose(K[i - 1].pose, K[i].pose, V[i - 1], V[i], seg, s);
      P.push(p);
      if (k < 3) continue;
      const a = P[k], b = P[k - 1], c = P[k - 2], d = P[k - 3];
      for (let j = 0; j < nj; j++) out[i] += (a[j] - 3 * b[j] + 3 * c[j] - d[j]) ** 2;
    }
    return out;
  }
}
const motionSmooth = {
  cache: /* @__PURE__ */ new WeakMap(),
  // collision answers per curved move: checking a 485-key dance's curves
  // took 2-7 s (2026-10-29, headless); after an edit only the moves next to
  // it are checked again. Forgotten when the rig, the gap or the pace changes.
  memo: /* @__PURE__ */ new Map(),
  memoSig: "",
  on(source) {
    return !!SMOOTH.on && (SMOOTH.sources || {})[source] !== false;
  },
  forget() {
    this.cache = /* @__PURE__ */ new WeakMap();
    this.memo = /* @__PURE__ */ new Map();
  },
  sig(K) {
    let s = K.length;
    for (const k of K) {
      s = s * 31 + (+k.t || 0) + (+k.hold || 0) * 7;
      for (const v of k.pose) s = (s * 1.000001 + v) % 1e12;
    }
    return s + "|" + RIG.servoMaxDps + "|" + RIG.servoAccel + "|" + maxDps() + "|" + JSON.stringify(SMOOTH);
  },
  // V for the list K, or null when this maker is not smoothed (cosine)
  of(K, source = "studio") {
    if (!K || K.length < 3 || !this.on(source)) return null;
    const sig = this.sig(K), got = this.cache.get(K);
    if (got && got.sig === sig) return got.V;
    const world = safeRevision() + "|" + CLEAR + "|" + planPace();
    if (world !== this.memoSig) {
      this.memo = /* @__PURE__ */ new Map();
      this.memoSig = world;
    }
    const sm = new MotionSmooth({
      cfg: { ...SMOOTH, checkDeg: SAFE.checkDeg },
      maxDps: Array.from({ length: NJ }, (_, j) => jointMaxDps(j)),
      acc: RIG.servoAccel,
      cap: planPace(K) === "music" ? musicPace.cap(K) : SAFE_DPS,
      touches: (p) => !!collisionAt(p),
      memo: this.memo,
      // planner detours (safe_path.js marks them k.via) are corners the RRT
      // chose; with "planner" off the arm rests on them exactly as before
      rest: (k) => !!k.via && !this.on("planner")
    });
    const V = sm.vias(K);
    this.cache.set(K, { sig, V });
    return V;
  }
};
function addKey() {
  clearBadMarks();
  const k = { pose: [...pose], t: 1e3, hold: 0 };
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
  if (selKey >= 1 && !timePinned(selKey))
    keys[selKey].t = autoTime(keys[selKey - 1].pose, keys[selKey].pose, keyDps(selKey));
  if (keys[selKey + 1] && !timePinned(selKey + 1))
    keys[selKey + 1].t = autoTime(keys[selKey].pose, keys[selKey + 1].pose, keyDps(selKey + 1));
  clampKeyTimes();
  renderTimeline();
}
function dupKey() {
  if (!keys[selKey]) return;
  clearBadMarks();
  const copy = JSON.parse(JSON.stringify(keys[selKey]));
  delete copy.cues;
  delete copy.cuesAfter;
  keys.splice(selKey + 1, 0, copy);
  bumpKeys();
  selKey++;
  clampKeyTimes();
  renderTimeline();
}
function delKey() {
  if (keys.length <= 1 || !keys[selKey]) return;
  clearBadMarks();
  const gone = selKey;
  keys.splice(selKey, 1);
  bumpKeys();
  selKey = Math.max(0, selKey - 1);
  retimeAt(gone);
  renderTimeline();
  selectKey(selKey);
}
function moveKey(d) {
  const i = selKey, j = i + d;
  if (!keys[i] || !keys[j]) return;
  clearBadMarks();
  [keys[i], keys[j]] = [keys[j], keys[i]];
  bumpKeys();
  selKey = j;
  const last = Math.max(i, j);
  retimeAt(i);
  retimeAt(j);
  if (keys[last + 1]) retimeAt(last + 1);
  renderTimeline();
}
function keyTravelMs(i) {
  const K = playKeys();
  const at = K.findIndex((k) => k.src === i && !k.loopReturn);
  if (at > 0) {
    let travel = 0;
    for (let n = at; n < K.length && K[n].src === i && !K[n].loopReturn; n++)
      travel += K[n].t + (K[n].via ? K[n].hold || 0 : 0);
    return travel;
  }
  if (at === 0) return 0;
  return keys[i] ? keys[i].t : 0;
}
function keyStartMs(i) {
  const K = playKeys();
  let at = K.findIndex((k) => k.src === i && !k.loopReturn);
  if (at < 0) {
    at = K.findIndex((k) => k.src > i);
    if (at < 0) return totalMs();
  }
  if (at <= 0) return 0;
  let t = K[0].hold || 0;
  for (let j = 1; j < at; j++) t += K[j].t + (K[j].hold || 0);
  return t;
}
function keyIndexAtMs(ms) {
  const K = playKeys();
  if (K.length < 2) return 0;
  let clock = K[0].hold || 0;
  if (ms <= clock) return 0;
  for (let i = 1; i < K.length; i++) {
    clock += K[i].t;
    if (ms < clock) return i;
    clock += K[i].hold || 0;
    if (ms < clock) return Math.min(i + 1, K.length - 1);
  }
  return K.length - 1;
}
let seekToken = 0;
function selectKey(i) {
  if (typeof sequenceAudio !== "undefined" && sequenceAudio.preview) {
    selKey = i;
    sequenceAudio.rewind(keyStartMs(i));
    return;
  }
  const was = playing;
  let token = ++seekToken;
  if (was) {
    playing = false;
    $("playBtn").textContent = "▶ Play";
    livePause();
    stopRobotSequence();
    keepAwake(false);
  }
  token = seekToken;
  servoPlay = null;
  selKey = i;
  let travel = 0;
  if (keys[i]) {
    const from = pose.slice();
    pose = [...keys[i].pose];
    travel = Math.max(keyTravelMs(i), autoTime(from, pose, keyDps(i)));
    poseChanged(false, travel);
  }
  playT = was ? keyStartMs(i) + keyTravelMs(i) : keyStartMs(i);
  if (was) {
    const epoch = safeMotionEpoch;
    const arrived = liveLinked() ? lastSafeMove : new Promise((r) => setTimeout(() => r(true), travel));
    arrived.then((ok) => {
      if (ok && token === seekToken && epoch === safeMotionEpoch && !playing) togglePlay();
    });
  }
  const total = totalMs();
  $("scrub").value = total ? Math.round(playT / total * 1e3) : 0;
  renderTimeline();
}
function totalMs() {
  const K = playKeys();
  let t = 0;
  for (let i = 1; i < K.length; i++) t += K[i].t + (K[i].hold || 0);
  t += K.length ? K[0].hold || 0 : 0;
  return t + loopReturnMs();
}
function loopReturnMs() {
  if (checkedTimeline() && safeTimelineCache.loop) return 0;
  const K = playKeys();
  if (!$("loopChk") || !$("loopChk").checked || K.length < 2) return 0;
  return autoTime(K[K.length - 1].pose, K[0].pose, speedDps());
}
function renderTimeline() {
  if (typeof timelineUndo !== "undefined") timelineUndo.seed();
  const box = $("keys");
  $("timelineEmpty").hidden = keys.length > 0;
  box.innerHTML = "";
  keys.forEach((k, i) => {
    const el = document.createElement("div");
    el.className = "key" + (i === selKey ? " sel" : "") + (k.off ? " off" : "") + (k.seqStart && i > 0 ? " seqstart" : "");
    el.onclick = (e) => {
      if (!e.target.closest("input,button,select,label,textarea")) selectKey(i);
    };
    el.setAttribute("data-keyboard", ".kgo");
    const bar = document.createElement("div");
    bar.className = "kbar";
    const idx = document.createElement("div");
    idx.className = "kidx";
    const go = document.createElement("button");
    go.className = "kgo";
    go.textContent = String(i);
    go.title = "go to move " + i + " and show that pose";
    go.setAttribute("aria-label", "go to move " + i + (k.name ? ": " + k.name : ""));
    go.setAttribute("aria-pressed", i === selKey ? "true" : "false");
    go.onclick = (e) => {
      e.stopPropagation();
      selectKey(i);
    };
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
    nm.title = "what this move is, in your words. Saved with the project and written into the exported file as a comment.";
    nm.onclick = (e) => e.stopPropagation();
    nm.onchange = () => {
      const v = nm.value.trim();
      if (v) k.name = v;
      else delete k.name;
      bumpKeys();
      renderTimeline();
    };
    idx.appendChild(nm);
    const sk = document.createElement("button");
    sk.className = "kskip";
    sk.textContent = k.off ? "○" : "●";
    sk.title = k.off ? "suspended — click to put this keyframe back in the run" : "suspend: skip this keyframe when playing, exporting and uploading";
    sk.onclick = (e) => {
      e.stopPropagation();
      k.off = !k.off;
      bumpKeys();
      clearBadMarks();
      playT = 0;
      renderTimeline();
      $("tlStat").textContent = anySuspended() ? keys.filter((x) => x.off).length + " keyframe(s) suspended — they are skipped when playing, exporting and uploading" : "all keyframes active";
    };
    idx.appendChild(sk);
    HANDS.forEach((h, arm) => {
      const now = palmWord(palmUpnessOf(k.pose, arm));
      const sel = document.createElement("select");
      sel.className = "kpalm";
      [
        ["palm", h.side + " ✋ palm up"],
        ["back", h.side + " 🤚 back up"],
        ["side", h.side + " on edge"]
      ].forEach(([v, label]) => {
        const o = document.createElement("option");
        o.value = v;
        o.textContent = label;
        o.disabled = v === "side";
        sel.appendChild(o);
      });
      sel.value = now;
      sel.title = "which side of the " + h.label.toLowerCase() + " the audience sees on top in this move. Pick the other and the arm turns round; the hand stays where it is.";
      sel.onclick = (e) => e.stopPropagation();
      sel.onchange = () => turnKeyPalm(i, arm, sel.value === "palm" ? 1 : -1);
      idx.appendChild(sel);
    });
    if (i > 0) {
      [
        ["⇄", "lr", "mirror LEFT and RIGHT: the same shape on the other arm"],
        ["⇅", "fb", "mirror FRONT and BACK: each arm reaches the other way and stays on its own side"]
      ].forEach(([glyph, which, tip]) => {
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
    const pv = document.createElement("div");
    pv.className = "kpose";
    pv.textContent = k.pose.map((a) => Math.round(a)).join(" ");
    const lim = i > 0 && keys[i - 1] ? minTimeWhy(keys[i - 1].pose, k.pose) : null;
    const kmin = lim ? lim.ms : MIN_MOVE_MS;
    const tr = document.createElement("div");
    tr.className = "ktime";
    const tIn = document.createElement("input");
    tIn.type = "number";
    tIn.value = k.t;
    tIn.min = kmin;
    tIn.step = 50;
    tIn.title = (i === 0 ? "entry time from wherever the robot is (ms)" : "time from previous keyframe (ms)") + ` — minimum ${kmin} ms, set by ${lim ? lim.why : "the 80 ms floor"}; longer is always allowed. Typing one PINS it: editing the pose afterwards will not re-time this move.`;
    if (k.tset) tIn.classList.add("pinned");
    tIn.onchange = () => {
      const want = Math.round(+tIn.value || 0);
      k.t = Math.max(kmin, want);
      delete k.dps;
      pinTime(i);
      bumpKeys();
      if (want < kmin)
        $("tlStat").textContent = `time raised to ${kmin} ms — held by ${lim ? lim.why : "the 80 ms floor"}. ` + (lim && lim.fix ? lim.fix : "");
      renderTimeline();
    };
    let reNote = null;
    const eff = playKeys().find((x) => x.src === i);
    if (eff && Math.round(eff.t) !== Math.round(k.t)) {
      const re = document.createElement("span");
      re.className = "statline";
      re.style.marginLeft = "6px";
      re.textContent = "runs " + Math.round(eff.t) + "ms";
      re.title = "a keyframe before this one is suspended, so this move runs between different poses and is re-timed. Your " + Math.round(k.t) + " ms comes back when you un-suspend.";
      reNote = re;
    }
    const hIn = document.createElement("input");
    hIn.type = "number";
    hIn.value = k.hold || 0;
    hIn.min = 0;
    hIn.step = 100;
    hIn.title = "hold this pose (ms) before the next move";
    hIn.onchange = () => {
      k.hold = Math.max(0, Math.round(+hIn.value || 0));
      bumpKeys();
      renderTimeline();
    };
    tr.append(document.createTextNode("T"), tIn);
    if (i > 0) {
      const pin = document.createElement("button");
      pin.className = "kpin" + (k.tset ? " on" : "");
      pin.textContent = k.tset ? "📌" : "🕘";
      pin.setAttribute("aria-pressed", k.tset ? "true" : "false");
      pin.title = k.tset ? "this time is yours and is kept when you edit the pose. Click to let Studio time this move again." : "Studio times this move from the pose and the speed. Click to keep the time it has now, whatever you change afterwards.";
      pin.onclick = (e) => {
        e.stopPropagation();
        if (k.tset) {
          unpinTime(i);
          retimeAt(i);
          $("tlStat").textContent = `move ${i} is timed by Studio again: ${keys[i].t} ms.`;
        } else {
          pinTime(i);
          $("tlStat").textContent = `move ${i} is held at ${k.t} ms — editing the pose will not change it. Only the servos' own minimum can raise it.`;
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
      const dIn = document.createElement("input");
      dIn.type = "number";
      dIn.min = 5;
      dIn.max = 600;
      dIn.step = 5;
      dIn.className = "kdps";
      dIn.value = k.dps ? Math.round(k.dps) : "";
      dIn.placeholder = Math.round(speedDps());
      dIn.title = "this move's own speed (°/s). Empty = the sequence's " + Math.round(speedDps()) + " °/s. Setting it re-times this move and hands the timing back to Studio; typing a time above pins it again. This move cannot go under " + kmin + " ms: " + (lim ? lim.why : "the 80 ms floor") + ".";
      dIn.onchange = () => {
        const v = Math.round(+dIn.value || 0);
        const use = v >= 5 ? Math.min(v, slowestDps()) : speedDps();
        if (v >= 5) k.dps = use;
        else delete k.dps;
        unpinTime(i);
        const free = Math.max(
          MIN_MOVE_MS,
          Math.round(deltaDeg(keys[i - 1].pose, k.pose) / use * 1e3)
        );
        k.t = autoTime(keys[i - 1].pose, k.pose, use);
        bumpKeys();
        renderTimeline();
        $("tlStat").textContent = v >= 5 && v > use ? `${v} °/s kept at ${use} °/s — no servo on this robot goes faster.` : free < k.t ? `move ${i} stays ${k.t} ms — held by ${lim ? lim.why : "the 80 ms floor"}. ` + (lim && lim.fix ? lim.fix : "") : `move ${i} now takes ${k.t} ms at ${Math.round(use)} °/s.`;
      };
      const held = lim && Math.max(
        MIN_MOVE_MS,
        Math.round(deltaDeg(keys[i - 1].pose, k.pose) / keyDps(i) * 1e3)
      ) < lim.ms;
      const minTxt = document.createElement("span");
      minTxt.textContent = "min " + kmin + " · ";
      if (held) {
        minTxt.className = "statline";
        minTxt.textContent = "min " + kmin + " ⚑ · ";
        minTxt.title = "this move is already as short as it is allowed to be: " + lim.why + ". " + lim.fix;
      }
      mn.append(minTxt, dIn, document.createTextNode("°/s"));
    }
    const mus = document.createElement("button");
    mus.type = "button";
    mus.className = "kmus" + (keyCue(k, "play") ? " on" : "");
    mus.textContent = "♪";
    mus.setAttribute("aria-pressed", musOpen.has(i) ? "true" : "false");
    mus.title = keyCue(k, "play") ? "plays " + cueTrack(k) + (cueLoop(k) ? " on repeat" : "") + " from here" : "give this move a track from the robot's card";
    mus.onclick = () => {
      if (musOpen.has(i)) musOpen.delete(i);
      else musOpen.add(i);
      loadMusicList();
      renderTimeline();
    };
    mn.appendChild(mus);
    el.append(bar, idx, pv, tr, mn);
    if (musOpen.has(i) || keyCue(k, "play")) el.append(musicRow(k, i));
    const lag = servoLag.forKey(i);
    if (lag && lag.level) {
      el.classList.add("lag" + lag.level);
      el.title = `the real servos fall ${Math.round(lag.deg)}° behind here (${JOINT_LABELS[lag.joint] || "joint " + (lag.joint + 1)})`;
    }
    if (k.bad) {
      el.classList.add("bad");
      const b = document.createElement("div");
      b.className = "kbad";
      b.textContent = "⚠ " + k.bad;
      el.append(b);
    }
    box.appendChild(el);
  });
  $("tlTime").textContent = (playT / 1e3).toFixed(1) + "s / " + (totalMs() / 1e3).toFixed(1) + "s";
  musicPace.render();
  if ($("servoStat")) $("servoStat").textContent = servoLag.summary();
  renderTimeBar();
}
let tlZoom = 1;
function zoomTimeline(factor) {
  tlZoom = Math.max(0.5, Math.min(10, tlZoom * factor));
  const tr = $("tbTrack");
  const ru = $("tbRuler");
  if (tr) tr.style.width = tlZoom * 100 + "%";
  if (ru) ru.style.width = tlZoom * 100 + "%";
  renderTimeBar();
}
function renderTimeBar() {
  const box = $("tbBlocks"), ruler = $("tbRuler");
  if (!box) return;
  box.innerHTML = "";
  const K = playKeys(), total = totalMs();
  if (!total || K.length < 2) {
    const empty = document.createElement("div");
    empty.className = "tb-blk note";
    empty.style.left = "0";
    empty.style.width = "100%";
    empty.textContent = K.length < 2 ? "add a second pose to make a movement" : "these poses are all the same";
    box.appendChild(empty);
    if (ruler) ruler.innerHTML = "";
    return;
  }
  const pct = (ms) => ms / total * 100 + "%";
  const band = (left, width, cls, label, title) => {
    if (width <= 0) return;
    const d = document.createElement("div");
    d.className = "tb-blk" + (cls ? " " + cls : "");
    d.style.left = pct(left);
    d.style.width = pct(width);
    if (label && width / total > 0.06) d.textContent = label;
    d.title = title;
    box.appendChild(d);
  };
  if (K[0].hold) band(
    0,
    K[0].hold,
    "hold",
    "wait",
    "waits " + (K[0].hold / 1e3).toFixed(1) + "s before starting"
  );
  for (let i = 1; i < K.length; i++) {
    const src = K[i].src, k = keys[src] || K[i];
    const start = keyStartMs(src), dur = keyTravelMs(src);
    const name = k.name || String(src);
    band(
      start,
      dur,
      (src === selKey ? "sel" : "") + (k.bad ? " bad" : ""),
      name,
      "move " + src + (k.name ? " (" + k.name + ")" : "") + " takes " + (dur / 1e3).toFixed(1) + "s"
    );
    if (K[i].hold) band(
      start + dur,
      K[i].hold,
      "hold",
      "wait",
      "then waits " + (K[i].hold / 1e3).toFixed(1) + "s"
    );
  }
  if (!ruler) return;
  ruler.innerHTML = "";
  const w = ruler.getBoundingClientRect().width || 600;
  const steps = Math.max(2, Math.min(8, Math.floor(w / 90)));
  for (let s = 0; s <= steps; s++) {
    const t = total * s / steps;
    const tick2 = document.createElement("span");
    tick2.className = "tb-tick" + (s === 0 ? " first" : s === steps ? " last" : "");
    tick2.style.left = pct(t);
    tick2.textContent = (t / 1e3).toFixed(t < 1e4 ? 1 : 0) + "s";
    ruler.appendChild(tick2);
  }
}
function rewind() {
  if (typeof sequenceAudio !== "undefined" && sequenceAudio.preview) {
    sequenceAudio.rewind(0);
    return;
  }
  scrubTo(0);
  $("scrub").value = 0;
  _lastScrub = 0;
  $("tlStat").textContent = "back at the start — press Play to run the whole show";
}
let _pkCache = null;
function keysSignature() {
  let s = keys.length + "|" + speedDps();
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    s += ";" + (k.name || "") + "," + (k.tset ? 1 : 0) + "," + (k.off ? 1 : 0) + "," + k.t + "," + (k.hold || 0) + "," + (k.dps || 0) + "," + k.pose + "," + (k.cues || []).join("|") + "," + (k.cuesAfter || []).join("|");
  }
  return s;
}
function bumpKeys() {
  crashForced = false;
  if (typeof sequenceAudio !== "undefined") sequenceAudio.keysChanged(keys);
  if (playing && safeTimelineCache) cancelSafeMotion("timeline edited", { previewOnly });
  _pkCache = null;
  saveDraft();
  if (typeof timelineUndo !== "undefined") timelineUndo.changed();
}
const DRAFT_KEY = "nong_timeline_draft";
let draftTimer = null;
let draftArmed = false;
function saveDraft() {
  if (!draftArmed) return;
  clearTimeout(draftTimer);
  draftTimer = setTimeout(() => {
    try {
      if (keys.length <= 1 || !isDirty()) {
        localStorage.removeItem(DRAFT_KEY);
        return;
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        at: Date.now(),
        name: $("projName") && $("projName").value || "",
        keys,
        rig: RIG,
        safeDps: SAFE_DPS,
        musicDps: SEQ_MUSIC_DPS,
        speedDps: speedDps(),
        maxDps: maxDps(),
        loop: $("loopChk").checked,
        seqNext: $("seqNext").value,
        sourceAudioAsset: typeof sequenceAudio !== "undefined" ? sequenceAudio.draftRef() : null
      }));
    } catch (e) {
    }
  }, 400);
}
function offerDraft() {
  let d = null;
  try {
    d = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null");
  } catch (e) {
    d = null;
  }
  if (!d || !Array.isArray(d.keys) || d.keys.length <= 1) return;
  if (keys.length > 1) return;
  const when = new Date(d.at || Date.now()).toLocaleString();
  const st = $("tlStat");
  if (st) {
    st.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "There is unsaved work from " + when + " (" + d.keys.length + " keyframes). ";
    const yes = document.createElement("button");
    yes.textContent = "Restore it";
    yes.onclick = () => {
      if (d.rig) {
        try {
          localStorage.setItem("nong_rig_prev", JSON.stringify(RIG));
        } catch (e) {
        }
        RIG = mergeRig(d.rig);
        saveRig();
        renderRigUI();
        buildRobot();
      }
      keys = d.keys;
      if (d.safeDps >= 5 && !boardSafeDpsMax) {
        SAFE_DPS = Math.round(d.safeDps);
        $("safeDpsInput").value = String(SAFE_DPS);
      }
      if (Number.isFinite(d.musicDps)) SEQ_MUSIC_DPS = d.musicDps;
      if (d.speedDps) $("speedDps").value = d.speedDps;
      if (d.maxDps) $("maxDps").value = d.maxDps;
      if (d.loop != null) $("loopChk").checked = !!d.loop;
      if (d.seqNext != null) $("seqNext").value = d.seqNext;
      if ((d.name || d.seq) && $("projName")) $("projName").value = d.name || d.seq;
      selKey = 0;
      if (keys.length) pose = [...keys[0].pose];
      bumpKeys();
      timelineUndo.reset();
      poseChanged(false, 0, { previewOnly: true });
      renderTimeline();
      renderSliders();
      if (typeof sequenceAudio !== "undefined") sequenceAudio.restore(d.sourceAudioAsset).then(() => saveDraft());
      st.textContent = "Restored the unsaved timeline. Save it to keep it.";
    };
    const no = document.createElement("button");
    no.textContent = "Discard";
    no.onclick = () => {
      try {
        localStorage.removeItem(DRAFT_KEY);
      } catch (e) {
      }
      st.textContent = "";
    };
    st.append(msg, yes, document.createTextNode(" "), no);
    noticeSaid = null;
    notice(msg.textContent, { actions: [
      { label: yes.textContent, id: "draftRestoreBtn", run: () => yes.onclick() },
      { label: no.textContent, run: () => no.onclick() }
    ] });
  }
}
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
  let gap = false;
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
      t = autoTime(prev.pose, posed, k.dps || speedDps());
    }
    out.push({
      pose: posed,
      hold: k.hold || 0,
      src: i,
      dps: k.dps || 0,
      t,
      name: k.name || "",
      // cues travel with the PLAYED move, like the name above: both
      // buildYaml and hubShowSteps read this list, so a cue left
      // behind here reaches neither the file nor the robot
      cues: carry.concat(k.cues || []),
      cuesAfter: (k.cuesAfter || []).slice()
    });
    carry = [];
    gap = false;
  });
  if (carry.length && out.length)
    out[out.length - 1].cuesAfter = out[out.length - 1].cuesAfter.concat(carry);
  return out;
}
function anySuspended() {
  return keys.some((k) => k.off);
}
function mirrorKeyArms(i, which) {
  const k = keys[i];
  if (!k) return;
  const m = mirrorPose(k.pose, which);
  if (!m) {
    $("tlStat").textContent = "this rig's two arms are not set up as mirror images (their rotation axes differ in Setup > rig), so there is no mirror to take. Nothing was changed.";
    notice($("tlStat").textContent);
    return;
  }
  k.pose = m;
  bumpKeys();
  clearBadMarks();
  if (i === selKey) {
    pose = [...k.pose];
    poseChanged(false);
    renderSliders();
  }
  renderTimeline();
  $("tlStat").textContent = which === "fb" ? "move " + i + " mirrored front to back — each arm reaches the other way, and stays on its own side" : "move " + i + " mirrored left to right — the same shape on the other arm";
}
function turnKeyPalm(i, arm, want) {
  const k = keys[i];
  if (!k) return;
  const r = facePalm(k.pose, arm, want);
  if (!r) return;
  k.pose = r.pose;
  bumpKeys();
  clearBadMarks();
  if (i === selKey) {
    pose = [...k.pose];
    poseChanged(false);
    renderSliders();
  }
  renderTimeline();
  const h = HANDS[arm].label.toLowerCase();
  $("tlStat").textContent = want * r.upness > 0.5 ? "move " + i + ": " + h + " shows its " + (want > 0 ? "palm" : "back") + " on top now" : "move " + i + ": the joints cannot turn the " + h + " that far with the hand where it is; this is the closest. Move the hand a little and try again.";
  if (want * r.upness <= 0.5) notice($("tlStat").textContent);
}
function easeKeys(K, ms, source = "studio") {
  let t = K[0].hold || 0;
  if (ms <= t) return { pose: [...K[0].pose] };
  const V = motionSmooth.of(K, source);
  for (let i = 1; i < K.length; i++) {
    const seg = K[i].t;
    if (ms < t + seg) {
      if (V) return { pose: MotionSmooth.pose(K[i - 1].pose, K[i].pose, V[i - 1], V[i], seg, (ms - t) / seg) };
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
  return [...ret ? K[0].pose : last];
}
function segmentAt(ms) {
  const K = playKeys();
  let t = K.length ? K[0].hold || 0 : 0;
  if (ms <= t) return -1;
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return i;
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return -1;
  }
  if (K.length && ms < t + loopReturnMs()) return K.length;
  return -1;
}
const MAX_TICK_MS = 120;
let keepAwakeEl = null, playClock = null;
function keepAwake(on) {
  try {
    if (on) {
      if (!keepAwakeEl) {
        keepAwakeEl = new Audio(
          "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA="
        );
        keepAwakeEl.loop = true;
        keepAwakeEl.volume = 1e-4;
      }
      keepAwakeEl.play().catch(() => {
      });
      if (!playClock) playClock = setInterval(playTick, 60);
    } else {
      if (keepAwakeEl) keepAwakeEl.pause();
      if (playClock) {
        clearInterval(playClock);
        playClock = null;
      }
    }
  } catch (e) {
  }
}
async function togglePlay(opts = {}) {
  if (typeof sequenceAudio !== "undefined" && sequenceAudio.pendingRef) {
    sequenceAudio.readyForSave();
    return;
  }
  if (!opts.sequenceAudio && typeof sequenceAudio !== "undefined" && sequenceAudio.asset && sequenceAudio.preview) return sequenceAudio.toggle();
  if (timelinePreparing) {
    timelinePreparing = false;
    cancelSafeMotion("planning cancelled", { previewOnly: !!opts.previewOnly || previewOnly });
    return;
  }
  if (!playing) {
    const epoch = safeMotionEpoch;
    timelinePreparing = true;
    $("playBtn").textContent = "⏹ Stop planning";
    let ready = false;
    try {
      ready = await ensureSafeTimeline(() => epoch !== safeMotionEpoch);
    } finally {
      timelinePreparing = false;
      $("playBtn").textContent = "▶ Play";
    }
    if (epoch !== safeMotionEpoch) return;
    previewOnly = !ready;
  }
  const K = playKeys();
  if (K.length < 2) {
    $("tlStat").textContent = keys.length >= 2 ? "only " + K.length + " keyframe(s) are active — un-suspend some to play" : "add at least 2 keyframes to play";
    return;
  }
  if (!playing) {
    previewOnly = !checkedTimeline();
    if (opts.previewOnly) previewOnly = true;
    else if (checkCollisions(false).length && (liveLinked() || hubDriven())) {
      previewOnly = !crashGate("PLAY it on the robot");
      if (previewOnly) {
        const st = $("tlStat");
        if (st) st.textContent = "playing the PREVIEW only — the robot is not being driven, because this movement crashes";
      }
    }
  }
  playing = !playing;
  $("playBtn").textContent = playing ? "❚❚ Pause" : "▶ Play";
  lastFrame = performance.now();
  lastPlayMs = 0;
  entryHold = false;
  keepAwake(playing);
  lastLiveSeg = -1;
  if (playing && playT >= totalMs()) playT = 0;
  if (!opts.previewOnly) stopRobotSequence();
  if (!playing) {
    livePause();
    return;
  }
  if (previewOnly) return;
  if (hubDriven()) {
    entryHold = true;
    hubPlay(playT).then((ok) => {
      if (ok) return waitEntry();
      entryHold = false;
      playing = false;
      $("playBtn").textContent = "▶ Play";
      keepAwake(false);
    });
    return;
  }
  if (liveLinked()) directSafePlay(playT);
}
function liveLinked() {
  return $("liveChk").checked && haveRobot();
}
function hubDriven() {
  return liveLinked() && !usbDirect();
}
function hubShowSteps() {
  const K = playKeys();
  if (K.length < 2) return null;
  const V = motionSmooth.of(K);
  const steps = K.map((k, i) => ({
    pose: k.pose.map((v) => +fmtA(v)),
    t: i === 0 ? minTime(pose, K[0].pose) : k.t,
    hold: k.hold || 0,
    // the speeds this move starts and ends with (PASS); the hub sends them
    // only to a board that knows PASS
    ...MotionSmooth.passFor(V, i) ? { pass: MotionSmooth.passFor(V, i) } : {},
    // the hub decides which cue is a command it may send (main.py cue_lines),
    // so the editor passes the file's own words straight through
    cues: k.cues || [],
    cues_after: k.cuesAfter || []
  }));
  const ret = loopReturnMs();
  if (ret) steps.push({ pose: steps[0].pose.slice(), t: ret, hold: 0, cues: [], cues_after: [] });
  return steps;
}
async function hubPlay(fromMs) {
  const epoch = safeMotionEpoch, device = safeTarget(), revision = safeRevision();
  const goalRevision = safeGoalRevision;
  const sig = safeTimelineSignature();
  const stale = () => safeStale(epoch, device, revision) || goalRevision !== safeGoalRevision || sig !== safeTimelineSignature();
  return withSafeMotion(async () => {
    try {
      if (stale() || !await ensureSafeTimeline(stale)) return false;
      const steps = hubShowSteps();
      const destination = poseAt(fromMs || 0).slice();
      const loop = $("loopChk").checked, name = ($("projName").value || "sequence").trim();
      const musicStop = showBarMusicStop();
      const initial = await safeTakeover(stale);
      if (!initial || stale()) return false;
      if (!await checkedPoseUnlocked(destination, 0, epoch, goalRevision, initial) || stale()) return false;
      if (!steps || stale()) return false;
      if (!(fromMs > 0)) steps[0].t = MIN_MOVE_MS;
      const r = await fetch("/api/play", {
        method: "POST",
        body: JSON.stringify({
          dev: moduleDev(),
          steps,
          loop,
          name,
          from_ms: Math.round(fromMs || 0),
          watch: !document.hidden,
          // stop the arm if this page freezes (A26-46)
          music_stop_ms: musicStop
          // a show's track may outlive its moves
        })
      }).then((r2) => r2.json());
      if (stale()) {
        await hubStop();
        return false;
      }
      if (r.error) throw new Error(r.error);
      $("robotStat").textContent = "the HUB is playing this — it keeps going with this page closed or hidden. Pause or Stop here ends it.";
      return true;
    } catch (e) {
      $("robotStat").textContent = "The hub could not start the show, so the robot did not move. Check the hub is still running, then press Play again. " + Mice.Words.plain(e).says;
      notice($("robotStat").textContent);
      playing = false;
      $("playBtn").textContent = "▶ Play";
      keepAwake(false);
      return false;
    }
  });
}
let entryHold = false;
async function waitEntry() {
  while (entryHold && playing) {
    try {
      const st = await fetch("/api/play").then((r) => r.json());
      if (!st.running || !st.entering) break;
    } catch (e) {
      break;
    }
    await new Promise((r) => setTimeout(r, 120));
  }
  entryHold = false;
  lastPlayMs = 0;
}
setInterval(() => {
  if (playing && !document.hidden && hubDriven())
    fetch("/api/play/beat", { method: "POST", body: "{}" }).catch(() => {
    });
}, 1e3);
function hubLeaving() {
  try {
    navigator.sendBeacon("/api/play/beat", JSON.stringify({ leaving: true }));
  } catch (e) {
  }
}
document.addEventListener("visibilitychange", () => {
  if (!playing || !hubDriven()) return;
  if (document.hidden) hubLeaving();
  else fetch("/api/play/beat", { method: "POST", body: "{}" }).catch(() => {
  });
});
window.addEventListener("pagehide", () => {
  if (playing && hubDriven()) hubLeaving();
});
function hubStop() {
  return fetch("/api/play/stop", { method: "POST" }).catch(() => {
  });
}
function livePause() {
  cancelSafeMotion("paused");
  lastLiveSeg = -1;
}
function segRemaining(ms) {
  const K = playKeys();
  let t = K.length ? K[0].hold || 0 : 0;
  if (ms <= t) return 0;
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return Math.max(1, Math.round(t + K[i].t - ms));
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return 0;
  }
  const ret = loopReturnMs();
  if (ret && ms < t + ret) return Math.max(1, Math.round(t + ret - ms));
  return 0;
}
function scrubTo(v) {
  if (typeof sequenceAudio !== "undefined" && sequenceAudio.preview) {
    sequenceAudio.rewind(totalMs() * (+v / 1e3));
    return;
  }
  const was = playing;
  ++seekToken;
  const from = pose.slice();
  playing = false;
  $("playBtn").textContent = "▶ Play";
  if (was) {
    livePause();
    stopRobotSequence();
    keepAwake(false);
  }
  playT = totalMs() * (+v / 1e3);
  pose = poseAt(playT).map((v2, i) => clampJ(i, v2));
  applyPose();
  renderSliders();
  renderTimeline();
  if (liveLinked()) {
    const safe = autoTime(from, pose, speedDps());
    if (safe > LIVE_T_MAX) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + safe);
    else sendPoseLive();
  }
}
function fmtA(a) {
  return (Math.round(a * 10) / 10).toString();
}
function buildYaml(fromMs) {
  const name = ($("projName").value || "sequence").trim().replace(/[^\w.-]+/g, "_");
  const lines = [
    "# generated by Nong Studio (code/nong/main_python_set_nong)",
    "# pose order: " + JOINT_NAMES.join(" ") + "  (joint deg, T = ms)",
    "name: " + name,
    "loop: " + ($("loopChk").checked ? "true" : "false"),
    "steps:"
  ];
  const seqDps = Math.round(speedDps());
  const K0 = playKeys();
  const from = fromMs > 0 ? keyIndexAtMs(fromMs) : 0;
  let cur = seqDps;
  for (let s = 0; s < from && s < K0.length; s++) cur = Math.round(K0[s].dps || seqDps);
  lines.push(`  - speed: ${cur}`);
  const music = planPace(K0) === "music";
  if (music && !K0.some((k) => keyCue(k, "pace"))) lines.push("  - " + musicPace.cue());
  const V = motionSmooth.of(K0);
  playKeys().forEach((k, i) => {
    if (i < from) return;
    const want = Math.round(k.dps || speedDps());
    if (want !== cur) {
      lines.push(`  - speed: ${want}`);
      cur = want;
    }
    if (k.name) lines.push(`  # ${k.name.replace(/[\r\n]/g, " ")}`);
    (k.cues || []).forEach((c) => lines.push(`  - ${/^pace:\s*music/i.test(c) ? musicPace.cue() : c}`));
    const t = i === from && from > 0 ? Math.max(k.t, minTime(pose, k.pose)) : k.t;
    const pass = i > from ? MotionSmooth.passFor(V, i) : null;
    if (pass) lines.push(`  - pass: "${pass.map(fmtA).join(" ")}"`);
    lines.push(`  - pose: "${k.pose.map(fmtA).join(" ")} T ${t}"` + (i === 0 ? "    # start pose" : i === from ? "    # resumed from here" : ""));
    if (k.hold > 0) lines.push(`  - wait: ${k.hold}`);
    (k.cuesAfter || []).forEach((c) => lines.push(`  - ${c}`));
  });
  if (music) lines.push("  - pace: normal");
  const next = ($("seqNext").value || "").trim().replace(/[^\w.-]+/g, "");
  if (next) {
    lines.splice(4, 0, "next: " + (next.endsWith(".yaml") ? next : next + ".yaml"));
  }
  return { name, yaml: lines.join("\n") + "\n" };
}
function nothingToWrite(where) {
  if (playKeys().length) return false;
  $(where).textContent = keys.length ? "every keyframe is suspended — un-suspend at least one to export or upload" : "no keyframes yet";
  return true;
}
async function exportYaml(opts) {
  opts = opts || {};
  if (nothingToWrite("tlStat")) return false;
  const sig = workSig();
  const { name, yaml } = buildYaml();
  const have = [...$("seqList").options].map((o) => o.value);
  if (!opts.noAsk && have.includes(name + ".yaml") && !confirm(name + ".yaml is already saved. Replace it?\n\nCancel, then type a new name in the sequence name box to keep both.")) {
    $("tlStat").textContent = "not saved — " + name + ".yaml was left as it was";
    return false;
  }
  let ok = false;
  try {
    const r = await fetch("/api/export", {
      method: "POST",
      body: JSON.stringify({ name: name + ".yaml", yaml })
    });
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error(j && j.error || "HTTP " + r.status);
    $("tlStat").textContent = `saved ${j.file} on this PC — voice answers and the other apps can use it now. Send to robot SD puts it on the board.`;
    ok = true;
    if (!opts.keepDraft) markSaved(sig, name, 0);
  } catch (e) {
    $("tlStat").textContent = "export failed — the hub is not answering, or refused the name. Nothing was written. " + Mice.Words.plain(e).says;
    notice($("tlStat").textContent);
  }
  await refreshSeqs();
  if (ok) seqsChanged();
  if (ok) $("seqList").value = name + ".yaml";
  return ok;
}
const DIM_LABELS = {
  shoulderX: "shoulder ±X",
  shoulderY: "shoulder Y",
  upperLenL: "L upper arm",
  upperLenR: "R upper arm",
  foreLenL: "L forearm",
  foreLenR: "R forearm",
  torsoW: "torso W",
  torsoH: "torso H",
  torsoD: "torso D",
  shrugPivot: "shrug pivot ↑ (mm above shoulders)"
};
function renderRigUI() {
  var _a;
  if ($("extraClearanceMm")) $("extraClearanceMm").value = (_a = RIG.extraClearanceMm) != null ? _a : 0;
  const jb = $("rigJoints");
  jb.innerHTML = "";
  HANDS.forEach((h, i) => {
    const row = document.createElement("div");
    row.className = "row";
    const lbl = document.createElement("span");
    lbl.className = "lbl";
    lbl.textContent = h.label + " palm";
    const turn = document.createElement("button");
    turn.textContent = "↻ Turn the drawn hand";
    turn.title = "the skin-coloured side of the drawn hand is its palm. Turn it until it faces the same way as the real hand's palm.";
    const at = document.createElement("span");
    at.className = "mini";
    at.textContent = RIG.palmTurn[i] + "°";
    turn.onclick = () => {
      RIG.palmTurn[i] = (RIG.palmTurn[i] + 90) % 360;
      at.textContent = RIG.palmTurn[i] + "°";
      rigChanged();
      renderTimeline();
    };
    row.append(lbl, turn, at);
    jb.appendChild(row);
  });
  const hdr = document.createElement("div");
  hdr.className = "rigjrow";
  ["joint", "zero°", "start°", "min°", "max°", "axis", "inv"].forEach((t) => {
    const s = document.createElement("span");
    s.className = "mini";
    s.textContent = t;
    hdr.appendChild(s);
  });
  jb.appendChild(hdr);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "rigjrow";
    const name = document.createElement("span");
    name.className = "jname";
    name.textContent = label;
    const zero = document.createElement("input");
    zero.type = "number";
    zero.min = 0;
    zero.max = 180;
    zero.value = RIG.zero[i];
    zero.title = "zero deg: joint angle where this joint is straight (arm along the body)";
    zero.onchange = () => {
      RIG.zero[i] = clampDeg(+zero.value);
      rigChanged();
    };
    const neu = document.createElement("input");
    neu.type = "number";
    neu.min = 0;
    neu.max = 180;
    neu.value = RIG.home[i];
    neu.title = "robot home: where this joint goes when the robot starts, and when you press Home";
    neu.onchange = () => {
      RIG.home[i] = Math.max(RIG.min[i], Math.min(
        RIG.max[i],
        clampDeg(+neu.value || 0)
      ));
      neu.value = RIG.home[i];
      rigChanged();
    };
    const lo = document.createElement("input");
    lo.type = "number";
    lo.min = 0;
    lo.max = 180;
    lo.value = RIG.min[i];
    lo.title = "minimum JOINT angle this joint can reach";
    lo.onchange = () => {
      RIG.min[i] = Math.min(clampDeg(+lo.value || 0), RIG.max[i] - 1);
      lo.value = RIG.min[i];
      rigChanged();
    };
    const hi = document.createElement("input");
    hi.type = "number";
    hi.min = 0;
    hi.max = 180;
    hi.value = RIG.max[i];
    hi.title = "maximum JOINT angle this joint can reach";
    hi.onchange = () => {
      RIG.max[i] = Math.max(clampDeg(+hi.value || 0), RIG.min[i] + 1);
      hi.value = RIG.max[i];
      rigChanged();
    };
    const ax = document.createElement("select");
    ax.title = "which way this joint rotates: roll (X), pitch (Y) or yaw (Z)";
    ["x", "y", "z"].forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = AXIS_LABEL[v];
      if (RIG.axis[i] === v) o.selected = true;
      ax.appendChild(o);
    });
    ax.onchange = () => {
      RIG.axis[i] = ax.value;
      rigChanged();
    };
    const inv = document.createElement("label");
    inv.style.justifySelf = "center";
    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.checked = !!RIG.invert[i];
    chk.onchange = () => {
      RIG.invert[i] = chk.checked ? 1 : 0;
      rigChanged();
    };
    inv.append(chk);
    row.append(name, zero, neu, lo, hi, ax, inv);
    jb.appendChild(row);
  });
  const svh = document.createElement("div");
  svh.className = "tlabel";
  svh.style.marginTop = "8px";
  svh.textContent = "servo & gear per joint (pinion:gear, pulse µs, max °/s, delay ms, speed-up °/s², travel°, Hz):";
  jb.appendChild(svh);
  const presetRow = document.createElement("div");
  presetRow.className = "row";
  const pl = document.createElement("span");
  pl.className = "lbl";
  pl.textContent = "preset";
  const psel = document.createElement("select");
  psel.innerHTML = "<option value=''>apply a servo to…</option>" + Object.keys(SERVO_TYPES).map((t) => {
    const s = SERVO_TYPES[t];
    const nm = s.label + " (" + s.range + "°)";
    return `<option value="${t}|sh">${nm} → shoulders</option><option value="${t}|el">${nm} → elbows</option><option value="${t}|waist">${nm} → waist</option><option value="${t}|shrug">${nm} → shrug</option><option value="${t}|all">${nm} → all</option>`;
  }).join("");
  psel.onchange = () => {
    if (psel.value) {
      applyServoPreset(psel.value);
      psel.value = "";
    }
  };
  presetRow.append(pl, psel);
  jb.appendChild(presetRow);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 38px 38px 50px 50px 44px 40px 52px 44px 44px";
    const name = document.createElement("span");
    name.className = "jname";
    name.textContent = label;
    row.appendChild(name);
    const mk = (key, min, title, max) => {
      const inp = document.createElement("input");
      inp.type = "number";
      inp.min = min;
      inp.value = RIG[key][i];
      inp.title = title;
      if (max) inp.max = max;
      inp.onchange = () => {
        let v = +inp.value || RIG[key][i];
        if (key === "gearPinion" || key === "gearGear") v = Math.round(v);
        v = Math.max(min, max ? Math.min(max, v) : v);
        RIG[key][i] = v;
        inp.value = v;
        rigChanged();
        renderRigUI();
      };
      row.appendChild(inp);
    };
    mk("gearPinion", 1, "pinion teeth (on the servo)");
    mk("gearGear", 1, "gear teeth (on the joint)");
    mk("pulseMin", 100, "servo pulse minimum (µs)");
    mk("pulseMax", 200, "servo pulse maximum (µs)");
    mk("servoMaxDps", 30, "this servo's physical speed limit (°/s of the joint)");
    mk("servoLagMs", 0, "how late this servo answers a new target (ms). A guess until measured; only Studio's picture of the real servos uses it.");
    mk("servoAccel", 100, "how fast this servo can speed up (°/s² of the joint). A guess until measured; only Studio's picture of the real servos uses it.", 1e5);
    mk(
      "servoRange",
      60,
      "SERVO travel: how far this servo turns end to end. 180 = normal hobby servo, 270 = wide-angle. NOT the joint's range (that is min°/max° above).",
      360
    );
    mk(
      "frameHz",
      40,
      "SERVO frame rate (Hz). 50 = normal hobby servo; the PDI-1181MG is a 330 Hz digital servo. A wrong rate can make a digital servo cut torque.",
      400
    );
    jb.appendChild(row);
    const w = travelWarning(i);
    if (w) {
      const warn = document.createElement("div");
      warn.className = "mini";
      warn.style.color = "var(--warn)";
      warn.style.margin = "0 0 4px 78px";
      warn.textContent = "⚠ " + w;
      jb.appendChild(warn);
    }
  });
  const gm = document.createElement("div");
  gm.className = "mini";
  gm.textContent = "columns: pinion : gear · pulse min · pulse max · max °/s · servo travel°. The robot converts joint→servo with each joint's own ratio and travel, so a 270° shoulder and a 180° elbow both drive correctly. Fitting a wider servo later = change travel° (and the pulse range) on that joint — every saved pose still works, because poses are joint degrees. Push with the button below.";
  jb.appendChild(gm);
  const sh2 = document.createElement("div");
  sh2.className = "tlabel";
  sh2.style.marginTop = "8px";
  sh2.textContent = "sizes (mm radius) — joint ball / bar thickness:";
  jb.appendChild(sh2);
  const SIZE_LABELS = ["L shoulder", "L elbow", "R shoulder", "R elbow"];
  const BAR_LABELS = ["L upper arm", "L forearm", "R upper arm", "R forearm"];
  SIZE_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 1fr 1fr";
    const name = document.createElement("span");
    name.className = "jname";
    name.textContent = label;
    const jr = document.createElement("input");
    jr.type = "number";
    jr.min = 2;
    jr.max = 200;
    jr.value = RIG.jointR[i];
    jr.title = "radius of the " + label + " joint ball (mm)";
    jr.onchange = () => {
      RIG.jointR[i] = Math.max(2, +jr.value || RIG.jointR[i]);
      rigChanged();
    };
    const br = document.createElement("input");
    br.type = "number";
    br.min = 1;
    br.max = 200;
    br.value = RIG.barR[i];
    br.title = "thickness (radius) of the " + BAR_LABELS[i] + " bar (mm)";
    br.onchange = () => {
      RIG.barR[i] = Math.max(1, +br.value || RIG.barR[i]);
      rigChanged();
    };
    row.append(name, jr, br);
    jb.appendChild(row);
  });
  const sizeHint = document.createElement("div");
  sizeHint.className = "mini";
  sizeHint.textContent = "left box = joint ball, right box = the bar below it (L shoulder→upper arm, L elbow→forearm, …). Bar lengths are in the sizes list below.";
  jb.appendChild(sizeHint);
  const th = document.createElement("div");
  th.className = "tlabel";
  th.style.marginTop = "8px";
  th.textContent = "axis tilt (° roll/pitch/yaw) — for joints not exactly at 90°:";
  jb.appendChild(th);
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "rigjrow";
    row.style.gridTemplateColumns = "78px 1fr 1fr 1fr";
    const name = document.createElement("span");
    name.className = "jname";
    name.textContent = label;
    row.appendChild(name);
    ["roll", "pitch", "yaw"].forEach((axName, k) => {
      const inp = document.createElement("input");
      inp.type = "number";
      inp.step = 1;
      inp.value = RIG.tilt[i][k];
      inp.title = axName + " tilt of this joint's axis (deg)";
      inp.onchange = () => {
        RIG.tilt[i][k] = +inp.value || 0;
        rigChanged();
      };
      row.appendChild(inp);
    });
    jb.appendChild(row);
  });
  renderShrugCurve();
  const db = $("rigDims");
  db.innerHTML = "";
  const bodyRow = document.createElement("div");
  bodyRow.className = "jrow";
  const bl = document.createElement("span");
  bl.className = "jname";
  bl.textContent = "body";
  const bsel = document.createElement("select");
  bsel.innerHTML = "<option value=''>use a measured body…</option>" + RIG_PRESETS.map((p) => `<option value="${p.id}">${p.label}</option>`).join("");
  bsel.title = "sets every size below from a real robot; each one says where its numbers come from";
  bsel.onchange = () => {
    if (bsel.value) {
      applyRigPreset(bsel.value);
      bsel.value = "";
    }
  };
  const why = document.createElement("span");
  why.className = "hint";
  why.style.fontSize = "11px";
  why.textContent = RIG_PRESETS.length ? "reach " + RIG_PRESETS[0].reach_mm + " mm" : "";
  bodyRow.append(bl, bsel, why);
  db.appendChild(bodyRow);
  Object.entries(DIM_LABELS).forEach(([k, label]) => {
    const row = document.createElement("div");
    row.className = "jrow";
    const name = document.createElement("span");
    name.className = "jname";
    name.textContent = label;
    const lo = k === "shrugPivot" ? 0 : 5;
    const inp = document.createElement("input");
    inp.type = "number";
    inp.min = lo;
    inp.max = 1e3;
    inp.value = RIG.dims[k];
    inp.onchange = () => {
      RIG.dims[k] = Math.max(lo, +inp.value || 0);
      rigChanged();
    };
    row.append(name, inp, document.createElement("span"));
    db.appendChild(row);
  });
  renderOffsets();
}
let SERVO_TYPES = {
  mg90s: { label: "MG90S", min: 500, max: 2400, dps: 400, range: 180, hz: 50 },
  pdi1181mg: { label: "PDI-1181MG", min: 500, max: 2500, dps: 375, range: 270, hz: 50 },
  tiankong35: { label: "TianKongRC 35kg", min: 500, max: 2500, dps: 250, range: 270, hz: 50 },
  generic180: { label: "generic 180", min: 500, max: 2500, dps: 300, range: 180, hz: 50 },
  generic270: { label: "generic 270", min: 500, max: 2500, dps: 300, range: 270, hz: 50 }
};
let RIG_PRESETS = [
  {
    id: "nong_step_2026_09",
    label: "Nong, measured from the STEP file (Sep 2026)",
    source: "nong_assembly.STEP",
    dims: {
      shoulderX: 88,
      shoulderY: 110,
      upperLenL: 128.7,
      upperLenR: 128.7,
      foreLenL: 167.64,
      foreLenR: 167.64,
      torsoW: 100,
      torsoH: 250,
      torsoD: 70,
      shrugPivot: 68.1
    },
    reach_mm: 296.34,
    note: "arm links and shoulder spacing measured; the torso box is still the drawn stand-in"
  }
];
async function loadRigPresets() {
  try {
    const r = await fetch("/api/rigpresets").then((r2) => r2.json());
    if (r && r.ok && Array.isArray(r.presets) && r.presets.length) {
      RIG_PRESETS = r.presets;
      if (typeof renderRigUI === "function") renderRigUI();
    }
  } catch (e) {
  }
}
loadRigPresets();
function applyRigPreset(id) {
  const p = RIG_PRESETS.find((x) => x.id === id);
  if (!p || !p.dims) return;
  Object.entries(p.dims).forEach(([k, v]) => {
    if (k in RIG.dims) RIG.dims[k] = +v;
  });
  let servos = "";
  if (p.servos && confirm(
    "This body also knows its servos and gears from the STEP file:\n\n" + presetServoSummary(p) + "\n\nOK — use them too\nCancel — keep the servo settings you have now"
  ))
    servos = applyPresetServos(p);
  rigChanged();
  renderRigUI();
  buildRobot();
  renderSliders();
  if (typeof notice === "function")
    notice(p.label + " — reach " + (p.reach_mm || "?") + " mm. " + (servos ? "Servos set: " + servos + ". Press “Send Studio's limits to the robot” to put them on the robot. " : "") + (p.note || ""));
}
function presetServoSummary(p) {
  return Object.entries(p.servos).map(([name, s]) => {
    const t = SERVO_TYPES[s.servo];
    return name + ": " + (t ? t.label : s.servo) + (s.gear ? ", gear " + s.gear[0] + ":" + s.gear[1] : "") + (s.min != null ? ", " + s.min + "–" + s.max + "°" : "");
  }).join("\n");
}
function applyPresetServos(p) {
  try {
    localStorage.setItem("nong_rig_prev", JSON.stringify(RIG));
  } catch (e) {
  }
  const done = [];
  Object.entries(p.servos).forEach(([name, s]) => {
    const i = JOINT_NAMES.indexOf(name);
    if (i < 0) return;
    const t = SERVO_TYPES[s.servo];
    if (t) {
      RIG.pulseMin[i] = t.min;
      RIG.pulseMax[i] = t.max;
      RIG.servoMaxDps[i] = t.dps;
      RIG.servoRange[i] = t.range;
      RIG.frameHz[i] = t.hz;
    }
    if (Array.isArray(s.gear) && s.gear.length === 2) {
      RIG.gearPinion[i] = Math.round(s.gear[0]);
      RIG.gearGear[i] = Math.round(s.gear[1]);
    }
    if (s.min != null && s.max != null) {
      RIG.min[i] = +s.min;
      RIG.max[i] = +s.max;
    }
    done.push(name);
  });
  saveRig();
  return done.join(", ");
}
async function loadServoTypes() {
  try {
    const r = await fetch("/api/servos").then((r2) => r2.json());
    if (r && r.ok && r.servos && Object.keys(r.servos).length) {
      SERVO_TYPES = r.servos;
      if (typeof renderRigUI === "function") renderRigUI();
    }
  } catch (e) {
  }
}
loadServoTypes();
function isShoulderJoint(i) {
  return i === 0 || i === 1 || i === 4 || i === 5;
}
function isElbowJoint(i) {
  return i === 2 || i === 3 || i === 6 || i === 7;
}
function applyServoPreset(val) {
  const [type, where] = val.split("|");
  const s = SERVO_TYPES[type];
  if (!s) return;
  const hit = (i) => where === "all" || where === "sh" && isShoulderJoint(i) || where === "el" && isElbowJoint(i) || where === "waist" && i === 8 || where === "shrug" && i === 9;
  for (let i = 0; i < NJ; i++) {
    if (!hit(i)) continue;
    RIG.pulseMin[i] = s.min;
    RIG.pulseMax[i] = s.max;
    RIG.servoMaxDps[i] = s.dps;
    RIG.servoRange[i] = s.range;
    RIG.frameHz[i] = s.hz;
  }
  rigChanged();
  renderRigUI();
  const wLabel = {
    sh: "the shoulders",
    el: "the elbows",
    waist: "the waist",
    shrug: "the shrug",
    all: "all joints"
  }[where] || where;
  $("limStat").textContent = s.label + " applied to " + wLabel + " — press “Send limits + gear to robot” to push it";
}
function travelWarning(i) {
  const range = RIG.servoRange[i] || 180;
  const ratio = (RIG.gearGear[i] || 1) / (RIG.gearPinion[i] || 1);
  const need = Math.max(90 - RIG.min[i], RIG.max[i] - 90) * ratio;
  const have = range / 2;
  if (need <= have + 0.01) return null;
  const reach = 90 + have / ratio;
  return `this joint needs ±${need.toFixed(0)}° of servo travel but a ${range}° servo only gives ±${have.toFixed(0)}° — it will stop at about ${(180 - reach).toFixed(0)}°–${reach.toFixed(0)}°. Use a wider servo (270°), a smaller gear ratio, or tighter min°/max°.`;
}
function rigChanged() {
  if (typeof cancelSafeMotion === "function") cancelSafeMotion("the rig or safety gap changed");
  saveRig();
  buildRobot();
  renderSliders();
}
function setSafetyClearance(raw) {
  var _a;
  const value = raw.trim() === "" ? NaN : Number(raw);
  const stat = $("clearanceStat");
  if (!Number.isFinite(value) || value < 0) {
    stat.textContent = "Enter a distance of zero or more millimetres.";
    $("extraClearanceMm").value = (_a = RIG.extraClearanceMm) != null ? _a : 0;
    return false;
  }
  RIG.extraClearanceMm = value;
  rigChanged();
  stat.textContent = "Saved: keep at least " + (CLEAR + value) + " mm between parts. Existing paths will be checked again.";
  return true;
}
const OFFSET_STEP = 0.5;
const OFFSET_MAX = 30;
function renderOffsets() {
  const box = $("trimUI");
  if (!box) return;
  box.innerHTML = "";
  JOINT_LABELS.forEach((label, i) => {
    const row = document.createElement("div");
    row.className = "trow-t" + (Math.abs(RIG.offset[i]) > 0.01 ? " set" : "");
    const name = document.createElement("span");
    name.className = "t-lbl";
    name.textContent = label;
    const val = document.createElement("input");
    val.type = "number";
    val.className = "t-val";
    val.step = OFFSET_STEP;
    val.min = -OFFSET_MAX;
    val.max = OFFSET_MAX;
    val.value = RIG.offset[i];
    val.setAttribute("aria-label", "offset for " + label + ", in degrees");
    val.title = "how far this joint is corrected, in degrees on the arm";
    val.onchange = () => sendOffset(i, +val.value || 0);
    const step = (delta, text, hint) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "t-btn";
      b.textContent = text;
      b.title = hint;
      b.onclick = () => sendOffset(i, RIG.offset[i] + delta);
      return b;
    };
    const zero = document.createElement("button");
    zero.type = "button";
    zero.className = "t-btn";
    zero.textContent = "0";
    zero.title = "clear this joint's offset";
    zero.onclick = () => sendOffset(i, 0);
    row.append(
      name,
      step(-OFFSET_STEP, "−", "move " + label + " back " + OFFSET_STEP + "°"),
      val,
      step(OFFSET_STEP, "+", "move " + label + " on " + OFFSET_STEP + "°"),
      zero
    );
    box.appendChild(row);
  });
}
async function sendOffset(i, deg) {
  const clamped = Math.max(-OFFSET_MAX, Math.min(OFFSET_MAX, Math.round(deg * 2) / 2));
  RIG.offset[i] = clamped;
  saveRig();
  renderOffsets();
  const st = $("trimStat");
  if (!haveRobot()) {
    if (st) st.textContent = JOINT_LABELS[i] + " offset " + clamped + "° — saved here. Connect the robot to move it.";
    return;
  }
  try {
    const r = await rawCmd("OFFSET " + (i + 1) + " " + clamped);
    if (st) st.textContent = /^ERR/i.test(r || "") ? "the robot refused it: " + r : JOINT_LABELS[i] + " is now corrected by " + clamped + "°";
  } catch (e) {
    if (st) st.textContent = "saved here, but it did not reach the robot: " + Mice.Words.plain(e).says;
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
      RIG.offset = RIG.offset.map((d, i) => j.offset[i] !== void 0 ? Number(j.offset[i]) : d);
    saveRig();
    renderOffsets();
    if (st) st.textContent = "read the offsets the robot is using ✓";
  } catch (e) {
    if (st) Mice.fail(st, "read failed", e);
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
    if (st) Mice.fail(st, "cleared here, but the robot was not told", e);
  }
}
function resetRig() {
  const mine = loadRigDefault();
  if (mine) {
    RIG = mine;
  } else {
    if (!confirm("Reset the rig to the factory defaults? (You haven't saved a default of your own — use “★ Save current as default” to keep your tuning.)")) return;
    RIG = JSON.parse(JSON.stringify(DEFAULT_RIG));
  }
  saveRig();
  renderRigUI();
  buildRobot();
}
async function pushLimits() {
  if (!haveRobot()) {
    $("limStat").textContent = "connect to the robot first (Robot link card)";
    notice($("limStat").textContent);
    return;
  }
  try {
    let have = null;
    $("limStat").textContent = "reading what the robot has…";
    try {
      have = JSON.parse(await rawCmd("LIMIT?"));
    } catch (e) {
      have = null;
    }
    const at = (key, i) => {
      const a = have && have[key];
      return Array.isArray(a) && a[i] !== void 0 ? Number(a[i]) : null;
    };
    const same = (key, i, v) => at(key, i) !== null && at(key, i) === v;
    const jobs = [];
    for (let i = 0; i < NJ; i++) {
      const mn = Math.round(RIG.min[i]), mx = Math.round(RIG.max[i]);
      const pmin = RIG.pulseMin[i], pmax = RIG.pulseMax[i];
      const dps = Math.round(RIG.servoMaxDps[i]);
      const rng = Math.round(RIG.servoRange[i]), hz = Math.round(RIG.frameHz[i]);
      const neu = Math.round(RIG.home[i]);
      const off = Math.round(RIG.offset[i] * 2) / 2;
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
      const always = same("offset", i, off) ? [] : [`OFFSET ${i + 1} ${off}`];
      if (!parts.length && !always.length) continue;
      jobs.push({
        joint: i + 1,
        parts,
        always,
        // neutral is APPENDED, never inserted: an older board ignores the extra
        // token, and QC reads the first nine values by position.
        batch: `JCFG ${i + 1} ${RIG.gearPinion[i]} ${RIG.gearGear[i]} ${pmin} ${pmax} ${dps} ${rng} ${hz} ${mn} ${mx} ${neu}`
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
      for (const c of job.always) {
        await rawCmd(c);
        sent++;
      }
      if (useBatch && job.parts.length) {
        const r = await rawCmd(job.batch);
        sent++;
        if (/unknown cmd|ERR usage/i.test(r || "")) {
          useBatch = false;
          sent--;
        } else continue;
      }
      for (const c of job.parts) {
        await rawCmd(c);
        sent++;
      }
    }
    $("limStat").textContent = `sent ${sent} command${sent > 1 ? "s" : ""} for ${jobs.length} joint${jobs.length > 1 ? "s" : ""} (limits, gear, pulse, travel, frame rate, start angle, offset)` + (useBatch ? "" : " — this board is older than JCFG, so each setting went separately") + (have ? "" : " — could not read the robot first, so everything was sent") + " ✓";
  } catch (e) {
    notice(Mice.fail($("limStat"), "send failed", e));
  }
}
async function pullLimits() {
  if (!haveRobot()) {
    $("limStat").textContent = "connect to the robot first";
    notice($("limStat").textContent);
    return;
  }
  try {
    const t = await rawCmd("LIMIT?");
    const j = JSON.parse(t);
    const pull = (src, key) => {
      if (Array.isArray(src)) RIG[key] = RIG[key].map((d, i) => src[i] !== void 0 ? Number(src[i]) : d);
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
    saveRig();
    renderRigUI();
    buildRobot();
    renderSliders();
    $("limStat").textContent = "read limits, gear, start angles and offsets from the robot ✓";
  } catch (e) {
    notice(Mice.fail($("limStat"), "read failed", e));
  }
}
function blankShow() {
  return {
    name: "",
    loop: false,
    items: [],
    join_dps: 0,
    join_ms: 0,
    music: "",
    music_vol: -1,
    music_loop: false,
    music_end: "",
    music_secs: 0
  };
}
let showDraft = blankShow();
let showOnBar = "";
let showBar = { keys: null, musicStopMs: null };
function showBarMusicStop() {
  return showBar.keys === keys ? showBar.musicStopMs : null;
}
function showLimits() {
  const max = [];
  for (let i = 0; i < NJ; i++) max.push(jointMaxDps(i));
  return { safe_dps: SAFE_DPS, max_dps: max };
}
async function refreshShows() {
  try {
    const [s, q] = await Promise.all([
      fetch("/api/shows").then((r) => r.json()),
      fetch("/api/list?kind=sequences").then((r) => r.json())
    ]);
    const sel = $("showList"), add = $("showAddSeq");
    if (!sel || !add) return;
    sel.innerHTML = "<option value=''>Open saved show…</option>";
    (s.shows || []).forEach((n) => {
      const o = document.createElement("option");
      o.value = o.textContent = n;
      sel.appendChild(o);
    });
    if (showDraft.name && (s.shows || []).includes(showDraft.name)) sel.value = showDraft.name;
    const keep = add.value;
    add.innerHTML = "<option value=''>Add a saved sequence…</option>";
    (q.files || []).filter((f) => f.endsWith(".yaml")).forEach((f) => {
      const o = document.createElement("option");
      o.value = o.textContent = f;
      add.appendChild(o);
    });
    if (keep && (q.files || []).includes(keep)) add.value = keep;
  } catch (e) {
  }
}
const seqChan = "BroadcastChannel" in window ? new BroadcastChannel("mice-seqs") : null;
function seqsChanged() {
  refreshShows();
  if (seqChan) seqChan.postMessage("changed");
}
if (seqChan) seqChan.onmessage = () => {
  refreshSeqs().catch(() => {
  });
  refreshShows();
};
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refreshShows();
});
window.addEventListener("focus", () => refreshShows());
function renderShowMusic() {
  const sel = $("showMusic");
  if (!sel) return;
  const cur = showDraft.music || "";
  const names = musicList ? musicList.slice() : [];
  if (cur && names.indexOf(cur) < 0) names.push(cur);
  sel.innerHTML = "";
  [["", "no music"]].concat(names.map((n) => [n, n])).forEach(([v, label]) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = label;
    sel.appendChild(o);
  });
  sel.value = cur;
  sel.title = musicList ? "a track on the robot's card, played from the start of the show to its end" : musicNote || "connect the robot to choose a track";
  $("showMusicVol").value = showDraft.music_vol >= 0 ? showDraft.music_vol : "";
  $("showMusicVol").disabled = !cur;
  $("showMusicLoop").checked = !!showDraft.music_loop;
  $("showMusicLoop").disabled = !cur;
  $("showMusicEndRow").style.display = cur ? "" : "none";
  $("showMusicEnd").value = showDraft.music_end || "";
  $("showMusicSecs").value = showDraft.music_end ? showDraft.music_secs : "";
  $("showMusicSecs").style.display = showDraft.music_end ? "" : "none";
  if (!musicList && robotLinked()) loadMusicList().then(() => {
    if (musicList) renderShowMusic();
  });
}
function addShowMusicFromPc() {
  if (!robotLinked()) {
    $("showStat").textContent = "Connect the robot first (Robot tab) — the track goes onto the robot's card, so it needs the robot.";
    notice($("showStat").textContent);
    return;
  }
  const pick = (name, whyNot, renamed) => {
    if (!name) {
      $("showStat").textContent = whyNot;
      notice(whyNot);
      return;
    }
    showDraft.music = name;
    renderShowMusic();
    showChanged();
    $("showStat").textContent = name + " is on the robot's card and is now this show's music" + (renamed || "") + ". Save the show to keep it.";
  };
  pick.busy = (msg) => {
    $("showStat").textContent = msg;
  };
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
  $("showJoinS").value = showDraft.join_ms > 0 ? showDraft.join_ms / 1e3 : "";
  renderShowMusic();
  box.innerHTML = "";
  if (!showDraft.items.length) {
    box.innerHTML = "<div class='mini'>No sequences yet — add one above.</div>";
    return;
  }
  showDraft.items.forEach((it, i) => {
    const row = document.createElement("div");
    row.className = "row";
    const n = document.createElement("span");
    n.className = "lbl";
    n.textContent = i + 1 + ".";
    const name = document.createElement("span");
    name.style.flex = "1";
    name.textContent = it.seq;
    const hold = document.createElement("input");
    hold.type = "number";
    hold.min = 0;
    hold.step = 100;
    hold.value = it.hold || 0;
    hold.style.width = "80px";
    hold.title = "stand still for this long AFTER this sequence, in ms. 0 = run straight on into the next one.";
    hold.onchange = () => {
      it.hold = Math.max(0, +hold.value || 0);
      showChanged();
    };
    const mode = document.createElement("select");
    mode.style.width = "110px";
    mode.title = "play this sequence again: a number of times, or for a number of seconds";
    [
      ["", "play once"],
      ["times", "repeat × times"],
      ["seconds", "repeat for seconds"],
      ["exact", "run for exactly … s"]
    ].forEach(([v, label]) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = label;
      mode.appendChild(o);
    });
    mode.value = it.repeat_mode || "";
    const rep = document.createElement("input");
    rep.type = "number";
    rep.min = mode.value === "times" ? 2 : mode.value === "exact" ? 0.1 : 1;
    rep.step = mode.value === "seconds" ? 5 : 1;
    rep.style.width = "70px";
    rep.value = it.repeat || "";
    rep.style.display = mode.value ? "" : "none";
    rep.title = mode.value === "seconds" ? "keep repeating until this many seconds have passed. A pass is never cut in half, so the last one finishes and the item runs a little over." : mode.value === "exact" ? "this sequence gets exactly this many seconds and no more. It is cut wherever it has got to, and the move into the next sequence's first pose is timed to arrive right on the deadline — so the show keeps to its timetable and the join is not visible." : "how many times this sequence plays in a row";
    mode.onchange = () => {
      it.repeat_mode = mode.value;
      if (!mode.value) it.repeat = 0;
      else if (!(it.repeat > 0)) it.repeat = mode.value === "times" ? 2 : 30;
      if (mode.value === "exact" && it.repeat < 0.1) it.repeat = 30;
      renderShow();
      showChanged();
    };
    rep.onchange = () => {
      it.repeat = Math.max(mode.value === "times" ? 2 : 0.1, +rep.value || 0);
      renderShow();
      showChanged();
    };
    const unit = document.createElement("span");
    unit.className = "mini";
    unit.textContent = mode.value === "times" ? "×" : mode.value ? "s" : "";
    const btn = (label, title, fn) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.title = title;
      b.onclick = fn;
      return b;
    };
    const spd = document.createElement("input");
    spd.type = "number";
    spd.min = 10;
    spd.max = 400;
    spd.step = 10;
    spd.style.width = "64px";
    spd.value = it.speed_pct || 100;
    spd.setAttribute("aria-label", "speed of " + it.seq + " in this show, percent");
    spd.title = "how fast this sequence runs in this show: 100 = as saved, 50 = half speed, 200 = twice as fast. Pauses keep their length, and a move is never faster than the robot allows.";
    spd.onchange = () => {
      it.speed_pct = Math.max(10, Math.min(400, Math.round(+spd.value || 100)));
      spd.value = it.speed_pct;
      showChanged();
    };
    row.append(
      n,
      name,
      mode,
      rep,
      unit,
      document.createTextNode("speed"),
      spd,
      document.createTextNode("%"),
      document.createTextNode("pause"),
      hold,
      btn("▲", "play earlier", () => {
        moveShowItem(i, -1);
        showChanged();
      }),
      btn("▼", "play later", () => {
        moveShowItem(i, 1);
        showChanged();
      }),
      btn("✕", "take out of this show", () => {
        showDraft.items.splice(i, 1);
        renderShow();
        showChanged();
      })
    );
    box.appendChild(row);
  });
}
function showChanged() {
  if (showOnBar) showOnTimeline(true);
}
function readShowForm() {
  showDraft.name = $("showName").value.trim();
  showDraft.loop = $("showLoop").checked;
  showDraft.join_dps = Math.max(0, +$("showJoinDps").value || 0);
  showDraft.join_ms = Math.max(0, Math.round((+$("showJoinS").value || 0) * 1e3));
  showDraft.music = $("showMusic").value;
  const v = $("showMusicVol").value;
  showDraft.music_vol = showDraft.music && v !== "" ? Math.max(0, Math.min(100, Math.round(+v || 0))) : -1;
  showDraft.music_loop = !!showDraft.music && $("showMusicLoop").checked;
  showDraft.music_end = showDraft.music ? $("showMusicEnd").value : "";
  let secs = Math.max(0, +$("showMusicSecs").value || 0);
  if (showDraft.music_end && $("showMusicSecs").value === "")
    secs = showDraft.music_end === "total" ? 60 : 5;
  showDraft.music_secs = showDraft.music_end ? secs : 0;
  return showDraft;
}
function newShow() {
  showDraft = blankShow();
  renderShow();
  $("showStat").textContent = "new show — add sequences, then Save.";
}
function addShowItem() {
  const f = $("showAddSeq").value;
  if (!f) {
    $("showStat").textContent = "pick a saved sequence to add first.";
    return;
  }
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
  const r = await fetch("/api/show?name=" + encodeURIComponent(n)).then((r2) => r2.json());
  if (!r.ok) {
    $("showStat").textContent = "cannot open " + n + ": " + (r.error || "not found");
    notice($("showStat").textContent);
    return;
  }
  showDraft = Object.assign(blankShow(), r.show);
  showDraft.name = showDraft.name || n;
  renderShow();
  $("showStat").textContent = "opened " + n + " (" + showDraft.items.length + " sequences).";
  await showOnTimeline(false, true);
}
async function showOnTimeline(quiet, onlyIfSafe) {
  const s = readShowForm();
  if (!s.items.length) {
    if (!quiet) $("showStat").textContent = "add at least one sequence first.";
    return false;
  }
  if (quiet && isDirty()) {
    $("showStat").textContent = "the time bar has edits that are not saved, so the show was not redrawn over them. Press ⇣ Show on the time bar to redraw it.";
    return false;
  }
  if (!quiet && !await askUnsaved("put " + (s.name || "this show") + " on the time bar")) {
    $("showStat").textContent = (onlyIfSafe ? "opened " + (s.name || "this show") + " — " : "") + "the time bar was left as it was.";
    return false;
  }
  try {
    const j = await showPost("/api/show/steps", { show: s, limits: showLimits() });
    const steps = j.steps || [], marks = j.marks || [];
    if (steps.length < 2) throw new Error("this show has fewer than two poses");
    const startOf = {}, travel = {}, taken = new Set(marks.map((m) => m.step));
    let prev = "";
    marks.forEach((m) => {
      const name = m.pass > 1 ? m.seq.replace(/\.yaml$/, "") + " ×" + m.pass : m.seq.replace(/\.yaml$/, "");
      if (m.handover && m.step + 1 < steps.length && !taken.has(m.step + 1)) {
        travel[m.step] = prev + " → " + name;
        startOf[m.step + 1] = name;
      } else startOf[m.step] = name;
      prev = m.seq.replace(/\.yaml$/, "");
    });
    keys = steps.map((st, i) => {
      const k = {
        pose: st.pose.map(Number),
        t: Math.round(st.t || 0),
        hold: Math.round(st.hold || 0)
      };
      if (travel[i] !== void 0) k.name = travel[i];
      if (startOf[i] !== void 0) {
        k.name = startOf[i];
        k.seqStart = true;
      }
      if (st.cues && st.cues.length) k.cues = st.cues.slice();
      if (st.cues_after && st.cues_after.length) k.cuesAfter = st.cues_after.slice();
      return k;
    });
    showBar = { keys, musicStopMs: j.music_stop_ms == null ? null : j.music_stop_ms };
    selKey = 0;
    playT = 0;
    bumpKeys();
    timelineUndo.reset();
    clearBadMarks();
    renderTimeline();
    markSaved(workSig(), "", 0);
    showOnBar = s.name || "(unsaved show)";
    const secs = (totalMs() / 1e3).toFixed(1);
    $("showStat").textContent = `${showOnBar} is on the time bar: ${marks.length} sequence pass(es), ${keys.length} keyframes, ${secs}s. Saving a SEQUENCE from here would save the whole show as one file.`;
    return true;
  } catch (e) {
    Mice.fail($("showStat"), "could not draw the show", e);
    notice($("showStat").textContent);
    return false;
  }
}
async function showPost(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.ok === false || j.error) throw new Error(j.need_login ? "log in first" : j.error || "HTTP " + r.status);
  return j;
}
async function saveShow() {
  const s = readShowForm();
  if (!s.name) {
    $("showStat").textContent = "give the show a name first.";
    return;
  }
  try {
    const j = await showPost("/api/show/save", { show: s });
    $("showStat").textContent = (j.replaced ? "saved over " : "saved ") + s.name + ".";
    refreshShows();
  } catch (e) {
    notice(Mice.fail($("showStat"), "not saved", e));
  }
}
async function deleteShow() {
  const n = $("showList").value || readShowForm().name;
  if (!n) {
    $("showStat").textContent = "open a show to delete first.";
    return;
  }
  if (!confirm("Delete the show " + n + "?\n\nIt is moved to shows/.deleted, not erased. Its sequences stay.")) return;
  try {
    await showPost("/api/show/delete", { name: n });
    newShow();
    refreshShows();
    $("showStat").textContent = n + " deleted (kept in shows/.deleted).";
  } catch (e) {
    notice(Mice.fail($("showStat"), "not deleted", e));
  }
}
async function playShow() {
  const s = readShowForm();
  const dev = moduleDev();
  if (!dev) {
    $("showStat").textContent = "connect to the robot first (Robot tab).";
    notice($("showStat").textContent);
    return;
  }
  if (!s.items.length) {
    $("showStat").textContent = "add at least one sequence first.";
    return;
  }
  let kept = "";
  if (keepRunOn() && haveRobot()) {
    $("showStat").textContent = "keeping a copy of " + (s.name || "this show") + " on the robot…";
    try {
      const j = await showPost("/api/show/yaml", { show: s, limits: showLimits() });
      kept = await keepLastRun(j.yaml, j.file);
    } catch (e) {
      kept = "the copy as " + LAST_RUN_FILE + " was not kept: " + Mice.Words.plain(e).says;
    }
  }
  try {
    await showPost("/api/show/play", { dev, show: s, limits: showLimits() });
    $("showStat").textContent = "the hub is running " + (s.name || "this show") + " — it keeps going with this page closed. ⏹ Stop ends it." + (kept ? " Note: " + kept : keepRunOn() && haveRobot() ? " A copy is on the robot as " + LAST_RUN_FILE + ", to play from its own page." : "");
    if (kept) notice(kept);
  } catch (e) {
    notice(Mice.fail($("showStat"), "did not start", e));
  }
}
async function sendShowToRobot() {
  const s = readShowForm();
  if (!haveRobot()) {
    $("showStat").textContent = "connect to the robot first (Robot tab).";
    notice($("showStat").textContent);
    return;
  }
  if (!s.items.length) {
    $("showStat").textContent = "add at least one sequence first.";
    return;
  }
  try {
    $("showStat").textContent = "sending " + (s.name || "this show") + " to the robot…";
    const j = await showPost("/api/show/yaml", { show: s, limits: showLimits() });
    await sdUpload(j.file, j.yaml);
    $("showStat").textContent = j.file + " is saved on the robot. The robot can play it by itself now: pick it in the robot's list (Sequence tab, or the robot's own page).";
    refreshSd();
  } catch (e) {
    notice(Mice.fail($("showStat"), "not sent", e));
  }
}
async function stopShow() {
  try {
    await fetch("/api/play/stop", { method: "POST" });
    $("showStat").textContent = "stopped.";
  } catch (e) {
    $("showStat").textContent = "the hub did not answer the stop.";
  }
}
let musicList = null;
let musicNote = "";
let musicBusy = false;
function robotLinked() {
  return haveRobot();
}
const musOpen = /* @__PURE__ */ new Set();
function keyCue(k, key) {
  const c = (k.cues || []).find((x) => x.toLowerCase().startsWith(key + ":"));
  return c ? c.slice(c.indexOf(":") + 1).trim() : "";
}
function setKeyCue(k, key, val) {
  const rest = (k.cues || []).filter((x) => !x.toLowerCase().startsWith(key + ":"));
  k.cues = val === "" ? rest : rest.concat(key + ": " + val);
  if (!k.cues.length) delete k.cues;
  bumpKeys();
}
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
    if (!robotLinked()) throw new Error("offline");
    const r = await fetch("/api/dev/files?dir=/music&dev=" + encodeURIComponent(moduleDev()));
    const list = await r.json();
    musicList = list.map((f) => f.n).filter((n) => /\.(mp3|wav)$/i.test(n));
    musicNote = musicList.length ? "" : "no tracks on the robot's card yet — add one in the hub: Modules ▸ Open module ▸ Files ▸ /music";
  } catch (e) {
    musicList = null;
    musicNote = "connect the robot to choose a track — it reads the /music folder on its own card. What is already set is kept.";
  }
  musicBusy = false;
  renderTimeline();
}
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
function robotTrackName(name) {
  const ok = /^[A-Za-z0-9._ -]{1,80}$/;
  if (ok.test(name) && name[0] !== ".") return name;
  const dot = name.lastIndexOf(".");
  const ext = dot > 0 ? name.slice(dot).replace(/[^A-Za-z0-9.]/g, "") : "";
  let base = (dot > 0 ? name.slice(0, dot) : name).replace(/[^A-Za-z0-9._ -]+/g, "").replace(/^[ ._-]+|[ .]+$/g, "");
  if (!/[A-Za-z0-9]/.test(base)) {
    const d = /* @__PURE__ */ new Date(), two = (n) => String(n).padStart(2, "0");
    base = "track-" + two(d.getMonth() + 1) + two(d.getDate()) + "-" + two(d.getHours()) + two(d.getMinutes());
  }
  return base.slice(0, 80 - ext.length) + ext;
}
async function uploadMusicFile(k, f, pick) {
  if (usbDirect()) {
    musicNote = "this browser is holding the cable itself, so the hub cannot send the file. Connect through the hub, or add the track on the module website: Files ▸ /music.";
    if (pick) pick("", musicNote);
    renderTimeline();
    return;
  }
  const stop = (why) => {
    musicNote = why;
    if (pick) pick("", why);
    renderTimeline();
  };
  try {
    const w = await fetch("/api/whoami").then((r) => r.json());
    if (!w.authed) {
      currentUser = null;
      showTab("robot");
      return stop("log in again first — the hub was restarted or your login ran out. Log in on the card that just opened, then add the track again.");
    }
  } catch (e) {
  }
  const name = robotTrackName(f.name);
  const renamed = name !== f.name ? " (saved on the robot as " + name + " — its card only takes English letters and numbers in a name)" : "";
  musicNote = "sending " + f.name + " to the robot…";
  if (pick && pick.busy) pick.busy(musicNote);
  renderTimeline();
  try {
    const r = await fetch(
      "/api/dev/upload?background=1&dir=/music&name=" + encodeURIComponent(name) + "&dev=" + encodeURIComponent(moduleDev()),
      { method: "POST", body: await f.arrayBuffer() }
    );
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.error || j.ok === false)
      throw new Error(j.need_login ? "log in first" : j.error || "HTTP " + r.status);
    const end = await watchUpload(name);
    if (end.error) throw new Error(end.error);
    musicList = null;
    await loadMusicList();
    if (pick) pick(name, "", renamed);
    else setKeyCue(k, "play", name);
    musicNote = name + " is on the robot's card — press ▶ to hear it" + renamed;
  } catch (e) {
    musicNote = "the track did not reach the robot: " + Mice.Words.plain(e).says;
    if (pick) pick("", musicNote);
  }
  renderTimeline();
}
function watchUpload(name) {
  let dlg = $("uploadDlg");
  if (!dlg) {
    dlg = document.createElement("dialog");
    dlg.id = "uploadDlg";
    dlg.className = "askdlg updlg";
    dlg.setAttribute("aria-labelledby", "uploadTitle");
    dlg.innerHTML = '<h2 id="uploadTitle">Sending music to the robot</h2><div class="upwheel" id="uploadWheel" role="progressbar" aria-valuemin="0" aria-valuemax="100"><span id="uploadPct">0%</span></div><p class="mini" id="uploadText"></p><p class="mini">Please wait. Nothing else can be done until it is sent — the robot is busy taking the file.</p><div class="row"><button id="uploadCancel">Cancel sending</button></div>';
    document.body.appendChild(dlg);
  }
  const mb = (n) => (n / 1048576).toFixed(1) + " MB";
  return new Promise((resolve) => {
    let done = false;
    const finish = (s) => {
      if (done) return;
      done = true;
      clearInterval(t);
      dlg.close();
      resolve(s);
    };
    $("uploadCancel").disabled = false;
    $("uploadCancel").onclick = () => {
      $("uploadCancel").disabled = true;
      $("uploadText").textContent = "cancelling — taking the half-sent file back off the card…";
      fetch("/api/upload/cancel", { method: "POST" }).catch(() => {
      });
    };
    dlg.oncancel = (e) => e.preventDefault();
    const tick2 = async () => {
      let s;
      try {
        s = await fetch("/api/upload/progress").then((r) => r.json());
      } catch (e) {
        return;
      }
      const pct = s.total ? Math.floor(100 * s.sent / s.total) : 0;
      $("uploadWheel").style.setProperty("--p", pct);
      $("uploadWheel").setAttribute("aria-valuenow", pct);
      $("uploadPct").textContent = pct + "%";
      const secs = Date.now() / 1e3 - (s.started || 0);
      const left = s.sent > 0 && secs > 2 ? (s.total - s.sent) / (s.sent / secs) : 0;
      if (!$("uploadCancel").disabled)
        $("uploadText").textContent = name + " — " + mb(s.sent) + " of " + mb(s.total) + (left ? ", about " + (left >= 90 ? Math.round(left / 60) + " min" : Math.round(left) + " s") + " left" : "");
      if (!s.running) finish(s);
    };
    const t = setInterval(tick2, 500);
    dlg.showModal();
    tick2();
  });
}
function musicRow(k, i) {
  const row = document.createElement("div");
  row.className = "ktime kmusrow";
  const cur = cueTrack(k);
  const sel = document.createElement("select");
  sel.className = "kmustrack";
  sel.setAttribute("aria-label", "music for move " + (i + 1));
  const names = musicList ? musicList.slice() : [];
  if (cur && names.indexOf(cur) < 0) names.push(cur);
  [["", "no music"]].concat(names.map((n) => [n, n])).forEach(([v, label]) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = label;
    if (v === cur) o.selected = true;
    sel.appendChild(o);
  });
  sel.disabled = !musicList && !cur;
  sel.title = musicList ? "the tracks on the robot's card" : "the robot's track list could not be read";
  sel.onchange = () => {
    setCueTrack(k, sel.value, cueLoop(k));
    if (!sel.value) setKeyCue(k, "vol", "");
    renderTimeline();
  };
  const vol = document.createElement("input");
  vol.type = "number";
  vol.min = 0;
  vol.max = 100;
  vol.step = 5;
  vol.className = "kmusvol";
  vol.value = keyCue(k, "vol");
  vol.placeholder = "vol";
  vol.disabled = !cur;
  vol.title = cur ? "volume for this track, 0-100" : "choose a track first, then set its volume";
  vol.onchange = () => {
    const v = vol.value === "" ? "" : String(Math.max(0, Math.min(100, Math.round(+vol.value || 0))));
    setKeyCue(k, "vol", v);
    renderTimeline();
  };
  const rep = document.createElement("label");
  rep.className = "kmusloop";
  const repChk = document.createElement("input");
  repChk.type = "checkbox";
  repChk.checked = cueLoop(k);
  repChk.disabled = !cur;
  rep.title = cur ? "Keep playing this track again and again until the show ends or you press Stop. It restarts in a blink, not as a seamless join." : "choose a track first, then it can repeat";
  repChk.onchange = () => {
    setCueTrack(k, cur, repChk.checked);
    renderTimeline();
  };
  rep.append(repChk, document.createTextNode(" repeat"));
  const play = document.createElement("button");
  play.type = "button";
  play.className = "kmusbtn";
  play.textContent = "▶";
  play.disabled = !cur || !robotLinked();
  play.title = !robotLinked() ? "connect the robot to hear it" : cur ? "play " + cur + " on the robot now, once through" : "choose a track first";
  play.onclick = async () => {
    const v = keyCue(k, "vol");
    try {
      if (v !== "") await rawCmd("VOL " + v);
      musicNote = await rawCmd("PLAY " + cur);
    } catch (e) {
      musicNote = "the robot did not take it: " + Mice.Words.plain(e).says;
    }
    renderTimeline();
  };
  const stop = document.createElement("button");
  stop.type = "button";
  stop.className = "kmusbtn";
  stop.textContent = "■";
  stop.disabled = !robotLinked();
  stop.title = "stop the sound";
  stop.onclick = async () => {
    try {
      musicNote = await rawCmd("PLAY STOP");
    } catch (e) {
      musicNote = Mice.Words.plain(e).says;
    }
    renderTimeline();
  };
  const add = document.createElement("button");
  add.type = "button";
  add.className = "kmusbtn";
  add.textContent = "＋";
  add.disabled = !robotLinked();
  add.title = robotLinked() ? "put a track from this PC onto the robot's card" : "connect the robot to add a track";
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
  let curSpeed = 0;
  let pend = [];
  let pendName = "";
  for (const raw of text.split(/\r?\n/)) {
    const nm = raw.match(/^\s+#\s*(.*?)\s*$/);
    if (nm) {
      pendName = nm[1];
      continue;
    }
    const line = raw.replace(/#.*$/, "").trimEnd();
    let m;
    if (m = line.match(/^name:\s*(.+)$/)) out.name = m[1].trim();
    else if (m = line.match(/^next:\s*(.+)$/)) out.next = m[1].trim();
    else if (m = line.match(/^loop:\s*(true|false)/)) out.loop = m[1] === "true";
    else if (m = line.match(/^\s*-\s*pose:\s*"?([\d.\s]+?)(?:\s+T\s+(\d+))?"?\s*$/)) {
      const nums = m[1].trim().split(/\s+/).map(Number);
      if ((nums.length === ARMJ || nums.length === NJ) && nums.every((n) => !isNaN(n))) {
        while (nums.length < NJ) nums.push(90);
        const k = { pose: nums.map((v, i) => clampJ(i, v)), t: m[2] ? +m[2] : 0, hold: 0 };
        if (curSpeed && curSpeed !== out.speed) k.dps = curSpeed;
        if (pend.length) {
          k.cues = pend;
          out.cues += pend.length;
          pend = [];
        }
        if (pendName) k.name = pendName;
        pendName = "";
        out.keys.push(k);
      } else out.skipped++;
    } else if (m = line.match(/^\s*-\s*wait:\s*(\d+)/)) {
      if (out.keys.length) out.keys[out.keys.length - 1].hold = +m[1];
      else out.skipped++;
    } else if (m = line.match(/^\s*-\s*speed:\s*([\d.]+)/)) {
      curSpeed = +m[1];
      if (!out.speed) out.speed = curSpeed;
    } else if (/^\s*-\s*pass\s*:/.test(line)) {
    } else if (m = line.match(/^\s*-\s*([A-Za-z_][\w-]*):\s*"?(.*?)"?\s*$/)) {
      pend.push((m[1].toLowerCase() + ": " + m[2]).trim());
    } else if (/^\s*-\s/.test(line)) out.skipped++;
  }
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
  timelineUndo.reset();
  if (p.speed >= 5) $("speedDps").value = Math.min(p.speed, slowestDps());
  for (let i = 0; i < keys.length; i++)
    if (!keys[i].t) keys[i].t = i ? autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i)) : 1e3;
  clampKeyTimes();
  $("loopChk").checked = p.loop;
  $("seqNext").value = p.next || "";
  if (p.name) $("projName").value = p.name;
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  $("tlStat").textContent = `loaded ${keys.length} keyframes from ${sourceLabel}` + (p.speed >= 5 ? ` at its own ${Math.round(p.speed)} °/s` : "") + (p.cues ? ` with ${p.cues} music/light step(s), which play with the show and are written back on export` : "") + (p.skipped ? ` (${p.skipped} step(s) this editor does not read — kept only in the original file)` : "") + " — edit, then Save";
  const local = sourceLabel.startsWith("sequences/") ? sourceLabel.slice(10).replace(/\.yaml$/, "") : "";
  markSaved(workSig(), local, p.skipped || 0);
}
async function editLocalSeq() {
  const f = $("seqList").value;
  if (!f) return;
  if (!await askUnsaved("open " + f)) return;
  const r = await fetch("/api/loadseq?name=" + encodeURIComponent(f));
  if (!r.ok) {
    $("tlStat").textContent = "cannot read sequences/" + f + " — the hub answered " + r.status + ". Pick it in the list again, or refresh.";
    notice($("tlStat").textContent);
    return;
  }
  loadParsedSeq(parseSeqYaml(await r.text()), "sequences/" + f);
}
async function editSdSeq(fname) {
  if (!await askUnsaved("open " + fname + " from the robot")) return;
  try {
    const text = await sdDownload(fname);
    loadParsedSeq(parseSeqYaml(text), "robot SD " + fname);
  } catch (e) {
    $("tlStat").textContent = "cannot read " + fname + ": " + Mice.Words.plain(e).says;
    notice($("tlStat").textContent);
  }
}
async function playSavedSeq(sourceLabel, getText) {
  const stat = $("tlStat");
  stat.textContent = "loading " + sourceLabel + "…";
  let text;
  try {
    text = await getText();
  } catch (e) {
    stat.textContent = "cannot read " + sourceLabel + ": " + Mice.Words.plain(e).says;
    notice(stat.textContent);
    return;
  }
  if (!await askUnsaved("play " + sourceLabel)) {
    stat.textContent = "";
    return;
  }
  if (playing) togglePlay();
  const before = keys;
  loadParsedSeq(parseSeqYaml(text), sourceLabel);
  if (keys === before) return;
  playT = 0;
  $("scrub").value = 0;
  togglePlay();
}
async function playLocalSeq() {
  const f = $("seqList").value;
  if (!f) {
    $("tlStat").textContent = "pick a saved sequence in the list first.";
    return;
  }
  await playSavedSeq("sequences/" + f, async () => {
    const r = await fetch("/api/loadseq?name=" + encodeURIComponent(f));
    if (!r.ok) throw new Error("the hub answered HTTP " + r.status + " — is sequences/" + f + " still there?");
    return r.text();
  });
}
async function playSdSeq(fname) {
  await playSavedSeq("robot SD " + fname, () => sdDownload(fname));
}
async function putLocalSeqOnRobot() {
  const f = $("seqList").value;
  if (!f) {
    $("tlStat").textContent = "pick a saved YAML in the list first.";
    return;
  }
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
    $("tlStat").textContent = f + " is saved on the robot. It can play it by itself now, from the robot's list here or on its own page.";
    refreshSd();
  } catch (e) {
    $("tlStat").textContent = f + " was not saved on the robot: " + Mice.Words.plain(e).says;
    notice($("tlStat").textContent);
  }
}
async function deleteLocalSeq() {
  const f = $("seqList").value;
  if (!f) {
    $("tlStat").textContent = "pick a saved YAML in the list first.";
    return;
  }
  if (!confirm("Delete " + f + "?\n\nIt is moved to sequences/.deleted on this PC, not erased.")) return;
  try {
    const r = await fetch("/api/seqdelete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: f })
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.ok) throw new Error(j.need_login ? "log in first" : j.error || "HTTP " + r.status);
    $("tlStat").textContent = f + " deleted (kept in sequences/.deleted).";
    await refreshSeqs();
    seqsChanged();
  } catch (e) {
    $("tlStat").textContent = "could not delete " + f + ": " + Mice.Words.plain(e).says;
    notice($("tlStat").textContent);
  }
}
async function refreshSeqs() {
  const r = await fetch("/api/list?kind=sequences").then((r2) => r2.json());
  const sel = $("seqList");
  sel.innerHTML = "<option value=''>Open saved YAML…</option>";
  (r.files || []).filter((f) => f.endsWith(".yaml")).forEach((f) => {
    const o = document.createElement("option");
    o.value = o.textContent = f;
    sel.appendChild(o);
  });
}
class StudioAudioDigest {
  static portable(bytes) {
    const primes = [];
    for (let n = 2; primes.length < 64; n++) if (!primes.some((p) => p * p <= n && n % p === 0)) primes.push(n);
    const fraction = (x) => Math.floor((x - Math.floor(x)) * 4294967296) >>> 0;
    const state = primes.slice(0, 8).map((p) => fraction(Math.sqrt(p)));
    const constants = primes.map((p) => fraction(Math.cbrt(p)));
    const size = Math.ceil((bytes.length + 9) / 64) * 64, padded = new Uint8Array(size);
    padded.set(bytes);
    padded[bytes.length] = 128;
    const view = new DataView(padded.buffer), bitLength = bytes.length * 8;
    view.setUint32(size - 8, Math.floor(bitLength / 4294967296));
    view.setUint32(size - 4, bitLength >>> 0);
    const rotate = (x, n) => x >>> n | x << 32 - n, words = new Uint32Array(64);
    for (let offset = 0; offset < size; offset += 64) {
      for (let i = 0; i < 16; i++) words[i] = view.getUint32(offset + i * 4);
      for (let i = 16; i < 64; i++) {
        const a2 = words[i - 15], b2 = words[i - 2];
        words[i] = words[i - 16] + (rotate(a2, 7) ^ rotate(a2, 18) ^ a2 >>> 3) + words[i - 7] + (rotate(b2, 17) ^ rotate(b2, 19) ^ b2 >>> 10) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = state;
      for (let i = 0; i < 64; i++) {
        const t1 = h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) + (e & f ^ ~e & g) + constants[i] + words[i] >>> 0;
        const t2 = (rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) + (a & b ^ a & c ^ b & c) >>> 0;
        h = g;
        g = f;
        f = e;
        e = d + t1 >>> 0;
        d = c;
        c = b;
        b = a;
        a = t1 + t2 >>> 0;
      }
      [a, b, c, d, e, f, g, h].forEach((x, i) => {
        state[i] = state[i] + x >>> 0;
      });
    }
    return state.map((x) => x.toString(16).padStart(8, "0")).join("");
  }
  static async sha256(bytes) {
    if (window.crypto && crypto.subtle) return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
    return this.portable(bytes);
  }
}
class StudioSequenceAudio {
  constructor() {
    this.asset = null;
    this.media = null;
    this.preview = false;
    this.tail = null;
    this.loadSerial = 0;
  }
  signature() {
    const a = this.asset || this.pendingRef;
    return a ? [a.sha256, a.name, a.offsetMs || 0].join("|") : "";
  }
  serializable() {
    if (!this.readyForSave()) throw new Error("เพลงที่กู้คืนยังไม่พร้อม เลือกไฟล์ .nong.json อีกครั้ง");
    return this.asset ? { ...this.asset } : null;
  }
  readyForSave() {
    if (!this.pendingRef) return true;
    notice("เพลงที่กู้คืนยังไม่พร้อม รอให้โหลดเสร็จ หรือเปิดไฟล์ .nong.json อีกครั้ง");
    return false;
  }
  draftRef() {
    if (this.pendingRef) return { ...this.pendingRef };
    if (!this.asset) return null;
    const { dataUrl, ...ref } = this.asset;
    return ref;
  }
  async cache(asset, readOnly = false) {
    return new Promise((resolve) => {
      if (!window.indexedDB) return resolve(null);
      const req = indexedDB.open("nong_project_audio", 1);
      req.onupgradeneeded = () => req.result.createObjectStore("tracks");
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
      req.onsuccess = () => {
        const db = req.result, tx = db.transaction("tracks", readOnly ? "readonly" : "readwrite");
        const op = readOnly ? tx.objectStore("tracks").get(asset.sha256) : tx.objectStore("tracks").put(asset, asset.sha256);
        let value = null;
        op.onsuccess = () => {
          value = readOnly ? op.result : asset;
        };
        tx.oncomplete = () => {
          db.close();
          resolve(value);
        };
        tx.onerror = () => {
          db.close();
          resolve(null);
        };
        tx.onabort = () => {
          db.close();
          resolve(null);
        };
      };
    });
  }
  async prepare(input) {
    if (!input) return null;
    let asset = { ...input };
    if (!asset.dataUrl) {
      const cached = await this.cache(asset, true);
      asset = cached ? { ...cached, ...asset, dataUrl: cached.dataUrl } : null;
    }
    if (!asset || typeof asset.dataUrl !== "string" || !/^data:audio\/[a-z0-9.+-]+;base64,/i.test(asset.dataUrl))
      throw new Error("ไฟล์นี้ไม่มีเพลงที่เปิดได้ เลือกไฟล์ท่าและเพลง .nong.json อีกครั้ง");
    if (asset.dataUrl.length > 48 * 1024 * 1024) throw new Error("ไฟล์เพลงใหญ่เกิน 32 MB");
    const raw = atob(asset.dataUrl.slice(asset.dataUrl.indexOf(",") + 1));
    const bytes = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    if (!bytes.length || bytes.length > 32 * 1024 * 1024) throw new Error("ขนาดไฟล์เพลงไม่ถูกต้อง");
    const hash = await StudioAudioDigest.sha256(bytes);
    if (asset.sha256 && asset.sha256 !== hash) throw new Error("เพลงไม่ตรงกับไฟล์ที่บันทึกไว้");
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) throw new Error("เบราว์เซอร์นี้ยังอ่านเพลงไม่ได้ ลองเปิดด้วย Edge หรือ Chrome");
    const decoder = new Context();
    try {
      const decoded = await decoder.decodeAudioData(bytes.buffer.slice(0));
      if (!(decoded.duration > 0)) throw new Error("empty audio");
    } catch (e) {
      throw new Error("อ่านเพลงไม่ได้ ไฟล์อาจไม่สมบูรณ์");
    } finally {
      await decoder.close().catch(() => {
      });
    }
    asset = {
      ...asset,
      name: String(asset.name || asset.file || "เพลง"),
      sha256: hash,
      offsetMs: Number.isFinite(asset.offsetMs) ? asset.offsetMs : 0
    };
    const media = new Audio(asset.dataUrl);
    media.preload = "auto";
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        clean();
        reject(new Error("โหลดเพลงนานเกินไป ลองเลือกไฟล์อีกครั้ง"));
      }, 15e3);
      const clean = () => {
        clearTimeout(timer);
        media.onloadedmetadata = media.onerror = null;
      };
      media.onloadedmetadata = () => {
        clean();
        resolve();
      };
      media.onerror = () => {
        clean();
        reject(new Error("เปิดเพลงไม่ได้"));
      };
      media.load();
    });
    if (!Number.isFinite(media.duration) || media.duration <= 0) throw new Error("ความยาวเพลงไม่ถูกต้อง");
    await this.cache(asset);
    return { asset, media };
  }
  commit(prepared, ownerKeys = keys) {
    ++this.loadSerial;
    this.pendingRef = null;
    this.restoring = false;
    this.pause();
    if (this.media) {
      this.media.onerror = null;
      this.media.removeAttribute("src");
      this.media.load();
    }
    this.asset = prepared ? prepared.asset : null;
    this.media = prepared ? prepared.media : null;
    this.ownerKeys = ownerKeys;
    this.preview = !!prepared;
    this.tail = null;
    this.poseCache = null;
    const bar = $("sequenceAudioBar");
    if (bar) bar.hidden = !prepared;
    if ($("sequenceAudioTitle")) $("sequenceAudioTitle").textContent = prepared ? "เพลง: " + this.asset.name : "";
    if (this.media) this.media.onerror = () => {
      this.pausePreview();
      notice("เพลงหยุดเพราะอ่านไฟล์ไม่ได้ ท่ายังคงอยู่ เลือกเพลงใหม่แล้วลองอีกครั้ง");
    };
    this.status("พร้อมทดลองในหน้าจอ");
  }
  keysChanged(current) {
    if (this.ownerKeys && this.ownerKeys !== current) {
      ++projectLoadGeneration;
      this.pausePreview();
      this.commit(null, current);
    }
    this.ownerKeys = current;
  }
  restart() {
    this.seek(0);
    if (!this.head) this.media.play().catch(() => {
      this.pausePreview();
      this.status("กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง");
    });
  }
  status(text) {
    if ($("sequenceAudioStatus")) $("sequenceAudioStatus").textContent = text;
  }
  pause() {
    if (this.media) this.media.pause();
  }
  pausePreview() {
    this.pause();
    if (this.preview) {
      playing = false;
      lastPlayMs = 0;
      keepAwake(false);
      if ($("playBtn")) $("playBtn").textContent = "▶ Play";
    }
    if ($("sequenceAudioPlay")) $("sequenceAudioPlay").textContent = "▶ ทดลองพร้อมเพลง";
  }
  seek(ms) {
    if (!this.media) return;
    const time = Math.max(0, (ms - (this.asset.offsetMs || 0)) / 1e3);
    this.media.currentTime = Math.min(time, this.media.duration);
    this.head = ms < (this.asset.offsetMs || 0) ? { at: performance.now(), ms } : null;
    if (this.head) this.media.pause();
    this.tail = time >= this.media.duration ? { at: performance.now(), ms } : null;
  }
  async toggle() {
    if (!this.media) return;
    this.preview = true;
    if (playing) {
      this.pausePreview();
      return;
    }
    await togglePlay({ previewOnly: true, sequenceAudio: true });
    if (!playing) return;
    this.seek(playT);
    try {
      if (!this.head && playT < this.media.duration * 1e3 + (this.asset.offsetMs || 0)) await this.media.play();
      if ($("sequenceAudioPlay")) $("sequenceAudioPlay").textContent = "❚❚ หยุดชั่วคราว";
      this.status("เล่นเพลงและท่าในหน้าจอ");
    } catch (e) {
      this.lastPlayError = String(e.name || "") + ": " + e.message;
      this.pausePreview();
      this.status("กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง");
    }
  }
  downloadSong() {
    if (!this.asset) return;
    const link = document.createElement("a");
    link.href = this.asset.dataUrl;
    link.download = this.asset.name;
    link.click();
  }
  clock(ms) {
    if (!this.preview || !this.media || !playing || !previewOnly || entryHold) return null;
    if (this.head) {
      const at = this.head.ms + performance.now() - this.head.at;
      if (at < this.asset.offsetMs) return at;
      this.head = null;
      this.media.currentTime = 0;
      this.media.play().catch(() => {
        this.pausePreview();
        this.status("กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง");
      });
      return this.asset.offsetMs;
    }
    if (this.media.ended || ms >= this.media.duration * 1e3 + (this.asset.offsetMs || 0)) {
      if (!this.tail) this.tail = { at: performance.now(), ms: this.media.duration * 1e3 + (this.asset.offsetMs || 0) };
      return this.tail.ms + performance.now() - this.tail.at;
    }
    if (this.media.paused || this.media.seeking || this.media.readyState < 2) return ms;
    return Math.max(0, this.media.currentTime * 1e3 + (this.asset.offsetMs || 0));
  }
  visualPose(ms) {
    if (!$("servoView") || !$("servoView").checked) return poseAt(ms);
    const signature = keysSignature() + "|" + $("loopChk").checked + "|" + JSON.stringify(RIG);
    if (!this.poseCache || this.poseCache.signature !== signature) {
      const start = playKeys().length ? playKeys()[0].pose : poseAt(0);
      this.poseCache = { signature, model: new ServoFollow(start), samples: [start.slice()] };
    }
    const cache = this.poseCache, index = Math.max(0, Math.floor(ms / 20));
    while (cache.samples.length <= index) {
      const at = cache.samples.length * 20;
      cache.samples.push(cache.model.step(poseAt(at), 20).slice());
    }
    return cache.samples[index].slice();
  }
  rewind(ms = 0) {
    this.pausePreview();
    this.seek(ms);
    playT = ms;
    servoPlay = null;
    pose = poseAt(playT).map((v, i) => clampJ(i, v));
    applyPose();
    renderSliders();
    renderTimeline();
    if ($("scrub")) $("scrub").value = totalMs() ? Math.round(ms / totalMs() * 1e3) : 0;
  }
  async restore(ref) {
    if (!ref) {
      this.commit(null);
      return;
    }
    const serial = ++this.loadSerial;
    this.pendingRef = { ...ref };
    this.restoring = true;
    this.preview = true;
    try {
      const prepared = await this.prepare(ref);
      if (serial === this.loadSerial) this.commit(prepared);
    } catch (e) {
      if (serial === this.loadSerial) {
        this.restoring = false;
        this.pausePreview();
        notice("ท่ากู้คืนแล้ว แต่เพลงยังไม่พร้อม เปิดไฟล์ .nong.json อีกครั้ง: " + e.message);
      }
    }
  }
}
const sequenceAudio = new StudioSequenceAudio();
window.StudioSequenceAudio = StudioSequenceAudio;
class StudioProjectLibrary {
  constructor() {
    this.items = [];
    this.serial = 0;
  }
  async open(selectedId = "") {
    const dialog = $("projectLibrary");
    if (!dialog.open) dialog.showModal();
    const status = $("projectLibraryStatus");
    status.textContent = "กำลังโหลดผลงานล่าสุด…";
    try {
      const response = await fetch("/app/latest-results/catalog.json", { cache: "no-store", signal: AbortSignal.timeout(1e4) });
      if (!response.ok) throw new Error("ยังไม่พบรายการผลงานบน Hub เครื่องนี้");
      const catalog = await response.json();
      if (!Array.isArray(catalog.items)) throw new Error("รายการผลงานไม่สมบูรณ์");
      this.items = catalog.items;
      const list = $("projectLibraryList");
      list.replaceChildren();
      for (const item of this.items) {
        if (!item || typeof item.id !== "string" || typeof item.title !== "string") continue;
        const url = new URL(item.projectUrl, location.origin);
        if (url.origin !== location.origin || !url.pathname.startsWith("/app/latest-results/bundles/")) continue;
        const row = document.createElement("div");
        row.className = "library-item";
        const label = document.createElement("strong");
        label.textContent = item.title;
        const info = document.createElement("span");
        info.className = "hint";
        info.textContent = [item.version, item.status].filter(Boolean).join(" · ");
        const button = document.createElement("button");
        button.textContent = "เปิดพร้อมเพลง";
        button.className = "primary";
        button.onclick = () => this.load(item);
        row.append(label, info, button);
        list.append(row);
        if (item.id === selectedId) {
          row.classList.add("library-selected");
          button.focus();
        }
      }
      status.textContent = this.items.length ? "เลือกชุดงาน หรือเลือกไฟล์ .nong.json ที่ดาวน์โหลดไว้" : "ยังไม่มีชุดงาน เลือกไฟล์ที่บันทึกไว้ได้";
    } catch (e) {
      status.textContent = e.message + " — ยังนำเข้าไฟล์ท่าและเพลงที่ดาวน์โหลดไว้ได้";
    }
  }
  async load(item) {
    const generation = ++projectLoadGeneration;
    const status = $("projectLibraryStatus");
    status.textContent = "กำลังอ่านท่าและเพลงของ " + item.title + "…";
    try {
      const response = await fetch(item.projectUrl, { cache: "no-store", signal: AbortSignal.timeout(15e3) });
      if (!response.ok) throw new Error("ไม่พบไฟล์ชุดงาน");
      const project = await response.json();
      if (generation !== projectLoadGeneration) return;
      const opened = await applyProjectData(project, item.id + ".json", { generation, imported: true });
      if (opened) {
        $("projectLibrary").close();
        showTab("sequence");
      }
    } catch (e) {
      if (generation === projectLoadGeneration) status.textContent = e.message + " — งานเดิมยังอยู่";
    }
  }
  async importFile(file) {
    if (!file) return;
    const generation = ++projectLoadGeneration;
    try {
      if (file.size > 48 * 1024 * 1024) throw new Error("ไฟล์ใหญ่เกิน 48 MB");
      const project = JSON.parse(await file.text());
      if (generation !== projectLoadGeneration) return;
      const opened = await applyProjectData(project, file.name.replace(/\.nong\.json$/i, ".json"), { generation, imported: true });
      if (opened) {
        if ($("projectLibrary").open) $("projectLibrary").close();
        showTab("sequence");
      }
    } catch (e) {
      if (generation === projectLoadGeneration) notice("เปิดไฟล์ไม่ได้: " + e.message + " งานเดิมยังอยู่");
    }
  }
  downloadProject() {
    const blob = new Blob([JSON.stringify(projectSnapshot(), null, 1)], { type: "application/json" });
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url;
    link.download = cleanName($("projName").value || "my_move") + ".nong.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1e3);
  }
}
const projectLibrary = new StudioProjectLibrary();
window.StudioProjectLibrary = StudioProjectLibrary;
function projectSnapshot() {
  return {
    sourceAudioAsset: typeof sequenceAudio !== "undefined" ? sequenceAudio.serializable() : null,
    keys,
    speedDps: speedDps(),
    maxDps: maxDps(),
    loop: $("loopChk").checked,
    // The planning peak limit rides with the project: without it, reopening a
    // project re-times every automatic move against a different 60 °/s default
    // and the show quietly got slower (A31-4).
    safeDps: SAFE_DPS,
    musicDps: SEQ_MUSIC_DPS,
    // speed limit with music, this sequence only (A48-23)
    meshes: meshCfg,
    addons,
    robotIp: $("robotIp").value,
    seqName: $("projName").value,
    // kept: older Studios read it
    // The chain is part of the show: a project saved with one and reopened
    // without it exported a different sequence than the one saved.
    seqNext: ($("seqNext").value || "").trim(),
    rig: RIG,
    // The video the moves were made from, and how (A44-8); null if none.
    video: vidSettings()
  };
}
async function saveProject(opts) {
  if (typeof sequenceAudio !== "undefined" && !sequenceAudio.readyForSave()) return false;
  opts = opts || {};
  const name = ($("projName").value || "project").trim();
  const sig = workSig();
  const project = projectSnapshot();
  const a = await Mice.Api.post("/api/save", { name, project });
  if (!a.ok) {
    $("tlStat").textContent = a.status ? "could not save: " + String(a.says).replace(/[.\s]+$/, "") + ". Your work is still here." : "could not save — the hub is not answering. Your work is still here, and is kept in this browser.";
    notice($("tlStat").textContent);
    return false;
  }
  const r = a.data;
  if (!opts.keepDraft) markSaved(sig, name);
  $("tlStat").textContent = r.replaced ? "saved over the existing " + r.file + " (the previous version is kept as " + r.file + ".bak)" : "project saved: " + r.file;
  refreshProjects();
  return true;
}
let projectLoadGeneration = 0;
async function loadProject(file) {
  if (!file) return;
  const generation = ++projectLoadGeneration;
  const a = await Mice.Api.get("/api/load?name=" + encodeURIComponent(file));
  if (generation !== projectLoadGeneration) return;
  if (!a.ok) {
    $("tlStat").textContent = "could not load " + file + " — " + String(a.says).replace(/[.\s]+$/, "") + ". Nothing on screen was changed.";
    notice($("tlStat").textContent);
    return;
  }
  try {
    return await applyProjectData(a.data, file, { generation });
  } catch (e) {
    if (generation === projectLoadGeneration) notice("เปิดโปรเจกต์ไม่ได้: " + e.message + " งานเดิมยังอยู่");
  }
}
async function applyProjectData(p, file, opts = {}) {
  const generation = opts.generation == null ? ++projectLoadGeneration : opts.generation;
  if (!p || !Array.isArray(p.keys) || p.keys.length && !p.keys.some((k) => k && Array.isArray(k.pose) && k.pose.some((v) => Number.isFinite(Number(v)))))
    throw new Error("ไฟล์ไม่มีท่าที่อ่านได้");
  for (const field of ["seqName", "seqNext", "robotIp"])
    if (p[field] != null && typeof p[field] !== "string") throw new Error("ข้อมูล " + field + " ไม่ถูกต้อง");
  if (p.addons != null && !Array.isArray(p.addons)) throw new Error("ข้อมูล addons ไม่ถูกต้อง");
  for (const field of ["rig", "meshes", "video"])
    if (p[field] != null && (typeof p[field] !== "object" || Array.isArray(p[field]))) throw new Error("ข้อมูล " + field + " ไม่ถูกต้อง");
  for (const key of p.keys) for (const field of ["cues", "cuesAfter"])
    if (key && key[field] != null && (!Array.isArray(key[field]) || key[field].some((v) => typeof v !== "string")))
      throw new Error("ข้อมูลคำสั่งในคีย์ไม่ถูกต้อง");
  const preparedAudio = typeof sequenceAudio !== "undefined" ? await sequenceAudio.prepare(p.sourceAudioAsset) : null;
  await refreshModels();
  if (generation !== projectLoadGeneration) return false;
  if (typeof sequenceAudio !== "undefined" && sequenceAudio.pendingRef && preparedAudio && sequenceAudio.pendingRef.sha256 === preparedAudio.asset.sha256 && confirm("พบเพลงที่ตรงกับงานกู้คืน ใช้เพลงนี้กับท่าที่แก้ค้างไว้หรือไม่?\n\nOK — กู้เฉพาะเพลงและเก็บท่าปัจจุบันทั้งหมด\nCancel — เปิดโปรเจกต์ตามปกติ")) {
    sequenceAudio.commit(preparedAudio, keys);
    saveDraft();
    notice("กู้เพลงกลับแล้ว ท่าที่แก้ค้างไว้ยังอยู่ กด Save เพื่อเก็บงาน");
    return true;
  }
  if (timelinePreparing) throw new Error("กำลังตรวจเส้นทาง กดหยุดตรวจให้เสร็จก่อนเปิดโปรเจกต์ใหม่");
  if (!await askUnsaved("open " + file)) {
    if ($("projList")) $("projList").value = "";
    return false;
  }
  if (generation !== projectLoadGeneration) return false;
  if (playing && !previewOnly) throw new Error("หยุดการเล่นท่าปัจจุบันก่อนเปิดโปรเจกต์ใหม่");
  if (playing) {
    playing = false;
    keepAwake(false);
    $("playBtn").textContent = "▶ Play";
  }
  let takeRig = false;
  if (p.rig) {
    takeRig = confirm(
      "This project was saved with its own robot setup (joint limits, gears, pulse ranges, zero offsets).\n\nOK  — use the project's setup\nCancel — keep the setup you have now (recommended)"
    );
  }
  if (p.rig && takeRig) {
    try {
      localStorage.setItem("nong_rig_prev", JSON.stringify(RIG));
    } catch (e) {
    }
    RIG = mergeRig(p.rig);
    saveRig();
  }
  const loaded = p.keys.filter((k) => k && Array.isArray(k.pose)).map((k) => {
    const q = k.pose.slice(0, NJ).map(Number);
    while (q.length < NJ) q.push(90);
    const t = Number(k.t), hold = Number(k.hold);
    return {
      ...k,
      pose: q.map((v, i) => clampJ(i, Number.isFinite(v) ? v : 90)),
      t: Number.isFinite(t) ? Math.max(0, Math.round(t)) : 0,
      hold: Number.isFinite(hold) ? Math.max(0, Math.round(hold)) : 0
    };
  });
  if (typeof sequenceAudio !== "undefined") sequenceAudio.commit(preparedAudio, loaded);
  keys = loaded;
  bumpKeys();
  timelineUndo.reset();
  $("speedDps").value = p.speedDps || 120;
  $("maxDps").value = p.maxDps || 400;
  SEQ_MUSIC_DPS = Number.isFinite(p.musicDps) && p.musicDps >= 0 ? p.musicDps : null;
  if (p.safeDps >= 5 && !boardSafeDpsMax) {
    SAFE_DPS = Math.round(p.safeDps);
    $("safeDpsInput").value = String(SAFE_DPS);
  }
  clampKeyTimes();
  $("loopChk").checked = !!p.loop;
  $("robotIp").value = p.robotIp || "";
  const pname = file.replace(/\.json$/, "");
  const oldSeq = (p.seqName || "").trim();
  setWorkName(pname);
  $("seqNext").value = p.seqNext || "";
  vidApplySettings(p.video);
  if (p.meshes) {
    MESH_PARTS.forEach((part) => {
      const v = p.meshes[part];
      if (v === void 0) return;
      meshCfg[part] = typeof v === "string" ? { ...defMeshCfg(part), file: v, scale: p.stlScale || 1 } : { ...defMeshCfg(part), ...v };
    });
  }
  addons = p.addons || addons;
  saveMeshes();
  const openedSig = workSig();
  if (generation !== projectLoadGeneration) return false;
  renderRigUI();
  buildRobot();
  selKey = 0;
  if (keys.length) {
    pose = [...keys[0].pose];
  }
  poseChanged(false, 0, { previewOnly: true });
  renderTimeline();
  if (opts.imported) {
    markClean("", "");
    loadedSkipped = 0;
    saveDraft();
  } else markSaved(openedSig, oldSeq === pname ? pname : "", 0);
  if (oldSeq && oldSeq !== pname)
    $("tlStat").textContent = "opened " + file + ". It used to save its moves as " + oldSeq + ".yaml; Save now writes " + pname + ".json and " + pname + ".yaml together.";
  if (opts.imported) $("tlStat").textContent = "เปิดท่าและเพลงแล้ว — กด Save เพื่อเก็บเป็นงานของคุณ";
  return true;
}
let savedSig = null;
let savedName = "";
let loadedSkipped = 0;
function workSig() {
  return keysSignature() + "|" + ($("loopChk") && $("loopChk").checked ? 1 : 0) + "|" + ($("seqNext") && $("seqNext").value || "").trim() + "|" + (typeof sequenceAudio !== "undefined" ? sequenceAudio.signature() : "");
}
function markClean(sig, name) {
  savedSig = sig;
  if (name != null) savedName = name;
}
function markSaved(sig, name, skipped) {
  markClean(sig, name);
  if (skipped != null) loadedSkipped = skipped;
  try {
    if (workSig() === sig) localStorage.removeItem(DRAFT_KEY);
  } catch (e) {
  }
}
function isDirty() {
  if (savedSig === null || !keys.length) return false;
  return workSig() !== savedSig;
}
const ASK_UNSAVED_KEY = "nong_ask_unsaved";
function askUnsavedOn() {
  try {
    return localStorage.getItem(ASK_UNSAVED_KEY) !== "0";
  } catch (e) {
    return true;
  }
}
function setAskUnsaved(on) {
  try {
    localStorage.setItem(ASK_UNSAVED_KEY, on ? "1" : "0");
  } catch (e) {
  }
}
function cleanName(v) {
  return (v || "").trim().replace(/[^\w.-]+/g, "_");
}
function setWorkName(v) {
  const n = cleanName(v);
  if ($("projName")) $("projName").value = n;
}
async function savedNamesNow(kind) {
  const a = await Mice.Api.get("/api/list?kind=" + kind);
  return a.ok && a.data && Array.isArray(a.data.files) ? a.data.files : [];
}
async function saveAll() {
  if (typeof sequenceAudio !== "undefined" && !sequenceAudio.readyForSave()) return false;
  const name = cleanName($("projName").value || "my_move");
  setWorkName(name);
  const sig = workSig();
  const writeYaml = playKeys().length > 0;
  const have = [...$("seqList").options].map((o) => o.value);
  let clash = "";
  if (name !== savedName) {
    const [ys, ps] = await Promise.all([savedNamesNow("sequences"), savedNamesNow("projects")]);
    if (writeYaml && (have.includes(name + ".yaml") || ys.includes(name + ".yaml"))) clash = name + ".yaml";
    else if (ps.includes(name + ".json")) clash = name + ".json";
  }
  if (clash && !confirm(clash + " is already saved. Replace it?\n\nCancel, then type a new name to keep both.")) {
    $("tlStat").textContent = "not saved — " + clash + " was left as it was";
    return false;
  }
  if (writeYaml && name === savedName && loadedSkipped > 0 && !confirm(name + ".yaml has " + loadedSkipped + " step(s) this editor cannot read. Saving over it removes them.\n\nOK — save anyway\nCancel — keep the file; type a new name to save a copy")) {
    $("tlStat").textContent = "not saved — " + name + ".yaml was left as it was";
    return false;
  }
  const boxes = [$("projName")].filter(Boolean);
  boxes.forEach((b) => {
    b.readOnly = true;
  });
  let ok = false;
  try {
    ok = await saveProject({ keepDraft: true }) && (!writeYaml || await exportYaml({ noAsk: true, keepDraft: true }));
  } finally {
    boxes.forEach((b) => {
      b.readOnly = false;
    });
  }
  if (!ok) return false;
  markSaved(sig, name, 0);
  $("tlStat").textContent = "saved " + name + " — " + name + ".json (to edit later)" + (writeYaml ? " and " + name + ".yaml (what the robot plays)" : ". No .yaml: every move is suspended, so there is nothing to play");
  return true;
}
function askUnsaved(what) {
  if (!askUnsavedOn() || !isDirty()) return Promise.resolve(true);
  return new Promise((resolve) => {
    let dlg = $("unsavedDlg");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.id = "unsavedDlg";
      dlg.className = "askdlg";
      dlg.setAttribute("aria-labelledby", "unsavedTitle");
      dlg.innerHTML = '<h2 id="unsavedTitle">Save your changes first?</h2><p class="mini" id="unsavedText"></p><div class="row"><button class="primary" id="unsavedSave">Save, then continue</button><button class="danger" id="unsavedDrop">Don’t save</button><button id="unsavedCancel">Cancel</button></div>';
      document.body.appendChild(dlg);
    }
    $("unsavedText").textContent = "The moves on the time bar have changes that are not saved" + (savedName ? " to " + savedName : "") + ". If you " + what + " now, they are replaced.";
    const done = async (how) => {
      dlg.close();
      resolve(how === "save" ? await saveAll() : how === "drop");
    };
    $("unsavedSave").onclick = () => done("save");
    $("unsavedDrop").onclick = () => done("drop");
    $("unsavedCancel").onclick = () => done("cancel");
    dlg.oncancel = (e) => {
      e.preventDefault();
      done("cancel");
    };
    dlg.showModal();
    $("unsavedCancel").focus();
  });
}
function syncAskUnsavedBox() {
  const box = $("askUnsavedChk");
  if (box) box.checked = askUnsavedOn();
}
syncAskUnsavedBox();
async function refreshProjects() {
  const a = await Mice.Api.get("/api/list?kind=projects");
  const retry = $("projRetry");
  if (retry) retry.hidden = a.ok;
  if (!a.ok) {
    $("tlStat").textContent = "Could not read saved moves. Your choices are kept. Press Retry saved moves.";
    notice($("tlStat").textContent);
    return;
  }
  const r = a.data;
  const sel = $("projList");
  sel.innerHTML = "<option value=''>Load…</option>";
  (r.files || []).forEach((f) => {
    const o = document.createElement("option");
    o.value = o.textContent = f;
    sel.appendChild(o);
  });
}
const headStat = new Mice.Status("stat");
let headSaid = "";
function showSaveState() {
  let kind, says, tech = "";
  if (savedSig === null) {
    kind = "loading";
    says = "opening…";
  } else if (isDirty()) {
    kind = "warn";
    says = "not saved";
  } else if (savedName) {
    kind = "ready";
    says = "saved";
    tech = savedName + ".json + " + savedName + ".yaml";
  } else {
    kind = "empty";
    says = keys.length > 1 ? "not saved" : "nothing to save yet";
  }
  const now = kind + says + tech;
  if (now === headSaid) return;
  headSaid = now;
  headStat[kind](says, tech);
}
showSaveState();
setInterval(showSaveState, 1e3);
class TimelineUndo {
  constructor() {
    this.MAX = 60;
    this.COALESCE_MS = 700;
    this.past = [];
    this.future = [];
    this.last = null;
    this.lastLen = 0;
    this.lastAt = 0;
    this.busy = false;
  }
  snap() {
    return JSON.stringify(keys);
  }
  seed() {
    if (this.last === null) {
      this.last = this.snap();
      this.lastLen = keys.length;
    }
  }
  reset() {
    this.past = [];
    this.future = [];
    this.last = this.snap();
    this.lastLen = keys.length;
    this.refresh();
  }
  changed() {
    if (this.busy) return;
    const now = this.snap();
    if (this.last === null || now === this.last) {
      this.last = now;
      this.lastLen = keys.length;
      return;
    }
    const t = Date.now();
    const sameStep = this.past.length && keys.length === this.lastLen && t - this.lastAt < this.COALESCE_MS;
    if (!sameStep) {
      this.past.push(this.last);
      if (this.past.length > this.MAX) this.past.shift();
    }
    this.future = [];
    this.last = now;
    this.lastLen = keys.length;
    this.lastAt = t;
    this.refresh();
  }
  undo() {
    if (this.past.length) {
      this.future.push(this.snap());
      this.apply(this.past.pop());
    }
  }
  redo() {
    if (this.future.length) {
      this.past.push(this.snap());
      this.apply(this.future.pop());
    }
  }
  apply(snapshot) {
    const before = keys;
    this.busy = true;
    try {
      keys = JSON.parse(snapshot);
      this.last = snapshot;
      this.lastLen = keys.length;
      this.lastAt = 0;
      let at = 0;
      while (at < keys.length - 1 && before[at] && JSON.stringify(before[at]) === JSON.stringify(keys[at])) at++;
      selKey = Math.max(0, Math.min(at, keys.length - 1));
      clearBadMarks();
      bumpKeys();
      renderTimeline();
      if (keys.length) selectKey(selKey);
    } finally {
      this.busy = false;
    }
    this.refresh();
  }
  refresh() {
    const u = $("undoBtn"), r = $("redoBtn");
    if (u) u.disabled = !this.past.length;
    if (r) r.disabled = !this.future.length;
  }
}
var timelineUndo = new TimelineUndo();
window.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
  const t = e.target, tag = t && t.tagName;
  if (tag === "TEXTAREA" || tag === "SELECT" || tag === "INPUT" && !/^(range|checkbox|button)$/.test(t.type)) return;
  const k = e.key.toLowerCase();
  if (k === "z" && !e.shiftKey) timelineUndo.undo();
  else if (k === "y" || k === "z" && e.shiftKey) timelineUndo.redo();
  else return;
  e.preventDefault();
});
if (window.miceTheme) miceTheme.picker($("themePick"));
if (window.miceTheme) miceTheme.onChange(() => {
  scene.background = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim());
  markDirty3d();
});
const stlLoader = new THREE.STLLoader();
const stlCache = {};
let meshGen = 0;
const PART_PAIR = { L_upper: 0, L_fore: 1, R_upper: 2, R_fore: 3 };
function getGeo(file, cb) {
  if (stlCache[file]) {
    cb(stlCache[file]);
    return;
  }
  stlLoader.load(
    "/models/" + encodeURIComponent(file),
    (geo) => {
      stlCache[file] = geo;
      cb(geo);
    },
    void 0,
    () => {
      $("tlStat").textContent = "cannot load models/" + file;
      notice($("tlStat").textContent);
    }
  );
}
function ensureUVs(geo) {
  if (geo.attributes.uv) return geo;
  geo.computeBoundingBox();
  const bb = geo.boundingBox, size = new THREE.Vector3();
  bb.getSize(size);
  const comps = ["x", "y", "z"].sort((a, b) => size[b] - size[a]);
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
    color: tex ? "#ffffff" : cfg.color || "#8a94a6",
    map: tex || null,
    roughness: 0.65
  });
  const m = new THREE.Mesh(geo, mat);
  const r = cfg.rot || [0, 0, 0], o = cfg.off || [0, 0, 0];
  m.rotation.set(
    THREE.MathUtils.degToRad(+r[0] || 0),
    THREE.MathUtils.degToRad(+r[1] || 0),
    THREE.MathUtils.degToRad(+r[2] || 0)
  );
  m.position.set(+o[0] || 0, +o[1] || 0, +o[2] || 0);
  m.scale.setScalar(+cfg.scale || 1);
  const pair = PART_PAIR[part];
  if (pair !== void 0) {
    m.userData.pair = pair;
    pickMeshes.push(m);
  }
  return m;
}
function applyMeshes() {
  if (typeof markDirty3d === "function") markDirty3d(5);
  const gen = ++meshGen;
  MESH_PARTS.forEach((part) => {
    const cfg = meshCfg[part];
    const holder = linkHolders[part];
    if (!holder) return;
    holder.children[0].traverse((o) => {
      if (o.isMesh && !o.userData.skel) o.visible = !cfg.file;
    });
    while (holder.children.length > 1) holder.remove(holder.children[holder.children.length - 1]);
    if (cfg.file) getGeo(cfg.file, (geo) => {
      if (gen !== meshGen || linkHolders[part] !== holder) return;
      holder.add(cfgMesh(geo, cfg, part));
      if (typeof markDirty3d === "function") markDirty3d(5);
    });
  });
  addons.forEach((ad) => {
    const holder = linkHolders[ad.part];
    if (!holder || !ad.file) return;
    getGeo(ad.file, (geo) => {
      if (gen !== meshGen || linkHolders[ad.part] !== holder) return;
      holder.add(cfgMesh(geo, ad, ad.part));
      if (typeof markDirty3d === "function") markDirty3d(5);
    });
  });
}
function measureFromStl(part) {
  const cfg = meshCfg[part];
  if (!cfg.file) return;
  getGeo(cfg.file, (geo) => {
    const g = geo.clone();
    const r = cfg.rot || [0, 0, 0];
    g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(
      THREE.MathUtils.degToRad(+r[0] || 0),
      THREE.MathUtils.degToRad(+r[1] || 0),
      THREE.MathUtils.degToRad(+r[2] || 0)
    )));
    g.computeBoundingBox();
    const size = new THREE.Vector3();
    g.boundingBox.getSize(size);
    size.multiplyScalar(+cfg.scale || 1);
    g.dispose();
    let msg = "";
    const rd = (v) => Math.max(5, Math.round(v));
    if (part === "L_upper") {
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
      RIG.dims.torsoW = rd(size.x);
      RIG.dims.torsoH = rd(size.y);
      RIG.dims.torsoD = rd(size.z);
      msg = `torso from the STL: ${RIG.dims.torsoW}×${RIG.dims.torsoH}×${RIG.dims.torsoD} mm`;
    }
    saveRig();
    renderRigUI();
    buildRobot();
    if (msg) $("tlStat").textContent = msg + " — fine-tune in Rig setup if needed";
  });
}
function revertDims(part) {
  const D = DEFAULT_RIG.dims;
  if (part === "L_upper") RIG.dims.upperLenL = D.upperLenL;
  else if (part === "R_upper") RIG.dims.upperLenR = D.upperLenR;
  else if (part === "L_fore") RIG.dims.foreLenL = D.foreLenL;
  else if (part === "R_fore") RIG.dims.foreLenR = D.foreLenR;
  else if (part === "torso") {
    RIG.dims.torsoW = D.torsoW;
    RIG.dims.torsoH = D.torsoH;
    RIG.dims.torsoD = D.torsoD;
  } else return;
  saveRig();
  renderRigUI();
}
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
    inp.type = "number";
    inp.step = step;
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
  sc.type = "number";
  sc.step = 0.1;
  sc.min = 0.01;
  sc.value = cfg.scale || 1;
  sc.onchange = () => {
    cfg.scale = +sc.value || 1;
    onchange();
  };
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
  modelFiles.filter(isStl).forEach((f) => {
    const o = document.createElement("option");
    o.value = o.textContent = f;
    if (cfg.file === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => {
    cfg.file = sel.value;
    onpick();
  };
  return sel;
}
function texSelect(cfg, onpick) {
  const sel = document.createElement("select");
  sel.style.flex = "1";
  sel.title = "texture image (draw it in any paint program, Import it, pick it here)";
  sel.innerHTML = "<option value=''>(no texture)</option>";
  modelFiles.filter(isImg).forEach((f) => {
    const o = document.createElement("option");
    o.value = o.textContent = f;
    if (cfg.tex === f) o.selected = true;
    sel.appendChild(o);
  });
  sel.onchange = () => {
    cfg.tex = sel.value;
    onpick();
  };
  return sel;
}
function renderModelsUI() {
  const box = $("meshAssign");
  box.innerHTML = "";
  MESH_PARTS.forEach((part) => {
    const cfg = meshCfg[part];
    const row = document.createElement("div");
    row.className = "row";
    const lbl = document.createElement("span");
    lbl.className = "lbl";
    lbl.textContent = part;
    const sel = fileSelect(cfg, () => {
      saveMeshes();
      renderModelsUI();
      if (cfg.file) measureFromStl(part);
      else {
        revertDims(part);
        buildRobot();
      }
    });
    const col = document.createElement("input");
    col.type = "color";
    col.value = cfg.color || "#8a94a6";
    col.title = "color of this part (ignored while a texture is set)";
    col.onchange = () => {
      cfg.color = col.value;
      saveMeshes();
      buildRobot();
    };
    row.append(lbl, sel, col);
    box.appendChild(row);
    const texRow = document.createElement("div");
    texRow.className = "row";
    const texLbl = document.createElement("span");
    texLbl.className = "lbl";
    texLbl.textContent = "└ texture";
    texRow.append(texLbl, texSelect(cfg, () => {
      saveMeshes();
      buildRobot();
    }));
    box.appendChild(texRow);
    if (cfg.file) {
      const sub = document.createElement("div");
      sub.style.margin = "0 0 8px 12px";
      transformRows(cfg, sub, () => {
        saveMeshes();
        measureFromStl(part);
      });
      box.appendChild(sub);
    }
  });
  renderAddonsUI();
}
function renderAddonsUI() {
  const box = $("addonList");
  box.innerHTML = "";
  addons.forEach((ad, i) => {
    const row = document.createElement("div");
    row.className = "row";
    const sel = fileSelect(ad, () => {
      saveMeshes();
      buildRobot();
    });
    const at = document.createElement("select");
    MESH_PARTS.forEach((p) => {
      const o = document.createElement("option");
      o.value = o.textContent = p;
      if (ad.part === p) o.selected = true;
      at.appendChild(o);
    });
    at.title = "which body part this piece follows";
    at.onchange = () => {
      ad.part = at.value;
      saveMeshes();
      buildRobot();
    };
    const col = document.createElement("input");
    col.type = "color";
    col.value = ad.color || "#7a5cc4";
    col.onchange = () => {
      ad.color = col.value;
      saveMeshes();
      buildRobot();
    };
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => {
      addons.splice(i, 1);
      saveMeshes();
      renderModelsUI();
      buildRobot();
    };
    row.append(sel, at, col, del);
    box.appendChild(row);
    const sub = document.createElement("div");
    sub.style.margin = "0 0 8px 12px";
    transformRows(ad, sub, () => {
      saveMeshes();
      buildRobot();
    });
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
  if (!f) {
    alert("choose a file first: .stl shape (mm) or a painted .png/.jpg texture");
    return;
  }
  const r = await fetch("/api/model/upload?name=" + encodeURIComponent(f.name), {
    method: "POST",
    body: await f.arrayBuffer()
  }).then((r2) => r2.json());
  if (!r.ok) {
    alert("import failed: " + r.error);
    return;
  }
  delete stlCache[r.file];
  delete texCache[r.file];
  await refreshModels();
  $("tlStat").textContent = "imported " + r.file + " — assign it below (" + (isImg(r.file) ? "as a texture on a part" : "as a body part or add-on") + ")";
}
async function refreshModels() {
  const r = await fetch("/api/list?kind=models").then((r2) => r2.json());
  modelFiles = (r.files || []).filter((f) => isStl(f) || isImg(f));
  renderModelsUI();
}
const URDF_DEF = { mm: 1e3, up: "z" };
let urdfDoc = null;
let urdfMap = {};
let urdfName = "";
const URDF_GUESS = [
  [/(^|[_\- ])(l|left)([_\- ]|$).*(upper|shoulder|humerus)/i, "L_upper"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(upper|shoulder|humerus)/i, "R_upper"],
  [/(^|[_\- ])(l|left)([_\- ]|$).*(fore|lower|elbow|radius)/i, "L_fore"],
  [/(^|[_\- ])(r|right)([_\- ]|$).*(fore|lower|elbow|radius)/i, "R_fore"],
  [/head|skull|face/i, "head"],
  [/torso|body|chest|trunk|base/i, "torso"]
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
function urdfToStudioXYZ(v, up) {
  return up === "y" ? [v[0], v[1], v[2]] : [v[1], v[2], v[0]];
}
function urdfToStudioRPY(rpy, up) {
  const s = urdfToStudioXYZ(rpy, up);
  return s.map((r) => Math.round(THREE.MathUtils.radToDeg(r) * 10) / 10);
}
function urdfVisual(link, opt) {
  const vis = link.querySelector("visual");
  const mesh = vis && vis.querySelector("geometry mesh");
  if (!mesh) return null;
  const file = (mesh.getAttribute("filename") || "").split(/[\\/]/).pop();
  if (!file) return null;
  const org = vis.querySelector("origin");
  const off = urdfToStudioXYZ(urdfNums(org, "xyz", [0, 0, 0]), opt.up).map((v) => Math.round(v * opt.mm * 10) / 10);
  const rot = urdfToStudioRPY(urdfNums(org, "rpy", [0, 0, 0]), opt.up);
  const ms = urdfNums(mesh, "scale", [1, 1, 1]);
  const even = Math.abs(ms[0] - ms[1]) < 1e-9 && Math.abs(ms[1] - ms[2]) < 1e-9;
  return { file, off, rot, scale: ms[0] * opt.mm, even };
}
function urdfParse(text) {
  const doc = new DOMParser().parseFromString(text, "application/xml");
  if (doc.querySelector("parsererror"))
    throw new Error("this file is not valid XML, so it cannot be a URDF");
  const robot2 = doc.querySelector("robot");
  if (!robot2) throw new Error("no <robot> in this file - is it a URDF?");
  const links = [...doc.querySelectorAll("robot > link")];
  if (!links.length) throw new Error("this URDF has no links in it");
  return {
    doc,
    robot: robot2,
    links,
    joints: [...doc.querySelectorAll("robot > joint")]
  };
}
function urdfJointLengths(parsed, opt) {
  const out = {};
  parsed.joints.forEach((j) => {
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
async function importUrdf() {
  const f = $("urdfFile").files[0];
  if (!f) {
    $("urdfStat").textContent = "choose a .urdf file first. Its .stl meshes must be imported too (Models > Import), or the parts have nothing to draw.";
    return;
  }
  try {
    const parsed = urdfParse(await f.text());
    urdfDoc = parsed;
    urdfName = f.name;
    urdfMap = {};
    parsed.links.forEach((l) => {
      const name = l.getAttribute("name") || "";
      urdfMap[name] = urdfGuessPart(name);
    });
    renderUrdfUI();
    const matched = Object.values(urdfMap).filter(Boolean).length;
    $("urdfStat").textContent = `${f.name}: ${parsed.links.length} links, ${parsed.joints.length} joints. ${matched} matched to a body part by name — check them below, then press Use this URDF.`;
  } catch (e) {
    Mice.fail($("urdfStat"), "could not read it", e);
    notice($("urdfStat").textContent);
  }
}
function urdfOptions() {
  return {
    mm: +$("urdfMm").value || URDF_DEF.mm,
    up: $("urdfUp").value || URDF_DEF.up
  };
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
  urdfDoc.links.forEach((l) => {
    const name = l.getAttribute("name") || "";
    const vis = urdfVisual(l, opt);
    const row = document.createElement("div");
    row.className = "row";
    const nm = document.createElement("span");
    nm.style.flex = "1";
    nm.textContent = name;
    nm.title = vis ? "mesh: " + vis.file : "this link has no mesh to draw";
    const sel = document.createElement("select");
    sel.innerHTML = "<option value=''>(not used)</option>";
    MESH_PARTS.forEach((p) => {
      const o = document.createElement("option");
      o.value = o.textContent = p;
      if (urdfMap[name] === p) o.selected = true;
      sel.appendChild(o);
    });
    sel.disabled = !vis;
    sel.onchange = () => {
      urdfMap[name] = sel.value;
    };
    const note = document.createElement("span");
    note.className = "mini";
    note.textContent = vis ? vis.even ? vis.file : vis.file + " ⚠ uneven scale" : "no mesh";
    row.append(nm, sel, note);
    box.appendChild(row);
  });
}
function useUrdf() {
  if (!urdfDoc) {
    $("urdfStat").textContent = "load a .urdf file first.";
    return;
  }
  const opt = urdfOptions();
  const done = [], missing = [], uneven = [];
  urdfDoc.links.forEach((l) => {
    const name = l.getAttribute("name") || "";
    const part = urdfMap[name];
    if (!part) return;
    const vis = urdfVisual(l, opt);
    if (!vis) return;
    if (!vis.even) uneven.push(vis.file);
    if (!modelFiles.some((f) => f.toLowerCase() === vis.file.toLowerCase()))
      missing.push(vis.file);
    meshCfg[part] = {
      ...defMeshCfg(part),
      file: vis.file,
      rot: vis.rot,
      off: vis.off,
      scale: vis.scale,
      color: meshCfg[part].color
    };
    done.push(part);
  });
  if (!done.length) {
    $("urdfStat").textContent = "nothing was changed: no link is matched to a body part yet. Pick a part beside a link above.";
    return;
  }
  const lens = urdfJointLengths(urdfDoc, opt);
  const dimOf = {
    L_upper: "upperLenL",
    R_upper: "upperLenR",
    L_fore: "foreLenL",
    R_fore: "foreLenR"
  };
  const offer = Object.keys(lens).filter((p) => dimOf[p] && lens[p] > 1);
  let sized = 0;
  if (offer.length && confirm(
    "Also set the arm lengths from this URDF?\n\n" + offer.map((p) => "  " + dimOf[p] + ": " + RIG.dims[dimOf[p]] + " → " + lens[p] + " mm").join("\n") + "\n\nOK sets them. Cancel keeps the lengths you have."
  )) {
    offer.forEach((p) => {
      RIG.dims[dimOf[p]] = lens[p];
      sized++;
    });
  }
  saveMeshes();
  if (sized) rigChanged();
  else buildRobot();
  renderModelsUI();
  $("urdfStat").textContent = `${urdfName}: placed ${done.length} part(s) — ${done.join(", ")}` + (sized ? `, and set ${sized} arm length(s)` : "") + ". " + (missing.length ? `Import these meshes too (Models > Import): ${missing.join(", ")}. ` : "") + (uneven.length ? `${uneven.join(", ")} is scaled differently on each axis; this editor has one scale, so the first was used. ` : "") + "Nothing else in the rig was touched.";
}
function robotIp() {
  return $("robotIp").value.trim();
}
function transport() {
  return $("connSel").value;
}
function busId() {
  const v = $("busId").value.trim();
  return v ? parseInt(v, 10) : 0;
}
let serialPort = null;
let serialWaiters = [];
let hubPort = "";
function connModeChanged() {
  const t = transport(), usb = t === "usb", direct = t === "serial";
  $("robotIp").style.display = usb || direct ? "none" : "";
  $("busId").style.display = usb || direct ? "" : "none";
  $("usbPort").style.display = usb ? "" : "none";
  $("usbRescan").style.display = usb ? "" : "none";
  $("connBtn").textContent = direct && !serialPort ? "Connect USB" : "Connect";
  if (usb) {
    if (!$("usbPort").dataset.loaded) loadPorts();
  } else if (direct && !("serial" in navigator)) {
    $("robotStat").textContent = "This browser cannot open a USB port by itself. Pick “+ USB (shared)” instead — the hub opens the cable and shares it — or connect over WiFi. (Web Serial works in Chrome and Edge.)";
    notice($("robotStat").textContent);
  }
}
async function loadPorts(keepSel) {
  const sel = $("usbPort"), want = keepSel || sel.value;
  sel.innerHTML = "<option value=''>looking for USB ports…</option>";
  try {
    const r = await fetch("/api/ports").then((r2) => r2.json());
    const ps = (r.ports || []).filter((p) => !p.bt);
    sel.innerHTML = "<option value=''>pick the USB port…</option>";
    ps.forEach((p) => {
      const o = document.createElement("option");
      o.value = p.port;
      o.textContent = p.port + (p.who ? " — " + p.who : p.desc ? " — " + p.desc : "") + (p.inuse ? " · in use (shared)" : "");
      sel.appendChild(o);
    });
    if (!ps.length) sel.innerHTML = "<option value=''>no USB port found — cable plugged in?</option>";
    sel.dataset.loaded = "1";
    if (want && ps.some((p) => p.port === want)) sel.value = want;
    else if (ps.length === 1) sel.value = ps[0].port;
  } catch (e) {
    sel.innerHTML = "<option value=''>the port list needs the hub (python main.py)</option>";
  }
}
function usbPortChanged() {
  if (hubPort && hubPort !== $("usbPort").value) hubPort = "";
  $("robotStat").textContent = linkBadge();
}
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
    $("limMismatchText").textContent = diff.length ? "Studio and the robot allow different joint angles, so the arm will not match the preview. " + diff.join(" · ") : "";
  } catch (e) {
    box.hidden = true;
  }
}
async function findBusId(port) {
  for (const full of [0, 1]) {
    try {
      const r = await fetch(`/api/scanusb?full=${full}&port=` + encodeURIComponent(port)).then((r2) => r2.json());
      const u = (r.usb || [])[0] || {};
      if (u.module) return false;
      const nongs = (u.rs485 || []).filter((m) => m.type === "nong");
      if (!nongs.length) continue;
      $("busId").value = nongs[0].id;
      return true;
    } catch (e) {
      return false;
    }
  }
  return false;
}
const BUS_KEY = "nongBusId:";
function rememberBusId(port) {
  try {
    if (port) localStorage.setItem(BUS_KEY + port, String(busId() || ""));
  } catch (e) {
  }
}
function recallBusId(port) {
  if (busId() || !port) return;
  try {
    const v = localStorage.getItem(BUS_KEY + port);
    if (v) $("busId").value = v;
  } catch (e) {
  }
}
async function hubUsbCmd(c) {
  if (!hubPort && !(window.HUB_PEER || window.HUB_VIA))
    throw new Error("the USB link is closed - press Connect again");
  const url = window.HUB_PEER || window.HUB_VIA ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}&c=${encodeURIComponent(c)}` : `/api/usb/cmd?port=${encodeURIComponent(hubPort)}&id=${busId()}&c=${encodeURIComponent(c)}`;
  const r = await fetch(url, window.AbortSignal && AbortSignal.timeout ? { signal: AbortSignal.timeout(15e3) } : {});
  const t = await r.text();
  if (!r.ok) {
    let msg = t;
    try {
      msg = JSON.parse(t).error || t;
    } catch (e) {
    }
    throw new Error(msg);
  }
  return t.trim();
}
async function serialConnect() {
  if (!("serial" in navigator))
    throw new Error("no Web Serial here — USB works only in Chrome/Edge on the host PC at http://127.0.0.1:8642 (not from the LAN address or other devices); use WiFi mode instead");
  serialPort = await navigator.serial.requestPort();
  await serialPort.open({ baudRate: 115200 });
  try {
    await serialPort.setSignals({ dataTerminalReady: false, requestToSend: false });
  } catch (e) {
  }
  serialReadLoop();
  await new Promise((r) => setTimeout(r, 400));
}
async function serialReadLoop() {
  try {
    const decoder = new TextDecoderStream();
    serialPort.readable.pipeTo(decoder.writable).catch(() => {
    });
    const reader = decoder.readable.getReader();
    let buf = "";
    for (; ; ) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line || /^\[[\w ]*\]/.test(line)) continue;
        const w = serialWaiters[0];
        if (!w) continue;
        const out = w.filter(line);
        if (out !== null) {
          serialWaiters.shift();
          w.res(out);
        }
      }
    }
  } catch (e) {
  }
  serialPort = null;
  $("robotStat").textContent = "USB disconnected";
  notice($("robotStat").textContent);
}
let serialChain = Promise.resolve();
function serialCmd(c, connection = { port: serialPort, id: busId() }) {
  const epoch = safeMotionEpoch;
  const run = serialChain.then(() => /^POSE\s/i.test(c) && epoch !== safeMotionEpoch ? "ERR movement cancelled" : serialCmdNow(c, connection));
  serialChain = run.catch(() => {
  });
  return run;
}
function serialCmdNow(c, connection = { port: serialPort, id: busId() }) {
  return new Promise((res, rej) => {
    const port = connection.port;
    if (!port || !port.writable) return rej(new Error("USB not connected"));
    const id = connection.id;
    const filter = id ? (line) => line.startsWith("@" + id + " ") ? line.slice(String(id).length + 2) : null : (line) => line;
    const w = { filter, res, rej };
    serialWaiters.push(w);
    setTimeout(() => {
      const k = serialWaiters.indexOf(w);
      if (k >= 0) {
        serialWaiters.splice(k, 1);
        rej(new Error("timeout (bus id right?)"));
      }
    }, 2500);
    const framed = id ? "#" + id + " " + c : c;
    const drop = (e) => {
      const k = serialWaiters.indexOf(w);
      if (k >= 0) serialWaiters.splice(k, 1);
      rej(e);
    };
    try {
      const writer = port.writable.getWriter();
      writer.write(new TextEncoder().encode(framed + "\n")).catch(drop).finally(() => writer.releaseLock());
    } catch (e) {
      drop(e);
    }
  });
}
function usbDirect() {
  return !!(serialPort && serialPort.writable);
}
function haveUsb() {
  return usbDirect() || !!hubPort;
}
function haveWifi() {
  return !!robotIp();
}
function haveAuto() {
  return !!window.HUB_AUTO;
}
function haveRobot() {
  return haveAuto() || haveUsb() || haveWifi();
}
function cableCmd(c) {
  return usbDirect() ? serialCmd(c) : hubUsbCmd(c);
}
async function autoFetch(what, params, options) {
  const q = new URLSearchParams(Object.assign({ dev: window.HUB_AUTO }, params || {}));
  const r = await fetch(`/api/dev/${what}?${q}`, options);
  if (!r.ok) {
    const body = await r.text();
    let msg = body;
    try {
      msg = JSON.parse(body).error || body;
    } catch (e) {
    }
    throw new Error(msg);
  }
  return r;
}
async function autoCmd(c) {
  return (await (await autoFetch("cmd", { c })).text()).trim();
}
async function httpCmd(c) {
  const url = window.HUB_PEER || window.HUB_VIA ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}&c=${encodeURIComponent(c)}` : `/api/robot/cmd?ip=${encodeURIComponent(robotIp())}&c=${encodeURIComponent(c)}`;
  return fetch(url).then((r) => r.text());
}
async function rawCmd(c) {
  if (haveAuto()) return autoCmd(c);
  if (haveUsb()) return cableCmd(c);
  if (haveWifi()) return httpCmd(c);
  throw new Error("connect first — 🔍 Find modules (WiFi) or pick a USB port");
}
function moduleDev() {
  if (haveAuto()) return window.HUB_AUTO;
  const at = window.HUB_PEER ? "@" + window.HUB_PEER : "";
  const via = window.HUB_VIA || "";
  if (hubPort) return via + "usb:" + hubPort + (busId() ? ":" + busId() : "") + at;
  if (haveWifi()) return via + "wifi:" + robotIp() + at;
  return "";
}
window.addEventListener("DOMContentLoaded", function() {
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
    window.open("/mod?dev=" + encodeURIComponent(dev), "_blank");
    return;
  }
  if (usbDirect()) {
    $("robotStat").textContent = "direct Web Serial owns this cable, so the module site cannot share it — switch the link to “+ USB (shared)” and connect again, then this button works with both open at once.";
    notice($("robotStat").textContent);
    return;
  }
  $("robotStat").textContent = "connect first — pick a USB port or find a module on WiFi";
  notice($("robotStat").textContent);
}
async function robotCmd(c) {
  if (!currentUser) return "";
  if (/^POSE\s/i.test(c)) return await liveSend(c) ? "OK checked movement finished" : "";
  if (/^(?:MOVE\s+)?STOP\s*$/i.test(c)) {
    await cancelSafeMotion("Stop");
    return "OK stopped";
  }
  try {
    const t = await rawCmd(c);
    $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + t.slice(0, 120);
    return t;
  } catch (e) {
    Mice.fail($("robotStat"), "", e);
    return "";
  }
}
async function getStatus() {
  if (haveAuto()) return (await autoFetch("status")).json();
  if (haveUsb()) {
    try {
      return JSON.parse(await cableCmd("INFO"));
    } catch (e) {
      if (!/restart|JSON|Unexpected/i.test(e.message || "")) throw e;
      return JSON.parse(await cableCmd("INFO"));
    }
  }
  if (haveWifi())
    return fetch("/api/robot/status?ip=" + encodeURIComponent(robotIp())).then((r) => r.json());
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
    const s = await getStatus();
    const m = s && s.module;
    const speeds = m && m.max_dps;
    const ceiling = Array.isArray(speeds) && speeds.length === NJ ? Math.min(...speeds.map(Number)) : 0;
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
    const warning = `Save peak speed limit ${want} °/s to this board? It takes effect only after you restart the board. ` + (want > SAFE_DPS ? "Higher speed can cause harder impacts. " : "") + (boardSafePeer ? `Linked board #${boardSafePeer} must be set to the same limit before synchronized playback. ` : "") + "Check that every joint holds under load before running a show.";
    if (!confirm(warning)) return;
    const reply = await rawCmd(`CFG safe_dps ${want}`);
    if (!/^OK safe_dps=/.test(reply)) throw new Error(reply || "board did not confirm the setting");
    stat.textContent = `Saved ${want} °/s for next boot. Active limit is still ${SAFE_DPS} °/s. Restart the board, then reconnect Studio to confirm.` + (boardSafePeer ? ` Set linked board #${boardSafePeer} to the same limit.` : "");
  } catch (e) {
    Mice.fail(stat, "Safety speed not saved", e);
    notice(stat.textContent);
  }
}
function linkBadge() {
  const parts = [], bus = busId() ? "→RS485 #" + busId() : "";
  if (haveAuto()) parts.push("fastest route (hub) ✓");
  if (usbDirect()) parts.push("USB direct" + bus + " ✓");
  else if (hubPort) parts.push("USB " + hubPort + bus + " (shared) ✓");
  if (haveWifi()) parts.push("WiFi " + robotIp());
  if (parts.length) return parts.join(" + ");
  if (window.miceLink) {
    const s = window.miceLink.read({
      cable: false,
      wifi: false,
      viaHub: false,
      everHeard: false
    });
    return s.says + (s.next ? "  " + s.next : "");
  }
  return "not connected";
}
async function scanModules() {
  const sel = $("foundSel");
  sel.innerHTML = "<option value=''>scanning the WiFi… (a few seconds)</option>";
  try {
    const r = await fetch("/api/scan?force=1").then((r2) => r2.json());
    sel.innerHTML = "<option value=''>found: pick one…</option>";
    (r.modules || []).forEach((m) => {
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
let connecting = false;
async function connectRobot() {
  if (!currentUser) {
    showTab("robot");
    $("loginStat").textContent = "Log in to connect to the robot.";
    if (!pendingConnect) {
      pendingConnect = {};
      pendingConnect.promise = new Promise((resolve, reject) => {
        pendingConnect.resolve = resolve;
        pendingConnect.reject = reject;
      });
    }
    return pendingConnect.promise;
  }
  if (connecting) return;
  connecting = true;
  try {
    await connectLink();
  } finally {
    connecting = false;
  }
}
async function connectLink() {
  const t = transport(), had = hubPort;
  try {
    if (t === "usb") {
      if (!$("usbPort").dataset.loaded) await loadPorts();
      hubPort = $("usbPort").value;
      if (!hubPort) throw new Error("pick the USB port the module is plugged into (⟳ to rescan)");
      recallBusId(hubPort);
    } else if (t === "serial" && !usbDirect()) {
      await serialConnect();
    }
    let s;
    try {
      s = await getStatus();
    } catch (e) {
      if (t === "wifi" && hubPort && haveWifi()) {
        hubPort = "";
        s = await getStatus();
      } else {
        const tried = busId();
        if (t !== "usb" || !await findBusId(hubPort) || busId() === tried) throw e;
        s = await getStatus();
      }
    }
    if (t === "usb") rememberBusId(hubPort);
    checkLimitsMatch();
    boardSafeIdentity = String(s.chip || s.id || "");
    adoptBoardSafety(s.module);
    const own = s.seq && s.seq.running ? ` — the module is PLAYING ${s.seq.file || "a sequence"} on its own; Play or Stop here takes over` : "";
    $("robotStat").textContent = `[${linkBadge()}] ${s.name} (id ${s.id}, type ${s.type})` + (s.type !== "nong" ? " — WARNING: type is not nong" : "") + (s.sd ? ", SD ok" : ", no SD card") + own;
    refreshSd();
  } catch (e) {
    if (t === "usb" && !had) hubPort = "";
    boardSafeIdentity = "";
    $("safeDpsInput").disabled = $("saveSafeDps").disabled = true;
    $("safeSpeedStat").textContent = "Disconnected. Reconnect to read the active safety limit.";
    notice($("safeSpeedStat").textContent);
    $("robotStat").textContent = "Could not reach the robot. Check it is powered and on the same network or cable, then try again. " + Mice.Words.plain(e).says;
    notice($("robotStat").textContent);
  }
}
function sendPose(quiet) {
  return quiet ? sendPoseLive() : liveSend("POSE " + pose.map(fmtA).join(" "));
}
let liveBusy = false, livePending = null, liveQueue = [];
let liveRtt = 120;
const LIVE_T_MIN = 80, LIVE_T_MAX = 300;
function liveT() {
  return Math.max(LIVE_T_MIN, Math.min(LIVE_T_MAX, Math.round(liveRtt * 1.3)));
}
function liveSend(c) {
  if (!currentUser) return Promise.resolve(false);
  if (/^(?:MOVE\s+)?STOP\s*$/i.test(c)) return cancelSafeMotion("Stop");
  const p = /^POSE\s+(.+)$/i.exec(c);
  const work = { c, epoch: safeMotionEpoch, target: safeTarget(), goal: null, ms: 0, revision: null };
  if (p) {
    const bits = p[1].trim().split(/\s+/), at = bits.findIndex((v) => v.toUpperCase() === "T");
    work.goal = (at < 0 ? bits : bits.slice(0, at)).map(Number);
    work.ms = at < 0 ? 0 : Number(bits[at + 1]);
    if (work.goal.length !== NJ || work.goal.some((v) => !Number.isFinite(v)) || !Number.isFinite(work.ms) || work.ms < 0 || at >= 0 && at + 2 !== bits.length) {
      safeMotionNote("Not moved: invalid pose or duration", true);
      return Promise.resolve(false);
    }
  }
  const result = new Promise((resolve) => {
    work.resolve = resolve;
  });
  if (work.goal && !playing) {
    if (livePending && livePending.resolve) livePending.resolve(false);
    work.revision = ++safeGoalRevision;
    livePending = work;
  } else liveQueue.push(work);
  if (work.goal) lastSafeMove = result;
  livePump();
  return result;
}
function sendPoseLive() {
  return liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + liveT());
}
function liveAbort() {
  safeMotionEpoch++;
  safeGoalRevision++;
  liveQueue.forEach((work) => {
    if (work.resolve) work.resolve(false);
  });
  if (livePending && livePending.resolve) livePending.resolve(false);
  liveQueue = [];
  livePending = null;
}
function livePump() {
  if (liveBusy) return;
  liveBusy = true;
  (async () => {
    try {
      for (; ; ) {
        let work = null;
        if (liveQueue.length) {
          work = liveQueue.shift();
        } else if (livePending) {
          work = livePending;
          livePending = null;
        }
        if (!work) break;
        const c = work.c;
        if (work.epoch !== safeMotionEpoch || work.target !== safeTarget()) {
          work.resolve(false);
          continue;
        }
        try {
          if (work.goal) {
            const ok = await checkedPose(work.goal, work.ms, work.epoch, work.revision, work.target);
            work.resolve(ok);
            continue;
          }
          const t0 = performance.now();
          const r = await rawCmd(c);
          liveRtt += (performance.now() - t0 - liveRtt) * 0.25;
          $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + r.slice(0, 80);
          work.resolve(true);
        } catch (e) {
          work.resolve(false);
          liveAbort();
          Mice.fail($("robotStat"), "", e);
        }
      }
    } finally {
      liveBusy = false;
    }
  })();
}
async function sdUploadSerial(fname, text) {
  const bytes = new TextEncoder().encode(text);
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
      method: "POST",
      body: new TextEncoder().encode(text)
    })).text()).trim();
    if (body.startsWith("ERR")) throw new Error(body);
    return;
  }
  if (haveWifi()) {
    try {
      const r = await fetch("/api/robot/upload", {
        method: "POST",
        body: JSON.stringify({ ip: robotIp(), name: fname, yaml: text })
      }).then((r2) => r2.json());
      if (!r.ok) throw new Error(JSON.stringify(r));
      return;
    } catch (e) {
      if (!haveUsb()) throw e;
    }
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
  return new TextDecoder().decode(Uint8Array.from(all, (c) => c.charCodeAt(0)));
}
async function sdDownload(fname) {
  if (haveAuto())
    return (await autoFetch("download", { path: "/moves/" + fname })).text();
  if (haveWifi()) {
    try {
      const r = await fetch(`/api/robot/download?ip=${encodeURIComponent(robotIp())}&path=${encodeURIComponent("/moves/" + fname)}`);
      const text = await r.text();
      if (!r.ok) throw new Error(text.trim() || "the robot answered " + r.status);
      return text;
    } catch (e) {
      if (!haveUsb()) throw e;
    }
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
      const res = await fetch(`/api/robot/delete?ip=${encodeURIComponent(robotIp())}&path=${encodeURIComponent("/moves/" + fname)}`);
      const body = (await res.text()).trim();
      if (!res.ok || body.startsWith("ERR")) {
        throw new Error(body || "the robot answered " + res.status);
      }
      return;
    } catch (e) {
      if (!haveUsb()) throw e;
    }
  }
  if (!haveUsb()) throw new Error("connect first (WiFi or USB)");
  const r = await cableCmd("FDEL " + fname);
  if (!r.startsWith("OK")) throw new Error(r);
}
async function refreshSd() {
  const box = $("sdList");
  box.textContent = "Reading the robot's card…";
  try {
    let files;
    if (haveAuto()) {
      files = await (await autoFetch("files", { dir: "/moves" })).json();
    } else if (haveWifi()) {
      files = await fetch(`/api/robot/files?ip=${encodeURIComponent(robotIp())}&dir=/moves`).then((r) => r.json());
    } else if (haveUsb()) {
      files = JSON.parse(await cableCmd("FILES /moves"));
    } else {
      box.textContent = "Not connected to a robot yet, so there is no card to read. Press 🔍 Find modules, or pick a USB cable above.";
      return;
    }
    box.innerHTML = "";
    if (!files.length) {
      box.textContent = "This robot's card has no sequences on it yet. Build a timeline, then press “Send to robot” to put one there.";
    }
    const dl = $("seqNextList");
    if (dl) {
      dl.innerHTML = "";
      files.forEach((f) => {
        const o = document.createElement("option");
        o.value = f.n;
        dl.appendChild(o);
      });
    }
    files.forEach((f) => {
      const row = document.createElement("div");
      row.className = "row";
      const name = document.createElement("span");
      name.style.flex = "1";
      name.textContent = f.n + "  (" + (f.s / 1024).toFixed(1) + " kB)";
      const run = document.createElement("button");
      run.textContent = "▶ Run";
      run.className = "primary";
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
      del.textContent = "✕";
      del.title = "delete from SD";
      del.onclick = async () => {
        if (!confirm("Delete " + f.n + " from the robot SD card?")) return;
        try {
          await sdDelete(f.n);
        } catch (e) {
          $("sdStat").textContent = "" + e;
        }
        refreshSd();
      };
      row.append(name, run, play, edit, del);
      box.appendChild(row);
    });
    $("sdStat").textContent = "";
  } catch (e) {
    box.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "Could not read the robot's card. It may have gone off the network, or it has no card fitted. ";
    const why = document.createElement("span");
    why.className = "hint";
    why.textContent = Mice.Words.plain(e).says;
    const again = document.createElement("button");
    again.textContent = "Try again";
    again.onclick = () => refreshSd();
    box.append(msg, why, document.createTextNode(" "), again);
  }
}
async function uploadYaml() {
  if (nothingToWrite("sdStat")) return;
  if (!await ensureSafeTimeline()) return;
  if (!crashGate("UPLOAD it")) return;
  const { name, yaml } = buildYaml();
  try {
    await sdUpload(name + ".yaml", yaml);
    $("sdStat").textContent = `saved ${name}.yaml on the robot — press its ▶ Run button here, or pick it on the robot's own page`;
    refreshSd();
  } catch (e) {
    notice(Mice.fail($("sdStat"), "upload failed", e));
  }
}
function stopRobotSequence() {
  handedOff = false;
  if (!haveRobot()) return;
  try {
    cancelSafeMotion("sequence takeover");
  } catch (e) {
  }
}
let handedOff = false;
async function handOffToRobot() {
  if (handedOff || !playing) return;
  if (!haveRobot()) return;
  if (previewOnly) return;
  if (!liveLinked()) return;
  if (hubDriven()) return;
  handedOff = true;
  try {
    const fromMs = playT;
    await cancelSafeMotion("handover");
    entryHold = true;
    const started = await startCheckedSequence(fromMs, false);
    if (!started) {
      handedOff = false;
      return;
    }
    playing = false;
    keepAwake(false);
    $("playBtn").textContent = "▶ Play";
    const st = $("sdStat");
    if (st) st.textContent = "the module is running this sequence on its own — it keeps going with this page closed. Press Stop to end it.";
  } catch (e) {
    handedOff = false;
    safeMotionNote("Could not hand over: " + Mice.Words.plain(e).says, true);
  } finally {
    entryHold = false;
  }
}
document.addEventListener("visibilitychange", function() {
  if (document.hidden) {
    handOffToRobot();
    return;
  }
  handedOff = false;
  if (!hubDriven() || !playing) return;
  fetch("/api/play").then((r) => r.json()).then((s) => {
    if (!s.running) {
      playing = false;
      $("playBtn").textContent = "▶ Play";
      keepAwake(false);
      return;
    }
    playT = Math.min(s.at_ms || 0, totalMs());
    lastPlayMs = 0;
    pose = poseAt(playT).map((v, i) => clampJ(i, v));
    applyPose();
    renderSliders();
  }).catch(() => {
  });
});
const LAST_RUN_FILE = "last.yaml";
const KEEP_RUN_KEY = "nong_keep_last_run";
function keepRunOn() {
  try {
    return localStorage.getItem(KEEP_RUN_KEY) !== "0";
  } catch (e) {
    return true;
  }
}
function setKeepRun(on) {
  try {
    localStorage.setItem(KEEP_RUN_KEY, on ? "1" : "0");
  } catch (e) {
  }
}
async function keepLastRun(yaml, file) {
  if (!keepRunOn() || file === LAST_RUN_FILE) return "";
  try {
    await sdUpload(LAST_RUN_FILE, yaml);
    return "";
  } catch (e) {
    return "the copy as " + LAST_RUN_FILE + " was not kept: " + Mice.Words.plain(e).says;
  }
}
async function robotRun() {
  if (nothingToWrite("sdStat")) return;
  if (!await ensureSafeTimeline()) return;
  if (!crashGate("RUN it on the robot")) return;
  const st = $("sdStat");
  if (st) st.textContent = "checking and sending the sequence to the robot…";
  let started;
  try {
    started = await startCheckedSequence(playT);
  } catch (e) {
    cancelSafeMotion("sequence start failed");
    if (st) st.textContent = "could not start the sequence — " + Mice.Words.plain(e).says;
    return;
  }
  if (!started) {
    if (st) st.textContent = "Start cancelled; check the current settings and try again.";
    return;
  }
  const { file, name, part, kept } = started;
  if (st) st.textContent = (part ? "the robot is running the checked remainder once, including any checked loop return. The whole show is still saved as " + name + ".yaml." : "the robot is running " + file + " on its own.") + (kept ? " Note: " + kept : keepRunOn() ? " A copy is kept on it as " + LAST_RUN_FILE + "." : "");
  if (kept) notice(kept);
}
async function zeroUnlock() {
  const u = $("zUser").value.trim(), p = $("zPass").value;
  let ok = false, why = "";
  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: u, password: p })
    });
    const j = await r.json().catch(() => ({}));
    ok = r.ok && !!j.ok;
    if (j.locked_for > 0) why = `Too many tries. Wait ${j.locked_for} seconds.`;
  } catch (e) {
    const acc = getAccounts();
    ok = !!(acc[u] && acc[u] === p);
  }
  $("zPass").value = "";
  if (ok) {
    $("zeroLocked").style.display = "none";
    $("zeroPanel").style.display = "";
    $("zStat").textContent = "";
  } else {
    $("zStat").textContent = why || "That user name and password do not match. Use your hub login and try again.";
  }
}
function zeroLock() {
  $("zeroPanel").style.display = "none";
  $("zeroLocked").style.display = "";
}
async function robotZeroSet() {
  if (!haveRobot()) {
    $("zStat2").textContent = "connect to the robot first";
    notice($("zStat2").textContent);
    return;
  }
  const r = await robotCmd("SETZERO");
  $("zStat2").textContent = r.startsWith("OK") ? "zero set — this pose is now the robot's home. Your start angles are unchanged." : "failed: " + r;
  if (!r.startsWith("OK")) notice($("zStat2").textContent);
}
let monTimer = null;
function liveChanged() {
  if ($("liveChk").checked) {
    $("monChk").checked = false;
    monitorChanged();
  } else cancelSafeMotion("Live turned off");
}
function monitorChanged() {
  if ($("monChk").checked) {
    $("liveChk").checked = false;
    cancelSafeMotion("monitoring");
    playing = false;
    $("playBtn").textContent = "▶ Play";
    $("robotStat").textContent = "monitoring…";
    const start = () => {
      if ($("monChk").checked && !monTimer) monTimer = setInterval(monitorTick, 350);
    };
    if (haveRobot()) start();
    else Promise.resolve(connectRobot()).then(() => {
      if (haveRobot()) return start();
      $("monChk").checked = false;
      $("robotStat").textContent = "monitor needs the robot connected — pick the cable or WiFi above and press Connect, then tick monitor again.";
      notice($("robotStat").textContent);
    });
  } else {
    clearInterval(monTimer);
    monTimer = null;
  }
}
let monBusy = false;
async function monitorTick() {
  if (monBusy) return;
  monBusy = true;
  try {
    const s = await getStatus();
    const m = s.module || {};
    if (Array.isArray(m.joints) && m.joints.length >= ARMJ) {
      pose = pose.map((cur, i) => m.joints[i] !== void 0 ? clampJ(i, m.joints[i]) : cur);
      applyPose();
      renderSliders();
    }
    const seq = s.seq || {};
    $("robotStat").textContent = `MONITOR ${s.name}: ` + (seq.running ? `playing ${seq.file}` : "no sequence running") + (m.moving ? ` | moving (${m.move_left || 0} ms left)` : " | idle") + (m.attached === false ? " | relaxed" : "");
  } catch (e) {
    $("robotStat").textContent = "monitor: no reply (" + Mice.Words.plain(e).says + ")";
    notice($("robotStat").textContent);
  } finally {
    monBusy = false;
  }
}
const ROBOT_SETTINGS = [
  {
    id: "name",
    label: "Name",
    type: "text",
    hint: "letters, digits and -",
    ok: (v) => /^[A-Za-z0-9-]{1,24}$/.test(v),
    read: (s) => s.name,
    send: (v) => ["SET NAME " + v],
    ask: (v) => "Rename the robot to " + v + "?\n\nIts WiFi name and its address (" + v + ".local) change too, so connect again afterwards."
  },
  {
    id: "speed",
    label: "Speed when a pose has no time",
    type: "number",
    unit: "°/s",
    min: 5,
    max: 600,
    read: (s) => s.module && s.module.speed_dps,
    send: (v) => ["SPEED " + v, "CFG speed_dps " + v]
  },
  {
    id: "volume",
    label: "Volume",
    type: "number",
    unit: "0 to 100",
    min: 0,
    max: 100,
    read: (s) => s.module && s.module.audio && s.module.audio.vol,
    send: (v) => ["VOL " + v, "CFG volume " + v]
  }
];
function renderRobotSettings() {
  const box = $("robotSettings");
  if (!box || box.childElementCount) return;
  ROBOT_SETTINGS.forEach((def) => {
    const row = document.createElement("div");
    row.className = "row";
    const lbl = document.createElement("label");
    lbl.className = "lbl";
    lbl.htmlFor = "rs_" + def.id;
    lbl.textContent = def.label;
    const inp = document.createElement("input");
    inp.id = "rs_" + def.id;
    inp.type = def.type;
    if (def.type === "number") {
      inp.min = def.min;
      inp.max = def.max;
      inp.style.width = "80px";
    } else inp.style.flex = "1";
    inp.placeholder = def.hint || "";
    const unit = document.createElement("span");
    unit.className = "mini";
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
    ROBOT_SETTINGS.forEach((def) => {
      const v = def.read(s || {});
      if (v !== void 0 && v !== null) $("rs_" + def.id).value = v;
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
  const fine = def.type === "number" ? raw !== "" && Number.isFinite(v) && v >= def.min && v <= def.max : def.ok(v);
  if (!fine) {
    stat.textContent = def.label + ": " + (def.type === "number" ? "type a number from " + def.min + " to " + def.max + "." : "use " + def.hint + " only.");
    notice(stat.textContent);
    return;
  }
  if (def.ask && !confirm(def.ask(v))) return;
  try {
    for (const c of def.send(v)) {
      const r = await rawCmd(c);
      if (!/^OK/i.test(r || "")) throw new Error(r || "no answer");
    }
    stat.textContent = def.label + " is " + v + (def.unit ? " " + def.unit : "") + " on the robot now, and it keeps it after a restart.";
  } catch (e) {
    stat.textContent = def.label + " was not saved on the robot: " + Mice.Words.plain(e).says;
    notice(stat.textContent);
  }
}
renderRobotSettings();
let VIDEO_FOLLOW = null, VIDEO_POLICY = null, VIDEO_READY = null;
function videoFollowReady() {
  if (!VIDEO_READY) VIDEO_READY = (async () => {
    const config = await fetch("video_follow.json").then((r) => r.json());
    if (!config.tracking || !config.fitting || config.version !== 1) throw new Error("Video follow settings could not be read");
    let policy = null;
    try {
      policy = await fetch(config.policy.model).then((r) => r.json());
    } catch (_) {
    }
    VIDEO_POLICY = policy;
    VIDEO_FOLLOW = config;
    return config;
  })().catch((error) => {
    VIDEO_READY = null;
    throw error;
  });
  return VIDEO_READY;
}
class VideoBodyMotion {
  static wrap(v) {
    return Math.atan2(Math.sin(v), Math.cos(v));
  }
  static measure(w, mirror = false) {
    var _a;
    if (!w || w.length < 25) return null;
    const point = (i) => {
      var _a2, _b;
      const j = mirror ? i % 2 ? i + 1 : i - 1 : i, p = w[j];
      return { at: new THREE.Vector3(mirror ? -p.x : p.x, -p.y, -p.z), seen: (_b = (_a2 = p.v) != null ? _a2 : p.visibility) != null ? _b : 1 };
    };
    const sl = point(11), sr = point(12), hl = point(23), hr = point(24);
    const confidence = Math.min(sl.seen, sr.seen, hl.seen, hr.seen);
    if (confidence < ((_a = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.tracking.confidence) != null ? _a : 0.55)) return null;
    const left = hl.at.clone().sub(hr.at), spine = sl.at.clone().add(sr.at).sub(hl.at).sub(hr.at);
    if (left.length() < 0.025 || spine.length() < 0.05) return null;
    left.normalize();
    const up = spine.clone().addScaledVector(left, -spine.dot(left)).normalize();
    const front = left.clone().cross(up).normalize();
    const shoulder = sl.at.clone().sub(sr.at), sx = shoulder.dot(left), sz = shoulder.dot(front);
    const twist = Math.atan2(-sz, sx), roll = Math.atan2(shoulder.dot(up), Math.hypot(sx, sz));
    const torsoLeft = shoulder.clone().addScaledVector(up, -shoulder.dot(up)).normalize();
    const torsoFront = torsoLeft.clone().cross(up).normalize();
    const arms = [0, 1].map((a) => {
      var _a2;
      const S = point(11 + a), E = point(13 + a), W = point(15 + a);
      const local = (v) => new THREE.Vector3(v.dot(torsoLeft), v.dot(up), v.dot(torsoFront)).normalize();
      return {
        ok: Math.min(S.seen, E.seen, W.seen) >= ((_a2 = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.tracking.confidence) != null ? _a2 : 0.55),
        upper: local(E.at.clone().sub(S.at)),
        fore: local(W.at.clone().sub(E.at)),
        rawUpper: E.at.clone().sub(S.at).normalize(),
        rawFore: W.at.clone().sub(E.at).normalize()
      };
    });
    return { arms, twist, roll, confidence, viewUp: up.clone(), viewLeft: left.clone(), hipYaw: Math.atan2(front.x, front.z) };
  }
  static difference(a, b, raw = false) {
    if (!a || !b) return 180;
    let error = 0;
    for (let i = 0; i < 2; i++) if (a.arms[i].ok && b.arms[i].ok)
      for (const key of raw ? ["rawUpper", "rawFore"] : ["upper", "fore"])
        error = Math.max(error, THREE.MathUtils.radToDeg(a.arms[i][key].angleTo(b.arms[i][key])));
    return error;
  }
  static styleDifference(a, b) {
    if (!a || !b) return 180;
    return Math.max(this.difference(a, b), THREE.MathUtils.radToDeg(Math.max(
      Math.abs(this.wrap(a.twist - b.twist)),
      Math.abs(a.roll - b.roll)
    )));
  }
  static blend(previous, observed, weight = 0.6) {
    return {
      ...observed,
      twist: previous.twist + this.wrap(observed.twist - previous.twist) * weight,
      roll: previous.roll + (observed.roll - previous.roll) * weight,
      arms: observed.arms.map((a, i) => ({
        ...a,
        upper: previous.arms[i].upper.clone().lerp(a.upper, weight).normalize(),
        fore: previous.arms[i].fore.clone().lerp(a.fore, weight).normalize()
      }))
    };
  }
}
class VideoTemporalPolicy {
  constructor(model = VIDEO_POLICY, cameraMode = "fixed") {
    this.model = model;
    this.cameraMode = cameraMode;
    this.accepted = null;
    this.previous = null;
    this.headingBaseline = null;
    this.held = 0;
    this.heading = 0;
  }
  static bin(value, edges) {
    let n = 0;
    while (n < edges.length && value >= edges[n]) n++;
    return n;
  }
  static state(features, model) {
    return model.features.map((name, i) => VideoTemporalPolicy.bin(features[name], model.bins[i])).join(":");
  }
  step(body, scene2, shot, groupTrust = 1) {
    var _a, _b, _c;
    if (!body) {
      this.held++;
      return { body: this.accepted, action: "uncertain", trusted: false, waist: this.accepted ? this.heading + this.accepted.twist : null };
    }
    if (!this.accepted) {
      this.accepted = body;
      this.previous = body;
      this.headingBaseline = body.hipYaw;
      return { body, action: "initial", trusted: true, waist: body.twist };
    }
    const features = {
      invariant: VideoBodyMotion.difference(body, this.accepted),
      raw: VideoBodyMotion.difference(body, this.previous, true),
      body: THREE.MathUtils.radToDeg(Math.max(Math.abs(VideoBodyMotion.wrap(body.twist - this.accepted.twist)), Math.abs(body.roll - this.accepted.roll))),
      scene: scene2,
      confidence: body.confidence * groupTrust,
      held: this.held,
      heading: THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(body.hipYaw - this.headingBaseline)))
    };
    let action = "uncertain", learned = false;
    const model = this.model;
    if ((model == null ? void 0 : model.enabled) && model.schema === "mice-video-q-v1") {
      const row = model.q[VideoTemporalPolicy.state(features, model)];
      if (row && row.every(Number.isFinite)) {
        const ranks = row.map((q, i) => ({ q, i })).sort((a, b) => b.q - a.q);
        if (ranks[0].q - ranks[1].q >= ((_a = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.policy.minimumMargin) != null ? _a : 0.5)) {
          action = model.actions[ranks[0].i];
          learned = true;
        }
      }
    }
    if (!learned && features.confidence >= 0.55) {
      if (scene2 > 0.18 && features.invariant < 12 && features.body < 8) action = "compensate";
      else if (scene2 <= 0.18 && (features.invariant > 3 || features.body > 2 || features.heading > 3)) action = "accept";
      else if (features.invariant <= 3 && features.body <= 2) action = "hold";
    }
    if (groupTrust < 0.5 || scene2 > 0.18 && (features.invariant > 45 || features.body > 35)) action = "uncertain";
    if (features.confidence >= 0.55 && features.invariant < ((_b = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.body.stillBonesDegrees) != null ? _b : 6) && features.body < ((_c = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.body.stillBodyDegrees) != null ? _c : 3) && features.heading < 3 && scene2 < 0.1) action = "hold";
    const headingObservable = this.cameraMode === "fixed" || scene2 < 0.01;
    if (features.confidence >= 0.55 && features.heading >= 3 && !shot && scene2 <= 0.18 && headingObservable) {
      this.heading += VideoBodyMotion.wrap(body.hipYaw - this.headingBaseline);
      this.headingBaseline = body.hipYaw;
    }
    if (shot || scene2 > 0.18 || !headingObservable) this.headingBaseline = body.hipYaw;
    if (action === "accept" || action === "compensate") {
      this.accepted = action === "compensate" ? VideoBodyMotion.blend(this.accepted, body) : body;
      this.held = 0;
    } else this.held++;
    this.previous = body;
    return {
      body: this.accepted,
      action,
      learned,
      trusted: action !== "uncertain",
      features,
      waist: this.heading + this.accepted.twist
    };
  }
}
class VideoMotionSmoother {
  constructor(config = VIDEO_FOLLOW.smoothing) {
    this.config = config;
  }
  static quality(poses, times) {
    let reversals = 0, travel = 0, largestStep = 0;
    for (let i = 1; i < poses.length; i++) for (let j = 0; j < NJ; j++) {
      const d = poses[i][j] - poses[i - 1][j];
      travel += Math.abs(d);
      largestStep = Math.max(largestStep, Math.abs(d));
      if (i > 1 && times[i] - times[i - 2] < 700) {
        const previous = poses[i - 1][j] - poses[i - 2][j];
        if (d * previous < 0 && Math.min(Math.abs(d), Math.abs(previous)) > 2) reversals++;
      }
    }
    return { reversals, travel, largestStep };
  }
  apply(poses, times, frames) {
    if (!poses.length) return { poses: [], before: null, after: null };
    const cfg = this.config, before = VideoMotionSmoother.quality(poses, times);
    const out = [poses[0].slice()], velocity = poses[0].map(() => 0);
    const reliable = (i) => {
      var _a, _b, _c, _d, _e;
      return ((_a = frames[i]) == null ? void 0 : _a.trusted) !== false && ((_b = frames[i]) == null ? void 0 : _b.action) !== "uncertain" && (((_c = frames[i]) == null ? void 0 : _c.trusted) === true || ((_d = frames[i]) == null ? void 0 : _d.body) || ((_e = frames[i]) == null ? void 0 : _e.w));
    };
    for (let i = 1; i < poses.length; i++) {
      const previous = out[i - 1], dt = Math.max(1e-3, (times[i] - times[i - 1]) / 1e3);
      if (!reliable(i)) {
        out.push(previous.slice());
        velocity.fill(0);
        continue;
      }
      const near = (k, d) => {
        var _a, _b;
        const n = k + d;
        return n >= 1 && n < poses.length && Math.abs(times[n] - times[k]) <= cfg.windowMs && reliable(n) && ((_a = frames[n]) == null ? void 0 : _a.shot) === ((_b = frames[k]) == null ? void 0 : _b.shot) ? n : k;
      };
      const med3 = (k, j) => [poses[near(k, -1)][j], poses[k][j], poses[near(k, 1)][j]].sort((x, y) => x - y)[1];
      const next = poses[i].map((value, j) => {
        var _a;
        const target = ((_a = frames[i]) == null ? void 0 : _a.action) === "hold" ? value : 0.25 * med3(near(i, -1), j) + 0.5 * med3(i, j) + 0.25 * med3(near(i, 1), j);
        let distance = target - previous[j];
        if (Math.abs(distance) < cfg.deadbandDegrees) distance *= Math.abs(distance) / cfg.deadbandDegrees;
        const top = jointMaxDps(j) * (+cfg.speedScale || 1);
        const accel = (+RIG.servoAccel[j] || 3e3) * (+cfg.accelScale || 1);
        let speed = Math.max(-top, Math.min(top, distance / dt));
        speed = Math.max(velocity[j] - accel * dt, Math.min(velocity[j] + accel * dt, speed));
        const delta = Math.sign(speed) === Math.sign(distance) ? Math.sign(distance) * Math.min(Math.abs(distance), Math.abs(speed * dt)) : 0;
        velocity[j] = delta / dt;
        return clampJ(j, previous[j] + delta);
      });
      out.push(next);
    }
    return { poses: out, before, after: VideoMotionSmoother.quality(out, times) };
  }
}
class VideoAppearanceDescriptor {
  static measure(points, rgba, width, height) {
    if (!rgba || !(points == null ? void 0 : points[24]) || width * height * 4 !== rgba.length) return null;
    const shoulderY = (points[11].y + points[12].y) / 2, hipY = (points[23].y + points[24].y) / 2;
    const cx = (points[11].x + points[12].x) / 2;
    const half = Math.max(0.01, Math.abs(points[11].x - points[12].x) * 0.4);
    const noseY = points[0].y, torso = hipY - shoulderY;
    if (!(torso > 0.025)) return null;
    const bands = [
      [noseY - torso * 0.18, noseY + torso * 0.08, 0.7],
      [noseY + torso * 0.08, shoulderY, 0.65],
      [shoulderY, shoulderY + torso * 0.55, 1],
      [shoulderY + torso * 0.55, hipY, 0.8]
    ];
    const result = [];
    for (const [top, bottom, scale] of bands) {
      const hist = Array(24).fill(0);
      let count = 0;
      const x0 = Math.max(0, Math.floor((cx - half * scale) * width)), x1 = Math.min(width, Math.ceil((cx + half * scale) * width));
      const y0 = Math.max(0, Math.floor(top * height)), y1 = Math.min(height, Math.ceil(bottom * height));
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
        const at = (y * width + x) * 4;
        for (let channel = 0; channel < 3; channel++) hist[channel * 8 + Math.min(7, rgba[at + channel] >> 5)]++;
        count++;
      }
      if (!count) return null;
      result.push(...hist.map((v) => v / count));
    }
    return result;
  }
  static distance(a, b) {
    if (!a || !b || a.length !== b.length) return Infinity;
    return a.reduce((sum, v, i) => sum + Math.abs(v - b[i]), 0) / 24;
  }
  static average(values) {
    const valid = values.filter(Boolean);
    if (!valid.length) return null;
    return valid[0].map((_, i) => valid.reduce((sum, row) => sum + row[i], 0) / valid.length);
  }
}
class VideoRoutineAssignment {
  static solve(matrix, forbiddenRow = -1, forbiddenColumn = -1) {
    var _a;
    const rows = matrix.length, columns = ((_a = matrix[0]) == null ? void 0 : _a.length) || 0, large = 1e12;
    if (!rows) return { cost: 0, columns: [] };
    if (columns < rows || matrix.some((row) => row.length !== columns)) throw new Error("Incomplete routine assignment matrix");
    const u = new Float64Array(rows + 1), v = new Float64Array(columns + 1);
    const matched = new Int32Array(columns + 1), way = new Int32Array(columns + 1);
    const value = (i, j) => i === forbiddenRow && j === forbiddenColumn || !Number.isFinite(matrix[i][j]) ? large : matrix[i][j];
    for (let row = 1; row <= rows; row++) {
      matched[0] = row;
      const minimum = new Float64Array(columns + 1).fill(large), used = new Uint8Array(columns + 1);
      let column = 0;
      do {
        used[column] = 1;
        const current = matched[column];
        let delta = large, next = 0;
        for (let j = 1; j <= columns; j++) if (!used[j]) {
          const cost2 = value(current - 1, j - 1) - u[current] - v[j];
          if (cost2 < minimum[j]) {
            minimum[j] = cost2;
            way[j] = column;
          }
          if (minimum[j] < delta) {
            delta = minimum[j];
            next = j;
          }
        }
        if (delta >= large / 2) return { cost: Infinity, columns: [] };
        for (let j = 0; j <= columns; j++) {
          if (used[j]) {
            u[matched[j]] += delta;
            v[j] -= delta;
          } else minimum[j] -= delta;
        }
        column = next;
      } while (matched[column]);
      do {
        const previous = way[column];
        matched[column] = matched[previous];
        column = previous;
      } while (column);
    }
    const result = Array(rows).fill(-1);
    for (let j = 1; j <= columns; j++) if (matched[j]) result[matched[j] - 1] = j - 1;
    const cost = result.reduce((sum, column, row) => sum + value(row, column), 0);
    return { cost: cost >= large / 2 ? Infinity : cost, columns: result };
  }
}
class VideoRoutineSections {
  static observations(group) {
    var _a, _b;
    const leader = (_b = (_a = group.slice().sort((a, b) => b.reduce((sum, row) => sum + row.actor.confidence, 0) - a.reduce((sum, row) => sum + row.actor.confidence, 0))[0]) == null ? void 0 : _a[0]) == null ? void 0 : _b.actor.id;
    const selected = /* @__PURE__ */ new Map();
    for (const row of group.flat()) {
      const old = selected.get(row.index);
      if (!old || row.actor.id === leader || old.id !== leader && row.actor.confidence > old.confidence) selected.set(row.index, row.actor);
    }
    return selected;
  }
  static build(units, frames, options, config, qualified) {
    const sections = [];
    for (const unit of units) {
      if (qualified.has(unit.parentId) && !unit.ambiguous) continue;
      const indexes = [...unit.observations.keys()].sort((a, b) => a - b), first = indexes[0], last = indexes.at(-1);
      const from = frames[first].t, to = frames[last].t;
      if (to - from < config.minimumSegmentSeconds) continue;
      const policy = new VideoTemporalPolicy(options.learned === false ? null : VIDEO_POLICY, options.cameraMode);
      const local = frames.slice(first, last + 1).map((frame, offset) => {
        const actor = unit.observations.get(first + offset);
        const state = policy.step((actor == null ? void 0 : actor.body) || null, frame.scene, offset === 0, actor && actor.confidence >= VIDEO_FOLLOW.tracking.confidence ? 1 : 0);
        return { ...frame, ...state, t: frame.t - from, w: (actor == null ? void 0 : actor.w) || null, p: (actor == null ? void 0 : actor.p) || null, track: (actor == null ? void 0 : actor.id) || null };
      });
      sections.push({
        id: "scene_" + unit.shot + "_" + unit.ordinal,
        kind: "segment",
        parentId: unit.parentId,
        sourceStart: from,
        sourceEnd: to,
        frames: local,
        crossShotUncertain: unit.ambiguous,
        ambiguous: false,
        people: unit.people,
        coverage: local.filter((f) => f.w).length / local.length,
        trustedCoverage: local.filter((f) => f.w && f.trusted).length / local.length
      });
    }
    return sections.sort((a, b) => a.sourceStart - b.sourceStart || b.trustedCoverage - a.trustedCoverage);
  }
}
class VideoRoutineDiscovery {
  constructor(options, config = VIDEO_FOLLOW.routines) {
    this.options = options;
    this.config = config;
    this.frames = [];
    this.histories = /* @__PURE__ */ new Map();
  }
  static distance(a, b) {
    let sum = 0, count = 0;
    for (let arm = 0; arm < 2; arm++) if (a.arms[arm].ok && b.arms[arm].ok) for (const bone of ["upper", "fore"]) {
      sum += THREE.MathUtils.radToDeg(a.arms[arm][bone].angleTo(b.arms[arm][bone]));
      count++;
    }
    if (!count) return 180;
    return Math.max(sum / count, THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(a.twist - b.twist))), THREE.MathUtils.radToDeg(Math.abs(a.roll - b.roll)));
  }
  add(frame) {
    if (frame.cut) this.histories.clear();
    const actors = (frame.actors || []).map((actor) => {
      const history = this.histories.get(actor.id) || [];
      history.push(actor.body);
      if (history.length > 3) history.shift();
      this.histories.set(actor.id, history);
      if (history.length < 3) return actor;
      const median = (values) => values.sort((a, b) => a - b)[1], body = { ...actor.body, arms: actor.body.arms.map((a) => ({ ...a })) };
      for (const arm of [0, 1]) for (const bone of ["upper", "fore"]) body.arms[arm][bone] = new THREE.Vector3(...["x", "y", "z"].map((axis) => median(history.map((b) => b.arms[arm][bone][axis])))).normalize();
      body.twist += median(history.map((b) => VideoBodyMotion.wrap(b.twist - actor.body.twist)));
      body.roll = median(history.map((b) => b.roll));
      return { ...actor, body };
    });
    this.frames.push({ ...frame, actors });
  }
  compatible(a, b) {
    const other = new Map(b.map((r) => [r.index, r]));
    let count = 0, sum = 0, different = 0;
    for (const row of a) {
      const match = other.get(row.index);
      if (!match) continue;
      const error = VideoRoutineDiscovery.distance(row.actor.body, match.actor.body);
      count++;
      sum += error;
      if (error > this.config.styleDegrees) different++;
    }
    if (!count) {
      const first = a[0].t > b[0].t ? a[0] : b[0], last = a[0].t > b[0].t ? b.at(-1) : a.at(-1);
      return first.t >= last.t && first.t - last.t <= this.config.joinGapSeconds && Math.abs(first.actor.cx - last.actor.cx) < 0.12 && VideoRoutineDiscovery.distance(first.actor.body, last.actor.body) < this.config.styleDegrees;
    }
    return count >= this.config.minimumOverlap && sum / count <= this.config.styleDegrees && different / count <= this.config.divergentFraction;
  }
  joinCost(rows, routine) {
    const boundary = VideoRoutineDiscovery.distance(rows[0].actor.body, routine.last.actor.body);
    const past = [...routine.observations].map(([index, actor]) => ({ t: this.frames[index].t, actor }));
    const sample = rows.filter((r, i) => i % 2 === 0 && r.t - rows[0].t <= this.config.signatureSeconds);
    const near = rows[0].t - routine.last.t <= this.config.joinGapSeconds;
    if (sample.length < this.config.minimumSignatureSamples) return near ? boundary : Infinity;
    let repeated = Infinity;
    for (let k = 0; k < past.length; k += 3) {
      if (past[k].t < rows[0].t - VIDEO_FOLLOW.tracking.repeatSeconds) continue;
      let sum = 0, count = 0, cursor = k;
      for (const row of sample) {
        const target = past[k].t + row.t - rows[0].t;
        while (cursor + 1 < past.length && Math.abs(past[cursor + 1].t - target) < Math.abs(past[cursor].t - target)) cursor++;
        if (Math.abs(past[cursor].t - target) > 0.2) continue;
        sum += VideoRoutineDiscovery.distance(row.actor.body, past[cursor].actor.body);
        count++;
      }
      if (count >= Math.max(this.config.minimumSignatureSamples, sample.length * 0.8)) repeated = Math.min(repeated, sum / count);
    }
    return Number.isFinite(repeated) ? near ? boundary * 0.25 + repeated * 0.75 : repeated : near ? boundary : Infinity;
  }
  assign(groups, routines) {
    const choices = groups.map((group) => {
      const rows = group.flat().sort((a, b) => a.index - b.index);
      const appearance = VideoAppearanceDescriptor.average(rows.map((row) => row.actor.appearance));
      return routines.filter((r) => rows[0].t >= r.last.t).map((r) => {
        const motion = this.joinCost(rows, r), look = VideoAppearanceDescriptor.distance(appearance, r.appearance);
        const cost = Number.isFinite(look) ? Math.min(Number.isFinite(motion) ? motion : this.config.newRoutineCost, this.config.newRoutineCost) * this.config.motionWeight + look * this.config.appearanceWeight : motion;
        return { routine: r, cost };
      }).filter((c) => c.cost < this.config.newRoutineCost).sort((a, b) => a.cost - b.cost).concat({ routine: null, cost: this.config.newRoutineCost });
    });
    const slots = new Map(routines.map((routine, i) => [routine, i]));
    const matrix = choices.map((row, i) => {
      const costs = Array(routines.length + groups.length).fill(Infinity);
      for (const choice of row) costs[choice.routine ? slots.get(choice.routine) : routines.length + i] = choice.cost;
      return costs;
    });
    const best = VideoRoutineAssignment.solve(matrix);
    return best.columns.map((column, row) => ({
      routine: routines[column] || null,
      cost: matrix[row][column],
      ambiguous: column < routines.length && VideoRoutineAssignment.solve(matrix, row, column).cost - best.cost < this.config.joinMarginDegrees
    }));
  }
  classify(routines) {
    const distinct = [];
    for (const routine of routines) {
      routine.kind = distinct.every((other) => {
        let observed = 0, different = 0, persistent = 0, run = 0;
        const flush = () => {
          if (run >= this.config.minimumDifferenceRunSeconds) persistent += run;
          run = 0;
        };
        for (let i = 1; i < routine.frames.length; i++) {
          const a = routine.frames[i], b = other.frames[i];
          if (!a.w || !(b == null ? void 0 : b.w) || !a.trusted || !b.trusted) {
            flush();
            continue;
          }
          const dt = Math.min(0.5, Math.max(0, a.t - routine.frames[i - 1].t));
          observed += dt;
          if (VideoRoutineDiscovery.distance(a.body, b.body) > this.config.styleDegrees) {
            different += dt;
            run += dt;
          } else flush();
        }
        flush();
        return persistent >= this.config.minimumDistinctSeconds && different / Math.max(1e-3, observed) >= this.config.minimumDifferentFraction;
      }) ? "routine" : "fragment";
      if (routine.kind === "routine") distinct.push(routine);
    }
    return routines.sort((a, b) => (a.kind === "fragment") - (b.kind === "fragment") || b.trustedCoverage - a.trustedCoverage);
  }
  finish() {
    const shots = /* @__PURE__ */ new Map(), common = /* @__PURE__ */ new Map(), units = [];
    this.frames.forEach((frame, index) => {
      const visible = (frame.actors || []).filter((a) => a.confidence >= VIDEO_FOLLOW.tracking.confidence);
      if (visible.length > 1 && visible.every((a) => visible.every((b) => VideoRoutineDiscovery.distance(a.body, b.body) <= this.config.styleDegrees)))
        common.set(index, visible.slice().sort((a, b) => b.confidence - a.confidence)[0]);
      if (!shots.has(frame.shot)) shots.set(frame.shot, /* @__PURE__ */ new Map());
      const tracks = shots.get(frame.shot);
      for (const actor of frame.actors || []) {
        if (!tracks.has(actor.id)) tracks.set(actor.id, []);
        tracks.get(actor.id).push({ index, t: frame.t, actor });
      }
    });
    const routines = [];
    for (const tracks of shots.values()) {
      const groups = [];
      for (const track of tracks.values()) {
        if (track.length < this.config.minimumOverlap) continue;
        const group = groups.find((g) => g.every((member) => this.compatible(track, member)));
        if (group) group.push(track);
        else groups.push([track]);
      }
      const assignments = this.assign(groups, routines);
      for (const [groupIndex, group] of groups.entries()) {
        const rows = group.flat().sort((a, b) => a.index - b.index), first = rows[0];
        const assignment = assignments[groupIndex];
        let routine = assignment == null ? void 0 : assignment.routine;
        if (!routine) {
          routine = { id: routines.length + 1, observations: /* @__PURE__ */ new Map(), people: /* @__PURE__ */ new Set(), ambiguous: false };
          routines.push(routine);
        }
        routine.ambiguous || (routine.ambiguous = !!(assignment == null ? void 0 : assignment.ambiguous));
        const observations = VideoRoutineSections.observations(group);
        units.push({
          shot: this.frames[first.index].shot,
          ordinal: groupIndex + 1,
          parentId: routine.id,
          ambiguous: !!(assignment == null ? void 0 : assignment.ambiguous),
          people: new Set(rows.map((row) => row.actor.id)).size,
          observations
        });
        for (const row of rows) routine.people.add(row.actor.id);
        for (const [index, actor] of observations) {
          routine.observations.set(index, { ...actor, associationUncertain: !!(assignment == null ? void 0 : assignment.ambiguous) });
          routine.people.add(actor.id);
        }
        routine.last = rows.at(-1);
        routine.appearance = VideoAppearanceDescriptor.average([...routine.observations.values()].map((a) => a.appearance));
      }
    }
    const results = routines.map((r) => {
      var _a;
      const policy = new VideoTemporalPolicy(this.options.learned === false ? null : VIDEO_POLICY, this.options.cameraMode);
      const frames = this.frames.map((f, i) => {
        const own = r.observations.get(i);
        const actor = (own == null ? void 0 : own.associationUncertain) ? common.get(i) || own : own || common.get(i);
        const state = policy.step((actor == null ? void 0 : actor.associationUncertain) ? null : (actor == null ? void 0 : actor.body) || null, f.cut ? Math.max(0.25, f.scene) : f.scene, f.cut, actor && actor.confidence >= VIDEO_FOLLOW.tracking.confidence ? 1 : 0);
        return { ...f, ...state, w: (actor == null ? void 0 : actor.w) || null, p: (actor == null ? void 0 : actor.p) || null, track: (actor == null ? void 0 : actor.id) || null };
      });
      return {
        id: r.id,
        frames,
        sourceStart: 0,
        sourceEnd: ((_a = this.frames.at(-1)) == null ? void 0 : _a.t) || 0,
        coverage: frames.filter((f) => f.w).length / Math.max(1, this.frames.length),
        trustedCoverage: frames.filter((f) => f.w && f.trusted).length / Math.max(1, this.frames.length),
        people: r.people.size,
        ambiguous: r.ambiguous
      };
    }).sort((a, b) => b.coverage - a.coverage);
    const ranked = this.classify(results);
    const qualified = new Set(ranked.filter((r) => r.kind === "routine" && r.trustedCoverage >= this.config.minimumSaveCoverage).map((r) => r.id));
    const sections = VideoRoutineSections.build(units, this.frames, this.options, this.config, qualified);
    return qualified.size ? [...ranked, ...sections] : [...sections, ...ranked];
  }
}
class VideoSubjectTracker {
  constructor(options, config = VIDEO_FOLLOW) {
    this.options = options;
    this.config = config.tracking;
    this.tracks = [];
    this.nextId = 1;
    this.primary = null;
    this.shot = 0;
    this.lastImage = null;
    this.history = [];
    this.policy = new VideoTemporalPolicy(VIDEO_POLICY, options.cameraMode);
    this.observations = [];
  }
  imageChange(image) {
    if (!image) return 0;
    let difference = 0, count = 0;
    if (this.lastImage && this.lastImage.length === image.length)
      for (let i = 0; i < image.length; i += 4) {
        difference += Math.abs(image[i] - this.lastImage[i]) + Math.abs(image[i + 1] - this.lastImage[i + 1]) + Math.abs(image[i + 2] - this.lastImage[i + 2]);
        count += 3;
      }
    this.lastImage = new Uint8Array(image);
    return count ? difference / count / 255 : 0;
  }
  candidates(result, image = null) {
    return (result.worldLandmarks || []).map((points, i) => {
      var _a;
      const w = points.map((p2) => {
        var _a2;
        return { x: p2.x, y: p2.y, z: p2.z, v: (_a2 = p2.visibility) != null ? _a2 : 1 };
      });
      const p = result.landmarks[i].map((v) => {
        var _a2;
        return { x: v.x, y: v.y, v: (_a2 = v.visibility) != null ? _a2 : 1 };
      });
      const body = VideoBodyMotion.measure(w, false);
      const cx = (p[11].x + p[12].x + p[23].x + p[24].x) / 4, cy = (p[11].y + p[12].y + p[23].y + p[24].y) / 4;
      const size = Math.hypot(p[11].x - p[23].x, p[11].y - p[23].y) + Math.hypot(p[12].x - p[24].x, p[12].y - p[24].y);
      const appearance = ((_a = result.appearances) == null ? void 0 : _a[i]) || VideoAppearanceDescriptor.measure(p, image, this.config.imageWidth, this.config.imageHeight);
      return { w, p, body, cx, cy, size, appearance, confidence: (body == null ? void 0 : body.confidence) || 0 };
    }).filter((p) => p.body && p.size > 0.025);
  }
  step(result, t, image = null, sceneOverride = null) {
    const scene2 = sceneOverride != null ? sceneOverride : this.imageChange(image);
    const candidates = this.candidates(result, image), used = /* @__PURE__ */ new Set();
    const sameView = this.primary && candidates.some((c) => Math.hypot(c.cx - this.primary.cx, c.cy - this.primary.cy) < 0.06 && Math.abs(Math.log(c.size / this.primary.size)) < 0.15 && c.body.viewUp.angleTo(this.primary.body.viewUp) < 0.5 && c.body.viewLeft.angleTo(this.primary.body.viewLeft) < 0.7);
    const cut = this.options.cameraMode !== "fixed" && scene2 > this.config.cutDifference && !sameView;
    const policyScene = cut ? Math.max(0.25, scene2) : scene2;
    if (cut) {
      this.shot++;
      this.tracks = [];
      this.observations = [];
    }
    for (const c of candidates) {
      let match = null, cost = Infinity;
      for (const previous of this.tracks) if (!used.has(previous.id) && t - previous.t <= this.config.missingSeconds) {
        const spatial = Math.hypot(c.cx - previous.cx, c.cy - previous.cy);
        const distance = spatial + 0.15 * Math.abs(Math.log(c.size / previous.size)) + VideoBodyMotion.difference(c.body, previous.body) / 180 * 0.04;
        if (spatial < this.config.identityGap && distance < cost) {
          match = previous;
          cost = distance;
        }
      }
      c.id = match ? match.id : this.nextId++;
      c.t = t;
      used.add(c.id);
    }
    const actors = candidates.map((c) => ({ id: c.id, body: c.body, w: c.w, p: c.p, cx: c.cx, size: c.size, appearance: c.appearance, confidence: c.confidence }));
    const explicit = this.options.dancer && this.options.dancer !== "auto";
    let chosen = candidates.find((c) => String(c.id) === String(this.options.dancer));
    if (!chosen && this.primary && (!explicit || String(this.primary.id) === String(this.options.dancer))) chosen = candidates.find((c) => c.id === this.primary.id);
    if (!chosen && this.primary && (cut || t - this.primary.t > this.config.missingSeconds)) {
      const ranked = candidates.map((c) => ({ c, score: VideoBodyMotion.difference(c.body, this.primary.body) + THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(c.body.twist - this.primary.body.twist))) })).sort((a, b) => a.score - b.score);
      if (ranked.length && ranked[0].score < this.config.styleDegrees && (ranked.length === 1 || ranked[1].score - ranked[0].score > 8)) {
        chosen = ranked[0].c;
        chosen.id = this.primary.id;
      }
    }
    if (!chosen && (explicit || this.primary && !cut && t - this.primary.t <= this.config.missingSeconds)) {
      const state2 = this.policy.step(null, policyScene, cut, 0);
      return { t, w: null, p: null, shot: this.shot, cut, scene: scene2, ...state2, candidates: candidates.length, actors };
    }
    if (!chosen && candidates.length) {
      const previousBody = this.policy.accepted;
      chosen = candidates.slice().sort((a, b) => {
        const score = (c) => {
          var _a;
          return (previousBody ? VideoBodyMotion.difference(c.body, previousBody) / 90 : 0) + Math.abs(c.cx - ((_a = this.options.anchorX) != null ? _a : 0.5)) - c.size;
        };
        return score(a) - score(b);
      })[0];
    }
    this.tracks = candidates;
    if (!chosen) return { t, w: null, p: null, shot: this.shot, cut, scene: scene2, ...this.policy.step(null, policyScene, cut, 0), candidates: 0, actors };
    this.primary = chosen;
    this.observations.push(chosen.body);
    this.observations = this.observations.slice(-3);
    if (this.observations.length === 3) {
      const median = (values) => values.sort((a, b) => a - b)[1];
      const smooth = { ...chosen.body, arms: chosen.body.arms.map((a) => ({ ...a })) };
      for (const arm of [0, 1]) for (const key of ["upper", "fore"])
        smooth.arms[arm][key] = new THREE.Vector3(...["x", "y", "z"].map((axis) => median(this.observations.map((b) => b.arms[arm][key][axis])))).normalize();
      smooth.twist = chosen.body.twist + median(this.observations.map((b) => VideoBodyMotion.wrap(b.twist - chosen.body.twist)));
      smooth.roll = median(this.observations.map((b) => b.roll));
      chosen.body = smooth;
      smooth.hipYaw = chosen.body.hipYaw + median(this.observations.map((b) => VideoBodyMotion.wrap(b.hipYaw - chosen.body.hipYaw)));
    }
    const supporters = candidates.filter((c) => VideoBodyMotion.styleDifference(c.body, chosen.body) <= this.config.styleDegrees);
    const styles = [];
    for (const c of candidates) {
      const group = styles.find((s) => VideoBodyMotion.styleDifference(c.body, s.leader.body) <= this.config.styleDegrees);
      if (group) group.people.push(c.id);
      else styles.push({ leader: c, people: [c.id] });
    }
    const state = this.policy.step(chosen.body, policyScene, cut, chosen.confidence >= this.config.confidence ? 1 : 0);
    let repeatAt = null;
    for (const old of this.history) if (t - old.t > 1 && t - old.t <= this.config.repeatSeconds && VideoBodyMotion.styleDifference(chosen.body, old.body) < 3) {
      repeatAt = old.t;
      break;
    }
    this.history.push({ t, body: chosen.body });
    this.history = this.history.filter((h) => t - h.t <= this.config.repeatSeconds);
    return {
      t,
      w: chosen.w,
      p: chosen.p,
      shot: this.shot,
      cut,
      scene: scene2,
      ...state,
      actors,
      track: chosen.id,
      candidates: candidates.length,
      supporters: supporters.length,
      repeatAt,
      styles: styles.map((s) => ({ people: s.people, x: s.leader.cx })),
      people: candidates.map((c) => ({ id: c.id, x: c.cx, y: c.cy }))
    };
  }
}
class VideoRigFitter {
  constructor(options) {
    this.options = options;
    this.settings = VIDEO_FOLLOW.fitting;
    this.tables = {};
  }
  bodyTable(joint) {
    if (this.tables[joint]) return this.tables[joint];
    const saved = pose, rows = [];
    try {
      pose = RIG.neutral.slice();
      for (let v = RIG.min[joint]; v <= RIG.max[joint]; v += 0.5) {
        pose[joint] = v;
        applyPose();
        robot.updateMatrixWorld(true);
        let angle;
        if (joint === 8) {
          const front = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.getWorldQuaternion(new THREE.Quaternion()));
          angle = Math.atan2(front.x, front.z);
        } else {
          const local = (o) => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
          const line = local(jointGroups[0]).sub(local(jointGroups[4]));
          angle = Math.atan2(line.y, Math.hypot(line.x, line.z));
        }
        rows.push({ v, angle });
      }
    } finally {
      pose = saved;
      applyPose();
      robot.updateMatrixWorld(true);
    }
    const base = rows.reduce((a, b) => Math.abs(b.v - RIG.neutral[joint]) < Math.abs(a.v - RIG.neutral[joint]) ? b : a).angle;
    return this.tables[joint] = { rows, base };
  }
  setBody(joint, target) {
    const table = this.bodyTable(joint);
    const best = table.rows.reduce((a, b) => Math.abs(VideoBodyMotion.wrap(b.angle - table.base - target)) < Math.abs(VideoBodyMotion.wrap(a.angle - table.base - target)) ? b : a);
    pose[joint] = clampJ(joint, best.v);
  }
  armCost(arm, bones) {
    applyPose();
    robot.updateMatrixWorld(true);
    const local = (o) => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
    const s = local(jointGroups[arm * 4]), e = local(elbowBalls[arm]), w = local(wristBalls[arm]);
    const upper = e.clone().sub(s).normalize(), fore = w.clone().sub(e).normalize();
    return 1 - upper.dot(bones.upper) + 1 - fore.dot(bones.fore);
  }
  arm(arm, bones, first) {
    const before = pose.slice();
    const objective = () => this.armCost(arm, bones) + this.settings.continuityWeight * pose.slice(arm * 4, arm * 4 + 4).reduce((sum, v, k) => sum + (v - before[arm * 4 + k]) ** 2, 0) / 1e4;
    vidFitArm(arm, bones, first);
    let bestPose = pose.slice(), best = objective();
    const seeds = first ? [pose.slice(), before, RIG.neutral.map((v, j) => j >= arm * 4 && j < arm * 4 + 4 ? v : pose[j])] : [pose.slice(), before];
    for (const seed of seeds) {
      pose = seed.slice();
      for (const step of this.settings.steps) for (let pass = 0; pass < this.settings.passes; pass++) {
        let improved = false;
        for (let j = arm * 4; j < arm * 4 + 4; j++) {
          const old = pose[j];
          let chosen = old;
          const cost = objective;
          let score2 = cost();
          for (const sign of [-1, 1]) {
            pose[j] = clampJ(j, old + sign * step);
            const value = cost();
            if (value < score2 - 1e-8) {
              score2 = value;
              chosen = pose[j];
              improved = true;
            }
          }
          pose[j] = chosen;
        }
        if (!improved) break;
      }
      const score = objective();
      if (score < best + 1e-8) {
        best = score;
        bestPose = pose.slice();
      }
    }
    pose = bestPose;
    applyPose();
    return this.armCost(arm, bones);
  }
  repair(target, previous) {
    if (!collisionAt(target)) return { pose: target, repaired: false };
    let best = previous && !collisionAt(previous) ? previous.slice() : null;
    let distance = best ? Math.hypot(...best.map((v, j) => v - target[j])) : Infinity;
    const consider = (candidate) => {
      if (collisionAt(candidate)) return;
      const d = Math.hypot(...candidate.map((v, j) => v - target[j]));
      if (d < distance) {
        best = candidate.slice();
        distance = d;
      }
    };
    consider(RIG.neutral.map((v, j) => clampJ(j, v)));
    for (const step of this.settings.repairDegrees) {
      for (let j = 0; j < NJ; j++) for (const sign of [-1, 1]) {
        const candidate = target.slice();
        candidate[j] = clampJ(j, candidate[j] + sign * step);
        consider(candidate);
      }
      if (best && distance < step) break;
    }
    const random = safeRng(17);
    for (let k = 0; k < 64; k++) {
      const candidate = target.map((v, j) => clampJ(j, v + (random() - 0.5) * (k < 32 ? 24 : 60)));
      consider(candidate);
    }
    return best ? { pose: best, repaired: true } : null;
  }
  frames(frames) {
    const saved = pose, poses = [], times = [], targets = [], acceptedFrames = [], quality = { repaired: 0, missing: 0, uncertain: 0, worstBoneDegrees: 0 };
    let previous = null, shot = null;
    try {
      pose = RIG.neutral.map((v, j) => clampJ(j, v));
      for (const frame of frames) {
        let body = frame.body;
        if (body) body = { ...body, arms: body.arms.map((a) => ({
          ...a,
          upper: new THREE.Vector3(a.upper.x, a.upper.y, a.upper.z),
          fore: new THREE.Vector3(a.fore.x, a.fore.y, a.fore.z)
        })) };
        else body = VideoBodyMotion.measure(frame.w, false);
        if (body && this.options.mirror) body = {
          ...body,
          twist: -body.twist,
          roll: -body.roll,
          arms: [body.arms[1], body.arms[0]].map((a) => ({
            ...a,
            upper: new THREE.Vector3(-a.upper.x, a.upper.y, a.upper.z),
            fore: new THREE.Vector3(-a.fore.x, a.fore.y, a.fore.z)
          }))
        };
        const trusted = frame.trusted !== false;
        if (!body || !trusted) {
          quality[body ? "uncertain" : "missing"]++;
        } else if (!(previous && frame.action === "hold")) {
          if (this.options.waist) this.setBody(8, frame.waist == null ? body.twist : frame.waist * (this.options.mirror ? -1 : 1));
          if (this.options.shrug) this.setBody(9, body.roll);
          applyPose();
          for (const a of [0, 1]) if (body.arms[a].ok) {
            this.arm(a, body.arms[a], previous === null || shot !== frame.shot);
          }
        }
        const target = this.repair(pose.map((v, j) => clampJ(j, v)), previous);
        if (!target) {
          quality.uncertain++;
          continue;
        }
        if (target.repaired) quality.repaired++;
        pose = target.pose.slice();
        previous = pose.slice();
        shot = frame.shot;
        poses.push(pose.slice());
        times.push(frame.t * 1e3);
        targets.push(body && trusted ? body : null);
        acceptedFrames.push(frame);
      }
      if (this.options.smooth !== false && VIDEO_FOLLOW.smoothing && poses.length > 1) {
        const smoothed = new VideoMotionSmoother().apply(poses, times, acceptedFrames);
        quality.smoothing = { before: smoothed.before, after: smoothed.after };
        let previousSafe = poses[0];
        for (let i = 0; i < poses.length; i++) {
          const repaired = this.repair(smoothed.poses[i], previousSafe);
          poses[i] = repaired ? repaired.pose.slice() : previousSafe.slice();
          previousSafe = poses[i];
        }
        quality.smoothing.afterRepair = VideoMotionSmoother.quality(poses, times);
      }
    } finally {
      pose = saved;
      applyPose();
      robot.updateMatrixWorld(true);
    }
    return poses.length ? { poses, times, targets, videoMs: Math.round(times.at(-1)), quality, mirror: this.options.mirror, waist: this.options.waist, shrug: this.options.shrug } : null;
  }
  static assess(fit, made) {
    if (!fit.targets || !made.keys.length) return null;
    const saved = pose, errors = [];
    let sum = 0, worst = 0, count = 0;
    try {
      fit.targets.forEach((body, i) => {
        if (!body) return;
        pose = easeKeys(made.keys, this.clockForSource(made.keys, fit.times[i]).ms, "video").pose;
        applyPose();
        robot.updateMatrixWorld(true);
        const local = (o) => bodyGroup.worldToLocal(o.getWorldPosition(new THREE.Vector3()));
        let error = 0;
        for (const a of [0, 1]) if (body.arms[a].ok) {
          const s = local(jointGroups[a * 4]), e = local(elbowBalls[a]), w = local(wristBalls[a]);
          for (const [got, wanted] of [[e.clone().sub(s).normalize(), body.arms[a].upper], [w.clone().sub(e).normalize(), body.arms[a].fore]]) {
            const angle = THREE.MathUtils.radToDeg(got.angleTo(wanted));
            error = Math.max(error, angle);
            sum += angle;
            count++;
          }
        }
        worst = Math.max(worst, error);
        errors.push({ t: fit.times[i], degrees: Math.round(error * 10) / 10 });
      });
    } finally {
      pose = saved;
      applyPose();
      robot.updateMatrixWorld(true);
    }
    return {
      meanBoneDegrees: count ? sum / count : null,
      worstBoneDegrees: worst,
      samples: errors,
      measuredAfterCollisionAndTiming: true,
      limitedTransitions: made.partial,
      pathCorrections: { around: made.safe.around, dropped: made.safe.dropped, failed: made.safe.failed }
    };
  }
  static clockForSource(keys2, sourceMs) {
    var _a, _b;
    if (!keys2.length || !Number.isFinite(keys2[0].sourceMs)) return { ms: Math.max(0, sourceMs), rate: 1 };
    let clock = 0;
    for (let i = 0; i < keys2.length; i++) {
      const key = keys2[i], arrival = i ? clock + key.t : 0;
      if (i && sourceMs <= key.sourceMs) {
        const previous = keys2[i - 1], from = (_a = previous.sourceHoldEnd) != null ? _a : previous.sourceMs;
        const fraction = Math.max(0, Math.min(1, (sourceMs - from) / Math.max(1, key.sourceMs - from)));
        return { ms: clock + fraction * key.t, rate: (key.sourceMs - from) / Math.max(1, key.t) };
      }
      const end = (_b = key.sourceHoldEnd) != null ? _b : key.sourceMs;
      if (sourceMs < end) {
        const fraction = Math.max(0, Math.min(1, (sourceMs - key.sourceMs) / Math.max(1, end - key.sourceMs)));
        return { ms: arrival + fraction * (key.hold || 0), rate: (end - key.sourceMs) / Math.max(1, key.hold || 0) };
      }
      clock = arrival + (key.hold || 0);
    }
    return { ms: clock, rate: 1 };
  }
  static sourceForClock(keys2, robotMs) {
    var _a, _b, _c, _d, _e;
    let clock = 0;
    for (let i = 0; i < keys2.length; i++) {
      const key = keys2[i], arrival = i ? clock + key.t : 0;
      if (i && robotMs <= arrival) {
        const from = (_a = keys2[i - 1].sourceHoldEnd) != null ? _a : keys2[i - 1].sourceMs;
        return { sourceMs: from + (key.sourceMs - from) * Math.max(0, (robotMs - clock) / Math.max(1, key.t)), rate: (key.sourceMs - from) / Math.max(1, key.t), end: false };
      }
      const end = arrival + (key.hold || 0);
      if (robotMs <= end) return { sourceMs: key.sourceMs + (((_b = key.sourceHoldEnd) != null ? _b : key.sourceMs) - key.sourceMs) * Math.max(0, (robotMs - arrival) / Math.max(1, key.hold || 0)), rate: (((_c = key.sourceHoldEnd) != null ? _c : key.sourceMs) - key.sourceMs) / Math.max(1, key.hold || 0), end: false };
      clock = end;
    }
    const last = keys2.at(-1);
    return { sourceMs: last ? (_e = (_d = last.sourceHoldEnd) != null ? _d : last.sourceMs) != null ? _e : robotMs : 0, rate: 1, end: true };
  }
}
class VideoCheckedPlayback {
  constructor(now = () => performance.now()) {
    this.now = now;
    this.manual = null;
    this.notified = false;
    this.robotMs = null;
    this.pausedAt = null;
  }
  reset(video) {
    this.manual = null;
    this.robotMs = null;
    this.pausedAt = null;
    this.notified = false;
    if (video) video.playbackRate = 1;
  }
  stop(video) {
    this.reset(video);
    video.pause();
  }
  pause(video) {
    if (this.manual) this.pausedAt = { robotMs: this.manual.robotMs + Math.max(0, this.now() - this.manual.wallMs), sourceSeconds: video.currentTime };
    this.manual = null;
    video.pause();
  }
  start(video, robotMs) {
    if (this.pausedAt && Math.abs(this.pausedAt.sourceSeconds - video.currentTime) < 1e-3) robotMs = this.pausedAt.robotMs;
    this.pausedAt = null;
    video.pause();
    this.manual = { robotMs, wallMs: this.now() };
    if (!this.notified) {
      this.notified = true;
      vidSay("Very slow detours play frame by frame; sound pauses. Play both pauses or resumes.");
    }
  }
  update(video, made, sourceMs, fromSeconds, endMs) {
    if (!(made == null ? void 0 : made.keys.length) || made.keepMusic !== false) return sourceMs;
    if (this.manual) {
      const robotMs = this.manual.robotMs + Math.max(0, this.now() - this.manual.wallMs);
      this.robotMs = robotMs;
      const next = VideoRigFitter.sourceForClock(made.keys, robotMs);
      if (next.end || next.sourceMs >= endMs) {
        this.stop(video);
        return Math.min(endMs, next.sourceMs);
      }
      const rate = next.rate;
      if (!video.seeking) {
        video.currentTime = fromSeconds + next.sourceMs / 1e3;
        if (rate >= 0.0625) {
          this.manual = null;
          video.playbackRate = Math.min(4, rate);
          video.play().catch(() => {
          });
        }
      }
      return next.sourceMs;
    }
    const mapped = VideoRigFitter.clockForSource(made.keys, sourceMs);
    this.robotMs = mapped.ms;
    if (mapped.rate < 0.0625) {
      if (!video.paused) {
        this.start(video, mapped.ms);
      }
    } else video.playbackRate = Math.min(4, mapped.rate);
    return sourceMs;
  }
}
const vidCheckedPlayback = new VideoCheckedPlayback();
const VID_LIB = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35";
const VID_MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task";
const VID_PTS = { sh: [11, 12], el: [13, 14], wr: [15, 16] };
const VID_FPS = 10;
const VID_SMOOTH = 2;
const VID_SEEN = 0.5;
const VID_DETAIL = [
  { id: "smooth", label: "Smooth — fewer moves", tol: 14 },
  { id: "normal", label: "Normal", tol: 8 },
  { id: "close", label: "Close — more moves", tol: 4 }
];
const VID_HAND = [
  { id: "video", label: "as in the video" },
  { id: "palm", label: "palm on top", want: 1 },
  { id: "back", label: "back of the hand on top", want: -1 },
  { id: "palm-force", label: "palm on top, always (the hand may move)", want: 1, force: true },
  { id: "back-force", label: "back on top, always (the hand may move)", want: -1, force: true }
];
const VID_USE = [
  { id: "keep", label: "Keep" },
  { id: "force", label: "Keep, hand side forced" },
  { id: "moment", label: "Use another moment…" },
  { id: "drop", label: "Leave out" }
];
let vidRoutines = [], vidRoutineRange = null;
let vidLib = null, vidLibMode = null, vidFrames = null, vidMade = null, vidStop = false, vidBusy = false, vidGeneration = 0, vidSeekCancel = null;
let vidFit = null, vidPicks = null;
async function vidLoadLib(mode = "single") {
  if (vidLib && vidLibMode === mode) return vidLib;
  if (vidLib) {
    vidLib.close();
    vidLib = null;
  }
  const mp = await import(VID_LIB + "/vision_bundle.mjs");
  let model = null;
  try {
    const store = await caches.open("mice-pose-model");
    let r = await store.match(VID_MODEL);
    if (!r) {
      await store.add(VID_MODEL);
      r = await store.match(VID_MODEL);
    }
    if (r) model = new Uint8Array(await r.arrayBuffer());
  } catch (e) {
    model = null;
  }
  const files = await mp.FilesetResolver.forVisionTasks(VID_LIB + "/wasm");
  const base = model ? { modelAssetBuffer: model } : { modelAssetPath: VID_MODEL };
  const make = (delegate) => mp.PoseLandmarker.createFromOptions(files, {
    baseOptions: { ...base, delegate },
    runningMode: "VIDEO",
    numPoses: mode !== "single" ? VIDEO_FOLLOW.tracking.people : 1
  });
  try {
    vidLib = await make("GPU");
  } catch (e) {
    vidLib = await make("CPU");
  }
  vidLibMode = mode;
  return vidLib;
}
function vidSay(text, bad, tech) {
  $("vidStat").textContent = text;
  $("vidStatTech").textContent = tech ? " " + tech : "";
  if (bad) notice(text);
}
function vidOpts() {
  var _a, _b, _c, _d, _e, _f, _g;
  const det = VID_DETAIL.find((d) => d.id === $("vidDetail").value) || VID_DETAIL[1];
  const h = [0, 1].map((a) => VID_HAND.find((x) => x.id === $("vidHand" + a).value) || {});
  return {
    tol: det.tol,
    mirror: $("vidMirror").checked,
    waist: $("vidWaist").checked,
    hand: h.map((x) => x.want || 0),
    force: h.map((x) => !!x.force),
    music: $("vidMusic").checked,
    subjectMode: ((_a = $("vidSubject")) == null ? void 0 : _a.value) || "auto",
    cameraMode: ((_b = $("vidCamera")) == null ? void 0 : _b.value) || "auto",
    dancer: ((_c = $("vidDancer")) == null ? void 0 : _c.value) || "auto",
    shrug: (_e = (_d = $("vidShrug")) == null ? void 0 : _d.checked) != null ? _e : false,
    learned: (_g = (_f = $("vidLearned")) == null ? void 0 : _f.checked) != null ? _g : true,
    anchorX: typeof vidSaved !== "undefined" && Number.isFinite(vidSaved == null ? void 0 : vidSaved.anchorX) ? Math.max(0, Math.min(1, vidSaved.anchorX)) : 0.5
  };
}
function vidFill() {
  const fill = (sel, list, pick) => {
    if (!sel || sel.options.length) return;
    list.forEach((o) => sel.add(new Option(o.label, o.id, false, o.id === pick)));
  };
  fill($("vidDetail"), VID_DETAIL, "normal");
  HANDS.forEach((h, a) => {
    const lbl = $("vidHandLbl" + a);
    if (lbl) lbl.textContent = h.label;
    fill($("vidHand" + a), VID_HAND, "video");
  });
  if (VIDEO_FOLLOW) {
    fill($("vidSubject"), VIDEO_FOLLOW.subjectModes, "auto");
    fill($("vidCamera"), VIDEO_FOLLOW.cameraModes, "auto");
  }
}
function vidModeChanged() {
  vidGeneration++;
  if (vidSeekCancel) vidSeekCancel();
  if (typeof vidCheckedPlayback !== "undefined") vidCheckedPlayback.reset($("vidPlayer"));
  if (vidBusy) vidStop = true;
  vidFrames = vidFit = vidMade = vidPicks = null;
  vidRoutines = [];
  vidRoutineRange = null;
  vidSay("Video choices or range changed. Press Make moves to read the performers again.");
}
function vidPick(file) {
  vidFill();
  if (!file) return;
  vidSetSrc(URL.createObjectURL(file), { kind: "file", name: file.name, file });
}
function vidDetectPerformers(lib, video, group) {
  if (!group) return lib.detectForVideo(video, performance.now());
  const people = [], canvas = document.createElement("canvas");
  for (const [x0, y0, x1, y1] of VIDEO_FOLLOW.tracking.crops) {
    canvas.width = Math.max(1, Math.round(video.videoWidth * (x1 - x0)));
    canvas.height = Math.max(1, Math.round(video.videoHeight * (y1 - y0)));
    canvas.getContext("2d").drawImage(
      video,
      video.videoWidth * x0,
      video.videoHeight * y0,
      canvas.width,
      canvas.height,
      0,
      0,
      canvas.width,
      canvas.height
    );
    const result = lib.detectForVideo(canvas, performance.now());
    for (let i = 0; i < (result.landmarks || []).length; i++) {
      const p = result.landmarks[i].map((v) => ({ ...v, x: x0 + v.x * (x1 - x0), y: y0 + v.y * (y1 - y0) }));
      const center = [11, 12, 23, 24].reduce((s, j) => [s[0] + p[j].x / 4, s[1] + p[j].y / 4], [0, 0]);
      const quality = [11, 12, 13, 14, 15, 16, 23, 24].reduce((s, j) => {
        var _a;
        return s + ((_a = p[j].visibility) != null ? _a : 1);
      }, 0);
      const old = people.findIndex((q) => Math.hypot(q.center[0] - center[0], q.center[1] - center[1]) < 0.028);
      const candidate = { p, w: result.worldLandmarks[i], center, quality };
      if (old < 0) people.push(candidate);
      else if (quality > people[old].quality) people[old] = candidate;
    }
  }
  people.sort((a, b) => a.center[0] - b.center[0]);
  return { landmarks: people.map((p) => p.p), worldLandmarks: people.map((p) => p.w) };
}
function vidSeek(video, seconds, generation) {
  return new Promise((resolve) => {
    var _a;
    let settled = false, timer = 0;
    const cancel = () => finish(false), done = () => finish(generation === vidGeneration && !vidStop), error = () => finish(false);
    function finish(ok) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      video.removeEventListener("seeked", done);
      video.removeEventListener("error", error);
      video.removeEventListener("loadeddata", ready);
      if (vidSeekCancel === cancel) vidSeekCancel = null;
      resolve(ok);
    }
    function ready() {
      if (!video.seeking && Math.abs(video.currentTime - seconds) < 1e-3) done();
    }
    vidSeekCancel = cancel;
    video.addEventListener("seeked", done);
    video.addEventListener("error", error);
    video.addEventListener("loadeddata", ready);
    timer = setTimeout(error, (_a = VIDEO_FOLLOW == null ? void 0 : VIDEO_FOLLOW.tracking.seekTimeoutMs) != null ? _a : 5e3);
    if (generation !== vidGeneration || vidStop) return cancel();
    if (video.readyState >= 2 && !video.seeking && Math.abs(video.currentTime - seconds) < 1e-3) return done();
    video.currentTime = seconds;
  });
}
async function vidRead() {
  const generation = vidGeneration;
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration)) {
    vidSay("Pick a video first.", true);
    return null;
  }
  vidSay("Loading the body finder (the first time needs the internet)…");
  let lib;
  let tracker, picture, discovery, readOptions;
  try {
    await videoFollowReady();
    vidFill();
    const options = vidOpts();
    readOptions = options;
    discovery = new VideoRoutineDiscovery(options);
    tracker = new VideoSubjectTracker({ ...options, mirror: false });
    if (!options.learned) tracker.policy.model = null;
    picture = document.createElement("canvas");
    picture.width = VIDEO_FOLLOW.tracking.imageWidth;
    picture.height = VIDEO_FOLLOW.tracking.imageHeight;
    lib = await vidLoadLib(options.subjectMode);
  } catch (e) {
    vidSay("Could not load the body finder. It needs the internet the first time; check the connection and press Make moves again.", true);
    $("vidTech").textContent = String(e && e.message || e);
    return null;
  }
  const from = Math.max(0, +$("vidFrom").value || 0);
  const to = Math.min(v.duration, +$("vidTo").value || v.duration);
  const frames = [];
  v.pause();
  for (let t = from; t <= to + 1e-6 && !vidStop && generation === vidGeneration; t += 1 / VID_FPS) {
    if (!await vidSeek(v, Math.min(t, v.duration - 1e-3), generation)) {
      if (!vidStop && generation === vidGeneration) vidSay("The video could not reach that moment. Try reading it again.", true);
      return null;
    }
    const r = vidDetectPerformers(lib, v, vidLibMode !== "single");
    const context = picture.getContext("2d", { willReadFrequently: true });
    context.drawImage(v, 0, 0, picture.width, picture.height);
    const frame = tracker.step(r, t - from, context.getImageData(0, 0, picture.width, picture.height).data);
    frames.push(frame);
    discovery.add(frame);
    const select2 = $("vidDancer");
    for (const person of frame.people || []) if (select2 && ![...select2.options].some((o) => o.value === String(person.id)))
      select2.add(new Option("Performer " + person.id, String(person.id)));
    vidDraw(frame.p, frame.people);
    vidSay("Reading the video: " + Math.round(100 * (t - from) / Math.max(0.1, to - from)) + "%");
  }
  if (vidStop || generation !== vidGeneration) return null;
  vidRoutines = readOptions.subjectMode !== "single" && readOptions.dancer === "auto" ? discovery.finish() : [];
  vidRoutineRange = { from, to };
  const select = $("vidRoutine"), previous = select == null ? void 0 : select.value;
  if (select) {
    select.innerHTML = "";
    select.add(new Option("Automatic main routine", "auto"));
    vidRoutines.forEach((routine, i) => {
      const label = routine.kind === "segment" ? "Scene segment " + (i + 1) + " · " + (routine.sourceEnd - routine.sourceStart).toFixed(1) + " s" : (routine.kind === "fragment" ? "Partial routine " : "Routine ") + routine.id;
      select.add(new Option(label + " · " + Math.round(routine.trustedCoverage * 100) + "% reliable" + (routine.ambiguous ? " · check cut" : ""), String(routine.id)));
    });
    select.value = vidRoutines.some((r) => String(r.id) === previous) ? previous : "auto";
  }
  const selected = vidRoutines.find((r) => String(r.id) === (select == null ? void 0 : select.value)) || vidRoutines[0];
  return selected ? vidSelectFrames(selected) : frames;
}
const VID_BONES = [
  [11, 12],
  [11, 23],
  [12, 24],
  [23, 24],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16]
];
function vidDraw(pts, people) {
  const v = $("vidPlayer"), c = $("vidOverlay");
  c.width = v.clientWidth;
  c.height = v.clientHeight;
  c.style.left = v.offsetLeft + "px";
  c.style.top = v.offsetTop + "px";
  const g = c.getContext("2d");
  g.clearRect(0, 0, c.width, c.height);
  if (!pts || !v.videoWidth) return;
  const k = Math.min(c.width / v.videoWidth, c.height / v.videoHeight);
  const w = v.videoWidth * k, h = v.videoHeight * k, ox = (c.width - w) / 2, oy = (c.height - h) / 2;
  const css = getComputedStyle(document.documentElement);
  g.strokeStyle = g.fillStyle = css.getPropertyValue("--acc").trim() || "currentColor";
  g.lineWidth = 3;
  const P = (i) => [ox + pts[i].x * w, oy + pts[i].y * h];
  const seen = (i) => pts[i] && (pts[i].v == null || pts[i].v >= VID_SEEN);
  g.beginPath();
  for (const [a, b] of VID_BONES) if (seen(a) && seen(b)) {
    g.moveTo(...P(a));
    g.lineTo(...P(b));
  }
  g.stroke();
  for (const i of [11, 12, 13, 14, 15, 16]) if (seen(i)) {
    g.beginPath();
    g.arc(...P(i), 4, 0, 2 * Math.PI);
    g.fill();
  }
  g.font = "14px sans-serif";
  for (const person of people || []) g.fillText(String(person.id), ox + person.x * w, oy + person.y * h);
}
function vidBodyFrame(w, mirror) {
  const pt = (i) => {
    const j = mirror ? i % 2 ? i + 1 : i - 1 : i;
    const p = w[j];
    return { at: new THREE.Vector3(mirror ? -p.x : p.x, -p.y, -p.z), seen: p.v == null ? 1 : p.v };
  };
  const L = pt(VID_PTS.sh[0]), R = pt(VID_PTS.sh[1]);
  const left = L.at.clone().sub(R.at);
  left.y = 0;
  if (left.length() < 1e-4) return null;
  left.normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const front = left.clone().cross(up);
  const toBody = (d) => new THREE.Vector3(d.dot(left), d.dot(up), d.dot(front)).normalize();
  const arms = [0, 1].map((a) => {
    const S = pt(VID_PTS.sh[a]), E = pt(VID_PTS.el[a]), W = pt(VID_PTS.wr[a]);
    const ok = Math.min(S.seen, E.seen, W.seen) >= VID_SEEN;
    return { ok, upper: toBody(E.at.clone().sub(S.at)), fore: toBody(W.at.clone().sub(E.at)) };
  });
  return { arms, yaw: Math.atan2(front.x, front.z) };
}
function vidBones(frames, mirror) {
  const raw = frames.map((f) => f.w ? vidBodyFrame(f.w, mirror) : null);
  const out = frames.map((f, i) => ({ t: f.t, yaw: raw[i] ? raw[i].yaw : null, arms: [null, null] }));
  for (const a of [0, 1]) {
    const seen = raw.map((r, i) => r && r.arms[a].ok ? i : -1).filter((i) => i >= 0);
    if (!seen.length) continue;
    for (let i = 0, k = 0; i < raw.length; i++) {
      while (k + 1 < seen.length && Math.abs(seen[k + 1] - i) <= Math.abs(seen[k] - i)) k++;
      out[i].arms[a] = raw[seen[k]].arms[a];
    }
  }
  const smooth = (get) => out.map((_, i) => {
    const s = new THREE.Vector3();
    for (let j = Math.max(0, i - VID_SMOOTH); j <= Math.min(out.length - 1, i + VID_SMOOTH); j++) {
      const v = get(j);
      if (v) s.add(v);
    }
    return s.lengthSq() > 1e-9 ? s.normalize() : null;
  });
  const res = out.map((o) => ({ t: o.t, yaw: o.yaw, arms: [null, null] }));
  for (const a of [0, 1]) {
    const up = smooth((j) => out[j].arms[a] && out[j].arms[a].upper);
    const fo = smooth((j) => out[j].arms[a] && out[j].arms[a].fore);
    res.forEach((r, i) => {
      if (up[i] && fo[i]) r.arms[a] = { upper: up[i], fore: fo[i] };
    });
  }
  return res;
}
function vidWaistTable() {
  const tbl = [];
  for (let v = RIG.min[8]; v <= RIG.max[8]; v += 1) {
    pose[8] = v;
    applyPose();
    robot.updateMatrixWorld(true);
    const d = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.getWorldQuaternion(new THREE.Quaternion()));
    tbl.push({ v, yaw: Math.atan2(d.x, d.z) });
  }
  return tbl;
}
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
  robot.updateMatrixWorld(true);
  const achievedElbow = bodyGroup.worldToLocal(W(elbowBalls[arm]));
  const achievedHand = bodyGroup.localToWorld(achievedElbow.addScaledVector(bones.fore, foreLen));
  ccdChain(el, wristBalls[arm], achievedHand, first ? 24 : 8);
  applyPose();
}
function vidThin(times, poses, tol) {
  const keep = /* @__PURE__ */ new Set([0, poses.length - 1]);
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
    for (let i = a + 1; i < b; i++) {
      const d = off(a, b, i);
      if (d > far) {
        far = d;
        worst = i;
      }
    }
    if (worst >= 0) {
      keep.add(worst);
      stack.push([a, worst], [worst, b]);
    }
  }
  return [...keep].sort((x, y) => x - y);
}
function vidFitFrames(frames, opts) {
  if (opts.subjectMode && VIDEO_FOLLOW) return new VideoRigFitter(opts).frames(frames);
  const bones = vidBones(frames, opts.mirror);
  if (!bones.some((b) => b.arms[0] || b.arms[1])) return null;
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
      poses.push(pose.map((v) => Math.round(v * 10) / 10));
    });
  } finally {
    pose = saved;
    applyPose();
  }
  const times = bones.map((b) => b.t * 1e3);
  return {
    times,
    poses,
    mirror: opts.mirror,
    waist: opts.waist,
    videoMs: Math.round(times[times.length - 1] || 0)
  };
}
function vidPicksFor(fit, tol) {
  return vidThin(fit.times, fit.poses, tol).map((i) => ({ i, use: "keep", at: fit.times[i] }));
}
function vidPoseAt(fit, ms) {
  let best = 0;
  fit.times.forEach((t, i) => {
    if (Math.abs(t - ms) < Math.abs(fit.times[best] - ms)) best = i;
  });
  return fit.poses[best];
}
function vidForceHand(p, arm, want, near) {
  const r = near ? { pose: p, upness: palmUpnessOf(p, arm) } : facePalm(p, arm, want);
  if (!r || want * r.upness > 0.5) return r;
  const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
  const saved = pose;
  try {
    pose = p.slice();
    applyPose();
    robot.updateMatrixWorld(true);
    const h0 = wristBalls[arm].getWorldPosition(new THREE.Vector3());
    const cost = () => {
      applyPose();
      robot.updateMatrixWorld(true);
      return wristBalls[arm].getWorldPosition(new THREE.Vector3()).distanceTo(h0) + 2e3 * Math.max(0, 0.6 - want * palmUpness(arm));
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
        if (c < best - 0.01) {
          best = c;
          better = true;
        } else pose[j] = old;
      }
      if (!better) break;
    }
    applyPose();
    return { pose: pose.slice(), upness: palmUpness(arm) };
  } finally {
    pose = saved;
    applyPose();
  }
}
function vidReachIn(from, to, ms) {
  if (minTime(from, to) <= ms) return to;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  let lo = 0, hi = 1;
  for (let k = 0; k < 14; k++) {
    const m = (lo + hi) / 2;
    if (minTime(from, at(m)) <= ms) lo = m;
    else hi = m;
  }
  return at(lo);
}
function vidSide(p, pk, opts, near) {
  const miss = [false, false];
  for (const a of [0, 1]) if (opts.hand[a]) {
    const force = opts.force[a] || pk.use === "force";
    const r = near ? vidForceHand(p, a, opts.hand[a], true) : force ? vidForceHand(p, a, opts.hand[a]) : facePalm(p, a, opts.hand[a]);
    if (r) p = r.pose.map((v) => Math.round(v * 10) / 10);
    if (!r || opts.hand[a] * r.upness <= 0.5) miss[a] = true;
  }
  return { pose: p, miss };
}
function vidReachSide(from, to, ms, pk, opts) {
  const forced = [0, 1].filter((a) => opts.hand[a] && (opts.force[a] || pk.use === "force"));
  const fits = (s) => minTime(from, s.pose) <= ms && forced.every((a) => !s.miss[a]);
  const plain = vidReachIn(from, to, ms), near = vidSide(plain, pk, opts, true);
  if (fits(near)) return near;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  const still = vidSide(from, pk, opts, true);
  let lo = 0, hi = 1, best = fits(still) ? still : null;
  for (let k = 0; k < 8; k++) {
    const m = (lo + hi) / 2, s = vidSide(at(m), pk, opts, true);
    if (fits(s)) {
      lo = m;
      best = s;
    } else hi = m;
  }
  return best || { pose: plain, miss: [0, 1].map((a) => !!opts.hand[a] && opts.hand[a] * palmUpnessOf(plain, a) <= 0.5) };
}
function vidBuild(fit, picks, opts) {
  const before = PACE_OVERRIDE;
  PACE_OVERRIDE = opts.music ? "music" : null;
  try {
    return vidBuildAtPace(fit, picks, opts);
  } finally {
    PACE_OVERRIDE = before;
  }
}
function vidBuildAtPace(fit, picks, opts) {
  const out = [], handMiss = [0, 0];
  let kept = 0, partial = 0, last = 0, start = 0;
  for (const pk of picks) {
    pk.missHand = [false, false];
    if (pk.use === "drop") continue;
    let s = vidSide(pk.use === "moment" ? vidPoseAt(fit, pk.at) : fit.poses[pk.i], pk, opts);
    kept++;
    const t = fit.times[pk.i];
    const prev = out[out.length - 1];
    const gap = t - last;
    last = t;
    if (!prev) {
      out.push({ pose: s.pose, t: 1e3, hold: 0, sourceMs: t, sourceHoldEnd: t });
      start = t;
    } else if (deltaDeg(prev.pose, s.pose) < 1) {
      prev.hold += gap;
      prev.sourceHoldEnd = t;
    } else {
      if (opts.music && minTime(prev.pose, s.pose) > gap) {
        s = vidReachSide(prev.pose, s.pose, gap, pk, opts);
        partial++;
      }
      if (deltaDeg(prev.pose, s.pose) < 1) {
        prev.hold += gap;
        prev.sourceHoldEnd = t;
      } else out.push({
        pose: s.pose,
        t: opts.music ? Math.round(gap) : Math.max(Math.round(gap), minTime(prev.pose, s.pose)),
        hold: 0,
        tset: true,
        sourceMs: t,
        sourceHoldEnd: t
      });
    }
    for (const a of [0, 1]) if (s.miss[a]) {
      handMiss[a]++;
      pk.missHand[a] = true;
    }
  }
  out.forEach((k) => {
    k.hold = Math.round(k.hold);
  });
  const safe = safeKeys(out, void 0, opts.music);
  if (opts.music) safe.keys.forEach((k, i) => {
    if (i) k.musicMs = k.t;
  });
  const settled = opts.music ? ServoFollow.settle(safe.keys) : 0;
  if (opts.music && safe.keys.length)
    safe.keys[0].cues = (safe.keys[0].cues || []).filter((c) => !/^pace:/i.test(c)).concat(musicPace.cue());
  const made = { keys: safe.keys, videoMs: fit.videoMs, handMiss, kept, partial, start, safe, settled, keepMusic: opts.music, quality: fit.quality || null };
  if (fit.targets) made.achieved = VideoRigFitter.assess(fit, made);
  if (made.achieved && made.quality) made.quality.worstBoneDegrees = made.achieved.worstBoneDegrees;
  return made;
}
function movesFromFrames(frames, opts) {
  const fit = vidFitFrames(frames, opts);
  if (!fit) return null;
  const o = { force: [false, false], music: false, ...opts };
  return vidBuild(fit, vidPicksFor(fit, o.tol), o);
}
function vidHandNote(made) {
  const opts = vidOpts();
  return [0, 1].filter((a) => opts.hand[a] && made.handMiss[a]).map((a) => " The " + HANDS[a].label.toLowerCase() + " could not show its " + (opts.hand[a] > 0 ? "palm" : "back") + " on top in " + made.handMiss[a] + " of " + made.kept + " moves" + (opts.force[a] ? ": the joints cannot turn it that far even with the hand moved." : ": the arm is almost straight there. Pick “always” for that hand, or “Keep, hand side forced” on those moves below, and the hand moves just enough to show it.")).join("");
}
function vidSelectFrames(routine) {
  if (vidRoutineRange && Number.isFinite(routine.sourceStart) && Number.isFinite(routine.sourceEnd)) {
    $("vidFrom").value = (vidRoutineRange.from + routine.sourceStart).toFixed(3);
    $("vidTo").value = Math.min(vidRoutineRange.to, vidRoutineRange.from + routine.sourceEnd).toFixed(3);
  }
  return routine.frames;
}
function vidEligibleRoutines() {
  return vidRoutines.filter((r) => (r.kind === "routine" || r.kind === "segment") && r.trustedCoverage >= VIDEO_FOLLOW.routines.minimumSaveCoverage);
}
function vidChooseRoutine() {
  if (vidBusy || !vidRoutines.length) return;
  const selected = vidRoutines.find((r) => String(r.id) === $("vidRoutine").value) || vidRoutines[0];
  vidFrames = vidSelectFrames(selected);
  vidRemake("fit");
  vidLastMs = -1;
  const video = $("vidPlayer");
  vidCheckedPlayback.reset(video);
  if (video == null ? void 0 : video.pause) video.pause();
  if ((video == null ? void 0 : video.src) && Number.isFinite(video.duration)) video.currentTime = +$("vidFrom").value || 0;
  vidSay(vidSummary(), false, vidSummaryTech());
}
async function vidSaveRoutines() {
  if (vidBusy) return;
  if (!vidRoutines.length && !await vidMake()) return;
  if (!vidRoutines.length) return vidMakeAndSave();
  const generation = vidGeneration, stamp = Date.now();
  const original = $("vidRoutine").value;
  if (!await askUnsaved("save the discovered dance routines as separate projects") || generation !== vidGeneration) return;
  vidBusy = true;
  vidStop = false;
  $("vidGo").textContent = "■ Stop";
  let saved = 0;
  try {
    for (const routine of vidEligibleRoutines()) {
      if (vidStop || generation !== vidGeneration) break;
      $("vidRoutine").value = String(routine.id);
      vidFrames = vidSelectFrames(routine);
      vidRemake("fit");
      if (!(vidMade == null ? void 0 : vidMade.keys.length)) continue;
      setWorkName("video_" + stamp + "_routine_" + routine.id);
      if (!await vidUse("replace", { skipUnsaved: true }) || generation !== vidGeneration || vidStop) break;
      if (!await saveAll()) break;
      saved++;
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  } finally {
    vidBusy = false;
    $("vidGo").textContent = "▶ Make moves";
    if (generation === vidGeneration) {
      $("vidRoutine").value = original;
      vidChooseRoutine();
      vidSay("Saved " + saved + " separate routine projects. Short or uncertain fragments remain available for review.");
    }
  }
}
function vidSummary() {
  const m = vidMade, opts = vidOpts();
  return m.keys.length + " moves from " + (m.videoMs / 1e3).toFixed(1) + " s of video." + (m.safe && safeSay(m.safe) ? " " + safeSay(m.safe) : "") + (opts.music && m.partial ? " To stay with the music, " + m.partial + " of them go only part of the way: the person moved faster than the robot can." : "") + vidHandNote(m) + " Choose what to keep below, then put them on the time bar:";
}
function vidSummaryTech() {
  var _a, _b;
  const m = vidMade;
  return [
    vidRoutines.length ? vidRoutines.length + " routine groups / scene sections found automatically. Uncertain camera links are split rather than stitched into another dance." : "",
    ((_a = m.quality) == null ? void 0 : _a.smoothing) ? "Short reversals: " + m.quality.smoothing.before.reversals + " → " + m.quality.smoothing.afterRepair.reversals + "." : "",
    ((_b = m.quality) == null ? void 0 : _b.uncertain) ? m.quality.uncertain + " uncertain observations hold the last trustworthy pose." : ""
  ].filter(Boolean).join(" ");
}
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
    see.textContent = n + 1 + " · " + (vidFit.times[pk.i] / 1e3).toFixed(1) + " s";
    see.title = "see this moment of the video and the robot's pose for it";
    see.onclick = () => vidSee(pk);
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "move " + (n + 1));
    VID_USE.filter((u) => u.id !== "force" || anyHand).forEach((u) => sel.add(new Option(u.label, u.id, false, u.id === pk.use)));
    const at = document.createElement("input");
    at.type = "number";
    at.step = "0.1";
    at.min = "0";
    at.value = (pk.at / 1e3).toFixed(1);
    at.hidden = pk.use !== "moment";
    at.title = "the moment of the video (s) whose pose fills this move; it keeps its own place in time";
    at.setAttribute("aria-label", "moment for move " + (n + 1));
    sel.onchange = () => {
      pk.use = sel.value;
      at.hidden = pk.use !== "moment";
      vidRebuild();
    };
    at.onchange = () => {
      pk.at = Math.max(0, +at.value || 0) * 1e3;
      vidRebuild();
      vidSee(pk);
    };
    row.append(see, sel, at);
    const miss = HANDS.filter((h, a) => pk.missHand && pk.missHand[a]).map((h) => h.side);
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
    v.currentTime = Math.min(v.duration, (+$("vidFrom").value || 0) + ms / 1e3);
  }
  pose = (vidMade == null ? void 0 : vidMade.keys.length) ? easeKeys(vidMade.keys, VideoRigFitter.clockForSource(vidMade.keys, ms).ms, "video").pose : vidPoseAt(vidFit, ms).slice();
  poseChanged(false);
}
async function vidMakeAndSave() {
  if (vidBusy) return;
  const generation = vidGeneration;
  if (!await vidMake() || generation !== vidGeneration) return;
  if (!vidMade || vidMade.keys.length < 2) return;
  if (vidEligibleRoutines().length > 1) {
    await vidSaveRoutines();
    return;
  }
  const base = (vidSrc && (vidSrc.name || vidSrc.url) || "video").split(/[\\/?#]/).filter(Boolean).pop();
  setWorkName("video_" + base.replace(/\.[^.]*$/, ""));
  if (!await vidUse("replace")) return;
  if (generation !== vidGeneration) return;
  if (await saveAll()) vidSay($("tlStat").textContent);
}
async function vidMake() {
  if (vidBusy) {
    vidStop = true;
    if (vidSeekCancel) vidSeekCancel();
    return false;
  }
  vidBusy = true;
  vidStop = false;
  const generation = vidGeneration;
  $("vidGo").textContent = "■ Stop";
  $("vidUseBox").hidden = true;
  try {
    const frames = await vidRead();
    if (!frames || vidStop || generation !== vidGeneration) return false;
    if (!frames.some((f) => f.w)) {
      vidSay("No person was found in the video. Use a video where one person's upper body and arms are in the picture.", true);
      return;
    }
    vidFrames = frames;
    vidSay("Fitting the robot's arms…");
    await new Promise((r) => setTimeout(r, 30));
    vidRemake("fit");
    if (!vidMade || vidMade.keys.length < 2) {
      vidSay("The arms were not seen clearly enough to make moves. Try a video where the arms are in the picture and not hidden.", true);
      vidMade = null;
      return;
    }
    const seen = frames.filter((f) => f.w).length;
    const pct = Math.round(100 * seen / frames.length);
    if (pct < 25) vidSay("I could hardly see a person in this video (only " + pct + "% of it), so these moves are probably not useful. Try a video where the whole person, arms included, is in the picture. " + vidSummary(), true, vidSummaryTech());
    else vidSay("The person was found in " + pct + "% of the video. " + vidSummary(), false, vidSummaryTech());
    return true;
  } finally {
    vidBusy = false;
    $("vidGo").textContent = "▶ Make moves";
  }
}
function vidRemake(step) {
  if (!vidFrames || vidBusy && step !== "fit") return;
  const opts = vidOpts();
  if (step === "fit" || !vidFit) vidFit = vidFitFrames(vidFrames, opts);
  if (!vidFit) {
    vidMade = null;
    vidPicks = null;
    vidList();
    return;
  }
  if (step === "fit" || step === "pick" || !vidPicks) vidPicks = vidPicksFor(vidFit, opts.tol);
  vidRebuild();
}
function vidRebuild() {
  vidMade = vidBuild(vidFit, vidPicks, vidOpts());
  vidList();
  $("vidUseBox").hidden = !(vidMade && vidMade.keys.length >= 2);
  vidSay(vidSummary(), false, vidSummaryTech());
}
async function vidUse(how, options = {}) {
  const generation = vidGeneration;
  if (!vidMade) return false;
  const add = JSON.parse(JSON.stringify(vidMade.keys));
  if (how === "replace") {
    if (!options.skipUnsaved && !await askUnsaved("replace the time bar with the moves from the video")) return false;
    if (generation !== vidGeneration || vidStop) return false;
    keys = add;
  } else {
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
  $("tlStat").textContent = add.length + " moves from the video are on the time bar. " + (robotMs > vidMade.videoMs * 1.15 ? "The robot needs " + (robotMs / 1e3).toFixed(1) + " s for " + (vidMade.videoMs / 1e3).toFixed(1) + " s of video: the person moved faster than its servos and speed limit allow. Tick “Stay with the music” to keep the video's timing instead. " : "") + "Press Play to watch, edit any move, then Save or Save to robot.";
  vidSay($("tlStat").textContent);
  return true;
}
vidFill();
videoFollowReady().then(() => {
  vidFill();
  if (typeof vidSaved !== "undefined" && vidSaved) vidApplySettings(vidSaved);
}).catch(() => {
});
let vidSrc = null;
let vidFetchId = null, vidLinkBusy = false;
let vidHeld = null;
let vidView = "iso";
let vidLastMs = -1, vidOn = false, vidFirstKey = -1;
let vidSaved = null;
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
    const cur = document.querySelector("#viewCube [data-view].on");
    vidView = cur ? cur.dataset.view : "iso";
    setView("front");
    requestAnimationFrame(vidTick);
    return;
  }
  vidGeneration++;
  if (vidBusy) vidStop = true;
  if (vidSeekCancel) vidSeekCancel();
  vidCheckedPlayback.reset(v);
  if (v && !v.paused) v.pause();
  if (vidHeld) {
    pose = vidHeld;
    applyPose();
    renderSliders();
  }
  vidHeld = null;
  setView(vidView);
}
function vidSetSrc(url, src) {
  var _a;
  vidGeneration++;
  if (vidSeekCancel) vidSeekCancel();
  if (vidBusy) vidStop = true;
  const v = $("vidPlayer");
  vidCheckedPlayback.reset(v);
  const keepSaved = !!(((_a = vidSaved == null ? void 0 : vidSaved.src) == null ? void 0 : _a.url) && src.url && vidSaved.src.url === src.url);
  if (!keepSaved) {
    vidSaved = null;
    $("vidRoutine").innerHTML = '<option value="auto">Find routines automatically</option>';
    $("vidRoutine").value = "auto";
    $("vidDancer").innerHTML = '<option value="auto">Automatic — discover dance groups</option>';
    $("vidDancer").value = "auto";
  }
  if (v.src && v.src.startsWith("blob:")) URL.revokeObjectURL(v.src);
  vidSrc = src;
  v.src = url;
  v.hidden = false;
  $("vidEmpty").hidden = true;
  vidFrames = null;
  vidMade = null;
  vidFit = null;
  vidPicks = null;
  vidRoutines = [];
  vidRoutineRange = null;
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
    const keep = keepSaved && vidSaved;
    $("vidFrom").value = keep ? String(vidSaved.from || 0) : "0";
    $("vidTo").value = keep && vidSaved.to ? String(vidSaved.to) : v.duration.toFixed(1);
    vidSay("Ready: " + v.duration.toFixed(1) + " s of video. Press Make moves.");
  };
  v.onerror = () => vidSay("This browser cannot play that video. Try an MP4 or WEBM file.", true);
  v.onended = v.onpause = () => {
    $("vidPlayBtn").textContent = "▶ Play person and robot";
  };
  v.onplay = () => {
    $("vidPlayBtn").textContent = "❚❚ Pause";
  };
}
async function vidFetch() {
  if (vidLinkBusy) {
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
      vidSay("Fetching the video onto this PC" + (st.how ? " (" + st.how + ")" : "") + ": " + (st.pct || 0) + "%" + (st.title ? " · " + st.title : ""));
      await new Promise((r) => setTimeout(r, 700));
      a = await Mice.Api.get("/api/video/fetch?id=" + encodeURIComponent(vidFetchId));
      if (!a.ok) {
        vidSay(a.says, true);
        return;
      }
      st = a.data;
    }
    if (st.state !== "done") {
      vidSay(st.error || "The link could not be fetched.", st.error !== "Stopped.");
      $("vidTech").textContent = st.tech || "";
      return;
    }
    vidSetSrc(
      "/api/video/file?id=" + encodeURIComponent(vidFetchId),
      { kind: "link", url, id: vidFetchId, name: st.title || "video" }
    );
  } finally {
    vidLinkBusy = false;
    $("vidFetchBtn").textContent = "Fetch";
  }
}
function vidPlayBoth() {
  const v = $("vidPlayer");
  if (!v.src) return;
  if (vidCheckedPlayback.manual) {
    vidCheckedPlayback.pause(v);
    return;
  }
  if (!v.paused) {
    v.pause();
    return;
  }
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (v.currentTime < from || v.currentTime >= to - 0.05) v.currentTime = from;
  v.muted = false;
  if ((vidMade == null ? void 0 : vidMade.keepMusic) === false && vidMade.keys.length) {
    const mapped = VideoRigFitter.clockForSource(vidMade.keys, (v.currentTime - from) * 1e3);
    if (mapped.rate < 0.0625) {
      vidCheckedPlayback.start(v, mapped.ms);
      return;
    }
    v.playbackRate = Math.min(4, mapped.rate);
  }
  v.play().catch((e) => vidSay("The video would not play: " + Mice.Words.plain(e).says, true));
}
function vidTick() {
  if (!vidOn) return;
  requestAnimationFrame(vidTick);
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration) || vidBusy || playing) return;
  const from = +$("vidFrom").value || 0, to = +$("vidTo").value || v.duration;
  if (!v.paused && v.currentTime >= to) v.pause();
  let ms = Math.round((v.currentTime - from) * 1e3);
  ms = vidCheckedPlayback.update(v, vidMade, ms, from, (to - from) * 1e3);
  if (ms === vidLastMs && !vidCheckedPlayback.manual) return;
  vidLastMs = ms;
  vidShowAt(ms, vidCheckedPlayback.robotMs);
}
function vidShowAt(ms, checkedMs = null) {
  if (vidFrames && vidFrames.length) {
    const f = vidFrames[Math.max(0, Math.min(vidFrames.length - 1, Math.round(ms * VID_FPS / 1e3)))];
    vidDraw($("vidSkel").checked && ms >= 0 ? f.p : null);
  }
  if (vidMade && vidMade.keys.length && ms >= 0) {
    pose = easeKeys(vidMade.keys, checkedMs != null ? checkedMs : VideoRigFitter.clockForSource(vidMade.keys, ms).ms, "video").pose;
    applyPose();
  }
  $("vidClock").textContent = ms >= 0 ? (ms / 1e3).toFixed(1) + " s" : "";
}
function vidOnBar(first) {
  vidFirstKey = first;
  vidHeld = null;
  $("vidSoundBox").hidden = !vidSrc;
}
async function vidSound() {
  var _a;
  if ((vidMade == null ? void 0 : vidMade.keepMusic) === false && vidMade.keys.length) {
    const last = vidMade.keys.at(-1), end = (_a = last.sourceHoldEnd) != null ? _a : last.sourceMs;
    const timed = VideoRigFitter.clockForSource(vidMade.keys, end).ms;
    if (Number.isFinite(end) && timed > end - (vidMade.keys[0].sourceMs || 0) + 2) {
      vidSay("These moves use a slower clock. The original sound would be out of step; use a retimed music file for this show.", true);
      return;
    }
  }
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
      const r2 = await fetch(
        "/api/video/put?name=" + encodeURIComponent(vidSrc.name),
        { method: "POST", body: vidSrc.file }
      ).catch(() => null);
      const j = r2 ? await r2.json().catch(() => ({})) : {};
      if (!r2 || !j.ok) {
        vidSay(j.need_login ? VID_LOGIN : "The video could not be copied: " + (j.error || "the hub is not answering"), true);
        return;
      }
      vidSrc.id = j.id;
    }
    vidSay("Taking the sound out of the video…");
    const from = (+$("vidFrom").value || 0) + (vidMade ? vidMade.start / 1e3 : 0);
    const a = await Mice.Api.post(
      "/api/video/sound",
      { id: vidSrc.id, from, to: +$("vidTo").value || 0 }
    );
    if (!a.ok) {
      vidSay(a.needLogin ? VID_LOGIN : a.says, true);
      return;
    }
    const r = await fetch("/api/video/file?kind=sound&id=" + encodeURIComponent(vidSrc.id));
    if (!r.ok) {
      vidSay("The sound was made but could not be read back.", true);
      return;
    }
    const name = robotTrackName((vidSrc.name || "video").replace(/\.[^.]*$/, "").slice(0, 40) + ".mp3");
    await uploadMusicFile(k, new File([await r.blob()], name, { type: "audio/mpeg" }), Object.assign(
      (track, why, renamed) => {
        if (!track) {
          vidSay("The sound did not reach the robot: " + why, true);
          return;
        }
        setCueTrack(k, track, false);
        renderTimeline();
        vidSay("♪ " + track + " is on the robot's card and plays with the first video move" + (renamed || "") + ". Save to keep it.");
      },
      { busy: (t) => vidSay(t) }
    ));
  } finally {
    btn.disabled = false;
  }
}
function vidSettings() {
  var _a, _b, _c, _d, _e, _f, _g;
  if (!vidSrc) return vidSaved;
  return {
    src: { kind: vidSrc.kind, name: vidSrc.name, url: vidSrc.url || "" },
    subjectMode: ((_a = $("vidSubject")) == null ? void 0 : _a.value) || "auto",
    cameraMode: ((_b = $("vidCamera")) == null ? void 0 : _b.value) || "auto",
    routine: ((_c = $("vidRoutine")) == null ? void 0 : _c.value) || "auto",
    routineSummary: typeof vidRoutines !== "undefined" ? vidRoutines.map((r) => ({ id: r.id, kind: r.kind, sourceStart: r.sourceStart, sourceEnd: r.sourceEnd, coverage: r.coverage, trustedCoverage: r.trustedCoverage, ambiguous: r.ambiguous })) : [],
    dancer: ((_d = $("vidDancer")) == null ? void 0 : _d.value) || "auto",
    shrug: !!((_e = $("vidShrug")) == null ? void 0 : _e.checked),
    anchorX: Number.isFinite(vidSaved == null ? void 0 : vidSaved.anchorX) ? vidSaved.anchorX : 0.5,
    analysis: (vidMade == null ? void 0 : vidMade.achieved) ? {
      meanBoneDegrees: vidMade.achieved.meanBoneDegrees,
      worstBoneDegrees: vidMade.achieved.worstBoneDegrees,
      corrected: vidMade.safe.around,
      uncertain: ((_f = vidMade.quality) == null ? void 0 : _f.uncertain) || 0,
      limited: vidMade.partial
    } : null,
    learned: ((_g = $("vidLearned")) == null ? void 0 : _g.checked) !== false,
    detail: $("vidDetail").value,
    mirror: $("vidMirror").checked,
    music: $("vidMusic").checked,
    waist: $("vidWaist").checked,
    hand: [$("vidHand0").value, $("vidHand1").value],
    from: +$("vidFrom").value || 0,
    to: +$("vidTo").value || 0
  };
}
function vidApplySettings(s) {
  vidSaved = s && typeof s === "object" ? s : null;
  if (!vidSaved) return;
  vidFill();
  const pick = (sel, id) => {
    if (sel && [...sel.options].some((o) => o.value === id)) sel.value = id;
  };
  pick($("vidDetail"), s.detail);
  pick($("vidSubject"), s.subjectMode || "auto");
  pick($("vidCamera"), s.cameraMode || "auto");
  if ($("vidShrug")) $("vidShrug").checked = !!s.shrug;
  if ($("vidLearned")) $("vidLearned").checked = s.learned !== false;
  if ($("vidDancer")) {
    if (s.dancer && ![...$("vidDancer").options].some((o) => o.value === s.dancer))
      $("vidDancer").add(new Option("Performer " + s.dancer, s.dancer));
    $("vidDancer").value = s.dancer || "auto";
    if ($("vidDancer").options[0]) $("vidDancer").options[0].text = Number.isFinite(s.anchorX) && s.anchorX !== 0.5 ? "Saved reference" : "Main performer";
  }
  if ($("vidRoutine")) {
    if (s.routine && ![...$("vidRoutine").options].some((o) => o.value === s.routine)) $("vidRoutine").add(new Option("Saved routine " + s.routine, s.routine));
    $("vidRoutine").value = s.routine || "auto";
  }
  (s.hand || []).forEach((h, a) => pick($("vidHand" + a), h));
  $("vidMirror").checked = !!s.mirror;
  $("vidMusic").checked = s.music === true;
  $("vidWaist").checked = !!s.waist;
  $("vidFrom").value = String(s.from || 0);
  if (s.to) $("vidTo").value = String(s.to);
  if (s.src && s.src.url) $("vidLink").value = s.src.url;
  if (s.src) vidSay("These moves were made from " + (s.src.url ? "a link: press Fetch to see it again." : "the file " + s.src.name + ": pick it again to see it."));
}
let dummySim = null;
let dummyFollowOn = false;
let dummyLast = null;
let dummySafePose = null;
let dummyRobotFollowing = false;
let dummyHeld = "";
let dummyRec = null;
function dummySource() {
  return $("dummySrc").value;
}
function dummyBus() {
  const v = $("dummyBus").value.trim();
  return v ? parseInt(v, 10) : 0;
}
function dummySrcChanged(boot) {
  const s = dummySource();
  $("dummyPort").style.display = s === "usb" ? "" : "none";
  $("dummyRescan").style.display = s === "usb" ? "" : "none";
  $("dummyBusWrap").style.display = s === "usb" ? "" : "none";
  $("dummyIpWrap").style.display = s === "wifi" ? "" : "none";
  $("dummySimBox").style.display = s === "sim" ? "" : "none";
  if (s === "usb" && !boot && !$("dummyPort").dataset.loaded) dummyLoadPorts();
  if (s === "sim") dummyBuildSim();
}
async function dummyLoadPorts() {
  const sel = $("dummyPort");
  try {
    const r = await fetch("/api/ports").then((r2) => r2.json());
    const ps = (r.ports || []).filter((p) => !p.bt);
    sel.innerHTML = "<option value=''>pick the USB port…</option>";
    ps.forEach((p) => {
      const o = document.createElement("option");
      o.value = p.port;
      o.textContent = p.port + (p.who ? " — " + p.who : p.desc ? " — " + p.desc : "");
      sel.appendChild(o);
    });
    const robotPort = $("usbPort") ? $("usbPort").value : "";
    if (robotPort && ps.some((p) => p.port === robotPort)) sel.value = robotPort;
    else if (ps.length === 1) sel.value = ps[0].port;
    sel.dataset.loaded = "1";
  } catch (e) {
    sel.innerHTML = "<option value=''>the port list needs the hub</option>";
  }
}
async function dummyCmd(c) {
  const s = dummySource();
  if (s === "sim") {
    if (c.toUpperCase() !== "POSE?") return "OK";
    return dummySim.map((v) => v === null ? "-" : fmtA(v)).join(" ");
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
    try {
      msg = JSON.parse(t).error || t;
    } catch (e) {
    }
    throw new Error(msg);
  }
  return t;
}
function parseDummyPose(text) {
  const tok = String(text || "").trim().split(/\s+/);
  if (tok.length < ARMJ || tok.some((t) => t !== "-" && !isFinite(parseFloat(t))))
    throw new Error("the dummy did not answer with a pose (" + String(text).slice(0, 40) + ")");
  return Array.from({ length: NJ }, (_, i) => tok[i] === void 0 || tok[i] === "-" ? null : parseFloat(tok[i]));
}
async function dummyRead() {
  const vals = parseDummyPose(await dummyCmd("POSE?"));
  dummyLast = vals;
  return vals;
}
function dummyApply(vals) {
  pose = pose.map((cur, i) => vals[i] === null ? cur : clampJ(i, vals[i]));
  applyPose();
  renderSliders();
}
async function dummyConnect() {
  try {
    const v = await dummyRead();
    const n = v.filter((x) => x !== null).length;
    $("dummyStat").textContent = "dummy answers ✓ — " + n + " of " + NJ + " joints have a pot";
  } catch (e) {
    Mice.fail($("dummyStat"), "no answer from the dummy", e);
    notice($("dummyStat").textContent);
  }
}
function dummyFollowChanged() {
  const mode = $("dummyFollow").value;
  if (dummyRobotFollowing && mode !== "robot") cancelSafeMotion("dummy follow stopped");
  dummyRobotFollowing = mode === "robot";
  if (mode === "robot") dummySafePose = null;
  if (mode !== "off") {
    if (mode === "robot" && !(haveUsb() || haveWifi())) {
      $("dummyStat").textContent = "connect the robot first (Robot link above), then pick this again";
      notice($("dummyStat").textContent);
      $("dummyFollow").value = "studio";
    }
    if ($("monChk").checked) {
      $("monChk").checked = false;
      monitorChanged();
    }
    if (playing) togglePlay();
    if (!dummyFollowOn) {
      dummyFollowOn = true;
      dummyFollowTick();
    }
  } else {
    dummyFollowOn = false;
    dummySafePose = null;
    dummyHeld = "";
  }
}
function dummySafeSend() {
  const want = pose.slice();
  const plan = planSafe(dummySafePose || want, want, SAFE.liveBudgetMs);
  if (plan.fail) {
    dummyHeld = "robot holds its last safe pose: " + plan.fail;
    return false;
  }
  dummyHeld = "";
  sendPoseLive();
  dummySafePose = want;
  return true;
}
function dummyRecToggle() {
  if (!dummyRec) {
    if ($("dummyFollow").value === "off") {
      $("dummyFollow").value = "studio";
      dummyFollowChanged();
    }
    dummyRec = [{ pose: pose.slice(), ms: performance.now() }];
    $("dummyRecBtn").textContent = "■ Stop and save";
    $("dummyStat").textContent = "recording the dummy: move it, then press Stop and save";
    return;
  }
  const rec = dummyRec;
  dummyRec = null;
  $("dummyRecBtn").textContent = "● Record the dummy";
  return dummyRecSave(rec);
}
async function dummyRecSave(rec) {
  const K = [];
  for (const r of rec) {
    const prev = K[K.length - 1];
    if (!prev) {
      K.push({ pose: r.pose, t: 1e3, hold: 0, ms: r.ms });
      continue;
    }
    if (deltaDeg(prev.pose, r.pose) < 2) continue;
    K.push({ pose: r.pose, t: Math.max(MIN_MOVE_MS, Math.round(r.ms - prev.ms)), hold: 0, tset: true, ms: r.ms });
  }
  if (K.length < 2) {
    $("dummyStat").textContent = "nothing to keep: the dummy did not move";
    return false;
  }
  const safe = safeKeys(K.map(({ ms, ...k }) => k));
  if (safe.keys.length < 2) {
    $("dummyStat").textContent = "nothing to keep: every pose would make the robot hit itself";
    return false;
  }
  if (!await askUnsaved("replace the time bar with the recording")) return false;
  keys = safe.keys;
  bumpKeys();
  clearBadMarks();
  clampKeyTimes();
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  setWorkName("dummy_" + (/* @__PURE__ */ new Date()).toISOString().slice(0, 16).replace(/[-:T]/g, ""));
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
    const moved = mode === "robot" && !dummySafePose || !prev || v.some((x, i) => x === null !== (prev[i] === null) || x !== null && Math.abs(x - prev[i]) >= 0.2);
    if (moved && dummyFollowOn && mode === $("dummyFollow").value) {
      dummyApply(v);
      if (dummyRec) dummyRec.push({ pose: pose.slice(), ms: performance.now() });
      if (mode === "robot") dummySafeSend();
    }
    $("dummyStat").textContent = mode === "robot" && dummyHeld ? dummyHeld : (mode === "robot" ? "robot + Studio follow" : "Studio follows") + " the dummy" + (dummyRec ? " (recording)" : "");
  } catch (e) {
    $("dummyStat").textContent = "dummy: no answer (" + Mice.Words.plain(e).says + ") — still trying";
  }
  if (dummyFollowOn) setTimeout(dummyFollowTick, 80);
}
async function dummyToNewKey() {
  try {
    dummyApply(await dummyRead());
    addKey();
    $("dummyStat").textContent = "dummy pose saved as move " + selKey;
  } catch (e) {
    Mice.fail($("dummyStat"), "", e);
  }
}
async function dummyToSelectedKey() {
  if (!keys[selKey]) {
    $("dummyStat").textContent = "select a move in the timeline first";
    return;
  }
  try {
    dummyApply(await dummyRead());
    updateKey();
    $("dummyStat").textContent = "move " + selKey + " now holds the dummy pose";
  } catch (e) {
    Mice.fail($("dummyStat"), "", e);
  }
}
function robotToSelectedKey() {
  const k = keys[selKey];
  if (!k) {
    $("dummyStat").textContent = "select a move in the timeline first";
    return;
  }
  if (!(haveUsb() || haveWifi())) {
    $("dummyStat").textContent = "connect the robot first (Robot link above)";
    return;
  }
  if ($("dummyFollow").value !== "off") {
    $("dummyFollow").value = "off";
    dummyFollowChanged();
  }
  const from = pose.slice();
  const tgt = k.pose.map((v, i) => clampJ(i, v));
  const ms = Math.max(keyTravelMs(selKey), autoTime(from, tgt, keyDps(selKey)), MIN_MOVE_MS);
  selectKey(selKey);
  if (!$("liveChk").checked) robotCmd("POSE " + tgt.map(fmtA).join(" ") + " T " + Math.round(ms));
  $("dummyStat").textContent = "robot moving to move " + selKey;
}
function dummyBuildSim() {
  const box = $("dummySimRows");
  if (!dummySim) dummySim = pose.slice();
  if (box.dataset.built) return;
  box.dataset.built = "1";
  for (let i = 0; i < NJ; i++) {
    const r = document.createElement("div");
    r.className = "row";
    const l = document.createElement("span");
    l.className = "lbl";
    l.textContent = JOINT_LABELS[i];
    const s = document.createElement("input");
    s.type = "range";
    s.min = 0;
    s.max = 180;
    s.step = 0.5;
    s.value = dummySim[i];
    s.style.flex = "1";
    s.id = "dsim" + i;
    const v = document.createElement("span");
    v.className = "mini";
    v.style.minWidth = "40px";
    v.textContent = fmtA(dummySim[i]) + "°";
    s.oninput = () => {
      dummySim[i] = parseFloat(s.value);
      v.textContent = fmtA(dummySim[i]) + "°";
    };
    r.append(l, s, v);
    box.appendChild(r);
  }
}
window.addEventListener("DOMContentLoaded", function() {
  if (!document.getElementById("dummySrc")) return;
  dummySrcChanged(true);
  $("dummyPort").addEventListener("focus", () => {
    if (!$("dummyPort").dataset.loaded) dummyLoadPorts();
  });
});
const FREEZE_MS = 1500;
const _fw = { last: 0, hiddenSince: 0, sentAt: -1e9, calls: [], longs: [] };
(function() {
  const realFetch = window.fetch.bind(window);
  window.fetch = function(url, opts) {
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
    new PerformanceObserver((l) => l.getEntries().forEach((e) => {
      _fw.longs.push({ ms: Math.round(e.duration), at: Math.round(e.startTime) });
      if (_fw.longs.length > 20) _fw.longs.shift();
    })).observe({ entryTypes: ["longtask"] });
  } catch (e) {
  }
  document.addEventListener("visibilitychange", () => {
    _fw.hiddenSince = document.hidden ? performance.now() : 0;
    _fw.last = 0;
  });
})();
function freezeCheck(now) {
  const gap = _fw.last ? now - _fw.last : 0;
  _fw.last = now;
  if (gap < FREEZE_MS || document.hidden || now - _fw.sentAt < 3e4) return;
  _fw.sentAt = now;
  const gi = renderer && renderer.info || {};
  const state = {
    gapMs: Math.round(gap),
    playing: typeof playing !== "undefined" && playing,
    live: !!($("liveChk") && $("liveChk").checked),
    monitor: !!($("monChk") && $("monChk").checked),
    auto: haveAuto(),
    usb: haveUsb(),
    wifi: haveWifi(),
    keys: keys.length,
    gpu: {
      geometries: gi.memory && gi.memory.geometries,
      textures: gi.memory && gi.memory.textures,
      programs: gi.programs && gi.programs.length
    },
    heapMB: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null,
    longTasks: _fw.longs.filter((x) => x.at > now - gap - 2e3),
    slowCalls: _fw.calls.filter((c) => c.ms > 300 || c.at > now - gap - 2e3).slice(-15)
  };
  fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: "STUDIO FREEZE " + JSON.stringify(state),
      page: "studio",
      time: (/* @__PURE__ */ new Date()).toISOString(),
      attachDiag: false
    })
  }).catch(() => {
  });
}
let distPairs = null;
let distOn = false;
let distHeld = false;
let distLines = [];
const distLayer = document.createElement("div");
distLayer.id = "distLayer";
distLayer.hidden = true;
viewport.appendChild(distLayer);
const DIST_POINTS = {
  shoulder: (side) => shrugAnchors[side],
  elbow: (side) => elbowBalls[side === "L" ? 0 : 1],
  // arm 0 is the robot's left (+X)
  hand: (side) => wristBalls[side === "L" ? 0 : 1]
};
function distPoint(name) {
  const m = /^([LR])_([a-z]+)$/.exec(name || "");
  const pick = m && Object.prototype.hasOwnProperty.call(DIST_POINTS, m[2]) ? DIST_POINTS[m[2]] : null;
  const obj = pick ? pick(m[1]) : null;
  return obj ? obj.getWorldPosition(new THREE.Vector3()) : null;
}
async function distLoad() {
  if (distPairs) return;
  try {
    const j = await fetch("distances.json").then((r) => r.json());
    distPairs = (j.pairs || []).filter((p) => p && p.from && p.to);
  } catch (e) {
    distPairs = [];
    distLayer.dataset.note = "the list of distances (distances.json) could not be read";
  }
}
function distShown() {
  return distOn || distHeld;
}
function distSet(on) {
  distOn = on;
  const b = $("distBtn");
  if (b) {
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", on ? "true" : "false");
  }
  distLoad().then(distDraw);
}
function distClear() {
  distLines.forEach((l) => {
    scene.remove(l);
    l.geometry.dispose();
    l.material.dispose();
  });
  distLines = [];
  distLayer.textContent = "";
}
function distDraw() {
  if (!distShown() || !distPairs) {
    if (distLines.length || !distLayer.hidden) {
      distClear();
      distLayer.hidden = true;
    }
    return;
  }
  distClear();
  distLayer.hidden = false;
  scene.updateMatrixWorld();
  const cam = activeCam(), rect = renderer.domElement.getBoundingClientRect();
  const color = getComputedStyle(document.documentElement).getPropertyValue("--acc").trim() || "#4ea1ff";
  let drawn = 0;
  distPairs.forEach((p) => {
    const a = distPoint(p.from), b = distPoint(p.to);
    if (!a || !b) return;
    const g = new THREE.BufferGeometry().setFromPoints([a, b]);
    const line = new THREE.Line(g, new THREE.LineDashedMaterial(
      { color: new THREE.Color(color), dashSize: 8, gapSize: 6, depthTest: false }
    ));
    line.computeLineDistances();
    line.renderOrder = 30;
    scene.add(line);
    distLines.push(line);
    const mid = a.clone().add(b).multiplyScalar(0.5).project(cam);
    if (mid.z > 1) return;
    const tag = document.createElement("span");
    tag.className = "distTag";
    tag.textContent = Math.round(a.distanceTo(b)) + " mm";
    tag.title = p.label || p.from + " to " + p.to;
    tag.style.left = (mid.x + 1) / 2 * rect.width + "px";
    tag.style.top = (1 - mid.y) / 2 * rect.height + "px";
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
  if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
  if (!distHeld) {
    distHeld = true;
    distLoad().then(distDraw);
  }
});
window.addEventListener("keyup", (e) => {
  if (e.key === "d" || e.key === "D") distHeld = false;
});
window.addEventListener("blur", () => {
  distHeld = false;
});
let TALK = { lib: null, fit: null, busy: false, hub: false };
const TALK_IDLE_MS = 2e4;
let talkIdleAt = performance.now();
["pointerdown", "keydown", "wheel"].forEach((e) => window.addEventListener(e, () => {
  talkIdleAt = performance.now();
}, true));
function talkSay(s) {
  if ($("talkStat")) $("talkStat").textContent = s;
}
function talkRigSnap() {
  const r = JSON.parse(JSON.stringify(RIG));
  return {
    dims: r.dims,
    zero: r.zero,
    axis: r.axis,
    invert: r.invert,
    offset: r.offset,
    tilt: r.tilt,
    min: r.min,
    max: r.max,
    home: r.home,
    palmTurn: r.palmTurn
  };
}
async function talkLoad() {
  try {
    const j = await fetch("/api/gestures").then((r) => r.json());
    if (!j.ok) throw new Error(j.error || "no answer");
    if (TALK.character !== j.character) TALK.events = null;
    TALK.character = j.character || "";
    TALK.revision = j.gestureRevision || "";
    TALK.readOnly = !!j.readOnly;
    TALK.lib = j.lib;
    TALK.fit = j.fit || {};
    TALK.hub = true;
  } catch (e) {
    TALK.hub = false;
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
  return Object.keys(L.gestures || {}).some((id) => JSON.stringify(defs[id] || null) !== JSON.stringify(L.gestures[id].keys || null)) || Object.keys(defs).some((id) => !(L.gestures || {})[id]);
}
function talkKeyPose(k, from, restArm, mirror) {
  const p = from.slice();
  const sideOf = (a) => a === 0 ? 1 : -1;
  const tgt = [mirror ? k.R : k.L, mirror ? k.L : k.R];
  const palm = [mirror ? k.palmR : k.palmL, mirror ? k.palmL : k.palmR];
  if (k.pose) return k.pose.map((v, j) => clampJ(j, v));
  p[8] = clampJ(8, RIG.home[8] + (mirror ? -1 : 1) * (k.waist || 0));
  p[9] = clampJ(9, RIG.home[9] + (k.shrug || 0));
  for (const a of [0, 1]) {
    const idx = a === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    if (!tgt[a]) {
      idx.forEach((j) => {
        p[j] = restArm[j];
      });
      continue;
    }
    pose = p.slice();
    applyPose();
    robot.updateMatrixWorld(true);
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
    idx.forEach((j) => {
      p[j] = clampJ(j, q[j]);
    });
  }
  return p;
}
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
  const inner = safeKeys(raw);
  if (inner.failed || inner.dropped) return { bad: "a move inside it has no safe way" };
  const leg = (a, b) => {
    const r = planSafe(a, b);
    return r.fail ? null : r.path.slice(1, -1).map((q) => ({ pose: q, t: 300, via: true }));
  };
  const ins = leg(restPose, inner.keys[0].pose), outs = leg(inner.keys[inner.keys.length - 1].pose, restPose);
  if (!ins || !outs) return { bad: "no safe way from the resting hands" };
  return { keys: inner.keys.map((k) => ({ pose: k.pose, t: k.t, hold: k.hold || 0, via: !!k.via })), in: ins, out: outs };
}
async function talkFit() {
  if (TALK.busy || !TALK.lib || !robot) return false;
  TALK.busy = true;
  const saved = pose.slice();
  const L = TALK.lib, fit = {
    rig: { min: RIG.min.slice(), max: RIG.max.slice(), home: RIG.home.slice() },
    rigFull: talkRigSnap(),
    restDef: (L.rest || {}).keys || [],
    defs: {},
    gestures: {},
    bad: {},
    direct: [],
    at: (/* @__PURE__ */ new Date()).toISOString()
  };
  try {
    talkSay("Fitting the gestures to this robot…");
    const home = RIG.home.map((v, j) => clampJ(j, v));
    const restDef = (L.rest || {}).keys || [];
    const restKeys = [];
    let from = home;
    for (const k of restDef) {
      const p = talkKeyPose(k, from, home, false);
      restKeys.push({ pose: p, t: k.t || 600, hold: k.hold || 0 });
      from = p;
    }
    if (!restKeys.length || poseHit(restKeys[restKeys.length - 1].pose)) throw new Error("the resting hands hit the body on this robot");
    const restPose = restKeys[restKeys.length - 1].pose;
    const rIn = planSafe(home, restKeys[0].pose), rOut = planSafe(restPose, home);
    if (rIn.fail || rOut.fail) throw new Error("no safe way from home to the resting hands");
    fit.rest = {
      keys: restKeys,
      in: rIn.path.slice(1, -1).map((q) => ({ pose: q, t: 300, via: true })),
      out: rOut.path.slice(1, -1).map((q) => ({ pose: q, t: 300, via: true }))
    };
    for (const [id, g] of Object.entries(L.gestures || {})) {
      await new Promise((r2) => setTimeout(r2, 0));
      fit.defs[id] = g.keys || [];
      for (const m of g.mirror && !(g.keys || []).some((k) => k.pose) ? [false, true] : [false]) {
        const vid = id + (m ? "~m" : "");
        const one = talkFitOne(g.keys || [], m, restPose);
        if (one.bad) fit.bad[vid] = one.bad;
        else fit.gestures[vid] = one;
      }
      pose = saved.slice();
      applyPose();
    }
    const ids = Object.keys(fit.gestures);
    for (const a of ids) for (const b of ids) {
      const ka = fit.gestures[a].keys, kb = fit.gestures[b].keys;
      if (a !== b && !pathHit(ka[ka.length - 1].pose, kb[0].pose)) fit.direct.push(a + ">" + b);
    }
    const r = await fetch("/api/gestures/fit", { method: "POST", body: JSON.stringify({ ...fit, character: TALK.character, gestureRevision: TALK.revision }) }).then((x) => x.json());
    if (!r.ok) throw new Error(r.error || "the hub did not keep it");
    TALK.fit = fit;
    TALK.revision = r.gestureRevision || TALK.revision;
    talkRender();
    return true;
  } catch (e) {
    talkSay("The gestures could not be fitted: " + Mice.Words.plain(e).says);
    return false;
  } finally {
    pose = saved;
    applyPose();
    TALK.busy = false;
  }
}
async function talkCheckFit() {
  if (!TALK.lib && !await talkLoad()) return;
  if (talkStale()) await talkFit();
}
function talkShown() {
  talkCheckFit();
}
setInterval(() => {
  if (!TALK.busy && !document.hidden && performance.now() - talkIdleAt > TALK_IDLE_MS && typeof robot !== "undefined" && robot) {
    talkIdleAt = performance.now();
    talkCheckFit();
  }
}, 5e3);
function talkRender() {
  const card = $("talkCard");
  if (!card) return;
  card.hidden = !TALK.hub;
  if (!TALK.hub) return;
  const L = TALK.lib, F = TALK.fit || {};
  $("talkOn").checked = L.on !== false;
  const sel = $("talkManner"), keep = sel.value;
  sel.textContent = "";
  Object.keys(L.manners || {}).filter((m) => m !== "_default").forEach((m) => {
    const o = document.createElement("option");
    o.value = o.textContent = m;
    sel.appendChild(o);
  });
  sel.value = keep || "friendly";
  const rs = $("talkRest");
  rs.textContent = "";
  Object.entries(L.rests || {}).forEach(([id, r]) => {
    const o = document.createElement("option");
    o.value = id;
    o.textContent = (r || {}).label || id;
    rs.appendChild(o);
  });
  rs.value = L.restStyle || "";
  try {
    $("talkAi").checked = localStorage.getItem("talkAi") === "1";
  } catch (e) {
  }
  const n = Object.keys(F.gestures || {}).length, bad = Object.keys(F.bad || {});
  talkSay(talkStale() ? "The gestures are not fitted to this robot as it is now. They will be in a moment." : n + " gestures fitted to this robot and kept clear of its body." + (bad.length ? " Left out on this robot: " + bad.map((b) => talkName(b) + " (" + F.bad[b] + ")").join(", ") + "." : ""));
  const list = $("talkList");
  list.textContent = "";
  Object.entries(L.gestures || {}).forEach(([id, g]) => {
    const row = document.createElement("div");
    row.className = "row";
    const name = document.createElement("span");
    name.className = "lbl";
    name.textContent = g.label || id;
    const words = document.createElement("input");
    words.style.flex = "1";
    words.style.minWidth = "0";
    words.title = "Words that bring this gesture, a comma between. Any language.";
    words.value = [].concat(...Object.values(g.words || {})).join(", ");
    words.onchange = () => talkSave({ gestures: { [id]: { words: { any: words.value.split(",").map((s) => s.trim()).filter(Boolean) } } } });
    const show = document.createElement("button");
    show.textContent = "▶";
    show.title = "Put this gesture on the time bar, fitted to this robot";
    show.onclick = () => talkShowOne(id);
    row.append(name, words, show);
    if (g.mine) {
      const del = document.createElement("button");
      del.textContent = "✕";
      del.title = "Remove this gesture";
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
    const j = await fetch("/api/gestures", { method: "POST", body: JSON.stringify({ ...change, character: TALK.character, gestureRevision: TALK.revision }) }).then((r) => r.json());
    if (!j.ok) throw new Error(j.error || "not saved");
    TALK.lib = j.lib;
    TALK.revision = j.gestureRevision || TALK.revision;
    talkRender();
    talkCheckFit();
  } catch (e) {
    talkSay("Not saved: " + Mice.Words.plain(e).says);
    notice($("talkStat").textContent);
  }
}
function talkSaveSwitch() {
  talkSave({ on: $("talkOn").checked });
}
async function talkEvents() {
  var _a;
  const box = $("talkEvents");
  if (!box) return;
  if (!TALK.events) {
    TALK.events = [];
    try {
      TALK.events = (((_a = (await fetch("/api/voice/config").then((r) => r.json())).config) == null ? void 0 : _a.scenarios) || []).map((s) => s.name).filter(Boolean);
    } catch (e) {
    }
  }
  const names = TALK.events;
  box.textContent = "";
  if (!names.length) {
    box.textContent = "No events are set up on the Voice page yet.";
    return;
  }
  names.forEach((n) => {
    const lab = document.createElement("label");
    lab.className = "row";
    const c = document.createElement("input");
    c.type = "checkbox";
    c.checked = ((TALK.lib.events || {})[n] || {}).on !== false;
    c.onchange = () => talkSave({ events: { [n]: Object.assign({}, (TALK.lib.events || {})[n], { on: c.checked }) } });
    lab.append(c, document.createTextNode(" " + n));
    box.appendChild(lab);
  });
}
async function talkToBar(steps, what) {
  if (!await askUnsaved(what)) return false;
  keys = steps.map((s, i) => ({ pose: s.pose.map((v, j) => clampJ(j, v)), t: i ? s.t : 1e3, hold: s.hold || 0, tset: i > 0 }));
  bumpKeys();
  clearBadMarks();
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  return true;
}
function talkAiSwitch() {
  try {
    localStorage.setItem("talkAi", $("talkAi").checked ? "1" : "0");
  } catch (e) {
  }
}
const talkPost = (url, body) => fetch(url, { method: "POST", body: JSON.stringify(body) }).then(async (r) => Object.assign({ status: r.status }, await r.json().catch(() => ({}))));
function talkFitDef(id, def, mirror) {
  const rest = (TALK.fit || {}).rest;
  if (!rest || !robot) return { bad: "the gestures are not fitted yet" };
  const restPose = rest.keys[rest.keys.length - 1].pose, saved = pose.slice();
  const out = {};
  let bad = "";
  try {
    for (const m of mirror ? [false, true] : [false]) {
      const one = talkFitOne(def, m, restPose);
      if (one.bad) bad = one.bad;
      else out[id + (m ? "~m" : "")] = one;
    }
  } finally {
    pose = saved;
    applyPose();
  }
  return Object.keys(out).length ? { fit: out } : { bad: bad || "it does not fit this robot" };
}
async function talkMake(text) {
  let made = [], why = "";
  const r = await talkPost("/api/gestures/make", { text }).catch((e) => ({ error: String(e) }));
  if (r.ok) made = r.made || [];
  if (!made.length && $("talkAi").checked) {
    talkSay("Asking the AI for a move…");
    const a = await talkPost("/api/gestures/think", { text }).catch((e) => ({ error: String(e) }));
    if (a.status === 401 || a.need_login) why = "Log in (Robot tab) to ask the AI for moves.";
    else if (a.ok) made = a.made || [];
    else why = "The AI made no move: " + (a.why || a.error || "no answer");
  }
  for (const m of made) Object.assign(m, talkFitDef(m.id, m.keys, m.mirror));
  return { made, why };
}
async function talkSound(text, manner) {
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang: "", style: manner })
    });
    if (r.status === 401) return { why: "log in (Robot tab) to hear the voice" };
    if (!r.ok) return { why: (await r.json().catch(() => ({}))).error || "the voice did not answer" };
    const url = URL.createObjectURL(await r.blob()), audio = new Audio(url);
    await new Promise((ok, no) => {
      audio.onloadedmetadata = ok;
      audio.onerror = no;
    });
    return { audio, url, ms: isFinite(audio.duration) ? audio.duration * 1e3 : 0 };
  } catch (e) {
    return { why: "the voice could not play here" };
  }
}
async function talkTry() {
  const text = $("talkText").value.trim();
  if (!text) {
    talkSay("Type something the robot might say.");
    return;
  }
  if (TALK.audio) {
    TALK.audio.pause();
    TALK.audio = null;
  }
  await talkCheckFit();
  const manner = $("talkManner").value;
  talkSay("Getting the voice and the moves…");
  const [mk, snd] = await Promise.all([talkMake(text), talkSound(text, manner)]);
  const extra = {};
  mk.made.filter((m) => m.fit).forEach((m) => {
    extra[m.id] = { label: m.label, words: m.words, keys: m.keys, mirror: m.mirror, fit: { gestures: m.fit } };
  });
  TALK.made = mk.made;
  talkMadeRender(mk.why);
  const j = await talkPost("/api/gestures/plan", {
    text,
    manner,
    ms: snd.ms || 0,
    extra,
    seed: Math.floor(Math.random() * 1e9)
  }).catch((e) => ({ why: String(e) }));
  if (!j.ok) {
    talkSay(j.why || j.error || "No gestures for that.");
    return;
  }
  if (!await talkToBar(j.steps, "put these gestures on the time bar")) return;
  $("talkPicks").textContent = j.picks.length ? j.picks.map((p) => (p.at / 1e3).toFixed(1) + " s " + p.label + (p.mirrored ? " (other arm)" : "") + (p.word ? " ← “" + p.word + "”" : "")).join(" · ") : "No gesture fitted this robot for that.";
  talkSay(snd.audio ? "Saying it with the arms." : "The moves show without sound: " + snd.why + ".");
  if (playing) await togglePlay();
  playT = 0;
  await togglePlay({ previewOnly: true });
  if (snd.audio && playing) {
    TALK.audio = snd.audio;
    snd.audio.ontimeupdate = () => {
      if (!playing) snd.audio.pause();
    };
    snd.audio.onended = () => URL.revokeObjectURL(snd.url);
    snd.audio.play().catch(() => talkSay("The browser held the sound back: press Show again."));
  }
  $("tlStat").textContent = "Gestures for " + (j.ms / 1e3).toFixed(1) + " s of talk. Show again for another random pick; Play repeats the moves without sound.";
}
function talkMadeRender(why) {
  const box = $("talkMade");
  box.textContent = "";
  const made = TALK.made || [];
  if (why) {
    const p = document.createElement("div");
    p.className = "mini";
    p.textContent = why;
    box.appendChild(p);
  }
  if (!made.length) return;
  const h = document.createElement("div");
  h.className = "mini";
  h.textContent = "New moves made for words no gesture has:";
  box.appendChild(h);
  made.forEach((m) => {
    const row = document.createElement("div");
    row.className = "row";
    const name = document.createElement("span");
    name.className = "lbl";
    name.textContent = m.label + " ← “" + m.word + "”" + (m.by === "ai" ? " (AI)" : "");
    row.appendChild(name);
    if (!m.fit) {
      const no = document.createElement("span");
      no.className = "mini";
      no.textContent = "not safe on this robot: " + m.bad;
      row.appendChild(no);
    } else {
      const show = document.createElement("button");
      show.textContent = "▶";
      show.title = "Put this move on the time bar, fitted to this robot";
      show.onclick = () => talkShowFitted(m.label, m.fit[Object.keys(m.fit)[0]]);
      const keep = document.createElement("button");
      keep.textContent = "＋ Keep";
      keep.title = "Keep it as a gesture: the Voice page then uses it for these words";
      keep.onclick = () => talkSave({ gestures: { [m.id]: {
        label: m.label,
        mine: true,
        made: m.by,
        mirror: m.mirror,
        words: m.words,
        keys: m.keys
      } } });
      row.append(show, keep);
    }
    box.appendChild(row);
  });
}
async function talkShowOne(id) {
  await talkCheckFit();
  const F = TALK.fit || {}, g = (F.gestures || {})[id];
  if (!g || !F.rest) {
    talkSay(talkName(id) + " is not fitted to this robot: " + ((F.bad || {})[id] || "fit it first"));
    return;
  }
  talkShowFitted(talkName(id), g);
}
async function talkShowFitted(name, g) {
  const rest = (TALK.fit || {}).rest;
  if (!rest) return;
  const steps = [{ pose: rest.keys[rest.keys.length - 1].pose, t: 0, hold: 300 }].concat(g.in, g.keys, g.out, [{ pose: rest.keys[rest.keys.length - 1].pose, t: 500, hold: 0 }]);
  if (await talkToBar(steps, "show this gesture on the time bar")) $("tlStat").textContent = name + " is on the time bar. Press Play to watch.";
}
async function talkAddFromBar() {
  const name = $("talkNewName").value.trim();
  if (!name) {
    talkSay("Give the gesture a name first.");
    return;
  }
  const K = playKeys();
  if (K.length < 1) {
    talkSay("Put at least one move on the time bar first.");
    return;
  }
  const id = "mine_" + name.toLowerCase().replace(/[^\w]+/g, "_");
  await talkSave({ gestures: { [id]: {
    label: name,
    mine: true,
    words: { any: $("talkNewWords").value.split(",").map((s) => s.trim()).filter(Boolean) },
    keys: K.map((k) => ({ pose: k.pose.map((v) => Math.round(v * 10) / 10), t: Math.round(k.t || 400), hold: Math.round(k.hold || 0) }))
  } } });
  talkSay(name + " is kept as a gesture. It is fitted and checked next, then the Voice page can use it.");
}
window.addEventListener("load", () => setTimeout(talkLoad, 800));
function resize() {
  const w = viewport.clientWidth, h = viewport.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  syncOrtho();
  viewport.classList.toggle("short", h < 260);
  markDirty3d(5);
}
window.addEventListener("resize", resize);
if (window.ResizeObserver) {
  let lastW = 0, lastH = 0;
  new ResizeObserver(function() {
    const w = viewport.clientWidth, h = viewport.clientHeight;
    if (w === lastW && h === lastH) return;
    lastW = w;
    lastH = h;
    resize();
  }).observe(viewport);
}
let lastPlayMs = 0;
let _drawing = false;
let _lastScrub = -1, _lastTime = "";
function playTick() {
  if (!playing) {
    lastPlayMs = 0;
    return;
  }
  if (entryHold) {
    lastPlayMs = 0;
    return;
  }
  const now = performance.now();
  if (!lastPlayMs) {
    lastPlayMs = now;
    return;
  }
  const audioMs = typeof sequenceAudio !== "undefined" ? sequenceAudio.clock(playT) : null;
  const dt = audioMs == null ? Math.min(now - lastPlayMs, MAX_TICK_MS) : Math.max(0, audioMs - playT);
  lastPlayMs = now;
  if (dt <= 0) return;
  playT += dt;
  const total = totalMs();
  if (playT >= total) {
    if ($("loopChk").checked) {
      playT = 0;
      lastLiveSeg = -1;
      if (typeof sequenceAudio !== "undefined" && sequenceAudio.preview && sequenceAudio.media) sequenceAudio.restart();
    } else {
      playT = total;
      playing = false;
      $("playBtn").textContent = "▶ Play";
      if (typeof sequenceAudio !== "undefined") sequenceAudio.pausePreview();
      keepAwake(false);
    }
  }
  pose = (audioMs == null ? servoPlayPose(poseAt(playT), dt) : sequenceAudio.visualPose(playT)).map((v, i) => clampJ(i, v));
  if (_drawing) {
    applyPose();
    renderSliders();
    const scrub = total ? Math.round(playT / total * 1e3) : 0;
    if (_lastScrub !== scrub) {
      _lastScrub = scrub;
      $("scrub").value = scrub;
    }
    const lbl = (playT / 1e3).toFixed(1) + "s / " + (total / 1e3).toFixed(1) + "s";
    if (_lastTime !== lbl) {
      _lastTime = lbl;
      $("tlTime").textContent = lbl;
    }
  }
  if (liveLinked() && !hubDriven() && !previewOnly) {
    const seg = segmentAt(playT);
    if (seg !== -1 && seg !== lastLiveSeg) {
      lastLiveSeg = seg;
      const K = playKeys();
      const rem = segRemaining(playT);
      const to = seg === K.length ? { pose: K[0].pose, t: loopReturnMs() } : K[seg];
      const tt = to.t - rem <= 50 ? to.t : rem;
      liveSend("POSE " + to.pose.map(fmtA).join(" ") + " T " + tt);
    }
  }
}
let _dirty3d = 60;
function markDirty3d(n) {
  _dirty3d = Math.max(_dirty3d, n || 10);
}
if (typeof controls !== "undefined" && controls && controls.addEventListener) {
  controls.addEventListener("change", function() {
    markDirty3d(5);
  });
}
function tick(now) {
  requestAnimationFrame(tick);
  freezeCheck(now);
  _drawing = true;
  playTick();
  _drawing = false;
  lastFrame = now;
  distDraw();
  const inMotion = controls ? controls.update() : false;
  const needRender = playing || inMotion || typeof distShown === "function" && distShown() || _dirty3d > 0;
  if (needRender && (!window.MiceResources || window.MiceResources.frameDue(now))) {
    if (!playing && !inMotion && (!distShown || !distShown()) && _dirty3d > 0) _dirty3d--;
    renderer.render(scene, activeCam());
    if (window.MiceResources) window.MiceResources.rendered(now);
  }
}
function runServoSelfTest() {
  const save = {
    dps: RIG.servoMaxDps.slice(),
    lo: RIG.pulseMin.slice(),
    hi: RIG.pulseMax.slice(),
    rng: RIG.servoRange.slice(),
    mn: RIG.min.slice(),
    mx: RIG.max.slice(),
    gp: RIG.gearPinion.slice(),
    gg: RIG.gearGear.slice(),
    hz: RIG.frameHz.slice()
  };
  const fails = [];
  const flat = new Array(NJ).fill(90);
  RIG.servoMaxDps = new Array(NJ).fill(400);
  const a = flat.slice();
  a[2] = 130;
  const fastElbow = minTime(flat, a);
  const b = flat.slice();
  b[0] = 130;
  const fastSh = minTime(flat, b);
  RIG.servoMaxDps[2] = 100;
  const slowElbow = minTime(flat, a);
  const shAfter = minTime(flat, b);
  if (!(slowElbow > fastElbow * 3.5))
    fails.push(`slow joint did not stretch its move (${fastElbow}->${slowElbow}ms)`);
  if (shAfter !== fastSh)
    fails.push(`slow joint changed an unrelated move (${fastSh}->${shAfter}ms)`);
  RIG.servoMaxDps = new Array(NJ).fill(1);
  RIG.pulseMin = new Array(NJ).fill(1);
  RIG.pulseMax = new Array(NJ).fill(1);
  RIG.servoRange = new Array(NJ).fill(1);
  applyServoPreset("pdi1181mg|sh");
  const shIdx = [0, 1, 4, 5], elIdx = [2, 3, 6, 7];
  if (!shIdx.every((i) => RIG.pulseMax[i] === 2500 && RIG.servoMaxDps[i] === 375 && RIG.servoRange[i] === 270))
    fails.push("shoulder preset did not reach every shoulder joint (with 270 travel)");
  if (!elIdx.every((i) => RIG.pulseMax[i] === 1))
    fails.push("shoulder preset leaked into the elbows");
  if (RIG.pulseMax[8] === 2500 || RIG.pulseMax[9] === 2500)
    fails.push("shoulder preset leaked into the body joints");
  applyServoPreset("mg90s|el");
  if (!elIdx.every((i) => RIG.pulseMax[i] === 2400 && RIG.servoMaxDps[i] === 400))
    fails.push("elbow preset did not reach every elbow joint");
  if (!shIdx.every((i) => RIG.pulseMax[i] === 2500))
    fails.push("elbow preset overwrote the shoulders");
  applyServoPreset("tiankong35|waist");
  if (!(RIG.servoRange[8] === 270 && RIG.pulseMax[8] === 2500 && RIG.servoMaxDps[8] === 250))
    fails.push("tiankong35 waist preset did not set the WAIST joint");
  if (RIG.servoRange[9] === 270) fails.push("waist preset leaked into the shrug");
  applyServoPreset("mg90s|shrug");
  if (!(RIG.servoRange[9] === 180 && RIG.pulseMax[9] === 2400))
    fails.push("mg90s shrug preset did not set the SHRUG joint");
  RIG.gearPinion = new Array(NJ).fill(15);
  RIG.gearGear = new Array(NJ).fill(18);
  RIG.min = new Array(NJ).fill(10);
  RIG.max = new Array(NJ).fill(170);
  RIG.servoRange = new Array(NJ).fill(180);
  const w180 = travelWarning(0);
  RIG.servoRange = new Array(NJ).fill(270);
  const w270 = travelWarning(0);
  if (!w180) fails.push("180 deg servo not flagged as too narrow for a 10-170 joint");
  if (w270) fails.push("270 deg servo wrongly flagged as too narrow: " + w270);
  RIG.min = new Array(NJ).fill(60);
  RIG.max = new Array(NJ).fill(120);
  RIG.servoRange = new Array(NJ).fill(180);
  if (travelWarning(0)) fails.push("180 deg servo wrongly flagged on a narrow joint");
  applyServoPreset("generic270|sh");
  if (!(RIG.servoRange[0] === 270 && RIG.servoRange[4] === 270))
    fails.push("generic270 preset did not set the shoulders' travel");
  if (RIG.servoRange[2] !== 180)
    fails.push("generic270 preset leaked travel into the elbows");
  RIG.frameHz = new Array(NJ).fill(111);
  applyServoPreset("pdi1181mg|sh");
  if (!shIdx.every((i) => RIG.frameHz[i] === 50))
    fails.push("pdi1181mg preset did not set 50 Hz on the shoulders");
  if (!elIdx.every((i) => RIG.frameHz[i] === 111))
    fails.push("pdi1181mg preset changed the elbows' frame rate");
  RIG.servoMaxDps = save.dps;
  RIG.pulseMin = save.lo;
  RIG.pulseMax = save.hi;
  RIG.servoRange = save.rng;
  RIG.min = save.mn;
  RIG.max = save.mx;
  RIG.gearPinion = save.gp;
  RIG.gearGear = save.gg;
  RIG.frameHz = save.hz;
  rigChanged();
  renderRigUI();
  document.title = fails.length ? "SERVO FAIL " + fails.join(" | ") : `SERVO PASS slowJointStretched=${fastElbow}->${slowElbow}ms otherMoveUnchanged=${shAfter}ms presets=perGroup travel=ok frameRate=default50`;
  console.log(document.title);
}
renderRigUI();
buildRobot();
showTab("pose");
addKey();
renderSliders();
renderTimeline();
poseChanged(false);
refreshProjects();
refreshSeqs();
refreshShows();
renderShow();
refreshModels();
connModeChanged();
initSideDrag();
initTimeDrag();
draftArmed = true;
markClean(workSig(), "");
offerDraft();
resize();
requestAnimationFrame((t) => {
  lastFrame = t;
  tick(t);
});
{
  const qp = new URLSearchParams(location.search);
  const dev = qp.get("dev") || "";
  const startMonitor = () => {
    if (qp.get("monitor") === "1") {
      $("monChk").checked = true;
      monitorChanged();
    }
  };
  const at = dev.indexOf("@");
  const peer = at >= 0 ? dev.slice(at + 1) : "";
  const addr = at >= 0 ? dev.slice(0, at) : dev;
  window.HUB_PEER = peer;
  let via = "";
  let inner = addr;
  if (inner.indexOf("hub:") === 0) {
    const slash = inner.indexOf("/");
    if (slash > 0) {
      via = inner.slice(0, slash + 1);
      inner = inner.slice(slash + 1);
    }
  }
  window.HUB_VIA = via;
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
      if (sel.value !== bits[0]) {
        const o = document.createElement("option");
        o.value = o.textContent = bits[0];
        sel.appendChild(o);
        sel.value = bits[0];
      }
      return connectRobot();
    }).then(startMonitor);
  } else if (qp.get("ip") || inner.indexOf("wifi:") === 0) {
    $("robotIp").value = qp.get("ip") || inner.slice(5);
    connectRobot().then(startMonitor);
  }
  if (qp.get("selftest") === "ik") setTimeout(runIkSelfTest, 400);
  if (qp.get("selftest") === "gimbal") setTimeout(runGimbalSelfTest, 400);
  if (qp.get("selftest") === "elbow") setTimeout(runElbowSelfTest, 400);
  if (qp.get("selftest") === "view") setTimeout(runViewSelfTest, 400);
  if (qp.get("selftest") === "servo") setTimeout(runServoSelfTest, 400);
  if (qp.get("selftest") === "migrate") setTimeout(runMigrateSelfTest, 400);
}
function runMigrateSelfTest() {
  const fails = [];
  const old = {
    // a pre-waist/shrug saved rig
    dims: { shoulderX: 105, shoulderY: 95, upperLen: 115, foreLen: 105 },
    zero: [90, 90, 90, 90, 90, 90, 90, 90],
    min: [30, 30, 30, 30, 30, 30, 30, 30],
    max: [150, 150, 150, 150, 150, 150, 150, 150],
    axis: ["x", "z", "x", "z", "x", "z", "x", "z"],
    invert: [0, 0, 0, 0, 0, 0, 0, 0],
    neutral: [90, 90, 90, 90, 90, 90, 90, 90],
    gearPinion: [15, 15, 12, 12, 15, 15, 12, 12],
    gearGear: [18, 18, 13, 13, 18, 18, 13, 13],
    tilt: [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]],
    jointR: [17, 15, 17, 15],
    barR: [13, 11, 13, 11]
  };
  const m = mergeRig(old);
  [
    "zero",
    "min",
    "max",
    "axis",
    "invert",
    "neutral",
    "gearPinion",
    "gearGear",
    "pulseMin",
    "pulseMax",
    "servoMaxDps",
    "servoRange",
    "tilt"
  ].forEach((k) => {
    if (!Array.isArray(m[k]) || m[k].length !== NJ)
      fails.push(`${k} not length ${NJ} (got ${Array.isArray(m[k]) ? m[k].length : typeof m[k]})`);
  });
  const savedRig = RIG, savedPose = pose;
  RIG = m;
  pose = new Array(NJ).fill(90);
  buildRobot();
  const finite = (o) => o && Number.isFinite(o.rotation.x) && Number.isFinite(o.rotation.y) && Number.isFinite(o.rotation.z);
  if (!finite(bodyGroup)) fails.push("bodyGroup rotation NaN (waist)");
  if (!finite(shoulderMount)) fails.push("shoulderMount rotation NaN (shrug)");
  for (let i = 0; i < ARMJ; i++)
    if (jointGroups[i] && !Number.isFinite(jointGroups[i].quaternion.x)) {
      fails.push(`joint ${i} quaternion NaN`);
      break;
    }
  RIG = savedRig;
  pose = savedPose;
  buildRobot();
  document.title = fails.length ? "MIGRATE FAIL " + fails.join(" | ") : `MIGRATE PASS old-8-joint rig -> all length ${NJ}, body transforms finite`;
  console.log(document.title);
}
function ikTo(arm, target) {
  const wrKey = arm === 0 ? "wrL" : "wrR";
  const start = fkPoints(pose)[wrKey].clone();
  const steps = Math.min(60, Math.max(6, Math.ceil(start.distanceTo(target) / 12)));
  for (let s = 1; s <= steps; s++) solveIK(arm, start.clone().lerp(target, s / steps), 8);
  solveIK(arm, target, 25);
  return fkPoints(pose)[wrKey];
}
function runIkSelfTest() {
  const arm = 0, idxSh = [0, 1], idxEl = [2, 3];
  const poses = [
    [110, 100, 95, 90],
    [70, 90, 120, 90],
    [90, 110, 90, 110],
    [130, 80, 115, 100],
    [60, 120, 130, 80]
  ];
  let pass = 0, worst = 0, shOK = true, elOK = true, errs = [];
  const reach = (RIG.dims.upperLenL || 115) + (RIG.dims.foreLenL || 105);
  const tol = Math.max(8, reach * 0.045);
  poses.forEach((tp) => {
    pose = [...RIG.neutral];
    for (let k = 0; k < 4; k++) pose[idxSh[0] + k] = clampJ(idxSh[0] + k, tp[k]);
    applyPose();
    robot.updateMatrixWorld(true);
    const target = fkPoints(pose).wrL.clone();
    pose = [...RIG.neutral];
    const before = [...pose];
    ikTo(arm, target);
    const err = fkPoints(pose).wrL.distanceTo(target);
    errs.push(err.toFixed(0));
    worst = Math.max(worst, err);
    if (err < tol) pass++;
    if (Math.abs(pose[0] - before[0]) + Math.abs(pose[1] - before[1]) < 0.3) shOK = false;
    if (Math.abs(pose[2] - before[2]) + Math.abs(pose[3] - before[3]) < 0.3) elOK = false;
  });
  pose = [...RIG.neutral];
  poseChanged(false);
  const ok = pass === poses.length && shOK && elOK;
  const msg = `IKTEST ${ok ? "PASS" : "FAIL"} reached ${pass}/${poses.length} worst=${worst.toFixed(1)}mm tol=${tol.toFixed(1)}mm errs=[${errs}] shoulderMoves=${shOK} elbowMoves=${elOK}`;
  document.title = msg;
  $("tlStat").textContent = msg;
}
function ringFollows(pairIdx, pitchJoint) {
  pose = [...RIG.neutral];
  applyPose();
  robot.updateMatrixWorld(true);
  showGizmo(pairIdx);
  const second = rings[1].mesh;
  const q0 = second.getWorldQuaternion(new THREE.Quaternion());
  pose[pitchJoint] = clampJ(pitchJoint, 130);
  applyPose();
  robot.updateMatrixWorld(true);
  const q1 = second.getWorldQuaternion(new THREE.Quaternion());
  showGizmo(-1);
  return q0.angleTo(q1) * 180 / Math.PI;
}
function runGimbalSelfTest() {
  const sh = ringFollows(0, 0);
  const el = ringFollows(1, 2);
  pose = [...RIG.neutral];
  poseChanged(false);
  const ok = sh > 10 && el > 10 && Math.abs(sh - el) < 3;
  document.title = `GIMBAL ${ok ? "PASS" : "FAIL"} shoulderInnerTurned=${sh.toFixed(1)}deg elbowInnerTurned=${el.toFixed(1)}deg`;
}
function runViewSelfTest() {
  const t = controls.target;
  const checks = [
    ["front", "z", 1, "xy"],
    ["back", "z", -1, "xy"],
    ["right", "x", 1, "yz"],
    ["left", "x", -1, "yz"],
    ["top", "y", 1, "xz"],
    ["bottom", "y", -1, "xz"]
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
  const arm = 0;
  pose = [...RIG.neutral];
  pose[0] = 120;
  pose[1] = 115;
  applyPose();
  robot.updateMatrixWorld(true);
  const target = elbowBalls[arm].getWorldPosition(new THREE.Vector3());
  pose = [...RIG.neutral];
  const before = [...pose];
  solveElbowIK(arm, target);
  const err = elbowBalls[arm].getWorldPosition(new THREE.Vector3()).distanceTo(target);
  const shMoved = Math.abs(pose[0] - before[0]) + Math.abs(pose[1] - before[1]) > 1;
  const elbowUntouched = Math.abs(pose[2] - before[2]) + Math.abs(pose[3] - before[3]) < 0.1;
  pose = [...RIG.neutral];
  poseChanged(false);
  document.title = `ELBOW ${err < 8 && shMoved && elbowUntouched ? "PASS" : "FAIL"} err=${err.toFixed(1)}mm shoulderMoved=${shMoved} elbowJointsUntouched=${elbowUntouched}`;
}
function getAccounts() {
  try {
    const acc = JSON.parse(localStorage.getItem("nongAccounts"));
    if (acc && typeof acc === "object") return acc;
  } catch (e) {
  }
  return { "super_admin": "admin123", "admin": "admin123" };
}
function saveAccounts(acc) {
  localStorage.setItem("nongAccounts", JSON.stringify(acc));
}
function loggedIn(u) {
  currentUser = u;
  $("loginStat").textContent = "";
  showTab(sideTab);
  window.dispatchEvent(new Event("resize"));
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
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: u, password: p })
    });
    const j = await r.json().catch(() => ({}));
    ok = r.ok && !!j.ok;
    why = j.locked_for > 0 ? `Too many tries. Wait ${j.locked_for} seconds.` : "";
  } catch (e) {
    const acc = getAccounts();
    ok = !!(acc[u] && acc[u] === p);
  }
  if (ok) {
    $("loginPass").value = "";
    localStorage.removeItem("nongZeroCred");
    loggedIn(u);
  } else {
    $("loginStat").textContent = why || "Wrong username or password.";
  }
}
async function syncHubLogin() {
  if (currentUser) return;
  try {
    const j = await fetch("/api/whoami").then((r) => r.json());
    if (j.authed && !currentUser) loggedIn(j.user || "user");
  } catch (e) {
  }
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
  if (!u) {
    $("muStat").textContent = "Username required.";
    return;
  }
  const acc = getAccounts();
  if (p) {
    acc[u] = p;
  } else if (!acc[u]) {
    $("muStat").textContent = "Password required for new user.";
    return;
  }
  saveAccounts(acc);
  $("muStat").textContent = "User saved.";
  populateUserList();
  $("muList").value = u;
}
function muDelete() {
  const u = $("muUser").value.trim();
  if (!u) return;
  if (u === "super_admin") {
    $("muStat").textContent = "Cannot delete super_admin.";
    notice("Cannot delete super_admin.");
    return;
  }
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
{
  const libraryId = new URLSearchParams(location.search).get("library");
  if (libraryId) projectLibrary.open(libraryId);
}
const PANEL_KEY = "nong_panels";
const PANEL_DESK = "(min-width:861px)";
let panelSaved = {};
function panelKey(card) {
  const h = card.querySelector(":scope > h2");
  return card.dataset.stab + ":" + (h ? h.firstChild.textContent.trim() : card.id);
}
function panelKeep() {
  try {
    localStorage.setItem(PANEL_KEY, JSON.stringify(panelSaved));
  } catch (e) {
  }
}
function panelClamp(card) {
  if (!card.offsetWidth) return;
  const r = card.getBoundingClientRect();
  const x = Math.min(Math.max(0, r.left), Math.max(0, innerWidth - 120));
  const y = Math.min(Math.max(0, r.top), Math.max(0, innerHeight - 40));
  card.style.left = x + "px";
  card.style.top = y + "px";
}
function panelFloat(card, at, remember) {
  const r = card.getBoundingClientRect();
  at = at || { x: r.left - 40, y: r.top + 20, w: r.width };
  card.classList.add("floating");
  card.style.left = at.x + "px";
  card.style.top = at.y + "px";
  card.style.width = (at.w || r.width) + "px";
  if (at.h) card.style.height = at.h + "px";
  showTab(sideTab);
  panelClamp(card);
  card.querySelector(".popout").textContent = "⇲";
  card.querySelector(".popout").title = "Put this panel back in the side panel";
  if (remember) {
    panelSaved[panelKey(card)] = panelWhere(card);
    panelKeep();
  }
}
function panelDock(card) {
  card.classList.remove("floating");
  ["left", "top", "width", "height"].forEach((k) => card.style[k] = "");
  card.querySelector(".popout").textContent = "⧉";
  card.querySelector(".popout").title = "Take this panel out: drag it anywhere, it stays open on every tab";
  delete panelSaved[panelKey(card)];
  panelKeep();
  showTab(sideTab);
}
function panelWhere(card) {
  const r = card.getBoundingClientRect();
  return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
}
function panelDrag(card, h) {
  let start = null, moved = false;
  h.addEventListener("pointerdown", (e) => {
    if (!card.classList.contains("floating") || e.target.closest("label, input, button, select, a")) return;
    const r = card.getBoundingClientRect();
    start = { x: e.clientX - r.left, y: e.clientY - r.top, cx: e.clientX, cy: e.clientY };
    moved = false;
    try {
      h.setPointerCapture(e.pointerId);
    } catch (err) {
    }
  });
  h.addEventListener("pointermove", (e) => {
    if (!start) return;
    if (Math.abs(e.clientX - start.cx) + Math.abs(e.clientY - start.cy) > 4) moved = true;
    card.style.left = e.clientX - start.x + "px";
    card.style.top = e.clientY - start.y + "px";
  });
  h.addEventListener("pointerup", () => {
    if (!start) return;
    start = null;
    panelClamp(card);
    panelSaved[panelKey(card)] = panelWhere(card);
    panelKeep();
  });
  card.addEventListener("click", (e) => {
    if (moved && e.target.closest(":scope > h2")) {
      e.stopPropagation();
      moved = false;
    }
  }, true);
}
function initPanels() {
  try {
    panelSaved = JSON.parse(localStorage.getItem(PANEL_KEY)) || {};
  } catch (e) {
  }
  const desk = window.matchMedia(PANEL_DESK);
  document.querySelectorAll("#side div.card[data-stab]").forEach((card) => {
    const h = card.querySelector(":scope > h2");
    if (!h || card.dataset.stab === "login" || card.id === "userManageCard") return;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "popout";
    b.textContent = "⧉";
    b.title = "Take this panel out: drag it anywhere, it stays open on every tab";
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      if (card.classList.contains("floating")) panelDock(card);
      else panelFloat(card, null, true);
    });
    h.appendChild(b);
    panelDrag(card, h);
    const at = panelSaved[panelKey(card)];
    if (at && desk.matches) panelFloat(card, at, false);
  });
  if ("ResizeObserver" in window) {
    let soon = null;
    const ro = new ResizeObserver(() => {
      clearTimeout(soon);
      soon = setTimeout(() => {
        document.querySelectorAll("#side .card.floating").forEach((c) => {
          if (c.offsetWidth) panelSaved[panelKey(c)] = panelWhere(c);
        });
        panelKeep();
      }, 300);
    });
    document.querySelectorAll("#side div.card[data-stab]").forEach((c) => ro.observe(c));
  }
  desk.addEventListener("change", () => {
    document.querySelectorAll("#side .card.floating").forEach((c) => {
      c.classList.remove("floating");
      ["left", "top", "width", "height"].forEach((k) => c.style[k] = "");
    });
    if (desk.matches) document.querySelectorAll("#side div.card[data-stab]").forEach((c) => {
      const at = panelSaved[panelKey(c)];
      if (at && c.querySelector(".popout")) panelFloat(c, at, false);
    });
    showTab(sideTab);
  });
  window.addEventListener("resize", () => document.querySelectorAll("#side .card.floating").forEach(panelClamp));
  const tabs = $("sideTabs"), side = $("side");
  if (tabs && side && "ResizeObserver" in window)
    new ResizeObserver(() => tabs.classList.toggle("narrow", side.clientWidth < 420)).observe(side);
}
initPanels();
