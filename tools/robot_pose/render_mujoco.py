"""Render synth/views.jsonl as textured, lit YOLO-pose images with depth labels.

    python -m tools.robot_pose.render_mujoco ABSOLUTE/views.jsonl --out ABSOLUTE/dataset
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

from .camera import Camera
from .keypoints import RobotKeypoints
from .render_scene import RenderScene
from .synth import SynthViews, V_HIDDEN, V_OFF, V_SEEN


def private_path(value):
    """Dataset/media destinations must be explicit and under this PC's private root."""
    path = Path(value)
    private = Path(__file__).resolve().parents[4] / ".local"
    # A git worktree can sit several levels below code; use the code ancestor.
    private = next((p / ".local" for p in Path(__file__).resolve().parents if p.name == "code"), private)
    if not path.is_absolute() or not path.resolve().is_relative_to(private.resolve()):
        raise ValueError(f"use an absolute path inside {private}")
    return path


class MujocoPoseRenderer:
    def __init__(self, kp=None, seed=None):
        self.kp = kp or RobotKeypoints()
        self.cfg = self.kp.cfg["render"]
        self.rng = np.random.default_rng(self.cfg["seed"] if seed is None else seed)
        self.scene = None

    def visibility(self, uv, z, depth):
        h, w = depth.shape
        inside = (z > 0) & (uv[:, 0] >= 0) & (uv[:, 0] < w) & (uv[:, 1] >= 0) & (uv[:, 1] < h)
        vis = np.where(inside, V_SEEN, V_OFF)
        # Joint labels sit inside their own housings. Only a larger depth gap
        # means another part is in front; the radii follow the rig dimensions.
        from .keypoints import expr
        names = dict(self.kp.rig["dims"], headR=self.kp.facts.head_r,
                     jointR=max(self.kp.rig["jointR"]), barR=max(self.kp.rig["barR"]))
        for i in np.flatnonzero(inside):
            x, y = np.floor(uv[i]).astype(int)
            radii = self.cfg["cad"]["keypointRadiusMm"] if self.scene and self.scene.cad.enabled else {}
            radius = expr(radii.get(self.kp.names[i], self.cfg["keypointRadiusMm"].get(self.kp.names[i], "jointR")), names)
            if z[i] - depth[y, x] > radius + self.cfg["depthMarginMm"]:
                vis[i] = V_HIDDEN
        return vis

    def render(self, pose, camera, randomize=True):
        import cv2
        if self.scene is None:
            self.scene = RenderScene(self.kp, camera.width, camera.height)
        if (camera.height, camera.width) != (self.scene.renderer.height, self.scene.renderer.width):
            raise ValueError("all views in a render run must have the same resolution")
        self.scene.place(pose, camera)
        if randomize:
            m, r, c = self.scene.model, self.rng, self.cfg
            m.geom_rgba[:, :3] = r.uniform(*c["colour"], (m.ngeom, 3))
            m.light_pos[0] = r.uniform(c["lightMin"], c["lightMax"])
            m.light_diffuse[0] = r.uniform(*c["light"], 3)
            m.mat_rgba[0, :3] = r.uniform(*c["colour"], 3)
            m.mat_texrepeat[0] = r.uniform(*c["textureRepeat"], 2)
        rgb, depth = self.scene.draw()
        uv, z = camera.project(self.kp.points3d(pose))
        vis = self.visibility(uv, z, depth)
        if self.scene.cad.enabled:
            for name in self.cfg["cad"]["unlabelled"]:
                vis[self.kp.index[name]] = V_OFF
        if randomize:
            # Coarse procedural backdrop texture is independent of the robot.
            coarse = self.rng.uniform(0, 255, (8, 8, 3)).astype(np.uint8)
            backdrop = cv2.resize(coarse, (camera.width, camera.height), interpolation=cv2.INTER_CUBIC)
            rgb[depth > self.cfg["backgroundDepthMm"]] = backdrop[depth > self.cfg["backgroundDepthMm"]]
            sigma = self.rng.uniform(*self.cfg["blurSigma"])
            rgb = cv2.GaussianBlur(rgb, (0, 0), sigma)
            noise = self.rng.normal(0, self.rng.uniform(*self.cfg["noiseSigma"]), rgb.shape)
            rgb = np.clip(rgb.astype(float) + noise, 0, 255).astype(np.uint8)
        return rgb, uv, vis, depth

    def write(self, views, out):
        from PIL import Image
        views, out = private_path(views), private_path(out)
        if (out / "rendered.jsonl").exists() or any((out / "images").rglob("*.jpg")):
            raise ValueError("render destination already contains images/metadata; use a fresh dataset directory")
        out.mkdir(parents=True, exist_ok=True)
        start, counts, hidden, dropped = time.perf_counter(), {}, 0, 0
        source = SynthViews(self.kp)
        with views.open(encoding="utf-8") as inputs, (out / "rendered.jsonl").open("w", encoding="utf-8") as meta:
            for line in inputs:
                row = json.loads(line)
                name, split = row["name"], row["split"]
                if Path(name).name != name or split not in ("train", "val"):
                    raise ValueError("invalid view name or split")
                camera = Camera.from_json(row["camera"])
                rgb, uv, vis, _ = self.render(row["pose"], camera)
                if (vis == V_SEEN).sum() < self.cfg["minVisibleKeypoints"]:
                    dropped += 1
                    continue
                for kind in ("images", "labels"):
                    (out / kind / split).mkdir(parents=True, exist_ok=True)
                Image.fromarray(rgb).save(out / "images" / split / (name + ".jpg"), quality=self.cfg["jpegQuality"])
                (out / "labels" / split / (name + ".txt")).write_text(
                    self.label_line(row["pose"], camera, uv, vis) + "\n", encoding="utf-8")
                meta.write(json.dumps(dict(row, vis=vis.tolist())) + "\n")
                counts[split] = counts.get(split, 0) + 1
                hidden += int((vis == V_HIDDEN).sum())
                if sum(counts.values()) % 1000 == 0:
                    print(sum(counts.values()), "rendered", flush=True)
        (out / "dataset.yaml").write_text(source.dataset_yaml(out), encoding="utf-8")
        report = dict(images=sum(counts.values()), splits=counts, dropped=dropped, hiddenKeypoints=hidden,
                      wallS=round(time.perf_counter() - start, 3), source=str(views), rig=self.kp.rig,
                      settings=self.cfg, renderer="MuJoCo shared NongTree; CAD link appearance" if self.scene.cad.enabled else "MuJoCo shared NongTree primitives")
        (out / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def label_line(self, pose, camera, uv, vis):
        """Unlabelled anatomical anchors can still bound the whole robot post."""
        bounds = vis.copy()
        _, z = camera.project(self.kp.points3d(pose))
        for name in self.cfg["boundsLandmarks"]:
            i = self.kp.index[name]
            x, y = uv[i]
            if z[i] > 0 and 0 <= x < camera.width and 0 <= y < camera.height:
                bounds[i] = V_SEEN
        box = SynthViews.yolo_line(uv, bounds, camera.width, camera.height).split()[:5]
        labels = SynthViews.yolo_line(uv, vis, camera.width, camera.height).split()[5:]
        return " ".join(box + labels)

    def close(self):
        if self.scene is not None:
            self.scene.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("views")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    renderer = MujocoPoseRenderer()
    try:
        print(json.dumps(renderer.write(args.views, args.out), default=str))
    finally:
        renderer.close()


if __name__ == "__main__":
    main()
