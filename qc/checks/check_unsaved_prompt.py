"""One Save writes both files, and unsaved moves are never replaced silently.

Asked 2026-09-23 (A31-18): *make to save yaml and the studio json config more
easy than this why we not make it same thing ... when i change the sequence or
change the save json or yaml make it ask if i not update ... because i found
the problem i loss it a lot of time but make can setting this up in setting to
disable this feature*.

Before: two buttons, two name boxes (project .json, sequence .yaml), and
picking another file replaced the time bar with no question - the draft only
said "unsaved" until a PROJECT save, so a YAML save still read as unsaved and
a project save left the YAML behind. Holds:
  * saveAll writes NAME.json and NAME.yaml, with no question for a new name;
  * after it the page is clean; one edit makes it dirty;
  * opening a file while dirty shows the dialog, and Cancel keeps every move;
  * "Don't save" opens the file;
  * with the Settings switch off, the file opens without a dialog.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "one Save writes .json and .yaml, and opening a file asks first"
SLOW = True

NAME = "qc_unsaved_prompt"

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK UNS~" + s); }
var asked = 0;
window.confirm = function(){ asked++; return true; };
function dlgOpen(){ var d = document.getElementById("unsavedDlg"); return !!(d && d.open); }
function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    setAskUnsaved(true);
    keys = [];
    [90, 40, 140].forEach(function(v){ pose = pose.map(function(){ return v; }); addKey(); });
    document.getElementById("projName").value = "%(name)s";
    document.getElementById("projName").dispatchEvent(new Event("input"));
    report("synced=" + document.getElementById("seqName").value);
    await refreshSeqs();
    var ok = await saveAll();
    report("saved=" + ok + "~asked=" + asked + "~dirty=" + isDirty());
    pose = pose.map(function(){ return 60; }); addKey();
    report("edited~dirty=" + isDirty() + "~keys=" + keys.length);
    await refreshSeqs();
    document.getElementById("seqList").value = "%(name)s.yaml";
    var p = editLocalSeq(); await wait(300);
    report("dialog=" + dlgOpen());
    document.getElementById("unsavedCancel").click(); await p;
    report("cancel~keys=" + keys.length + "~dialog=" + dlgOpen());
    p = editLocalSeq(); await wait(300);
    document.getElementById("unsavedDrop").click(); await p; await wait(300);
    report("drop~keys=" + keys.length + "~dirty=" + isDirty());
    pose = pose.map(function(){ return 70; }); addKey();
    setAskUnsaved(false);
    p = editLocalSeq(); await wait(300);
    report("off~dialog=" + dlgOpen()); await p; await wait(300);
    report("off~keys=" + keys.length);
    setAskUnsaved(true);
  }catch(e){ report("ERR-" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
""" % {"name": NAME}


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    seq = F.STUDIO / "sequences" / (NAME + ".yaml")
    proj = F.STUDIO / "projects" / (NAME + ".json")
    extras = [seq, proj, seq.with_name(seq.name + ".bak"), proj.with_name(proj.name + ".bak")]
    for f in extras:
        f.unlink(missing_ok=True)
    fake_serial.reset()
    base, _main = F.start_hub()
    try:
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=30)
        marks = [m[4:] for m in fake_serial.qc_marks if m.startswith("UNS~")]
        bad = [m for m in marks if m.startswith("ERR-")]
        if not t.ok(marks and not bad, "the driver ran without throwing", marks[-3:]):
            return
        t.ok("synced=%s" % NAME in marks, "the two name boxes are one name", marks)
        t.ok("saved=true~asked=0~dirty=false" in marks,
             "Save writes a new name without a question and leaves the page clean", marks)
        t.ok(seq.is_file() and proj.is_file(),
             "one Save wrote BOTH %s.yaml and %s.json" % (NAME, NAME),
             "yaml %s, json %s" % (seq.is_file(), proj.is_file()))
        if proj.is_file():
            t.ok(len(json.loads(proj.read_text(encoding="utf-8")).get("keys", [])) == 3,
                 "and the .json holds the same 3 moves")
        t.ok("edited~dirty=true~keys=4" in marks, "one more keyframe is unsaved work", marks)
        t.ok("dialog=true" in marks, "opening a file while unsaved asks first", marks)
        t.ok("cancel~keys=4~dialog=false" in marks,
             "Cancel closes the question and keeps all 4 moves", marks)
        t.ok("drop~keys=3~dirty=false" in marks,
             "Don't save opens the file (3 moves), clean", marks)
        t.ok("off~dialog=false" in marks and "off~keys=3" in marks,
             "with the Settings switch off, the file opens without asking", marks)
    finally:
        for f in extras:
            f.unlink(missing_ok=True)
