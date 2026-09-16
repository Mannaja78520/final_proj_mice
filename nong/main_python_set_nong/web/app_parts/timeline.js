// --- timeline ---
function addKey() {
  clearBadMarks(); // poses changed: collision marks are stale until re-checked
  const k = { pose: [...pose], t: 1000, hold: 0 };
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
  if (selKey >= 1) keys[selKey].t = autoTime(keys[selKey - 1].pose, keys[selKey].pose, keyDps(selKey));
  if (keys[selKey + 1]) keys[selKey + 1].t = autoTime(keys[selKey].pose, keys[selKey + 1].pose, keyDps(selKey + 1));
  clampKeyTimes();
  renderTimeline();
}
function dupKey() {
  if (!keys[selKey]) return;
  clearBadMarks();
  keys.splice(selKey + 1, 0, JSON.parse(JSON.stringify(keys[selKey])));
  bumpKeys();
  selKey++;
  // The copy keeps its source's time, which makes it a HOLD of that length:
  // the move into the copy covers zero distance (same pose as the keyframe
  // before it). No predecessor pose changed anywhere else on the line, so no
  // other time moves — recalcTimes() here used to wipe every hand-typed one.
  clampKeyTimes(); renderTimeline();
}
function delKey() {
  if (keys.length <= 1 || !keys[selKey]) return;
  clearBadMarks();
  const gone = selKey;
  keys.splice(selKey, 1);
  bumpKeys();
  selKey = Math.max(0, selKey - 1);
  // Only the keyframe that FOLLOWED the deleted one starts from a different
  // pose now; every hand-typed time further down must survive.
  retimeAt(gone); renderTimeline(); selectKey(selKey);
}
function moveKey(d) {
  const i = selKey, j = i + d;
  if (!keys[i] || !keys[j]) return;
  clearBadMarks();
  [keys[i], keys[j]] = [keys[j], keys[i]];
  bumpKeys();
  selKey = j;
  // Both swapped keyframes changed what they travel FROM, and so did the
  // keyframe AFTER them (it now follows the other of the pair).
  const last = Math.max(i, j);
  retimeAt(i); retimeAt(j);
  if (keys[last + 1]) retimeAt(last + 1);
  renderTimeline();
}
// How long the move INTO keyframe i takes, as the show would run it. Reads
// the played timeline, so a keyframe that follows a suspended one gets the
// re-timed value rather than the number stored against it.
function keyTravelMs(i) {
  const K = playKeys();
  const at = K.findIndex(k => k.src === i);
  if (at > 0) return K[at].t;                 // its move, as played
  if (at === 0) return 0;                     // the start pose: nowhere to come from
  return keys[i] ? keys[i].t : 0;             // suspended: fall back to its own
}
// Where the show's clock sits when the move INTO keyframe i begins — the same
// walk totalMs() makes over the PLAYED list, holds counted. Selecting a
// keyframe parks the clock here, so Play carries on from the move on screen.
// A suspended keyframe has no move of its own: the show jumps the gap, so the
// clock lands where that jump begins (end of the show if none follows).
function keyStartMs(i) {
  const K = playKeys();
  let at = K.findIndex(k => k.src === i);
  if (at < 0) {
    at = K.findIndex(k => k.src > i);
    if (at < 0) return totalMs();
  }
  if (at <= 0) return 0;
  let t = K[0].hold || 0;
  for (let j = 1; j < at; j++) t += K[j].t + (K[j].hold || 0);
  return t;
}

// Which PLAYED keyframe the clock at `ms` is standing on — keyStartMs() run
// backwards, and the same walk main.py's _play_once makes when the hub resumes
// a show. Inside a move: that move is the one to run. Inside a hold: the next
// one. The answer is an index into playKeys(), never into keys[].
function keyIndexAtMs(ms) {
  const K = playKeys();
  if (K.length < 2) return 0;
  let clock = K[0].hold || 0;
  if (ms <= clock) return 0;
  for (let i = 1; i < K.length; i++) {
    clock += K[i].t;
    if (ms < clock) return i;                       // part-way through its move
    clock += K[i].hold || 0;
    if (ms < clock) return Math.min(i + 1, K.length - 1);   // in its hold
  }
  return K.length - 1;
}

