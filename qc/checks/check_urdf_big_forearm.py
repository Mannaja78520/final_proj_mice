"""The CAD hand's tip is measured even from a forearm of 300 000 points.

2026-11-23: with the real SolidWorks forearm (~70 000 points, more with its
pieces) urdfMeshTip did Math.max(...points), which overflows the browser's call
stack (RangeError). The error was swallowed, the tip was never measured and in
the CAD look the hand (and wrist ball) sat at the elbow, the arms looking
broken. Fixture CADs are tiny, so nothing caught it; this feeds the pure
urdfFarEnd a big cloud and checks the answer.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "CAD hand tip: a very big forearm mesh still gives its far end"
SLOW = True

DRIVER = """
function wait(){
  if (typeof urdfFarEnd !== "function" || typeof THREE === "undefined") return setTimeout(wait, 200);
  try {
    var pts = [], n = 300000;
    for (var i = 0; i < n; i++) {           // a bar from the elbow 180 mm along +x, 5 mm thick
      var x = 180 * (i / n);
      pts.push(new THREE.Vector3(x, 5 * Math.sin(i), 5 * Math.cos(i)));
    }
    var r = urdfFarEnd(pts);
    qcMark("far-" + (r && Math.abs(r.mm - 180) < 1) + "-" + (r && Math.round(r.mm)));
    qcMark("dir-" + (r && r.dir.x > 0.99));
    qcMark("done");
  } catch (e) { qcMark("ERROR " + e.message); }
}
window.addEventListener("load", function(){ setTimeout(wait, 800); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html" % base, seconds=30)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "no error (a RangeError was the bug)", marks)
    t.ok("far-true-180" in marks, "the far end is 180 mm along the bar", marks)
    t.ok("dir-true" in marks, "its direction points along the bar", marks)
