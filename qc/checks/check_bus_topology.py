"""Chained buses: 247 boards, one of them a bridge to another 247, and so on.

The user's case (2026-11-21): bus A has 247 boards; one is wired by RX/TX to a
board that runs bus B with 247 more; one of THOSE bridges to bus C. Also the odd
rigs a clever customer builds: a ring (bus B's bridge is wired back to A), a board
on two buses, two buses with the same ids, ids clashing inside a bridged bus, a
cloned chip, and a chain longer than the firmware allows.

Simulated (qc/lib/bus_sim.py, real collisions per wire), not wired on a bench.
"""
import json
import random
import sys
from pathlib import Path

import qc as F

AREA = "connection"
TITLE = "bridged buses: 741 boards over three levels, loops and clones handled"

ROOT = Path(F.__file__).resolve().parents[2]


def run(t):
    for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import bus_net
    from bus_sim import Board, Bus, Gateway

    rnd = random.Random(11)
    rec = {}
    n_chip = [0]

    def chip(tag):
        n_chip[0] += 1
        return "%02X%02X%08X" % (tag, n_chip[0] >> 8 & 255, (n_chip[0] << 12) ^ rnd.randrange(1 << 12))

    def plain(tag, n, skip=()):
        return [Board(chip(tag), i) for i in range(1, n + 1) if i not in skip]

    # --- 1. the asked-for rig: A(247) -> gateway id 100 -> B(247) -> gateway id 200 -> C(247)
    c = Bus(plain(0xC0, 247))
    b = Bus(plain(0xB0, 247, skip=(200,)) + [Gateway(chip(0xB1), 200, down=c)])
    a = Bus(plain(0xA0, 247, skip=(100,)) + [Gateway(chip(0xA1), 100, down=b)])
    topo = bus_net.Topology(a.exchange).discover()
    total = len(topo.boards)
    t.ok(total == 741, "3 buses x 247: all 741 boards found, each with its own chip (%d)" % total)
    t.ok(topo.buses == 3 and not topo.loops, "3 buses walked, no loop reported (buses=%d loops=%d)" %
         (topo.buses, len(topo.loops)))
    deep = [x for x in topo.boards.values() if x["bus"] == ">100>200"]
    t.ok(len(deep) == 247 and all(x["path"].startswith(">100>200>") for x in deep),
         "the 247 boards two bridges away are addressed by path, e.g. %s" % deep[0]["path"])
    # same ids on three buses: identity is the chip, not the id
    ids_seen = [x["id"] for x in topo.boards.values()]
    t.ok(len(set(ids_seen)) == 247 and len({k for k in topo.boards}) == 741,
         "ids repeat on every bus (%d distinct ids) yet 741 distinct chips" % len(set(ids_seen)))
    rec["three_levels"] = {"boards": total, "buses": topo.buses, "scan_virtual_s": round(a.clock, 1),
                           "clock_bus_B_s": round(b.clock, 1), "clock_bus_C_s": round(c.clock, 1),
                           "collisions": [a.collisions, b.collisions, c.collisions]}

    # latency by depth: reply delay seen on the first wire, with every relay in it
    lat = {}
    for label, line in (("depth0_board_on_A", "#7 PING"), ("depth1_via_1_bridge", "#>100>7 PING"),
                        ("depth2_via_2_bridges", "#>100>200>7 PING")):
        fr = [d for d, tx in a.frames(line) if tx.startswith("@")]
        lat[label + "_ms"] = round(fr[0] * 1000, 2) if fr else None
    rec["reply_delay_by_depth"] = lat
    t.ok(all(v is not None for v in lat.values()) and lat["depth2_via_2_bridges_ms"] < 50,
         "a command two bridges away answers within 50 ms of relay time: %s" % lat)

    # a command to a board two bridges away reaches only that board
    tgt = deep[5]
    heard = a.exchange("%s SET NAME far" % bus_net.Topology.address(tgt["path"] + "")
                       .replace(tgt["path"], ">100>200>%d" % tgt["id"]), 0.5)
    t.ok(any(ln.startswith("@>100>200>%d " % tgt["id"]) for ln in heard),
         "a command by path is answered under the same path", str(heard[:2]))

    # --- 2. a ring: bus B has a gateway wired back to bus A; A's gateway to B
    a2 = Bus(plain(0xA2, 20, skip=(5,)))
    b2 = Bus(plain(0xB2, 20, skip=(7,)))
    ga = Gateway(chip(0xAA), 5, down=b2)
    gb = Gateway(chip(0xBB), 7, down=a2)
    a2.boards.append(ga)
    b2.boards.append(gb)
    topo = bus_net.Topology(a2.exchange).discover()
    t.ok(len(topo.boards) == 40, "ring A->B->A ends, every board once (%d of 40)" % len(topo.boards))
    t.ok(topo.loops and all(c in topo.boards for c, _, _ in topo.loops),
         "the loop is reported, not followed (%d extra routes)" % len(topo.loops))
    rec["ring"] = {"boards": len(topo.boards), "extra_routes": len(topo.loops)}

    # --- 3. a board on two buses (dual-homed): one chip, two routes
    shared = Board(chip(0xDD), 50)
    a3 = Bus(plain(0xA3, 10) + [shared])
    b3 = Bus(plain(0xB3, 10, skip=()) + [Board(shared.chip, 60)])
    a3.boards.append(Gateway(chip(0xAB), 90, down=b3))
    topo = bus_net.Topology(a3.exchange).discover()
    t.ok(len(topo.routes[shared.chip]) == 2, "a board on two buses is one board with two routes: %s" %
         topo.routes[shared.chip])

    # --- 4. ids clash INSIDE a bridged bus: repaired by chip on that bus
    c4 = Bus([Board(chip(0xC4), 3) for _ in range(4)] + plain(0xC5, 10, skip=(3,)))
    a4 = Bus(plain(0xA4, 5, skip=(2,)) + [Gateway(chip(0xAC), 2, down=c4)])
    topo = bus_net.Topology(a4.exchange).discover()
    t.ok(len(topo.duplicate_ids.get(">2", {}).get(3, [])) == 4,
         "four boards sharing id 3 behind a bridge are all seen", str(topo.duplicate_ids)[:80])

    # --- 5. a cloned chip on two separate buses: flagged, not merged silently
    clone = chip(0xEE)
    a5 = Bus([Board(clone, 1)] + plain(0xA5, 3, skip=(1,)) + [Gateway(chip(0xAD), 9, down=Bus([Board(clone, 4)]))])
    topo = bus_net.Topology(a5.exchange).discover()
    t.ok(any(c == clone for c, _, _ in topo.loops), "the same chip in two places is reported for a person to decide")

    # --- 6. too deep: more bridges than the firmware forwards are refused, not followed
    leaf = Bus(plain(0xF0, 3))
    bus = leaf
    for lvl in range(6):
        bus = Bus(plain(0xF1 + lvl, 3, skip=(2,)) + [Gateway(chip(0xF8 + lvl), 2, down=bus)])
    topo = bus_net.Topology(bus.exchange).discover()
    t.ok(topo.refused and topo.buses <= bus_net.MAX_DEPTH + 0,
         "a chain longer than %d hops stops (buses walked %d, refused %s)" %
         (bus_net.MAX_DEPTH, topo.buses, topo.refused))

    # --- 7. broadcasts do not cross a bridge (no storm): a plain PING on A is not answered from B
    a6 = Bus(plain(0xA6, 4, skip=(2,)) + [Gateway(chip(0xAE), 2, down=Bus(plain(0xB6, 30)))])
    heard = [ln for ln in a6.exchange("#* PING", 2.0) if ln.startswith("@")]
    t.ok(len(heard) == 4, "a broadcast on A stays on A (%d answers, B's 30 boards stayed quiet)" % len(heard))

    # --- 8. old firmware beside a gateway: a path line is not understood as a plain id
    old = Board(chip(0x99), 12, old=True)
    t.ok(old.hear("#>12>7 SET NAME x") == [], "an old board ignores a path-addressed line")

    # --- 9. the firmware side exists and its constants agree
    h = (F.FIRMWARE / "src" / "core" / "BusPath.h").read_text(encoding="utf-8")
    cpp = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    t.contains(h, "MAX_DEPTH = 4", "firmware and hub agree on 4 hops")
    t.contains(cpp, "downstream_(", "the gateway puts the rest of the path on its second link")
    t.contains(cpp, "onDownstreamLine", "and relays what it hears back upstream under its own path")

    out = ROOT / "docs" / "experiments" / "2026-11-21_bus_topology.json"
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
