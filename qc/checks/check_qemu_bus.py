"""Two REAL firmwares on one emulated RS485 bus: a nong master and a gacha module.

The master takes `#<id> CMD` on its USB serial and puts it on the bus; the module
with that id answers `@<id> ...`. Each board is the compiled firmware on QEMU,
their UART2s joined by qemu_board.Rs485Bus - so the bus framing, the id filter,
the reply path AND the update-over-the-bus protocol are the genuine code, not
fake_serial's idea of them. Companion of check_qemu_firmware (single board).

  * a bus command reaches the right module and the reply comes back;
  * an id nobody has is silently ignored, and the module is unharmed;
  * a change made over the bus really happened on the other board (read on ITS
    own USB serial, not on what the master said);
  * the whole firmware-update-over-RS485 round trip: the master sends
    FWBEGIN/FWDATA/FWEND for the module, which reboots into the new app slot
    (sentinel printed on ITS console) while the master keeps running.

Not covered: bus contention with three talkers, termination, real cable timing.
Skips with a note when QEMU or the builds are missing.
"""
import base64
import hashlib
import time
from pathlib import Path

import qemu_board as Q

AREA = "firmware"
TITLE = "two real firmwares talk over an emulated RS485 bus (QEMU)"
SLOW = True

DATA = Path(__file__).resolve().parent.parent / "data"


def run(t):
    if not Q.find_qemu():
        t.ok(True, "SKIPPED: no QEMU for ESP32 here (python tools/qemu_esp32.py install)")
        return
    if not (Q.images("mice_nong") and Q.images("mice_gacha")):
        t.ok(True, "SKIPPED: needs mice_nong and mice_gacha builds (pio run -e ...)")
        return
    img = (DATA / "qemu_sentinel.bin").read_bytes()
    md5 = hashlib.md5(img).hexdigest()

    master = Q.QemuBoard("mice_nong", bus=True)
    slave = Q.QemuBoard("mice_gacha", nvs=DATA / "qemu_nvs_gacha_wifi_off.bin", bus=True)
    bus = None
    try:
        master.start()
        slave.start()
        bus = Q.Rs485Bus([master, slave])

        t.eq(master.ask("#9 PING", "@9 "), "@9 PONG 9 QEMU-GACHA gacha",
             "a bus PING reaches module 9 and its reply comes back")
        t.contains(master.ask("#9 GSTOCK 4", "@9 "), "stock=4", "a command with an argument works over the bus")
        t.contains(slave.cmd("G?"), '"stock":4', "and the change really happened on the OTHER board")
        n = len(bus.frames)
        master.ask("#77 PING", "@77 ", timeout=4)
        t.ok("@" not in bus.text(n), "an id nobody has gets no answer from anyone", bus.text(n))
        t.eq(master.ask("#9 PING", "@9 "), "@9 PONG 9 QEMU-GACHA gacha", "the bus still works after that")
        t.contains(master.ask("#9 BOGUS", "@9 "), "ERR", "an unknown command is refused by the module, over the bus")

        # ---- firmware over the bus ---------------------------------------
        t.contains(master.ask("#9 FWBEGIN %d %s" % (len(img), md5), "@9 "), "OK FWBEGIN",
                   "FWBEGIN over the bus")
        for i, o in enumerate(range(0, len(img), 150)):
            c = img[o:o + 150]
            line = "#9 FWDATA %d %d %s" % (i, len(c), base64.b64encode(c).decode())
            t.ok(len(line) <= 250, "a chunk line fits the 250-character bus limit", len(line))
            t.contains(master.ask(line, "@9 "), "OK %d" % i, "chunk %d acknowledged" % i)
        mark = len(slave.log)
        t.contains(master.ask("#9 FWEND", "@9 ", timeout=15), "OK FWEND", "FWEND accepted over the bus")
        t.ok(slave.wait_for("SENTINEL-SLOT-B", 20, since=mark),
             "the module reboots into the new app slot", slave.log[mark:][-300:])
        t.eq(master.cmd("PING"), "PONG 7 QEMU-NONG nong", "the master kept running throughout")
    finally:
        if bus:
            bus.close()
        master.stop()
        slave.stop()
