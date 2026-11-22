"""Studio's timeline has Undo and Redo, so one wrong tap on Delete is not final.

Found 2026-11-22 walking Studio as a newcomer: Delete removed a keyframe with
no question and no way back. Undo (button and Ctrl+Z) now returns the timeline
as it was before the last edit, Redo puts it back, a drag of one value counts as
one step, and opening a file starts a clean history.

Driven in the real browser; asserts on the keyframes themselves and on the keys
a person would press, not on what the buttons say.
"""
import browser
import fake_serial

AREA = "studio"
TITLE = "timeline Undo/Redo: delete, add and Ctrl+Z come back"
SLOW = True

DRIVER = """
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
function wait(){
  if (typeof addKey !== "function" || typeof timelineUndo === "undefined" || !keys.length)
    return setTimeout(wait, 200);
  run().catch(qcFail);
}
async function run(){
  var P = function(v){ pose = pose.map(function(o,j){ return clampJ(j,v); }); };
  P(60);  addKey(); await sleep(800);
  P(120); addKey(); await sleep(800);
  P(30);  addKey(); await sleep(800);
  qcMark("three-" + (keys.length === 4));
  qcMark("undo-enabled-" + !document.getElementById("undoBtn").disabled);

  selKey = 2; delKey(); await sleep(800);
  qcMark("deleted-" + (keys.length === 3));
  document.getElementById("undoBtn").click(); await sleep(200);
  qcMark("undo-restores-" + (keys.length === 4 && keys[2].pose[0] === 120));
  qcMark("undo-selects-" + (selKey === 2));
  document.getElementById("redoBtn").click(); await sleep(200);
  qcMark("redo-deletes-" + (keys.length === 3));
  document.getElementById("undoBtn").click(); await sleep(200);

  // the key a person presses, from the page body (not from a text box)
  document.body.focus();
  window.dispatchEvent(new KeyboardEvent("keydown", {key: "z", ctrlKey: true, bubbles: true}));
  await sleep(200);
  qcMark("ctrl-z-" + (keys.length === 3));
  window.dispatchEvent(new KeyboardEvent("keydown", {key: "y", ctrlKey: true, bubbles: true}));
  await sleep(200);
  qcMark("ctrl-y-" + (keys.length === 4));

  // a drag of one value is ONE step: twenty small edits within a moment
  var before = JSON.stringify(keys[1].pose);
  for (var i = 0; i < 20; i++) { keys[1].pose[0] = 100 + i; bumpKeys(); await sleep(15); }
  document.getElementById("undoBtn").click(); await sleep(200);
  qcMark("drag-one-step-" + (JSON.stringify(keys[1].pose) === before));

  // a typed field is not hijacked: Ctrl+Z inside a text box leaves the timeline alone
  var n = keys.length; delKey(); await sleep(800);
  var box = document.getElementById("projName"); box.focus();
  box.dispatchEvent(new KeyboardEvent("keydown", {key: "z", ctrlKey: true, bubbles: true}));
  await sleep(200);
  qcMark("text-box-keeps-its-own-undo-" + (keys.length === n - 1));

  // opening a file starts a clean history
  timelineUndo.reset();
  qcMark("reset-clears-" + (document.getElementById("undoBtn").disabled &&
                            document.getElementById("redoBtn").disabled));
  qcMark("done");
}
window.addEventListener("load", function(){ setTimeout(wait, 800); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    import qc as F
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html" % base, seconds=40)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks)
    for want, label in (
        ("three-true", "three keyframes were added"),
        ("undo-enabled-true", "Undo is available after an edit"),
        ("deleted-true", "Delete removed the keyframe"),
        ("undo-restores-true", "Undo brings the deleted keyframe back, unchanged"),
        ("undo-selects-true", "and selects it"),
        ("redo-deletes-true", "Redo deletes it again"),
        ("ctrl-z-true", "Ctrl+Z undoes"),
        ("ctrl-y-true", "Ctrl+Y redoes"),
        ("drag-one-step-true", "a drag of one value is a single Undo step"),
        ("text-box-keeps-its-own-undo-true", "Ctrl+Z in a text box does not touch the timeline"),
        ("reset-clears-true", "opening a file clears the history"),
    ):
        t.contains(marks, want, label)
