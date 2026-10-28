"""2D keypoints from a video with a YOLO pose model trained on nong (optional).

Needs `pip install ultralytics opencv-python` and a model at config detector.model
(training: handoff/tasks/robot-pose-data.md). Writes the keypoints file every
other step reads, one JSON per line:
    {"names": [...]}                                  first line
    {"t": 1.23, "cam": 0, "kp": [[x, y], ...], "conf": [...]}
so a check can also run on keypoints from anywhere else (hand labels, markers).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class YoloKeypoints:
    def __init__(self, cfg, names):
        from ultralytics import YOLO          # optional: only this step needs it
        self.cfg, self.names = cfg["detector"], names
        self.model = YOLO(str(ROOT / self.cfg["model"]))

    def video(self, path, every_s=0.2, cam=0):
        import cv2
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        step = max(1, round(every_s * fps))
        n = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if n % step == 0:
                r = self.model.predict(frame, conf=self.cfg["conf"], verbose=False)[0]
                if r.keypoints is not None and len(r.keypoints):
                    best = int(r.boxes.conf.argmax())          # one robot: the surest box
                    xy = r.keypoints.xy[best].tolist()
                    cf = (r.keypoints.conf[best].tolist() if r.keypoints.conf is not None
                          else [1.0] * len(xy))
                    yield {"t": n / fps, "cam": cam, "kp": xy, "conf": cf}
            n += 1
        cap.release()


def write_keypoints(path, names, rows):
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"names": names}) + "\n")
        for r in rows:
            f.write(json.dumps(r) + "\n")


def read_keypoints(path, names):
    """-> rows, re-ordered to `names` (a file made with another keypoint list still reads)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    head = json.loads(lines[0])["names"]
    order = [head.index(n) if n in head else None for n in names]
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        r = json.loads(line)
        r["kp"] = [r["kp"][i] if i is not None else [0, 0] for i in order]
        r["conf"] = [r["conf"][i] if i is not None else 0.0 for i in order]
        rows.append(r)
    return rows
