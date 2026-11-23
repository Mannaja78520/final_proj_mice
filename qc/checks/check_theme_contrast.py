"""Every theme keeps its text readable (WCAG AA) on every page.

2026-11-23: both AI reviewers called the dark-red Stop/"Switch motors off" buttons low-contrast;
measured here: TV "Speak" was 1.84:1 in Midnight (white on a pale accent), the STOP buttons were
3.5-3.9:1 in Indigo (the DEFAULT theme) and Daylight. Nobody had measured a contrast ratio. This
does, for every theme in themes.css and every hub page, so a new colour cannot quietly fail.
The audit is tools/visual/contrast.js (the same file a person can paste into a console).
"""
import json
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "text contrast is at least 4.5:1 (3:1 for large text) in every theme on every page"
SLOW = True

HERE = Path(F.CODE) / "tools" / "visual"
# The four CSS themes + every built-in theme pack (shared/web/themes/<id>/): a new pack is measured with no edit here.
THEMES = ["indigo", "midnight", "daylight", "carnival"] + sorted(
    d.name for d in (Path(F.CODE) / "shared" / "web" / "themes").iterdir() if d.is_dir())

DRIVER = """
__AUDIT__
var PAGES = __PAGES__, THEMES = __THEMES__;
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 20000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  localStorage.setItem("mice.lang", "en");
  for (var ti = 0; ti < THEMES.length; ti++) {
    localStorage.setItem("mice_theme", THEMES[ti]);
    for (var pi = 0; pi < PAGES.length; pi++) {
      var f = document.createElement("iframe");
      f.style.cssText = "width:1200px;height:800px";
      document.body.appendChild(f);
      f.src = PAGES[pi].url;
      await ready(f); await sleep(PAGES[pi].wait || 1200);
      try {
        var bad = contrastAudit(f.contentDocument);
        qcMark("CONTRAST~" + THEMES[ti] + "~" + PAGES[pi].id + "~" + bad.length + "~" + (bad[0] || "").replace(/[^a-zA-Z0-9.]/g, "_").slice(0, 40));
      } catch (e) { qcMark("ERR~" + PAGES[pi].id); }
      f.remove();
    }
  }
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    cfg = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
    pages = [{"id": p["id"], "url": p["url"], "wait": p.get("wait")} for p in cfg["pages"] if p["id"] not in ("hub", "module")]
    drv = (DRIVER.replace("__AUDIT__", (HERE / "contrast.js").read_text(encoding="utf-8"))
           .replace("__PAGES__", json.dumps(pages)).replace("__THEMES__", json.dumps(THEMES)))
    browser.raw_page("<h1>wrapper</h1><script>" + drv + "</script>", base, seconds=240)
    marks = list(fake_serial.qc_marks)
    t.ok("done" in marks, "the audit finished", marks[-3:])
    got = [m for m in marks if m.startswith("CONTRAST~")]
    t.ok(len(got) >= len(pages) * len(THEMES), "every page was audited in every theme", len(got))
    for m in got:
        _, theme, pid, n = m.split("~")[:4]
        t.ok(int(n) == 0, "%s / %s: no text below the contrast floor" % (theme, pid), m)
