"""Fill a Studio body preset from the robot's own STEP files (A31-17).

    python tools/step_preset.py            print what the STEP says
    python tools/step_preset.py --write    and put it into config/rig_presets.json

The preset names its STEP folder and parts in its "from_step" block, so a new
CAD version is one path change and one command - nothing here knows a part name.

What it measures, all from the assembly placements and the cylinder axes of
each part (a hole or a bearing seat IS a cylinder, so its axis is the pin):
  * the shrug 4-bar: servo spline, horn pin, rocker pin and pivot, then the
    servo angle for every shrug angle, so the gear ratio and the limits come out
    of the linkage instead of a guess (the old guess was 1:4.5; the CAD says 2.38);
  * shrugPivot: how far the see-saw bearing sits above the shoulder centres.
Arm lengths stay with A30's measurement (analysis json named in from_step).
Standard library only, like the rest of the hub.
"""
import argparse
import json
import math
import re
from fractions import Fraction
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
PRESETS = CODE / "config" / "rig_presets.json"
# the model folder sits beside code/ - found by walking up, so a staging copy works too
ROOT = next((p for p in CODE.parents if (p / "model").is_dir()), CODE.parent)


# ------------------------------------------------------------ tiny STEP reader
def _load(path):
    txt = path.read_text(encoding="latin-1").split("DATA;", 1)[1]
    ents = {}
    for m in re.finditer(r"#(\d+)\s*=\s*(.*?);\s*(?=#\d+\s*=|ENDSEC)", txt, re.S):
        ents[int(m.group(1))] = " ".join(m.group(2).split())
    return ents


def _refs(s):
    return [int(x) for x in re.findall(r"#(\d+)", s)]


def _nums(s):
    return [float(x) for x in re.findall(r"[-+]?\d+\.\d*(?:E[-+]?\d+)?", s)]


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _placement(E, i):
    """AXIS2_PLACEMENT_3D -> 4x4 (rows)."""
    r = _refs(E[i])
    p = _nums(E[r[0]])[:3]
    z = _unit(_nums(E[r[1]])[:3])
    x = _nums(E[r[2]])[:3] if len(r) > 2 else [1.0, 0.0, 0.0]
    d = sum(a * b for a, b in zip(x, z))
    x = _unit([a - d * b for a, b in zip(x, z)])
    y = _cross(z, x)
    return [[x[0], y[0], z[0], p[0]], [x[1], y[1], z[1], p[1]],
            [x[2], y[2], z[2], p[2]], [0, 0, 0, 1]]


def _mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _pt(T, p):
    return [sum(T[i][k] * p[k] for k in range(3)) + T[i][3] for i in range(3)]


def _dir(T, d):
    return [sum(T[i][k] * d[k] for k in range(3)) for i in range(3)]


