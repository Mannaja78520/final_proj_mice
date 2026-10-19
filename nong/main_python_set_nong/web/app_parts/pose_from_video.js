// --- moves from a video of a person (A44-4) ---
// User 2026-10-19: make the robot's moves from a video of a person, as close
// as the robot's joints allow. The browser finds the person's skeleton in each
// frame (MediaPipe Pose). Each arm is then placed by the rig's own solvers: the
// person's upper-arm and forearm DIRECTIONS, at the robot's own bone lengths,
// give an elbow and a hand target - the two-target fit mirrorPose() uses, so
// mounting tilts and joint limits hold and a shape out of reach lands on the
// closest one. The video is read in this browser and never uploaded.
const VID_LIB = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35";
const VID_MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                + "pose_landmarker_full/float16/1/pose_landmarker_full.task";
// MediaPipe's 33-point body: shoulder, elbow, wrist of the person's own L, R.
const VID_PTS = { sh: [11, 12], el: [13, 14], wr: [15, 16] };
const VID_FPS = 10;        // frames read per second of video; the fit is warm-started from the last
const VID_SMOOTH = 2;      // frames each side averaged: tracking jitters ~1-2 cm a frame
const VID_SEEN = 0.5;      // a point MediaPipe is less sure of than this is a guess, not a sighting
// How closely the moves follow the video, in joint degrees off the straight
// line between two kept moves. Every move eases to a stop (as the firmware
// does), so more moves is closer but stop-start. One entry = one choice.
const VID_DETAIL = [
  { id: "smooth", label: "Smooth — fewer moves", tol: 14 },
  { id: "normal", label: "Normal", tol: 8 },
  { id: "close", label: "Close — more moves", tol: 4 },
];
// "always" (A44-6, user 2026-10-19): show that side even where the hand has to
// move for it, as close to the person's pose as the joints allow.
const VID_HAND = [
  { id: "video", label: "as in the video" },
  { id: "palm", label: "palm on top", want: 1 },
  { id: "back", label: "back of the hand on top", want: -1 },
  { id: "palm-force", label: "palm on top, always (the hand may move)", want: 1, force: true },
  { id: "back-force", label: "back on top, always (the hand may move)", want: -1, force: true },
];
// What each made move can become before it goes on the time bar (A44-6).
const VID_USE = [
  { id: "keep", label: "Keep" },
  { id: "force", label: "Keep, hand side forced" },
  { id: "moment", label: "Use another moment…" },
  { id: "drop", label: "Leave out" },
];
let vidLib = null, vidFrames = null, vidMade = null, vidStop = false, vidBusy = false;
let vidFit = null, vidPicks = null;   // fitted frames, and the moves made from them

// The person's skeleton finder. Loaded the first time it is used; the model
// file is then kept in the browser's own store, as its server lets a cache
// hold it for only an hour and the hub must not need the internet every time.
async function vidLoadLib() {
  if (vidLib) return vidLib;
  const mp = await import(VID_LIB + "/vision_bundle.mjs");
  let model = null;
  try {
    const store = await caches.open("mice-pose-model");
    let r = await store.match(VID_MODEL);
    if (!r) { await store.add(VID_MODEL); r = await store.match(VID_MODEL); }
    if (r) model = new Uint8Array(await r.arrayBuffer());
  } catch (e) { model = null; }      // no store here (a phone over plain http): fetch each time
  const files = await mp.FilesetResolver.forVisionTasks(VID_LIB + "/wasm");
  const base = model ? { modelAssetBuffer: model } : { modelAssetPath: VID_MODEL };
  const make = (delegate) => mp.PoseLandmarker.createFromOptions(files, {
    baseOptions: { ...base, delegate }, runningMode: "VIDEO", numPoses: 1 });
  // Some graphics drivers refuse the GPU path; the CPU one is slower, not wrong.
  try { vidLib = await make("GPU"); } catch (e) { vidLib = await make("CPU"); }
  return vidLib;
}

