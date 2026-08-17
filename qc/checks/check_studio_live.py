"""Live mode: dragging in the editor must leave the robot where the numbers say.

The trap is that the UI is always right about itself — `pose` and the slider
both hold the final value — while the ARM sits somewhere else. So this check
only ever asserts on what the module was told, and specifically on the LAST
thing it was told.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "live drag delivers the final pose"
SLOW = True

FINAL = 137.5          # where the drag ends: no other step uses this value
UPDATES = len(range(40, 131, 2)) + 1        # how many values the drag pushes

DRIVER = """
function step(){
  try{
    if (typeof poseChanged !== "function" || !document.getElementById("liveChk"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    document.getElementById("liveChk").checked = true;
    liveChanged();
    qcMark("connected");

    // A FAST drag: many values in a tight loop, far quicker than the link can
    // ship them, ending on FINAL — this is "drag quickly and let go".
    // Only the "input" path fires — NO final poseChanged(false). That is the
    // user's "drag fast and let go with the mouse off the bar": the commit
    // event never arrives, so the last value reaches the robot only if the
    // send path itself guarantees it. A time throttle drops it instead.
    var vals = [], v;
    for (v = 40; v <= 130; v += 2) vals.push(v);
    vals.push(%s);
    var k = 0;
    (function pump(){
      if (k < vals.length) {
        pose[0] = vals[k++];
        poseChanged(true);            // the throttled path a slider uses
        return setTimeout(pump, 8);   // ~125 updates/s, faster than the cable
      }
      setTimeout(function(){ qcMark("settled"); qcMark("done"); }, 3000);
    })();
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % (FINAL,)


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the drag ran clean", marks)
    t.contains(marks, "connected", "Studio connected over USB")
    t.contains(marks, "settled", "the drag finished")

    poses = fake_serial.poses()
    if not t.ok(poses, "the drag sent poses at all"):
        return

    # ---- THE assertion: wherever the drag ended is where the arm ends -----
    last = poses[-1][1][0]
    t.eq(float(last), FINAL,
         "the LAST pose sent is the value the drag ended on")

    # ---- and the module's own idea of where it is agrees -----------------
    t.eq(float(fake_serial.NONG.joints[0]), FINAL,
         "the module actually holds that pose")

    # ---- ordering: a fire-and-forget burst can deliver an OLD pose last.
    # One command in flight at a time is what prevents it, and it also means
    # the burst is coalesced instead of queued.
    # Never MORE sends than updates — that is the invariant that proves poses
    # are superseded rather than queued. (How much coalescing actually happens
    # depends on link speed, so it is not something to pin a number to.)
    t.under(len(poses), UPDATES,
            "a fast drag is coalesced, never queued up per frame", " poses")
    t.ok(len(poses) >= 2, "but intermediate poses still stream while dragging",
         "only %d pose(s) sent — live mode would feel dead" % len(poses))
