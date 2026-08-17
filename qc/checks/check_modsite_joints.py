"""The nong joint sliders really appear on the module website, over a cable.

This exists because they did not, and nothing noticed. `isNong` was used to
decide whether to build them but was never defined anywhere — a ReferenceError
thrown in the middle of the status handler. Everything below that line stopped
too, so the sliders, the servo-travel readout and the rest simply never
appeared. The data was perfect the whole time: over USB the status carried
`caps:[... "joints" ...]` and all ten angles.

Every check that existed passed. `modsite_tabs` proved the tabs work,
`transports` proved commands round-trip on the cable, `check_registries` proved
each card's visibility is expressed as `has(...)`. None of them ever asked the
question a person asks first: **are the sliders on the screen?**

So this drives the real page, served the way the hub serves it for a cable
(`/mod?dev=usb:COM99`), and asserts on the rendered DOM. It also fails on any
console error, because a ReferenceError anywhere in that handler silently
truncates the page.
"""
import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "the nong joint sliders render on the module site over USB"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:1200px;height:900px;border:0}</style>
<iframe id="f" src="/mod?dev=usb%3ACOM99"></iframe>
<script>
function done(s){ qcMark("JOINTS " + s); qcMark("done"); }
var errs = 0;
setTimeout(function(){
  try{
    var fr = document.getElementById('f');
    var w = fr.contentWindow, d = fr.contentDocument;
    // a ReferenceError inside the status handler is exactly the bug this
    // check exists for, so treat ANY page error as a failure
    w.addEventListener('error', function(){ errs++; });
    setTimeout(function(){
      var out = [];
      var box = d.getElementById('jointRows');
      out.push("box=" + (box ? "yes" : "no"));
      out.push("rows=" + (box ? box.querySelectorAll('.row').length : 0));
      out.push("sliders=" + d.querySelectorAll('#jointRows input[type=range]').length);
      out.push("numbers=" + d.querySelectorAll('#jointRows input[type=number]').length);
      // the live readout after the sliders proves the handler did not stop
      out.push("now0=" + (d.getElementById('jnow0') ? "yes" : "no"));
      var s0 = d.getElementById('j0');
      out.push("value0=" + (s0 ? s0.value : "-"));
      out.push("errs=" + errs);
      done(out.join(" "));
    }, 6000);
  } catch (e) { done("ERR=" + String(e).slice(0,60)); }
}, 3000);
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(PAGE, base, seconds=26)

    marks = [m for m in fake_serial.qc_marks if m.startswith("JOINTS ")]
    if not t.ok(marks, "the module page reported back",
                "it never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][7:].split(" ") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the driver ran without throwing", got["ERR"])
        return

    t.eq(got.get("box"), "yes", "the joints card is on the page")
    t.ok(int(got.get("sliders", "0")) == 10,
         "all ten joints have a slider (%s)" % got.get("sliders"),
         "the sliders never rendered — this is the bug, on a real page")
    t.ok(int(got.get("numbers", "0")) == 10,
         "and a number box each (%s)" % got.get("numbers"))
    t.eq(got.get("now0"), "yes",
         "the live position readout is there too")
    t.ok(got.get("value0") not in (None, "-", ""),
         "and a slider carries the robot's actual angle (%s)" % got.get("value0"),
         "built, but never filled from the module")
    t.ok(got.get("errs") == "0",
         "the page raised no script error",
         "a throw in the status handler truncates everything after it")

    # the definition must exist at all — the whole bug was that it did not
    ui = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    t.ok("const isNong" in ui or "let isNong" in ui or "var isNong" in ui,
         "isNong is actually defined, not just used",
         "using an undefined name throws and stops the whole handler")
