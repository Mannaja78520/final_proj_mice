function projectSnapshot() {
  return {
    sourceAudioAsset: typeof sequenceAudio !== "undefined" ? sequenceAudio.serializable() : null,
    keys, speedDps: speedDps(), maxDps: maxDps(), loop: $("loopChk").checked,
    // The planning peak limit rides with the project: without it, reopening a
    // project re-times every automatic move against a different 60 °/s default
    // and the show quietly got slower (A31-4).
    safeDps: SAFE_DPS,
    musicDps: SEQ_MUSIC_DPS,   // speed limit with music, this sequence only (A48-23)
    meshes: meshCfg, addons,
    robotIp: $("robotIp").value, seqName: $("projName").value,   // kept: older Studios read it
    // The chain is part of the show: a project saved with one and reopened
    // without it exported a different sequence than the one saved.
    seqNext: ($("seqNext").value || "").trim(),
    rig: RIG,
    // The video the moves were made from, and how (A44-8); null if none.
    video: vidSettings(),
  };
}
// --- project save/load ---
// opts.keepDraft: saveAll() clears the draft itself, only once BOTH files are
// on disk. Returns true when the project reached the disk.
async function saveProject(opts) {
  if (typeof sequenceAudio !== "undefined" && !sequenceAudio.readyForSave()) return false;
  opts = opts || {};
  const name = ($("projName").value || "project").trim();
  const sig = workSig();                  // what THIS save writes, before any await
  const project = projectSnapshot();
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
let projectLoadGeneration = 0;
async function loadProject(file) {
  if (!file) return;
  const generation = ++projectLoadGeneration;
  const a = await Mice.Api.get("/api/load?name=" + encodeURIComponent(file));
  if (generation !== projectLoadGeneration) return;
  if (!a.ok) { $("tlStat").textContent = "could not load " + file + " — " + a.says + ". Nothing on screen was changed."; notice($("tlStat").textContent); return; }
  try { return await applyProjectData(a.data, file, { generation }); }
  catch (e) { if (generation === projectLoadGeneration) notice("เปิดโปรเจกต์ไม่ได้: " + e.message + " งานเดิมยังอยู่"); }
}
async function applyProjectData(p, file, opts = {}) {
  const generation = opts.generation == null ? ++projectLoadGeneration : opts.generation;
  if (!p || !Array.isArray(p.keys) || (p.keys.length && !p.keys.some(k => k && Array.isArray(k.pose) && k.pose.some(v => Number.isFinite(Number(v))))))
    throw new Error("ไฟล์ไม่มีท่าที่อ่านได้");
  // Reject malformed supported fields before replacing rig, keys, or audio.
  for (const field of ['seqName', 'seqNext', 'robotIp'])
    if (p[field] != null && typeof p[field] !== 'string') throw new Error('ข้อมูล ' + field + ' ไม่ถูกต้อง');
  if (p.addons != null && !Array.isArray(p.addons)) throw new Error('ข้อมูล addons ไม่ถูกต้อง');
  for (const field of ['rig', 'meshes', 'video'])
    if (p[field] != null && (typeof p[field] !== 'object' || Array.isArray(p[field]))) throw new Error('ข้อมูล ' + field + ' ไม่ถูกต้อง');
  for (const key of p.keys) for (const field of ['cues', 'cuesAfter'])
    if (key && key[field] != null && (!Array.isArray(key[field]) || key[field].some(v => typeof v !== 'string')))
      throw new Error('ข้อมูลคำสั่งในคีย์ไม่ถูกต้อง');
  const preparedAudio = typeof sequenceAudio !== "undefined" ? await sequenceAudio.prepare(p.sourceAudioAsset) : null;
  await refreshModels();  // Resolve fallible model-list work before replacing any project state.
  if (generation !== projectLoadGeneration) return false;
  if (typeof sequenceAudio !== 'undefined' && sequenceAudio.pendingRef && preparedAudio &&
      sequenceAudio.pendingRef.sha256 === preparedAudio.asset.sha256 &&
      confirm('พบเพลงที่ตรงกับงานกู้คืน ใช้เพลงนี้กับท่าที่แก้ค้างไว้หรือไม่?\n\nOK — กู้เฉพาะเพลงและเก็บท่าปัจจุบันทั้งหมด\nCancel — เปิดโปรเจกต์ตามปกติ')) {
    sequenceAudio.commit(preparedAudio, keys); saveDraft();
    notice('กู้เพลงกลับแล้ว ท่าที่แก้ค้างไว้ยังอยู่ กด Save เพื่อเก็บงาน');
    return true;
  }
  if (timelinePreparing) throw new Error("กำลังตรวจเส้นทาง กดหยุดตรวจให้เสร็จก่อนเปิดโปรเจกต์ใหม่");
  if (!(await askUnsaved("open " + file))) { if ($("projList")) $("projList").value = ""; return false; }
  if (generation !== projectLoadGeneration) return false;
  if (playing && !previewOnly) throw new Error("หยุดการเล่นท่าปัจจุบันก่อนเปิดโปรเจกต์ใหม่");
  if (playing) { playing = false; keepAwake(false); $("playBtn").textContent = "▶ Play"; }
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
  if (typeof sequenceAudio !== "undefined") sequenceAudio.commit(preparedAudio, loaded);
  keys = loaded;
  bumpKeys();
  $("speedDps").value = p.speedDps || 120;
  $("maxDps").value = p.maxDps || 400;
  SEQ_MUSIC_DPS = Number.isFinite(p.musicDps) && p.musicDps >= 0 ? p.musicDps : null;
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
  if (generation !== projectLoadGeneration) return false;
  renderRigUI();
  buildRobot(); // re-applies meshes + rig in one pass
  selKey = 0;
  if (keys.length) { pose = [...keys[0].pose]; }
  poseChanged(false, 0, { previewOnly: true }); renderTimeline();
  // Only a project whose YAML already had its own name owns NAME.yaml; for any
  // other, Save still asks before replacing a NAME.yaml that is somebody else's.
  if (opts.imported) { markClean("", ""); loadedSkipped = 0; saveDraft(); }
  else markSaved(openedSig, oldSeq === pname ? pname : "", 0);
  if (oldSeq && oldSeq !== pname)
    $("tlStat").textContent = "opened " + file + ". It used to save its moves as "
      + oldSeq + ".yaml; Save now writes " + pname + ".json and " + pname + ".yaml together.";
  if (opts.imported) $("tlStat").textContent = "เปิดท่าและเพลงแล้ว — กด Save เพื่อเก็บเป็นงานของคุณ";
  return true;
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
    + "|" + (($("seqNext") && $("seqNext").value) || "").trim()
    + "|" + (typeof sequenceAudio !== "undefined" ? sequenceAudio.signature() : "");
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
  if (typeof sequenceAudio !== "undefined" && !sequenceAudio.readyForSave()) return false;
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
  (r.files || []).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}
