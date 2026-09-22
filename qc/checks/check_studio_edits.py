"""Editing the timeline in the REAL browser must not rewrite hand-typed times.

recalcTimes() used to run on every structural edit (delete, duplicate, move),
silently overwriting every time somebody had typed by hand — a typed time wins
over the automatic one by design, so that was data loss with no error. The
fix re-times only the keyframes whose predecessor actually changed — which,
for a MOVE, includes the keyframe after the swapped pair.

The same driver proves three more edits: Pause and switching to Monitor both
end the HUB's clock even when Live is unticked (a show started live-linked
keeps running after the tick is removed — an early return left it playing),
and a project round-trip keeps its sequence chain (`seqNext`).

It asserts on page state via marks and on what the hub itself reports
(GET /api/play), not on what the UI says about itself.
"""
import json
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "timeline edits keep hand-typed times; pause/monitor end the hub show"
SLOW = True

DRIVER = """
function step(){
    

  try{

    if (typeof addKey !== "function" || !document.getElementById("liveChk"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");
    run();
  }catch(e){ qcFail(e); }
}
async function run(){
  try{
    // five keyframes so every edit has an UNAFFECTED witness further down
    pose = pose.map(function(){ return 60; });  addKey();
    pose = pose.map(function(){ return 120; }); addKey();
    pose = pose.map(function(){ return 90; });  addKey();
    pose = pose.map(function(){ return 30; });  addKey();
    pose = pose.map(function(){ return 45; });  addKey();

    // ---- DELETE: only the keyframe after the gap may be re-timed.
    keys[1].t = 5000; bumpKeys();               // the hand-typed time
    selKey = 2; delKey();
    qcMark("del-kept-" + (keys[1].t === 5000));

    // ---- DUPLICATE: nothing changes predecessor poses anywhere on the line,
    // so NO time at all may move.
    dupKey();                                    // selKey was 1 -> copies to 2
    qcMark("dup-kept-" + (keys[2] && keys[2].t === 5000 && keys[1].t === 5000));

    // ---- MOVE: the swapped pair AND the keyframe after them re-time; the
    // witness below them does not. The pair must be two DIFFERENT poses or
    // the swap is a no-op and proves nothing.
    pose = pose.map(function(){ return 60; });  addKey();   // 6th keyframe
    keys[5].t = 7000; bumpKeys();                // witness AFTER the trio
    selKey = 3;                                  // swaps 30 and 120-dup
    moveKey(-1);
    var followOk = keys[4].t === autoTime(keys[3].pose, keys[4].pose, keyDps(4));
    qcMark("move-follower-" + followOk);
    qcMark("move-kept-" + (keys[5].t === 7000));

    // ---- PAUSE with Live unticked still ends the hub's clock.
    document.getElementById("liveChk").checked = true;
    var started = await hubPlay(0);
    await new Promise(function(r){ setTimeout(r, 400); });
    var st = await (await fetch("/api/play")).json();
    qcMark("show-started-" + (started && st.running));
    document.getElementById("liveChk").checked = false;
    livePause();                                 // Live is OFF here on purpose
    await new Promise(function(r){ setTimeout(r, 500); });
    st = await (await fetch("/api/play")).json();
    qcMark("pause-hub-stopped-" + !st.running);

    // ---- switching to MONITOR ends it too (same hub-clock trap).
    document.getElementById("liveChk").checked = true;
    await hubPlay(0);
    await new Promise(function(r){ setTimeout(r, 400); });
    document.getElementById("monChk").checked = true;
    monitorChanged();
    await new Promise(function(r){ setTimeout(r, 500); });
    st = await (await fetch("/api/play")).json();
    qcMark("monitor-hub-stopped-" + !st.running);

    // ---- the chain survives a save / load round trip.
    document.getElementById("monChk").checked = false;
    monitorChanged();
    document.getElementById("seqNext").value = "part_two";
    document.getElementById("projName").value = "qc_chain_proj";
    window.confirm = function(){ return false; };   // keep the rig on screen
    await saveProject();
    document.getElementById("seqNext").value = "";
    await loadProject("qc_chain_proj.json");
    qcMark("chain-restored-" +
           (document.getElementById("seqNext").value === "part_two"));
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=26)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)
    t.contains(marks, "connected", "Studio connected over USB")
    for want, label in (
        ("del-kept-true", "deleting one keyframe keeps other hand-typed times"),
        ("dup-kept-true", "duplicating moves no time on the line"),
        ("move-follower-true", "moving re-times the keyframe after the pair"),
        ("move-kept-true", "moving a keyframe leaves later times alone"),
        ("show-started-true", "the hub show was running before the pause"),
        ("pause-hub-stopped-true",
         "Pause ends the hub's show even with Live unticked"),
        ("monitor-hub-stopped-true",
         "switching to Monitor ends the hub's show too"),
        ("chain-restored-true", "a project reloads with its sequence chain"),
    ):
        t.contains(marks, want, label)

    _safety_speed(t, base)


SAFETY_DRIVER = """
function waitForSafety(){
  if (typeof saveSafetySpeed !== "function" || !haveUsb() ||
      document.getElementById("safeDpsInput").disabled)
    return setTimeout(waitForSafety, 150);
  testSafety().catch(qcFail);
}
async function testSafety(){
  const input = document.getElementById("safeDpsInput");
  const stat = document.getElementById("safeSpeedStat");
  const p0 = Array(NJ).fill(90), p1 = Array(NJ).fill(120);
  keys = [{pose:p0, t:80}, {pose:p1, t:0}, {pose:p0, t:7000}];
  keys[1].t = autoTime(p0, p1, speedDps());
  const oldTime = keys[1].t;
  qcMark("active-" + SAFE_DPS + "-floor-" + oldTime);

  input.value = "300";                     // board's slowest servo max is 200
  await saveSafetySpeed();
  qcMark("high-rejected-" + stat.textContent.includes("5 to 200"));
  input.value = "120";
  window.confirm = function(){ return false; };
  await saveSafetySpeed();
  qcMark("cancelled-" + (SAFE_DPS === 60));
  window.confirm = function(){ return true; };
  await saveSafetySpeed();
  qcMark("saved-pending-" + (SAFE_DPS === 60 && keys[1].t === oldTime &&
    stat.textContent.includes("Restart the board")));

  // The next boot reports the new active limit. Auto times may shorten;
  // hand-typed times must not be lost on this reconnect.
  adoptBoardSafety({safe_dps:120, max_dps:Array(NJ).fill(200), link:true, peer:85});
  qcMark("reboot-retimed-" + (SAFE_DPS === 120 && keys[1].t < oldTime &&
    keys[2].t === 7000));
  qcMark("done");
}
window.addEventListener("load", function(){ setTimeout(waitForSafety, 1200); });
"""


def _safety_speed(t, base):
    # Give this fake the same INFO fields and CFG reply the real board has.
    # The browser still sends through the hub; assert on fake_serial.wire.
    fake_serial.reset()
    board = fake_serial.NONG
    old_info, old_line = board.info, board.line

    def info():
        s = json.loads(old_info())
        s["module"].update(safe_dps=60, max_dps=[200] * 10, link=True, peer=85)
        return json.dumps(s)

    def line(cmd):
        reply = old_line(cmd)
        if cmd.startswith("CFG safe_dps "):
            return "OK safe_dps=%s (reboot to apply)" % cmd.split()[-1]
        return reply

    board.info, board.line = info, line
    try:
        browser.page(SAFETY_DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=20)
        marks = list(fake_serial.qc_marks)
        sent = [c for _, c in fake_serial.wire if c.startswith("CFG safe_dps ")]
        t.ok(not any(m.startswith("ERROR") for m in marks),
             "safety control ran without throwing", marks)
        for want, label in (
            ("active-60-floor-786", "the connected board's 60 dps cap sets the floor"),
            ("high-rejected-true", "values above the board's servo max are rejected"),
            ("cancelled-true", "cancel leaves the active cap alone"),
            ("saved-pending-true", "saving does not pretend the new cap is active"),
            ("reboot-retimed-true", "reconnect shortens auto times but keeps hand-typed time"),
        ):
            t.contains(marks, want, label)
        t.eq(sent, ["CFG safe_dps 120"],
             "only the confirmed safety speed reaches the board")
    finally:
        board.info, board.line = old_info, old_line
        browser.kill()
