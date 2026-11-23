"""Studio on a phone: both rows of the side tabs clear the Stop strip on first load.

2026-11-23 screenshot review: at 390x844 the 3D view took 44vh under a six-row header, so
Shows / Robot / Setup sat half under the Stop/Help strip until you scrolled. A person
sees half-hidden buttons and thinks the page is broken. The view is 34vh now.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio phone: every side tab is fully above the Stop strip on first load (390x844)"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.getElementById("tabBtnSetup") && f.contentWindow.palmMarks && f.contentWindow.palmMarks.length === 2; } catch (e) { return false; } }, 25000); }
async function run(){
  var f = document.createElement("iframe");
  f.style.cssText = "width:390px;height:844px";
  document.body.appendChild(f);
  f.src = "/studio/";
  await ready(f);
  await new Promise(function(r){ setTimeout(r, 800); });
  var d = f.contentDocument;
  var tabs = ["Move", "Seq", "Video", "Shows", "Robot", "Setup"].map(function(n){ return d.getElementById("tabBtn" + n).getBoundingClientRect(); });
  var low = Math.max.apply(null, tabs.map(function(b){ return b.bottom; }));
  var strip = 844 - 72;              // style.css: body::after strip is 72px high
  qcMark("TABS~" + Math.round(low) + "~" + strip);
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
    got = [m for m in fake_serial.qc_marks if m.startswith("TABS~")]
    t.ok(bool(got), "Studio loaded on a phone", fake_serial.qc_marks[-3:])
    if got:
        _, low, strip = got[0].split("~")
        t.ok(int(low) <= int(strip), "the lowest tab ends above the Stop strip (%s <= %s)" % (low, strip), got[0])