// CLICKING A MOVE WHILE IT PLAYS (user 2026-09-16): the clock was parked at
// the START of that move and play kept running, so the show went back to the
// pose before it and replayed the move - a sudden servo swing that can break
// the robot. Now: stop every clock, travel from where the arm IS to the
// clicked pose at the show's speed, park the clock where that pose is
// reached, and carry on from there once the arm has arrived.
let seekToken = 0;
function selectKey(i) {
  const was = playing;
  const token = ++seekToken;
  if (was) {
    playing = false; $("playBtn").textContent = "▶ Play";
    livePause(); stopRobotSequence(); keepAwake(false);
  }
  selKey = i;
  let travel = 0;
  if (keys[i]) {
    const from = pose.slice();
    pose = [...keys[i].pose];
    // the move's own speed, and never faster than the show's speed allows
    // from where the arm stands now - the start pose has no move of its own
    travel = Math.max(keyTravelMs(i), autoTime(from, pose, keyDps(i)));
    poseChanged(false, travel);
  }
  // the clock follows the click: stopped, Play replays this move; playing,
  // the show continues AFTER it, since the arm is travelling there already
  playT = was ? keyStartMs(i) + keyTravelMs(i) : keyStartMs(i);
  if (was) setTimeout(() => {
    if (token === seekToken && !playing) togglePlay();
  }, travel);
  const total = totalMs();
  $("scrub").value = total ? Math.round(playT / total * 1000) : 0;
  renderTimeline();
}
function totalMs() {
  const K = playKeys();
  let t = 0;
  for (let i = 1; i < K.length; i++) t += K[i].t + (K[i].hold || 0);
  t += K.length ? (K[0].hold || 0) : 0;
  return t;
}
function renderTimeline() {
  const box = $("keys");
  $("timelineEmpty").hidden = keys.length > 0;
  box.innerHTML = "";
  keys.forEach((k, i) => {
    const el = document.createElement("div");
    el.className = "key" + (i === selKey ? " sel" : "") + (k.off ? " off" : "");
    el.onclick = (e) => {
      if (e.target.tagName !== "INPUT" && e.target.tagName !== "BUTTON") selectKey(i);
    };
    // Clicking anywhere on the chip selects it, which is worth keeping for a
    // mouse - so the chip names the control that does the same job for the
    // keyboard. check_keyboard_only reads this: a clickable box that cannot
    // point at its own keyboard equivalent is counted as mouse-only.
    el.setAttribute("data-keyboard", ".kgo");
    const bar = document.createElement("div"); bar.className = "kbar";
    const idx = document.createElement("div"); idx.className = "kidx";
    // Number, then a name you can type. A timeline of "0 1 2 3 4 5" tells you
    // nothing about what the show does; "wave", "reach cup", "bow" does. The
    // number stays because it is what every message and error refers to.
    //
    // The number is a real BUTTON, not text: selecting a keyframe used to be
    // possible only by clicking the chip, so with a keyboard alone the
    // timeline could not be moved through at all (A9-3b, measured 2026-08-21).
    // Gemini Pro chose this over making the chip itself tabbable, because the
    // chip contains a text field and two number fields - a control that
    // contains controls is wrong for a screen reader and takes the focus its
    // own fields need.
    const go = document.createElement("button");
    go.className = "kgo";
    go.textContent = String(i);
    go.title = "go to move " + i + " and show that pose";
    go.setAttribute("aria-label", "go to move " + i + (k.name ? ": " + k.name : ""));
    go.setAttribute("aria-pressed", i === selKey ? "true" : "false");
    go.onclick = (e) => { e.stopPropagation(); selectKey(i); };
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
    nm.title = "what this move is, in your words. Saved with the project and "
             + "written into the exported file as a comment.";
    nm.onclick = (e) => e.stopPropagation();      // typing must not re-select
    nm.onchange = () => {
      const v = nm.value.trim();
      if (v) k.name = v; else delete k.name;
      bumpKeys();
      renderTimeline();
    };
    idx.appendChild(nm);
    // Suspend: keep the keyframe but leave it out of the run. For trying a
    // move without deleting the rest, and it never reaches the robot or the
    // exported file until you switch it back on.
    const sk = document.createElement("button");
    sk.className = "kskip";
    sk.textContent = k.off ? "○" : "●";
    sk.title = k.off ? "suspended — click to put this keyframe back in the run"
                     : "suspend: skip this keyframe when playing, exporting and uploading";
    sk.onclick = (e) => {
      e.stopPropagation();
      k.off = !k.off;
      bumpKeys();
      clearBadMarks();          // the moves either side of it just changed
      playT = 0;
      renderTimeline();
      $("tlStat").textContent = anySuspended()
        ? keys.filter(x => x.off).length + " keyframe(s) suspended — they are skipped " +
          "when playing, exporting and uploading"
        : "all keyframes active";
    };
    idx.appendChild(sk);
    const pv = document.createElement("div"); pv.className = "kpose";
    pv.textContent = k.pose.map(a => Math.round(a)).join(" ");
    const kmin = keyMin(i);
    const tr = document.createElement("div"); tr.className = "ktime";
    const tIn = document.createElement("input");
    tIn.type = "number"; tIn.value = k.t; tIn.min = kmin; tIn.step = 50;
    tIn.title = (i === 0 ? "entry time from wherever the robot is (ms)"
                         : "time from previous keyframe (ms)")
              + ` — minimum ${kmin} ms (servo max speed); longer is always allowed`;
    tIn.onchange = () => {
      const want = Math.round(+tIn.value || 0);
      k.t = Math.max(kmin, want);
      delete k.dps;
      bumpKeys();             // a typed time wins over a speed override
      if (want < kmin)
        $("tlStat").textContent = `time raised to ${kmin} ms — the servos can't move that far faster (slowest joint on this move: ${slowestDps()} °/s)`;
      renderTimeline();
    };
    // A move that follows a SUSPENDED keyframe no longer starts where its
    // stored time was written for — it begins from an earlier pose, covers
    // more ground, and is re-timed for real in buildPlayKeys(). The box kept
    // showing the number you typed while the move actually took longer, so
    // the timeline and the robot disagreed with no way to see why. Say what
    // it really runs at, without touching what you set.
    let reNote = null;
    const eff = playKeys().find(x => x.src === i);
    if (eff && Math.round(eff.t) !== Math.round(k.t)) {
      const re = document.createElement("span");
      re.className = "statline";
      re.style.marginLeft = "6px";
      re.textContent = "runs " + Math.round(eff.t) + "ms";
      re.title = "a keyframe before this one is suspended, so this move runs "
               + "between different poses and is re-timed. Your "
               + Math.round(k.t) + " ms comes back when you un-suspend.";
      reNote = re;
    }

    const hIn = document.createElement("input");
    hIn.type = "number"; hIn.value = k.hold || 0; hIn.min = 0; hIn.step = 100;
    hIn.title = "hold this pose (ms) before the next move";
    hIn.onchange = () => { k.hold = Math.max(0, Math.round(+hIn.value || 0)); bumpKeys(); renderTimeline(); };
    tr.append(document.createTextNode("T"), tIn, document.createTextNode("hold"), hIn);
    if (reNote) tr.appendChild(reNote);
    const mn = document.createElement("div");
    mn.className = "ktime";
    if (i === 0) {
      mn.textContent = "min " + kmin + " ms";
    } else {
      // this move's own speed: blank = run at the sequence's speed
      const dIn = document.createElement("input");
      dIn.type = "number"; dIn.min = 5; dIn.max = 600; dIn.step = 5;
      dIn.className = "kdps";
      dIn.value = k.dps ? Math.round(k.dps) : "";
      dIn.placeholder = Math.round(speedDps());
      dIn.title = "this move's own speed (°/s). Empty = the sequence's " +
                  Math.round(speedDps()) + " °/s. Setting it re-times this move; " +
                  "typing a time above clears it again.";
      dIn.onchange = () => {
        const v = Math.round(+dIn.value || 0);
        if (v >= 5) { k.dps = Math.min(v, slowestDps()); k.t = autoTime(keys[i - 1].pose, k.pose, k.dps); }
        else { delete k.dps; k.t = autoTime(keys[i - 1].pose, k.pose, speedDps()); }
        bumpKeys();
        renderTimeline();
      };
      mn.append(document.createTextNode("min " + kmin + " · "), dIn,
                document.createTextNode("°/s"));
    }
    // ♪ lives on the existing speed line rather than in a row of its own:
    // most moves never carry music, and a row per keyframe for a rare thing
    // is how a timeline stops fitting on a laptop.
    const mus = document.createElement("button");
    mus.type = "button";
    mus.className = "kmus" + (keyCue(k, "play") ? " on" : "");
    mus.textContent = "♪";
    mus.setAttribute("aria-pressed", musOpen.has(i) ? "true" : "false");
    mus.title = keyCue(k, "play")
      ? "plays " + cueTrack(k) + (cueLoop(k) ? " on repeat" : "") + " from here"
      : "give this move a track from the robot's card";
    mus.onclick = () => {
      if (musOpen.has(i)) musOpen.delete(i); else musOpen.add(i);
      loadMusicList();
      renderTimeline();
    };
    mn.appendChild(mus);
    el.append(bar, idx, pv, tr, mn);
    if (musOpen.has(i) || keyCue(k, "play")) el.append(musicRow(k, i));
    if (k.bad) { // collision found by checkCollisions(): mark the chip red
      el.classList.add("bad");
      const b = document.createElement("div");
      b.className = "kbad";
      b.textContent = "⚠ " + k.bad;
      el.append(b);
    }
    box.appendChild(el);
  });
  $("tlTime").textContent = (playT / 1000).toFixed(1) + "s / " + (totalMs() / 1000).toFixed(1) + "s";
  renderTimeBar();
}

