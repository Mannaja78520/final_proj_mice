"""Boards are found, told apart and re-addressed at 247 per bus and 988 in all.

BEFORE (measured here, virtual time, real collision model - qc/lib/bus_sim.py):
the 24-slot `#* PING` finds almost nothing once a bus is full, because ~10
boards share each 10 ms slot and destroy each other's frames. Default ids are
one MAC byte, so two boards of a box share an id (birthday problem) and cannot
be addressed separately.

AFTER: ranged PING (one board per slot), CHIPS (permanent chip per id, two
lanes so duplicates show), `#~chip SET ID` (fix by chip). Several buses make
>247 boards: ids repeat across buses and companies, so a board is named by its
chip (hub_modules.board_key), never by id alone.
"""
import json
import random
import sys
from pathlib import Path

import qc as F

AREA = "connection"
TITLE = "247 boards per bus, duplicate ids repaired, 988 boards over four buses"

ROOT = Path(F.__file__).resolve().parents[2]


def _boards(bus_no, n, rnd, old=0, default_ids=False):
    from bus_sim import Board
    ids = ([(int(rnd.random() * 247) % 247) + 1 for _ in range(n)] if default_ids
           else list(range(1, n + 1)))
    return [Board("%02X%02X%04X%04X" % (0xA0 + bus_no, bus_no, i, rnd.randrange(65536)),
                  ids[i], old=(i < old)) for i in range(n)]


