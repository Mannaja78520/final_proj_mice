// --- moves while talking (A46-1) ---
// User 2026-10-22: gestures that fit the words, made with the robot's own size
// and shared between the Voice page and Studio. The library is
// config/gestures.json on the hub (plus this PC's own, saved by this card);
// Studio is where the body lives, so Studio FITS it: hand targets -> joint
// angles by IK on this rig, every pose and every move checked by safe_path.js,
// and the result posted to the hub, which only times and plays it. A fit is
// redone when the rig or a gesture changes: when the Sequence tab opens, or
// after the page has been left alone a while (TALK_IDLE_MS).
let TALK = { lib: null, fit: null, busy: false, hub: false };
const TALK_IDLE_MS = 20000;
let talkIdleAt = performance.now();
["pointerdown", "keydown", "wheel"].forEach(e => window.addEventListener(e, () => { talkIdleAt = performance.now(); }, true));

function talkSay(s) { if ($("talkStat")) $("talkStat").textContent = s; }
// The rig as it shapes a gesture: sizes, calibration and limits. A change to
// any of it changes where a hand lands, so it is part of what was fitted.
function talkRigSnap() {
  const r = JSON.parse(JSON.stringify(RIG));
  return { dims: r.dims, zero: r.zero, axis: r.axis, invert: r.invert, offset: r.offset,
           tilt: r.tilt, min: r.min, max: r.max, home: r.home, palmTurn: r.palmTurn };
}
async function talkLoad() {
  try {
    const j = await fetch("/api/gestures").then(r => r.json());
    if (!j.ok) throw new Error(j.error || "no answer");
    TALK.lib = j.lib; TALK.fit = j.fit || {}; TALK.hub = true;
  } catch (e) {
    TALK.hub = false;                 // Studio on its own server: no hub, no card
  }
  talkRender();
  return TALK.hub;
}
function talkStale() {
  const L = TALK.lib, F = TALK.fit || {};
  if (!L) return false;
  if (JSON.stringify(F.rigFull || null) !== JSON.stringify(talkRigSnap())) return true;
  if (JSON.stringify(F.restDef || null) !== JSON.stringify((L.rest || {}).keys || null)) return true;
  const defs = F.defs || {};
  return Object.keys(L.gestures || {}).some(id => JSON.stringify(defs[id] || null) !== JSON.stringify(L.gestures[id].keys || null))
    || Object.keys(defs).some(id => !(L.gestures || {})[id]);
}
// One key of the library -> a pose on this rig. `from` is where the arms come
// from (IK starts there, so a gesture flows), `restArm` holds a hand left out.
function talkKeyPose(k, from, restArm, mirror) {
  const p = from.slice();
  const sideOf = a => (a === 0 ? 1 : -1);
  const tgt = [mirror ? k.R : k.L, mirror ? k.L : k.R];
  const palm = [mirror ? k.palmR : k.palmL, mirror ? k.palmL : k.palmR];
  if (k.pose) return k.pose.map((v, j) => clampJ(j, v));          // a pose made on the time bar
  p[8] = clampJ(8, RIG.home[8] + (mirror ? -1 : 1) * (k.waist || 0));
  p[9] = clampJ(9, RIG.home[9] + (k.shrug || 0));
  for (const a of [0, 1]) {
    const idx = a === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    if (!tgt[a]) { idx.forEach(j => { p[j] = restArm[j]; }); continue; }
    pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
    const S = bodyGroup.worldToLocal(jointGroups[idx[0]].parent.getWorldPosition(new THREE.Vector3()));
    const d = RIG.dims, reach = a === 0 ? d.upperLenL + d.foreLenL : d.upperLenR + d.foreLenR;
    const v = tgt[a];
    const local = new THREE.Vector3(S.x + sideOf(a) * v[0] * reach, S.y + v[1] * reach, S.z + v[2] * reach);
    solveIK(a, bodyGroup.localToWorld(local), 24);
    let q = pose.slice();
    if (palm[a] === "up" || palm[a] === "down") {
      const f = facePalm(q, a, palm[a] === "up" ? 1 : -1);
      if (f) q = f.pose;
    }
    idx.forEach(j => { p[j] = clampJ(j, q[j]); });
  }
  return p;
}
// A gesture's keys from `start`, made safe: { keys, in, out } or { bad }
function talkFitOne(def, mirror, restPose) {
  const raw = [];
  let from = restPose;
  for (const k of def) {
    const p = talkKeyPose(k, from, restPose, mirror);
    const hit = poseHit(p);
    if (hit) return { bad: hit };
    raw.push({ pose: p, t: k.t || 400, hold: k.hold || 0 });
    from = p;
  }
  // inside the gesture: a hitting move gets in-between keys (marked via)
  const inner = safeKeys(raw);
  if (inner.failed || inner.dropped) return { bad: "a move inside it has no safe way" };
  const leg = (a, b) => {
    const r = planSafe(a, b);
    return r.fail ? null : r.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true }));
  };
  const ins = leg(restPose, inner.keys[0].pose), outs = leg(inner.keys[inner.keys.length - 1].pose, restPose);
  if (!ins || !outs) return { bad: "no safe way from the resting hands" };
  return { keys: inner.keys.map(k => ({ pose: k.pose, t: k.t, hold: k.hold || 0, via: !!k.via })), in: ins, out: outs };
}
// The whole library, a gesture per tick so the page stays live.
async function talkFit() {
  if (TALK.busy || !TALK.lib || !robot) return false;
  TALK.busy = true;
  const saved = pose.slice();
  const L = TALK.lib, fit = { rig: { min: RIG.min.slice(), max: RIG.max.slice(), home: RIG.home.slice() },
    rigFull: talkRigSnap(), restDef: (L.rest || {}).keys || [], defs: {}, gestures: {}, bad: {}, direct: [],
    at: new Date().toISOString() };
  try {
    talkSay("Fitting the gestures to this robot…");
    const home = RIG.home.map((v, j) => clampJ(j, v));
    const restDef = (L.rest || {}).keys || [];
    const restKeys = [];
    let from = home;
    for (const k of restDef) { const p = talkKeyPose(k, from, home, false); restKeys.push({ pose: p, t: k.t || 600, hold: k.hold || 0 }); from = p; }
    if (!restKeys.length || poseHit(restKeys[restKeys.length - 1].pose)) throw new Error("the resting hands hit the body on this robot");
    const restPose = restKeys[restKeys.length - 1].pose;
    const rIn = planSafe(home, restKeys[0].pose), rOut = planSafe(restPose, home);
    if (rIn.fail || rOut.fail) throw new Error("no safe way from home to the resting hands");
    fit.rest = { keys: restKeys,
                 in: rIn.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true })),
                 out: rOut.path.slice(1, -1).map(q => ({ pose: q, t: 300, via: true })) };
    for (const [id, g] of Object.entries(L.gestures || {})) {
      await new Promise(r => setTimeout(r, 0));
      fit.defs[id] = g.keys || [];
      for (const m of g.mirror && !(g.keys || []).some(k => k.pose) ? [false, true] : [false]) {
        const vid = id + (m ? "~m" : "");
        const one = talkFitOne(g.keys || [], m, restPose);
        if (one.bad) fit.bad[vid] = one.bad; else fit.gestures[vid] = one;
      }
      pose = saved.slice(); applyPose();
    }
    // which gesture may flow straight into which, without resting between
    const ids = Object.keys(fit.gestures);
    for (const a of ids) for (const b of ids) {
      const ka = fit.gestures[a].keys, kb = fit.gestures[b].keys;
      if (a !== b && !pathHit(ka[ka.length - 1].pose, kb[0].pose)) fit.direct.push(a + ">" + b);
    }
    const r = await fetch("/api/gestures/fit", { method: "POST", body: JSON.stringify(fit) }).then(x => x.json());
    if (!r.ok) throw new Error(r.error || "the hub did not keep it");
    TALK.fit = fit;
    talkRender();
    return true;
  } catch (e) {
    talkSay("The gestures could not be fitted: " + (e.message || e));
    return false;
  } finally {
    pose = saved; applyPose();
    TALK.busy = false;
  }
}
async function talkCheckFit() {
  if (!TALK.lib && !(await talkLoad())) return;
  if (talkStale()) await talkFit();
}
// The Sequence tab opened (showTab), or the page sat still long enough.
function talkShown() { talkCheckFit(); }
setInterval(() => {
  if (!TALK.busy && !document.hidden && performance.now() - talkIdleAt > TALK_IDLE_MS && typeof robot !== "undefined" && robot) {
    talkIdleAt = performance.now();
    talkCheckFit();
  }
}, 5000);

