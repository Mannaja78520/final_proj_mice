"""Nong Studio builds its body from a URDF instead of every STL being nudged.

User 2026-09-23: *show we already have all step file when i drag it cannot be
as my aspect make can use urdf too*.

A STEP file cannot be opened in a browser at all, and an STL carries no origin:
dragged in on its own it lands at the middle of the robot and has to be
rotated, offset and scaled by hand until it looks right. That is what "cannot
be as my aspect" was. A URDF carries those numbers, so importing one fills the
boxes in.

The conversions are where an importer like this goes quietly wrong, so each one
is asserted on the value that ends up in meshCfg - the thing the renderer
actually reads:

  * metres to millimetres (x1000 by default, settable: not every exporter
    agrees);
  * Z-up ROS axes to this editor's Y-up axes, as the cyclic swap (x,y,z) ->
    (y,z,x), which keeps the handedness and therefore keeps every rotation
    turning the same way;
  * fixed-axis rpy in radians to the editor's degrees, on the right axes;
  * the distance between two joint origins as the real bar length.

And two things that are not conversions but are how an import stops being
mysterious: reading the file changes NOTHING until Use this URDF is pressed,
and a mesh the URDF names but models/ does not hold is reported by name rather
than drawn as an empty part.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a URDF places every body part, with its units and axes converted"
SLOW = True

# A minimal, valid URDF with the two shapes that matter: a link with a turned,
# offset visual, and a joint whose origin IS the arm's length.
URDF = """<?xml version="1.0"?>
<robot name="qc_nong">
  <link name="torso_link">
    <visual>
      <origin xyz="0.01 0.02 0.03" rpy="0 0 1.5707963"/>
      <geometry><mesh filename="package://qc/meshes/qc_torso.stl"/></geometry>
    </visual>
  </link>
  <link name="left_upper_arm">
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="qc_lupper.stl" scale="0.001 0.001 0.001"/></geometry>
    </visual>
  </link>
  <link name="nothing_to_draw"/>
  <joint name="l_shoulder" type="revolute">
    <parent link="torso_link"/>
    <child link="left_upper_arm"/>
    <origin xyz="0.05 0 0.12" rpy="0 0 0"/>
    <axis xyz="1 0 0"/>
  </joint>
</robot>
"""

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK URDF~" + s); }
var URDF_TEXT = %s;
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    await refreshModels();
    var before = JSON.stringify(meshCfg.torso);
    var dt = new DataTransfer();
    dt.items.add(new File([URDF_TEXT], "qc_nong.urdf", {type: "application/xml"}));
    document.getElementById("urdfFile").files = dt.files;
    await importUrdf();
    // READING CHANGES NOTHING. The whole point of two buttons.
    var untouched = JSON.stringify(meshCfg.torso) === before;
    var guessTorso = urdfMap["torso_link"] || "";
    var guessArm = urdfMap["left_upper_arm"] || "";
    var rows = document.getElementById("urdfLinks").querySelectorAll(".row").length;
    // the link with no mesh cannot be given a part
    var sels = document.getElementById("urdfLinks").querySelectorAll("select");
    var lockedNoMesh = sels[sels.length - 1].disabled;

    window.confirm = function(){ return true; };     // yes, take the lengths
    useUrdf();
    var c = meshCfg.torso;
    var stat = document.getElementById("urdfStat").textContent;
    report("untouched=" + untouched + "~guessTorso=" + guessTorso +
           "~guessArm=" + guessArm + "~rows=" + rows +
           "~lockedNoMesh=" + lockedNoMesh +
           "~file=" + c.file + "~off=" + c.off.join("_") + "~rot=" + c.rot.join("_") +
           "~scale=" + meshCfg.L_upper.scale +
           "~upperL=" + RIG.dims.upperLenL +
           "~missing=" + (stat.indexOf("qc_torso.stl") >= 0));
  }catch(e){ report("ERR-" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - this needs a real browser")
    fake_serial.reset()
    base, main = F.start_hub()
    # Only ONE of the two meshes exists, so the import must name the other.
    models = main.MODELS
    models.mkdir(parents=True, exist_ok=True)
    made = [models / "qc_lupper.stl"]
    made[0].write_bytes(b"solid qc\nendsolid qc\n")
    try:
        import json as _json
        driver = DRIVER % _json.dumps(URDF)
        browser.page(driver, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=22)
        marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("URDF~")]
        got = next((m for m in marks if m.startswith("untouched=")), "")
        if not t.ok(got, "the driver read the URDF", marks):
            return
        v = dict(kv.split("=", 1) for kv in got.split("~"))

        t.ok(v.get("untouched") == "true",
             "reading a URDF changes nothing until Use this URDF is pressed",
             "one button that reads AND applies cannot be undone halfway: %s" % v)
        t.eq(v.get("guessTorso"), "torso", "a link called torso_link is guessed as the torso")
        t.eq(v.get("guessArm"), "L_upper",
             "and left_upper_arm as the left upper arm - the guess is a data table, "
             "so the next naming habit costs one row")
        t.eq(v.get("rows"), "3", "every link is listed, including the ones with no mesh")
        t.ok(v.get("lockedNoMesh") == "true",
             "a link with no mesh cannot be given a body part",
             "there would be nothing to draw: %s" % v)
        t.eq(v.get("file"), "qc_torso.stl",
             "the mesh name is taken from the URDF, package:// path and all")
        # xyz 0.01 0.02 0.03 m, Z-up -> (y, z, x) -> 0.02 0.03 0.01 m -> mm
        t.eq(v.get("off"), "20_30_10",
             "metres become millimetres and ROS Z-up axes become this editor's Y-up")
        # rpy 0 0 pi/2 -> the yaw moves onto the axis it now turns about
        t.eq(v.get("rot"), "0_90_0",
             "fixed-axis rpy in radians becomes degrees, on the swapped axes")
        t.eq(v.get("scale"), "1",
             "a mesh already scaled to 0.001 in the URDF ends up at 1, not 1000 "
             "- the two conversions multiply, and missing that makes a robot a "
             "thousand times too big")
        # joint origin 0.05 0 0.12 m -> 130 mm
        t.eq(v.get("upperL"), "130",
             "the distance between two joint origins becomes the arm's real length")
        t.ok(v.get("missing") == "true",
             "a mesh the URDF names but models/ does not hold is reported by name",
             "otherwise the part is simply not drawn, which reads as a broken "
             "import rather than a missing file: %s" % v)
    finally:
        for p in made:
            try:
                p.unlink()
            except OSError:
                pass
