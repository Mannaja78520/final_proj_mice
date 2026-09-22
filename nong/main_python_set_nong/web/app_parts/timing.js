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
function minTime(from, to) {
  // per joint (the slow WAIST servo counts too), the slowest joint wins
  let need = 0;
  for (let i = 0; i < NJ; i++)
    need = Math.max(need, Math.abs(to[i] - from[i]) / jointMaxDps(i));
  // safety floor, same as firmware nongmath::safeDuration (ease peaks at pi/2 x average)
  need = Math.max(need, deltaDeg(from, to) * (Math.PI / 2) / Math.max(1, SAFE_DPS));
  return Math.max(MIN_MOVE_MS, Math.ceil(need * 1000));
}
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
function speedChanged() {
  if (speedDps() > slowestDps()) $("speedDps").value = slowestDps();
  recalcTimes();
  renderTimeline();
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
    input.disabled = button.disabled = true;
    $("safeSpeedStat").textContent = "This board does not report its safety speed. No setting was changed.";
    return;
  }
  // Only automatically timed moves shorten. A hand-typed time is the user's
  // choice and must not be silently replaced after reconnecting to a board.
  const wasAuto = keys.map((k, i) => i > 0 && k.t ===
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
  const flat = Math.floor(safe * 2 / Math.PI);
  $("safeSpeedStat").textContent = `Active peak limit: ${safe} °/s. ` +
    `For safety-limited moves, Show speed above about ${flat} °/s will not shorten them.` +
    (boardSafePeer ? ` Linked board #${boardSafePeer} needs the same limit.` : "");
}
function recalcTimes() {   // keeps each keyframe's own speed override
  bumpKeys();
  for (let i = 1; i < keys.length; i++)
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
}
// ONE keyframe's predecessor changed (delete / reorder): re-time only it.
// recalcTimes() would silently overwrite every hand-typed time on the line,
// and a typed time wins over the automatic one by design.
function retimeAt(i) {
  bumpKeys();
  if (i >= 1 && keys[i])
    keys[i].t = autoTime(keys[i - 1].pose, keys[i].pose, keyDps(i));
  clampKeyTimes();
}
function clampKeyTimes() { // raise any hand-edited time that fell below the floor
  bumpKeys();
  for (let i = 0; i < keys.length; i++) keys[i].t = Math.max(keys[i].t, keyMin(i));
}
