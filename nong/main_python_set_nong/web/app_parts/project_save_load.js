// --- project save/load ---
async function saveProject() {
  const name = ($("projName").value || "project").trim();
  const project = {
    keys, speedDps: speedDps(), maxDps: maxDps(), loop: $("loopChk").checked,
    meshes: meshCfg, addons,
    robotIp: $("robotIp").value, seqName: $("seqName").value,
    // The chain is part of the show: a project saved with one and reopened
    // without it exported a different sequence than the one saved.
    seqNext: ($("seqNext").value || "").trim(),
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
    notice($("tlStat").textContent);
    return;
  }
  if (!r || !r.ok) {
    $("tlStat").textContent = "could not save: " + ((r && r.error) || "unknown")
      + ". Your work is still here.";
    notice($("tlStat").textContent);
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
  // The chain rides with the project; an older project without one clears the
  // field rather than keeping a chain this project never had.
  $("seqNext").value = p.seqNext || "";
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
