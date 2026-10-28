"""nong's skeleton from a camera (A52-3). Results go to .local (git-ignored).

    python -m tools.robot_pose synth --n 20000            YOLO-pose training views (labels + stick pictures)
    python -m tools.robot_pose detect VIDEO.mp4           keypoints file (needs ultralytics + a trained model)
    python -m tools.robot_pose check KP.jsonl SEQ.yaml --start 3.2   seen vs commanded, per joint
    python -m tools.robot_pose calibrate KP.jsonl SEQ.yaml --start 3.2  length / offset suggestions
"""
import argparse
import json
import sys
from pathlib import Path

from .calibrate import Calibrator
from .camera import Camera
from .check import VideoCheck, write_report
from .fit import PoseFitter
from .detect import YoloKeypoints, read_keypoints, write_keypoints
from .keypoints import RobotKeypoints, load_config
from .synth import SynthViews

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["synth", "detect", "check", "calibrate"])
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--start", type=float, default=0.0, help="video second the show started")
    ap.add_argument("--camera", help="camera json (from an earlier report); default: fitted from a hold")
    ap.add_argument("--every", type=float, default=0.2, help="detect: seconds between frames")
    ap.add_argument("--rig", help="a Studio rig/settings json instead of rig_default.json")
    a = ap.parse_args(argv)
    cfg = load_config()
    from tools.nong_sim.studio import load_rig
    kp = RobotKeypoints(load_rig(a.rig), cfg=cfg)
    if a.action == "synth":
        out = ROOT / (a.out or cfg["synth"]["out"])
        n = SynthViews(kp).write(out, a.n, images=not a.no_images)
        print("%d views -> %s" % (n, out))
    elif a.action == "detect":
        video = Path(a.inputs[0])
        out = Path(a.out or video.with_suffix(".kp.jsonl"))
        write_keypoints(out, kp.names, YoloKeypoints(cfg, kp.names).video(video, a.every))
        print("keypoints ->", out)
    else:
        rows = read_keypoints(a.inputs[0], kp.names)
        seq = Path(a.inputs[1]).read_text(encoding="utf-8")
        cam = Camera.from_json(json.loads(Path(a.camera).read_text(encoding="utf-8"))) if a.camera else None
        vc = VideoCheck(PoseFitter(kp, cfg))
        name = Path(a.inputs[0]).name.split(".")[0]
        if a.action == "check":
            report, per = vc.run(rows, seq, a.start, cam)
            out = write_report(ROOT / (a.out or cfg["reports"]), name, report, per)
            print("verdict %s -> %s" % (report["verdict"], out / "report.md"))
        else:
            from .compare import commanded_from_sequence
            commanded, _ = commanded_from_sequence(seq, kp.rig, kp.facts)
            holds = vc.holds(rows, commanded, a.start)
            cam = cam or vc.fit.fit_camera(holds[:12])
            res = Calibrator(kp, cfg).run([cam], [(p, [k], [c]) for k, c, p in holds])
            out = ROOT / (a.out or cfg["reports"]) / name
            out.mkdir(parents=True, exist_ok=True)
            (out / "calibrate.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
            print(json.dumps(res["lengthsMm"], indent=1), json.dumps(res["jointOffsetDeg"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