// The blocks and ruler under the time bar: a picture of the show, drawn from the
// SAME numbers playback uses (keyStartMs / keyTravelMs / totalMs), so the bar
// cannot disagree with what the robot does.
//
// Called from renderTimeline() only — never per frame. renderTimeline() rebuilds
// every chip with innerHTML="", so driving a playhead through it would do that
// sixty times a second; the playhead is the range's own thumb and moves by
// value alone (see playTick).
let tlZoom = 1;
function zoomTimeline(factor) {
  tlZoom = Math.max(0.5, Math.min(10, tlZoom * factor));
  const tr = $("tbTrack");
  const ru = $("tbRuler");
  if (tr) tr.style.width = (tlZoom * 100) + "%";
  if (ru) ru.style.width = (tlZoom * 100) + "%";
  renderTimeBar();
}

function renderTimeBar() {
  const box = $("tbBlocks"), ruler = $("tbRuler");
  if (!box) return;                      // an older page without the bar
  box.innerHTML = "";
  const K = playKeys(), total = totalMs();
  if (!total || K.length < 2) {
    const empty = document.createElement("div");
    empty.className = "tb-blk";
    empty.style.left = "0"; empty.style.width = "100%";
    empty.textContent = K.length < 2 ? "add a second pose to make a movement"
                                     : "these poses are all the same";
    box.appendChild(empty);
    if (ruler) ruler.innerHTML = "";
    return;
  }
  const pct = ms => (ms / total * 100) + "%";
  // keyframe 0 has no move to arrive by, so only its hold occupies the start —
  // the same reason totalMs() counts K[0].hold but not K[0].t.
  const band = (left, width, cls, label, title) => {
    if (width <= 0) return;
    const d = document.createElement("div");
    d.className = "tb-blk" + (cls ? " " + cls : "");
    d.style.left = pct(left); d.style.width = pct(width);
    if (label && width / total > 0.06) d.textContent = label;
    d.title = title;
    box.appendChild(d);
  };
  if (K[0].hold) band(0, K[0].hold, "hold", "wait",
                      "waits " + (K[0].hold / 1000).toFixed(1) + "s before starting");
  for (let i = 1; i < K.length; i++) {
    const src = K[i].src, k = keys[src] || K[i];
    const start = keyStartMs(src), dur = keyTravelMs(src);
    const name = k.name || String(src);
    band(start, dur, (src === selKey ? "sel" : "") + (k.bad ? " bad" : ""), name,
         "move " + src + (k.name ? " (" + k.name + ")" : "") +
         " takes " + (dur / 1000).toFixed(1) + "s");
    if (K[i].hold) band(start + dur, K[i].hold, "hold", "wait",
                        "then waits " + (K[i].hold / 1000).toFixed(1) + "s");
  }
  if (!ruler) return;
  // Ticks in real seconds. The count comes from the bar's own width so a phone
  // gets two labels and a desktop gets eight, instead of a crowded smear.
  ruler.innerHTML = "";
  const w = ruler.getBoundingClientRect().width || 600;
  const steps = Math.max(2, Math.min(8, Math.floor(w / 90)));
  for (let s = 0; s <= steps; s++) {
    const t = total * s / steps;
    const tick = document.createElement("span");
    tick.className = "tb-tick" + (s === 0 ? " first" : s === steps ? " last" : "");
    tick.style.left = pct(t);
    tick.textContent = (t / 1000).toFixed(t < 10000 ? 1 : 0) + "s";
    ruler.appendChild(tick);
  }
}

