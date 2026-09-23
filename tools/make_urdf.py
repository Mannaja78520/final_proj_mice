#!/usr/bin/env python3
"""Write the nong's URDF from the measured rig. One command, no CAD needed.

    python tools/make_urdf.py                 -> models/nong.urdf
    python tools/make_urdf.py --out X.urdf    somewhere else
    python tools/make_urdf.py --meshes m.json name the STL per body part

User 2026-09-23: *first of all you open my solidwork and make the geomatry for
me too and then export to urdf i already have that addin*, and *make show urdf
look like in nong studio too*.

The SolidWorks sw2urdf add-in is a GUI wizard: it cannot be driven from a
script, and SolidWorks was open in another session while this was written. But
the only thing sw2urdf really produces that matters here is a joint tree with
origins, axes and limits - and every one of those numbers is already measured,
in rig_default.json, which came from nong_assembly.STEP. So this writes the
same file directly, and a rig change is one command away from a new URDF
instead of a wizard run.

What this CANNOT produce is the meshes. A URDF names them; it does not carry
them. Export an STL per body part from SolidWorks (or use the ones already in
models/) and name them with --meshes; a part with no mesh is written as a link
with no <visual>, which Studio lists and skips rather than drawing an empty
body.

The axis convention, the tree and every number are explained in
docs/urdf_nong.md. Keep the two together: this writes the file, that says why.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RIG = ROOT / "nong/main_python_set_nong/rig_default.json"
MODELS = ROOT / "nong/main_python_set_nong/models"

# Studio is Y-up Z-forward; URDF/ROS is Z-up X-forward. Studio's importer
# converts with the cyclic swap (x, y, z) -> (y, z, x), so writing a URDF is
# the inverse: a Studio point (x, y, z) is URDF (z, x, y). A cyclic swap is a
# rotation, not a reflection, so the handedness holds and nothing mirrors.
def urdf_xyz(studio_mm):
    x, y, z = studio_mm
    return (z / 1000.0, x / 1000.0, y / 1000.0)

# and the same for which axis a joint turns about
STUDIO_AXIS_TO_URDF = {"x": (0, 1, 0), "y": (0, 0, 1), "z": (1, 0, 0)}

# Stall torque per joint, N.m, from the datasheets the thesis uses (A30-3):
# PDI-1181MG shoulders 3.6, MG90S elbows 0.31, TD-8135MG waist 33.4, and the
# shrug rides the same TD-8135MG through a 1:4.5 linkage. URDF requires an
# `effort` on every joint and Nong Studio ignores it - it is here so the file
# is worth something to a simulator later, not because anything reads it.
EFFORT_NM = [3.6, 3.6, 0.31, 0.31, 3.6, 3.6, 0.31, 0.31, 33.4, 33.4]

# The joint tree. Each row is:
#   name, parent link, child link, joint index (0-9), origin in STUDIO mm
# A shoulder and an elbow are each a universal joint of TWO servos, so they are
# two revolute joints at the same origin with a zero-length link between them.
def tree(rig):
    d = rig["dims"]
    sx, sy = d["shoulderX"], d["shoulderY"]
    piv = d.get("shrugPivot", 0) or 0
    up = {"L": d["upperLenL"], "R": d["upperLenR"]}
    rows = [
        ("waist", "base_link", "waist_link", 8, (0, 0, 0)),
        ("shrug", "waist_link", "shrug_link", 9, (0, sy + piv, 0)),
    ]
    for side, sign in (("L", +1), ("R", -1)):
        rows += [
            ("%s_SH_P" % side, "shrug_link", "%s_sh_mid" % side,
             0 if side == "L" else 4, (sign * sx, -piv, 0)),
            ("%s_SH_R" % side, "%s_sh_mid" % side, "%s_upper_link" % side,
             1 if side == "L" else 5, (0, 0, 0)),
            ("%s_EL_P" % side, "%s_upper_link" % side, "%s_el_mid" % side,
             2 if side == "L" else 6, (0, -up[side], 0)),
            ("%s_EL_R" % side, "%s_el_mid" % side, "%s_fore_link" % side,
             3 if side == "L" else 7, (0, 0, 0)),
        ]
    return rows


# Which link carries which Studio body part's mesh. The link names are the ones
# Studio's URDF_GUESS already recognises, so an imported file needs no
# correcting by hand.
LINK_PART = {
    "base_link": "torso",
    "head_link": "head",
    "L_upper_link": "L_upper",
    "L_fore_link": "L_fore",
    "R_upper_link": "R_upper",
    "R_fore_link": "R_fore",
}
DEF_MESH = {part: part + ".stl" for part in LINK_PART.values()}


def build(rig, meshes, mesh_dir="meshes", mesh_mm=True):
    rows = tree(rig)
    # In order, once each: waist_link and shrug_link are both the roots of the
    # tree AND the children of a row, and a URDF with a link declared twice is
    # accepted by lenient parsers and rejected by strict ones.
    links = []
    for name in (["base_link", "head_link"]
                 + [child for _n, _p, child, _j, _o in rows]):
        if name not in links:
            links.append(name)
    out = ['<?xml version="1.0"?>', '<robot name="nong">']
    missing = []
    for link in links:
        part = LINK_PART.get(link)
        mesh = meshes.get(part) if part else None
        if part and not mesh:
            missing.append(part)
        out.append('  <link name="%s">' % link)
        if mesh:
            # THE MESH SCALE AND THE LENGTH SCALE MULTIPLY. Studio reads a
            # <mesh scale> and then multiplies by its metres-to-millimetres
            # number, so an STL exported in MILLIMETRES - which is what this
            # project exports and what Studio's own Import expects - must
            # declare 0.001 here, or it arrives a thousand times too big.
            # Leaving the attribute out silently declared metres.
            scale = ' scale="0.001 0.001 0.001"' if mesh_mm else ""
            out += ['    <visual>',
                    '      <origin xyz="0 0 0" rpy="0 0 0"/>',
                    '      <geometry><mesh filename="%s/%s"%s/></geometry>'
                    % (mesh_dir, mesh, scale),
                    '    </visual>']
        out.append('  </link>')
    # the head hangs off the shoulder bar, and its offset is not in the rig
    out += ['  <joint name="head" type="fixed">',
            '    <parent link="shrug_link"/>',
            '    <child link="head_link"/>',
            '    <origin xyz="0 0 0" rpy="0 0 0"/>',
            '  </joint>']
    for name, parent, child, j, off in rows:
        x, y, z = urdf_xyz(off)
        ax = STUDIO_AXIS_TO_URDF[rig["axis"][j]]
        # URDF limits are radians from the joint's own zero; Studio holds joint
        # degrees with a zero per joint, so this is (min - zero) in radians.
        lo = math.radians(rig["min"][j] - rig["zero"][j])
        hi = math.radians(rig["max"][j] - rig["zero"][j])
        vel = math.radians(rig["servoMaxDps"][j])
        out += ['  <joint name="%s" type="revolute">' % name,
                '    <parent link="%s"/>' % parent,
                '    <child link="%s"/>' % child,
                '    <origin xyz="%.6g %.6g %.6g" rpy="0 0 0"/>' % (x, y, z),
                '    <axis xyz="%d %d %d"/>' % ax,
                '    <limit lower="%.4f" upper="%.4f" effort="%.3g" velocity="%.3f"/>'
                % (lo, hi, EFFORT_NM[j], vel),
                '  </joint>']
    out.append('</robot>')
    return "\n".join(out) + "\n", missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rig", type=Path, default=RIG)
    ap.add_argument("--out", type=Path, default=MODELS / "nong.urdf")
    ap.add_argument("--meshes", type=Path,
                    help='JSON: {"torso": "torso.stl", ...}. Left out, every '
                         "part uses <part>.stl if models/ holds it.")
    ap.add_argument("--mesh-dir", default="meshes",
                    help="the folder the URDF names before each mesh")
    ap.add_argument("--mesh-metres", action="store_true",
                    help="the STL files are in metres. Default is MILLIMETRES, "
                         "which is what SolidWorks exports here and what "
                         "Studio's own STL import expects.")
    a = ap.parse_args(argv)
    rig = json.loads(a.rig.read_text(encoding="utf-8"))
    if a.meshes:
        meshes = json.loads(a.meshes.read_text(encoding="utf-8"))
    else:
        have = {p.name.lower() for p in MODELS.glob("*") if p.is_file()}
        meshes = {k: v for k, v in DEF_MESH.items() if v.lower() in have}
    text, missing = build(rig, meshes, a.mesh_dir, not a.mesh_metres)
    # write_bytes, never write_text: on Windows write_text turns every \n into
    # \r\n and the whole file changes line ending (CLAUDE.md, cost a gate).
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(text.encode("utf-8"))
    print("wrote %s (%d bytes)" % (a.out, len(text)))
    if missing:
        print("no mesh for: %s - export an STL per part and pass --meshes, or "
              "put <part>.stl in models/. Those links are written without a "
              "<visual>, so Studio lists them and draws nothing."
              % ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
