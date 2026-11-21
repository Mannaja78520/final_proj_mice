"""Boards far from the router with other boards in between: what the WiFi rules do.

    python tools/bench/wifi_topology_model.py [--out file.json]

The DECISIONS are the firmware's own: firmware/src/core/WifiLink.h is compiled
here (g++) and called through ctypes, so `decide` (stay / relay / return) and
`mayJoin` (a module only joins a hotspot whose name sorts after its own) are the
shipped code, not a copy. Only the radio is a model: log-distance path loss,

    rssi = -40 - 10 * n * log10(distance_m) + noise      (n = 3 indoors)

visible down to -90 dBm, plus shadow noise of a few dB that changes every round.
Each round every board scans (router + the hotspots of the other boards it may
join) and applies the firmware rule; a board that relays through a neighbour that
is itself cut off is counted as STRANDED, because every hotspot is 192.168.4.1/24
and a station of a station has no route (firmware/src/core/WebPortal.cpp).
Reported per scenario: direct / one-hop / stranded boards, flips (changes of
link per board per round - the hysteresis check), longest chain the rules form.
NOT modelled: real antennas, walls, channel overlap, DHCP time. Lab list.
"""
import argparse
import ctypes
import json
import math
import os
import random
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "firmware" / "src" / "core" / "WifiLink.h"


def load_logic():
    d = Path(tempfile.mkdtemp())
    # copied alone: -I on firmware/src/core would shadow system headers with its own
    (d / "WifiLink.h").write_text(SRC.read_text(encoding="utf-8"))
    (d / "shim.cpp").write_text('''#include <string>   // WifiLink.h includes <string> inside its namespace; do it first
#include "WifiLink.h"
extern "C" int decide(int on, int m, int p) { return (int)wifilink::decide(on != 0, m, p); }
extern "C" int mayjoin(const char* a, const char* b) { return wifilink::mayJoin(a, b) ? 1 : 0; }
''')
    subprocess.check_call(["g++", "-shared", "-fPIC", "-O1", "-I", str(d), str(d / "shim.cpp"),
                           "-o", str(d / "shim.so")])
    lib = ctypes.CDLL(str(d / "shim.so"))
    lib.mayjoin.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    return lib


def rssi(a, b, rng, noise):
    d = max(1.0, math.dist(a, b))
    v = -40 - 30 * math.log10(d) + rng.gauss(0, noise)
    return int(v) if v > -90 else 0          # 0 = not seen, like the scan


def run(lib, name, router, pos, rounds=30, noise=3.0, known=True, seed=1):
    rng = random.Random(seed)
    names = ["m%02d" % i for i in range(len(pos))]
    host = [None] * len(pos)                  # index of the module it leans on
    flips = 0
    for _ in range(rounds):
        for i in range(len(pos)):
            main = rssi(pos[i], router, rng, noise)
            best, best_name = 0, None
            for j in range(len(pos)):
                if j == i or not lib.mayjoin(names[i].encode(), names[j].encode()):
                    continue
                if not known and False:
                    continue
                r = rssi(pos[i], pos[j], rng, noise)
                if r and (not best or r > best):
                    best, best_name = r, j
            act = lib.decide(1 if host[i] is not None else 0, main, best)
            old = host[i]
            if act == 1:
                host[i] = best_name
            elif act == 2:
                host[i] = None
            flips += old != host[i]
    direct = [i for i in range(len(pos)) if host[i] is None]
    # a board is reachable if its chain ends at a board that hears the router well enough
    def depth(i, seen=()):
        if host[i] is None:
            return 0 if rssi(pos[i], router, random.Random(0), 0) else None
        if i in seen:
            return None                        # a ring
        d = depth(host[i], seen + (i,))
        return None if d is None else d + 1
    depths = [depth(i) for i in range(len(pos))]
    one_hop = sum(d == 1 for d in depths)
    return {"scenario": name, "boards": len(pos), "direct": sum(d == 0 for d in depths),
            "one_hop": one_hop, "two_or_more_hops": sum(d is not None and d >= 2 for d in depths),
            "stranded": sum(d is None for d in depths), "longest_chain": max([d for d in depths if d is not None] or [0]),
            "flips_per_board_per_round": round(flips / len(pos) / rounds, 3), "noise_db": noise}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    lib = load_logic()
    rows = []
    r = (0, 0)
    for step in (8, 15, 25):                 # boards in a line away from the router, step m apart
        rows.append(run(lib, "line of 10, %d m apart" % step, r, [(step * (i + 1), 0) for i in range(10)]))
    rows.append(run(lib, "line of 10, 15 m apart, no shadowing", r, [(15 * (i + 1), 0) for i in range(10)], noise=0.0))
    for n, side in ((30, 60), (100, 120), (255, 200)):
        rng = random.Random(n)
        pts = [(rng.uniform(5, side), rng.uniform(-side / 2, side / 2)) for _ in range(n)]
        rows.append(run(lib, "%d boards random in %dx%d m" % (n, side, side), r, pts))
    rows.append(run(lib, "robot 60 m out, only 2 boards between", r, [(20, 0), (40, 0), (60, 0)]))
    for x in rows:
        print(x)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
