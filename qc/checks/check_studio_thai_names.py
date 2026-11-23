"""Studio file names: different Thai (or other non-ASCII) names never meet on one file.

2026-11-23 case review (GPT: odd project names, mixed scripts): cleanName() turned every
character outside A-Z a-z 0-9 _ . - into "_", so "ท่าเต้น" and "ท่ารำ" both became "_" and the
second Save asked to replace the first (or, without the question, replaced it). The robot's SD
card and the saved files take ASCII names, so the fix keeps ASCII where it can and adds a short
fixed code of the typed name when letters had to go: the same name gives the same file, different
names never share one.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio: Thai file names stay different from each other and from run to run"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && f.contentWindow.cleanName; } catch (e) { return false; } }, 25000); }
async function run(){
  var f = document.createElement("iframe");
  f.style.cssText = "width:1000px;height:700px";
  document.body.appendChild(f);
  f.src = "/studio/";
  await ready(f);
  var c = f.contentWindow.cleanName;
  var names = ["my_move", "ท่าเต้น", "ท่ารำ", "ท่าเต้น", "my ท่า", "日本語", "a b", "../x"];
  qcMark("N~" + JSON.stringify(names.map(function(n){ return c(n); })));
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=60)
    import json
    got = [m for m in fake_serial.qc_marks if m.startswith("N~")]
    t.ok(bool(got), "Studio answered", fake_serial.qc_marks[-3:])
    if not got:
        return
    out = json.loads(got[0][2:])
    mv, d1, d2, d1b, mixed, jp, ab, up = out
    t.ok(mv == "my_move" and ab == "a_b", "plain names are cleaned as before", out)
    t.ok(d1 != d2 and d1 != "_" and d2 != "_", "two different Thai names do not become the same file", out)
    t.ok(d1 == d1b, "the same Thai name always gives the same file", out)
    t.ok(all(x.isascii() and x for x in (d1, d2, mixed, jp)), "every file name is plain ASCII", out)
    t.ok(mixed.startswith("my_"), "a name that starts in ASCII keeps that part", mixed)
    t.ok("/" not in up and "\\" not in up, "no path characters survive", up)
