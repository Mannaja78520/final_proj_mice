"""Labelled training views for free: a random pose seen by a random camera.

The rig knows where every keypoint is, so a view of a known pose IS its label.
This writes YOLO-pose labels (one class, K keypoints x (x, y, v)) and the
dataset yaml (kpt_shape, flip_idx from the L_/R_ names). Pictures come from a
renderer (handoff/tasks/robot-pose-data.md: MuJoCo on the PC); `paint` here
draws a plain stick robot so the pipeline runs end to end without one.
"""
import json
import math
from pathlib import Path

import numpy as np

from .camera import Camera
from .keypoints import RobotKeypoints

V_OFF, V_HIDDEN, V_SEEN = 0, 1, 2   # YOLO/COCO visibility


class SynthViews:
    def __init__(self, kp=None, cfg=None, seed=None):
        self.kp = kp or RobotKeypoints(cfg=cfg)
        self.cfg = self.kp.cfg if cfg is None else cfg
        self.s = self.cfg["synth"]
        self.rng = np.random.default_rng(self.s["seed"] if seed is None else seed)
        self.front_only = [i for i, k in enumerate(self.kp.kps) if k.get("seenFrom") == "front"]
        self.neck = self.kp.index.get("neck", 0)

    def pose(self):
        lo, hi = np.array(self.kp.rig["min"], float), np.array(self.kp.rig["max"], float)
        return list(self.rng.uniform(lo, hi))

    def camera(self, azimuth=None):
        s, c = self.s, self.cfg["camera"]
        u = lambda r: float(self.rng.uniform(*r))
        look = np.array([0.0, 100.0, 0.0]) + self.rng.normal(0, s["lookJitterMm"] / 2, 3)
        return Camera.orbit(u(s["azimuthDeg"]) if azimuth is None else azimuth, u(s["elevationDeg"]),
                            u(s["distanceMm"]), look, u(s["fovDeg"]), c["width"], c["height"])

    def view(self, pose=None, cam=None):
        """-> dict(pose, camera, uv (K,2), vis (K,)) for one picture."""
        pose = self.pose() if pose is None else pose
        cam = cam or self.camera()
        uv, z = cam.project(self.kp.points3d(pose))
        inside = (uv[:, 0] >= 0) & (uv[:, 0] < cam.width) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.height) & (z > 0)
        vis = np.where(inside, V_SEEN, V_OFF)
        for i in self.front_only:                 # the chest marker faces away: hidden
            if z[i] >= z[self.neck] and vis[i]:
                vis[i] = V_HIDDEN
        return {"pose": pose, "camera": cam, "uv": uv, "vis": vis}

    @staticmethod
    def yolo_line(uv, vis, width, height, pad=0.08):
        """'0 cx cy w h  x y v ...' normalised; the box is the seen keypoints + pad."""
        seen = uv[vis > 0]
        x0, y0 = seen.min(0)
        x1, y1 = seen.max(0)
        px, py = (x1 - x0) * pad + 4, (y1 - y0) * pad + 4
        x0, y0 = max(0, x0 - px), max(0, y0 - py)
        x1, y1 = min(width, x1 + px), min(height, y1 + py)
        vals = [0, (x0 + x1) / 2 / width, (y0 + y1) / 2 / height, (x1 - x0) / width, (y1 - y0) / height]
        for (x, y), v in zip(uv, vis):
            vals += [x / width, y / height, int(v)] if v else [0, 0, 0]
        return " ".join("%d" % v if isinstance(v, (int, np.integer)) else "%.6f" % v for v in vals)

    def dataset_yaml(self, root):
        k = len(self.kp.names)
        return "\n".join(["# made by tools/robot_pose/synth.py from config/robot_pose.json",
                          "path: %s" % Path(root).as_posix(), "train: images/train", "val: images/val",
                          "kpt_shape: [%d, 3]" % k, "flip_idx: %s" % json.dumps(self.kp.flip),
                          "names:", "  0: nong", ""])

    def paint(self, view):
        """A plain stick robot on a random grey (PIL), for a pipeline run only."""
        from PIL import Image, ImageDraw
        cam = view["camera"]
        g = int(self.rng.integers(40, 220))
        img = Image.new("RGB", (cam.width, cam.height), (g, g, g))
        d = ImageDraw.Draw(img)
        uv, vis = view["uv"], view["vis"]
        for a, b in self.kp.edges:
            if vis[a] == V_SEEN and vis[b] == V_SEEN:
                d.line([tuple(uv[a]), tuple(uv[b])], fill=(230, 120, 30), width=6)
        for i, (x, y) in enumerate(uv):
            if vis[i] == V_SEEN:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(30, 90, 220) if self.kp.names[i].startswith("L_")
                          else (220, 40, 40) if self.kp.names[i].startswith("R_") else (250, 250, 250))
        return img

    def write(self, root, n, val_share=0.1, images=True):
        root = Path(root)
        meta = []
        for i in range(n):
            split = "val" if i < n * val_share else "train"
            v = self.view()
            if (v["vis"] > 0).sum() < 3:
                continue
            name = "synth_%06d" % i
            (root / "labels" / split).mkdir(parents=True, exist_ok=True)
            (root / "images" / split).mkdir(parents=True, exist_ok=True)
            (root / "labels" / split / (name + ".txt")).write_text(
                self.yolo_line(v["uv"], v["vis"], v["camera"].width, v["camera"].height) + "\n", encoding="utf-8")
            if images:
                self.paint(v).save(root / "images" / split / (name + ".jpg"), quality=90)
            meta.append({"name": name, "split": split, "pose": v["pose"], "camera": v["camera"].to_json()})
        (root / "dataset.yaml").write_text(self.dataset_yaml(root), encoding="utf-8")
        (root / "views.jsonl").write_text("\n".join(json.dumps(m) for m in meta) + "\n", encoding="utf-8")
        return len(meta)
