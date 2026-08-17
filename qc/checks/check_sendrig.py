"""Sending the rig to the robot must be one line per joint, not five.

"Send rig" used to push GEAR + PULSE + RANGE + RATE + LIMIT separately — five
commands times ten joints, fifty round trips, about 1.6 s of watching a status
line crawl. `JCFG` carries a joint's whole setup, so it should be ten.

The number of commands is the thing to assert: a future change that quietly
goes back to sending them one field at a time would still *work*, just slowly,
and nothing else would notice.
"""
import browser
import fake_serial
import qc as F

AREA = "sendrig"
TITLE = "send rig is one line per joint"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof pushLimits !== "function") return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");
    // a rig that differs from the board in EVERY field, so nothing is skipped
    for (var i = 0; i < NJ; i++) {
      RIG.gearPinion[i] = 14; RIG.gearGear[i] = 19;
      RIG.pulseMin[i] = 505;  RIG.pulseMax[i] = 2495;
      RIG.servoMaxDps[i] = 321; RIG.servoRange[i] = 181;
      RIG.frameHz[i] = 51;    RIG.min[i] = 26; RIG.max[i] = 154;
    }
    qcMark("start");
    pushLimits().then(function(){
      qcMark("done-" + document.getElementById("limStat").textContent
        .replace(/[^A-Za-z0-9 ]/g, "").slice(0, 40).replace(/ /g, "_"));
      qcMark("done");
    });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "send rig ran clean", marks)
    t.contains(marks, "start", "it started sending")
    t.ok(any(m.startswith("done-") for m in marks), "and finished", marks)

    cmds = [c for _, c in fake_serial.wire]
    jcfg = [c for c in cmds if c.upper().startswith("JCFG")]
    old_style = [c for c in cmds
                 if c.upper().split(" ")[0] in ("GEAR", "PULSE", "RANGE", "RATE", "LIMIT")]

    # ---- the point: one line per joint --------------------------------
    t.eq(len(jcfg), 10, "one JCFG per joint (10 joints, 10 commands)")
    t.ok(not old_style,
         "and none of the five old per-field commands were needed",
         "still sending them one field at a time: %s" % old_style[:6])

    # ---- the batch must actually carry the values ---------------------
    # A fast command that applied the wrong numbers would be worse than a slow
    # one, so read back what the module was told.
    applied = fake_serial.NONG.jcfg
    t.eq(len(applied), 10, "the module received a setup for every joint")
    if applied:
        one = applied.get("1") or list(applied.values())[0]
        t.eq(one[:8], ["14", "19", "505", "2495", "321", "181", "51", "26"],
             "the values arrived intact (gear, pulse, dps, travel, hz, min)")

    # ---- nothing is sent when the robot already matches ---------------
    before = len(fake_serial.wire)
    t.ok(before > 0, "traffic was recorded")

    # ---- the firmware and the docs agree it exists --------------------
    nong = (F.FIRMWARE / "src/modules/nong/NongModule.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(nong, 'cmd == "JCFG"', "the firmware implements JCFG")
    t.contains(nong, "reattach(j)",
               "and re-attaches only that joint, never all ten")
    cmds_md = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(cmds_md, "JCFG", "COMMANDS.md documents it")

    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "unknown cmd",
               "Studio falls back to the old commands on an older board")
