"""A lost tab's unsaved timeline is offered back where the person can SEE it.

2026-11-22 walk-through: after a reload the "Restore it / Discard" question was
written only to the status line at the bottom of the timeline, off screen on
laptops and phones, so the person never learned their work was waiting. The same
question now also sits in the notice line under the tab strip.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the unsaved-work Restore question shows in the notice line"
SLOW = True

DRIVER = """
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function wait(){
  if (typeof offerDraft !== "function" || !keys.length) return setTimeout(wait, 200);
  run().catch(qcFail);
}
async function run(){
  var P = function(v){ pose = pose.map(function(o,j){ return clampJ(j,v); }); };
  P(60); addKey(); P(100); addKey(); await sleep(1200);   // the draft is written 0.4 s after an edit
  var draft = localStorage.getItem(DRAFT_KEY);
  qcMark("draft-" + !!draft);
  keys = [keys[0]]; selKey = 0;                            // what a fresh load looks like
  clearNotice(); offerDraft();
  var box = document.getElementById("notice");
  qcMark("notice-shown-" + (!box.hidden && /unsaved work/.test(box.innerText)));
  var b = document.getElementById("draftRestoreBtn");
  qcMark("button-" + !!b);
  b.click(); await sleep(300);
  qcMark("restored-" + (keys.length === 3));
  qcMark("notice-closed-" + box.hidden);
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
        ("draft-true", "an edit leaves a draft"),
        ("notice-shown-true", "the question is in the notice line, visible on every tab"),
        ("button-true", "with a Restore button"),
        ("restored-true", "Restore brings the three keyframes back"),
        ("notice-closed-true", "and the notice goes away"),
    ):
        t.contains(marks, want, label)
