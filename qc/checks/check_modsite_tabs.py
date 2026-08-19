"""The module website shows one group of cards at a time, and only what you may see.

Thirteen cards in a single column meant scrolling past the lift controls to
reach the SD card. Tabs fix that — but they introduce the failure this guards:
TWO things now decide whether a card is on screen (which tab is open, and
whether Setup is unlocked), and if they are decided in two places a config card
eventually appears to someone who has not logged in.

Driven in a real browser through the hub, which serves the board's own page.
"""
import subprocess
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "module site tabs, and the login gate they must respect"
SLOW = True

DRIVER = """
// The module page sets document.title from the module's NAME, so a title-based
// report is overwritten. Send it down the wire instead, where the fake module
// records it — the same channel every other browser check uses.
// XHR, not fetch: this page carries the hub's transport shim, which rewrites
// every /api/ fetch into /api/dev/... — a report sent with fetch came back as
// /api/dev/dev/cmd and vanished. The shim does not wrap XMLHttpRequest.
function report(s){
  try{
    var x = new XMLHttpRequest();
    x.open("GET", "/api/usb/cmd?port=COM99&id=0&c=" +
           encodeURIComponent("MOVE QCMARK " + s.replace(/ /g, "~")), true);
    x.send();
  }catch(e){}
}
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];
    function vis(sel){
      var e = document.querySelector(sel);
      if (!e) return "missing";
      return getComputedStyle(e).display === "none" ? "hidden" : "shown";
    }
    function countShown(tab){
      var n = 0;
      document.querySelectorAll('[data-tab="' + tab + '"]').forEach(function(e){
        if (getComputedStyle(e).display !== "none") n++;
      });
      return n;
    }
    out.push("tabs:" + document.querySelectorAll(".mtab").length);

    // start: Control, and NOTHING from setup — nobody has logged in
    showTab("control");
    out.push("ctlOnControl:" + countShown("control"));
    out.push("setupOnControl:" + countShown("setup"));
    out.push("filesOnControl:" + countShown("files"));

    // the Setup tab, still logged OUT: the login card shows, the config does not
    showTab("setup");
    out.push("loginVisible:" + vis("#loginCard"));
    out.push("settingsLockedOut:" + vis(".card.setupCard"));

    // pretend the login succeeded — the SAME rule must now reveal them
    auth = { user: "qc", pass: "x" };
    applyTabs();
    out.push("settingsAfterLogin:" + vis(".card.setupCard"));
    // ...and they must still be hidden on another tab
    showTab("control");
    out.push("settingsOnOtherTab:" + vis(".card.setupCard"));

    // files tab carries the SD card and console
    showTab("files");
    out.push("filesOnFiles:" + countShown("files"));
    out.push("ctlOnFiles:" + countShown("control"));

    report(out.join(" "));
  }catch(e){ report("ERR " + e.message); }
  // Say so, rather than leaving the runner to guess with a stopwatch.
  qcMark("done");
}, 900); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    _drive(base)
    marks = [m.replace("~", " ") for m in fake_serial.qc_marks]
    if not t.ok(marks and not any("ERR" in m for m in marks),
                "the module site loaded and ran", marks or "(nothing reported)"):
        return
    got = dict(p.split(":", 1) for p in marks[-1].split() if ":" in p)

    t.eq(got.get("tabs"), "3", "the page has its three tabs")

    # ---- one group at a time ------------------------------------------
    t.ok(int(got.get("ctlOnControl", 0)) >= 1,
         "the Control tab shows the module's own controls")
    t.eq(got.get("setupOnControl"), "0", "and no setup card leaks onto it")
    t.eq(got.get("filesOnControl"), "0", "nor the files cards")
    t.ok(int(got.get("filesOnFiles", 0)) >= 2,
         "the files tab carries sequences, SD and the console")
    t.eq(got.get("ctlOnFiles"), "0", "and the controls are put away there")

    # ---- THE risk: the login gate must survive the tabs ---------------
    t.eq(got.get("loginVisible"), "shown",
         "the Setup tab offers the login")
    t.eq(got.get("settingsLockedOut"), "hidden",
         "but the config cards stay hidden until you are logged in")
    t.eq(got.get("settingsAfterLogin"), "shown",
         "logging in reveals them on that tab")
    t.eq(got.get("settingsOnOtherTab"), "hidden",
         "and they are still put away when you leave the tab")

    # ---- one rule, not two -------------------------------------------
    web = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    t.contains(web, "function applyTabs",
               "one function decides visibility")
    t.eq(web.count("querySelectorAll('.setupCard').forEach(e=>e.style.display=e.dataset.disp"), 0,
         "the old separate login show/hide is gone, so the two cannot disagree")


def _drive(base):
    """The module page exactly as the hub serves it, driven in real time.

    NOT --dump-dom: the report goes over the wire (a real fetch), and dump-dom
    exits as soon as the load settles — before the fetch lands. Real time, then
    kill, like every other browser check here.
    """
    import time
    web = F.STUDIO_WEB
    drv = web / "_qcmod.html"
    html = F.get(base + "/mod?dev=usb%3A" + fake_serial.PORT)[1]
    # This check builds its own page rather than going through
    # browser.page, so it has to ask for the login script itself: its
    # report goes to /api/usb/cmd, which needs a session now. Without it
    # the page runs fine and simply cannot be heard, which reads as
    # "nothing reported" — a failure that points at the wrong thing.
    drv.write_text(browser._login_js() + html          # noqa: SLF001
                   + "<script>\n" + DRIVER + "\n</script>", encoding="utf-8")
    browser.SCRATCH.mkdir(parents=True, exist_ok=True)
    prof = str(browser.SCRATCH / ("profile_mod_%d" % int(time.time() * 1000)))
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Start-Process -FilePath '%s' -ArgumentList "
                        "'--headless=new','--disable-gpu','--no-sandbox',"
                        "'--no-first-run','--disable-extensions','--%s',"
                        "'--user-data-dir=%s',"
                        "'%s/studio/_qcmod.html?dev=usb%%3A%s' -NoNewWindow"
                        % (browser.EDGE, browser.TAG, prof, base, fake_serial.PORT)],
                       timeout=60)
        # Wait for the page to report, not for the clock. A flat sleep is a
        # bet on how fast the machine is today: under the full suite this one
        # expired mid-run and failed a promote for a page that was working.
        browser._wait_for_done(14)            # noqa: SLF001 - same wait as raw_page
    finally:
        drv.unlink(missing_ok=True)
        browser.kill()
        browser._rmtree(prof)
