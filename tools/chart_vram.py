"""Charts and a table from a tools/vram_measure.py session folder.

    python tools/chart_vram.py .local/perf/vram_2026-11-26 --out docs/img/perf_vram_2026-11-26.png --md docs/img/perf_vram_tables.md

Reads <setting>/perf*.json (tools/perf_load.py output) and <setting>/info.json. A setting folder is named
<strategy>_budget<MiB> (the reduced run) or cap_<MiB> / <strategy>_<MiB> (the full run).
"""
import argparse
import json
import re
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = {"spill": "#2f6fed", "swap": "#d9822b", "hybrid": "#3a9d5d"}
WORK = ("voice", "stt", "face", "camera")
LABEL = {"voice": "ask", "stt": "hearing (stt)", "face": "face look", "camera": "camera frame"}


def load(folder):
    runs = [json.loads(p.read_text(encoding="utf-8"))["together"] for p in sorted(folder.glob("perf*.json"))]
    info = json.loads((folder / "info.json").read_text(encoding="utf-8")) if (folder / "info.json").exists() else {}
    return runs, info


def mean(runs, work, field):
    vals = [r[work][field] for r in runs if r.get(work, {}).get(field) is not None]
    return statistics.mean(vals) if vals else float("nan")


def parse(name):
    m = re.match(r"(spill|swap|hybrid)_budget(\d+)$", name) or re.match(r"(swap|hybrid)_(\d+)$", name)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r"cap_(\d+)$", name)
    if m:
        return "spill", int(m.group(1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default="")
    a = ap.parse_args()
    root = Path(a.folder)
    settings = {}
    for d in sorted(root.iterdir()):
        if d.is_dir() and parse(d.name) and list(d.glob("perf*.json")):
            strat, size = parse(d.name)
            settings.setdefault(size, {})[strat] = load(d)
    sizes = sorted(settings)
    if not sizes:
        raise SystemExit("no settings with perf files in " + str(root))
    fig, axes = plt.subplots(2, len(sizes), figsize=(5.4 * len(sizes), 7.4), dpi=150, squeeze=False)
    for col, size in enumerate(sizes):
        for row, field in enumerate(("p95_ms", "p99_ms")):
            ax = axes[row][col]
            strategies = [s for s in ("spill", "swap", "hybrid") if s in settings[size]]
            w = 0.8 / max(1, len(strategies))
            for j, strat in enumerate(strategies):
                runs, _ = settings[size][strat]
                ys = [mean(runs, k, field) for k in WORK]
                bars = ax.bar([i + (j - (len(strategies) - 1) / 2) * w for i in range(len(WORK))], ys, w, color=COLORS[strat], label=strat)
                for b in bars:
                    if b.get_height() == b.get_height():
                        ax.annotate("%d" % round(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()), ha="center", va="bottom",
                                    fontsize=7, xytext=(0, 2), textcoords="offset points")
            ax.set_xticks(range(len(WORK)))
            ax.set_xticklabels([LABEL[k] for k in WORK], fontsize=8)
            ax.set_title("%s, Voice budget %.1f GB (ms)" % (field[:3], size / 1024), fontsize=10, loc="left")
            ax.spines[["top", "right"]].set_visible(False)
            if row == 0 and col == 0:
                ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out)
    print("wrote", a.out)
    if a.md:
        lines = ["| budget | strategy | ask p50/p95/p99 | stt p50/p95/p99 | face look p50/p95/p99 | camera p50/p95/p99 | background jobs | models on GPU |", "|---|---|---|---|---|---|---|---|"]
        for size in sizes:
            for strat in ("spill", "swap", "hybrid"):
                if strat not in settings[size]:
                    continue
                runs, info = settings[size][strat]
                cells = ["%d / %d / %d" % tuple(round(mean(runs, k, f)) for f in ("med_ms", "p95_ms", "p99_ms")) for k in WORK]
                gpu = sorted(k for k, v in (info.get("devicesAfter") or {}).items() if str(v).startswith("cuda"))
                lines.append("| %.1f GB | %s | %s | %.0f | %s |" % (size / 1024, strat, " | ".join(cells), mean(runs, "helper", "calls"), ", ".join(gpu) or "none"))
        Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("wrote", a.md)


if __name__ == "__main__":
    main()
