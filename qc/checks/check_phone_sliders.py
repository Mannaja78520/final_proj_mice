"""On a phone, the module's joint sliders stay big enough to drag.

2026-11-23 screenshot review (GPT and Gemini both flagged it, measured here): at 390 px the
label + slider + number box + "now" share one row and flex squeezed every slider to 38 px.
The fix is a minimum width on the slider so the row wraps instead. A page that is fine in
a 1280 px test and unusable in a hand is the kind of bug API tests cannot see.
"""
import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "module page: joint sliders are at least 100 px wide on a 390 px phone"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 20000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  var f = document.createElement("iframe");
  f.style.cssText = "width:390px;height:800px";
  document.body.appendChild(f);
  f.src = "/mod?dev=usb:COM99:67&name=nong-far";
  await ready(f); await sleep(1500);
  var d = f.contentDocument, ws = [];
  var rs = d.querySelectorAll("#jointRows input[type=range]");
  for (var i = 0; i < rs.length; i++) ws.push(Math.round(rs[i].getBoundingClientRect().width));
  qcMark("SLIDERS~" + rs.length + "~" + (ws.length ? Math.min.apply(null, ws) : 0));
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=40)
    marks = list(fake_serial.qc_marks)
    got = [m for m in marks if m.startswith("SLIDERS~")]
    t.ok(bool(got), "the module page showed its joint sliders", marks[-3:])
    if got:
        _, n, narrowest = got[0].split("~")
        t.ok(int(n) >= 8, "all the joints are listed", got[0])
        t.ok(int(narrowest) >= 100, "the narrowest slider is at least 100 px wide on a phone", got[0])
