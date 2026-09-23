"""A flat view stays flat, and the hand drags in it without Shift held.

User 2026-09-23: *when i select the 2d plan make can drag the move only in 2d
not 3d too i see in 2d but the arm when am drag it in 3d so i cannot drag it in
2d anymore now*.

Picking Front already snapped the camera square-on and set the drag plane to
XY. Two things then undid it:

  * OrbitControls still rotated. A plain left-drag is how you take hold of the
    scene, and it orbited - so the flat view lasted until the first drag, and
    after that the plane the person had chosen no longer matched what they were
    looking at. The view-cube button stayed lit the whole time, which made it
    worse: the page said Front while showing something else.
  * dragging a hand needed SHIFT. Shift exists only because a plain drag
    orbits. In a flat view nothing orbits, so the requirement was pure
    ceremony - and it was the one gesture the 2D plane exists for.

So: a plane view turns rotation off and dragging a hand works with no modifier;
the 3D button turns both back on. Asserted in a real browser on the live
OrbitControls flag and on the pose the drag actually produced - not on what the
page says about itself.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a flat view cannot be orbited out of, and drags the hand without Shift"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK FLATV~" + s); }
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    var canvas = renderer.domElement;
    setView("iso");
    var isoRotate = controls.enableRotate, isoFlat = flatView();

    setView("front");
    var frontRotate = controls.enableRotate;
    var frontPlane = document.getElementById("dragPlane").value;
    var frontFlat = flatView();

    // Drag the LEFT wrist ball with NO shift held. Grab it where it really is
    // on screen, so this fails if picking stops finding it at all.
    var ball = wristBalls[0];
    var before = pose.slice();
    var p = ball.getWorldPosition(new THREE.Vector3()).project(activeCam());
    var r = canvas.getBoundingClientRect();
    var x = r.left + (p.x + 1) / 2 * r.width;
    var y = r.top + (1 - p.y) / 2 * r.height;
    function send(type, cx, cy, shift){
      canvas.dispatchEvent(new PointerEvent(type, {clientX: cx, clientY: cy,
        button: 0, buttons: 1, pointerId: 3, shiftKey: !!shift, bubbles: true}));
    }
    send("pointerdown", x, y, false);
    var grabbed = !!drag && drag.kind === "ik";
    window.dispatchEvent(new PointerEvent("pointermove", {clientX: x + 60,
      clientY: y - 40, button: 0, buttons: 1, pointerId: 3, bubbles: true}));
    window.dispatchEvent(new PointerEvent("pointerup", {clientX: x + 60,
      clientY: y - 40, button: 0, pointerId: 3, bubbles: true}));
    var moved = 0;
    for (var i = 0; i < NJ; i++) moved = Math.max(moved, Math.abs(pose[i] - before[i]));

    setView("iso");
    var backRotate = controls.enableRotate, backFlat = flatView();

    report("isoRotate=" + isoRotate + "~isoFlat=" + isoFlat +
           "~frontRotate=" + frontRotate + "~frontPlane=" + frontPlane +
           "~frontFlat=" + frontFlat + "~grabbed=" + grabbed +
           "~moved=" + moved.toFixed(2) +
           "~backRotate=" + backRotate + "~backFlat=" + backFlat);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = [m[6:] for m in fake_serial.qc_marks if m.startswith("FLATV~")]
    got = next((m for m in marks if m.startswith("isoRotate=")), "")
    if not t.ok(got, "the driver measured the view", marks):
        return
    v = dict(kv.split("=", 1) for kv in got.split("~"))

    t.ok(v.get("isoRotate") == "true" and v.get("isoFlat") == "false",
         "the free 3D view still orbits", v)
    t.ok(v.get("frontRotate") == "false",
         "a flat view cannot be orbited out of",
         "a plain drag used to rotate the camera away from the plane while the "
         "view-cube button still said Front: %s" % v)
    t.eq(v.get("frontPlane"), "xy", "and the drag plane follows the view")
    t.ok(v.get("frontFlat") == "true", "flatView() says the view is flat", v)
    t.ok(v.get("grabbed") == "true",
         "dragging the hand in a flat view needs no Shift held",
         "Shift exists only because a plain drag orbits, and in a flat view "
         "nothing orbits: %s" % v)
    t.ok(float(v.get("moved") or 0) > 0.5,
         "and the drag really moved the arm",
         "joints changed by at most %s deg" % v.get("moved"))
    t.ok(v.get("backRotate") == "true" and v.get("backFlat") == "false",
         "pressing 3D turns the view loose again",
         "a lock with no way out would be worse than the bug: %s" % v)
