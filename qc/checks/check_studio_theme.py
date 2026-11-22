"""Studio has its own colour-theme picker, and the 3D backdrop follows it.

2026-11-22 walk-through: Studio wore the hub's theme but had no way to change it,
so someone who opened Studio first could not get a dark page, and a theme picked
later left the 3D view white. The picker is the shared one (themes are discovered
from themes.css), and the backdrop colour is read again on a change.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio's theme picker works and the 3D backdrop follows the theme"
SLOW = True

DRIVER = """
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function wait(){
  if (typeof addKey !== "function" || typeof scene === "undefined" || !document.querySelector("#themePick select")) return setTimeout(wait, 200);
  run().catch(qcFail);
}
async function run(){
  var sel = document.querySelector("#themePick select");
  qcMark("themes-" + (sel.options.length >= 2));
  var ids = Array.prototype.map.call(sel.options, function(o){ return o.value; });
  var other = ids.indexOf("midnight") >= 0 ? "midnight" : ids[ids.length - 1];   // the dark one: its backdrop differs from the light default
  var before = scene.background.getHexString();
  sel.value = other; sel.onchange(); await sleep(300);
  qcMark("attr-" + (document.documentElement.getAttribute("data-theme") === other));
  var want = new THREE.Color(getComputedStyle(document.body).getPropertyValue("--bg").trim()).getHexString();
  qcMark("backdrop-follows-" + (scene.background.getHexString() === want));
  qcMark("backdrop-changed-" + (scene.background.getHexString() !== before));
  qcMark("done");
}
window.addEventListener("load", function(){ setTimeout(wait, 800); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html" % base, seconds=40)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks)
    for want, label in (
        ("themes-true", "the picker offers the hub's themes"),
        ("attr-true", "picking one puts it on the page"),
        ("backdrop-follows-true", "the 3D backdrop takes the theme's colour"),
        ("backdrop-changed-true", "and it really changed"),
    ):
        t.contains(marks, want, label)
