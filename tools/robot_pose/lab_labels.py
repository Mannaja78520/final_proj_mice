"""Conservative labels from independently annotated, observed command holds.

    python -m tools.robot_pose.lab_labels ABSOLUTE/manifest.json --out ABSOLUTE/dataset

The private manifest supplies videos, archived logs, still windows, measured
2D calibration anchors, validated label names, split and pose acceptance.
It must never be filled with projections from the camera being fitted.
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .check import VideoCheck
from .fit import PoseFitter
from .keypoints import RobotKeypoints
from .render_mujoco import private_path
from .synth import SynthViews


class LabFrameLabels:
    def __init__(self, kp=None):
        self.kp = kp or RobotKeypoints()
        self.cfg = self.kp.cfg["labLabels"]
        self.check = VideoCheck(PoseFitter(self.kp))

    def observations(self, clip):
        points = np.zeros((len(self.kp.names), 2))
        conf = np.zeros(len(self.kp.names))
        for name, xy in clip["anchors"].items():
            points[self.kp.index[name]], conf[self.kp.index[name]] = xy, 1
        if not np.isfinite(points).all():
            raise ValueError("camera observations must be finite pixels")
        if (conf > 0).sum() < self.cfg["minAnchors"]:
            raise ValueError("not enough independently observed camera anchors")
        return points, conf

    def fit_camera(self, clips):
        holds = []
        home = self.kp.rig["home"]
        for clip in clips:
            if not clip["poseAccepted"]:
                continue
            xy, conf = self.observations(clip)
            row = dict(t=clip["stillStartVideoS"] + 1, kp=xy, conf=conf)
            holds += self.check.holds([row], lambda t: home if t >= clip["stillStartVideoS"] else None, 0)
        if not holds:
            raise ValueError("no independently observed accepted holds")
        camera = self.check.fit.fit_camera(holds)
        errors = []
        for xy, conf, pose in holds:
            projected, z = camera.project(self.kp.points3d(pose))
            if np.any(z[conf > 0] <= 0):
                raise ValueError("camera placed observed joints behind image plane")
            errors.extend(np.linalg.norm(projected[conf > 0] - xy[conf > 0], axis=1))
        if max(errors) > self.cfg["maxAnchorPx"]:
            raise ValueError(f"commanded rig disagrees with observed holds: {max(errors):.2f} px")
        return camera, dict(maxPx=float(max(errors)), rmsPx=float(np.sqrt(np.mean(np.square(errors)))),
                            observations=len(holds), metricCalibration=False,
                            limitation="one planar HOME pose; only annotated shoulder/elbow landmarks validated")

    def write(self, manifest_path, out):
        import cv2
        start = time.perf_counter()
        manifest_path, out = private_path(manifest_path), private_path(out)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if out.exists() and any(out.iterdir()):
            raise ValueError("lab output must be empty to avoid stale labels")
        clips = manifest["clips"]
        if len({str(private_path(c["video"]).resolve()) for c in clips}) != len(clips):
            raise ValueError("one split per video; duplicate video would leak train/validation")
        camera, calibration = self.fit_camera(clips)
        out.mkdir(parents=True, exist_ok=True)
        (out / "camera.json").write_text(json.dumps(camera.to_json(), indent=2), encoding="utf-8")
        rows, reasons, splits = [], Counter(), Counter()
        uv, _ = camera.project(self.kp.points3d(self.kp.rig["home"]))
        vis = np.zeros(len(uv), dtype=int)
        for name in manifest["labelNames"]:
            vis[self.kp.index[name]] = 2
        if set(manifest["labelNames"]) - set.intersection(*(set(c["anchors"]) for c in clips if c["poseAccepted"])):
            raise ValueError("every labelled landmark must have independent calibration observations")
        for clip in clips:
            video, log = private_path(clip["video"]), private_path(clip["log"])
            if "HOME OK home T=2000ms" not in log.read_text(encoding="utf-8"):
                raise ValueError("missing archived final HOME acknowledgement")
            split = clip["split"]
            if split not in ("train", "val"):
                raise ValueError("split must be train or val")
            cap = cv2.VideoCapture(str(video))
            try:
                fps, count = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if count <= 0 or fps <= 0:
                    raise ValueError("video cannot be decoded")
                if (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (camera.width, camera.height):
                    raise ValueError("video resolution differs from fitted camera")
                cap.set(cv2.CAP_PROP_POS_FRAMES, count - 1)
                ok, reference = cap.read()
                if not ok:
                    raise ValueError("reference frame missing")
                x0, y0, x1, y1 = clip["robotBox"]
                if not (0 <= x0 < x1 <= camera.width and 0 <= y0 < y1 <= camera.height):
                    raise ValueError("invalid observed robot box")
                reference = cv2.cvtColor(reference[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
                for index in clip["candidateFrames"]:
                    if not 0 <= index < count:
                        raise ValueError("candidate outside video")
                    row = dict(video=str(video), frame=index, t=index / fps, split=split)
                    observation = dict(t=row["t"], kp=np.zeros_like(uv), conf=vis / 2)
                    hold = self.check.holds([observation], lambda t: self.kp.rig["home"] if t + 1e-8 >= clip["stillStartVideoS"] else None, 0)
                    reason = "hold boundary" if not hold else (clip.get("rejection") or "command pose rejected") if not clip["poseAccepted"] else ""
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok:
                        reason = "decode failed"
                    elif not reason:
                        gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
                        difference = float(np.abs(gray.astype(float) - reference).mean())
                        row["stillMeanAbs"] = difference
                        if difference > self.cfg["stillMeanAbs"]:
                            reason = "observed motion"
                    if not reason and np.any((uv[vis > 0] < [x0, y0]) | (uv[vis > 0] >= [x1, y1])):
                        reason = "projection outside observed robot"
                    row["decision"] = reason or "kept"
                    reasons[row["decision"]] += 1
                    if not reason:
                        for kind in ("images", "labels"):
                            (out / kind / split).mkdir(parents=True, exist_ok=True)
                        name = f"{video.stem}_{index:06d}"
                        if not cv2.imwrite(str(out / "images" / split / (name + ".jpg")), frame):
                            raise OSError("could not write lab image")
                        label = SynthViews.yolo_line(uv, vis, camera.width, camera.height).split()
                        label[1:5] = [f"{v:.6f}" for v in ((x0 + x1) / 2 / camera.width,
                            (y0 + y1) / 2 / camera.height, (x1 - x0) / camera.width, (y1 - y0) / camera.height)]
                        (out / "labels" / split / (name + ".txt")).write_text(" ".join(label) + "\n", encoding="utf-8")
                        splits[split] += 1
                    rows.append(row)
            finally:
                cap.release()
        report = dict(candidates=len(rows), kept=reasons["kept"], dropped=len(rows) - reasons["kept"],
                      decisions=dict(reasons), splits=dict(splits), labelledKeypoints=manifest["labelNames"],
                      cameraFit=calibration, corrupt=manifest.get("corrupt", []), wallS=round(time.perf_counter() - start, 3),
                      visualReview="pending; complete independent contact-sheet sample before training")
        (out / "frames.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (out / "dataset.yaml").write_text(SynthViews(self.kp).dataset_yaml(out), encoding="utf-8")
        return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    print(json.dumps(LabFrameLabels().write(args.manifest, args.out)))


if __name__ == "__main__":
    main()