// Back to start. Goes through scrubTo() rather than setting playT, because
// scrubTo is where the ONE-PLAYER discipline lives: it pauses the preview, ends
// the module's own sequence and lets the tab idle. Setting playT directly would
// leave the robot running its copy of the show from the old position.
function rewind() {
  scrubTo(0);
  $("scrub").value = 0;
  _lastScrub = 0;
  $("tlStat").textContent = "back at the start — press Play to run the whole show";
}

// ------- the timeline AS IT PLAYS
// `keys` is the edit list — everything you see in the timeline, including the
// keyframes you have suspended. This is what actually runs: suspended
// keyframes dropped, and the move time into each survivor raised when skipping
// made the jump bigger than its stored time allowed for (suspend the middle of
// 1-2-3 and the move 1->3 is longer than the one 2->3 was timed for).
// `src` maps back to the edit list so warnings land on the right chip.
// Everything about playback, export and collision checking reads THIS.
// tick() asks for the play list up to four times a frame (poseAt, segmentAt,
// segRemaining, the live-follow send). Rebuilding it each time re-runs minTime
// over every joint of every keyframe, so it is cached and thrown away whenever
// the timeline changes. bumpKeys() is the ONE way to invalidate it — anything
// that edits `keys` must call it, or the editor shows a stale run.
// A hand-invalidated cache goes stale silently — one forgotten call and the
// editor shows a run the robot will not perform. So the cache validates itself
// against a cheap signature of exactly the fields buildPlayKeys() reads.
// Reading five numbers per keyframe is far cheaper than re-running minTime over
// ten joints per keyframe, and it CANNOT be wrong: change anything that matters
// and the signature changes with it.
let _pkCache = null;
function keysSignature() {
  let s = keys.length + "|" + speedDps();
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    s += ";" + (k.name || "") + "," + (k.off ? 1 : 0) + "," + k.t + "," + (k.hold || 0) + "," +
         (k.dps || 0) + "," + k.pose + "," + (k.cues || []).join("|") + "," +
         (k.cuesAfter || []).join("|");
  }
  return s;
}
function bumpKeys() {
  // the timeline changed: a "yes, run it anyway" given for the old one does
  // not carry over to this
  crashForced = false;
  _pkCache = null;                          // kept for explicit invalidation
  saveDraft();                              // and it is no longer only in RAM
}

