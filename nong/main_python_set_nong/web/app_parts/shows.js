// --- shows: saved sequences in series ---
// User 2026-09-17: mix and match sequences (greeting, then byebye). A show is a
// list of sequence NAMES saved by the hub in shows/*.json (main_python/shows.py);
// the hub plays it as one run, so it works over WiFi or the cable.
let showDraft = { name: "", loop: false, items: [] };
let showOnBar = "";      // the show currently drawn on the time bar, "" = none

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
    add.innerHTML = "<option value=''>Add a saved sequence…</option>";
    (q.files || []).filter(f => f.endsWith(".yaml")).forEach(f => {
      const o = document.createElement("option"); o.value = o.textContent = f; add.appendChild(o);
    });
  } catch (e) { /* Studio opened without the hub: nothing to list */ }
}
function renderShow() {
  const box = $("showItems");
  if (!box) return;
  $("showName").value = showDraft.name;
  $("showLoop").checked = showDraft.loop;
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
    row.append(n, name, mode, rep, unit, document.createTextNode("pause"), hold,
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
  return showDraft;
}
function newShow() { showDraft = { name: "", loop: false, items: [] }; renderShow(); $("showStat").textContent = "new show — add sequences, then Save."; }
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
  showDraft = r.show; showDraft.name = showDraft.name || n;
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
    const j = await showPost("/api/show/steps", { show: s });
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
    selKey = 0;
    playT = 0;
    bumpKeys();
    clearBadMarks();
    renderTimeline();
    // drawn from saved files, so nothing on the bar is unsaved work yet; it is
    // no file's own moves either, so saving it still asks before replacing one
    markSaved(workSig(), "", 0);
    showOnBar = s.name || "(unsaved show)";
    const secs = (keys.reduce((a, k) => a + k.t + (k.hold || 0), 0) / 1000).toFixed(1);
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
  try {
    await showPost("/api/show/play", { dev, show: s });
    $("showStat").textContent = "the hub is running " + (s.name || "this show") +
      " — it keeps going with this page closed. ⏹ Stop ends it.";
  } catch (e) { $("showStat").textContent = "did not start: " + (e.message || e); notice($("showStat").textContent); }
}
async function stopShow() {
  try { await fetch("/api/play/stop", { method: "POST" }); $("showStat").textContent = "stopped."; }
  catch (e) { $("showStat").textContent = "the hub did not answer the stop."; }
}
