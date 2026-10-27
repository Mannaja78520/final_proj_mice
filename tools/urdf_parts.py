"""List what each URDF link carries, piece by piece, and where the joints turn.

Why (user 2026-10-27): in the CAD look the ring fixed to the body turned with
the shoulder roll and the bolts did not stay on their axes. A SolidWorks
export can put a body-fixed piece on the child link, or place a joint origin
off the bolt. This splits every mesh into its separate pieces (touching
triangles) and says, per piece, how far it is from each joint axis, so the
fix can go in urdf_view.json "pieces" data instead of the private URDF.

Read only: never writes next to the model.
  python tools/urdf_parts.py <file.urdf> [--json out.json]
"""
import argparse, json, math, os, re, struct, sys
import xml.etree.ElementTree as ET


def nums(s, n, d=0.0):
    v = [float(x) for x in (s or "").split()] if s else []
    return v if len(v) == n else [d] * n


def rpy_mat(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def app(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def add(a, b):
    return [a[i] + b[i] for i in range(3)]


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def read_stl(path):
    data = open(path, "rb").read()
    tris = []
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 == len(data):
            for i in range(n):
                f = struct.unpack("<12f", data[84 + i * 50: 84 + i * 50 + 48])
                tris.append((f[3:6], f[6:9], f[9:12]))
            return tris
    pts = [tuple(map(float, m.groups())) for m in
           re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)]
    return [tuple(pts[i:i + 3]) for i in range(0, len(pts) - 2, 3)]


def pieces(tris, q=1e-5):
    """Split triangles into pieces that share corners (union-find on welded corners)."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    keys = []
    for t in tris:
        k = [tuple(round(c / q) for c in p) for p in t]
        keys.append(k)
        a = find(k[0])
        for o in k[1:]:
            b = find(o)
            if a != b:
                parent[b] = a
    groups = {}
    for i, k in enumerate(keys):
        groups.setdefault(find(k[0]), []).append(i)
    return list(groups.values())


def mesh_path(fn, urdf_path):
    fn = re.sub(r"^package://[^/]+/", "", fn).replace("file://", "")
    base = os.path.dirname(os.path.dirname(os.path.abspath(urdf_path)))
    for c in (os.path.join(base, fn), os.path.join(os.path.dirname(urdf_path), fn),
              os.path.join(base, "meshes", os.path.basename(fn))):
        if os.path.isfile(c):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urdf")
    ap.add_argument("--json")
    a = ap.parse_args()
    root = ET.parse(a.urdf).getroot()
    joints = []
    for j in root.findall("joint"):
        o = j.find("origin")
        joints.append({"name": j.get("name"), "type": j.get("type"),
                       "parent": j.find("parent").get("link"), "child": j.find("child").get("link"),
                       "xyz": nums(o.get("xyz") if o is not None else None, 3),
                       "rpy": nums(o.get("rpy") if o is not None else None, 3),
                       "axis": nums(j.find("axis").get("xyz") if j.find("axis") is not None else "1 0 0", 3)})
    child = {j["child"]: j for j in joints}
    links = [l.get("name") for l in root.findall("link")]
    pose = {}

    def world(link):          # link frame in the file's frame at all joints zero
        if link in pose:
            return pose[link]
        j = child.get(link)
        if not j:
            pose[link] = ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])
        else:
            R, t = world(j["parent"])
            pose[link] = (mul(R, rpy_mat(*j["rpy"])), add(t, app(R, j["xyz"])))
        return pose[link]
    axes = []
    for j in joints:
        R, t = world(j["parent"])
        R2 = mul(R, rpy_mat(*j["rpy"]))
        d = app(R2, j["axis"]); n = norm(d) or 1
        axes.append({"name": j["name"], "type": j["type"], "parent": j["parent"], "child": j["child"],
                     "at_mm": [round(v * 1000, 2) for v in add(t, app(R, j["xyz"]))],
                     "dir": [round(v / n, 4) for v in d]})

    def axis_dist(p, ax):     # mm from point p (m) to the joint's axis line
        o = [v / 1000 for v in ax["at_mm"]]
        return round(norm(cross(sub(p, o), ax["dir"])) * 1000, 2)

    near = {}                 # link -> the joints that touch it (its own and its children's)
    for ax in axes:
        near.setdefault(ax["child"], []).append(ax)
        near.setdefault(ax["parent"], []).append(ax)
    out = {"urdf": os.path.basename(a.urdf), "joints": axes, "links": []}
    for ln in links:
        el = root.find("link[@name='%s']" % ln)
        R, t = world(ln)
        rec = {"link": ln, "moved_by": child[ln]["name"] if ln in child else None, "visuals": []}
        for v in el.findall("visual"):
            m = v.find("geometry/mesh")
            if m is None:
                continue
            o = v.find("origin")
            vR = mul(R, rpy_mat(*nums(o.get("rpy") if o is not None else None, 3)))
            vt = add(t, app(R, nums(o.get("xyz") if o is not None else None, 3)))
            sc = nums(m.get("scale"), 3, 1.0)
            p = mesh_path(m.get("filename"), a.urdf)
            vis = {"mesh": os.path.basename(m.get("filename")), "found": bool(p), "pieces": []}
            if p:
                tris = read_stl(p)
                vis["triangles"] = len(tris)
                for gi, g in enumerate(sorted(pieces(tris), key=len, reverse=True)):
                    P = [add(vt, app(vR, [c[k] * sc[k] for k in range(3)])) for i in g for c in tris[i]]
                    lo = [min(x[k] for x in P) for k in range(3)]
                    hi = [max(x[k] for x in P) for k in range(3)]
                    mid = [(lo[k] + hi[k]) / 2 for k in range(3)]
                    vis["pieces"].append({"i": gi, "tris": len(g),
                                          "mid_mm": [round(x * 1000, 1) for x in mid],
                                          "size_mm": [round((hi[k] - lo[k]) * 1000, 1) for k in range(3)],
                                          "axis_mm": {ax["name"]: axis_dist(mid, ax) for ax in near.get(ln, [])}})
            rec["visuals"].append(vis)
        out["links"].append(rec)
    if a.json:
        open(a.json, "w", newline="").write(json.dumps(out, indent=1))
    for ax in axes:
        print("joint %-10s %-9s %s -> %s at %s dir %s" % (ax["name"], ax["type"], ax["parent"], ax["child"], ax["at_mm"], ax["dir"]))
    for rec in out["links"]:
        for vis in rec["visuals"]:
            print("link %s (moved by %s) %s: %d pieces%s" % (rec["link"], rec["moved_by"], vis["mesh"],
                  len(vis["pieces"]), "" if vis["found"] else " MESH NOT FOUND"))
            for pc in vis["pieces"][:12]:
                print("   #%d tris %d mid %s size %s axis-mm %s" % (pc["i"], pc["tris"], pc["mid_mm"], pc["size_mm"], pc["axis_mm"]))


if __name__ == "__main__":
    sys.exit(main())
