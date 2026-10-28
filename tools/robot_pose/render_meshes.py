"""Private CAD appearance attached to the shared rig, without changing its joints.

CAD axes/servo fit is deliberately not used as a second kinematic model.
Each link is attached at the corresponding Studio bar frame. This approximates
small CAD offsets; it does not replace measured calibration or prove realism.
"""
import hashlib
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


class CadAppearance:
    def __init__(self, kp):
        self.cfg = kp.cfg["render"]["cad"]
        code = next((p for p in Path(__file__).resolve().parents if p.name == "code"), None)
        self.root = code / self.cfg["source"] if code else Path(self.cfg["source"])
        self.cache = code / ".local/robot_pose/mesh_cache" if code else None
        self.enabled = bool(self.cfg["enabled"] and self.cache and all(
            (self.root / (v + ".STL")).is_file() for v in self.cfg["links"].values()))
        self.kp = kp

    def reduced(self, link):
        """Cluster STL vertices on a millimetre grid; retain surface winding."""
        src = self.root / (link + ".STL")
        raw = src.read_bytes()
        key = hashlib.sha256(raw + str(self.cfg["gridMm"]).encode()).hexdigest()[:16]
        self.cache.mkdir(parents=True, exist_ok=True)
        out = self.cache / (link + "_" + key + ".stl")
        if out.exists():
            return out
        count = struct.unpack_from("<I", raw, 80)[0]
        dtype = np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")])
        faces = np.frombuffer(raw, dtype=dtype, count=count, offset=84)
        points = faces["v"].reshape(-1, 3)
        cells = np.round(points / (self.cfg["gridMm"] * .001)).astype(np.int64)
        _, inv = np.unique(cells, axis=0, return_inverse=True)
        centers = np.zeros((int(inv.max()) + 1, 3))
        np.add.at(centers, inv, points)
        centers /= np.bincount(inv)[:, None]
        triangles = centers[inv].reshape(-1, 3, 3)
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        keep = lengths > 1e-12
        result = np.zeros(int(keep.sum()), dtype=dtype)
        result["v"] = triangles[keep]
        result["normal"] = normals[keep] / lengths[keep, None]
        out.write_bytes(b"private robot pose CAD cache".ljust(80, b" ") + struct.pack("<I", len(result)) + result.tobytes())
        return out

    def attach(self, asset, body, key):
        link = self.cfg["links"][key]
        ET.SubElement(asset, "mesh", name=link, file=str(self.reduced(link)))
        # ROS [x,y,z] -> Studio [y,z,x], matching urdf_view.js.
        attrs = dict(name="cad_" + key, type="mesh", mesh=link, quat=".5 -.5 -.5 -.5",
                     rgba=".85 .85 .85 1", contype="0", conaffinity="0")
        if key == "waist":
            attrs["pos"] = f"0 {(self.kp.rig['dims']['shoulderY'] + self.cfg['shrugLiftMm'] - self.cfg['waistTopMm']) * .001} 0"
        elif key == "shrug":
            # CAD anchors are ~63 mm below the collar; tree anchors are at mount.
            attrs["pos"] = f"0 {self.cfg['shrugLiftMm'] * .001} 0"
        ET.SubElement(body, "geom", **attrs)

    def key_for_body(self, name):
        if name in ("waist", "mount"):
            return "waist" if name == "waist" else "shrug"
        for side, order in zip(("L", "R"), self.kp.rig["order"]):
            for j, part in zip(order, ("sh", "upper", "el", "fore")):
                if name == f"{side}_j{j}_after":
                    return side + "_" + part
        return None
