// --- sliders ---
function renderSliders() {
  const box = $("sliders");
  if (!box.dataset.built) {
    box.dataset.built = 1;
    JOINT_LABELS.forEach((label, i) => {
      const row = document.createElement("div");
      row.className = "jrow"; row.id = "jrow" + i;
      const name = document.createElement("span");
      name.className = "jname"; name.textContent = label;
      const slider = document.createElement("input");
      slider.type = "range"; slider.min = 0; slider.max = 180; slider.step = 0.5;
      slider.id = "js" + i;
      const num = document.createElement("input");
      num.type = "number"; num.min = 0; num.max = 180; num.id = "jn" + i;
      slider.oninput = () => { pose[i] = clampJ(i, +slider.value); poseChanged(true); };
      slider.onchange = () => poseChanged(false);
      num.onchange = () => { pose[i] = clampJ(i, +num.value); poseChanged(false); };
      row.append(name, slider, num);
      box.appendChild(row);
    });
  }
  // Only write what actually CHANGED. This runs on every frame of playback,
  // and it used to set six properties per joint every time — sixty DOM writes
  // a frame, of which the min/max were the same numbers as the frame before.
  // Setting min/max on a range input makes the browser re-validate and clamp
  // its value, so those were the expensive ones. At ~76 ticks a second that
  // was roughly 4500 writes a second, and it is why playback felt heavy and
  // the page froze when it had anything else to do.
  const sel = selPair >= 0 ? PAIRS[selPair].joints : [];
  for (let i = 0; i < NJ; i++) {
    const js = $("js" + i), jn = $("jn" + i);
    const inPair = sel.includes(i);
    if (_lastSel[i] !== inPair) {
      _lastSel[i] = inPair;
      $("jrow" + i).classList.toggle("sel", inPair);
    }
    if (_lastMin[i] !== RIG.min[i]) { _lastMin[i] = js.min = jn.min = RIG.min[i]; }
    if (_lastMax[i] !== RIG.max[i]) { _lastMax[i] = js.max = jn.max = RIG.max[i]; }
    // one decimal is all a servo can act on, and it keeps this from writing
    // on every frame while a value creeps by a thousandth of a degree
    const v = Math.round(pose[i] * 10) / 10;
    if (_lastVal[i] !== v) {
      _lastVal[i] = v;
      if (document.activeElement !== js) js.value = v;
      if (document.activeElement !== jn) jn.value = v;
    }
  }
}
// what the slider row is currently showing, so an unchanged value is not
// written again. Rig edits and rebuilds clear these through renderSliders().
const _lastVal = new Array(NJ).fill(NaN);
const _lastMin = new Array(NJ).fill(NaN);
const _lastMax = new Array(NJ).fill(NaN);
const _lastSel = new Array(NJ).fill(null);

// XYZ readout of the important joints (mm, robot frame: origin torso center)
// vertical layout so long numbers never overflow the card
function renderXyz() {
  const k = fkPoints(pose);
  const f = (p) => `(${Math.round(p.x)}, ${Math.round(p.y)}, ${Math.round(p.z)})`;
  $("jointXyz").textContent =
    "Left:\n" +
    "  shoulder " + f(k.shL) + "\n" +
    "  elbow    " + f(k.elL) + "\n" +
    "  wrist    " + f(k.wrL) + "\n" +
    "Right:\n" +
    "  shoulder " + f(k.shR) + "\n" +
    "  elbow    " + f(k.elR) + "\n" +
    "  wrist    " + f(k.wrR);
  // keep the editable wrist-target boxes in sync while not being typed in
  [["L", k.wrL], ["R", k.wrR]].forEach(([s, p]) => {
    ["x", "y", "z"].forEach(ax => {
      const el = $("tgt" + s + ax);
      if (el && document.activeElement !== el) el.value = Math.round(p[ax]);
    });
  });
}

