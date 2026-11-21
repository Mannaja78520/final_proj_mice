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
    return [Board("%02X%02X%08X" % (0xA0 + bus_no, bus_no, i * 7919 + rnd.randrange(1 << 20) * 4096 + i),
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

    out = ROOT / "docs" / "experiments" / "2026-11-21_bus_scale.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
