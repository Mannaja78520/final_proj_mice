"""Independent forward kinematics of a URDF, in plain Python (no three.js).

Used to check Studio's 3D robot numerically: the same joint angles through this
file and through the page must put every joint frame and every mesh in the same
place. Also checks the model itself: left/right mirror, mesh sits on its own link.
  python tools/visual/urdf_fk.py <file.urdf> [--json]
"""
import json, math, sys, struct, re
import xml.etree.ElementTree as ET
from pathlib import Path


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    # URDF: fixed axes X then Y then Z  =  Rz * Ry * Rx
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def _T(xyz, rpy):
    R = _rpy(*rpy)
    return [R[0] + [xyz[0]], R[1] + [xyz[1]], R[2] + [xyz[2]], [0, 0, 0, 1]]


def _axis_rot(ax, ang):
    n = math.sqrt(sum(v * v for v in ax)) or 1.0
    x, y, z = (v / n for v in ax)
    c, s = math.cos(ang), math.sin(ang)
    t = 1 - c
    R = [[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
         [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
         [t * x * z - s * y, t * y * z + s * x, t * z * z + c]]
    return R[0] + [0], R[1] + [0], R[2] + [0], [0, 0, 0, 1]


def _nums(el, attr, n=3):
    v = el.get(attr) if el is not None else None
    return [float(t) for t in v.split()] if v else [0.0] * n


class Urdf:
    def __init__(self, path):
        self.path = Path(path)
        root = ET.parse(path).getroot()
        self.links = {}
        for l in root.findall("link"):
            vis = []
            for v in l.findall("visual"):
                o = v.find("origin")
                m = v.find("geometry/mesh")
                vis.append({"T": _T(_nums(o, "xyz"), _nums(o, "rpy")),
                            "mesh": m.get("filename") if m is not None else None,
                            "scale": _nums(m, "scale") if m is not None and m.get("scale") else [1, 1, 1]})
            self.links[l.get("name")] = vis
        self.joints = []
        for j in root.findall("joint"):
            o = j.find("origin")
            ax = j.find("axis")
            self.joints.append({"name": j.get("name"), "type": j.get("type"), "parent": j.find("parent").get("link"),
                                "child": j.find("child").get("link"), "T": _T(_nums(o, "xyz"), _nums(o, "rpy")),
                                "axis": _nums(ax, "xyz") if ax is not None else [1, 0, 0]})
        kids = {j["child"] for j in self.joints}
        self.root = next(n for n in self.links if n not in kids)

    def fk(self, q=None):
        """world 4x4 of every link; q = {joint name: radians} (others 0)."""
        q = q or {}
        W = {self.root: [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}
        todo = list(self.joints)
        while todo:
            nxt = []
            for j in todo:
                if j["parent"] not in W:
                    nxt.append(j)
                    continue
                M = _mul(W[j["parent"]], j["T"])
                if j["type"] in ("revolute", "continuous") and q.get(j["name"]):
                    M = _mul(M, _axis_rot(j["axis"], q[j["name"]]))
                W[j["child"]] = M
            if len(nxt) == len(todo):
                raise ValueError("loop or missing parent in " + str(self.path))
            todo = nxt
        return W

    def mesh_points(self, link, W):
        """world points of the mesh corners (bbox of an STL, scaled, placed through the visual origin)."""
        out = []
        for v in self.links.get(link, []):
            if not v["mesh"]:
                continue
            f = (self.path.parent / v["mesh"].replace("package://", "").lstrip("/"))
            if not f.exists():
                f = next(iter(self.path.parent.rglob(Path(v["mesh"]).name)), f)
            if not f.exists():
                continue
            bb = stl_bbox(f)
            if not bb:
                continue
            M = _mul(W[link], v["T"])
            for x in (bb[0][0], bb[1][0]):
                for y in (bb[0][1], bb[1][1]):
                    for z in (bb[0][2], bb[1][2]):
                        p = (x * v["scale"][0], y * v["scale"][1], z * v["scale"][2])
                        out.append(tuple(M[i][0] * p[0] + M[i][1] * p[1] + M[i][2] * p[2] + M[i][3] for i in range(3)))
        return out


def stl_bbox(f):
    b = Path(f).read_bytes()
    pts = []
    if b[:5] == b"solid" and b"facet" in b[:400]:
        for m in re.finditer(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", b):
            pts.append(tuple(float(x) for x in m.groups()))
    else:
        n = struct.unpack("<I", b[80:84])[0]
        for i in range(n):
            o = 84 + i * 50 + 12
            for k in range(3):
                pts.append(struct.unpack("<3f", b[o + k * 12:o + k * 12 + 12]))
    if not pts:
        return None
    return [tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))]


def pos(M):
    return (M[0][3], M[1][3], M[2][3])


def model_findings(u, tol=3e-3):
    """Model sanity at zero pose, in the URDF's own frame (metres). Returns a list of problems."""
    W = u.fk()
    bad = []
    P = {n: pos(m) for n, m in W.items()}
    # L/R mirror: some axis is the left-right one; find a pair of links named L_*/R_* and require equal distances to the root
    for n in P:
        if n.startswith("L_"):
            m = "R_" + n[2:]
            if m in P:
                dl = math.dist(P[n], P[u.root]); dr = math.dist(P[m], P[u.root])
                if abs(dl - dr) > tol:
                    bad.append("left/right not mirrored: %s is %.0f mm from the base, %s is %.0f mm" % (n, dl * 1000, m, dr * 1000))
    # a mesh must sit near its own link frame or the next joint (the "hand at the elbow" failure: a mesh drawn at the wrong link)
    child_of = {}
    for j in u.joints:
        child_of.setdefault(j["parent"], []).append(j["child"])
    for link, vis in u.links.items():
        pts = u.mesh_points(link, W)
        if not pts:
            continue
        c = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
        far = max(math.dist(c, P[link]), *(math.dist(c, P[k]) for k in child_of.get(link, [])), 0)
        near = min([math.dist(c, P[link])] + [math.dist(c, P[k]) for k in child_of.get(link, [])])
        ext = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
        if near > ext:
            bad.append("mesh of %s is %.0f mm from its own joints (its size is %.0f mm): drawn at the wrong link?" % (link, near * 1000, ext * 1000))
    return bad


if __name__ == "__main__":
    u = Urdf(sys.argv[1])
    for b in model_findings(u):
        print("PROBLEM", b)
    W = u.fk()
    for n, m in W.items():
        print("%-16s %8.1f %8.1f %8.1f mm" % ((n,) + tuple(v * 1000 for v in pos(m))))
