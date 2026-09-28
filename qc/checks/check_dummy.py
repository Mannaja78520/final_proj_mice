"""The dummy: a hand-posed copy of the robot drives Studio and the robot.

The dummy is its own module (firmware type "dummy") with a pot on every joint.
It answers POSE? like the robot, on the same RS485 bus with its own id (68
here, beside the robot). Studio reads it over its OWN link and:

  * saves its pose as a new move, and writes it into the selected move;
  * follows it, and with "robot follows" sends each new pose to the robot;
  * sends the robot to a saved move, at that move's speed.

Asserted on the wire: the dummy was asked (dummy_wire), the robot received
the pose (fake_serial.wire), and never the other way round - a dummy command
reaching the robot, or a robot pose reaching the dummy, is exactly the mix-up
two modules on one cable invite. The robot's limits must hold: a dummy bent
past them sends the limit.

Bending the dummy mid-test is done with DCAL ZERO through the dummy's own
link: moving a pot's zero by 455 counts is the same angle change as turning
the pot 30 degrees, and it stays inside the real protocol.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the dummy poses Studio and the robot, and fills the sequence"
SLOW = True

DRIVER = """
function report(s){ return rawCmd("MOVE QCMARK " + s); }
function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
window.addEventListener("load", function(){ setTimeout(async function(){
  try{
    if (!await qcStudioReady()) throw new Error("studio not ready");
    // the dummy on the robot's cable, as bus id 68
    var sel = document.getElementById("dummyPort");
    var o = document.createElement("option"); o.value = o.textContent = "%(port)s";
    sel.appendChild(o); sel.value = "%(port)s"; sel.dataset.loaded = "1";
    document.getElementById("dummySrc").value = "usb"; dummySrcChanged();
    document.getElementById("dummyBus").value = "%(bus)s";

    pose[7] = clampJ(7, 45);                              // R_EL_R has no pot: must stay put
    await report("keep=" + fmtA(pose[7]));
    keys = []; addKey();                                  // move 0: the start pose
    await dummyToNewKey();                                // move 1 from the dummy
    await report("new=" + keys[keys.length - 1].pose.map(fmtA).join(","));
    await report("lim=" + clampJ(9, 999));
    selectKey(0);
    await dummyToSelectedKey();
    await report("upd=" + keys[0].pose.map(fmtA).join(","));

    // robot follows the dummy; then bend joint 1 up 30 degrees
    document.getElementById("dummyFollow").value = "robot"; dummyFollowChanged();
    await wait(700);
    await report("FOLLOW");
    await dummyCmd("DCAL 1 ZERO %(zero)s");
    await wait(1500);
    document.getElementById("dummyFollow").value = "off"; dummyFollowChanged();
    await wait(300);
    await report("want1=" + fmtA(clampJ(0, 120)));

    // the robot to a saved move
    keys[1].pose = keys[1].pose.map(function(v, i){ return i === 1 ? 70 : v; });
    selKey = 1;
    await report("TOKEY");
    robotToSelectedKey();
    await wait(600);
    await report("key1=" + keys[1].pose.map(function(v, i){ return fmtA(clampJ(i, v)); }).join(","));

    // the simulated dummy answers through the same path
    document.getElementById("dummySrc").value = "sim"; dummySrcChanged();
    dummySim[4] = 55;
    await dummyToNewKey();
    await report("sim=" + fmtA(keys[keys.length - 1].pose[4]));
    await report("done");
  }catch(e){ report("ERR-" + String(e).slice(0,80)); }
}, 1500); });
"""


def _mark(marks, key):
    for m in marks:
        if m.startswith(key + "="):
            return m[len(key) + 1:]
    return None


def _poses_after(wire, marker):
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK " + marker)
    except ValueError:
        return None
    return [c for c in wire[i + 1:] if c.upper().startswith("POSE ")]


def _vals(cmd):
    return [float(v) for v in cmd.split()[1:11]]


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — this needs a real browser")
    fake_serial.reset()
    d = fake_serial.DUMMY
    d.raw[2] = fake_serial.dummy_raw_for(120)       # L_EL_P bent to 120
    d.raw[9] = 4095                                  # SHRUG far past the robot's limit
    d.cal["ch"][7] = -1                              # R_EL_R has no pot
    d.cal["max"][9] = 180                            # the dummy's own limit is wider:
                                                     # only Studio's clamp can hold it
    zero = round(2048 - 30 * 4095 / 270)             # joint 1 reads 30 deg higher

    base, main = F.start_hub()
    drv = DRIVER % {"port": fake_serial.PORT, "bus": fake_serial.DUMMY_ID, "zero": zero}
    browser.page(drv, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=30)

    marks = fake_serial.qc_marks
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    if not t.ok("done" in marks, "the driver finished", marks[-4:]):
        return

    # ---- reading: the dummy was asked, on its own id ------------------------
    t.ok(any(c.upper() == "POSE?" for c in fake_serial.dummy_wire),
         "Studio read the dummy's pose on bus id %d" % fake_serial.DUMMY_ID,
         fake_serial.dummy_wire[:4])
    robot = [c for _, c in fake_serial.wire]
    t.ok(not any(c.upper().startswith(("DCAL", "POSE?")) for c in robot),
         "no dummy command reached the robot",
         [c for c in robot if c.upper().startswith(("DCAL", "POSE?"))][:3])
    t.ok(not any(c.upper().startswith("POSE ") for c in fake_serial.dummy_wire),
         "and no robot pose reached the dummy")

    # ---- the sequence ----------------------------------------------------------
    lim = float(_mark(marks, "lim") or "nan")
    for key, what in (("new", "saved as a new move"), ("upd", "written into the selected move")):
        got = _mark(marks, key)
        if not t.ok(got, "the dummy pose was %s" % what, marks[:6]):
            continue
        v = [float(x) for x in got.split(",")]
        t.ok(abs(v[2] - 120) < 0.6, "%s: L_EL_P is the dummy's 120 (%s)" % (key, v[2]))
        # The dummy reads 180 (its own limit); only Studio's clamp to the
        # robot's limit keeps it from asking for an angle the robot refuses.
        t.ok(v[9] <= lim + 0.01 and v[9] < 130,
             "%s: SHRUG bent past the limit holds inside the robot's limit %s (%s)" % (key, lim, v[9]),
             "a dummy bent too far would ask the robot for an angle it refuses")
        keep = _mark(marks, "keep")
        t.ok(keep and abs(v[7] - float(keep)) < 0.11,
             "%s: R_EL_R with no pot stays where it was (%s)" % (key, v[7]),
             "was %s - a '-' in POSE? must leave the joint alone" % keep)
    t.eq(_mark(marks, "sim"), "55", "the simulated dummy's pose becomes a move")

    # ---- robot follows the dummy ---------------------------------------------
    after = _poses_after(robot, "FOLLOW")
    tail = _poses_after(robot, "TOKEY") or []
    after = after[:len(after) - len(tail)] if after else after   # only the follow part
    if t.ok(after, "robot-follows sent poses to the robot", robot[-4:]):
        want1 = float(_mark(marks, "want1") or "nan")
        last = _vals(after[-1])
        t.ok(abs(last[0] - want1) < 0.6,
             "bending the dummy's joint 1 moved the robot's joint 1 to %s (%s)" % (want1, last[0]),
             after[-3:])
        t.ok(abs(last[2] - 120) < 0.6, "and joint 3 still holds the dummy's 120 (%s)" % last[2])
        t.ok(all(re.search(r"\bT\s+\d+", c) for c in after),
             "every followed pose carries a travel time, so the robot's max speed applies")

    # ---- the robot to a saved move ---------------------------------------------
    to_key = _poses_after(robot, "TOKEY")
    want = _mark(marks, "key1")
    if t.ok(to_key and want, "sending the robot to a saved move sent a pose", robot[-4:]):
        got = _vals(to_key[0])
        exp = [float(x) for x in want.split(",")]
        t.ok(all(abs(a - b) < 0.11 for a, b in zip(got, exp)),
             "the robot got exactly that move's pose", "sent %s, move is %s" % (got, exp))
        t.ok(re.search(r"\bT\s+\d+", to_key[0]), "at a travel time", to_key[0])
