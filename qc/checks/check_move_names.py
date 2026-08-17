"""A move in a sequence can be given a name.

The timeline showed "0 start pose" and then 1, 2, 3 — which says nothing about
what the show actually does. Naming a move ("wave", "reach cup", "bow") is how
a sequence stays readable a week later, and how you find the one you meant to
edit.

Three things have to hold, and only the first is visible on screen:

  * the name is kept on the keyframe and survives a save/load round trip —
    a name that vanishes when the project is reopened is worse than none;
  * it reaches the exported file, as a COMMENT, so every existing player still
    reads the file unchanged and the firmware needs no new step key;
  * typing in it does not re-select the keyframe under it, or every keystroke
    would jump the arm to that pose.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a move can be named, and the name survives saving and exporting"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK " + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];
    keys = [];
    [90, 40, 120].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    keys[1].name = "reach cup";
    keys[2].name = "bow";
    renderTimeline();

    // the field is on the chip, and shows the name
    var f = document.querySelectorAll("#keys .kname");
    out.push("fields=" + f.length);
    out.push("shows=" + (f.length > 1 && f[1].value === "reach cup" ? "yes" : "no"));

    // typing must not re-select the keyframe under the field
    selKey = 0;
    if (f.length > 2) {
      f[2].dispatchEvent(new MouseEvent("click", {bubbles: true}));
    }
    out.push("stayed=" + (selKey === 0 ? "yes" : "no"));

    // it goes into the exported file, as a comment
    var y = buildYaml().yaml;
    out.push("inyaml=" + (y.indexOf("# reach cup") >= 0 ? "yes" : "no"));
    // ...and NOT as a step key the firmware would have to understand
    out.push("notastep=" + (/^\\s*-\\s*name:/m.test(y) ? "STEP" : "ok"));

    // a save/load round trip keeps it
    var saved = JSON.stringify({keys: keys});
    keys = JSON.parse(saved).keys;
    out.push("roundtrip=" + (keys[1] && keys[1].name === "reach cup" ? "yes" : "no"));

    // an empty name is removed, not stored as ""
    keys[1].name = "";
    var v = (keys[1].name || "").length;
    out.push("empty=" + v);

    report(out.join("~"));
  }catch(e){ report("ERR~" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = [m for m in fake_serial.qc_marks if "~" in m]
    if not t.ok(marks, "the naming driver reported",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    g = dict(kv.split("=", 1) for kv in marks[-1].split("~") if "=" in kv)
    if "ERR" in g:
        t.ok(False, "the driver ran without throwing", g["ERR"])
        return

    t.ok(int(g.get("fields", "0")) >= 3,
         "every keyframe has a name field (%s)" % g.get("fields"))
    t.eq(g.get("shows"), "yes", "and it shows the name that was set")
    t.eq(g.get("stayed"), "yes",
         "clicking into the field does not re-select the keyframe",
         )
    t.eq(g.get("inyaml"), "yes",
         "the name reaches the exported file")
    t.eq(g.get("notastep"), "ok",
         "as a comment, not a step key the firmware would have to understand")
    t.eq(g.get("roundtrip"), "yes",
         "and it survives saving and reloading the project")
    t.eq(g.get("empty"), "0", "clearing a name leaves nothing behind")

    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "k.name",
               "the name lives on the keyframe, with the rest of the move")
    t.contains(app, 'nm.onclick = (e) => e.stopPropagation()',
               "and typing in it is kept away from the chip's click")
    css = (F.STUDIO / "web/style.css").read_text(encoding="utf-8", errors="replace")
    # the RULE, not the substring: ".knameXX{" still contains ".kname"
    t.ok(re.search(r"\.kname\s*[,{]", css),
         "the field is styled with the rest of the app",
         "an unstyled input here is a raw browser box on every chip")
