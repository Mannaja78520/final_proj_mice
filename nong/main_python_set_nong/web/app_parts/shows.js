// --- shows: saved sequences in series ---
// User 2026-09-17: mix and match sequences (greeting, then byebye). A show is a
// list of sequence NAMES saved by the hub in shows/*.json (main_python/shows.py);
// the hub plays it as one run, so it works over WiFi or the cable.
let showDraft = { name: "", loop: false, items: [] };

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
    hold.title = "pause after this sequence, in ms";
    hold.onchange = () => { it.hold = Math.max(0, +hold.value || 0); };
    const btn = (label, title, fn) => { const b = document.createElement("button"); b.textContent = label; b.title = title; b.onclick = fn; return b; };
    row.append(n, name, document.createTextNode("pause"), hold,
      btn("▲", "play earlier", () => moveShowItem(i, -1)),
      btn("▼", "play later", () => moveShowItem(i, 1)),
      btn("✕", "take out of this show", () => { showDraft.items.splice(i, 1); renderShow(); }));
    box.appendChild(row);
  });
}
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
