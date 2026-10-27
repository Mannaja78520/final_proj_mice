"""RL vs planner on the cheer v2 dances: one command does it all (A50-1).

    python -m tools.rl_compare.run                 everything in config/rl_compare.json
    python -m tools.rl_compare.run --dance come_and_cheer_left_v2 --scenario firmware
    python -m tools.rl_compare.run --quick         tiny run: proves the pipeline only
    python -m tools.rl_compare.run --fresh         train again even if a run exists
    python -m tools.rl_compare.run --report        only rebuild the index from saved results

Per dance and scenario: Studio's planner (each variant) and the RL policy are
scored on the same servo model; RL keeps every round. Results, videos and the
index page go to the config's out folder (git-ignored, kept for the user).
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

from tools.nong_sim.studio import StudioFacts, load_rig

from .kin import TorchRig
from .metrics import Scorer
from .planner import PlannerRun
from .reference import load_dance
from .render import ComparisonVideo, RobotPainter
from .report import Report
from .rl import RLRun, pick_device
from .servo import ServoModel

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "rl_compare.json"


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


class Case:
    """One dance under one speed rule: every contender, scored the same way."""

    def __init__(self, exp, dance_name, scenario):
        self.exp, self.scenario = exp, scenario
        self.cfg = exp.cfg
        self.dance = load_dance(exp.data_dir, dance_name)
        self.out = exp.out / dance_name / scenario["id"]
        self.kin, self.servo = exp.make("cpu")
        # the scenario's collision gap: Studio adds rig extraClearanceMm to its own base gap
        base = exp.facts.clear_mm
        self.gap = scenario.get("gapMm") or base + (exp.rig.get("extraClearanceMm") or 0)
        self.extra = max(0.0, self.gap - base)
        self.scorer = Scorer(self.dance, exp.rig, self.kin, self.cfg["metrics"], self.cfg["servo"]["frameHz"], self.gap)
        self.hz = self.cfg["servo"]["frameHz"]
        self.rows = []
        self.started = time.time()

    # ---- shared scoring ----------------------------------------------
    def studio_check(self, q, name):
        """Studio's own collision verdict on the servo motion (every 2nd frame)."""
        poses = self.out / f"{name}_poses.json"
        verdict = self.out / f"{name}_studio.json"
        save_json(poses, np.round(q[::2], 2).tolist())
        subprocess.run(["node", str(HERE / "studio_eval.cjs"), str(poses), str(verdict), str(self.extra)], check=True)
        poses.unlink()
        v = json.loads(verdict.read_text(encoding="utf-8"))
        flags = np.array(v.pop("flags"), bool)
        v["flaggedS"] = float(flags.sum() * 2 / self.hz)
        v["gapMm"] = self.gap
        verdict.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
        return v

    def scored(self, cid, label, color, c, q, extra):
        s = self.scorer.score(torch.as_tensor(q), torch.as_tensor(c))
        s["studio"] = self.studio_check(np.asarray(q), cid)
        s.update(extra)
        save_json(self.out / f"{cid}_score.json", s)
        np.savez_compressed(self.out / f"{cid}_motion.npz", c=np.asarray(c), q=np.asarray(q))
        return {"id": cid, "label": label, "color": tuple(color), "q": np.asarray(q), "score": s}

    # ---- contenders ----------------------------------------------------
    def planners(self):
        for v in self.cfg["planner"]["variants"]:
            run = PlannerRun(v, self.scenario, self.exp.facts, self.extra)
            keys = run.make_keys(self.exp.data_dir, self.dance.name, self.out / f"{v['id']}_keys.json",
                                 self.cfg["planner"]["repeats"])
            c, info = run.commands(self.exp.rig, keys["keys"], self.hz)
            q = self.servo.follow(torch.as_tensor(c, dtype=self.kin.dtype)).numpy()
            info.update(computeS=keys["computeMs"] / 1000, studioScoreDeg=(keys.get("studioScore") or {}).get("meanBoneDegrees"),
                        keys=len(keys["keys"]), partial=keys.get("partial"), safe=keys.get("safe"))
            print(f"  {v['id']}: {info['computeS']:.1f}s to plan, {info['boardLengthS']:.0f}s on the board", flush=True)
            self.rows.append(self.scored(v["id"], v["label"], v["color"], c, q, info))

    def rl(self, fresh):
        rc = dict(self.cfg["rl"], collisionMm=self.gap, nearMm=max(self.cfg["metrics"]["nearMm"], self.gap + 3))
        if self.exp.quick:
            rc.update({k: self.cfg["quick"][k] for k in ("envs", "rounds", "updatesPerRound")})
        folder = self.out / rc["id"]
        done = folder / ("round_%02d" % rc["rounds"]) / "round.json"
        if fresh and folder.exists():
            shutil.rmtree(folder)
        if not done.exists():
            run = RLRun(self.dance, self.exp.make, self.scenario, rc, self.exp.device, folder)

            def on_round(r, c, q):
                s = self.scorer.score(q.cpu(), c.cpu())
                return {k: s[k] for k in ("boneMusicDeg", "boneShapeDeg", "jerkRms", "driftMedianS",
                                          "minGapMmApprox", "collisionFramesApprox", "limitFramesPct")}
            rounds = run.train(on_round)
            save_json(folder / "training.json", {"device": self.exp.device, "gpu": self.exp.gpu, "rounds": rounds,
                                                 "totalTrainS": rounds[-1]["totalTrainS"], "config": rc})
        training = json.loads((folder / "training.json").read_text(encoding="utf-8"))
        last = training["rounds"][-1]
        m = np.load(folder / ("round_%02d" % last["round"]) / "motion.npz")
        extra = {"trainS": training["totalTrainS"], "performS": last["performS"], "rounds": len(training["rounds"]),
                 "gpu": training["gpu"], "device": training["device"]}
        self.rows.append(self.scored(rc["id"], rc["label"], rc["color"], m["c"], m["q"], extra))
        self.training = training

    # ---- videos --------------------------------------------------------
    def videos(self):
        vcfg = dict(self.cfg["video"])
        q = self.exp.quick
        if q:
            vcfg["fps"] = self.cfg["quick"]["fps"]
        painter = RobotPainter(self.kin, self.exp.rig)
        src = self.exp.source_dir / f"{self.dance.source['id']}.mp4"
        title = f"{self.dance.name} · {self.scenario['label']}"
        vid = ComparisonVideo(painter, self.dance, vcfg, title, "RL vs planner · same dancer, same servo model, same song clock")
        rows = []
        for r in self.rows:
            curve = r["score"]["curve"]
            rows.append({"label": r["label"], "color": r["color"], "q": r["q"], "tag": r["id"],
                         "err": self.scorer.per_frame(torch.as_tensor(r["q"])),
                         "lag": (lambda t, c=curve: float(np.interp(t, c["t"], c["driftS"])))})
        size = self.cfg["quick"]["size"] if q else None
        length = self.cfg["quick"]["videoS"] if q else None
        vid.make(self.out / "comparison.mp4", rows, src, length, size,
                 note="ม่วง = ท่าของคนที่หุ่นควรทำ · late = หุ่นช้ากว่าเพลงกี่วินาที")
        rl = [r for r in rows if r["tag"] == self.cfg["rl"]["id"]]
        if not rl:
            return
        clips = []
        folder = self.out / self.cfg["rl"]["id"]
        for info in self.training["rounds"]:
            m = np.load(folder / ("round_%02d" % info["round"]) / "motion.npz")
            row = dict(rl[0], q=m["q"], err=self.scorer.per_frame(torch.as_tensor(m["q"])), lag=None,
                       label="RL round %d/%d · trained %.0f s" % (info["round"], len(self.training["rounds"]), info["totalTrainS"]))
            clip = folder / ("round_%02d" % info["round"]) / "clip.mp4"
            ComparisonVideo(painter, self.dance, vcfg, title,
                            "RL round %d · bone error %.1f deg on the song clock" % (info["round"], info.get("boneMusicDeg", float("nan")))
                            ).make(clip, [row], src, self.cfg["quick"]["videoS"] if q else vcfg["roundClipS"],
                                  self.cfg["quick"]["roundSize"] if q else vcfg["roundSize"])
            clips.append(clip)
        listing = folder / "clips.txt"
        listing.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-c", "copy", str(self.out / "rl_progress.mp4")], check=True)
        listing.unlink()

    def summary(self):
        out = {"dance": self.dance.name, "scenario": self.scenario, "songS": self.dance.length,
               "contenders": [{k: v for k, v in r.items() if k not in ("q",)} for r in self.rows]}
        for c in out["contenders"]:
            c["score"] = {k: v for k, v in c["score"].items() if k != "curve"}
            c["color"] = list(c["color"])
        out["record"] = self.exp.record(self.started)
        save_json(self.out / "summary.json", out)
        with open(self.exp.out / "experiments.jsonl", "a", encoding="utf-8") as log:   # every run, never overwritten
            log.write(json.dumps(out, ensure_ascii=False, default=str) + "\n")
        return out


