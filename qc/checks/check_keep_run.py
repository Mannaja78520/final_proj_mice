"""What Studio runs is kept on the robot, and the robot's settings are set from
Studio (A44-2, A44-3).

User 2026-10-19: keep whatever is sent to the robot to run (e.g. last.yaml) on
the robot, so it can run later from the robot's own page with no hub and no
Studio; a simple way to put a show on the robot, or save on Run, chosen in
Settings; the robot's device settings editable in Studio's settings; sending
or updating moves on the nong made easy.

A timeline Run already left <name>.yaml on the card. A SHOW Run did not: the
hub plays a show step by step, so nothing of it reached the card. Now both
also write last.yaml (the robot's page offers it first), unless Setup turns
it off. Asserted on the FILES that reached the module over the fake cable,
never on what the page says it did.
"""
import base64

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "every Run is kept on the robot as last.yaml, and robot settings save from Studio"
SLOW = True

SEQ = ("name: qc_keep_seq\nloop: false\nsteps:\n"
       "  - speed: 120\n"
       '  - pose: "31 90 90 90 90 90 90 90 90 90 T 700"\n'
       '  - pose: "35 90 90 90 90 90 90 90 90 90 T 400"\n')

DRIVER = """
function mark(s){ return rawCmd("MOVE QCMARK KEEP~" + s); }
function later(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
window.addEventListener("load", function(){ qcWaitFor(function(){
    return typeof robotRun === "function" && typeof saveRobotSetting === "function"
           && document.getElementById("rs_volume") && typeof haveUsb === "function"
           && haveUsb() && !!boardSafeIdentity;   // a Run before the board is read goes stale (A46-3)
  }, 20000).then(async function(ready){
  if (!ready) { qcMark("ERR-not-ready"); qcMark("done"); return; }
  try{
    var a = pose.slice(), b = pose.slice(); b[0] = 40;
    keys = [{pose: a, t: 80, hold: 0}, {pose: b, t: 600, hold: 0}];
    selKey = 0; playT = 0; bumpKeys();
    document.getElementById("projName").value = "qc_keep_run";

    await mark("RUN-ON"); setKeepRun(true); await robotRun(); await later(200);
    await mark("RUN-OFF"); setKeepRun(false); await robotRun(); await later(200);
    setKeepRun(true);

    // the robot's settings, from Setup
    await mark("SET");
    document.getElementById("rs_volume").value = 40;
    await saveRobotSetting(ROBOT_SETTINGS.filter(function(d){ return d.id === "volume"; })[0]);
    document.getElementById("rs_speed").value = 3;          // below the 5 floor
    await saveRobotSetting(ROBOT_SETTINGS.filter(function(d){ return d.id === "speed"; })[0]);
    var refused = document.getElementById("robotSetStat").textContent;

    // a saved PC file onto the robot, without opening it
    await mark("PUT");
    var sel = document.getElementById("seqList"), o = document.createElement("option");
    o.value = o.textContent = "qc_keep_seq.yaml"; sel.appendChild(o); sel.value = o.value;
    await putLocalSeqOnRobot(); await later(200);

    // a SHOW Run keeps the show on the robot too
    await mark("SHOW");
    newShow(); showDraft.items = [{seq: "qc_keep_seq.yaml"}]; renderShow();
    document.getElementById("showName").value = "qc keep";
    await playShow(); await later(300);
    await mark("END~refused=" + refused.replace(/[ ~]/g, "_").slice(0, 60));
  }catch(e){ qcMark("ERR-" + String(e).slice(0, 70)); }
  setTimeout(function(){ qcMark("done"); }, 300);
}); });
"""


def sections():
    """The wire cut at each KEEP~ mark: {name: [commands after it]}."""
    out, cur = {}, None
    for _ms, c in fake_serial.wire:
        if c.startswith("MOVE QCMARK KEEP~"):
            cur = c[len("MOVE QCMARK KEEP~"):].split("~")[0]
            out[cur] = []
        elif cur:
            out[cur].append(c)
    return out


def files(cmds):
    """(name, text) of each file written in these commands, in order."""
    got, name, buf = [], None, ""
    for c in cmds + ["FBEGIN -"]:
        head = c.split(" ", 1)[0].upper()
        if head == "FBEGIN":
            if name is not None:
                got.append((name, buf))
            name, buf = c.split(" ", 1)[1].strip(), ""
        elif head == "FDATA" and name is not None:
            buf += base64.b64decode(c.split(" ", 1)[1]).decode(errors="replace")
    return got


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    seq = main.SEQUENCES
    seq.mkdir(exist_ok=True)
    made = seq / "qc_keep_seq.yaml"
    made.write_bytes(SEQ.encode())
    try:
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=40)
    finally:
        made.unlink(missing_ok=True)
    marks = fake_serial.qc_marks
    bad = [m for m in marks if m.startswith("ERR-")]
    if not t.ok(not bad, "the driver ran without throwing", bad[:1]):
        return
    s = sections()
    if not t.ok("END" in s, "the driver got to the end", list(s)):
        return

    # ---- a timeline Run, keep on: the file, then last.yaml, then MOVE -------
    on = s.get("RUN-ON", [])
    wrote = files(on)
    names = [n for n, _ in wrote]
    t.eq(names, ["qc_keep_run.yaml", "last.yaml"],
         "Run writes the sequence, then the same moves as last.yaml")
    t.ok(len(wrote) == 2 and wrote[0][1] == wrote[1][1],
         "last.yaml is the very file that was run", wrote)
    moves = [c for c in on if c.startswith("MOVE ")]
    t.eq(moves, ["MOVE qc_keep_run.yaml"], "and the robot runs the sequence itself")
    t.ok(on and on.index(moves[0]) > max(i for i, c in enumerate(on) if c.startswith("FEND")),
         "only after both files are written", on)

    # ---- keep off: no copy ----------------------------------------------------
    off = s.get("RUN-OFF", [])
    t.eq([n for n, _ in files(off)], ["qc_keep_run.yaml"],
         "with the setting off, Run sends only the sequence")

    # ---- robot settings --------------------------------------------------------
    st = s.get("SET", [])
    t.ok("VOL 40" in st and "CFG volume 40" in st,
         "Setup's volume is set now and kept over a restart", st)
    t.ok(not any(c.startswith("SPEED") or "speed_dps" in c for c in st),
         "a speed below the robot's floor is refused before anything is sent", st)
    end = next(c for _, c in fake_serial.wire if c.startswith("MOVE QCMARK KEEP~END"))
    t.ok("number_from_5" in end, "and the page says what it wants", end)

    # ---- a saved PC file onto the robot, as it is ------------------------------
    put = files(s.get("PUT", []))
    t.eq(put, [("qc_keep_seq.yaml", SEQ)],
         "Save to robot on a saved PC file puts that file on the robot, byte for byte")

    # ---- a show Run keeps the show's file as last.yaml -------------------------
    shown = files(s.get("SHOW", []))
    t.ok([n for n, _ in shown] == ["last.yaml"],
         "a show Run writes last.yaml on the robot (it wrote nothing there before)", shown)
    t.ok(shown and "35 90 90" in shown[0][1] and "pose" in shown[0][1],
         "and it is the show's run, the same file Save to robot writes", shown)

    # ---- the robot's own page offers last.yaml first ---------------------------
    page = (F.CODE / "firmware/src/web/WebUI.h").read_text(encoding="utf-8")
    t.contains(page, "if(fs.some(f=>f.n=='last.yaml'))s.value=dir+'/last.yaml';",
               "the robot's own page picks last.yaml first in Play a saved show")