function vidSay(text, bad) {
  $("vidStat").textContent = text;
  if (bad) notice(text);
}
function vidOpts() {
  const det = VID_DETAIL.find(d => d.id === $("vidDetail").value) || VID_DETAIL[1];
  const h = [0, 1].map(a => VID_HAND.find(x => x.id === $("vidHand" + a).value) || {});
  return { tol: det.tol, mirror: $("vidMirror").checked, waist: $("vidWaist").checked,
           hand: h.map(x => x.want || 0), force: h.map(x => !!x.force),
           music: $("vidMusic").checked };
}
function vidFill() {        // the choices are built from the lists above
  const fill = (sel, list, pick) => {
    if (!sel || sel.options.length) return;
    list.forEach(o => sel.add(new Option(o.label, o.id, false, o.id === pick)));
  };
  fill($("vidDetail"), VID_DETAIL, "normal");
  HANDS.forEach((h, a) => {
    const lbl = $("vidHandLbl" + a);
    if (lbl) lbl.textContent = h.label;
    fill($("vidHand" + a), VID_HAND, "video");
  });
}

function vidPick(file) {
  vidFill();
  if (!file) return;
  const v = $("vidPlayer");
  if (v.src) URL.revokeObjectURL(v.src);
  v.src = URL.createObjectURL(file);
  v.hidden = false;
  vidFrames = null; vidMade = null; vidFit = null; vidPicks = null;
  vidList();
  $("vidUseBox").hidden = true;
  $("vidGo").disabled = false;
  v.onloadedmetadata = () => {
    $("vidTo").value = v.duration.toFixed(1);
    $("vidFrom").value = "0";
    vidSay("Ready: " + v.duration.toFixed(1) + " s of video. Press Make moves.");
  };
  v.onerror = () => vidSay("This browser cannot play that video. Try an MP4 or WEBM file.", true);
}

// Seek through the video and find the person in each frame. Seeking, not
// playing, so every frame is read however slow the PC is.
async function vidRead() {
  const v = $("vidPlayer");
  if (!v.src || !isFinite(v.duration)) { vidSay("Pick a video first.", true); return null; }
  vidSay("Loading the body finder (the first time needs the internet)…");
  let lib;
  try { lib = await vidLoadLib(); }
  catch (e) {
    vidSay("Could not load the body finder. It needs the internet the first time; "
           + "check the connection and press Make moves again.", true);
    $("vidTech").textContent = String(e && e.message || e);
    return null;
  }
  const from = Math.max(0, +$("vidFrom").value || 0);
  const to = Math.min(v.duration, +$("vidTo").value || v.duration);
  const frames = [];
  v.pause();
  for (let t = from; t <= to + 1e-6 && !vidStop; t += 1 / VID_FPS) {
    await new Promise(res => { v.onseeked = res; v.currentTime = Math.min(t, v.duration - 0.001); });
    // timestamps must only grow, also on a second read of the same video
    const r = lib.detectForVideo(v, performance.now());
    const w = r.worldLandmarks && r.worldLandmarks[0];
    frames.push({ t: t - from, w: w ? w.map(p => ({ x: p.x, y: p.y, z: p.z, v: p.visibility })) : null });
    vidDraw(r.landmarks && r.landmarks[0]);
    vidSay("Reading the video: " + Math.round(100 * (t - from) / Math.max(0.1, to - from)) + "%");
  }
  return frames;
}
// The skeleton over the video, so it is plain whether the person was found.
function vidDraw(pts) {
  const v = $("vidPlayer"), c = $("vidOverlay");
  c.width = v.clientWidth; c.height = v.clientHeight;
  const g = c.getContext("2d");
  g.clearRect(0, 0, c.width, c.height);
  if (!pts) return;
  const css = getComputedStyle(document.documentElement);
  g.strokeStyle = css.getPropertyValue("--acc").trim() || "currentColor";
  g.lineWidth = 3;
  const P = i => [pts[i].x * c.width, pts[i].y * c.height];
  const lines = [[11, 12]];
  for (const s of [0, 1]) lines.push([VID_PTS.sh[s], VID_PTS.el[s]], [VID_PTS.el[s], VID_PTS.wr[s]]);
  g.beginPath();
  for (const [a, b] of lines) { g.moveTo(...P(a)); g.lineTo(...P(b)); }
  g.stroke();
}

