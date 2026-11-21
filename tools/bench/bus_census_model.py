"""How many modules answer a `#* PING` census, old slot rule vs new, 5..255 boards.

    python tools/bench/bus_census_model.py [--out file.json]

A bus model, not a board: every reply is a line of 8N1 characters on one wire
at 115200 baud; two lines that overlap in time are both lost (no collision
detection on RS485). Delays are the firmware's rules, the old one copied here
on purpose so the comparison stays reproducible:
    old: (id % 24) * 10 ms          new: id * 6 ms  (firmware/src/core/BusSlot.h)
Ids are drawn two ways: contiguous 1..N, and random from 1..255 (what a rig
looks like after people set ids by hand). 200 random draws per size.
Real wires, termination and the boards' own jitter are NOT modelled: lab list.
"""
import argparse
import json
import random

BYTE_MS = 10 * 1000 / 115200
RULES = {"old": lambda i: (i % 24) * 10, "new": lambda i: i * 6}


def answered(ids, rule, chars=40, jitter=1.0, rng=random):
    """Ids whose reply was not overlapped by any other reply."""
    spans = sorted((rule(i) + rng.uniform(0, jitter), i) for i in ids)
    dur = chars * BYTE_MS
    ok, last_end = set(), -1e9
    for k, (start, i) in enumerate(spans):
        end = start + dur
        nxt = spans[k + 1][0] if k + 1 < len(spans) else 1e9
        if start >= last_end and end <= nxt:
            ok.add(i)
        last_end = max(last_end, end)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    rng = random.Random(2026)
    rows = []
    for n in (5, 10, 24, 30, 60, 100, 150, 255):
        for kind in ("contiguous", "random"):
            r = {"boards": n, "ids": kind}
            for name, rule in RULES.items():
                lost = 0
                runs = 1 if kind == "contiguous" else 200
                for _ in range(runs):
                    ids = list(range(1, n + 1)) if kind == "contiguous" else rng.sample(range(1, 256), n)
                    lost += n - len(answered(ids, rule, rng=rng))
                r[name + "_lost_avg"] = round(lost / runs, 2)
            r["new_last_answer_ms"] = RULES["new"](n if kind == "contiguous" else 255)
            rows.append(r)
            print(r)
    if a.out:
        json.dump(rows, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