// ---- the card ----------------------------------------------------------------
function talkRender() {
  const card = $("talkCard");
  if (!card) return;
  card.hidden = !TALK.hub;
  if (!TALK.hub) return;
  const L = TALK.lib, F = TALK.fit || {};
  $("talkOn").checked = L.on !== false;
  const sel = $("talkManner"), keep = sel.value;
  sel.textContent = "";
  Object.keys(L.manners || {}).filter(m => m !== "_default").forEach(m => {
    const o = document.createElement("option"); o.value = o.textContent = m; sel.appendChild(o);
  });
  sel.value = keep || "friendly";
  const n = Object.keys(F.gestures || {}).length, bad = Object.keys(F.bad || {});
  talkSay(talkStale() ? "The gestures are not fitted to this robot as it is now. They will be in a moment."
    : n + " gestures fitted to this robot and kept clear of its body."
      + (bad.length ? " Left out on this robot: " + bad.map(b => talkName(b) + " (" + F.bad[b] + ")").join(", ") + "." : ""));
  const list = $("talkList");
  list.textContent = "";
  Object.entries(L.gestures || {}).forEach(([id, g]) => {
    const row = document.createElement("div"); row.className = "row";
    const name = document.createElement("span"); name.className = "lbl"; name.textContent = g.label || id;
    const words = document.createElement("input");
    words.style.flex = "1"; words.style.minWidth = "0";
    words.title = "Words that bring this gesture, a comma between. Any language.";
    words.value = [].concat(...Object.values(g.words || {})).join(", ");
    words.onchange = () => talkSave({ gestures: { [id]: { words: { any: words.value.split(",").map(s => s.trim()).filter(Boolean) } } } });
    const show = document.createElement("button");
    show.textContent = "▶"; show.title = "Put this gesture on the time bar, fitted to this robot";
    show.onclick = () => talkShowOne(id);
    row.append(name, words, show);
    if (g.mine) {
      const del = document.createElement("button");
      del.textContent = "✕"; del.title = "Remove this gesture";
      del.onclick = () => talkSave({ gestures: { [id]: null } });
      row.append(del);
    }
    list.appendChild(row);
  });
  talkEvents();
}
function talkName(vid) {
  const g = ((TALK.lib || {}).gestures || {})[vid.replace(/~m$/, "")] || {};
  return (g.label || vid) + (vid.endsWith("~m") ? " (other arm)" : "");
}
async function talkSave(change) {
  try {
    const j = await fetch("/api/gestures", { method: "POST", body: JSON.stringify(change) }).then(r => r.json());
    if (!j.ok) throw new Error(j.error || "not saved");
    TALK.lib = j.lib;
    talkRender();
    talkCheckFit();
  } catch (e) { talkSay("Not saved: " + (e.message || e)); notice($("talkStat").textContent); }
}
function talkSaveSwitch() { talkSave({ on: $("talkOn").checked }); }
// The events are the Voice page's scenarios: one switch each.
async function talkEvents() {
  const box = $("talkEvents");
  if (!box) return;
  if (!TALK.events) {            // asked once: the voice helper may be far away or off
    TALK.events = [];
    try { TALK.events = ((await fetch("/api/voice/config").then(r => r.json())).scenarios || []).map(s => s.name).filter(Boolean); }
    catch (e) { /* no voice settings here: no events to list */ }
  }
  const names = TALK.events;
  box.textContent = "";
  if (!names.length) { box.textContent = "No events are set up on the Voice page yet."; return; }
  names.forEach(n => {
    const lab = document.createElement("label"); lab.className = "row";
    const c = document.createElement("input"); c.type = "checkbox";
    c.checked = ((TALK.lib.events || {})[n] || {}).on !== false;
    c.onchange = () => talkSave({ events: { [n]: Object.assign({}, (TALK.lib.events || {})[n], { on: c.checked }) } });
    lab.append(c, document.createTextNode(" " + n));
    box.appendChild(lab);
  });
}
// Steps from the hub (or a fit) -> the time bar, pinned to their own times.
async function talkToBar(steps, what) {
  if (!(await askUnsaved(what))) return false;
  keys = steps.map((s, i) => ({ pose: s.pose.map((v, j) => clampJ(j, v)), t: i ? s.t : 1000, hold: s.hold || 0, tset: i > 0 }));
  bumpKeys(); clearBadMarks();
  selKey = 0; pose = [...keys[0].pose]; poseChanged(false); renderTimeline();
  return true;
}
async function talkTry() {
  const text = $("talkText").value.trim();
  if (!text) { talkSay("Type something the robot might say."); return; }
  await talkCheckFit();
  const j = await fetch("/api/gestures/plan", { method: "POST", body: JSON.stringify({
    text, manner: $("talkManner").value, seed: Math.floor(Math.random() * 1e9) }) }).then(r => r.json()).catch(e => ({ why: String(e) }));
  if (!j.ok) { talkSay(j.why || j.error || "No gestures for that."); return; }
  if (!(await talkToBar(j.steps, "put these gestures on the time bar"))) return;
  $("talkPicks").textContent = j.picks.length
    ? j.picks.map(p => (p.at / 1000).toFixed(1) + " s " + p.label + (p.mirrored ? " (other arm)" : "") + (p.word ? " ← “" + p.word + "”" : "")).join(" · ")
    : "No word asked for a gesture and no beat fitted.";
  $("tlStat").textContent = "Gestures for " + (j.ms / 1000).toFixed(1) + " s of talk are on the time bar. Press Play to watch; press Show again for another random pick.";
}
async function talkShowOne(id) {
  await talkCheckFit();
  const F = TALK.fit || {}, g = (F.gestures || {})[id], rest = F.rest;
  if (!g || !rest) { talkSay(talkName(id) + " is not fitted to this robot: " + ((F.bad || {})[id] || "fit it first")); return; }
  const steps = [{ pose: rest.keys[rest.keys.length - 1].pose, t: 0, hold: 300 }]
    .concat(g.in, g.keys, g.out, [{ pose: rest.keys[rest.keys.length - 1].pose, t: 500, hold: 0 }]);
  if (await talkToBar(steps, "show this gesture on the time bar")) $("tlStat").textContent = talkName(id) + " is on the time bar. Press Play to watch.";
}
// The time bar as a new gesture: its poses as they are (made on this robot),
// checked like every other gesture when it is fitted.
async function talkAddFromBar() {
  const name = $("talkNewName").value.trim();
  if (!name) { talkSay("Give the gesture a name first."); return; }
  const K = playKeys();
  if (K.length < 1) { talkSay("Put at least one move on the time bar first."); return; }
  const id = "mine_" + name.toLowerCase().replace(/[^\w]+/g, "_");
  await talkSave({ gestures: { [id]: { label: name, mine: true,
    words: { any: $("talkNewWords").value.split(",").map(s => s.trim()).filter(Boolean) },
    keys: K.map(k => ({ pose: k.pose.map(v => Math.round(v * 10) / 10), t: Math.round(k.t || 400), hold: Math.round(k.hold || 0) })) } } });
  talkSay(name + " is kept as a gesture. It is fitted and checked next, then the Voice page can use it.");
}
window.addEventListener("load", () => setTimeout(talkLoad, 800));
