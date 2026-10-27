"""Play Nong Studio sequences on simulated robots in MuJoCo, and say what went wrong.

    python -m tools.nong_sim.play SEQ.yaml [SEQ2.yaml ...] [--robots N] [--view]
    python -m tools.nong_sim.play SEQ.yaml --report out.json      no window

Needs `pip install mujoco` (only this tool does). Settings: config/nong_sim.json.
Studio stays the judge of collisions and limits; this is a second look with
what Studio cannot model: servo lag, gravity, and the board's real clock.
Tested against Studio's own 3D scene (check_nong_sim), never on the robot.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

from .board_clock import parse_sequence
from .studio import ROOT, StudioFacts, load_rig

CONFIG = ROOT / "config" / "nong_sim.json"


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _peaks(series, dt):
    """Largest joint speed, acceleration and jerk (deg/s, /s2, /s3)."""
    best = [0.0, 0.0, 0.0]
    d = series
    for order in range(3):
        d = [[(b - a) / dt for a, b in zip(p, q)] for p, q in zip(d, d[1:])]
        if d:
            best[order] = max(max(abs(v) for v in row) for row in d)
    return best


def run(world, seconds=None, on_frame=None):
    """Play every robot to the end; returns one report per robot."""
    world.reset()
    end = seconds or world.length() + 0.5
    rows = [{"name": r["name"], "lagScale": round(r["lagScale"], 2), "worstFollowDeg": 0.0, "worstJoint": None,
             "hits": [], "nearMisses": 0, "closestMm": None, "actual": []} for r in world.robots]
    seen = set()
    while world.t < end:
        world.step_frame()
        for k, r in enumerate(world.robots):
            got = world.joint_deg(r)
            rows[k]["actual"].append(got)
            for j in r["qadr"]:
                err = abs(got[j] - r["target"][j])
                if err > rows[k]["worstFollowDeg"]:
                    rows[k]["worstFollowDeg"], rows[k]["worstJoint"] = round(err, 2), world.facts.joint_names[j]
        for k, a, b, gap in world.contacts():
            row = rows[k]
            row["closestMm"] = round(gap, 1) if row["closestMm"] is None else min(row["closestMm"], round(gap, 1))
            key = (k, a, b, round(world.t, 1))
            if gap < 0 and (k, a, b) not in seen:
                row["hits"].append({"t": round(world.t, 2), "parts": [a, b], "overlapMm": round(-gap, 1)})
                seen.add((k, a, b))
            elif gap >= 0 and key not in seen:
                row["nearMisses"] += 1
                seen.add(key)
        if on_frame and on_frame() is False:
            break
    out = []
    for k, r in enumerate(world.robots):
        row = rows[k]
        actual = row.pop("actual")
        speed, accel, jerk = _peaks(actual, 0.02)
        late = [{"step": m.line, "asked": round(m.asked, 3), "took": round(m.took, 3)}
                for m in r["moves"] if m.took - m.asked > 0.0005]
        row.update({
            "boardSeconds": round(r["clock"].length, 3), "musicSeconds": round(r["clock"].asked_length, 3),
            "behindMusicSeconds": round(r["clock"].length - r["clock"].asked_length, 3),
            "lengthenedSteps": len(late), "lengthened": late[:20],
            "peakSpeedDps": round(speed), "peakAccelDps2": round(accel), "peakJerkDps3": round(jerk)})
        out.append(row)
    return out


def view(world, speed=1.0, loop=True):
    import mujoco.viewer
    with mujoco.viewer.launch_passive(world.model, world.data) as v:
        while v.is_running():
            start = time.perf_counter()

            def frame():
                v.sync()
                wait = world.t / speed - (time.perf_counter() - start)
                if wait > 0:
                    time.sleep(wait)
                return v.is_running()
            run(world, on_frame=frame)
            if not loop:
                break


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sequences", nargs="+", type=Path)
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--rig", type=Path, help="a rig Studio saved; default from the config")
    ap.add_argument("--robots", type=int, help="how many robots; default from the config")
    ap.add_argument("--view", action="store_true", help="open the 3D window")
    ap.add_argument("--report", type=Path, help="write the report here as JSON")
    ap.add_argument("--xml", type=Path, help="also save the MuJoCo model")
    a = ap.parse_args(argv)
    try:
        import mujoco  # noqa: F401
    except ImportError:
        print("MuJoCo is not installed: pip install mujoco")
        return 2
    from .world import NongWorld
    cfg = load_config(a.config)
    if a.robots:
        cfg["robots"]["count"] = a.robots
    rig = load_rig(a.rig or (ROOT / cfg["rig"] if cfg.get("rig") else None))
    seqs = [(p.stem, parse_sequence(p.read_text(encoding="utf-8"))) for p in a.sequences]
    world = NongWorld(rig, StudioFacts(), cfg, seqs)
    if a.xml:
        a.xml.write_bytes(world.xml().encode("utf-8"))
    if a.view:
        view(world, cfg["view"]["speed"], cfg["view"]["loop"])
        return 0
    report = run(world)
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if a.report:
        a.report.write_bytes(text.encode("utf-8"))
    for row in report:
        print("%-24s lag x%.2f | %d hits, %d near | behind music %.2f s (%d steps lengthened) | worst follow %.1f deg %s"
              % (row["name"], row["lagScale"], len(row["hits"]), row["nearMisses"], row["behindMusicSeconds"],
                 row["lengthenedSteps"], row["worstFollowDeg"], row["worstJoint"] or ""))
    return 1 if any(r["hits"] for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
