"""Rebuilding the robot must not leak GPU memory.

Reported from the bench: "when I run Nong Studio my PC crashes a lot". Not an
error message — the machine falling over. That is the signature of exhausting
graphics memory, not of a JavaScript bug.

The cause: `buildRobot()` removed the old robot from the scene and disposed its
GEOMETRY, but never its MATERIALS. `partMat()` makes a brand new material for
every mesh, and `buildRobot()` runs on every rig edit — so tuning the rig
leaked a material, and its compiled shader program, on every single change.
Removing an object from a three.js scene frees the JavaScript reference only;
the buffers and programs stay on the card until they are disposed by hand.

three.js counts what it is holding, so this is measurable rather than a matter
of opinion: rebuild the robot many times and the counters must come back to
where they started.

Textures are deliberately exempt — getTex() caches them and shares one instance
across every build, so disposing one would blank every mesh that uses it later.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "rebuilding the robot does not leak GPU memory"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK " + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];
    // settle first: the first builds also create the textures and the grid
    for (var w = 0; w < 3; w++) buildRobot();
    renderer.render(scene, camera);
    var g0 = renderer.info.memory.geometries;
    var p0 = renderer.info.programs ? renderer.info.programs.length : -1;

    // now the thing a person actually does: edit the rig again and again
    for (var i = 0; i < 25; i++) buildRobot();
    renderer.render(scene, camera);
    var g1 = renderer.info.memory.geometries;
    var p1 = renderer.info.programs ? renderer.info.programs.length : -1;

    out.push("g0=" + g0);
    out.push("g1=" + g1);
    out.push("gleak=" + (g1 - g0));
    out.push("pleak=" + (p1 < 0 || p0 < 0 ? 0 : p1 - p0));
    // the robot must still be there and still renderable after all that
    out.push("alive=" + (robot && robot.children.length > 0 ? "yes" : "no"));
    out.push("disposed=" + (typeof partMat === "function" ? "ok" : "no"));
    report(out.join("~"));
  }catch(e){ report("ERR~" + String(e).slice(0,60)); }
  setTimeout(function(){ report("done"); }, 300);
}, 2000); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=24)

    marks = [m for m in fake_serial.qc_marks if "~" in m]
    if not t.ok(marks, "the leak driver reported",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1].split("~") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the driver ran without throwing", got["ERR"])
        return

    t.eq(got.get("alive"), "yes", "the robot is still built and renderable")

    # 25 rebuilds. A per-build leak shows up as a number that scales with the
    # loop count; a stable count means everything was handed back.
    gleak = int(got.get("gleak", "999"))
    t.ok(gleak <= 0,
         "25 rebuilds leak no geometry (delta %d)" % gleak,
         "each rebuild keeps its buffers on the graphics card")

    pleak = int(got.get("pleak", "999"))
    t.ok(pleak <= 2,
         "and no pile of shader programs (delta %d)" % pleak,
         "a material leaked per mesh per rebuild — this is what exhausts the "
         "card and takes the machine down with it")

    # and the disposal is actually in the source, for the material case
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    i = app.find("function buildRobot()")
    if t.ok(i >= 0, "buildRobot exists"):
        body = app[i:i + 1400]
        t.contains(body, "geometry.dispose()", "geometry is handed back")
        t.contains(body, "x.dispose", "and so are the materials")
        t.ok("texture" not in body.lower() or "NOT disposed" in body,
             "textures are left alone — they are shared between builds",
             "disposing a cached texture blanks every later mesh using it")
