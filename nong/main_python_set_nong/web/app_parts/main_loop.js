// --- main loop ---
function resize() {
  const w = viewport.clientWidth, h = viewport.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  syncOrtho();                    // the ortho frustum follows the new aspect
}
window.addEventListener("resize", resize);
// The viewport also changes size WITHOUT the window changing: dragging the
// side-panel splitter, a tab whose content is wider, a scrollbar appearing.
// The window resize event says nothing about any of those, so the canvas kept
// its old size and spilled over the settings panel. Watch the element itself.
if (window.ResizeObserver) {
  // Only act on a REAL size change. resize() sets the canvas size, and a
  // canvas inside the observed element can feed the change straight back —
  // an observer that re-triggers itself spins the CPU for as long as the page
  // is open, which looks exactly like the machine hanging.
  let lastW = 0, lastH = 0;
  new ResizeObserver(function () {
    const w = viewport.clientWidth, h = viewport.clientHeight;
    if (w === lastW && h === lastH) return;
    lastW = w; lastH = h;
    resize();
  }).observe(viewport);
}

// Advancing the show is separate from DRAWING it, because the two run at
// different times: the animation frame stops in a hidden tab, the interval in
// keepAwake() does not. Both call this, and it works out its own elapsed time
// from the clock — so whichever fires, time advances exactly once and never
// twice.
// NOTE — polling the hub for the play head does NOT work, and was removed.
//
// While the hub drives, this page kept its own clock and I tried correcting it
// once a second from GET /api/play. That broke playback outright: the check
// "the robot walks the whole timeline in order" saw 90,60,120,60,120,90 for a
// four-move timeline, and the hold between moves collapsed from 2200 ms to
// 1565 ms. Reading the player a second while it is running disturbs the thing
// being read.
//
// If the preview and the arm need tying together properly, the page must stop
// keeping a clock at all while the hub drives and simply draw the position the
// hub reports — not run a second clock and snap it. That is a bigger change
// than a poll and is not attempted here.
let lastPlayMs = 0;
let _drawing = false;          // true only inside the animation frame
let _lastScrub = -1, _lastTime = "";
function playTick() {
  if (!playing) { lastPlayMs = 0; return; }
  const now = performance.now();
  if (!lastPlayMs) { lastPlayMs = now; return; }
  // Clamp the step. A hidden tab has its timers throttled (to about once a
  // minute) and rAF stopped altogether, so coming back after 30 s gave a dt of
  // 30000: the play head teleported, the pose jumped across the whole show in
  // one tick, and every joint was re-sent at once — which is what made the
  // page hang for a moment on return.
  //
  // Clamping is also the CORRECT answer, not just a safe one. While the tab
  // was hidden nothing was being sent, so the robot did not advance either.
  // Advancing the preview by the wall-clock gap would put the preview ahead of
  // the real arm. Both simply continue from where they were.
  //
  // When the HUB is the clock that reasoning flips — the robot DID keep
  // moving — so the visibilitychange handler asks the hub where the show got
  // to and moves the play head there. Clamping still applies in between.
  const dt = Math.min(now - lastPlayMs, MAX_TICK_MS);
  lastPlayMs = now;
  if (dt <= 0) return;

  playT += dt;
  const total = totalMs();
  if (playT >= total) {
    if ($("loopChk").checked) { playT = 0; lastLiveSeg = -1; }  // re-send seg 1
    else {
      playT = total; playing = false;
      $("playBtn").textContent = "▶ Play";
      keepAwake(false);                    // the show is over: let the tab idle
    }
  }
  pose = poseAt(playT).map((v, i) => clampJ(i, v));
  // DRAW only from the animation frame. Both rAF and the keep-awake interval
  // call this, so the picture was being redrawn ~76 times a second when the
  // screen can only show 60 — the extra passes were pure cost. Time still
  // advances on whichever fires (that is what keeps a hidden tab moving);
  // only the painting is limited to the frame.
  if (_drawing) {
    applyPose(); renderSliders();
    const scrub = total ? Math.round(playT / total * 1000) : 0;
    if (_lastScrub !== scrub) { _lastScrub = scrub; $("scrub").value = scrub; }
    const lbl = (playT / 1000).toFixed(1) + "s / " + (total / 1000).toFixed(1) + "s";
    if (_lastTime !== lbl) { _lastTime = lbl; $("tlTime").textContent = lbl; }
  }
  // live-follow: push each segment to the robot with its exact duration.
  // Any open link counts — this used to test robotIp(), so Play moved the
  // robot over WiFi but silently did nothing over USB/RS485.
  //
  // ...unless the HUB is the clock. Then the hub is already sending these
  // exact commands from a process no browser can throttle, and this preview is
  // only a picture: sending from here as well would be the second clock all
  // over again. See hubDriven().
  if (liveLinked() && !hubDriven() && !previewOnly) {
    const seg = segmentAt(playT);
    if (seg !== -1 && seg !== lastLiveSeg) {
      lastLiveSeg = seg;
      // exact T at the head of a segment (a whole playthrough sends the
      // same numbers the YAML holds); after a pause, only what is left
      const K = playKeys();
      const rem = segRemaining(playT);
      const tt = K[seg].t - rem <= 50 ? K[seg].t : rem;
      liveSend("POSE " + K[seg].pose.map(fmtA).join(" ") + " T " + tt);
    }
  }
}

