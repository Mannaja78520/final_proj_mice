"""Run continues from the move you clicked, and never begins with a lunge.

The user's report, 2026-08-28, in their own words: *when i click pose 2 or
another pose in sequence warp the play time warp to time of that pose when i
run it will follow sequence not warp to pose 1 and run in sequence ... my body
of robot will broke it hit other thing that i don't want if it warp to pose 1
and then follow sequence*.

A SAFETY check. Clicking a keyframe already parked the play clock there
(A20-1), and both the browser clock and the hub clock honoured it —
`NongShow.start` takes `from_ms` and `_play_once` walks to the right step. But
two paths handed the module the WHOLE file and let it start at step 0:

  * `robotRun()` — Run on robot, and
  * `handOffToRobot()` — which fires BY ITSELF when the tab is hidden mid-show.

Either sends the arm sweeping from wherever it stands back to keyframe 0,
across whatever the rig has in the way. The second is worse: nobody pressed
anything.

Three things are asserted, because all three are easy to lose:

  * the file starts at the parked keyframe, on BOTH paths;
  * the keyframes before it are still walked for `speed`, which is STATE — a
    file starting in the middle must carry the speed in force there;
  * the first move written gets `max(its own time, minTime(here -> there))`.
    The file cannot know where the robot is standing, so the one move whose
    start is unknown is never allowed to be quicker than the distance needs.

Asserted on the bytes the MODULE received, decoded from the FBEGIN/FDATA
traffic on the wire — not on what the page says about itself. Reading the wire
rather than `NONG.held` is what lets all three phases live in ONE check: held
keeps only the last file, and this check must see every file it sent.

One guard is stood down to reach the second path: Studio talks to the board
THROUGH the hub in QC, and `handOffToRobot` correctly does nothing while the
hub holds the clock — that is what stops two clocks driving one arm. The driver
stubs `hubDriven()`; every other guard on it is left alone.

Merged from two checks on 2026-08-28: each was starting its own hub and its own
browser, and the gate began timing out under the extra load.
"""
import base64
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Run continues from the clicked move, and never begins with a lunge"
SLOW = True

