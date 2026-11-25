"""Chart of what the shared scheduler changes: live-question wait, before vs after.

Reads the files written by tools/bench_sched.py (simulation) and
tools/perf_load.py (real apps, scheduler on and off) and writes one PNG.
Panels with no input file are left out.

  python tools/chart_sched.py --sim .local/perf/sched_sim.json \
      --on .local/perf/sched_on.json --off .local/perf/sched_off.json \
      --bg-on .local/perf/bg_on1.json .local/perf/bg_on2.json \
      --bg-off .local/perf/bg_off1.json .local/perf/bg_off2.json \
      --out docs/img/perf_scheduler_2026-11-25.png
"""
import argparse
import json
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BEFORE, AFTER = "#8a8f98", "#2f6fed"


def _pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(round(p / 100 * len(v))) - 1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="")
    ap.add_argument("--on", default="")
    ap.add_argument("--off", default="")
    ap.add_argument("--bg-on", nargs="+", default=[],
                    help="perf_load files made with --helpers, scheduler on (averaged)")
    ap.add_argument("--bg-off", nargs="+", default=[], help="same, scheduler off")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    panels = []
    if a.sim and Path(a.sim).is_file():
        s = json.loads(Path(a.sim).read_text(encoding="utf-8"))
        b, n = s["plainLock"]["liveWaitMs"], s["scheduler"]["liveWaitMs"]
        panels.append(("Simulation: live question wait (ms)", "wait",
                       [statistics.median(b), _pct(b, 95)], [statistics.median(n), _pct(n, 95)]))
    if a.on and a.off and Path(a.on).is_file() and Path(a.off).is_file():
        on = json.loads(Path(a.on).read_text(encoding="utf-8"))["together"]["voice"]
        off = json.loads(Path(a.off).read_text(encoding="utf-8"))["together"]["voice"]
        panels.append(("Real apps, all running: Voice /ask latency (ms)", "latency",
                       [off["med_ms"], off["p95_ms"]], [on["med_ms"], on["p95_ms"]]))
    if a.bg_on and a.bg_off:
        def avg(files, key, field):
            vals = [json.loads(Path(f).read_text(encoding="utf-8"))["together"][key][field] for f in files]
            return statistics.mean(vals)
        keys = [("voice", "med_ms"), ("voice", "p95_ms"), ("stt", "med_ms"), ("stt", "p95_ms")]
        jobs_on, jobs_off = avg(a.bg_on, "helper", "calls"), avg(a.bg_off, "helper", "calls")
        panels.append(("With 4 background helper threads: live Voice /ask and STT (ms)\n"
                       "background jobs done in 20 s: off %.0f, on %.0f" % (jobs_off, jobs_on), "bg",
                       [avg(a.bg_off, k, f) for k, f in keys], [avg(a.bg_on, k, f) for k, f in keys],
                       ["ask p50", "ask p95", "stt p50", "stt p95"]))
    if not panels:
        raise SystemExit("no input files found")

    fig, axes = plt.subplots(1, len(panels), figsize=(5.6 * len(panels) + (1.6 if len(panels) > 2 else 0), 4.6), dpi=160, squeeze=False)
    for ax, (title, _, before, after, *lab) in zip(axes[0], panels):
        xs = list(range(len(before)))
        w = 0.36
        b1 = ax.bar([x - w / 2 for x in xs], before, w, color=BEFORE, label="before: plain FIFO")
        b2 = ax.bar([x + w / 2 for x in xs], after, w, color=AFTER, label="after: scheduler")
        for bars in (b1, b2):
            for r in bars:
                ax.annotate("%d" % round(r.get_height()), (r.get_x() + r.get_width() / 2, r.get_height()),
                            ha="center", va="bottom", fontsize=9, xytext=(0, 2), textcoords="offset points")
        ax.set_xticks(xs)
        ax.set_xticklabels(lab[0] if lab else ["p50", "p95"])
        ax.set_title(title, fontsize=10.5, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2)
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