function tick(now) {
  requestAnimationFrame(tick);
  _drawing = true;          // this pass may paint; the interval's may not
  playTick();               // no-op when the interval already advanced it
  _drawing = false;
  lastFrame = now;
  controls.update();
  renderer.render(scene, activeCam());
}

// Per-joint servo self-test (?selftest=servo): a slow servo on ONE joint must
// stretch the minimum time for a move that turns that joint, and must NOT
// affect a move that leaves it alone — the same rule the firmware applies.
function runServoSelfTest() {
  const save = { dps: RIG.servoMaxDps.slice(), lo: RIG.pulseMin.slice(),
                 hi: RIG.pulseMax.slice(), rng: RIG.servoRange.slice(),
                 mn: RIG.min.slice(), mx: RIG.max.slice(),
                 gp: RIG.gearPinion.slice(), gg: RIG.gearGear.slice(),
                 hz: RIG.frameHz.slice() };
  const fails = [];
  const flat = new Array(NJ).fill(90);
  RIG.servoMaxDps = new Array(NJ).fill(400);
  const a = flat.slice(); a[2] = 130;              // 40 deg on joint 3 (L_EL_P)
  const fastElbow = minTime(flat, a);
  const b = flat.slice(); b[0] = 130;              // 40 deg on joint 1 (L_SH_P)
  const fastSh = minTime(flat, b);
  RIG.servoMaxDps[2] = 100;                        // slow servo on joint 3 only
  const slowElbow = minTime(flat, a);
  const shAfter = minTime(flat, b);
  if (!(slowElbow > fastElbow * 3.5))
    fails.push(`slow joint did not stretch its move (${fastElbow}->${slowElbow}ms)`);
  if (shAfter !== fastSh)
    fails.push(`slow joint changed an unrelated move (${fastSh}->${shAfter}ms)`);
  // preset must hit only the joints it names
  RIG.servoMaxDps = new Array(NJ).fill(1);
  RIG.pulseMin = new Array(NJ).fill(1); RIG.pulseMax = new Array(NJ).fill(1);
  RIG.servoRange = new Array(NJ).fill(1);
  applyServoPreset("pdi1181mg|sh");
  const shIdx = [0, 1, 4, 5], elIdx = [2, 3, 6, 7];
  if (!shIdx.every(i => RIG.pulseMax[i] === 2500 && RIG.servoMaxDps[i] === 375 && RIG.servoRange[i] === 270))
    fails.push("shoulder preset did not reach every shoulder joint (with 270 travel)");
  if (!elIdx.every(i => RIG.pulseMax[i] === 1))
    fails.push("shoulder preset leaked into the elbows");
  if (RIG.pulseMax[8] === 2500 || RIG.pulseMax[9] === 2500)
    fails.push("shoulder preset leaked into the body joints");
  applyServoPreset("mg90s|el");
  if (!elIdx.every(i => RIG.pulseMax[i] === 2400 && RIG.servoMaxDps[i] === 400))
    fails.push("elbow preset did not reach every elbow joint");
  if (!shIdx.every(i => RIG.pulseMax[i] === 2500))
    fails.push("elbow preset overwrote the shoulders");
  // WAIST + SHRUG presets target exactly their one joint (idx 8 / 9)
  applyServoPreset("tiankong35|waist");
  if (!(RIG.servoRange[8] === 270 && RIG.pulseMax[8] === 2500 && RIG.servoMaxDps[8] === 250))
    fails.push("tiankong35 waist preset did not set the WAIST joint");
  if (RIG.servoRange[9] === 270) fails.push("waist preset leaked into the shrug");
  applyServoPreset("mg90s|shrug");
  if (!(RIG.servoRange[9] === 180 && RIG.pulseMax[9] === 2400))
    fails.push("mg90s shrug preset did not set the SHRUG joint");
  // servo TRAVEL: a 180 servo through 1.2:1 cannot reach a wide joint range,
  // a 270 servo can — and the preset must carry the travel with it.
  RIG.gearPinion = new Array(NJ).fill(15); RIG.gearGear = new Array(NJ).fill(18);
  RIG.min = new Array(NJ).fill(10); RIG.max = new Array(NJ).fill(170);
  RIG.servoRange = new Array(NJ).fill(180);
  const w180 = travelWarning(0);
  RIG.servoRange = new Array(NJ).fill(270);
  const w270 = travelWarning(0);
  if (!w180) fails.push("180 deg servo not flagged as too narrow for a 10-170 joint");
  if (w270) fails.push("270 deg servo wrongly flagged as too narrow: " + w270);
  RIG.min = new Array(NJ).fill(60); RIG.max = new Array(NJ).fill(120);
  RIG.servoRange = new Array(NJ).fill(180);
  if (travelWarning(0)) fails.push("180 deg servo wrongly flagged on a narrow joint");
  applyServoPreset("generic270|sh");
  if (!(RIG.servoRange[0] === 270 && RIG.servoRange[4] === 270))
    fails.push("generic270 preset did not set the shoulders' travel");
  if (RIG.servoRange[2] !== 180)
    fails.push("generic270 preset leaked travel into the elbows");
  // FRAME RATE: presets carry a rate (default 50 Hz for all types now) and a
  // RATE change must hit only its group, not leak elsewhere.
  RIG.frameHz = new Array(NJ).fill(111);
  applyServoPreset("pdi1181mg|sh");
  if (!shIdx.every(i => RIG.frameHz[i] === 50))
    fails.push("pdi1181mg preset did not set 50 Hz on the shoulders");
  if (!elIdx.every(i => RIG.frameHz[i] === 111))
    fails.push("pdi1181mg preset changed the elbows' frame rate");

  RIG.servoMaxDps = save.dps; RIG.pulseMin = save.lo; RIG.pulseMax = save.hi;
  RIG.servoRange = save.rng; RIG.min = save.mn; RIG.max = save.mx;
  RIG.gearPinion = save.gp; RIG.gearGear = save.gg; RIG.frameHz = save.hz;
  rigChanged(); renderRigUI();
  document.title = fails.length
    ? "SERVO FAIL " + fails.join(" | ")
    : `SERVO PASS slowJointStretched=${fastElbow}->${slowElbow}ms otherMoveUnchanged=${shAfter}ms presets=perGroup travel=ok frameRate=default50`;
  console.log(document.title);
}
