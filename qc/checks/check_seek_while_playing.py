"""Clicking a move while the show plays never swings the arm back or doubles up.

Reported 2026-09-16 (SAFETY): *when play and click to the position, it go to
the pose before it and then run in sequence ... servo instance move and then
make my robot broke*. selectKey() parked the clock at the START of the clicked
move and left play running, so the show replayed from the pose before - and a
hub-driven show kept running on its own clock beside the click's move.

Asserted on the WIRE (what reached the module), with the hub playing:
  * the click stops the old show: the move it was about to send never comes;
  * the arm travels to the clicked pose at the show's speed, not drag speed;
  * the show then carries on with the move AFTER the clicked one.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "clicking a move during play travels there safely and carries on"
SLOW = True

# four clearly different poses, a slow show, so every move is on the wire
DRIVER = """
function report(s){ rawCmd("MOVE QCMARK SEEK~" + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    document.getElementById("liveChk").checked = true;
    keys = [];
    [90, 40, 140, 60].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    document.getElementById("speedDps").value = 60;
    speedChanged(); recalcTimes();
    // the arm stands at 60 (the last pose added); a click at the START of the
    // time bar jumps it to 90 - a jump, not a drag
    scrubTo(0);
    selectKey(0);
    report("hub=" + (hubDriven() ? 1 : 0));
    setTimeout(function(){
      togglePlay();                            // the hub plays the show
      // late in move 2 (40 -> 140), when the arm is FAR from pose 40, click
      // move 1: its own time (833 ms) is then too fast for the distance
      var at = keyStartMs(2) + keyTravelMs(2) * 0.8;
      setTimeout(function(){
        selectKey(1);                          // <- the click under test
        report("clicked");
        setTimeout(function(){ report("done"); }, 6000);
      }, at + 300);
    }, 2500);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
}, 1500); });
"""


def _poses(wire):
    out = []
    for ms, c in wire:
        m = re.match(r"POSE\s+([\d.]+)(?:\s+[\d.]+)*\s+T\s+(\d+)", c.strip(), re.I)
        if m:
            out.append((ms, round(float(m.group(1))), int(m.group(2))))
    return out


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    F.login(base)
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=40)

    marks = [m for m in fake_serial.qc_marks if m.startswith("SEEK~")]
    bad = [m for m in marks if "ERR-" in m]
    if not t.ok(marks and not bad, "the driver ran without throwing", marks[-3:]):
        return
    t.ok("SEEK~hub=1" in marks, "the show is played by the hub, as on the bench", marks)

    poses = _poses(fake_serial.wire)
    seq = [p for _ms, p, _t in poses]
    first = poses[0] if poses else None
    t.ok(first and first[1] == 90 and first[2] >= 400,
         "a jump along the time bar travels at show speed, not drag speed",
         "30 deg at 60 deg/s is 500 ms; drag time 80-300 ms swings the servo: %r"
         % (first,))
    # the show got as far as move 2 (140) before the click
    if not t.ok(140 in seq, "the hub was playing the show", seq):
        return
    i140 = seq.index(140)
    after = poses[i140 + 1:]
    t.ok(after and after[0][1] == 40,
         "the click sent the arm to the clicked pose (40)",
         [p for _m, p, _t in after[:4]])
    if not after:
        return
    click_t = after[0][2]
    t.ok(click_t >= 1100,
         "at the show's speed from where the arm was (T %d ms)" % click_t,
         "about 80 deg at 60 deg/s needs ~1300 ms; the move's own 833 ms is a lunge")
    nxt = [p for _m, p, _t in after[1:]]
    t.ok(60 not in nxt[:1],
         "the old show did not carry on over the click (no 60 next)", nxt[:4])
    t.ok(nxt[:1] == [140],
         "the show carries on with the move AFTER the clicked one (140)", nxt[:4])
    t.ok(90 not in nxt[:2],
         "and never swings back to an earlier pose first", nxt[:4])
