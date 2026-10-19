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
