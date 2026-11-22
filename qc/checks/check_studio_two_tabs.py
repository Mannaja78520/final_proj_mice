"""A second tab cannot silently replace the first tab's saved work.

2026-11-22 walk-through: tab A saved "twotab"; tab B, opened earlier, typed the
same name and pressed Save. B's list of saved names was the one it drew at load,
so it did not know the name was taken and replaced A's work with no question
(the old file survives only as .bak). Save now asks the hub for the names it
holds at that moment.
"""
import json
from pathlib import Path
import tempfile
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "saving a name another tab just used asks before replacing it"
SLOW = True

DRIVER = """
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function wait(){
  if (typeof saveAll !== "function" || typeof addKey !== "function" || !keys.length) return setTimeout(wait, 200);
  run().catch(qcFail);
}
async function run(){
  var asked = [];
  window.confirm = function(m){ asked.push(m); return window.__answer; };
  pose = pose.map(function(o,j){ return clampJ(j,60); }); addKey();
  pose = pose.map(function(o,j){ return clampJ(j,120); }); addKey();
  document.getElementById("projName").value = "qc_two_tabs";
  // "the other tab" saved this name after this page drew its list
  var other = await Mice.Api.post("/api/save", {name: "qc_two_tabs", project: {keys: [], marker: "other-tab"}});
  qcMark("other-saved-" + other.ok);
  window.__answer = false;
  await saveAll(); await sleep(400);
  qcMark("asked-" + (asked.length === 1 && /qc_two_tabs/.test(asked[0])));
  var cur = await Mice.Api.get("/api/load?kind=projects&name=qc_two_tabs.json");
  qcMark("kept-" + (JSON.stringify(cur.data || {}).indexOf("other-tab") >= 0));
  window.__answer = true;
  await saveAll(); await sleep(400);
  cur = await Mice.Api.get("/api/load?kind=projects&name=qc_two_tabs.json");
  qcMark("replaced-" + (JSON.stringify(cur.data || {}).indexOf("other-tab") < 0));
  qcMark("done");
}
window.addEventListener("load", function(){ setTimeout(wait, 800); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    old_p, old_s = main.PROJECTS, main.SEQUENCES
    with tempfile.TemporaryDirectory(prefix="mice_two_tabs_") as tmp:
        main.PROJECTS = Path(tmp) / "p"
        main.SEQUENCES = Path(tmp) / "s"
        main.PROJECTS.mkdir()
        main.SEQUENCES.mkdir()
        try:
            browser.page(DRIVER, query="%s/studio/_qcdriver.html" % base, seconds=40)
        finally:
            main.PROJECTS, main.SEQUENCES = old_p, old_s
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks)
    for want, label in (
        ("other-saved-true", "the other tab's save reached the hub"),
        ("asked-true", "Save asks before replacing a name that appeared since the list was drawn"),
        ("kept-true", "and Cancel leaves the other tab's file alone"),
        ("replaced-true", "OK replaces it"),
    ):
        t.contains(marks, want, label)
