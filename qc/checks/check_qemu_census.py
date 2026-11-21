"""The bus census gives every module its own turn (real firmware, QEMU).

`#* PING` makes every module answer. Two modules whose ids are 24 apart used to
answer in the SAME 10 ms slot and garble each other on a real wire (model:
tools/bench/bus_census_model.py - 30 boards lose answers, 255 lose almost all).
Now a module waits id x 6 ms (core/BusSlot.h).

Three real firmwares on an emulated bus: a nong master (id 7) and two gachas
with ids 9 and 33 - the same slot under the old rule. Both must answer, in id
order, with the gap the rule promises. QEMU's UART is not paced like 115200
baud, so overlap itself cannot happen here; what this proves is that the
shipped firmware really uses the per-id delay. Tested against an emulator.
"""
import time
from pathlib import Path

import qemu_board as Q

AREA = "firmware"
TITLE = "bus census: modules 24 ids apart answer in their own turns (QEMU)"
SLOW = True

DATA = Path(__file__).resolve().parent.parent / "data"


def run(t):
    if not Q.find_qemu():
        t.ok(True, "SKIPPED: no QEMU for ESP32 here (python tools/qemu_esp32.py install)")
        return
    if not (Q.images("mice_nong") and Q.images("mice_gacha")):
        t.ok(True, "SKIPPED: needs mice_nong and mice_gacha builds (pio run -e ...)")
        return
    nvs = DATA / "qemu_nvs_gacha_wifi_off.bin"
    boards = [Q.QemuBoard("mice_nong", bus=True), Q.QemuBoard("mice_gacha", nvs=nvs, bus=True),
              Q.QemuBoard("mice_gacha", nvs=nvs, bus=True)]
    bus = None
    try:
        for b in boards:
            b.start()
        t.contains(boards[2].cmd("SET ID 33"), "OK", "the second gacha takes id 33")
        bus = Q.Rs485Bus(boards)
        master = boards[0]
        n = len(bus.timed)
        t0 = time.time()
        master.write("#* PING")
        time.sleep(4)
        seen = {}
        bufs = {1: "", 2: ""}                  # lines arrive in pieces: join per sender
        for who, data, at in bus.timed[n:]:
            if who in bufs:
                bufs[who] += data.decode("utf-8", "replace")
                for ident in (9, 33):
                    if "@%d PONG" % ident in bufs[who]:
                        seen.setdefault(ident, at - t0)
        t.ok(set(seen) == {9, 33}, "both modules answer the census", str(seen) + " frames=" + str([(w, d[:12]) for w, d, _ in bus.timed[n:]]))
        if set(seen) == {9, 33}:
            t.ok(seen[9] < seen[33], "in id order", str(seen))
            t.ok(seen[33] - seen[9] >= 0.1, "with a gap of about (33-9) x 6 ms between them", str(seen))
    finally:
        if bus:
            bus.close()
        for b in boards:
            b.stop()