// type a wrist target XYZ -> IK moves the whole arm there (then Add keyframe
// to put it into the sequence).
// The solver is a local tracker (that is why dragging works so well: the
// target only ever moves a little). So for a typed target we WALK the
// target from the current wrist position in small steps — same as a drag —
// instead of jumping, which strands the solver in a dead end.
function gotoXyz(arm) {
  const s = arm === 0 ? "L" : "R";
  const t = new THREE.Vector3(+$("tgt" + s + "x").value || 0,
                              +$("tgt" + s + "y").value || 0,
                              +$("tgt" + s + "z").value || 0);
  const wrKey = arm === 0 ? "wrL" : "wrR";
  let best = [...pose], bestErr = Infinity;
  const tryWalk = () => {
    const start = fkPoints(pose)[wrKey];
    const steps = Math.min(60, Math.max(6, Math.ceil(start.distanceTo(t) / 12)));
    for (let i = 1; i <= steps; i++)
      solveIK(arm, start.clone().lerp(t, i / steps), 6);
    solveIK(arm, t, 25); // final polish
    const err = fkPoints(pose)[wrKey].distanceTo(t);
    if (err < bestErr) { bestErr = err; best = [...pose]; }
    return err;
  };
  if (tryWalk() > 10) {
    // stuck? retry once from the neutral pose (different basin)
    const idx = arm === 0 ? [0, 1, 2, 3] : [4, 5, 6, 7];
    idx.forEach(j => pose[j] = RIG.neutral[j]);
    tryWalk();
  }
  pose = best;
  poseChanged(false);
  const got = fkPoints(pose)[wrKey];
  const err = Math.round(bestErr);
  $("tlStat").textContent = (arm === 0 ? "left" : "right") +
    ` wrist moved to (${Math.round(got.x)}, ${Math.round(got.y)}, ${Math.round(got.z)})` +
    (err > 10 ? ` — target is ${err} mm out of reach, this is the closest pose` : " ✓");
}

let liveTimer = 0, colTimer = 0;
function poseChanged(throttled, liveMs) {
  applyPose();
  renderSliders();
  const now = performance.now();
  if (!throttled || now - colTimer > 150) { // live crash warning + XYZ readout
    colTimer = now;
    $("collideWarn").style.display = collisionAt(pose) ? "block" : "none";
    renderXyz();
  }
  // No time throttle here: sendPoseLive() keeps one command in flight and
  // always carries the newest pose, so it paces itself to the link AND cannot
  // drop the value the drag ended on. See sendPoseLive().
  // Two different jobs, two different times.
  //
  // A DRAG follows your hand: sendPoseLive() carries a time measured from the
  // link's own round trip so the arm keeps up with the slider.
  //
  // Clicking a MOVE in the timeline is not that. It should travel the way the
  // move travels — at the speed set for that move, or the sequence's — so what
  // you see is what the show will do. Sending it down the drag path made the
  // arm snap there at full speed however slow the move was set to be.
  if ($("liveChk").checked) {
    if (liveMs > 0) liveSend("POSE " + pose.map(fmtA).join(" ") + " T " + Math.round(liveMs));
    else sendPoseLive();
  }
}

function setNeutral() { pose = [...RIG.neutral]; poseChanged(false); }
async function neutralFromPose() { // the start pose: saved here AND on the robot
  RIG.neutral = [...pose];
  saveRig();
  renderRigUI();                      // the start° column shows the new numbers
  const shown = RIG.neutral.map(Math.round).join(" ");
  // Sent as ONE whole-pose line, not ten. Until 2026-09-10 this only ever saved
  // in the browser, so the editor and the robot disagreed about where home was
  // and nothing on the page said so.
  // Any link will do, exactly as "send rig" decides. liveLinked() was wrong
  // here: it also requires the live-follow tick, so with that off the button
  // saved in the browser and quietly sent the robot nothing.
  if (!haveUsb() && !haveWifi()) {
    $("tlStat").textContent = "start pose = " + shown +
      " — saved here. Connect the robot and press Send rig to give it these.";
    return;
  }
  try {
    const r = await rawCmd("NEUTRAL " + RIG.neutral.map(fmtA).join(" "));
    $("tlStat").textContent = /^ERR/i.test(r || "")
      ? "the robot did not take the start pose: " + r
      : "start pose = " + shown + " — the robot will start here from now on. "
        + "Press Home to move there.";
  } catch (e) {
    $("tlStat").textContent = "saved here, but it did not reach the robot: "
      + (e.message || e);
  }
}
function mirrorLR() {
  // swap the arms; flip the waist to the other side (reflect about 90); the
  // shrug lifts both shoulders equally so it is unchanged.
  pose = [pose[4], pose[5], pose[6], pose[7], pose[0], pose[1], pose[2], pose[3],
          clampJ(8, 180 - pose[8]), pose[9]];
  poseChanged(false);
}
