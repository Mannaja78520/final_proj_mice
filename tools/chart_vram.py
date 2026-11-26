"""Charts and a table from a tools/vram_measure.py session folder.

    python tools/chart_vram.py .local/perf/vram_2026-11-26 --out docs/img/perf_vram_sizes.png \
        --out2 docs/img/perf_vram_strategies.png --md docs/img/perf_vram_tables.md

Reads <setting>/perf*.json (tools/perf_load.py output) and <setting>/info.json. A setting folder is named
cap_<MiB> (card size, spill = the planner as shipped), cap_uncapped (the whole card), <strategy>_<MiB> (swap or hybrid at that
size) or <strategy>_budget<MiB> (the reduced run's Voice budget).
  --out   p50/p95/p99 of ask and hearing against the card size (spill)
  --out2  spill / swap / hybrid side by side at every size that has more than one strategy
  --md    one table with every setting
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
FULL = 100000                                           # sort key and label of the uncapped card


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
    if name == "cap_uncapped":
        return "spill", FULL
    return None


def size_label(size):
    return "whole card" if size == FULL else "%g GB" % (size / 1024)


def on_gpu(info):
    return sorted(k.split(":", 1)[-1].split("/")[-1] for k, v in (info.get("devicesAfter") or info.get("devices") or {}).items()
                  if str(v).startswith("cuda"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--out2", default="")
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

    # 1. against the card size (spill)
    spill = [s for s in sizes if "spill" in settings[s]]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=150)
    for ax, work in zip(axes, ("stt", "voice")):
        for field, style in (("med_ms", "o-"), ("p95_ms", "s--"), ("p99_ms", "^:")):
            ys = [mean(settings[s]["spill"][0], work, field) for s in spill]
            ax.plot(range(len(spill)), ys, style, color=COLORS["spill"], label=field[:3], alpha=1.0 if field != "p99_ms" else 0.7)
            for i, y in enumerate(ys):
                if field == "p95_ms":
                    ax.annotate("%d" % round(y), (i, y), ha="center", va="bottom", fontsize=7, xytext=(0, 4), textcoords="offset points")
        gpu = [len(on_gpu(settings[s]["spill"][1])) for s in spill]
        ax.set_xticks(range(len(spill)))
        ax.set_xticklabels(["%s\n%d on GPU" % (size_label(s), n) for s, n in zip(spill, gpu)], fontsize=8)
        ax.set_title("%s against the card size, spill (ms)" % LABEL[work], fontsize=10, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out)
    print("wrote", a.out)

    # 2. strategies side by side
    multi = [s for s in sizes if len(settings[s]) > 1]
    if a.out2 and multi:
        fig, axes = plt.subplots(2, len(multi), figsize=(5.4 * len(multi), 7.4), dpi=150, squeeze=False)
        for col, size in enumerate(multi):
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
                ax.set_title("%s at %s (ms)" % (field[:3], size_label(size)), fontsize=10, loc="left")
                ax.spines[["top", "right"]].set_visible(False)
                if row == 0 and col == 0:
                    ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(a.out2)
        print("wrote", a.out2)

    if a.md:
        lines = ["| card | strategy | ask p50/p95/p99 | hearing p50/p95/p99 | face look p50/p95/p99 | camera p50/p95/p99 | background jobs in 60 s | on the GPU |",
                 "|---|---|---|---|---|---|---|---|"]
        for size in sizes:
            for strat in ("spill", "swap", "hybrid"):
                if strat not in settings[size]:
                    continue
                runs, info = settings[size][strat]
                cells = ["%d / %d / %d" % tuple(round(mean(runs, k, f)) for f in ("med_ms", "p95_ms", "p99_ms")) for k in WORK]
                lines.append("| %s | %s | %s | %.0f | %s |" % (size_label(size), strat, " | ".join(cells), mean(runs, "helper", "calls"),
                                                           ", ".join(on_gpu(info)) or "none"))
        Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("wrote", a.md)


if __name__ == "__main__":
    main()