// ---- skeleton -> the robot's two bone directions per arm --------------------
// MediaPipe's world points are metres, x right in the picture, y down, z away
// from the camera. Turned to y up and z toward the camera, a person facing the
// camera has the robot's own axes: +x their left, +y up, +z their front. The
// person's frame turns with their shoulder line, so a person standing at an
// angle still drives the arms as if facing the robot's front.
function vidBodyFrame(w, mirror) {
  const pt = (i) => {
    // A mirror swaps the person's sides and flips the picture: the robot then
    // moves like their reflection, which is how an audience in front sees it.
    const j = mirror ? (i % 2 ? i + 1 : i - 1) : i;
    const p = w[j];
    return { at: new THREE.Vector3(mirror ? -p.x : p.x, -p.y, -p.z), seen: (p.v == null ? 1 : p.v) };
  };
  const L = pt(VID_PTS.sh[0]), R = pt(VID_PTS.sh[1]);
  const left = L.at.clone().sub(R.at); left.y = 0;
  if (left.length() < 1e-4) return null;
  left.normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const front = left.clone().cross(up);
  const toBody = (d) => new THREE.Vector3(d.dot(left), d.dot(up), d.dot(front)).normalize();
  const arms = [0, 1].map(a => {
    const S = pt(VID_PTS.sh[a]), E = pt(VID_PTS.el[a]), W = pt(VID_PTS.wr[a]);
    const ok = Math.min(S.seen, E.seen, W.seen) >= VID_SEEN;
    return { ok, upper: toBody(E.at.clone().sub(S.at)), fore: toBody(W.at.clone().sub(E.at)) };
  });
  // yaw: 0 facing the camera, + turned toward their own left
  return { arms, yaw: Math.atan2(front.x, front.z) };
}
// One sample per frame: bone directions per arm, unseen frames filled from the
// nearest seen one, then averaged over a few frames each side.
function vidBones(frames, mirror) {
  const raw = frames.map(f => (f.w ? vidBodyFrame(f.w, mirror) : null));
  const out = frames.map((f, i) => ({ t: f.t, yaw: raw[i] ? raw[i].yaw : null, arms: [null, null] }));
  for (const a of [0, 1]) {
    const seen = raw.map((r, i) => (r && r.arms[a].ok ? i : -1)).filter(i => i >= 0);
    if (!seen.length) continue;
    for (let i = 0, k = 0; i < raw.length; i++) {
      while (k + 1 < seen.length && Math.abs(seen[k + 1] - i) <= Math.abs(seen[k] - i)) k++;
      out[i].arms[a] = raw[seen[k]].arms[a];
    }
  }
  const smooth = (get) => out.map((_, i) => {
    const s = new THREE.Vector3();
    for (let j = Math.max(0, i - VID_SMOOTH); j <= Math.min(out.length - 1, i + VID_SMOOTH); j++) {
      const v = get(j); if (v) s.add(v);
    }
    return s.lengthSq() > 1e-9 ? s.normalize() : null;
  });
  const res = out.map(o => ({ t: o.t, yaw: o.yaw, arms: [null, null] }));
  for (const a of [0, 1]) {
    const up = smooth(j => out[j].arms[a] && out[j].arms[a].upper);
    const fo = smooth(j => out[j].arms[a] && out[j].arms[a].fore);
    res.forEach((r, i) => { if (up[i] && fo[i]) r.arms[a] = { upper: up[i], fore: fo[i] }; });
  }
  return res;
}

