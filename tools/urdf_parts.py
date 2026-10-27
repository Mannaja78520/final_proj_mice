"""List what each URDF link carries, piece by piece, and where the joints turn.

Why (user 2026-10-27): in the CAD look the ring fixed to the body turned with
the shoulder roll and the bolts did not stay on their axes. A SolidWorks
export can put a body-fixed piece on the child link, or place a joint origin
off the bolt. This splits every mesh into its separate pieces (touching
triangles) and says, per piece, how far it is from each joint axis, so the
fix can go in urdf_view.json "pieces" data instead of the private URDF.

Read only: never writes next to the model.
  python tools/urdf_parts.py <file.urdf> [--json out.json] [--assign web/urdf_view.json]
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


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


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


def pieces(tris, mm=1000.0, q=0.01):
    """Split triangles into pieces that share corners (union-find on corners
    welded to q mm). Pieces come biggest first, ties in file order: Studio
    (urdf_view.js urdfSplit) numbers them the same way, so "pieces" data can
    name one by its number."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    keys = []
    for t in tris:
        k = [tuple(int(math.floor(c * mm / q + 0.5)) for c in p) for p in t]
        keys.append(k)
        a = find(k[0])
        for o in k[1:]:
            b = find(o)
            if a != b:
                parent[b] = a
    groups = {}
    for i, k in enumerate(keys):
        groups.setdefault(find(k[0]), []).append(i)
    return sorted(groups.values(), key=len, reverse=True)