def parts(folder, fname, T0=None, out=None):
    """Every leaf part of an assembly: (file name, 4x4 placement in the top frame).
    SolidWorks writes each part to its own file, named after the product."""
    T0 = T0 or [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    out = [] if out is None else out
    E = _load(folder / fname)
    name_of = {}
    for k, s in E.items():
        if s.startswith("PRODUCT_DEFINITION ("):
            prod = _refs(E[_refs(s)[0]])[0]
            name_of[k] = re.search(r"'([^']*)'", E[prod]).group(1)
    nauo = {k: _refs(s) for k, s in E.items() if s.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE")}
    pds = {k: _refs(s)[0] for k, s in E.items() if s.startswith("PRODUCT_DEFINITION_SHAPE")}
    rel = {}
    for k, s in E.items():
        m = re.search(r"REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION \( #(\d+)", s)
        if m:   # ITEM_DEFINED_TRANSFORMATION: item 1 places the child in this frame
            rel[k] = _placement(E, _refs(E[int(m.group(1))])[0])
    kids = []
    for s in E.values():
        if s.startswith("CONTEXT_DEPENDENT_SHAPE_REPRESENTATION"):
            r, p = _refs(s)[:2]
            if pds.get(p) in nauo:
                kids.append((name_of[nauo[pds[p]][1]], rel[r]))
    if not kids:
        out.append((fname, T0))
        return out
    for name, T in kids:
        f = name + ".STEP"
        if (folder / f).exists():
            parts(folder, f, _mul(T0, T), out)
    return out


def axes(folder, fname, T, rmin=1.4):
    """Hole/shaft axes of one part, in the top frame: [(radius, point, direction)]."""
    E = _load(folder / fname)
    res = []
    for s in E.values():
        if s.startswith("CYLINDRICAL_SURFACE"):
            rad = _nums(s.split(",")[-1])[0]
            if rad < rmin:
                continue
            P = _placement(E, _refs(s)[0])
            res.append((rad, _pt(T, [P[0][3], P[1][3], P[2][3]]),
                        _dir(T, [P[0][2], P[1][2], P[2][2]])))
    return res


# ------------------------------------------------------------ the shrug 4-bar
def _ends(ax, u, v):
    """The two pin centres of a link: axis points clustered, the farthest pair."""
    pts = []
    for _, p, _ in ax:
        q = (sum(a * b for a, b in zip(p, u)), sum(a * b for a, b in zip(p, v)))
        if not any(math.dist(q, o) < 0.5 for o in pts):
            pts.append(q)
    best = max(((a, b) for i, a in enumerate(pts) for b in pts[i + 1:]),
               key=lambda ab: math.dist(*ab))
    return best


def shrug(folder, spec, placed, up):
    """The 4-bar in the full robot's frame, so 'level' can use its real up."""
    first = {}
    for f, T in placed:
        first.setdefault(f, T)
    get = lambda key: (spec[key], first[spec[key]])
    pivot_ax = axes(folder, *get("pivot"))
    n = _unit(pivot_ax[0][2])                            # the see-saw axis
    u = _unit(_cross(n, [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0]))
    v = _cross(n, u)
    proj = lambda p: (sum(a * b for a, b in zip(p, u)), sum(a * b for a, b in zip(p, v)))
    P = proj(pivot_ax[0][1])
    vert = math.degrees(math.atan2(*proj(up)[::-1]))   # up, seen along the axis
    horn = _ends(axes(folder, *get("servo_horn")), u, v)
    link = _ends(axes(folder, *get("coupler")), u, v)
    A, S, B = _solve_pins(horn, link)
    a, b, c, g = math.dist(S, A), math.dist(A, B), math.dist(P, B), math.dist(P, S)
    ang = lambda o, p: math.degrees(math.atan2(p[1] - o[1], p[0] - o[0]))
    # Level = the rocker symmetric about the vertical through the pivot, found
    # from its mirror hole (same radius from the pivot, the other side).
    rock = [proj(p) for _, p, _ in axes(folder, *get("rocker"))]
    mirror = [q for q in rock if abs(math.dist(P, q) - c) < 0.5 and math.dist(q, B) > 5]
    tilt = 0.0
    if mirror:
        bis = (ang(P, B) + sum(ang(P, q) for q in mirror) / len(mirror)) / 2
        wrap = lambda x: (x + 180) % 360 - 180
        tilt = min((wrap(bis - vert), wrap(bis - vert - 180)), key=abs)
    beta0 = math.radians(ang(P, B) - tilt)
    phi_ref = math.radians(ang(S, A))

    def horn_at(theta):
        bt = beta0 + math.radians(theta)
        Bp = (P[0] + c * math.cos(bt), P[1] + c * math.sin(bt))
        d = math.dist(Bp, S)
        if not abs(a - b) < d < a + b:
            return None
        base = math.atan2(Bp[1] - S[1], Bp[0] - S[0])
        k = math.acos((a * a + d * d - b * b) / (2 * a * d))
        wrap = lambda x: (x + math.pi) % (2 * math.pi) - math.pi
        return math.degrees(min((base + k, base - k), key=lambda s: abs(wrap(s - phi_ref))))

    h0 = horn_at(0)
    rng = int(spec.get("range_deg", 16))
    table = [[t, round(horn_at(t) - h0, 2)] for t in range(-rng, rng + 1, 2)
             if horn_at(t) is not None]
    ratio = (horn_at(0.01) - horn_at(-0.01)) / 0.02
    return {
        "ground_mm": round(g, 2), "horn_mm": round(a, 2), "coupler_mm": round(b, 2),
        "rocker_mm": round(c, 2), "cad_pose_tilt_deg": round(tilt, 2),
        "ratio": round(ratio, 3), "range_deg": rng,
        "servo_deg_at_limits": [table[0][1], table[-1][1]],
        "table_shrug_to_servo": table,
        "pivot_top_frame": [round(x, 2) for x in pivot_ax[0][1]],
    }


def _solve_pins(horn, link):
    """(shared pin, servo spline, rocker pin): the horn end and the coupler end
    that coincide are the shared pin; the other ends are the spline and rocker."""
    best = None
    for h in (0, 1):
        for k in (0, 1):
            d = math.dist(horn[h], link[k])
            if best is None or d < best[0]:
                best = (d, horn[h], horn[1 - h], link[1 - k])
    return best[1], best[2], best[3]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--preset", default="nong_step_2026_09")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    data = json.loads(PRESETS.read_text(encoding="utf-8"))
    p = next(x for x in data["presets"] if x["id"] == args.preset)
    fs = p["from_step"]
    folder = ROOT / fs["dir"]
    full = parts(folder, fs["robot"])
    up = [1.0 if i == fs.get("up_axis", 1) else 0.0 for i in range(3)]
    sh = shrug(folder, fs["shrug"], full, up)
    an = json.loads((ROOT / fs["analysis"]).read_text(encoding="utf-8"))
    # the pivot is in the body sub-assembly's frame; the shoulder centre is in the
    # full robot's, so the full robot's placement of the same pivot is used
    piv = next(axes(folder, f, T)[0][1] for f, T in full if f == fs["shrug"]["pivot"])
    up = fs.get("up_axis", 1)
    pivot_above = round(piv[up] - an["joints"]["shoulder"][up], 1)
    print("shrug 4-bar: ground %(ground_mm)s horn %(horn_mm)s coupler %(coupler_mm)s "
          "rocker %(rocker_mm)s mm, servo/shrug %(ratio)s, CAD pose tilt %(cad_pose_tilt_deg)s deg" % sh)
    print("  +-%d deg shrug -> servo %s deg" % (sh["range_deg"], sh["servo_deg_at_limits"]))
    print("  shrug pivot %.1f mm above the shoulder centres" % pivot_above)
    if not args.write:
        return
    p["dims"]["shrugPivot"] = pivot_above
    s = p["servos"]["SHRUG"]
    # The board keeps WHOLE teeth (GEAR/JCFG parse with toInt: 4.5 became 4), so
    # the ratio goes over as the nearest fraction a pinion:gear pair can hold.
    fr = Fraction(sh["ratio"]).limit_denominator(64)
    s["gear"] = [fr.denominator, fr.numerator]
    s["min"], s["max"] = 90 - sh["range_deg"], 90 + sh["range_deg"]
    p["shrug_linkage"] = sh
    PRESETS.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print("written:", PRESETS)


if __name__ == "__main__":
    main()
