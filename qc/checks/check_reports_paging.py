"""Problem reports: a screenful at a time, not every report ever sent.

2026-11-23 screenshot review: the tab drew 93 rows at once (most are automatic "Studio stopped
answering" notes), so a phone scrolled for a minute and the page grew with every freeze. The tab
now draws 40 and a "Show older reports" button adds 40 more.
"""
import glob
import os

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "Problem reports: 40 rows first, a button for older ones"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 20000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  for (var i = 0; i < 55; i++)
    await fetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "qc paging " + i, page: "qc", module: "m", build: "1" }) });
  var f = document.createElement("iframe");
  f.style.cssText = "width:390px;height:800px";
  document.body.appendChild(f);
  f.src = "/";
  await ready(f); await sleep(1200);
  f.contentWindow.showTab("complaints"); await sleep(1500);
  var d = f.contentDocument;
  var rows = d.querySelectorAll("#complaintsList .mod").length;
  var more = d.querySelector("#complaintsList .more-reports");
  qcMark("FIRST~" + rows + "~" + (more ? 1 : 0));
  if (more) { more.click(); await sleep(300); }
  qcMark("AFTER~" + d.querySelectorAll("#complaintsList .mod").length);
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
    marks = list(fake_serial.qc_marks)
    # the hub keeps every report as a file next to its code: do not leave 55 test notes behind
    for f in glob.glob(os.path.join(str(_main.REPORTS), "*.json")):
        try:
            if "qc paging" in open(f, encoding="utf-8").read():
                os.remove(f)
        except OSError:
            pass
    first = [m for m in marks if m.startswith("FIRST~")]
    after = [m for m in marks if m.startswith("AFTER~")]
    t.ok(bool(first) and bool(after), "the reports tab answered", marks[-3:])
    if first and after:
        _, rows, more = first[0].split("~")
        t.ok(int(rows) == 40, "only 40 reports are drawn at first", first[0])
        t.ok(more == "1", "a button offers the older ones", first[0])
        t.ok(int(after[0].split("~")[1]) > 40, "the button adds more rows", after[0])
