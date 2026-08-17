"""Clicking a move travels at THAT move's speed, not at drag speed.

Reported from the bench: with the sequence speed set to 60 or 40 deg/s,
clicking a move in the timeline still snapped the arm across at full speed.

Two jobs share one path, and they want different times. A slider DRAG should
follow your hand, so the pose goes out with a time measured from the link's own
round trip (80-300ms) — deliberately quick. Clicking a MOVE is not that: it
should travel the way the move travels in the show, or what you are previewing
is not what will happen. Both went down the drag path, so the move's own speed
was ignored.

Asserted on the WIRE — the T that actually reached the module — because the
editor's opinion of how fast it went is exactly what was wrong.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "clicking a move sends that move's own time, not the drag time"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK " + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    document.getElementById("liveChk").checked = true;   // live link on

    // a slow sequence: three keyframes, a big move, low deg/s
    keys = [];
    [90, 30, 150].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    document.getElementById("speedDps").value = 40;      // slow
    speedChanged();
    recalcTimes();

    var want = Math.round(keyTravelMs(2));
    report("want=" + want);

    setTimeout(function(){
      rawCmd("MOVE QCMARK CLICK");        // marker so the next POSE is ours
      selectKey(2);                        // <- the click under test
      setTimeout(function(){ report("done"); }, 1200);
    }, 400);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
}, 1500); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = fake_serial.qc_marks
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    want = next((int(m[5:]) for m in marks if m.startswith("want=")), None)
    if not t.ok(want, "the driver reported the move's own time",
                "marks: %r" % (marks[-4:],)):
        return
    t.ok(want > 400,
         "and at 40 deg/s that move is genuinely slow (%d ms)" % want,
         "a fast move would prove nothing — drag time is 80-300ms")

    # the POSE that followed the click, off the wire
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK CLICK")
    except ValueError:
        t.ok(False, "the click marker reached the module", wire[-4:])
        return
    after = [c for c in wire[i + 1:] if c.upper().startswith("POSE ")]
    if not t.ok(after, "clicking the move sent a pose", wire[i + 1:][:4]):
        return

    m = re.search(r"\bT\s+(\d+)", after[0])
    if not t.ok(m, "it carries a travel time", after[0]):
        return
    got = int(m.group(1))
    t.ok(abs(got - want) <= max(60, want * 0.15),
         "at the move's own speed (%d ms, wanted %d)" % (got, want),
         "the arm was sent at drag speed and ignored the sequence's deg/s")
    t.ok(got > 300,
         "which is slower than the drag path could ever send (%d ms)" % got,
         "80-300ms is the live-drag range: this went out as a drag")

    # and the two paths are still distinct in the source
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "function keyTravelMs",
               "the move's own time is worked out from the played timeline")
    t.contains(app, "poseChanged(false, keyTravelMs(i))",
               "and clicking a keyframe uses it")
    t.contains(app, "else sendPoseLive();",
               "while a drag still follows the hand")
