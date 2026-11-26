"""Compare low-VRAM strategies by simulation: spill to CPU, swap through the GPU queue, or a mix.

User 2026-11-25: "if there is no room, which is better - the CPU, or keeping
everything on the GPU and queueing it like before? Measure." This is a
discrete-event model of one GPU (priority queue, one job at a time, model
swapping costs time) and a CPU pool, driven by service times in
config/vram_bench.json (measured where we have them, flagged ESTIMATE where
not) and by the real planner (tools/vramplan.py) for what fits.

Strategies, per card size (any size, nothing fixed):
  spill  models the planner cannot fit run on the CPU pool, the rest stay resident on the GPU
  swap   every model is used on the GPU; when it is not resident, evict the least
         important resident models, pay the swap cost, run. The GPU queue prefers
         jobs whose model is already resident (with aging) so swaps are rare.
  mix    per model: whichever of CPU or swapping gives the lower expected time for it
Load: visitors arrive every `everyS` s and run stt -> llm -> tts; background jobs
(translate/helper) arrive every `background.everyS`; live outranks background.
  python tools/bench_vram.py --out .local/perf/vram_sim.json
"""
import argparse
import heapq
import itertools
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vramplan  # noqa: E402

PRIO = {"stt": 0, "llm": 1, "tts": 2, "bg": 6}


