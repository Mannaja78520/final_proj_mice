"""Playback in the REAL browser: Play, Pause, resume, and holds.

This has to be a real browser driving the real app — the bugs it guards were
all in how the page's animation loop decides what to send, and a python
re-implementation of that logic would have happily agreed with itself.

It asserts on what reached the module, not on what the UI says about itself.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "play / pause / hold over the cable"
SLOW = True

MOVE, HOLD = 2000, 1200        # respects the actual calibrated servo minimum

DRIVER = """
async function step(){
    

  try{

    if (typeof addKey !== "function" || !document.getElementById("liveChk"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");
    document.getElementById("loopChk").checked = false;
    document.getElementById("liveChk").checked = true;
    liveChanged();
    pose = pose.map(function(v,j){ return clampJ(j,60); });  addKey();
    pose = pose.map(function(v,j){ return clampJ(j,120); }); addKey();
    pose = pose.map(function(){ return 90; });  addKey();
    keys.forEach(function(k,i){ if(i){ k.t = %d; k.hold = %d; } });
    qcMark("timeline-" + keys.map(function(k){ return Math.round(k.pose[0]); }).join("_"));
    playT = 0;
    await togglePlay();
    qcMark("playing");
    // The show clock starts once the arm has reached keyframe 0 (A26-50), so
    // the pause is timed from THEN - mid second move, then resume.
    (function afterEntry(){
      if (typeof entryHold !== "undefined" && entryHold) return setTimeout(afterEntry, 20);
      qcMark("entry-done-at-" + Math.round(playT));
      setTimeout(function(){ qcMark("pause"); togglePlay(); }, %d);
      setTimeout(function(){ qcMark("resume"); togglePlay(); }, %d);
      setTimeout(function(){ qcMark("done"); }, %d + 4000);
    })();
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % (MOVE, HOLD, MOVE + HOLD + MOVE // 2, MOVE + HOLD + MOVE // 2 + 1500,
       MOVE + HOLD + MOVE // 2 + 1500)


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    fake_serial.NONG.motion_clock = True
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=26)

    marks = fake_serial.qc_marks
    poses = fake_serial.poses()
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)
    t.contains(marks, "connected", "Studio connected over USB")
    t.contains(marks, "playing", "Play started")
    if not poses:
        t.ok(False, "PLAY SENT NOTHING — the robot cannot follow the editor",
             "this is the WiFi-only-gate regression")
        return

    line = next((m for m in marks if m.startswith("timeline-")), "")
    timeline = line[len("timeline-"):].split("_") if line else []
    sent = [p[1][0] for p in poses]

    # ---- keyframe 0 is a move nobody makes: segments are the moves INTO a
    # keyframe, so without an explicit send the robot starts from wherever
    # it happens to be standing.
    if timeline:
        t.eq(sent[0], timeline[0], "keyframe 0 is sent when Play starts")
        # Checked resume first returns from the reported stop position to the
        # parked timeline pose; the remaining native timeline follows it.
        timeline_values = set(timeline)
        walked = [v for i, v in enumerate(sent) if v in timeline_values and
                  (i == 0 or v != sent[i - 1])]
        t.eq(walked, timeline, "the robot walks the whole timeline in order")

    t.ok(all(p[2] for p in poses), "every move carries an explicit T",
         [p[2] for p in poses])

    # ---- HOLD must happen BETWEEN the moves. If segmentAt() forgets its
    # "in a hold" branch, the next move goes out the instant the hold begins,
    # the arm arrives early, and all the waiting piles up at the END.
    stamps = [p[0] for p in poses]
    # The first POSE is the travel INTO keyframe 0, timed by the board - not a
    # move + hold, so its gap is checked on its own.
    entry_t = poses[0][2] or 0
    if len(stamps) > 1:
        t.ok(stamps[1] - stamps[0] >= entry_t * 0.9,
             "the first move waits for the arm to reach keyframe 0",
             "gap %d ms, entry move T %d" % (stamps[1] - stamps[0], entry_t))
    # The page polls entryHold every 20 ms, so it can see the clock one frame
    # (~16 ms) after release: entry-done-at-16/17 in two gates, 2026-09-22.
    # Running ahead through the entry move would read hundreds of ms.
    done = [int(m.rsplit("-", 1)[1]) for m in marks
            if m.startswith("entry-done-at-") and m.rsplit("-", 1)[1].isdigit()]
    t.ok(done and done[0] <= 50,
         "and the preview clock waited for it too, instead of running ahead",
         [m for m in marks if m.startswith("entry-done")])
    pause_at = next((ms for ms,c in fake_serial.wire if c.endswith('QCMARK pause')), float('inf'))
    # Measure the uninterrupted completed move before Pause. A resumed move
    # has a shorter remaining duration; checked entry is not a timeline hold.
    sixty = next((p for p in poses if float(p[1][0]) == 60 and p[0] < pause_at), None)
    following = next((p for p in poses if sixty and p[0] > sixty[0] and
                      float(p[1][0]) == 120 and p[0] < pause_at), None)
    if t.ok(sixty and following, "there are uninterrupted moves to measure", poses):
        worst = following[0] - sixty[0]
        t.ok(worst > (sixty[2] + HOLD) * 0.85,
             "a hold really waits between the moves",
             "shortest gap %d ms, expected ~%d (move %d + hold %d)"
             % (worst, MOVE + HOLD, MOVE, HOLD))

    # ---- PAUSE. A segment is handed to the module as one whole move which it
    # interpolates itself, so pausing the editor does NOT stop the arm — only
    # STOP does. And resuming must ask for the time that is LEFT, or the arm
    # replays the whole segment while the editor plays only its tail.
    cmds = [c for _, c in fake_serial.wire]
    t.ok(any(c.upper() == "STOP" for c in cmds),
         "Pause sends STOP — otherwise the arm finishes the move anyway", cmds[:12])
    resume = next((i for i,c in enumerate(cmds) if c.endswith('QCMARK resume')), -1)
    if resume >= 0:
        i = resume
        after = [c for c in cmds[i + 1:] if c.upper().startswith("POSE")]
        if t.ok(len(after)>=2, "checked entry and playback continue after a resume"):
            left = int(after[1].split(" T ")[1]) if " T " in after[1] else 0
            t.ok(0 < left < MOVE,
                 "resume asks only for the time still left in the segment",
                 "asked for T=%s of a %d ms move" % (left, MOVE))
    else:
        t.ok(False, "resume marker reached the wire", cmds[-8:])

    # ---- RESUME INSIDE A HOLD (A26-50). The hub skipped what was left of the
    # hold and sent the next move at once, so the arm ran ahead of the preview.
    import time
    fake_serial.reset()
    steps = [{"pose": [90] * 10, "t": 80, "hold": 0},
             {"pose": [60] * 10, "t": MOVE, "hold": HOLD},
             {"pose": [120] * 10, "t": MOVE, "hold": 0}]
    at = MOVE + 200                       # 200 ms into the 1200 ms hold
    t0 = time.time()
    st = main.show.start("usb:%s" % fake_serial.PORT, steps, from_ms=at)
    t.ok(st.get("entering") is False,
         "a resume past keyframe 0 does not claim to be travelling there", st)
    while main.show.running() and not fake_serial.poses():
        time.sleep(0.02)
    waited = (time.time() - t0) * 1000
    main.show.stop()
    t.ok(waited >= (HOLD - 200) * 0.85,
         "a resume inside a hold waits what is left of it before the next move",
         "next move after %d ms, %d ms of hold were left" % (waited, HOLD - 200))
    st = main.show.start("usb:%s" % fake_serial.PORT, steps)
    t.ok(st.get("entering") is True,
         "a play from the start says it is travelling to keyframe 0", st)
    main.show.stop()
