"""One filmed move -> is every joint where the file said? (A52-3)

keypoints file (detect.py) + the sequence that was played -> camera (from the
first hold, or given), joint angles per frame, MoveCheck report, raw rows.
Static camera(s), robot on its base; `start` = video second the show began.
"""
import json
import time
from pathlib import Path

import numpy as np

from .camera import Camera
from .compare import MoveCheck, commanded_from_sequence
from .fit import PoseFitter

ROOT = Path(__file__).resolve().parents[2]


class VideoCheck:
    HOLD_S = 0.4        # a frame is a hold when the command is still for +-this long

    def __init__(self, fitter=None):
        self.fit = fitter or PoseFitter()
        self.kp, self.cfg = self.fit.kp, self.fit.cfg

    def holds(self, rows, commanded, start):
        out = []
        for r in rows:
            t = r["t"] - start
            a, b, c = commanded(t - self.HOLD_S), commanded(t), commanded(t + self.HOLD_S)
            if a and c and max(abs(x - y) for x, y in zip(a, c)) < 0.5 and max(abs(x - y) for x, y in zip(a, b)) < 0.5:
                out.append((np.array(r["kp"], float), np.array(r["conf"], float), b))
        return out

    def run(self, rows, seq_text, start=0.0, camera=None, safe_dps=None, max_holds=12):
        t0 = time.time()
        commanded, length = commanded_from_sequence(seq_text, self.kp.rig, self.kp.facts, safe_dps)
        rows = [r for r in rows if 0 <= r["t"] - start <= length]
        if camera is None:
            holds = self.holds(rows, commanded, start)
            if not holds:
                raise ValueError("no still moment in the video to place the camera; pass a camera file")
            camera = self.fit.fit_camera(holds[:: max(1, len(holds) // max_holds)][:max_holds])
        times, seen, per = [], [], []
        prev = None
        for r in rows:
            t = r["t"] - start
            start_pose = commanded(t) if prev is None else prev
            f = self.fit.fit_pose(camera, np.array(r["kp"], float), np.array(r["conf"], float), start_pose)
            prev = f.pose
            times.append(t)
            seen.append(f.pose)
            per.append({"t": round(t, 3), "seen": [round(v, 2) for v in f.pose],
                        "commanded": [round(v, 2) for v in commanded(t)], "rmsPx": round(f.rms_px, 2),
                        "facing": f.facing, "facingDeg": round(f.facing_deg, 1), "swapped": f.swapped})
        report = MoveCheck(self.kp.facts.joint_names, self.cfg).run(times, seen, commanded)
        facings = [p["facing"] for p in per]
        report.update({"camera": camera.to_json(), "fitS": time.time() - t0,
                       "facing": max(set(facings), key=facings.count) if facings else None,
                       "swappedFrames": sum(p["swapped"] for p in per),
                       "medianRmsPx": float(np.median([p["rmsPx"] for p in per])) if per else None})
        return report, per


def write_report(out_dir, name, report, per):
    out = Path(out_dir) / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (out / "frames.jsonl").write_text("\n".join(json.dumps(p) for p in per) + "\n", encoding="utf-8")
    lines = ["# Robot pose check: %s" % name, "",
             "verdict **%s**, %d frames, facing %s, median fit %.1f px" % (
                 report["verdict"], report["frames"], report["facing"], report["medianRmsPx"] or 0), "",
             "| joint | verdict | mean deg | p95 deg | bias deg | lag s | told range | seen range |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for j in report["joints"]:
        lines.append("| %s | %s | %.1f | %.1f | %+.1f | %+.2f | %.0f | %.0f |" % (
            j["joint"], j["verdict"], j["meanAbsDeg"], j["p95Deg"], j["biasDeg"], j["lagS"],
            j["commandedRangeDeg"], j["seenRangeDeg"]))
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
