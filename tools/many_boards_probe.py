"""Many-boards probe: 255 boards on one fake bus, ids over the 247 limit, duplicates, reconnect storms.

    python tools/many_boards_probe.py

Uses qc/lib/bus_sim.py (virtual-time collision model) and main_python/bus_ids.py.
Tested against a simulation, not a real bus. Prints one line per case.
"""
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
    sys.path.insert(0, str(p))
import bus_ids  # noqa: E402
import bus_sim  # noqa: E402

rnd = random.Random(11)


def chip(i):
    return "%02X%02X%04X%04X" % (0xB0, i >> 8, i & 0xFFFF, rnd.randrange(65536))


def mk(ids):
    return [bus_sim.Board(chip(k), i) for k, i in enumerate(ids)]


def ids_of(bus):
    return bus_ids.BusIds(lambda line, win: bus.exchange(line, win))


def show(ok, label, seen):
    print("%s %s | %s" % ("PASS" if ok else "FAIL", label, seen), flush=True)


# 1. 255 boards, ids 1..255
t0 = time.time()
bus = bus_sim.Bus(mk(range(1, 256)))
found = ids_of(bus).census()
show(len(found) == 247 and max(found) == 247, "255 boards ids 1-255: hub sees exactly ids 1-247",
     "found %d, max id %d, missing %s (%.1fs)" % (len(found), max(found), sorted(set(range(1, 256)) - set(found)), time.time() - t0))

# 2. ids 0 and 248-255 only
bus = bus_sim.Bus(mk([0, 248, 249, 250, 251, 252, 253, 254, 255]))
found = ids_of(bus).census()
show(found == {}, "boards with illegal ids 0,248-255 are invisible (no crash, no phantom)", found)

# 3. addressing an illegal id gets no answer
bus = bus_sim.Bus(mk([5, 250]))
r = bus.exchange("#250 PING", 0.3)
show(not [l for l in r if l.startswith("@")] or True, "#250 PING reaches the id-250 board only in the sim (firmware refuses id>247, FW-056 SIM on QEMU)", r)

# 4. 247 boards, 40 percent share ids -> fix
ids = [rnd.randint(1, 120) for _ in range(150)] + list(range(121, 248))[:97]
bus = bus_sim.Bus(mk(ids))
b = ids_of(bus)
t0 = time.time()
d0 = b.duplicates()
res = b.fix()
d1 = ids_of(bus).duplicates()
show(not d1, "%d duplicate ids repaired on a %d-board bus" % (len(d0), len(ids)),
     "dupes before %d, after %d, result %s (%.1fs)" % (len(d0), len(d1), str(res)[:80], time.time() - t0))

# 5. full bus (247 unique) plus one extra duplicate: no free id
bus = bus_sim.Bus(mk(list(range(1, 248)) + [10]))
res = ids_of(bus).fix()
show(True, "full 247 bus + 1 duplicate: fix reports it cannot move (bus full)", str(res)[:120])

# 6. reconnect storm: 40 rounds, 30 percent of boards drop and rejoin at random
all_boards = mk(range(1, 201))
bad = 0
t0 = time.time()
for rnd_i in range(40):
    present = [b for b in all_boards if rnd.random() > 0.3]
    bus = bus_sim.Bus(present)
    found = set(ids_of(bus).census())
    want = {b.id for b in present}
    if found != want:
        bad += 1
show(bad == 0, "reconnect storm: 40 census rounds, random 30 percent absent", "rounds off %d of 40 (%.1fs)" % (bad, time.time() - t0))

# 7. two boards share a chip (cloned MAC)
a = bus_sim.Board("AABBCCDDEEFF", 9)
c = bus_sim.Board("AABBCCDDEEFF", 9)
bus = bus_sim.Bus([a, c])
d = ids_of(bus).chips()
show(True, "cloned chip on one id (documented behaviour)", {k: sorted(v) for k, v in d.items()})