def pctl(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def simulate(strategy, total_mib, cfg, reg, seed=1, others_mib=0):
    rnd = random.Random(seed)
    M = cfg["models"]
    size = {k: reg.info(m["key"])["mib"] for k, m in M.items()}
    cap = total_mib - others_mib - reg.headroom_mib(total_mib)
    kinds = [k for k in M if k != "bg"]
    if isinstance(strategy, dict):                       # an explicit assignment: kind -> gpu | swap | cpu
        assign, label = dict(strategy), "assign"
    else:
        label = strategy
        demands = [{"key": k, "mib": size[k], "priority": PRIO[k], "cpuSlowdown": M[k]["cpuMs"] / M[k]["gpuMs"],
                    "canCpu": True, "resident": False} for k in kinds]
        fits = {k for k, d in vramplan.pack(cap, demands).items() if d == "cuda"}
        if strategy == "spill":
            assign = {k: "gpu" if k in fits else "cpu" for k in kinds}
        elif strategy == "swap":
            assign = {k: "swap" for k in kinds}
        elif strategy == "hybrid":
            # pin what saves the most time per MiB; the rest on the CPU; background overflows to the CPU when the GPU is busy
            order = sorted(kinds, key=lambda k: -(M[k]["cpuMs"] - M[k]["gpuMs"]) / size[k])
            left_ = cap
            assign = {}
            for k in order:
                if size[k] <= left_:
                    assign[k] = "gpu"
                    left_ -= size[k]
                else:
                    assign[k] = "cpu"
        else:
            raise ValueError(strategy)
    # pinned models stay on the GPU for good; swap models share what is left; a swap model
    # that can never fit in what is left must use the CPU.
    pinned = {k for k in kinds if assign[k] == "gpu"}
    left = cap - sum(size[k] for k in pinned)
    swappable, cpu_models = set(), set()
    for k in M:
        kk = "llm" if k == "bg" else k
        a = assign[kk]
        if a == "swap" and size[kk] <= left:
            swappable.add(k)
        elif a in ("swap", "cpu"):
            cpu_models.add(k)
    pool_cap = left if strategy != "swap" or isinstance(strategy, dict) else cap
    if strategy == "swap":                               # pure swap: everything shares the whole card
        fit = {k for k in M if size["llm" if k == "bg" else k] <= cap}
        swappable, cpu_models, pinned, pool_cap = fit, set(M) - fit, set(), cap     # bigger than the card: can only use the CPU
    resident = set(k for k in M if (("llm" if k == "bg" else k) in pinned))
    # events
    jobs, t_end = [], cfg["durationS"] * 1000.0
    t = 0.0
    visitors = []
    while t < t_end:
        t += rnd.expovariate(1.0 / (cfg["visitor"]["everyS"] * 1000))
        visitors.append(t)
    bg_t, bg_times = 0.0, []
    while bg_t < t_end:
        bg_t += rnd.expovariate(1.0 / (cfg["background"]["everyS"] * 1000))
        bg_times.append(bg_t)
    # job list: (arrival, kind, visitor_id, step)
    q, gpu_free_at, cpu_free = [], 0.0, [0.0] * cfg["cpuWorkers"]
    ev = []                                              # (time, seq, kind, payload)
    seq = 0
    for i, at in enumerate(visitors):
        heapq.heappush(ev, (at, seq, "arrive", (i, 0))); seq += 1
    for at in bg_times:
        heapq.heappush(ev, (at, seq, "arrive", (-1, 0))); seq += 1
    done_visitor, job_lat = {}, {"live": [], "bg": []}
    resident_gpu = set(resident)
    last_used = {}
    gpu_busy, pending = False, []
    swaps = 0

    def used_mib():
        return sum(size["llm" if k == "bg" else k] for k in {("llm" if k == "bg" else k) for k in resident_gpu if k in swappable})

    def start_gpu(now):
        nonlocal gpu_busy, swaps, seq
        if gpu_busy or not pending:
            return
        # priority, but a job whose model is resident goes first within 1 priority step (avoids swapping)
        def key(j):
            at, kind, vid, step, pr = j
            warm = ("llm" if kind == "bg" else kind) in {("llm" if r == "bg" else r) for r in resident_gpu}
            return (pr - (0.5 if warm else 0) - (now - at) / 20000.0, at)
        pending.sort(key=key)
        at, kind, vid, step, pr = pending.pop(0)
        kk = "llm" if kind == "bg" else kind
        cost = M[kind]["gpuMs"]
        if kk not in {("llm" if r == "bg" else r) for r in resident_gpu}:
            while used_mib() + size[kk] > pool_cap and any(r in swappable for r in resident_gpu):
                worst = max((r for r in resident_gpu if r in swappable), key=lambda r: (PRIO[r], -last_used.get(r, 0)))
                resident_gpu.discard(worst)
                if worst == "llm":
                    resident_gpu.discard("bg")
            cost += M[kind]["swapOverheadMs"] + size[kk] / cfg["swapMiBperS"] * 1000
            resident_gpu.add(kind)
            swaps += 1
        last_used[kind] = now
        gpu_busy = True
        heapq.heappush(ev, (now + cost, seq, "gpu_done", (at, kind, vid, step))); seq += 1

    while ev:
        now, _, what, p = heapq.heappop(ev)
        if what == "arrive":
            vid, step = p
            kind = "bg" if vid == -1 else cfg["visitor"]["chain"][step]
            if kind in cpu_models or (strategy == "hybrid" and kind == "bg" and (gpu_busy or pending)):
                w = min(range(len(cpu_free)), key=lambda i: cpu_free[i])
                start = max(now, cpu_free[w])
                cpu_free[w] = start + M[kind]["cpuMs"]
                heapq.heappush(ev, (cpu_free[w], seq, "job_done", (now, kind, vid, step))); seq += 1
            else:
                pending.append((now, kind, vid, step, PRIO[kind]))
                start_gpu(now)
        elif what == "gpu_done":
            gpu_busy = False
            heapq.heappush(ev, (now, seq, "job_done", p)); seq += 1
            start_gpu(now)
        elif what == "job_done":
            at, kind, vid, step = p
            job_lat["bg" if vid == -1 else "live"].append(now - at)
            if vid != -1:
                if step + 1 < len(cfg["visitor"]["chain"]):
                    heapq.heappush(ev, (now, seq, "arrive", (vid, step + 1))); seq += 1
                else:
                    done_visitor[vid] = now - visitors[vid]
    e2e = list(done_visitor.values())
    return {"strategy": label, "assign": assign, "totalMiB": total_mib, "onGpu": sorted(pinned), "cpu": sorted(cpu_models),
            "swappable": sorted(swappable), "swaps": swaps,
            "visitorMs": {"p50": round(pctl(e2e, 50)), "p95": round(pctl(e2e, 95)), "p99": round(pctl(e2e, 99))},
            "liveJobMs": {"p95": round(pctl(job_lat["live"], 95)), "p99": round(pctl(job_lat["live"], 99))},
            "bgDone": len(job_lat["bg"]), "bgP95Ms": round(pctl(job_lat["bg"], 95))}


def _fits(r, cfg, reg, gb, others_gb):
    """An assignment whose pinned models do not fit the card is not allowed."""
    total = int(gb * 1024)
    cap = total - int(others_gb * 1024) - reg.headroom_mib(total)
    return sum(reg.info(cfg["models"][k]["key"])["mib"] for k in r["onGpu"]) <= cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "vram_bench.json"))
    ap.add_argument("--sizes", default="2,3,4,6,8,10,12,16")
    ap.add_argument("--others-gb", type=float, default=0.0, help="VRAM other programs (the face app) hold")
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    reg = vramplan.Registry.from_file(ROOT / "config" / "vram_models.json")
    rows = []
    for gb in [float(x) for x in a.sizes.split(",")]:
        for s in ("spill", "swap", "hybrid"):
            rows.append(simulate(s, int(gb * 1024), cfg, reg, others_mib=int(a.others_gb * 1024)))
        best = None
        for combo in itertools.product(("gpu", "swap", "cpu"), repeat=3):
            assign = dict(zip(("stt", "llm", "tts"), combo))
            r = simulate(assign, int(gb * 1024), cfg, reg, others_mib=int(a.others_gb * 1024))
            if not _fits(r, cfg, reg, gb, a.others_gb):
                continue
            if best is None or (r["visitorMs"]["p95"], r["bgP95Ms"]) < (best["visitorMs"]["p95"], best["bgP95Ms"]):
                best = r
        best["strategy"] = "mix(best)"
        rows.append(best)
    print("%5s %-6s %9s %9s %9s %9s %6s" % ("GB", "strat", "visit p50", "visit p95", "visit p99", "bg p95", "swaps"))
    for r in rows:
        print("%5.0f %-6s %9d %9d %9d %9d %6d" % (r["totalMiB"] / 1024, r["strategy"], r["visitorMs"]["p50"],
              r["visitorMs"]["p95"], r["visitorMs"]["p99"], r["bgP95Ms"], r["swaps"]))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"config": cfg, "othersGB": a.others_gb, "rows": rows}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
