"""The robot's start pose can be set on the module page itself, not only in Studio.

User 2026-09-17 (A26-47), with nong #67 on the bench: *in the robot still cannot
adjust the robot home pose and zero position*. The board already had `NEUTRAL`,
and Studio could send it, but the module website had no way to set it at all:
its only button said *Neutral* and sent `HOME`, which MOVES to the pose and
never changes it. The Set zero button also said *home = 90 deg*, which stopped
being true when SETZERO learned to keep the chosen start angles.

So the page gets a Start pose card: *Keep where the arm is now as home* (the new
`NEUTRAL HERE`, which reads the board's own position rather than the page's
sliders) and ten start-angle boxes with a Save button.

Asserted on `fake_serial.NONG.neutral` - written by the fake module's handling
of the line - never on what the page says about itself.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "the module page sets the robot's start pose (here, or typed)"
SLOW = True

ARM = [91.0, 140.0, 72.0, 95.0, 88.0, 35.0, 101.0, 79.0, 93.0, 86.0]
TYPED = [95, 150, 90, 80, 96, 30, 100, 70, 92, 88]

PAGE = """
<style>html,body{margin:0}#f{width:1200px;height:900px;border:0}</style>
<iframe id="f" src="/mod?dev=usb%%3ACOM99"></iframe>
<script>
var TYPED = %s;
function say(s){ qcMark("HOME " + s); }
// Wait for the frame to BE there, then settle as before (A26-94): a fixed
// sleep measured an empty page under a full gate and reported nothing.
qcWaitFor(function(){
  var fr = document.getElementById("f");
  return fr && fr.contentWindow && fr.contentDocument
      && fr.contentDocument.readyState === "complete"
      && fr.contentDocument.body && fr.contentDocument.body.children.length;
}, 8000).then(function(){
setTimeout(function(){
  try{
    var fr = document.getElementById('f');
    var w = fr.contentWindow, d = fr.contentDocument;
    var errs = 0;
    w.addEventListener('error', function(){ errs++; });
    setTimeout(function(){
      var out = [];
      out.push("card=" + (d.getElementById('homeCard') ? "yes" : "no"));
      out.push("boxes=" + d.querySelectorAll('#homeRows input[type=number]').length);
      var v1 = d.getElementById('hv1');
      out.push("loaded1=" + (v1 ? v1.value : "-"));
      say(out.join(" "));
      d.getElementById('homeHereBtn').click();
      setTimeout(function(){
        qcMark("HOMEHERE stat=" + d.getElementById('homeStat').textContent
          .replace(/[^a-z ]/gi, "").trim().replace(/ +/g, "_").slice(0, 40)
          + " shown5=" + d.getElementById('hv5').value);
        qcMark("QC TYPED");
        for (var i = 0; i < 10; i++) d.getElementById('hv' + i).value = TYPED[i];
        d.getElementById('homeSaveBtn').click();
        setTimeout(function(){
          qcMark("HOMESAVE stat=" + d.getElementById('homeStat').textContent
            .replace(/[^a-z ]/gi, "").trim().replace(/ +/g, "_").slice(0, 40)
            + " errs=" + errs);
          qcMark("done");
        }, 3000);
      }, 3000);
    }, 6000);
  } catch (e) { qcMark("HOME ERR=" + String(e).slice(0, 60)); qcMark("done"); }
}, 3000); });
</script>
"""


def _kv(marks, head):
    got = [m for m in marks if m.startswith(head + " ")]
    if not got:
        return None
    return dict(kv.split("=", 1) for kv in got[-1][len(head) + 1:].split(" ") if "=" in kv)


def run(t):
    ui = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    src = (F.FIRMWARE / "src/modules/nong/NongModule.cpp").read_text(encoding="utf-8",
                                                                     errors="replace")
    here = src[src.find('equalsIgnoreCase("HERE")'):]
    here = here[:here.find("return true;")]
    t.ok("cur_[i]" in here and "saveCalSoon" in here,
         "NEUTRAL HERE takes the board's real position and saves it",
         "without cur_ it is not where the arm is; without a save it is gone on reboot")
    t.ok('forward("NEUTRAL" + line)' in here,
         "the 2-ESP partner is sent the numbers, not HERE",
         "the partner's own position can lag, so HERE there would be a different pose")
    t.ok(not re.search(r"<button[^>]*cmd\('HOME'\)[^>]*>Neutral<", ui),
         "no button called Neutral that only moves the arm",
         "that was the only 'home' control on the page, and it could not set home")
    t.ok("home = 90" not in ui,
         "the zero card no longer claims home is 90 deg",
         "SETZERO keeps the chosen start angles since A26-3")

    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    fake_serial.NONG.joints = list(ARM)
    fake_serial.NONG.neutral = [90.0, 120.0, 90.0, 90.0, 90.0, 60.0, 90.0, 90.0, 90.0, 90.0]
    base, main = F.start_hub()
    browser.raw_page(PAGE % ("[" + ",".join(str(v) for v in TYPED) + "]"), base, seconds=30)
    marks = list(fake_serial.qc_marks)

    first = _kv(marks, "HOME")
    if not t.ok(first and "ERR" not in first, "the module page reported back",
                "it never ran or threw: %r" % (marks[-4:],)):
        return
    t.eq(first.get("card"), "yes", "the start-pose card is on the module page")
    t.eq(first.get("boxes"), "10", "with a start angle box for every joint")
    t.eq(first.get("loaded1"), "120",
         "filled from what the BOARD holds, not a default")

    # the fake records NEUTRAL HERE as neutral = its joints; the typed Save
    # comes after the QC TYPED mark, so the order of the wire proves which is which
    here_mark = _kv(marks, "HOMEHERE") or {}
    wire = [c for _, c in fake_serial.wire]
    t.ok("NEUTRAL HERE" in wire, "the button sent NEUTRAL HERE to the module",
         "wire: %r" % [c for c in wire if c.startswith("NEUTRAL")])
    t.eq(here_mark.get("shown5"), "35",
         "and the boxes now show where the arm really was")
    t.ok(here_mark.get("stat", "").startswith("saved"),
         "the page says it was saved (%s)" % here_mark.get("stat"))

    save = _kv(marks, "HOMESAVE") or {}
    t.eq([round(x) for x in fake_serial.NONG.neutral], TYPED,
         "typed start angles reached the module, every joint in order")
    t.ok(save.get("stat", "").startswith("saved"),
         "and the page says so (%s)" % save.get("stat"))
    t.eq(save.get("errs"), "0", "the page raised no script error")
