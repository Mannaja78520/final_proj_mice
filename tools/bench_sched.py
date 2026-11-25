"""Measure what the shared scheduler changes, same load, plain lock vs scheduler.

Load (all numbers are arguments): `workers` background threads each run
`items` pieces of `piece` seconds on the one GPU (the translation pool), while
live questions of `live_run` seconds arrive every `gap` seconds. The plain
lock is what Voice had; the scheduler is tools/jobsched.py with config/scheduler.json.
Prints and (with --out) saves the waits a live question suffered.

  python tools/bench_sched.py --out .local/perf/sched.json
"""
import argparse
import json
import statistics
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import jobsched  # noqa: E402


def scenario(gate_for, workers, items, piece, lives, gap, live_run):
    live_waits, ends = [], []
    t0 = time.monotonic()

    def background():
        for _ in range(items):
            with gate_for("translate"):
                time.sleep(piece)
        ends.append(time.monotonic() - t0)

    def live():
        asked = time.monotonic()
        with gate_for("live"):
            live_waits.append(time.monotonic() - asked)
            time.sleep(live_run)

    bg = [threading.Thread(target=background) for _ in range(workers)]
    for t in bg:
        t.start()
    asks = []
    for _ in range(lives):
        time.sleep(gap)
        t = threading.Thread(target=live)
        t.start()
        asks.append(t)
    for t in asks + bg:
        t.join()
    return {"liveWaitMs": [round(w * 1000) for w in live_waits],
            "liveP50Ms": round(statistics.median(live_waits) * 1000),
            "liveMaxMs": round(max(live_waits) * 1000),
            "backgroundDoneS": round(max(ends), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--items", type=int, default=12)
    ap.add_argument("--piece", type=float, default=0.25)
    ap.add_argument("--lives", type=int, default=8)
    ap.add_argument("--gap", type=float, default=0.6)
    ap.add_argument("--live-run", type=float, default=0.15)
    ap.add_argument("--out")
    a = ap.parse_args()
    args = (a.workers, a.items, a.piece, a.lives, a.gap, a.live_run)
    plain = threading.Lock()
    before = scenario(lambda k: plain, *args)
    sched = jobsched.Scheduler.from_file(ROOT / "config" / "scheduler.json")
    after = scenario(sched.gate, *args)
    res = {"load": vars(a), "plainLock": before, "scheduler": after, "schedulerStatus": sched.status()}
    print("live question wait: plain lock p50 %d ms max %d ms | scheduler p50 %d ms max %d ms"
          % (before["liveP50Ms"], before["liveMaxMs"], after["liveP50Ms"], after["liveMaxMs"]))
    print("background all done: plain %.2f s | scheduler %.2f s" % (before["backgroundDoneS"], after["backgroundDoneS"]))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
