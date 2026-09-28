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
    await showPost("/api/show/play", { dev, show: s, limits: showLimits() });
    $("showStat").textContent = "the hub is running " + (s.name || "this show") +
      " — it keeps going with this page closed. ⏹ Stop ends it.";
  } catch (e) { $("showStat").textContent = "did not start: " + (e.message || e); notice($("showStat").textContent); }
}
async function stopShow() {
  try { await fetch("/api/play/stop", { method: "POST" }); $("showStat").textContent = "stopped."; }
  catch (e) { $("showStat").textContent = "the hub did not answer the stop."; }
}
