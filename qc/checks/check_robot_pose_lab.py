"""Synthetic recorded holds prove motion, command disagreement and split guards.

This verifies the lab-label tool, not the actual accuracy of lab observations.
Fixture media are created and removed exclusively under the PC's .local.
"""
import copy
import json
import tempfile
from pathlib import Path

AREA = "robot-pose"
TITLE = "lab labels require observed holds, camera anchors, and video-separated splits"
SLOW = False


def run(t):
    import cv2
    import numpy as np
    from tools.robot_pose.camera import Camera
    from tools.robot_pose.lab_labels import LabFrameLabels
    from tools.robot_pose.synth import SynthViews
    lab = LabFrameLabels()
    kp = lab.kp
    camera = Camera.orbit(0, 10, 1500, [0, 90, 0], 60, 640, 480)
    uv, _ = camera.project(kp.points3d(kp.rig["home"]))
    names = ["L_shoulder", "R_shoulder", "L_elbow", "R_elbow"]
    anchors = {n: uv[kp.index[n]].tolist() for n in names}
    from tools.robot_pose.render_mujoco import REAL as code
    (code / ".local").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=code / ".local", prefix="robot_pose_lab_qc_") as temp:
        root = Path(temp)
        (root / "home.log").write_text("HOME OK home T=2000ms\n", encoding="utf-8")
        clips = []
        for name in ("good", "bad"):
            video = root / (name + ".avi")
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 15, (640, 480))
            if not writer.isOpened():
                raise RuntimeError("QC video encoder unavailable")
            try:
                for i in range(40):
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    if i == 34:
                        frame[:] = 220
                    writer.write(frame)
            finally:
                writer.release()
            clips.append(dict(video=str(video), log=str(root / "home.log"), split="train", candidateFrames=list(range(25, 40)),
                              stillStartVideoS=25 / 15, anchors=anchors, robotBox=[0, 0, 640, 480],
                              poseAccepted=name == "good", rejection="known pose disagreement" if name == "bad" else ""))
        manifest = dict(labelNames=names, clips=clips)
        source = root / "manifest.json"
        source.write_text(json.dumps(manifest), encoding="utf-8")
        report = lab.write(source, root / "dataset")
        t.eq(report["candidates"], 30, "every held-frame candidate accounted for")
        t.eq(report["decisions"].get("observed motion"), 1, "observed motion rejected despite unchanged command")
        t.eq(report["decisions"].get("known pose disagreement"), 9, "still but wrong commanded pose rejected")
        t.eq(report["decisions"].get("hold boundary"), 12, "hold edges trimmed by VideoCheck.holds")
        t.eq(report["kept"], 8, "only valid still command frames kept")
        label = next((root / "dataset/labels/train").glob("*.txt")).read_text().split()
        vis = [int(float(v)) for v in label[7::3]]
        t.eq(sum(v == 2 for v in vis), 4, "only independently validated landmarks labelled")
        t.eq(len(label), 5 + 3 * len(kp.names), "partial labels retain registered keypoint order")
        t.ok(report["cameraFit"]["maxPx"] < lab.cfg["maxAnchorPx"], "camera fitted from known synthetic observations", str(report["cameraFit"]))
        for kind in ("missing anchors", "duplicate video", "bad log", "populated output"):
            changed = copy.deepcopy(manifest)
            destination = root / kind
            if kind == "missing anchors":
                changed["clips"][0]["anchors"] = {names[0]: anchors[names[0]]}
            elif kind == "duplicate video":
                changed["clips"][1]["video"] = changed["clips"][0]["video"]
                changed["clips"][1]["split"] = "val"
            elif kind == "bad log":
                (root / "unproven.log").write_text("HOME timeout", encoding="utf-8")
                changed["clips"][0]["log"] = str(root / "unproven.log")
            else:
                destination = root / "dataset"
            source.write_text(json.dumps(changed), encoding="utf-8")
            try:
                lab.write(source, destination)
                t.ok(False, kind + " refused", "unsafe labels accepted")
            except ValueError:
                t.ok(True, kind + " refused", "no inferred observation/timing")
