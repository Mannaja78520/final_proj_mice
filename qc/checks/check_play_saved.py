""""Play saved" runs a SAVED sequence without editing it first.

A20-2 asked for the one press that joins Load and Play: pick a saved
sequence (hub `sequences/` or robot SD `/moves`) and play it right away,
exactly like an edited one — same loader (`loadParsedSeq`), same Play
button (`togglePlay`), so whichever clock applies still applies.

Asserted on the WIRE: the seeded file's own poses and Ts must reach the
module, starting at the top, moving forward, nothing replayed — not on what
the stat line claims. The clock reset matters: `loadParsedSeq` deliberately
leaves `playT` alone when EDITING, so a fresh load used to inherit whatever
time the previous show had stopped at.
"""
import os

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Play saved loads a saved sequence and plays it"
SLOW = True

SEED = ("name: qcplay\nloop: false\nkeys:\n"
        "  - pose: 40 40 140 140 40 40 140 140 90 90 T 900\n"
        "  - wait: 150\n"
        "  - pose: 130 130 60 60 130 130 60 60 90 90 T 1100\n")
T_A, T_B = 900, 1100

DRIVER = """
function step(){
  try{
    if (!document.getElementById("liveChk")) return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    document.getElementById("loopChk").checked = false;
    document.getElementById("liveChk").checked = true;
    liveChanged();
    var sel = document.getElementById("seqList");
    var opt = Array.prototype.find.call(sel.options, function(o){
      return o.value === "qc_play.yaml"; });
    if (!opt) { qcFail(new Error("seeded sequence not offered in the list")); return; }
    sel.value = "qc_play.yaml";
    var btn = document.querySelector('button[onclick="playLocalSeq()"]');
    if (!btn) { qcFail(new Error("Play saved button missing")); return; }
    rawCmd("MOVE QCMARK PS");
    // let the link drain first — ONE clock rules this robot, and a queued
    // travel pose landing after Play would legitimately take over
    setTimeout(function(){
      btn.click();
      setTimeout(function(){
        qcMark("done");
        if (playing) togglePlay();
      }, 3600);
    }, 900);
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def lead_of(cmd):
    try:
        return float(cmd.split()[1])
    except (IndexError, ValueError):
        return None


def t_of(cmd):
    import re
    m = re.search(r"\bT\s+(\d+)", cmd)
    return int(m.group(1)) if m else None


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    seq_dir = main.SEQUENCES
    seq_dir.mkdir(exist_ok=True)
    seed_file = seq_dir / "qc_play.yaml"
    seed_file.write_text(SEED, encoding="utf-8", newline="\n")
    try:
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=16)
    finally:
        os.remove(seed_file)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)
    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK PS")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    # Everything after the marker belongs to the show (the link drained before
    # Play), and every real segment clears the firmware's 80 ms floor.
    segs = [c for c in wire[i + 1:]
            if c.upper().startswith("POSE ") and (t_of(c) or 0) > 80]
    if not t.ok(segs, "playing a saved sequence drove the module",
                [c for c in wire[i + 1:] if c.upper().startswith("POSE")][:4]):
        return
    a, b = segs[0], segs[-1]
    t.ok(lead_of(a) == 40.0,
         "it started AT THE TOP — the robot was put on the file's first pose "
         "before its clock ran (travel T %s ms)" % t_of(a), a)
    t.ok(lead_of(b) == 130.0 and abs((t_of(b) or 0) - T_B) <= 60,
         "then moved forward into the file's second move at ITS OWN time "
         "(%s ms of %d)" % (t_of(b), T_B), b)
    t.eq(len(segs), 2,
         "nothing else was sent — not the editor's old timeline, not a restart")