// ---- directions -> joint angles --------------------------------------------
// The waist value that turns the body by `yaw`, found by trying them on the
// rig: the joint's sense and zero are rig data, not a sign to guess here.
function vidWaistTable() {
  const tbl = [];
  for (let v = RIG.min[8]; v <= RIG.max[8]; v += 1) {
    pose[8] = v; applyPose();
    const d = new THREE.Vector3(0, 0, 1).applyQuaternion(bodyGroup.quaternion);
    tbl.push({ v, yaw: Math.atan2(d.x, d.z) });
  }
  return tbl;
}
// Put one arm where the person's arm points: elbow by the two shoulder joints,
// hand by the two elbow joints. `first` walks there from afar (solveElbowIK);
// later frames start from the last fit and are a few degrees away.
function vidFitArm(arm, bones, first) {
  const sh = arm === 0 ? [0, 1] : [4, 5], el = arm === 0 ? [2, 3] : [6, 7];
  robot.updateMatrixWorld(true);
  const W = (o) => o.getWorldPosition(new THREE.Vector3());
  const S = W(jointGroups[sh[0]]), E0 = W(elbowBalls[arm]), H0 = W(wristBalls[arm]);
  const upperLen = E0.distanceTo(S), foreLen = H0.distanceTo(E0);
  const s = bodyGroup.worldToLocal(S.clone());
  const e = s.clone().addScaledVector(bones.upper, upperLen);
  const h = e.clone().addScaledVector(bones.fore, foreLen);
  const eW = bodyGroup.localToWorld(e), hW = bodyGroup.localToWorld(h);
  if (first) solveElbowIK(arm, eW);
  else if (ccdChain(sh, elbowBalls[arm], eW, 6) > 15) solveElbowIK(arm, eW);
  ccdChain(el, wristBalls[arm], hW, first ? 24 : 8);
  applyPose();             // ccdChain leaves its last rejected try drawn
}
// Douglas-Peucker on the joint angles: keep the frame that strays furthest from
// the straight line between two kept ones, until none strays more than `tol`.
function vidThin(times, poses, tol) {
  const keep = new Set([0, poses.length - 1]);
  const off = (a, b, i) => {
    const f = (times[i] - times[a]) / Math.max(1e-6, times[b] - times[a]);
    let m = 0;
    for (let j = 0; j < NJ; j++)
      m = Math.max(m, Math.abs(poses[a][j] + (poses[b][j] - poses[a][j]) * f - poses[i][j]));
    return m;
  };
  const stack = [[0, poses.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    let worst = -1, far = tol;
    for (let i = a + 1; i < b; i++) { const d = off(a, b, i); if (d > far) { far = d; worst = i; } }
    if (worst >= 0) { keep.add(worst); stack.push([a, worst], [worst, b]); }
  }
  return [...keep].sort((x, y) => x - y);
}
// ---- frames -> moves, in three steps (A44-6) --------------------------------
// 1. Fit every frame: the slow part, done again only when Mirror or Waist change.
function vidFitFrames(frames, opts) {
  const bones = vidBones(frames, opts.mirror);
  if (!bones.some(b => b.arms[0] || b.arms[1])) return null;
  const saved = pose;
  const poses = [];
  try {
    pose = RIG.neutral.map((v, i) => clampJ(i, v));
    const waist = opts.waist ? vidWaistTable() : null;
    bones.forEach((b, i) => {
      if (waist && b.yaw != null) {
        let best = waist[0];
        for (const w of waist) if (Math.abs(w.yaw - b.yaw) < Math.abs(best.yaw - b.yaw)) best = w;
        pose[8] = best.v;
      } else pose[8] = clampJ(8, RIG.neutral[8]);
      applyPose();
      for (const a of [0, 1]) if (b.arms[a]) vidFitArm(a, b.arms[a], i === 0);
      poses.push(pose.map(v => Math.round(v * 10) / 10));
    });
  } finally { pose = saved; applyPose(); }
  const times = bones.map(b => b.t * 1000);
  return { times, poses, mirror: opts.mirror, waist: opts.waist,
           videoMs: Math.round(times[times.length - 1] || 0) };
}
// 2. Which frames become moves. Each can then be kept, left out, or filled
// with another moment of the video - its place on the video's clock stays.
function vidPicksFor(fit, tol) {
  return vidThin(fit.times, fit.poses, tol).map(i => ({ i, use: "keep", at: fit.times[i] }));
}
function vidPoseAt(fit, ms) {    // the fitted pose nearest a moment of the video
  let best = 0;
  fit.times.forEach((t, i) => { if (Math.abs(t - ms) < Math.abs(fit.times[best] - ms)) best = i; });
  return fit.poses[best];
}
// One side of a hand on top even where the hand must move for it: from
// facePalm's best shape, the least hand travel that shows that side. Returns
// facePalm's shape: { pose, upness } (+1 palm up, -1 back up).
// near: start from p itself, not facePalm's shape - the smallest nudge, for a
// move that has only so much time (facePalm may pick a far shape).
function vidForceHand(p, arm, want, near) {
  const r = near ? { pose: p, upness: palmUpnessOf(p, arm) } : facePalm(p, arm, want);
  if (!r || want * r.upness > 0.5) return r;
  const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
  const saved = pose;
  try {
    pose = p.slice(); applyPose(); robot.updateMatrixWorld(true);
    const h0 = wristBalls[arm].getWorldPosition(new THREE.Vector3());
    // 1 mm of hand travel against the side shown: not showing it costs as much
    // as moving the hand two metres, so the side always wins when it can.
    const cost = () => {
      applyPose(); robot.updateMatrixWorld(true);
      return wristBalls[arm].getWorldPosition(new THREE.Vector3()).distanceTo(h0)
           + 2000 * Math.max(0, 0.6 - want * palmUpness(arm));
    };
    pose = r.pose.slice();
    let best = cost();
    for (let round = 0; round < 40; round++) {
      let better = false;
      for (const j of idx) for (const step of [20, 8, 3, 1]) for (const dir of [1, -1]) {
        const old = pose[j], nv = clampJ(j, old + dir * step);
        if (nv === old) continue;
        pose[j] = nv;
        const c = cost();
        if (c < best - 0.01) { best = c; better = true; } else pose[j] = old;
      }
      if (!better) break;
    }
    applyPose();
    return { pose: pose.slice(), upness: palmUpness(arm) };
  } finally { pose = saved; applyPose(); }
}
// The furthest a move gets toward `to` in `ms`: all the way if the servos can,
// else part of the way - so it still ends on its beat and the show stays with
// the music (user 2026-10-19).
function vidReachIn(from, to, ms) {
  if (minTime(from, to) <= ms) return to;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  let lo = 0, hi = 1;
  for (let k = 0; k < 14; k++) {
    const m = (lo + hi) / 2;
    if (minTime(from, at(m)) <= ms) lo = m; else hi = m;
  }
  return at(lo);
}
// The asked hand side on a pose: { pose, miss: [L, R] } (miss = that hand
// still not showing it). upness is +1 palm up, -1 back up, whichever was asked.
// near: for a part-way move - a hand already showing it stays put, else it
// gets the smallest nudge; facePalm goes for the MOST upness, which can be a
// big jump the time left cannot pay for.
function vidSide(p, pk, opts, near) {
  const miss = [false, false];
  for (const a of [0, 1]) if (opts.hand[a]) {
    const force = opts.force[a] || pk.use === "force";
    const r = near ? vidForceHand(p, a, opts.hand[a], true)
      : force ? vidForceHand(p, a, opts.hand[a]) : facePalm(p, a, opts.hand[a]);
    if (r) p = r.pose.map(v => Math.round(v * 10) / 10);
    // A near-straight arm cannot roll its hand (the elbow sits on the
    // turning line); it stayed on its edge with nothing said (browser test
    // 2026-10-19).
    if (!r || opts.hand[a] * r.upness <= 0.5) miss[a] = true;
  }
  return { pose: p, miss };
}
// Part of the way in `ms` AND a forced hand side kept. A plain part-way pose
// is a joint blend, and a blend of two back-up shapes can pass the hand's edge
// (PC 2026-10-19: back forced, music on, upness up to +0.10 with no miss
// said). So the side goes on each try and the furthest try in time wins; at
// worst the robot stays where it is for that beat, still showing the side.
function vidReachSide(from, to, ms, pk, opts) {
  const forced = [0, 1].filter(a => opts.hand[a] && (opts.force[a] || pk.use === "force"));
  const fits = (s) => minTime(from, s.pose) <= ms && forced.every(a => !s.miss[a]);
  const plain = vidReachIn(from, to, ms), near = vidSide(plain, pk, opts, true);
  if (fits(near)) return near;
  const at = (f) => from.map((a, j) => a + (to[j] - a) * f);
  const still = vidSide(from, pk, opts, true);
  let lo = 0, hi = 1, best = fits(still) ? still : null;
  for (let k = 0; k < 8; k++) {
    const m = (lo + hi) / 2, s = vidSide(at(m), pk, opts, true);
    if (fits(s)) { lo = m; best = s; } else hi = m;
  }
  // The last move already lost the side: keep the beat and say so.
  return best || { pose: plain, miss: [0, 1].map(a => !!opts.hand[a]
    && opts.hand[a] * palmUpnessOf(plain, a) <= 0.5) };
}
// 3. The moves, from the picks and the choices.
function vidBuild(fit, picks, opts) {
  const out = [], handMiss = [0, 0];
  let kept = 0, partial = 0, last = 0;
  for (const pk of picks) {
    pk.missHand = [false, false];
    if (pk.use === "drop") continue;
    let s = vidSide(pk.use === "moment" ? vidPoseAt(fit, pk.at) : fit.poses[pk.i], pk, opts);
    kept++;
    const t = fit.times[pk.i];       // its place on the video's clock
    const prev = out[out.length - 1];
    const gap = t - last;
    last = t;
    if (!prev) out.push({ pose: s.pose, t: 1000, hold: 0 });
    // the same pose again is a pause on the last move, not a move of no length
    else if (deltaDeg(prev.pose, s.pose) < 1) prev.hold += gap;
    else {
      if (opts.music && minTime(prev.pose, s.pose) > gap) {
        s = vidReachSide(prev.pose, s.pose, gap, pk, opts);
        partial++;
      }
      // Pinned, so Show speed does not re-time the video's rhythm. Without
      // "stay with the music" a move too fast for the servos is slowed instead.
      if (deltaDeg(prev.pose, s.pose) < 1) prev.hold += gap;
      else out.push({ pose: s.pose, t: Math.round(gap), hold: 0, tset: true });
    }
    // counted on the pose that went on the bar, after any part-way cut
    for (const a of [0, 1]) if (s.miss[a]) { handMiss[a]++; pk.missHand[a] = true; }
  }
  out.forEach(k => { k.hold = Math.round(k.hold); });
  return { keys: out, videoMs: fit.videoMs, handMiss, kept, partial };
}
// frames -> timeline keys in one go. No video needed, so QC hands it a skeleton.
// opts: { tol, mirror, waist, hand: [want L, R] (0 = as in the video),
//         force: [L, R], music }
function movesFromFrames(frames, opts) {
  const fit = vidFitFrames(frames, opts);
  if (!fit) return null;
  const o = { force: [false, false], music: false, ...opts };
  return vidBuild(fit, vidPicksFor(fit, o.tol), o);
}

// What the choices could not do, in words; empty when everything worked.
function vidHandNote(made) {
  const opts = vidOpts();
  return [0, 1].filter(a => opts.hand[a] && made.handMiss[a]).map(a =>
    " The " + HANDS[a].label.toLowerCase() + " could not show its "
    + (opts.hand[a] > 0 ? "palm" : "back") + " on top in " + made.handMiss[a] + " of "
    + made.kept + " moves" + (opts.force[a]
      ? ": the joints cannot turn it that far even with the hand moved."
      : ": the arm is almost straight there. Pick “always” for that hand, or "
        + "“Keep, hand side forced” on those moves below, and the hand moves "
        + "just enough to show it.")).join("");
}
function vidSummary() {
  const m = vidMade, opts = vidOpts();
  return m.keys.length + " moves from " + (m.videoMs / 1000).toFixed(1) + " s of video."
    + (opts.music && m.partial
      ? " To stay with the music, " + m.partial + " of them go only part of the way: "
        + "the person moved faster than the robot can."
      : "")
    + vidHandNote(m) + " Choose what to keep below, then put them on the time bar:";
}
// One row per made move: its moment (click to see it), what it becomes, and
// what could not be done for it.
function vidList() {
  const box = $("vidList");
  box.innerHTML = "";
  if (!vidPicks) return;
  const opts = vidOpts(), anyHand = opts.hand.some(Boolean);
  vidPicks.forEach((pk, n) => {
    const row = document.createElement("div");
    row.className = "row vidrow";
    const see = document.createElement("button");
    see.type = "button";
    see.textContent = (n + 1) + " · " + (vidFit.times[pk.i] / 1000).toFixed(1) + " s";
    see.title = "see this moment of the video and the robot's pose for it";
    see.onclick = () => vidSee(pk);
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "move " + (n + 1));
    VID_USE.filter(u => u.id !== "force" || anyHand)
      .forEach(u => sel.add(new Option(u.label, u.id, false, u.id === pk.use)));
    const at = document.createElement("input");
    at.type = "number"; at.step = "0.1"; at.min = "0";
    at.value = (pk.at / 1000).toFixed(1);
    at.hidden = pk.use !== "moment";
    at.title = "the moment of the video (s) whose pose fills this move; it keeps its own place in time";
    at.setAttribute("aria-label", "moment for move " + (n + 1));
    sel.onchange = () => { pk.use = sel.value; at.hidden = pk.use !== "moment"; vidRebuild(); };
    at.onchange = () => { pk.at = Math.max(0, +at.value || 0) * 1000; vidRebuild(); vidSee(pk); };
    row.append(see, sel, at);
    const miss = HANDS.filter((h, a) => pk.missHand && pk.missHand[a]).map(h => h.side);
    if (miss.length) {
      const w = document.createElement("span");
      w.className = "mini";
      w.textContent = miss.join(" ") + " hand on its edge";
      row.appendChild(w);
    }
    box.appendChild(row);
  });
}
function vidSee(pk) {
  const v = $("vidPlayer");
  const ms = pk.use === "moment" ? pk.at : vidFit.times[pk.i];
  if (v.src && isFinite(v.duration)) {
    v.pause();
    v.currentTime = Math.min(v.duration, (+$("vidFrom").value || 0) + ms / 1000);
  }
  pose = vidPoseAt(vidFit, ms).slice();
  poseChanged(false);
}
async function vidMake() {
  if (vidBusy) { vidStop = true; return; }
  vidBusy = true; vidStop = false;
  $("vidGo").textContent = "■ Stop";
  $("vidUseBox").hidden = true;
  try {
    const frames = await vidRead();
    if (!frames) return;
    if (!frames.some(f => f.w)) {
      vidSay("No person was found in the video. Use a video where one person's "
             + "upper body and arms are in the picture.", true);
      return;
    }
    vidFrames = frames;
    vidSay("Fitting the robot's arms…");
    await new Promise(r => setTimeout(r, 30));      // let the line paint first
    vidRemake("fit");
    if (!vidMade || vidMade.keys.length < 2) {
      vidSay("The arms were not seen clearly enough to make moves. Try a video "
             + "where the arms are in the picture and not hidden.", true);
      vidMade = null;
      return;
    }
    const seen = frames.filter(f => f.w).length;
    vidSay("The person was found in " + Math.round(100 * seen / frames.length)
           + "% of the video. " + vidSummary());
  } finally {
    vidBusy = false;
    $("vidGo").textContent = "▶ Make moves";
  }
}
// A choice changed: redo only what it touches. "fit" (Mirror, Waist) fits the
// frames again, "pick" (Follow) chooses the moves again and resets each move's
// own choice, anything else (hands, music, a move's row) just rebuilds.
function vidRemake(step) {
  if (!vidFrames || (vidBusy && step !== "fit")) return;
  const opts = vidOpts();
  if (step === "fit" || !vidFit) vidFit = vidFitFrames(vidFrames, opts);
  if (!vidFit) { vidMade = null; vidPicks = null; vidList(); return; }
  if (step === "fit" || step === "pick" || !vidPicks) vidPicks = vidPicksFor(vidFit, opts.tol);
  vidRebuild();
}
function vidRebuild() {
  vidMade = vidBuild(vidFit, vidPicks, vidOpts());
  vidList();
  $("vidUseBox").hidden = !(vidMade && vidMade.keys.length >= 2);
  vidSay(vidSummary());
}
async function vidUse(how) {
  if (!vidMade) return;
  const add = JSON.parse(JSON.stringify(vidMade.keys));
  if (how === "replace") {
    if (!(await askUnsaved("replace the time bar with the moves from the video"))) return;
    keys = add;
  } else {
    // the first video pose is a move like any other once it follows a move
    add[0].t = autoTime(keys[keys.length - 1].pose, add[0].pose, keyDps(keys.length));
    keys = keys.concat(add);
  }
  bumpKeys();
  clearBadMarks();
  clampKeyTimes();
  selKey = how === "replace" ? 0 : keys.length - add.length;
  pose = [...keys[selKey].pose];
  poseChanged(false);
  renderTimeline();
  const robotMs = keys.slice(selKey).reduce((s, k, i) => s + (i ? k.t : 0) + (k.hold || 0), 0);
  $("tlStat").textContent = add.length + " moves from the video are on the time bar. "
    + (robotMs > vidMade.videoMs * 1.15
      ? "The robot needs " + (robotMs / 1000).toFixed(1) + " s for " + (vidMade.videoMs / 1000).toFixed(1)
        + " s of video: the person moved faster than its servos and speed limit allow. "
        + "Tick “Stay with the music” to keep the video's timing instead. "
      : "")
    + "Press Play to watch, edit any move, then Save or Save to robot.";
  vidSay($("tlStat").textContent);
}
vidFill();