def run(t):
    for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import bus_ids
    import bus_sim

    rnd = random.Random(2026)
    rec = {}

    # 1. the old plain broadcast, at growing bus sizes (the problem, in numbers)
    old_plain = {}
    for n in (8, 24, 64, 128, 247):
        b = bus_sim.Bus(_boards(0, n, rnd, old=n, default_ids=False))
        heard = [l for l in b.exchange("#* PING", 0.3) if l.startswith("@")]
        old_plain[n] = len(heard)
    rec["old_plain_ping_found"] = old_plain
    t.ok(old_plain[247] < 247 * 0.5, "plain PING loses most of a full bus (found %d of 247)" % old_plain[247],
         json.dumps(old_plain))

    # 1b. firmware after #154 (one 6 ms slot per id): fine while ids are unique,
    # blind exactly where two boards share an id - which default ids make likely
    new_plain = {}
    for n in (30, 100, 247):
        brd = _boards(0, n, rnd, default_ids=True)
        b = bus_sim.Bus(brd)
        heard = {int(l.split()[0][1:]) for l in b.exchange("#* PING", 2.0) if l.startswith("@")}
        new_plain[n] = {"boards": n, "distinct_ids": len({x.id for x in brd}), "heard_ids": len(heard)}
    rec["new_plain_ping_default_ids"] = new_plain
    t.ok(new_plain[247]["heard_ids"] < new_plain[247]["distinct_ids"],
         "slot-per-id PING still misses boards that share an id (%d of %d ids heard, 247 boards)" %
         (new_plain[247]["heard_ids"], new_plain[247]["distinct_ids"]),
         "this is the gap CHIPS and chip addressing close")
    full = bus_sim.Bus(_boards(0, 247, rnd))
    got = [l for l in full.exchange("#* PING", 2.0) if l.startswith("@")]
    t.ok(len(got) == 247, "slot-per-id PING finds 247 boards when ids are unique (%d)" % len(got))

    # 2. ranged census on a full bus: every board, no collision
    b = bus_sim.Bus(_boards(0, 247, rnd))
    found = bus_ids.BusIds(b.exchange).census()
    rec["ranged_census"] = {"found": len(found), "collisions": b.collisions, "virtual_s": round(b.clock, 2)}
    t.ok(len(found) == 247 and b.collisions == 0, "ranged PING finds all 247, 0 collisions (%.1f s)" % b.clock)

    # 3. duplicates: default ids drawn like the firmware (one random byte)
    for n in (30, 100, 247):
        brd = _boards(0, n, rnd, default_ids=True)
        by = {}
        for x in brd:
            by.setdefault(x.id, []).append(x.chip)
        truth = {i: sorted(c) for i, c in by.items() if len(c) > 1}
        b = bus_sim.Bus(brd)
        ids = bus_ids.BusIds(b.exchange)
        got = ids.duplicates()
        t.ok(set(got) == set(truth), "%d boards, default ids: %d duplicate ids found, all of them (truth %d)" %
             (n, len(got), len(truth)), "missed=%s" % (set(truth) ^ set(got)))
        res = ids.fix()
        again = bus_ids.BusIds(b.exchange).duplicates()
        uniq = len({x.id for x in brd}) == n
        t.ok(not again and not res["failed"] and uniq,
             "%d boards: after repair every id is unique (%d boards moved)" % (n, len(res["moved"])),
             "failed=%s" % res["failed"])
        rec["dups_%d" % n] = {"duplicate_ids": len(truth), "moved": len(res["moved"]),
                              "virtual_s": round(b.clock, 1)}

    # 3a. a full bus plus one duplicate cannot be repaired: say so ONCE per chip (the
    # old fix() listed the same chip once per retry round, 12 times)
    full = bus_sim.Bus(_boards(0, 247, rnd) + [bus_sim.Board("AB00000000CD", 10)])
    res = bus_ids.BusIds(full.exchange).fix()
    t.ok(res["failed"] == ["AB00000000CD"], "full bus + 1 duplicate: the stuck chip is named once", str(res["failed"])[:120])

    # 3b. mass power-on: everything plugged in at once, default ids. Time until
    # the hub knows every board uniquely = census + chips + repair (virtual s).
    boot = {}
    for n in (8, 24, 64, 128, 247):
        brd = _boards(0, n, rnd, default_ids=True)
        b = bus_sim.Bus(brd)
        ids = bus_ids.BusIds(b.exchange)
        ids.census()
        ids.fix()
        ok = len({x.id for x in brd}) == n
        boot[n] = {"seconds": round(b.clock, 1), "all_unique": ok}
        t.ok(ok, "mass power-on, %d boards: all unique after %.1f s of bus time" % (n, b.clock))
    rec["mass_poweron"] = boot

    # 3c. normal running: a command to one board costs the same with 247 on the
    # bus as with 1 (addressed lines have no slot), and a command that arrives
    # during a scan waits at most one range window.
    for n in (1, 247):
        b = bus_sim.Bus(_boards(0, n, rnd))
        r = b.exchange("#%d PING" % n, 0.05)
        t.ok(len(r) == 1 and r[0].startswith("@%d" % n), "addressed command answered cleanly with %d on the bus" % n)
    rec["command_latency_ms"] = {"addressed_reply_airtime": round(len("@247 PONG 247 MOD-000000 blank") * bus_sim.BYTE_S * 1000, 1),
                                 "worst_wait_behind_scan_range_s": round(24 * 0.010 + 0.15, 2),
                                 "scan_duty_at_one_per_minute_pct": round(4.3 / 60 * 100, 1)}

    # 4. a board that has the OLD firmware keeps working (ignored, never broken)
    brd = _boards(0, 20, rnd)
    for x in brd[::4]:                 # old boards spread through the bus
        x.old = True
    b = bus_sim.Bus(brd)
    f = bus_ids.BusIds(b.exchange).census()
    t.ok(all(x.id in f for x in brd),
         "20 boards, 5 on old firmware (every 4th): every one still found (%d of 20)" % len(f))

    # 5. 4 buses x 247 = 988 boards, 4 companies, ids repeat across buses
    total, seen_chips, per_bus = 0, set(), []
    for bus_no in range(4):
        brd = _boards(bus_no, 247, rnd)
        b = bus_sim.Bus(brd)
        total += len(bus_ids.BusIds(b.exchange).census())
        seen_chips |= {x.chip for x in brd}
        per_bus.append(round(b.clock, 1))
    t.ok(total == 988 and len(seen_chips) == 988,
         "988 boards over 4 buses found, 988 distinct chips (ids repeat, chips never)")
    rec["four_buses"] = {"found": total, "distinct_chips": len(seen_chips), "virtual_s_each": per_bus}

    # 6. the hub names a board by chip, so two companies with the same id differ
    import hub_modules
    a = hub_modules.board_key({"id": 5, "chip": "A0B1C2D3E4F5", "group": "acme"})
    c = hub_modules.board_key({"id": 5, "chip": "A0B1C2D3E4F6", "group": "globex"})
    t.ok(a != c, "same id 5 in two companies stays two boards")

    # 7. firmware side exists (the C++ is compiled by check_firmware_build)
    h = (F.FIRMWARE / "src" / "core" / "BusAddr.h").read_text(encoding="utf-8")
    cpp = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    t.contains(h, "constexpr int SLOTS = 24", "firmware slot count matches bus_ids.SLOTS")
    t.ok(bus_ids.SLOTS == 24 and bus_ids.LANES == 2, "python and firmware agree on 24 slots, 2 lanes")
    t.contains(cpp, 'addr.startsWith("~")', "firmware accepts chip addressing")
    t.contains(cpp, "BusAddr::chipsSlot", "firmware answers CHIPS")

    # 8. the C++ hash and range maths equal the Python model, bit for bit
    # (compiled with the host g++; skipped, said so, where there is none)
    import shutil
    import subprocess
    import tempfile
    gxx = shutil.which("g++")
    if not gxx:
        t.ok(True, "no host g++: C++ parity not compared here (firmware build still compiles it)")
    else:
        vec = [("A0B1C2D3E4F5", 1), ("A0B1C2D3E4F5", 2), ("a0b1c2d3e4f6", 7), ("000000000000", 0)]
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "p.cpp"
            body = "".join('printf("%%u\\n", BusAddr::hash("%s", %d));\n' % v for v in vec)
            body += ('int lo=0,hi=0; long s=0; bool ok=BusAddr::parseRange("5 28 3",lo,hi,&s);'
                     'printf("%d %d %d %d %ld\\n", ok, lo, hi, BusAddr::pingSlot(30,lo,hi), s);'
                     'printf("%d\\n", BusAddr::chipsSlot(10,5,28,"A0B1C2D3E4F5",1));')
            src.write_text('#include "core/BusAddr.h"\n#include <cstdio>\nint main(){\n' + body + '}\n')
            exe = Path(d) / "p"
            r = subprocess.run([gxx, "-std=c++17", "-I", str(F.FIRMWARE / "src"), str(src), "-o", str(exe)],
                               capture_output=True, text=True)
            t.ok(r.returncode == 0, "BusAddr.h compiles on the host", r.stderr[-300:])
            if r.returncode == 0:
                lines = subprocess.run([str(exe)], capture_output=True, text=True).stdout.split("\n")
                want = [str(bus_sim.fnv(c, s)) for c, s in vec]
                t.ok(lines[:4] == want, "C++ hash == Python hash on 4 vectors", "%s vs %s" % (lines[:4], want))
                t.ok(lines[4] == "1 5 28 -1 3", "parseRange and pingSlot (id outside range = -1)", lines[4])
                slot = (10 - 5) % 24 + 24 * (bus_sim.fnv("A0B1C2D3E4F5", 1) % 2)
                t.ok(lines[5] == str(slot), "chipsSlot equals the sim's slot", "%s vs %s" % (lines[5], slot))

    out = ROOT / "docs" / "experiments" / "2026-11-21_bus_scale.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