// ---- the timeline survives the tab closing -------------------------------
//
// `keys` lived ONLY in memory until someone pressed Save. F5, Ctrl+W, a closed
// lid, or this GPU-heavy three.js page losing its tab took every keyframe with
// it, with no copy anywhere. Hours of posing, gone to a mis-hit key.
//
// The draft is deliberately its OWN localStorage key, never a project file: it
// can therefore never overwrite something the user deliberately saved. It is
// offered back on the next load, and the user chooses.
const DRAFT_KEY = "nong_timeline_draft";
let draftTimer = null;
// Boot builds keyframe 0 itself, and that is not work anybody would mourn.
// Without this the page saved a draft of the untouched default the moment it
// opened, and then warned about "unsaved work" on every single close.
let draftArmed = false;
function saveDraft() {
  if (!draftArmed) return;
  clearTimeout(draftTimer);                 // coalesce a drag into one write
  draftTimer = setTimeout(() => {
    try {
      if (keys.length <= 1) { localStorage.removeItem(DRAFT_KEY); return; }
      localStorage.setItem(DRAFT_KEY, JSON.stringify({
        at: Date.now(),
        name: ($("projName") && $("projName").value) || "",
        seq: ($("seqName") && $("seqName").value) || "",
        keys: keys,
      }));
    } catch (e) {
      // storage full or blocked: the draft is a safety net, never a blocker
    }
  }, 400);
}
function offerDraft() {
  let d = null;
  try { d = JSON.parse(localStorage.getItem(DRAFT_KEY) || "null"); }
  catch (e) { d = null; }
  if (!d || !Array.isArray(d.keys) || d.keys.length <= 1) return;
  if (keys.length > 1) return;              // real work is already on screen
  const when = new Date(d.at || Date.now()).toLocaleString();
  const st = $("tlStat");
  if (st) {
    st.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "There is unsaved work from " + when
      + " (" + d.keys.length + " keyframes). ";
    const yes = document.createElement("button");
    yes.textContent = "Restore it";
    yes.onclick = () => {
      keys = d.keys;
      if (d.name && $("projName")) $("projName").value = d.name;
      if (d.seq && $("seqName")) $("seqName").value = d.seq;
      selKey = 0;
      if (keys.length) pose = [...keys[0].pose];
      bumpKeys(); poseChanged(false); renderTimeline(); renderSliders();
      st.textContent = "Restored the unsaved timeline. Save it to keep it.";
    };
    const no = document.createElement("button");
    no.textContent = "Discard";
    no.onclick = () => {
      try { localStorage.removeItem(DRAFT_KEY); } catch (e) { /* nothing to do */ }
      st.textContent = "";
    };
    st.append(msg, yes, document.createTextNode(" "), no);
  }
}
// Closing with unsaved keyframes asks first. The browser shows its own wording;
// all a page can do is say that there IS something to lose.
window.addEventListener("beforeunload", (e) => {
  if (keys.length <= 1) return;
  let unsaved = false;
  try { unsaved = !!localStorage.getItem(DRAFT_KEY); } catch (err) { unsaved = false; }
  if (!unsaved) return;                     // saveProject() cleared it
  e.preventDefault();
  e.returnValue = "";
});
function playKeys() {
  const sig = keysSignature();
  if (_pkCache && _pkCache.sig === sig) return _pkCache.list;
  const list = buildPlayKeys();
  _pkCache = { sig, list };
  return list;
}
function buildPlayKeys() {
  const out = [];
  let gap = false;                 // was anything suspended since the last one?
  // Cues from suspended keyframes move to the next one that plays: suspending
  // a move must not silently delete the show's music from the exported file.
  let carry = [];
  keys.forEach((k, i) => {
    if (k.off) {
      gap = true;
      carry = carry.concat(k.cues || [], k.cuesAfter || []);
      return;
    }
    const prev = out.length ? out[out.length - 1] : null;
    let t = k.t;
    if (prev && gap) {
      // This move is NOT the one its stored time was written for. With the
      // keyframe before it suspended it now runs between DIFFERENT poses, so
      // the stored number no longer describes anything real — it belongs to a
      // move that is not in the sequence any more.
      //
      // Re-time it at the SPEED that applies (this keyframe's own °/s, else
      // the sequence's). autoTime already floors the result at MIN_MOVE_MS
      // and at the per-joint physical limit, so this can never become a
      // full-speed lunge.
      //
      // It must NOT be max()'d with the stored time. Suspend the middle of
      // home -> somewhere -> home and the remaining move is home -> home:
      // it needs the minimum, but max() held it at the old 400 ms and the arm
      // sat still for 400 ms going nowhere. Re-timing has to be able to
      // shorten a move as well as lengthen it.
      t = autoTime(prev.pose, k.pose, k.dps || speedDps());
    }
    // The name travels with the PLAYED move. buildYaml() writes from this
    // list, so a name left behind here never reaches the exported file.
    out.push({ pose: k.pose, hold: k.hold || 0, src: i, dps: k.dps || 0, t,
               name: k.name || "",
               // cues travel with the PLAYED move, like the name above: both
               // buildYaml and hubShowSteps read this list, so a cue left
               // behind here reaches neither the file nor the robot
               cues: carry.concat(k.cues || []),
               cuesAfter: (k.cuesAfter || []).slice() });
    carry = [];
    gap = false;
  });
  if (carry.length && out.length)
    out[out.length - 1].cuesAfter = out[out.length - 1].cuesAfter.concat(carry);
  return out;
}
function anySuspended() { return keys.some(k => k.off); }