DRIVER = """
function build(vals, ms){
  keys.length = 0;
  vals.forEach(function(v){
    pose = pose.map(function(){ return v; });
    addKey();
  });
  keys.forEach(function(k, i){ if (i) { k.t = ms; k.hold = 0; } });
}
function step(){
  try{
    if (typeof addKey !== "function" || !document.getElementById("liveChk"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");
    document.getElementById("loopChk").checked = false;
    document.getElementById("liveChk").checked = true;
    liveChanged();
    // ---- phase 1: Run, after clicking the third pose -------------------
    build([30, 60, 120, 150], 900);
    document.getElementById("seqName").value = "qcrun";
    qcMark("keys-" + keys.length);
    selectKey(2);                       // the pose 120 keyframe
    qcMark("parked-" + Math.round(playT));
    setTimeout(function(){
      robotRun().then(function(){
        qcMark("ran");
        // ---- phase 2: the tab is hidden mid-show ------------------------
        setTimeout(function(){
          selectKey(3);                 // the last move
          playing = true;
          hubDriven = function(){ return false; };
          Object.defineProperty(document, "hidden",
                                { get: function(){ return true; }, configurable: true });
          document.dispatchEvent(new Event("visibilitychange"));
          qcMark("hidden-" + Math.round(playT));
          // ---- phase 3: parked far from where the robot stands ----------
          setTimeout(function(){
            handedOff = false;
            build([30, 60, 150], 80);   // the timeline asks for the 80ms floor
            document.getElementById("seqName").value = "qclunge";
            playT = keyStartMs(2);      // park WITHOUT clicking: pose stays put
            pose = pose.map(function(){ return 30; });
            qcMark("far-" + Math.round(playT));
            robotRun().then(function(){
              qcMark("ran2");
              setTimeout(function(){ qcMark("done"); }, 500);
            }).catch(function(e){ qcFail(e); });
          }, 1400);
        }, 500);
      }).catch(function(e){ qcFail(e); });
    }, 900);
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def uploads():
    """Every file the module was sent, as (name, text), in wire order.

    An upload is FBEGIN <name> then FDATA <base64> chunks. Decoding those is
    the most direct form of "assert on what reached the module" there is.
    """
    out, name, buf = [], None, ""
    for _ms, c in fake_serial.wire:
        head = c.split(" ", 1)[0].upper()
        if head == "FBEGIN":
            if name is not None:
                out.append((name, buf))
            name, buf = (c.split(" ", 1)[1].strip() if " " in c else "?"), ""
        elif head == "FDATA" and name is not None:
            try:
                buf += base64.b64decode(c.split(" ", 1)[1]).decode(errors="replace")
            except Exception:                       # noqa: BLE001 - a bad chunk
                pass                                # is the module's problem
    if name is not None:
        out.append((name, buf))
    return out


def poses_in(text):
    return [ln for ln in text.splitlines() if ln.strip().startswith("- pose:")]


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=34)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)
    t.contains(marks, "connected", "Studio connected over USB")
    t.contains(marks, "ran", "Run on robot finished")
    t.contains(marks, "ran2", "the third phase ran too")
    # build() clears the timeline first, so the clicked keyframe is index 2
    # of exactly four and one 900 ms move sits before it
    t.contains(marks, "parked-900",
               "clicking a keyframe parks the clock at its own time")

    files = uploads()
    t.ok(len(files) >= 3, "all three runs sent the module a file",
         [n for n, _ in files])
    if len(files) < 3:
        return
    run1, hand, lunge = files[0], files[1], files[2]

    # ---- phase 1: Run starts at the clicked move -------------------------
    t.contains(run1[0], ".part.yaml",
               "a partial run is its own file, so the saved show is not overwritten")
    p1 = poses_in(run1[1])
    t.eq(len(p1), 2, "only the moves from the clicked one onward were written")
    if len(p1) == 2:
        t.contains(p1[0], "120", "the file starts at the move that was clicked")
        t.contains(p1[1], "150", "and carries on to the end of the show")
    for gone, why in (("30", "the first pose of the show"),
                      ("60", "the move just before the clicked one")):
        t.ok('"%s ' % gone not in run1[1],
             "%s is nowhere in a resumed file" % why, run1[1])
    t.contains(run1[1], "- speed:",
               "the resumed file carries the speed in force there")

    # ---- phase 2: hiding the tab hands over from HERE --------------------
    t.contains(marks, "hidden-1800",
               "the clock was parked at the last move before the tab was hidden")
    p2 = poses_in(hand[1])
    t.eq(len(p2), 1, "the tab-hide handover wrote only the move still to come")
    if p2:
        t.contains(p2[0], "150", "and it is the move the clock was parked on")
    t.ok('"120 ' not in hand[1],
         "the move already played is nowhere in a handed-over file", hand[1])

    # ---- phase 3: the first move is never quicker than the distance ------
    p3 = poses_in(lunge[1])
    t.eq(len(p3), 1, "the third run also wrote only what is still to come")
    if not p3:
        return
    m = re.search(r"T (\d+)", p3[0])
    if not t.ok(m, "that move carries an explicit time", p3[0]):
        return
    got = int(m.group(1))
    # 120 deg cannot be crossed in 80 ms by any joint on this robot, so the
    # written time must have been raised. The exact floor is per joint and
    # lives in minTime(); "more than the timeline asked for" is the part that
    # must never stop being true. (900 ms would prove nothing here: that is
    # already slower than the distance needs, and an earlier version of this
    # check passed against the broken code because of it.)
    t.ok(got > 80,
         "the first move was slowed to the distance the arm really has to cross",
         "wrote T %d for a 120 deg move the timeline had at 80 ms" % got)
