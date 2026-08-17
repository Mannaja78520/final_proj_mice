"""Nong Studio's side panel groups by task, and every card is reachable.

The old split was Movement / Setup, which put the robot link, the SD card and
the zero calibration all under "Movement" — so posing meant scrolling past
things you touch once a month. Four task tabs fix that, and introduce exactly
one risk worth guarding: a card that belongs to no tab, or to a tab with no
button, becomes unreachable. The feature is still there and the user simply
cannot get to it.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "side panel is grouped by task, nothing unreachable"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof showTab !== "function") return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    var out = [];
    var tabs = ["pose", "sequence", "robot", "setup"];

    // every card must belong to a tab that exists
    var all = document.querySelectorAll("#side .card");
    var tagged = document.querySelectorAll("#side .card[data-stab]");
    out.push("cards:" + all.length + "/" + tagged.length);
    var bad = [];
    tagged.forEach(function(c){
      if (tabs.indexOf(c.dataset.stab) < 0) bad.push(c.dataset.stab);
    });
    out.push("unknownTabs:" + (bad.length ? bad.join(",") : "none"));

    // each tab shows its own cards and hides the others
    var counts = [];
    tabs.forEach(function(name){
      showTab(name);
      var shown = 0, wrong = 0;
      tagged.forEach(function(c){
        var vis = getComputedStyle(c).display !== "none";
        if (vis && c.dataset.stab === name) shown++;
        if (vis && c.dataset.stab !== name) wrong++;
      });
      counts.push(name + "=" + shown + (wrong ? "!" + wrong : ""));
    });
    out.push("perTab:" + counts.join(","));

    // the old tab name must still work — links and habits point at it
    showTab("move");
    out.push("legacyMove:" + (sideTab === "pose" ? "pose" : sideTab));
    // and nonsense must not blank the panel
    showTab("nope");
    out.push("badName:" + (sideTab === "pose" ? "pose" : sideTab));

    qcMark("T-" + out.join(" ").replace(/ /g, "~"));
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the panel ran clean", marks)
    line = next((m[2:].replace("~", " ") for m in marks if m.startswith("T-")), "")
    if not t.ok(line, "the panel reported its layout", marks):
        return
    got = dict(p.split(":", 1) for p in line.split() if ":" in p)

    # ---- nothing may be stranded ---------------------------------------
    total, tagged = got.get("cards", "0/0").split("/")
    t.eq(total, tagged,
         "every side-panel card belongs to a tab (%s of %s tagged)" % (tagged, total))
    t.eq(got.get("unknownTabs"), "none",
         "no card points at a tab that does not exist")

    # ---- each tab shows its own, and only its own -----------------------
    per = dict(x.split("=") for x in got.get("perTab", "").split(",") if "=" in x)
    for name in ("pose", "sequence", "robot", "setup"):
        v = per.get(name, "0")
        t.ok("!" not in v, "%s tab hides the other tabs' cards" % name,
             "%s cards from another tab were visible" % v.split("!")[-1])
        t.ok(int(v.split("!")[0]) >= 1, "%s tab has cards of its own" % name)

    # ---- old names and bad input ----------------------------------------
    t.eq(got.get("legacyMove"), "pose",
         "the old 'move' tab name still works, so nothing that used it breaks")
    t.eq(got.get("badName"), "pose",
         "an unknown tab name falls back instead of blanking the panel")

    # ---- the four buttons exist and are wired ---------------------------
    html = (F.STUDIO_WEB / "index.html").read_text(encoding="utf-8", errors="replace")
    for tab in ("pose", "sequence", "robot", "setup"):
        t.ok(re.search(r"showTab\('%s'\)" % tab, html),
             "there is a button for the %s tab" % tab)
