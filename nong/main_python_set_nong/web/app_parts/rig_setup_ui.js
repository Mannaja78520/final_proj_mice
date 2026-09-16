// --- rig setup UI ---
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
    neu.type = "number"; neu.min = 0; neu.max = 180; neu.value = RIG.neutral[i];
    neu.title = "where this joint goes when the robot starts, and when you "
              + "press Neutral or Home";
    neu.onchange = () => {
      RIG.neutral[i] = Math.max(RIG.min[i], Math.min(RIG.max[i],
                                clampDeg(+neu.value || 0)));
      neu.value = RIG.neutral[i];          // show what was actually accepted
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
  if (!haveUsb() && !haveWifi()) {
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
  if (!haveUsb() && !haveWifi()) {
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
  if (!haveUsb() && !haveWifi()) {
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
  if (!haveUsb() && !haveWifi()) { $("limStat").textContent = "connect to the robot first (Robot link card)"; notice($("limStat").textContent); return; }
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
      const neu = Math.round(RIG.neutral[i]);
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
  if (!haveUsb() && !haveWifi()) { $("limStat").textContent = "connect to the robot first"; notice($("limStat").textContent); return; }
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
    pull(j.neutral, "neutral");
    pull(j.offset, "offset");
    saveRig(); renderRigUI(); buildRobot(); renderSliders();
    $("limStat").textContent =
      "read limits, gear, start angles and offsets from the robot ✓";
  } catch (e) { $("limStat").textContent = "read failed: " + (e.message || e); notice($("limStat").textContent); }
}