// ------- playback preview (cosine ease per segment — same as the firmware)
function poseAt(ms) {
  const K = playKeys();
  if (!K.length) return pose;
  let t = K[0].hold || 0;
  if (ms <= t) return [...K[0].pose];
  for (let i = 1; i < K.length; i++) {
    const seg = K[i].t;
    if (ms < t + seg) {
      const f = 0.5 - 0.5 * Math.cos(Math.PI * (ms - t) / seg);
      return K[i - 1].pose.map((a, j) => a + (K[i].pose[j] - a) * f);
    }
    t += seg + (K[i].hold || 0);
    if (ms < t) return [...K[i].pose];
  }
  return [...K[K.length - 1].pose];
}
// Which MOVE is running at ms, or -1 when nothing is moving. The phases mirror
// poseAt() exactly: hold at keyframe 0, move into 1, hold at 1, move into 2 …
// The "in a hold" branch is what makes a hold real on the robot — without it
// this fell through to the NEXT segment the instant a hold began, so the arm
// started its next move immediately, finished early and stood still for the
// rest of the timeline. The pause then looked like it happened at the END
// instead of between the moves.
function segmentAt(ms) {
  const K = playKeys();
  let t = K.length ? (K[0].hold || 0) : 0;
  if (ms <= t) return -1;                      // holding on keyframe 0
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return i;             // moving into keyframe i
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return -1;                     // holding on keyframe i
  }
  return -1;
}
// ---- keeping playback alive when the tab is not in front -------------
// YouTube keeps going in a background tab because a <video> decodes on the
// browser's own media pipeline. Our playback is JavaScript: requestAnimationFrame
// STOPS in a hidden tab and timers are throttled to about once a minute, so a
// live-driven show freezes the moment you click away.
//
// Chrome exempts a page that is PLAYING AUDIO from that throttling, so we hold a
// silent looping track while a sequence is playing, and drive the live sends
// from a timer rather than from the animation frame. That gets browser-driven
// playback most of the way to YouTube behaviour.
//
// It is still best-effort — a browser may throttle anyway, and a phone that
// sleeps will stop regardless. For a SHOW, send the sequence to the robot and
// press Run: the module then plays it from its own clock and the browser can be
// closed entirely. That path is not just more robust, it is more accurate.
// One tick may never advance the show by more than a few frames — see
// playTick(). 120ms is a very slow frame; anything longer is a gap the
// browser took away from us, not time the robot actually spent moving.
const MAX_TICK_MS = 120;
let keepAwakeEl = null, playClock = null;   // NOT liveTimer - that name is already taken by the collision throttle
function keepAwake(on) {
  try {
    if (on) {
      if (!keepAwakeEl) {
        // a one-sample silent wav, inline — no file, no network
        keepAwakeEl = new Audio(
          "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=");
        keepAwakeEl.loop = true;
        keepAwakeEl.volume = 0.0001;   // silent, but genuinely "playing"
      }
      keepAwakeEl.play().catch(() => {});   // blocked before a click: fine
      if (!playClock) playClock = setInterval(playTick, 60);
    } else {
      if (keepAwakeEl) keepAwakeEl.pause();
      if (playClock) { clearInterval(playClock); playClock = null; }
    }
  } catch (e) { /* never let this break playback */ }
}

