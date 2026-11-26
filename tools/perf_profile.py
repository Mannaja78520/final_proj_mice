"""Sample what every Mice app costs on the PC while they all run together.

Asked for 2026-11-25: run hub + voice + face + games + cameras at once, find
the bottleneck, give the friend a concrete list. This only MEASURES; it never
starts, stops or tunes anything.

Per sample (every --every s, for --seconds):
  * per group (config/perf_profile.json "groups", matched on the command
    line): RAM (RSS MiB), CPU % of ONE core, process count
  * per group GPU memory (MiB): Windows "GPU Process Memory" counter, because
    nvidia-smi shows N/A per process under WDDM
  * whole GPU: util %, VRAM used, encoder %, decoder % (nvidia-smi)
  * whole PC: free RAM MiB
Output: one JSON file (raw) and a short table on stdout (median / max).

  python tools/perf_profile.py --seconds 30 --out .local/perf/idle.json
Groups are data: add an app = add a row in config/perf_profile.json.
"""
import argparse
import csv
import io
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / "config" / "perf_profile.json"


def load_groups():
    text = CONF.read_text(encoding="utf-8")
    return json.loads(text)["groups"]


def group_of(cmd, groups):
    low = cmd.lower().replace("\\", "/")
    for g in groups:
        if any(m.lower() in low for m in g["match"]):
            return g["id"]
    return None


def gpu_whole():
    q = "utilization.gpu,memory.used,utilization.encoder,utilization.decoder"
    out = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    try:
        a = [float(x) for x in out.split(",")]
        return dict(zip(["gpu_util", "vram_used", "enc_util", "dec_util"], a))
    except ValueError:
        return {}


def gpu_per_pid():
    """pid -> dedicated GPU MiB, from the Windows counter (works under WDDM)."""
    ps = ("(Get-Counter '\\GPU Process Memory(*)\\Dedicated Usage').CounterSamples |"
          " ForEach-Object { $_.InstanceName + ',' + $_.CookedValue }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return {}
    res = {}
    for line in out.splitlines():
        m = re.match(r"pid_(\d+)_.*,([\d.eE+]+)$", line.strip())
        if m:
            res[int(m.group(1))] = res.get(int(m.group(1)), 0) + float(m.group(2)) / 1048576
    return res


def sample(groups):
    pg = gpu_per_pid()
    per = {}
    for p in psutil.process_iter(["pid", "cmdline", "name"]):
        try:
            cmd = " ".join(p.info["cmdline"] or []) or p.info["name"] or ""
            gid = group_of(cmd, groups)
            if not gid:
                continue
            d = per.setdefault(gid, {"ram": 0.0, "cpu": 0.0, "n": 0, "vram": 0.0})
            d["ram"] += p.memory_info().rss / 1048576
            d["cpu"] += p.cpu_percent(None)
            d["n"] += 1
            d["vram"] += pg.get(p.info["pid"], 0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--every", type=float, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    groups = load_groups()
    sample(groups)  # primes cpu_percent
    rows = []
    t_end = time.time() + a.seconds
    while time.time() < t_end:
        time.sleep(a.every)
        rows.append({"t": time.time(), "groups": sample(groups), "gpu": gpu_whole(),
                     "free_ram": psutil.virtual_memory().available / 1048576})
    if a.out:
        Path(a.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    ids = sorted({g for r in rows for g in r["groups"]})
    print(f"{'group':14}{'RAM MiB med/max':>20}{'VRAM MiB med/max':>20}{'CPU% med/max':>16}")
    for g in ids:
        def col(k):
            v = [r["groups"].get(g, {}).get(k, 0) for r in rows]
            return statistics.median(v), max(v)
        r_, v_, c_ = col("ram"), col("vram"), col("cpu")
        print(f"{g:14}{r_[0]:>10.0f}/{r_[1]:<9.0f}{v_[0]:>10.0f}/{v_[1]:<9.0f}{c_[0]:>8.0f}/{c_[1]:<7.0f}")
    for k in ("gpu_util", "vram_used", "enc_util", "dec_util"):
        v = [r["gpu"].get(k, 0) for r in rows]
        print(f"GPU {k}: median {statistics.median(v):.0f} max {max(v):.0f}")
    fr = [r["free_ram"] for r in rows]
    print(f"PC free RAM MiB: min {min(fr):.0f} median {statistics.median(fr):.0f}")


if __name__ == "__main__":
    import polite  # our background tools run at low priority (tools/polite.py)
    polite.apply("perf_profile")
    sys.exit(main())
