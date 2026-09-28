// --- timing ---
// Show speed sets the automatic time; servo max speed sets the PHYSICAL
// floor: a keyframe time can always be made longer, never shorter than
// biggest-delta / max — otherwise the real arm can't reach the pose before
// the next move starts. The firmware applies the same rule (max_dps).
function speedDps() { return Math.max(5, +$("speedDps").value || 120); }
function maxDps() { return Math.max(30, +$("maxDps").value || 400); }
// Each joint can carry a different servo (Setup > rig), so the floor is the
// SLOWEST joint on this move, not one number for the whole arm. The project's
// max °/s field still caps every joint, so it can only make moves safer.
function jointMaxDps(i) {
  return Math.max(30, Math.min(maxDps(), RIG.servoMaxDps[i] || maxDps()));
}
function slowestDps() {
  let s = maxDps();
  for (let i = 0; i < NJ; i++) s = Math.min(s, jointMaxDps(i));
  return s;
}
function deltaDeg(from, to) {
  let dmax = 0;
  for (let i = 0; i < NJ; i++) dmax = Math.max(dmax, Math.abs(to[i] - from[i]));
  return dmax;
}
// The floor AND the reason for it. Typing a faster °/s did nothing and said
// nothing (user 2026-09-23: *when input the deg/s in sequence it not change
// the time for me anymore*) because the peak limit had already won: with the
// board's safe_dps at 60, pi/2 x delta / 60 floors every move at delta/38.2,
// so any speed above about 38 °/s produces the identical time. The number was
// never wrong; it was invisible. Every caller that shows a time to a person
// asks for the reason too.
function minTimeWhy(from, to) {
  // per joint (the slow WAIST servo counts too), the slowest joint wins
  let servo = 0, slowest = 0;
  for (let i = 0; i < NJ; i++) {
    const need = Math.abs(to[i] - from[i]) / jointMaxDps(i);
    if (need > servo) { servo = need; slowest = i; }
  }
  // safety floor, same as firmware nongmath::safeDuration (ease peaks at pi/2 x average)
  const peak = deltaDeg(from, to) * (Math.PI / 2) / Math.max(1, SAFE_DPS);
  const need = Math.max(servo, peak);
  const ms = Math.max(MIN_MOVE_MS, Math.ceil(need * 1000));
  let why = "the 80 ms shortest-move floor", fix = "";
  if (need * 1000 > MIN_MOVE_MS) {
    if (peak >= servo) {
      why = `the robot's peak speed limit, ${SAFE_DPS} °/s`;
      fix = `Above about ${flatDps()} °/s nothing gets faster. Raise ` +
            `Peak speed limit (Timing) to shorten it.`;
    } else {
      why = `${JOINT_LABELS[slowest] || ("joint " + (slowest + 1))} at its ` +
            `servo max, ${Math.round(jointMaxDps(slowest))} °/s`;
      fix = "Raise Servo max, or that joint's servo °/s in Setup > rig.";
    }
  }
  return { ms, why, fix };
}
function minTime(from, to) { return minTimeWhy(from, to).ms; }
// The show speed above which the peak limit decides every safety-limited move.
// pi/2 is the ease curve's peak-to-average ratio, the same one the firmware uses.
function flatDps() { return Math.floor(SAFE_DPS * 2 / Math.PI); }
// A move runs at the sequence's speed unless that keyframe overrides it, so one
// gesture can be slower or snappier than the rest of the show without hand-
// computing its time. Speed and time are two views of the SAME thing: set a
// speed and the time follows; type a time and the override is dropped.
function keyDps(i) {
  const k = keys[i];
  return k && k.dps ? Math.min(k.dps, slowestDps()) : speedDps();
}
function autoTime(from, to, dps) {
  const v = dps || speedDps();
  const t = Math.max(MIN_MOVE_MS, Math.round(deltaDeg(from, to) / v * 1000));
  return Math.max(t, minTime(from, to));
}
function keyMin(i) { // physical minimum for keyframe i (0 = entry, unknown start)
  return i > 0 && keys[i - 1] ? minTime(keys[i - 1].pose, keys[i].pose) : MIN_MOVE_MS;
}
// A speed the servos cannot hold used to be replaced in the box with no word
// said, so it read as *the number will not change*. Say what was kept and why.
// The fastest Show speed that DOES anything. Above the peak limit's flat point
// no move gets shorter, however large the number, so accepting a larger one is
// the box lying (user 2026-09-23: *the show speed can adjust in the save dps*).
// Raise the saved peak limit and this ceiling rises with it - measured on board
// 67: safe_dps 120 -> 76 °/s, safe_dps 190 -> 121 °/s.
function speedCeiling() { return Math.max(5, Math.min(slowestDps(), flatDps())); }
function speedChanged() {
  const asked = speedDps();
  let said = "";
  if (asked > speedCeiling()) {
    const cap = speedCeiling();
    $("speedDps").value = cap;
    said = flatDps() <= slowestDps()
      ? `Show speed kept at ${cap} °/s — above that, the robot's peak speed ` +
        `limit of ${SAFE_DPS} °/s decides every move and nothing gets faster. ` +
        "Raise Peak speed limit and Save to robot to go quicker."
      : `Show speed kept at ${cap} °/s — the slowest servo on this robot ` +
        "cannot go faster. Raise Servo max to allow more.";
  }
  recalcTimes();
  renderTimeline();
  $("tlStat").textContent = said || timingSummary();
}
// One sentence naming the limit that is actually deciding move times now, so
// the answer to *why did my number change nothing* is on the screen and not
// only in a tooltip.
function timingSummary() {
  let peak = 0, servo = 0, free = 0;
  for (let i = 1; i < keys.length; i++) {
    if (!keys[i - 1]) continue;
    const w = minTimeWhy(keys[i - 1].pose, keys[i].pose);
    const auto = Math.max(MIN_MOVE_MS,
      Math.round(deltaDeg(keys[i - 1].pose, keys[i].pose) / keyDps(i) * 1000));
    if (auto >= w.ms) free++;
    else if (w.why.indexOf("peak") >= 0) peak++;
    else servo++;
  }
  if (!peak && !servo) return `every move runs at the speed you set (${speedDps()} °/s)`;
  const bits = [];
  if (peak) bits.push(`${peak} held by the robot's peak speed limit (${SAFE_DPS} °/s — ` +
                      `above about ${flatDps()} °/s nothing gets faster)`);
  if (servo) bits.push(`${servo} held by a servo's own top speed`);
  return `${free} move(s) run at your speed; ` + bits.join(", ") +
         ". Change Peak speed limit or Servo max in Timing to shorten them.";
}
// The peak limit is the Studio's own planning number. It was locked until a
// board was connected, so away from the robot there was no way to make any
// move faster at all (user 2026-09-23: *max servo speed in show i cannot
// adjust anymore*). Editing it re-times the automatic moves here; SAVING it to
// the board is still a separate, connected-only step, because a Studio that
// plans faster than the robot allows would be lying about the show.
function safetyLimitChanged() {
  const want = Math.round(+$("safeDpsInput").value || 0);
  if (!(want >= 5)) { $("safeDpsInput").value = SAFE_DPS; return; }
  // A pinned time is never re-timed, even when it happens to equal the auto one.
  const wasAuto = keys.map((k, i) => i > 0 && keys[i - 1] && !timePinned(i) &&
    k.t === autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  SAFE_DPS = want;
  // Raising the limit raises what Show speed is allowed to be, so the two
  // boxes stay honest about each other. Capped BEFORE re-timing, or the moves
  // were timed at a speed the box no longer shows.
  if (speedDps() > speedCeiling()) $("speedDps").value = speedCeiling();
  for (let i = 1; i < keys.length; i++)
    if (wasAuto[i]) keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  bumpKeys();
  clampKeyTimes();
  renderTimeline();
  $("safeSpeedStat").textContent =
    `Planning at ${want} °/s, so Show speed can now go up to ${speedCeiling()} °/s. ` +
    (boardSafeDpsMax ? "Press Save to robot to make the robot use it too — it "
                       + "takes effect after the board restarts."
                     : "Not saved to any robot — connect first, then Save to robot.");
}
// INFO is the active board value. CFG only saves the NEXT boot's value, so do
// not change SAFE_DPS when the operator presses Save.
function adoptBoardSafety(module) {
  const safe = Number(module && module.safe_dps);
  const speeds = module && module.max_dps;
  const max = Array.isArray(speeds) && speeds.length === NJ
    ? Math.min(...speeds.map(Number)) : 0;
  const input = $("safeDpsInput"), button = $("saveSafeDps");
  if (!(safe >= 5) || !(max >= 5) || !Number.isFinite(max)) {
    boardSafeDpsMax = 0;
    boardSafePeer = 0;
    input.disabled = false;         // still the Studio's own planning number
    button.disabled = true;         // but there is nothing to save it to
    $("safeSpeedStat").textContent = "This board does not report its safety speed, so " +
      `nothing was changed on it. Studio still plans at ${SAFE_DPS} °/s — change it here ` +
      "to make the editor's times shorter.";
    return;
  }
  // Only automatically timed moves shorten. A hand-typed time is the user's
  // choice and must not be silently replaced after reconnecting to a board.
  const wasAuto = keys.map((k, i) => i > 0 && !timePinned(i) && k.t ===
    autoTime(keys[i - 1].pose, k.pose, keyDps(i)));
  const changed = safe !== SAFE_DPS;
  SAFE_DPS = safe;
  boardSafeDpsMax = max;
  boardSafePeer = module.link ? Number(module.peer) || 0 : 0;
  input.disabled = button.disabled = false;
  input.min = 5;
  input.max = Math.floor(max);
  input.value = String(safe);
  if (changed) {
    for (let i = 1; i < keys.length; i++)
      if (wasAuto[i]) keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
    clampKeyTimes();
    renderTimeline();
  }
  $("safeSpeedStat").textContent = `Active peak limit: ${safe} °/s. ` +
    `For safety-limited moves, Show speed above about ${flatDps()} °/s will not shorten ` +
    "them — raise this number and press Save to robot to go faster." +
    (boardSafePeer ? ` Linked board #${boardSafePeer} needs the same limit.` : "");
}
// A TIME TYPED BY HAND IS A DECISION, NOT A CACHE.
//
// User 2026-09-23: *when i already adjust to higer time and i change the move a
// little bit make the time it have the most not recreate the time of the rig
// because i need that move to that time when i change i change it everytime
// make me headace*. Nudging a pose ran the automatic timer over the top of the
// number they had set, so every small correction cost them the timing again.
//
// So a typed time is PINNED (`k.tset`). Nothing that re-times automatically may
// touch it, and nothing may make it shorter. Only clampKeyTimes may raise it,
// and only to the physical minimum - a move the servos cannot do in that time
// is not a choice anybody can make.
//
// Two ways out, both deliberate: type a °/s on that move, or press the pin on
// the time box. Both say "time this one for me again".
function timePinned(i) { return !!(keys[i] && keys[i].tset); }
function pinTime(i) { if (keys[i]) keys[i].tset = true; }
function unpinTime(i) { if (keys[i]) delete keys[i].tset; }
function recalcTimes() {   // keeps each keyframe's own speed override AND its pin
  bumpKeys();
  for (let i = 1; i < keys.length; i++)
    if (!timePinned(i))
      keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();         // a pinned time may still be raised to what is possible
}
// ONE keyframe's predecessor changed (delete / reorder): re-time only it.
// recalcTimes() would silently overwrite every hand-typed time on the line,
// and a typed time wins over the automatic one by design.
function retimeAt(i) {
  bumpKeys();
  if (i >= 1 && keys[i] && !timePinned(i))
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();
}
function clampKeyTimes() { // raise any hand-edited time that fell below the floor
  bumpKeys();
  for (let i = 0; i < keys.length; i++) keys[i].t = Math.max(keys[i].t, keyMin(i));
}