function togglePlay() {
  const K = playKeys();
  if (K.length < 2) {
    $("tlStat").textContent = keys.length >= 2
      ? "only " + K.length + " keyframe(s) are active — un-suspend some to play"
      : "add at least 2 keyframes to play";
    return;
  }
  // A crashing movement may always be PREVIEWED — watching where it goes wrong
  // is how you fix it. Whether it also reaches the robot is a separate
  // question, and it is asked only when something is actually connected.
  if (!playing) {
    previewOnly = false;
    if (checkCollisions(false).length && (liveLinked() || hubDriven())) {
      previewOnly = !crashGate("PLAY it on the robot");
      if (previewOnly) {
        const st = $("tlStat");
        if (st) st.textContent = "playing the PREVIEW only — the robot is not "
          + "being driven, because this movement crashes";
      }
    }
  }
  playing = !playing;
  $("playBtn").textContent = playing ? "❚❚ Pause" : "▶ Play";
  lastFrame = performance.now();
  lastPlayMs = 0;                 // fresh clock, so a pause never leaps forward
  keepAwake(playing);             // keep the tab off the throttling list
  lastLiveSeg = -1;
  if (playing && playT >= totalMs()) playT = 0;

  // THERE IS ONLY EVER ONE PLAYER.
  //
  // The module keeps a sequence in memory and plays it on its own clock — that
  // is what makes a show survive this page being closed. But it means the
  // module can still be running when you come back, and if this preview then
  // starts streaming poses too, BOTH are driving the same servos: the arm
  // fights itself, and Stop here only stopped the browser, so the module
  // carried on moving on its own.
  //
  // So: taking control here always stops the module first, and giving up
  // control always stops the module too. Never two clocks on one robot.
  stopRobotSequence();
  if (!playing) { livePause(); return; }
  // The HUB plays it when the link goes through the hub: a native process,
  // never throttled, so the show survives this page being hidden or closed —
  // which is the whole reason it exists. This preview keeps drawing, and sends
  // nothing (playTick skips its live sends while hubDriven()).
  if (previewOnly) return;          // refused at the crash gate: draw only
  if (hubDriven()) { hubPlay(playT); return; }
  // A segment is the move INTO a keyframe, so segmentAt() starts at 1 and
  // keyframe 0 is never one of them. Put the robot on it first, or its first
  // move starts from wherever it happens to be standing instead of from the
  // start of the timeline. T is only a request: the firmware floors it per
  // joint, so a short one is stretched to what the servos can really do.
  if (playT === 0 && K.length && liveLinked())
    liveSend("POSE " + K[0].pose.map(fmtA).join(" ") +
             " T " + minTime(pose, K[0].pose));
}
// A segment is handed to the module as one whole move (POSE ... T <ms>) and
// the firmware interpolates it on its own — that is what keeps the motion
// smooth and lets linked boards stay in step. So pausing the editor does NOT
// stop the robot by itself: the module is already carrying out the move and
// runs it to the end. STOP freezes it at the pose it has reached right now.
//
// STOP is a MOTION command, so the firmware also ends any sequence the module
// was playing on its own clock (config/commands.json `"motion": true`). That
// matters here: Pause used to stop only the browser, and a module that was
// mid-show carried on moving — the thing that looked like two shows running
// over each other, because it was.
function liveLinked() {
  return $("liveChk").checked && (haveUsb() || haveWifi());
}
// ---- who holds the clock -------------------------------------------------
//
// THREE CLOCKS, and only one of them may run at a time:
//
//   the module   Run on robot (MOVE)   survives the PC being switched off
//   THE HUB      python main.py        survives this page being closed
//   this browser rAF preview           survives nothing
//
// A hidden tab has rAF stopped and its timers throttled to about once a
// minute — browser policy, not something JavaScript can opt out of. So while a
// link goes THROUGH the hub, the hub plays the show and this page only draws
// it. Web Serial (USB direct) is the exception: the browser holds the port
// itself, so the hub cannot reach the robot and the old browser clock stands.
function hubDriven() {
  return liveLinked() && !usbDirect();
}
// What the hub is asked to play: the same keyframes this preview runs, with
// the same times. `t` on the first one is how long the robot may take to reach
// the start pose from wherever it is standing.
function hubShowSteps() {
  const K = playKeys();
  if (K.length < 2) return null;
  return K.map((k, i) => ({
    pose: k.pose.map(v => +fmtA(v)),
    t: i === 0 ? minTime(pose, K[0].pose) : k.t,
    hold: k.hold || 0,
    // the hub decides which cue is a command it may send (main.py cue_lines),
    // so the editor passes the file's own words straight through
    cues: k.cues || [],
    cues_after: k.cuesAfter || [],
  }));
}
async function hubPlay(fromMs) {
  const steps = hubShowSteps();
  if (!steps) return false;
  try {
    const r = await fetch("/api/play", {
      method: "POST",
      body: JSON.stringify({
        dev: moduleDev(), steps, loop: $("loopChk").checked,
        name: ($("seqName").value || "sequence").trim(), from_ms: Math.round(fromMs || 0),
      }),
    }).then(r => r.json());
    if (r.error) throw new Error(r.error);
    $("robotStat").textContent =
      "the HUB is playing this — it keeps going with this page closed or hidden. " +
      "Pause or Stop here ends it.";
    return true;
  } catch (e) {
    $("robotStat").textContent = "The hub could not start the show, so the robot "
      + "did not move. Check the hub is still running, then press Play again. "
      + (e.message || e);
    notice($("robotStat").textContent);
    return false;
  }
}
function hubStop() {
  return fetch("/api/play/stop", { method: "POST" }).catch(() => {});
}
function livePause() {
  // Stop the HUB's clock FIRST, whatever the link state: a show started while
  // Live was unticked is hub-driven, and an early return here left that clock
  // running — Pause stopped the drawing but the robot carried on.
  hubStop();
  if (!liveLinked()) return;
  liveAbort();        // drop moves not yet sent — pausing cancels them
  liveSend("STOP");
  lastLiveSeg = -1;   // resume re-sends the segment, with the time still left
}
// ms left in the segment playT is inside — what a resume must ask for, or the
// robot would replay the whole segment while the editor plays only its tail.
function segRemaining(ms) {
  const K = playKeys();
  let t = K.length ? (K[0].hold || 0) : 0;
  if (ms <= t) return 0;
  for (let i = 1; i < K.length; i++) {
    if (ms < t + K[i].t) return Math.max(1, Math.round(t + K[i].t - ms));
    t += K[i].t + (K[i].hold || 0);
    if (ms < t) return 0;                      // in a hold, nothing is running
  }
  return 0;
}
function scrubTo(v) {
  const was = playing;
  ++seekToken;                       // a scrub cancels a pending resume
  const from = pose.slice();
  playing = false; $("playBtn").textContent = "▶ Play";
  // Every other stop path releases the keep-awake; this one did not, so
  // scrubbing during playback left playClock firing every 60 ms and the silent
  // <audio> element "playing" for the life of the page. Nothing looked wrong —
  // playTick returns immediately while !playing — it just burned CPU and
  // battery forever, and kept the tab permanently exempt from throttling.
  if (was) { livePause(); stopRobotSequence(); keepAwake(false); }
  playT = totalMs() * (+v / 1000);
  pose = poseAt(playT).map((v,i)=>clampJ(i,v));
  applyPose(); renderSliders(); renderTimeline();
  // Take the ARM there too. Scrubbing is how you check a move without playing
  // the whole show - a preview that moves while the robot stays put is the one
  // thing you cannot check against. Uses the same path a slider drag does, so
  // it carries the link's own round-trip timing rather than letting the module
  // ease at its SPEED setting.
  // A JUMP along the bar is not a drag: sent at drag time (80-300 ms) the arm
  // swung across at full servo speed. Anything slower than a drag goes at
  // the show's speed from where the arm is (2026-09-16).
  if (liveLinked()) {
    const safe = autoTime(from, pose, speedDps());
    if (safe > LIVE_T_MAX) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + safe);
    else sendPoseLive();
  }
}
