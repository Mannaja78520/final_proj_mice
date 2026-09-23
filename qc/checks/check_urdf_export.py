"""The nong's URDF is written from the measured rig, and reads back the same.

User 2026-09-23: *first of all you open my solidwork and make the geomatry for
me too and then export to urdf i already have that addin*, and *make show urdf
look like in nong studio too*.

SolidWorks' sw2urdf is a GUI wizard - it cannot be driven from a script, and
SolidWorks was open in another session. But every number it would ask for is
already measured in rig_default.json (taken from nong_assembly.STEP), so
tools/make_urdf.py writes the file directly and a rig change is one command
away from a new URDF.

The assertion that matters is the ROUND TRIP: what make_urdf.py writes, Nong
Studio's importer reads back as the same lengths. Two halves written from one
convention will agree with each other while both being wrong, so each half is
also checked against the numbers a person would look up - the waist's travel,
the upper arm's length, the axis a joint turns about - and then they are made
to agree.

Break either side of the metre/millimetre or Z-up/Y-up conversion and the round
trip fails, which is the only way to notice: a URDF that is a thousand times
too big still parses perfectly.
"""
import importlib.util
import json
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "the nong's URDF is written from the rig, and Studio reads it back the same"
SLOW = True

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK UEXP~" + s); }
var URDF_TEXT = %s;
window.addEventListener("load", function(){ qcStudioReady().then(function(){ setTimeout(async function(){
  try{
    await refreshModels();
    RIG.dims.upperLenL = 1; RIG.dims.foreLenL = 1;      // wrong on purpose
    var dt = new DataTransfer();
    dt.items.add(new File([URDF_TEXT], "nong.urdf", {type: "application/xml"}));
    document.getElementById("urdfFile").files = dt.files;
    await importUrdf();
    var guessed = Object.keys(urdfMap).filter(function(k){ return urdfMap[k]; }).length;
    window.confirm = function(){ return true; };
    useUrdf();
    report("guessed=" + guessed +
           "~upperL=" + RIG.dims.upperLenL +
           "~torso=" + (meshCfg.torso.file || "") +
           "~lupper=" + (meshCfg.L_upper.file || "") +
           "~scale=" + meshCfg.L_upper.scale);
  }catch(e){ report("ERR-" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 150); }); });
"""


def _make_urdf():
    spec = importlib.util.spec_from_file_location(
        "make_urdf", str(F.CODE / "tools" / "make_urdf.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    mk = _make_urdf()
    rig = json.loads((F.CODE / "nong/main_python_set_nong/rig_default.json")
                     .read_text(encoding="utf-8"))
    meshes = {p: p + ".stl" for p in mk.LINK_PART.values()}
    text, missing = mk.build(rig, meshes)
    t.eq(missing, [], "every body part has a mesh named when one is given for each")

    # ---- the file itself, against the numbers a person would look up --------
    t.contains(text, '<robot name="nong">', "it is a URDF naming the robot")
    for link in ("base_link", "waist_link", "shrug_link",
                 "L_upper_link", "L_fore_link", "R_upper_link", "R_fore_link"):
        t.contains(text, '<link name="%s">' % link, "it has a %s" % link)
    # waist_link and shrug_link are both roots of the tree AND children of a
    # row, so they came out twice. A lenient parser accepts that and a strict
    # one rejects the whole file, which is the worst kind of bug: it works
    # here and fails on somebody else's machine.
    names = re.findall(r'<link name="([^"]+)"', text)
    dupes = sorted({n for n in names if names.count(n) > 1})
    t.ok(not dupes, "no link is declared twice", "declared twice: %s" % dupes)
    t.eq(text.count("<joint"), 11,
         "ten driven joints and one fixed head - a shoulder and an elbow are "
         "each TWO servos, so each is two revolute joints at one origin")
    # upperLenL is 129 mm and hangs DOWN, which is -Z in URDF's Z-up frame
    t.contains(text, 'xyz="0 0 -0.129"',
               "the elbow sits one upper-arm below the shoulder, in metres, hanging down")
    # shoulderX 180 mm to each side, which is +/-Y in URDF's X-forward frame
    t.contains(text, 'xyz="0 0.18 0"', "the left shoulder is 180 mm to one side")
    t.contains(text, 'xyz="0 -0.18 0"', "and the right shoulder the same the other way")
    # the waist turns about the vertical: Studio 'y' is URDF 'z'
    waist = text.split('<joint name="waist"')[1].split("</joint>")[0]
    t.contains(waist, '<axis xyz="0 0 1"/>',
               "the waist turns about the vertical - Studio's y axis is URDF's z")
    # min 30, max 150, zero 90 -> +/- 1.0472 rad
    t.contains(waist, 'lower="-1.0472" upper="1.0472"',
               "and its limits are the rig's 30-150 deg, in radians from its own zero")

    # ---- the round trip, in a real browser ---------------------------------
    if not browser.available():
        t.give_up("headless Edge unavailable - the file half above still ran")
    fake_serial.reset()
    base, main = F.start_hub()
    models = main.MODELS
    models.mkdir(parents=True, exist_ok=True)
    made = []
    try:
        for name in meshes.values():
            p = models / name
            if not p.exists():
                p.write_bytes(b"solid qc\nendsolid qc\n")
                made.append(p)
        browser.page(DRIVER % json.dumps(text),
                     query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=22)
        marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("UEXP~")]
        got = next((m for m in marks if m.startswith("guessed=")), "")
        if not t.ok(got, "Studio read the generated URDF", marks):
            return
        v = dict(kv.split("=", 1) for kv in got.split("~"))
        t.eq(v.get("guessed"), "6",
             "Studio matches all six body parts by name with nothing corrected "
             "by hand - the generator writes the names the importer looks for")
        t.eq(v.get("torso"), "torso.stl", "and takes the torso's mesh from the file")
        t.eq(v.get("lupper"), "L_upper.stl", "and the left upper arm's")
        t.eq(v.get("scale"), "1",
             "an STL exported in millimetres ends up at scale 1 in Studio, not "
             "1000 - the mesh scale and the metres-to-millimetres scale "
             "MULTIPLY, and leaving the attribute out declared metres")
        t.eq(v.get("upperL"), "129",
             "THE ROUND TRIP: 129 mm written as 0.129 m comes back as 129 mm. "
             "A URDF a thousand times too big still parses perfectly, so this "
             "is the only assertion that would notice")
    finally:
        for p in made:
            try:
                p.unlink()
            except OSError:
                pass
