"""Router-less multi-hop mesh at 5..255 boards: does a command get there and back?

    python tools/bench/mesh_model.py [--out file.json]

The forwarding rules are the firmware's own: firmware/src/core/MeshLogic.h is
compiled here (g++) and every simulated board is a real `mesh::MeshNode`. Only
the radio is modelled: log-distance path loss (-40 - 30 log10 d dBm, heard down
to -88 dBm, about 40 m), ESP-NOW airtime for the frame at 1 Mbit/s plus 0.2 ms
overhead, and collisions: a board loses a frame when another transmission it can
hear overlaps it in time (hidden boards included). Boards sit in a square sized
so each hears about 8 neighbours. One board near a corner sends a command to the
board farthest away; that board answers. Reported per run (30 random commands):
delivered with answer back, mean and worst round trip, hops, transmissions on air
per command, and frames lost to collisions.
NOT modelled: real antennas and walls, WiFi traffic on the same channel, a
board's own busy time. Lab list.
"""
import argparse
import ctypes
import json
import math
import random
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "firmware" / "src" / "core" / "MeshLogic.h"

SHIM = r'''
#include <string>
#include <vector>
#include <stdint.h>
#include "MeshLogic.h"
static uint32_t S = 2463534242u;
static uint32_t rng() { S ^= S << 13; S ^= S >> 17; S ^= S << 5; return S; }
static void tag(const uint8_t* k, size_t kl, const uint8_t* d, size_t n, uint8_t o[8]) {
    uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < kl; i++) { h ^= k[i]; h *= 1099511628211ULL; }
    for (size_t i = 0; i < n; i++) { h ^= d[i]; h *= 1099511628211ULL; }
    for (int i = 0; i < 8; i++) o[i] = (uint8_t)(h >> (8 * i));
}
static std::vector<mesh::MeshNode*> N;
static const uint8_t KEY[] = {'k', 'e', 'y'};
extern "C" {
void seed(uint32_t s) { S = s ? s : 1; }
void make(int n, int ttl, int jitter, int k) {
    for (auto p : N) delete p;
    N.clear();
    for (int i = 0; i < n; i++) {
        mesh::Config c; c.id = (uint8_t)(i + 1); c.ttl = (uint8_t)ttl; c.jitterMs = (uint16_t)jitter;
        c.suppressK = (uint8_t)k; c.key = KEY; c.keyLen = 3; c.tag = tag; c.rng = rng;
        N.push_back(new mesh::MeshNode(c));
    }
}
int send(int i, int dst, int type, const char* p, int len, uint32_t now) { return N[i]->send((uint8_t)dst, (uint8_t)type, p, len, now); }
int rx(int i, const uint8_t* b, int n, uint32_t now) { return N[i]->rx(b, n, now); }
int poll(int i, uint32_t now, uint8_t* out) { return (int)N[i]->poll(now, out, mesh::MAX_FRAME); }
int next_delivery(int i, int* type, int* src, int* hops) {
    mesh::Delivery d; if (!N[i]->nextDelivery(d)) return 0;
    *type = d.type; *src = d.src; *hops = d.hops; return 1;
}
}
'''


def load():
    d = Path(tempfile.mkdtemp())
    (d / "MeshLogic.h").write_text(SRC.read_text(encoding="utf-8"))
    (d / "shim.cpp").write_text(SHIM)
    subprocess.check_call(["g++", "-shared", "-fPIC", "-O2", "-std=c++11", "-I", str(d), str(d / "shim.cpp"),
                           "-o", str(d / "shim.so")])
    lib = ctypes.CDLL(str(d / "shim.so"))
    lib.send.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
    lib.rx.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
    lib.poll.argtypes = [ctypes.c_int, ctypes.c_uint32, ctypes.c_char_p]
    lib.next_delivery.argtypes = [ctypes.c_int] + [ctypes.POINTER(ctypes.c_int)] * 3
    return lib