class Experiment:
    def __init__(self, args):
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.quick = args.quick
        self.data_dir = ROOT / self.cfg["data"]["dir"]
        self.source_dir = ROOT / self.cfg["data"]["sourceDir"]
        self.out = ROOT / self.cfg["out"] / ("quick" if self.quick else "")
        self.facts = StudioFacts()
        self.rig = load_rig()
        self.device = pick_device(self.cfg["rl"]["device"])
        self.gpu = torch.cuda.get_device_name(0) if self.device == "cuda" else platform.processor() or "CPU"
        self.dances = args.dance or self.cfg["data"]["dances"]
        self.scenarios = [s for s in self.cfg["scenarios"] if not args.scenario or s["id"] in args.scenario]
        self.args = args

    def report(self):
        return Report(self.out, self.cfg, None if self.quick else ROOT / self.cfg["repoSummary"])

    def record(self, started):
        """What a later reader (or a thesis) needs to repeat this run exactly."""
        git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        import cv2
        return {"startedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                "wallS": time.time() - started, "gitCommit": git("rev-parse", "HEAD"),
                "gitDirty": bool(git("status", "--porcelain", "--", "tools/rl_compare", "config/rl_compare.json")),
                "config": self.cfg, "quick": self.quick, "device": self.device, "gpu": self.gpu,
                "cpu": platform.processor(), "os": platform.platform(), "python": platform.python_version(),
                "torch": torch.__version__, "cuda": torch.version.cuda, "opencv": cv2.__version__,
                "node": subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip(),
                "studioGapMm": self.facts.clear_mm, "safeDpsFirmware": self.facts.safe_dps}

    def make(self, device):
        return TorchRig(self.rig, self.facts, device), ServoModel(self.rig, self.facts, self.cfg["servo"], device)

    def check_rig(self, dance):
        """The planner runs on Studio's shipped rig; the dance must have been made on the same one."""
        project = json.loads((self.data_dir / f"{dance}.json").read_text(encoding="utf-8"))
        differ = [k for k, v in project.get("rig", {}).items() if k != "view" and self.rig.get(k) != v]
        if differ:
            print(f"  NOTE {dance}: its saved rig differs from rig_default.json in {differ}", flush=True)

    def run(self):
        t0 = time.time()
        print(f"device {self.device} ({self.gpu}), out {self.out}", flush=True)
        for name in self.dances:
            self.check_rig(name)
            for sc in self.scenarios:
                print(f"== {name} / {sc['id']}", flush=True)
                case = Case(self, name, sc)
                case.planners()
                case.rl(self.args.fresh)
                case.summary()
                if not self.args.no_video:
                    case.videos()
        self.report().write()
        print(f"done in {time.time() - t0:.0f} s -> {self.out / 'index.html'}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dance", action="append", help="one dance name (repeatable); default: all in the config")
    ap.add_argument("--scenario", action="append", help="one scenario id (repeatable); default: all")
    ap.add_argument("--quick", action="store_true", help="tiny run that only proves the pipeline")
    ap.add_argument("--fresh", action="store_true", help="train RL again even if a finished run is saved")
    ap.add_argument("--no-video", action="store_true", help="scores only")
    ap.add_argument("--report", action="store_true", help="only rebuild index.html from saved results")
    args = ap.parse_args(argv)
    exp = Experiment(args)
    if args.report:
        exp.report().write()
        return 0
    exp.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