def tri_dist(p, a, b, c):
    """mm from point p to triangle abc (closest point, Ericson 5.1.5)."""
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return norm(ap)
    bp = sub(p, b); d3, d4 = dot(ab, bp), dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return norm(bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return norm(sub(p, add(a, [x * v for x in ab])))
    cp = sub(p, c); d5, d6 = dot(ab, cp), dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return norm(cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return norm(sub(p, add(a, [x * w for x in ac])))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return norm(sub(p, add(b, [x * w for x in sub(c, b)])))
    den = 1.0 / (va + vb + vc)
    v, w = vb * den, vc * den
    return norm(sub(p, add(a, add([x * v for x in ab], [x * w for x in ac]))))


def assign(P, cfg):
    """Which link each piece rides on: the twin of urdf_view.js urdfAssign.
    P: [{link, i, tris (world mm), lo, hi}]. cfg: urdf_view.json "pieces".
    1 a "links" rule moves a whole link's pieces; 2 a small piece (a bolt)
    follows the big piece its corners touch most; 3 a "pick" rule wins."""
    owner = {}
    for pc in P:
        owner[id(pc)] = pc["link"]
    for r in cfg.get("links", []):
        for pc in P:
            if pc["link"] == r["link"]:
                owner[id(pc)] = r["to"]
    lock = cfg.get("lock", {})
    if lock.get("on", True):
        small_mm, touch, n_pts, cell = float(lock.get("smallMm", 12)), float(lock.get("touchMm", 0.3)), int(lock.get("points", 120)), float(lock.get("cellMm", 4))
        size = lambda pc: max(pc["hi"][k] - pc["lo"][k] for k in range(3))
        small = [pc for pc in P if size(pc) <= small_mm]
        big = [pc for pc in P if size(pc) > small_mm]
        grids = {}

        def grid(pc):
            if id(pc) not in grids:
                g = {}
                for t in pc["tris"]:
                    lo = [int(math.floor((min(v[k] for v in t) - touch) / cell)) for k in range(3)]
                    hi = [int(math.floor((max(v[k] for v in t) + touch) / cell)) for k in range(3)]
                    for x in range(lo[0], hi[0] + 1):
                        for y in range(lo[1], hi[1] + 1):
                            for z in range(lo[2], hi[2] + 1):
                                g.setdefault((x, y, z), []).append(t)
                grids[id(pc)] = g
            return grids[id(pc)]
        for s in small:
            pts = [v for t in s["tris"] for v in t]
            step = max(1, len(pts) // n_pts)
            pts = pts[::step]
            best, score = None, 0
            for b in big:
                if any(s["lo"][k] > b["hi"][k] + touch or s["hi"][k] < b["lo"][k] - touch for k in range(3)):
                    continue
                g, n = grid(b), 0
                for p in pts:
                    near = g.get(tuple(int(math.floor(p[k] / cell)) for k in range(3)), ())
                    if any(tri_dist(p, *t) <= touch for t in near):
                        n += 1
                if n > score or (n == score and n and owner[id(b)] == owner[id(s)]):
                    best, score = b, n
            s["touch"] = [best["link"], best["i"], score] if best else None
            if best:
                owner[id(s)] = owner[id(best)]
    for r in cfg.get("pick", []):
        for pc in P:
            if pc["link"] == r["link"] and pc["i"] in r["pieces"]:
                owner[id(pc)] = r["to"]
    return owner


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
    ap.add_argument("--assign", help="urdf_view.json: also say which link each piece rides on")
    a = ap.parse_args()
    cfg = json.load(open(a.assign, encoding="utf-8")).get("pieces", {}) if a.assign else None
    out = analyse(a.urdf, cfg)
    if a.json:
        open(a.json, "w", newline="").write(json.dumps(out, indent=1))
    for ax in out["joints"]:
        print("joint %-10s %-9s %s -> %s at %s dir %s" % (ax["name"], ax["type"], ax["parent"], ax["child"], ax["at_mm"], ax["dir"]))
    for rec in out["links"]:
        for vis in rec["visuals"]:
            print("link %s (moved by %s) %s: %d pieces%s" % (rec["link"], rec["moved_by"], vis["mesh"],
                  len(vis["pieces"]), "" if vis["found"] else " MESH NOT FOUND"))
            for pc in vis["pieces"][:None if a.assign else 12]:
                moved = pc.get("rides") not in (None, rec["link"])
                if a.assign and not moved and max(pc["size_mm"]) > 12:
                    continue
                print("   #%d tris %d mid %s size %s axis-mm %s%s" % (pc["i"], pc["tris"], pc["mid_mm"], pc["size_mm"], pc["axis_mm"],
                      (" touches %s -> rides %s%s" % (pc.get("touches"), pc["rides"], "  MOVED" if moved else "")) if a.assign else ""))
    if a.assign:
        print("moved: %s" % (", ".join(out["moved"]) or "nothing"))


def moved_pieces(urdf, cfg):
    """["link#i->to", ...] for every piece that leaves its file's link (QC twin)."""
    return analyse(urdf, cfg)["moved"]


def analyse(urdf, cfg=None):
    weld = float(((cfg or {}).get("lock") or {}).get("weldMm", 0.01))
    root = ET.parse(urdf).getroot()
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
    out = {"urdf": os.path.basename(urdf), "joints": axes, "links": []}
    allp = {}
    for ln in links:
        allp[ln] = []
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
            p = mesh_path(m.get("filename"), urdf)
            vis = {"mesh": os.path.basename(m.get("filename")), "found": bool(p), "pieces": []}
            if p:
                tris = read_stl(p)
                vis["triangles"] = len(tris)
                W = [[[x * 1000 for x in add(vt, app(vR, [c[k] * sc[k] for k in range(3)]))] for c in t] for t in tris]
                for g in pieces(tris, sc[0] * 1000, weld):
                    T = [W[i] for i in g]
                    lo = [min(v[k] for t in T for v in t) for k in range(3)]
                    hi = [max(v[k] for t in T for v in t) for k in range(3)]
                    mid = [(lo[k] + hi[k]) / 2 for k in range(3)]
                    pc = {"i": len(allp[ln]), "tris": len(g), "mid_mm": [round(x, 1) for x in mid],
                          "size_mm": [round(hi[k] - lo[k], 1) for k in range(3)],
                          "axis_mm": {ax["name"]: axis_dist([x / 1000 for x in mid], ax) for ax in near.get(ln, [])}}
                    vis["pieces"].append(pc)
                    allp[ln].append({"link": ln, "i": pc["i"], "tris": T, "lo": lo, "hi": hi, "rec": pc})
            rec["visuals"].append(vis)
        out["links"].append(rec)
    out["moved"] = []
    if cfg is not None:
        P = [pc for ln in links for pc in allp[ln]]
        own = assign(P, cfg)
        for pc in P:
            pc["rec"]["rides"] = own[id(pc)]
            if "touch" in pc:
                pc["rec"]["touches"] = pc["touch"]
            if own[id(pc)] != pc["link"]:
                out["moved"].append("%s#%d->%s" % (pc["link"], pc["i"], own[id(pc)]))
    return out


if __name__ == "__main__":
    sys.exit(main())