def run(lib, n, ttl=20, jitter=40, k=2, density=8, commands=30, seed=1, shape="field", gap_ms=2000, tries=1, retry_ms=900):
    rng = random.Random(seed)
    lib.seed(seed * 7919 + n)
    lib.make(n, ttl, jitter, k)
    rng_range = 39.8                                   # metres at -88 dBm
    if shape == "line":
        pos = [(i * 25.0, 0.0) for i in range(n)]
    else:
        side = math.sqrt(n * math.pi * rng_range ** 2 / density)
        while True:                                    # a layout where every board can be reached at all
            pos = [(rng.uniform(0, side), rng.uniform(0, side)) for _ in range(n)]
            seen, todo = {0}, [0]
            while todo:
                a_ = todo.pop()
                for b_ in range(n):
                    if b_ not in seen and math.dist(pos[a_], pos[b_]) <= rng_range:
                        seen.add(b_)
                        todo.append(b_)
            if len(seen) == n:
                break
    hear = [[j for j in range(n) if j != i and math.dist(pos[i], pos[j]) <= rng_range] for i in range(n)]
    hears = [set(h) for h in hear]
    src = min(range(n), key=lambda i: pos[i][0] + pos[i][1])
    air = []                                           # (start, end, sender)
    buf = ctypes.create_string_buffer(256)
    tx_count = collisions = 0
    ok = 0
    rtts, hops_l = [], []
    txs_per_cmd = []
    t = 0
    for c in range(commands):
        dst = max(range(n), key=lambda j: math.dist(pos[src], pos[j])) if c % 2 == 0 else rng.randrange(n)
        if dst == src:
            dst = (src + 1) % n
        start = t
        lib.send(src, dst + 1, 0, b"PING", 4, t)
        sent_at, attempts = t, 1
        got_cmd = got_reply = False
        tx_before = tx_count
        end = t + gap_ms
        pending_rx = []                                # (arrive, receiver, bytes)
        while t < end:
            for i in range(n):
                while True:
                    k_ = lib.poll(i, t, buf)
                    if not k_:
                        break
                    data = buf.raw[:k_]
                    dur = (k_ * 8) / 1000.0 + 0.2      # ms at 1 Mbit/s
                    air.append((t, t + dur, i))
                    tx_count += 1
                    for j in hear[i]:
                        pending_rx.append((t + dur, j, data, t, i))
            nxt = []
            for (arr, j, data, st, snd) in pending_rx:
                if arr > t + 1e-9:
                    nxt.append((arr, j, data, st, snd))
                    continue
                # lost when another transmission this receiver can hear overlapped it
                if any(o != snd and (o in hears[j]) and a < arr and b > st for (a, b, o) in air[-64:]):
                    collisions += 1
                    continue
                lib.rx(j, data, len(data), int(t))
            pending_rx = nxt
            for i in range(n):
                ty, sr, hp = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
                while lib.next_delivery(i, ctypes.byref(ty), ctypes.byref(sr), ctypes.byref(hp)):
                    if ty.value == 0 and i == dst and not got_cmd:
                        got_cmd = True
                        hops_l.append(hp.value)
                        lib.send(i, sr.value, 1, b"PONG", 4, t)
                    elif ty.value == 1 and i == src and sr.value == dst + 1 and not got_reply:
                        got_reply = True
                        rtts.append(t - start)
            t += 1
            if not got_reply and attempts < tries and t - sent_at >= retry_ms:
                lib.send(src, dst + 1, 0, b"PING", 4, t)         # same command again, a new frame
                sent_at, attempts = t, attempts + 1
                got_cmd = False
        ok += got_reply
        txs_per_cmd.append(tx_count - tx_before)
        # let the previous command's last repeats die out before the next one
    return {"boards": n, "shape": shape, "ttl": ttl, "jitter_ms": jitter, "suppress_k": k, "density": density,
            "tries": tries, "answered": "%d/%d" % (ok, commands),
            "rtt_ms_mean": round(sum(rtts) / len(rtts), 1) if rtts else None,
            "rtt_ms_worst": round(max(rtts), 1) if rtts else None,
            "hops_to_target_mean": round(sum(hops_l) / len(hops_l), 1) if hops_l else None,
            "tx_per_command": round(sum(txs_per_cmd) / len(txs_per_cmd), 1),
            "frames_lost_to_collisions": collisions}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    lib = load()
    rows = []
    sizes = (5, 10, 30) if a.quick else (5, 10, 30, 100, 255)
    for n in sizes:
        rows.append(run(lib, n, commands=10 if n > 100 else 20))
        if n >= 30 and not a.quick:
            rows.append(run(lib, n, k=3, tries=3, commands=10 if n > 100 else 20, gap_ms=3500))
    rows.append(run(lib, 10, shape="line", commands=10))
    if not a.quick:
        for jit, k, tr in ((10, 2, 1), (100, 2, 1), (40, 1, 1), (40, 99, 1), (40, 3, 1), (40, 4, 1), (40, 3, 3), (40, 2, 3)):
            rows.append(run(lib, 100, jitter=jit, k=k, tries=tr, commands=10, gap_ms=3500))
        rows.append(run(lib, 100, ttl=8, commands=10))      # a TTL too short for the field
    for r in rows:
        print(r)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
