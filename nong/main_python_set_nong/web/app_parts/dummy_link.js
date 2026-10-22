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
  plan.path.slice(1, -1).forEach(q => liveSend("POSE " + q.map(fmtA).join(" ") + " T " + liveT()));
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
    const moved = !prev || v.some((x, i) => (x === null) !== (prev[i] === null) ||
                                       (x !== null && Math.abs(x - prev[i]) >= 0.2));
    if (moved && dummyFollowOn) {
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
