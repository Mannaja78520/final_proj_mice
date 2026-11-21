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
extern "C" int mayrule(int nameRule, const char* a, const char* b, int cc, int rc) { return wifilink::mayJoinRule(nameRule != 0, a, b, cc, rc) ? 1 : 0; }
''')
    subprocess.check_call(["g++", "-shared", "-fPIC", "-O1", "-I", str(d), str(d / "shim.cpp"),
                           "-o", str(d / "shim.so")])
    lib = ctypes.CDLL(str(d / "shim.so"))
    lib.mayjoin.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.mayrule.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    return lib


def rssi(a, b, rng, noise):
    d = max(1.0, math.dist(a, b))
    v = -40 - 30 * math.log10(d) + rng.gauss(0, noise)
    return int(v) if v > -90 else 0          # 0 = not seen, like the scan


def run(lib, name, router, pos, rounds=30, noise=3.0, rule="name", seed=1):
    rng = random.Random(seed)
    names = ["m%02d" % i for i in range(len(pos))]
    host = [None] * len(pos)                  # index of the module it leans on
    heard = [0] * len(pos)                    # router channel once heard (0 = never)
    ROUTER_CH = 6
    flips = 0
    for _ in range(rounds):
        # who is on air with which channel THIS round: online = hotspot on the router's channel,
        # not online = channel 1, relaying = hidden (online rule only)
        if rule == "online":                  # a relay hides its hotspot, which kicks whoever leaned on it
            for k in range(len(pos)):
                if host[k] is not None and host[host[k]] is not None:
                    host[k] = None
                    flips += 1
        online = [host[k] is None and rssi(pos[k], router, random.Random(0), 0) != 0 for k in range(len(pos))]
        for i in range(len(pos)):
            main = rssi(pos[i], router, rng, noise)
            if main:
                heard[i] = ROUTER_CH
            best, best_name = 0, None
            for j in range(len(pos)):
                if j == i:
                    continue
                if rule == "name":
                    if not lib.mayjoin(names[i].encode(), names[j].encode()):
                        continue
                else:
                    if host[j] is not None:
                        continue                 # a relaying board hides its hotspot
                    ch = ROUTER_CH if online[j] else 1
                    if not lib.mayrule(0, names[i].encode(), names[j].encode(), ch, heard[i]):
                        continue
                r = rssi(pos[i], pos[j], rng, noise)
                if r and (not best or r > best):
                    best, best_name = r, j
            act = lib.decide(1 if host[i] is not None else 0, main, best)
            if rule == "online" and act == 1 and any(host[k] == i for k in range(len(pos))):
                act = 0                          # a board others lean on never leaves (hiding would kick them)
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
    return {"rule": rule, "scenario": name, "boards": len(pos), "direct": sum(d == 0 for d in depths),
            "one_hop": one_hop, "two_or_more_hops": sum(d is not None and d >= 2 for d in depths),
            "stranded": sum(d is None for d in depths), "longest_chain": max([d for d in depths if d is not None] or [0]),
            "flips_per_board_per_round": round(flips / len(pos) / rounds, 3), "noise_db": noise}


def run_no_router(lib, n, cap, area=20.0, seed=7, rounds=20, noise=3.0):
    """Boards of ONE company, no router anywhere: do they find each other by themselves?

    Every hotspot is on channel 1 (nobody is online), so the online rule cannot tell hosts apart and the
    name rule decides (WifiLink.h mayJoinRule -> mayJoin): a board only joins a hotspot whose name sorts
    after its own, so the highest name is the root. `cap` is the hotspot's client limit (ESP32 softAP
    default 4, hardware maximum 10). A board that already hosts clients never moves (firmware rule);
    a full hotspot refuses. Boards start in random order, one decision each per round.
    """
    rng = random.Random(seed)
    pos = [(rng.uniform(0, area), rng.uniform(0, area)) for _ in range(n)]
    names = ["m%03d" % i for i in range(n)]
    host = [None] * n
    for _ in range(rounds):
        order = list(range(n))
        rng.shuffle(order)
        for i in order:
            if host[i] is not None or any(h == i for h in host):
                continue                           # leaning already, or others lean on it
            best, bj = 0, None
            for j in range(n):
                if j == i or host[j] is not None or sum(h == j for h in host) >= cap:
                    continue
                if not lib.mayrule(0, names[i].encode(), names[j].encode(), 1, 0):
                    continue
                r = rssi(pos[i], pos[j], rng, noise)
                if r and (not best or r > best):
                    best, bj = r, j
            if bj is not None:
                host[i] = bj
    roots = [j for j in range(n) if host[j] is None and any(h == j for h in host)]
    alone = [j for j in range(n) if host[j] is None and not any(h == j for h in host)]
    in_cluster = sum(h is not None for h in host) + len(roots)
    biggest = max([1 + sum(h == j for h in host) for j in roots] or [1])
    return {"boards": n, "hotspot_client_limit": cap, "clusters": len(roots), "boards_in_a_cluster": in_cluster,
            "boards_alone": len(alone), "largest_cluster": biggest, "max_hops": 1 if roots else 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    lib = load_logic()
    rows = []
    r = (0, 0)
    for rule in ("name", "online"):         # old rule vs new rule, same layouts
        for step in (8, 15, 25):             # boards in a line away from the router, step m apart
            rows.append(run(lib, "line of 10, %d m apart" % step, r, [(step * (i + 1), 0) for i in range(10)], rule=rule))
        for n, side in ((30, 60), (100, 120), (255, 200)):
            rng = random.Random(n)
            pts = [(rng.uniform(5, side), rng.uniform(-side / 2, side / 2)) for _ in range(n)]
            rows.append(run(lib, "%d boards random in %dx%d m" % (n, side, side), r, pts, rule=rule))
        rows.append(run(lib, "robot 60 m out, only 2 boards between", r, [(20, 0), (40, 0), (60, 0)], rule=rule))
    for cap in (4, 8):
        for n in (2, 5, 10, 30, 100, 255):
            rows.append(dict(run_no_router(lib, n, cap), scenario="no router, one company"))
    for x in rows:
        print(x)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
