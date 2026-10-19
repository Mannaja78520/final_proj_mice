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
const VID_HAND = [
  { id: "video", label: "as in the video" },
  { id: "palm", label: "palm on top", want: 1 },
  { id: "back", label: "back of the hand on top", want: -1 },
];
let vidLib = null, vidFrames = null, vidMade = null, vidStop = false, vidBusy = false;

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
  const hand = [0, 1].map(a => (VID_HAND.find(h => h.id === $("vidHand" + a).value) || {}).want || 0);
  return { tol: det.tol, mirror: $("vidMirror").checked, waist: $("vidWaist").checked, hand };
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
  vidFrames = null; vidMade = null;
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
// frames -> timeline keys. No video needed, so QC can hand it a skeleton.
// opts: { tol, mirror, waist, hand: [want L, want R] } (want 0 = as in the video).
function movesFromFrames(frames, opts) {
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
  const idx = vidThin(times, poses, opts.tol);
  const out = [];
  idx.forEach((i, n) => {
    let p = poses[i];
    for (const a of [0, 1]) if (opts.hand[a]) {
      const r = facePalm(p, a, opts.hand[a]);
      if (r) p = r.pose.map(v => Math.round(v * 10) / 10);
    }
    const prev = out[out.length - 1];
    const gap = n ? times[i] - times[idx[n - 1]] : 0;
    // the same pose again is a pause on the last move, not a move of no length
    if (prev && deltaDeg(prev.pose, p) < 1) { prev.hold = (prev.hold || 0) + gap; return; }
    // The video's own rhythm, pinned so Show speed does not re-time it. A move
    // faster than the servos can go is still raised to what they can do.
    out.push(n ? { pose: p, t: Math.round(gap), hold: 0, tset: true } : { pose: p, t: 1000, hold: 0 });
  });
  out.forEach(k => { k.hold = Math.round(k.hold || 0); });
  return { keys: out, videoMs: Math.round(times[times.length - 1] || 0) };
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
    vidMade = movesFromFrames(frames, vidOpts());
    if (!vidMade || vidMade.keys.length < 2) {
      vidSay("The arms were not seen clearly enough to make moves. Try a video "
             + "where the arms are in the picture and not hidden.", true);
      vidMade = null;
      return;
    }
    const seen = frames.filter(f => f.w).length;
    vidSay(vidMade.keys.length + " moves made from " + (vidMade.videoMs / 1000).toFixed(1)
           + " s of video (the person was found in " + Math.round(100 * seen / frames.length)
           + "% of it). Put them on the time bar:");
    $("vidUseBox").hidden = false;
  } finally {
    vidBusy = false;
    $("vidGo").textContent = "▶ Make moves";
  }
}
// The choices changed after reading: make the moves again from the same frames.
function vidRemake() {
  if (!vidFrames || vidBusy) return;
  vidMade = movesFromFrames(vidFrames, vidOpts());
  if (vidMade) vidSay(vidMade.keys.length + " moves with these choices. Put them on the time bar:");
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
      : "")
    + "Press Play to watch, edit any move, then Save or Save to robot.";
  vidSay($("tlStat").textContent);
}
vidFill();
