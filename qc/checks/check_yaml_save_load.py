"""Nong Studio saves a YAML under its own name and opens one by picking it.

Asked 2026-09-16: *how to save to yaml to use in the voice and other thing too,
i see only the my_move and i can't save* and *when select the .yaml, give the
sequence of that yaml to the time line so it can edit its own time line*.

Every save went to my_move.yaml - the name the box starts with - and picking a
file in the list did nothing until a second button was pressed. Holds:
  * Save YAML writes <sequence name>.yaml on this PC;
  * picking a saved YAML in the list loads its moves into the timeline at once;
  * and sets the sequence name to that file, so Save writes back to it;
  * saving over an existing file asks first, and Cancel writes nothing.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Save YAML uses its own name, and picking a YAML opens it"
SLOW = True

NAME = "qc_yaml_saveload"

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK YAML~" + s); }
var asked = 0, answer = true;
window.confirm = function(){ asked++; return answer; };
window.addEventListener("load", function(){ setTimeout(async function(){
  try{
    keys = [];
    [90, 40, 140].forEach(function(v){ pose = pose.map(function(){ return v; }); addKey(); });
    document.getElementById("seqName").value = "%(name)s";
    await refreshSeqs();
    await exportYaml();                                   // a new name: no question
    report("asked1=" + asked);
    // open it again from the list, the way a person picks it
    keys = []; document.getElementById("seqName").value = "my_move";
    var sel = document.getElementById("seqList");
    sel.value = "%(name)s.yaml";
    sel.dispatchEvent(new Event("change"));
    await new Promise(function(r){ setTimeout(r, 1500); });
    report("keys=" + keys.length + "~name=" + document.getElementById("seqName").value);
    // saving over it asks, and Cancel writes nothing
    answer = false; asked = 0;
    keys.pop();
    await exportYaml();
    report("asked2=" + asked);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
""" % {"name": NAME}


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    seq = F.STUDIO / "sequences" / (NAME + ".yaml")
    seq.unlink(missing_ok=True)
    fake_serial.reset()
    base, _main = F.start_hub()
    try:
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=25)
        marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("YAML~")]
        bad = [m for m in marks if m.startswith("ERR-")]
        if not t.ok(marks and not bad, "the driver ran without throwing", marks[-3:]):
            return
        t.ok(seq.is_file(), "Save YAML wrote %s.yaml under the name typed" % NAME, marks)
        t.ok("asked1=0" in marks, "a new name saves without a question", marks)
        written = seq.read_text(encoding="utf-8") if seq.is_file() else ""
        t.ok(written.count("pose:") == 3, "with all three moves in it", written[-300:])
        t.ok("keys=3~name=%s" % NAME in marks,
             "picking it in the list loads its 3 moves and takes its name", marks)
        t.ok("asked2=1" in marks, "saving over an existing file asks first", marks)
        after = seq.read_text(encoding="utf-8") if seq.is_file() else ""
        t.ok(after == written, "and Cancel leaves the saved file exactly as it was")
    finally:
        seq.unlink(missing_ok=True)
        seq.with_name(seq.name + ".bak").unlink(missing_ok=True)   # the save keeps one
