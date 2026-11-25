#!/usr/bin/env python3
"""Live QC: hit the apps that are ALREADY RUNNING, all at once, read-only.

    python tools/qc_live.py                 15 s, 4 clients per app
    python tools/qc_live.py --seconds 60 --clients 8
    python tools/qc_live.py --selftest      against throwaway local servers

Why: the isolated QC boots a private hub per check, so it never sees what
happens when voice + face recognition + cameras + hub pages share the machine.
This sends GETs only (probe list: qc/data/live_probes.json), so it cannot
change anything, needs no restart, and is safe on a hub in real use.

It measures each app ALONE first, then ALL TOGETHER, and reports latency
(p50/p95/max) and errors for both. contention = together p95 / alone p95.
Apps that are not running are listed as "not running", not as failures.
Exit 1 when a running app breaks a budget. 2026-11-25.
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PROBES = Path(__file__).resolve().parent.parent / "qc" / "data" / "live_probes.json"


def _arg(argv, name, default):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return type(default)(argv[i + 1])
    return default


def fetch(url, timeout=10):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(65536)
            ok = r.status < 500
    except urllib.error.HTTPError as e:      # 401/403/404 = it answered
        ok = e.code < 500
    except Exception:                        # noqa: BLE001
        ok = False
    return (time.perf_counter() - t0) * 1000.0, ok


def alive(base):
    return fetch(base + "/", timeout=2)[1] or fetch(base + "/health", timeout=2)[1]


def pct(vals, p):
    if not vals:
        return 0.0
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(p / 100.0 * (len(v) - 1))))]


def hammer(groups, seconds, clients):
    """Every group at once: `clients` threads each, cycling its paths."""
    stats = {g: {"ms": [], "err": 0} for g in groups}
    lock = threading.Lock()
    stop = time.time() + seconds

    def worker(g, spec, k):
        paths, i = spec["paths"], k
        while time.time() < stop:
            ms, ok = fetch(spec["base"] + paths[i % len(paths)])
            i += 1
            with lock:
                stats[g]["ms"].append(ms)
                stats[g]["err"] += 0 if ok else 1
            time.sleep(0.02)

    ts = [threading.Thread(target=worker, args=(g, s, k), daemon=True)
          for g, s in groups.items() for k in range(clients)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return stats


def summarize(s):
    n = len(s["ms"])
    return {"n": n, "p50": pct(s["ms"], 50), "p95": pct(s["ms"], 95),
            "max": max(s["ms"] or [0]), "errors": s["err"],
            "err_rate": (s["err"] / n) if n else 0.0}


def run(cfg, seconds, clients):
    running, idle = {}, []
    for g, spec in cfg["groups"].items():
        if alive(spec["base"]):
            running[g] = spec
        else:
            idle.append((g, spec))
    for g, _s in idle:
        print("  %-16s not running (skipped)" % g)
    if not running:
        print("nothing is running; start the hub first")
        return 0
    solo = {}
    for g, spec in running.items():                    # each one alone
        solo[g] = summarize(hammer({g: spec}, max(2, seconds // 3), clients)[g])
    both = {g: summarize(s) for g, s in hammer(running, seconds, clients).items()}
    bud, bad = cfg["budgets"], []
    print("\n  %-16s %-9s %6s %7s %7s %7s %5s" % ("app", "mode", "reqs", "p50ms", "p95ms", "maxms", "err"))
    for g in running:
        for mode, row in (("alone", solo[g]), ("together", both[g])):
            print("  %-16s %-9s %6d %7.1f %7.1f %7.1f %5d" % (
                g, mode, row["n"], row["p50"], row["p95"], row["max"], row["errors"]))
        factor = both[g]["p95"] / max(solo[g]["p95"], 1.0)
        print("  %-16s contention x%.1f" % ("", factor))
        if both[g]["p95"] > bud["p95_ms"]:
            bad.append("%s p95 %.0f ms > %d" % (g, both[g]["p95"], bud["p95_ms"]))
        if both[g]["err_rate"] > bud["max_error_rate"]:
            bad.append("%s errors %d/%d" % (g, both[g]["errors"], both[g]["n"]))
        if factor > bud["contention_factor"] and both[g]["p95"] > 200:
            bad.append("%s slows x%.1f when the others run" % (g, factor))
    print("\nLIVE QC " + ("FAIL: " + "; ".join(bad) if bad else "PASS"))
    return 1 if bad else 0


def selftest():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def do_GET(self):                              # noqa: N802
            time.sleep(0.005)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass
    servers = []
    cfg = {"groups": {}, "budgets": json.loads(PROBES.read_text())["budgets"]}
    for name in ("hub", "voice"):
        sv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        servers.append(sv)
        cfg["groups"][name] = {"base": "http://127.0.0.1:%d" % sv.server_port, "paths": ["/", "/health"]}
    cfg["groups"]["off"] = {"base": "http://127.0.0.1:1", "paths": ["/"]}
    code = run(cfg, 3, 3)
    [s.shutdown() for s in servers]
    return code


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--selftest" in a:
        sys.exit(selftest())
    sys.exit(run(json.loads(PROBES.read_text(encoding="utf-8")),
                 _arg(a, "--seconds", 15), _arg(a, "--clients", 4)))
