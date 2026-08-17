"""A movement that crashes may always be previewed — but it only reaches the
robot if a person says so.

Two things were wrong, in opposite directions.

**Run and upload were blocked outright**, with no way past. The check works
from the rig's dimensions, so a rig that does not match the real robot can call
a safe move a crash — and then you are simply stuck, with the arm in front of
you telling you otherwise.

**Play was worse.** It warned "the 3D preview will play so you can see where,
but Run/Upload are blocked", and then `hubPlay()` (or the live sends) drove the
real arm anyway. It said one thing and did another, on the one path where being
wrong bends metal.

So now one gate decides for every route to the arm — Play, Run, upload — and
the preview always plays, because watching where it goes wrong is how you fix
it. Forcing is allowed and is remembered for ONE action: editing the timeline
withdraws it, so a "yes" given for one movement never covers a different one.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a crashing movement previews freely, but only reaches the robot if you force it"
SLOW = True

# Two keyframes that put the arms through each other, so collisionAt() fires.
DRIVER = """
function report(s){ rawCmd("MOVE QCMARK GATE~" + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];

    // Stub the DETECTOR, not the gate. Whether a particular pose collides is
    // collisionAt()'s job and is checked elsewhere; what matters here is what
    // the gate DOES with the answer. Driving it from a stub also means this
    // check keeps working when the rig's dimensions change - hunting for a
    // real colliding pose failed outright on the tuned rig, whose joint
    // limits (25-155) do not let the arms reach each other.
    var realCheck = checkCollisions;
    var fake = [];
    checkCollisions = function(){ return fake; };

    // ---- 1. nothing wrong: never asks, always allows ------------------
    var asked = 0;
    window.confirm = function(){ asked++; return true; };
    fake = [];
    var okSafe = crashGate("TEST");
    out.push("safequiet=" + (asked === 0 && okSafe === true ? "yes" : "no"));

    // ---- 2. a crash, and the person says NO ---------------------------
    fake = ["keyframe 1: left forearm hits the body"];
    asked = 0;
    window.confirm = function(){ asked++; return false; };
    var refused = crashGate("TEST");
    out.push("asked=" + (asked > 0 ? "yes" : "no"));
    out.push("refused=" + (refused === false ? "yes" : "no"));

    // ---- 3. same crash, and the person forces it ----------------------
    window.confirm = function(){ return true; };
    out.push("forced=" + (crashGate("TEST") === true ? "yes" : "no"));

    checkCollisions = realCheck;            // put the real one back
    report(out.join("~"));
  }catch(e){ report("ERR~" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
"""


def _js(src):
    nl = chr(10)
    src = re.sub(r"/\*(?:.|" + nl + r")*?\*/", " ", src)
    return re.sub(r"//[^" + nl + r"]*", " ", src)


def run(t):
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    code = _js(app)

    # ---- one gate, used by every route to the arm ----------------------
    t.contains(code, "function crashGate(", "there is one crash gate")
    for where, label in (("robotRun", "Run on robot"),
                         ("uploadYaml", "upload to the card")):
        i = code.find("function " + where)
        if i < 0:
            i = code.find(where + "(")
        body = code[i:i + 700] if i >= 0 else ""
        t.contains(body, "crashGate", "%s goes through the gate" % label)
        t.ok("checkCollisions(true)" not in body,
             "%s no longer blocks with no way past" % label,
             "a wrong rig would leave you unable to run a safe move")

    # ---- the preview may always run; the ROBOT may not -----------------
    t.contains(code, "previewOnly",
               "a refused movement can still be watched in 3D")
    i = code.find("if (previewOnly) return;")
    j = code.find("hubPlay(playT)")
    t.ok(0 <= i < j,
         "and the hub is not handed a show that was refused",
         "the warning said preview-only while hubPlay drove the real arm")
    t.contains(code, "!previewOnly",
               "nor do the live sends go out")

    # ---- permission does not outlive the timeline it was given for -----
    i = code.find("function bumpKeys()")
    body = code[i:i + 300] if i >= 0 else ""
    t.contains(body, "crashForced = false",
               "editing the timeline withdraws a previous 'run it anyway'")

    # ---- and it really behaves that way in a browser -------------------
    if not browser.available():
        t.give_up("headless Edge not found — the rest needs a browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    # the driver also sends a tagged "done"; take the report that has fields
    marks = [m for m in fake_serial.qc_marks
             if m.startswith("GATE~") and ("=" in m or "ERR" in m)]
    if not t.ok(marks, "the crash-gate driver reported",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    raw = marks[-1][5:]
    if raw.startswith("ERR"):
        t.ok(False, "the driver ran without throwing", raw)
        return
    g = dict(kv.split("=", 1) for kv in raw.split("~") if "=" in kv)
    if not g:
        t.ok(False, "the driver reported usable fields", repr(raw))
        return

    t.eq(g.get("asked"), "yes", "a crashing movement asks before touching the arm")
    t.eq(g.get("refused"), "yes", "answering no stops it")
    t.eq(g.get("forced"), "yes", "answering yes lets it through")
    t.eq(g.get("safequiet"), "yes",
         "and a safe movement is never asked about at all")
