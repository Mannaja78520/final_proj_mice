"""Studio's header is ONE row at 1440 px wide.

2026-11-23 old-vs-new screenshot review (GPT and Gemini both flagged it): the theme picker, the
language picker and the technical switch were added to the header on 2026-11-22 and it wrapped to
two rows at 1440 px, taking about 45 px from the 3D view and the side panel for everyone.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio desktop: the header stays one row at 1440 px"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.querySelector("header.topbar .topbar-end") && d.getElementById("themePick") && d.getElementById("themePick").children.length > 0; } catch (e) { return false; } }, 25000); }
async function run(){
  localStorage.setItem("mice.lang", "en");
  var f = document.createElement("iframe");
  f.style.cssText = "width:1440px;height:900px";
  document.body.appendChild(f);
  f.src = "/studio/";
  await ready(f);
  await new Promise(function(r){ setTimeout(r, 800); });
  var h = f.contentDocument.querySelector("header.topbar").getBoundingClientRect().height;
  qcMark("HEADER~" + Math.round(h));
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
    got = [m for m in fake_serial.qc_marks if m.startswith("HEADER~")]
    t.ok(bool(got), "Studio loaded at desktop width", fake_serial.qc_marks[-3:])
    if got:
        t.ok(int(got[0].split("~")[1]) <= 80, "the header is one row tall (<= 80 px)", got[0])
