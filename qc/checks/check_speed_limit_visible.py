"""Nong Studio says WHICH limit is holding a move, and the limit is editable.

User 2026-09-23: *the speed of servo i cannot adject anymore with show speed or
max servo speed in show i cannot adjust anymore ... when input the deg/s in
sequence it not change the time for me anymore*.

Nothing was broken in the arithmetic. Two things together made every speed box
look dead:

  * the peak-speed floor. A move eases in and out, so its peak is pi/2 times
    its average and the floor is delta * pi/2 / SAFE_DPS. With the board's
    safe_dps at 60, that is delta / 38.2 - so any Show speed or per-move deg/s
    above about 38 produced the IDENTICAL time, silently;
  * the Peak speed limit box was `disabled` until a board was connected, so
    away from the robot there was no number on the page that could shorten
    anything at all.

So the fix is not new maths, it is telling the truth on screen. This check
holds both halves:

  * the box is editable with no robot connected, and editing it re-times the
    automatic moves;
  * a per-move deg/s that cannot shorten the move puts the REASON in the
    status line, naming the peak limit;
  * when a servo (not the peak limit) is the binding one, the reason names
    that joint instead - otherwise every message would blame the same thing.

Break minTimeWhy's `why` strings, or put `disabled` back on safeDpsInput, and
this check fails. That is the whole point: the arithmetic was never the bug.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio names the limit holding a move, and the limit can be edited"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK SPDLIM~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var stat = document.getElementById("tlStat");
    var box = document.getElementById("safeDpsInput");
    // No board has answered INFO for this page, so this is the offline case.
    var editable = !box.disabled;

    // A big move on ONE joint: 90 -> 150 on L shoulder pitch, 60 deg.
    var p0 = Array(NJ).fill(90), p1 = Array(NJ).fill(90);
    p1[0] = 150;
    keys = [{pose: p0, t: 80, hold: 0}, {pose: p1, t: 0, hold: 0}];
    selKey = 0;
    SAFE_DPS = 60;
    box.value = "60";
    document.getElementById("speedDps").value = "120";
    keys[1].t = autoTime(p0, p1, speedDps());
    var slowT = keys[1].t;                       // 60 * pi/2 / 60 = 1571 ms
    var why = minTimeWhy(p0, p1).why;

    // Raising the PLANNING limit must shorten that automatic move.
    box.value = "200";
    safetyLimitChanged();
    var fastT = keys[1].t;
    var savedMsg = document.getElementById("safeSpeedStat").textContent;

    // Back to 60, then type a per-move speed the peak limit cannot honour.
    box.value = "60";
    safetyLimitChanged();
    renderTimeline();
    var dps = document.querySelector(".kdps");
    dps.value = "200";
    dps.dispatchEvent(new Event("change", {bubbles: true}));
    var blockedMsg = stat.textContent;
    var blockedT = keys[1].t;

    // A move the SERVO limit holds instead: WAIST (joint 9) is a 200 deg/s
    // servo, and at a 900 deg/s planning limit the servo is the slower of the
    // two - so the reason must name the joint, not the peak limit.
    var q0 = Array(NJ).fill(90), q1 = Array(NJ).fill(90);
    q1[8] = 150;
    SAFE_DPS = 900;
    var servoWhy = minTimeWhy(q0, q1).why;

    report("editable=" + editable + "~slowT=" + slowT + "~fastT=" + fastT +
           "~peakWhy=" + (why.indexOf("peak speed limit") >= 0) +
           "~servoWhy=" + (servoWhy.indexOf("Waist") >= 0) +
           "~offline=" + (savedMsg.indexOf("connect first") >= 0) +
           "~blockedSaid=" + (blockedMsg.indexOf("peak speed limit") >= 0) +
           "~blockedT=" + blockedT);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = [m[7:] for m in fake_serial.qc_marks if m.startswith("SPDLIM~")]
    got = next((m for m in marks if m.startswith("editable=")), "")
    if not t.ok(got, "the driver measured the speed limits", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.ok(v.get("editable") == "true",
         "the Peak speed limit box is editable with no robot connected",
         "it was disabled until a board answered INFO, so offline there was no "
         "number on the page that could make any move shorter")
    slow, fast = int(v["slowT"]), int(v["fastT"])
    t.ok(fast < slow - 200,
         "raising the planning limit shortens an automatically timed move",
         "60 deg/s -> %d ms, 200 deg/s -> %d ms" % (slow, fast))
    t.ok(v.get("peakWhy") == "true",
         "the peak speed limit is named when it is the binding one", v)
    t.ok(v.get("servoWhy") == "true",
         "a joint's own servo speed is named when THAT is the binding one",
         "otherwise every message blames the peak limit, including the ones it "
         "does not cause: %s" % v)
    t.ok(v.get("offline") == "true",
         "with no robot, the box says the limit was not saved to one", v)
    t.ok(v.get("blockedSaid") == "true",
         "a per-move deg/s that cannot shorten the move says why",
         "typing 200 deg/s where 38 is the ceiling used to change the box and "
         "nothing else: %s" % v)
