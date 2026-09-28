"""A time typed by hand survives editing the pose. Only physics may raise it.

User 2026-09-23: *the time in move in sequence when i already adjust to higer
time and i change the move a little bit make the time it have the most not
recreate the time of the rig because i need that move to that time when i
change i change it everytime make me headace*.

updateKey() re-timed the edited keyframe AND the one after it from the rig, so
every small correction to a pose threw away a duration the operator had chosen.
It had to be typed again, every time.

Now a typed time is PINNED. Nothing that re-times automatically may touch it -
not editing a pose, not changing Show speed, not deleting or reordering a
keyframe. Only clampKeyTimes may raise it, and only as far as the physical
minimum, because a move the servos cannot do in that time is not a choice
anybody can make.

Two ways back to automatic, both deliberate and both asserted here: typing a
°/s on that move, and the pin button on the time box. A time that is held with
no way to let go is the same trap the other way round.

Asserted on `keys` because this is the editor's own bookkeeping - what reaches
the module is covered by check_studio_edits and check_studio_playback.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a hand-typed move time survives pose edits, and can be released"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK TPIN~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var a = Array(NJ).fill(90), b = Array(NJ).fill(90), c = Array(NJ).fill(90);
    b[0] = 110; c[0] = 130;
    keys = [{pose: a.slice(), t: 80, hold: 0},
            {pose: b.slice(), t: 500, hold: 0},
            {pose: c.slice(), t: 500, hold: 0}];
    selKey = 1;
    document.getElementById("speedDps").value = "120";
    renderTimeline();

    // ---- type a time on move 1, the way a person does: in the box.
    var tIn = document.querySelectorAll(".key")[1].querySelector(".ktime input");
    tIn.value = "4000";
    tIn.dispatchEvent(new Event("change", {bubbles: true}));
    var typed = keys[1].t, pinned = !!keys[1].tset;

    // ---- now nudge the pose of that same move. THE HEADACHE.
    selKey = 1;
    pose = b.slice(); pose[1] = 95;
    updateKey();
    var afterEdit = keys[1].t;

    // ---- and nudge the move BEFORE it, which re-times the one after
    selKey = 0;
    pose = a.slice(); pose[1] = 85;
    updateKey();
    var afterPrevEdit = keys[1].t;

    // ---- Show speed must not wipe it either
    document.getElementById("speedDps").value = "300";
    speedChanged();
    var afterSpeed = keys[1].t;
    // ...but the UNPINNED move 2 does follow the speed
    var unpinnedMoved = keys[2].t !== 500;

    // ---- physics may still RAISE it: make the move far too big for 4000 ms
    var far = keys[1].pose.slice(); far[0] = 25; far[4] = 155;
    keys[1].pose = far;
    keys[1].t = 100;                     // below any possible minimum
    clampKeyTimes();
    var raised = keys[1].t;
    var floor = keyMin(1);

    // ---- the pin button lets go, and re-times
    keys[1].t = 4000;
    renderTimeline();
    var pinBtn = document.querySelectorAll(".key")[1].querySelector(".kpin");
    var wasOn = pinBtn.classList.contains("on");
    pinBtn.click();
    var afterRelease = keys[1].t, stillPinned = !!keys[1].tset;

    // ---- and typing a °/s is the other way out
    pinTime(1); keys[1].t = 4000; renderTimeline();
    var dIn = document.querySelectorAll(".key")[1].querySelector(".kdps");
    dIn.value = "60";
    dIn.dispatchEvent(new Event("change", {bubbles: true}));
    var afterDps = !!keys[1].tset;

    report("typed=" + typed + "~pinned=" + pinned +
           "~afterEdit=" + afterEdit + "~afterPrevEdit=" + afterPrevEdit +
           "~afterSpeed=" + afterSpeed + "~unpinnedMoved=" + unpinnedMoved +
           "~raised=" + raised + "~floor=" + floor +
           "~wasOn=" + wasOn + "~afterRelease=" + afterRelease +
           "~stillPinned=" + stillPinned + "~afterDps=" + afterDps);
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
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("TPIN~")]
    got = next((m for m in marks if m.startswith("typed=")), "")
    if not t.ok(got, "the driver typed a time and edited the pose", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.eq(v.get("typed"), "4000", "typing a time in the box sets it")
    t.ok(v.get("pinned") == "true",
         "and pins it, without a second thing to press",
         "the operator already said what they wanted by typing it: %s" % v)
    t.eq(v.get("afterEdit"), "4000",
         "editing that move's own pose keeps the time - THE HEADACHE")
    t.eq(v.get("afterPrevEdit"), "4000",
         "and so does editing the move before it, which also re-times this one")
    t.eq(v.get("afterSpeed"), "4000",
         "changing Show speed does not wipe it either")
    t.ok(v.get("unpinnedMoved") == "true",
         "while a move nobody pinned still follows Show speed",
         "pinning everything would be as bad as pinning nothing: %s" % v)
    floor = int(v.get("floor") or 0)
    t.ok(int(v.get("raised") or 0) == floor and floor > 100,
         "physics may still RAISE a pinned time to what the servos can do",
         "a move the arm cannot make in that time is not a choice anybody can "
         "make. floor %s, got %s" % (v.get("floor"), v.get("raised")))
    t.ok(v.get("wasOn") == "true", "the pin button shows the time is held", v)
    t.ok(v.get("stillPinned") == "false" and v.get("afterRelease") != "4000",
         "pressing the pin lets go, and Studio times the move again",
         "a time held with no way to let go is the same trap the other way "
         "round: %s" % v)
    t.ok(v.get("afterDps") == "false",
         "typing a °/s also hands the timing back to Studio",
         "asking for a speed IS asking to be timed: %s" % v)
