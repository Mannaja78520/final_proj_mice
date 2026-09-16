"""Clicking a move also moves the SHOW CLOCK to that move's time.

Asked 2026-08-22: *when click on the move in nong studio go to the time which
have that move too*. selectKey() already travelled to the pose at the move's
own speed (check_key_click) but left playT alone, so Play and the scrubber
carried on from wherever they were — the next play started at a different
point in the show than the one on screen.

The clock must land at the START of that keyframe's own segment: the sum of
the moves before it over the PLAYED timeline (holds counted, suspended
keyframes skipped exactly as playback skips them), so pressing Play plays THAT
move, at THAT move's speed.

Asserted on the WIRE for the play half — which pose the module was asked for,
and with what T — not on what the page claims. Through the hub the show is
driven by ShowPlayer (from_ms seek), so the segments that reach the module are
the hub's; they prove the same thing.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "clicking a move parks the play clock at that move"
SLOW = True

T1, H1, T2, H2, T3, T4 = 1000, 200, 1500, 300, 800, 900
START3 = T1 + H1 + T2 + H2            # clock when the move INTO keyframe 3 begins
TOTAL = START3 + T3 + T4

DRIVER = """
function step(){
  try{
    if (typeof addKey !== "function" || !document.getElementById("liveChk"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    document.getElementById("loopChk").checked = false;
    document.getElementById("liveChk").checked = true;
    liveChanged();
    keys = [];                                  // drop the boot keyframe
    pose = pose.map(function(){ return 60; });  addKey();
    pose = pose.map(function(){ return 120; }); addKey();
    pose = pose.map(function(){ return 90; });  addKey();
    pose = pose.map(function(){ return 30; });  addKey();
    pose = pose.map(function(){ return 75; });  addKey();
    keys[1].t = %d; keys[1].hold = %d;
    keys[2].t = %d; keys[2].hold = %d;
    keys[3].t = %d; keys[3].hold = 0;
    keys[4].t = %d; keys[4].hold = 0;

    // ---- phase A: click move 3 — the clock jumps to where that move begins
    selectKey(3);
    qcMark("A-playT=" + Math.round(playT));
    qcMark("A-scrub=" + document.getElementById("scrub").value);

    // ---- phase B: suspend move 2 and click move 3 again — the sum walks only
    // the PLAYED list, skipping the gap exactly as playback skips it
    keys[2].off = true; bumpKeys();
    selectKey(3);
    qcMark("B-playT=" + Math.round(playT));
    keys[2].off = false; bumpKeys();

    // ---- phase C: click move 3, press Play — the module is asked for move 3
    // at move 3's own time, then the show moves FORWARD, never restarting.
    // Let the link drain first: ONE clock rules this robot, and a queued
    // travel POSE landing after Play would legitimately take the show over.
    // Cleanup pauses ONLY if still playing — the page's preview clock stops
    // itself at the end, and toggling then would START a second show.
    setTimeout(function(){
      selectKey(3);
      rawCmd("MOVE QCMARK CLOCK");
      setTimeout(function(){
        togglePlay();
        setTimeout(function(){
          qcMark("done");
          if (playing) togglePlay();
        }, 3200);
      }, 700);
    }, 900);
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % (T1, H1, T2, H2, T3, T4)


def pose_of(cmd):
    m = re.match(r"POSE\s+(\S+)", cmd)
    return float(m.group(1)) if m else None


def t_of(cmd):
    m = re.search(r"\bT\s+(\d+)", cmd)
    return int(m.group(1)) if m else None


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

    # ---- A: the clock sits where move 3 begins, and the scrubber followed
    got_a = next((int(m.split("=")[1]) for m in marks if m.startswith("A-playT=")), None)
    t.eq(got_a, START3, "clicking move 3 puts playT at the sum of the moves before it")
    got_s = next((int(m.split("=")[1]) for m in marks if m.startswith("A-scrub=")), None)
    t.eq(got_s, round(START3 / TOTAL * 1000),
         "and the scrubber moved with it (%d/1000)" % round(START3 / TOTAL * 1000))
    if got_a != START3:
        t.ok(False, "clock did not follow the click — stopping here", marks[-6:])
        return

    # ---- B: a suspended keyframe is skipped by the SUM, as playback skips it
    got_b = next((int(m.split("=")[1]) for m in marks if m.startswith("B-playT=")), None)
    t.eq(got_b, T1 + H1,
         "with move 2 suspended the clock lands where the show jumps the gap")

    # ---- C: what reached the module after clicking 3 and pressing Play.
    # Only whole-segment sends count (T above the 80-300 ms drag window) — the
    # command queue can lag, so a stray drag pose says nothing here.
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK CLOCK")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    segs = [c for c in wire[i + 1:]
            if c.upper().startswith("POSE ") and (t_of(c) or 0) > 350]
    if not t.ok(segs, "playing from move 3 sent whole-move commands",
                [c for c in wire[i + 1:] if c.upper().startswith("POSE")][:4]):
        return
    p0, t0 = pose_of(segs[0]), t_of(segs[0])
    t.ok(p0 == 30.0 and abs(t0 - T3) <= 60,
         "the show started AT MOVE 3, at ITS OWN time (%s ms of %d)"
         % (t0, T3), segs[0])
    nxt = [c for c in segs[1:] if pose_of(c) == 75.0]
    t.ok(nxt and abs((t_of(nxt[0]) or 0) - T4) <= 60,
         "then moved FORWARD into move 4 — not a restart from the top",
         segs[:4])
    wrong = [c for c in segs if pose_of(c) in (60.0, 120.0, 90.0)]
    t.ok(not wrong, "no move from BEFORE the click was replayed", wrong[:2])
