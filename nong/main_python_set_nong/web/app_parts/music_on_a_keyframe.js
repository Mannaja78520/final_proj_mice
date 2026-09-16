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
    if (!liveLinked()) throw new Error("offline");
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
async function pickMusicFile(k) {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = ".mp3,.wav,audio/mpeg,audio/wav";
  inp.onchange = () => {
    const f = inp.files && inp.files[0];
    if (f) uploadMusicFile(k, f);
  };
  inp.click();
}
// The upload itself, given a file: separate from the dialog because a file
// picker cannot be opened by a script, and an upload path no check can reach
// is an upload path nothing guards.
async function uploadMusicFile(k, f) {
  if (usbDirect()) {
    musicNote = "this browser is holding the cable itself, so the hub cannot "
              + "send the file. Connect through the hub, or add the track on "
              + "the module website: Files ▸ /music.";
    renderTimeline();
    return;
  }
  musicNote = "sending " + f.name + " to the robot…";
  renderTimeline();
  try {
    const r = await fetch("/api/dev/upload?dir=/music&name="
                          + encodeURIComponent(f.name) + "&dev="
                          + encodeURIComponent(moduleDev()),
                          { method: "POST", body: await f.arrayBuffer() });
    const said = (await r.text()).trim();
    if (!said.startsWith("OK")) throw new Error(said);
    musicList = null;                   // the card has one more file on it now
    await loadMusicList();
    setKeyCue(k, "play", f.name);
    musicNote = f.name + " is on the robot's card — press ▶ to hear it";
  } catch (e) {
    musicNote = "the track did not reach the robot: " + (e.message || e);
  }
  renderTimeline();
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
  play.disabled = !cur || !liveLinked();
  play.title = !liveLinked() ? "connect the robot to hear it"
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
  stop.disabled = !liveLinked();
  stop.title = "stop the sound";
  stop.onclick = async () => {
    try { musicNote = await rawCmd("PLAY STOP"); } catch (e) { musicNote = String(e.message || e); }
    renderTimeline();
  };
  const add = document.createElement("button");
  add.type = "button"; add.className = "kmusbtn"; add.textContent = "＋";
  add.disabled = !liveLinked();
  add.title = liveLinked() ? "put a track from this PC onto the robot's card"
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
  for (const raw of text.split(/\r?\n/)) {
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
        // a speed step before this pose that differs from the sequence speed is
        // that MOVE's own speed, so it survives a round trip through the file
        if (curSpeed && curSpeed !== out.speed) k.dps = curSpeed;
        if (pend.length) { k.cues = pend; out.cues += pend.length; pend = []; }
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
  if (p.name) { $("seqName").value = p.name; $("projName").value = p.name; }
  selKey = 0;
  pose = [...keys[0].pose];
  poseChanged(false);
  renderTimeline();
  $("tlStat").textContent = `loaded ${keys.length} keyframes from ${sourceLabel}` +
    (p.speed >= 5 ? ` at its own ${Math.round(p.speed)} °/s` : "") +
    (p.cues ? ` with ${p.cues} music/light step(s), which play with the show and are written back on export` : "") +
    (p.skipped ? ` (${p.skipped} step(s) this editor does not read — kept only in the original file)` : "") +
    " — edit, then Export / Upload again";
}
async function editLocalSeq() {
  const f = $("seqList").value;
  if (!f) return;
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
async function refreshSeqs() {
  const r = await fetch("/api/list?kind=sequences").then(r => r.json());
  const sel = $("seqList");
  sel.innerHTML = "<option value=''>Open saved YAML…</option>";
  (r.files || []).filter(f => f.endsWith(".yaml")).forEach(f => {
    const o = document.createElement("option"); o.value = o.textContent = f; sel.appendChild(o);
  });
}
