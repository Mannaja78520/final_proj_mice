"""The REAL firmware, booted on an emulated ESP32 (QEMU) — no board needed.

Every other check answers for the firmware with a Python fake of what we
believe it says. This one boots the compiled `firmware.bin` from a flash image
(bootloader + partition table + app + NVS) and talks to it over its UART, so
CommandRouter, the identity store and BusUpdate (FWBEGIN/FWDATA/FWEND, the way
RS485-only boards get new firmware) are the genuine code.

What it proves (user 2026-11-20: simulate the upload instead of waiting for the lab):

  * the image boots to `[boot] ready` and the seeded identity (id 7, nong) is read;
  * PING / INFO / unknown command / POSE answer like the docs say;
  * the update protocol refuses what it must on the real board: no md5, a chunk
    out of order, a chunk that arrives short, and a wrong md5 at FWEND — and the
    board keeps running the old firmware each time;
  * a good image is accepted and the board REBOOTS INTO THE OTHER APP SLOT: the
    sentinel image (qc/data/qemu_sentinel.c, 112 bytes) prints SENTINEL-SLOT-B
    from the ROM, which the old firmware cannot;
  * a name saved with SET NAME is still there after REBOOT (NVS on flash);
  * the real gachapon firmware (mice_gacha): stock, event and open/closed rules,
    a dispense with NO hall pulse ends as `jam` (the bench has no magnet to find),
    and stock + event survive a reboot.

NOT covered, because QEMU has no radio: WiFi (the seeded NVS sets wmode=off,
otherwise the PHY start crashes the emulator), OTA over HTTP, servos, hall
sensor, SD. Those still need the lab. Skipped with a plain note when QEMU or the
build is absent (python tools/qemu_esp32.py install; pio run -e mice_nong).
"""
import base64
import hashlib
from pathlib import Path

import qc as F
import qemu_board as Q

AREA = "firmware"
TITLE = "real firmware boots, updates itself and keeps settings (QEMU)"
SLOW = True

SENTINEL = Path(__file__).resolve().parent.parent / "data" / "qemu_sentinel.bin"
ENV = "mice_nong"


def _fw_chunks(img):
    for i, o in enumerate(range(0, len(img), 150)):
        c = img[o:o + 150]
        yield i, "FWDATA %d %d %s" % (i, len(c), base64.b64encode(c).decode())


GACHA_ENV = "mice_gacha"
GACHA_NVS = Path(__file__).resolve().parent.parent / "data" / "qemu_nvs_gacha_wifi_off.bin"


def _gacha(t):
    """The gachapon firmware with nothing wired: no magnet ever reaches the hall."""
    import time
    with Q.QemuBoard(GACHA_ENV, nvs=GACHA_NVS) as b:
        t.eq(b.cmd("PING"), "PONG 9 QEMU-GACHA gacha", "the gacha build boots with its stored identity")
        t.contains(b.cmd("G?"), '"state":"idle"', "it starts idle")
        t.contains(b.cmd("GSTOCK 1"), "stock=1", "GSTOCK sets the balls in the machine")
        t.contains(b.cmd("GEVENT NAME qemu-show"), "qemu-show", "GEVENT NAME")
        t.contains(b.cmd("GEVENT CLOSE"), "closed", "an event can be closed")
        t.contains(b.cmd("GDISPENSE who1"), "event closed", "a closed event refuses a prize")
        t.contains(b.cmd("GEVENT OPEN"), "open", "and opens again")
        t.contains(b.cmd("GCFG timeout 1000"), "timeout=1000", "GCFG timeout (ms) is accepted")
        t.contains(b.cmd("GDISPENSE who1"), "OK dispensing", "a prize is dispensed")
        time.sleep(3)                       # real time: timeout 1000 ms + settle, no hall pulse
        st = b.cmd("G?")
        t.ok('"motion_result":"jam"' in st, "no hall pulse ends the turn as a jam, motor off", st[:200])
        t.contains(st, '"state":"idle"', "and the machine is idle again, not stuck turning")
        t.contains(b.cmd("GDISPENSE who2"), "empty", "stock 1 was used up: the next one says empty")
        t.contains(b.cmd("GDISPENSE FORCE who2"), "OK dispensing", "FORCE is the admin's way past empty")
        b.cmd("STOP")
        t.contains(b.cmd("STOP"), "stopped", "STOP needs no login")
        t.ok(b.reboot(), "gacha REBOOT comes back", b.log[-300:])
        st = b.cmd("G?")
        t.ok('"event":"qemu-show"' in st, "the event name survives the reboot", st[:200])
        t.contains(st, '"given":', "and so do the counts")


def run(t):
    if not Q.find_qemu():
        t.ok(True, "SKIPPED: no QEMU for ESP32 here (python tools/qemu_esp32.py install)")
        return
    if not Q.images(ENV):
        t.ok(True, "SKIPPED: no %s build here (pio run -e %s)" % (ENV, ENV))
        return
    img = SENTINEL.read_bytes()
    md5 = hashlib.md5(img).hexdigest()

    with Q.QemuBoard(ENV) as b:
        # ---- boot + identity from the seeded NVS ---------------------
        t.ok("[boot] ready" in b.log, "the real firmware boots to ready", b.log[-300:])
        t.ok("[wifi] disabled" in b.log, "wmode=off from NVS keeps the missing radio out of the way")
        t.eq(b.cmd("PING"), "PONG 7 QEMU-NONG nong", "PING reports the id/name/type stored in flash")
        t.contains(b.cmd("INFO"), '"id":7', "INFO is the status JSON")
        t.contains(b.cmd("BOGUS"), "ERR", "an unknown command is refused")
        t.contains(b.cmd("POSE 90 90 90 90 90 90 90 90 90 90 T 500"), "OK pose", "POSE is accepted")

        # ---- the update protocol, refusals first ---------------------
        t.contains(b.cmd("FWBEGIN %d" % len(img)), "ERR", "FWBEGIN without an md5 is refused")
        t.contains(b.cmd("FWDATA 0 112 AAAA"), "ERR", "FWDATA before FWBEGIN is refused")
        t.contains(b.cmd("FWBEGIN %d %s" % (len(img), md5)), "OK FWBEGIN", "FWBEGIN with an md5 starts")
        lines = dict(_fw_chunks(img))
        t.contains(b.cmd("FWDATA 5 112 AAAA"), "out of order", "a chunk out of order is refused")
        t.contains(b.cmd("FWDATA 0 150 %s" % base64.b64encode(img[:100]).decode()),
                   "short", "a chunk shorter than its declared length is refused")
        t.contains(b.cmd(lines[0]), "OK 0", "the right chunk is taken after the refusals")
        t.contains(b.cmd("FWABORT"), "OK", "FWABORT is accepted")
        t.contains(b.cmd("FWSTAT"), "idle", "and leaves nothing half written")
        t.eq(b.cmd("PING"), "PONG 7 QEMU-NONG nong", "the old firmware is still running")

        # a wrong md5 is caught at FWEND, before any reboot
        t.contains(b.cmd("FWBEGIN %d %s" % (len(img), "0" * 32)), "OK FWBEGIN", "begin with a wrong md5")
        for _, ln in lines.items():
            b.cmd(ln)
        mark = len(b.log)
        t.contains(b.cmd("FWEND"), "ERR", "FWEND refuses an image that does not match its md5")
        t.ok("SENTINEL" not in b.log[mark:], "and the board does not reboot into it")
        t.eq(b.cmd("PING"), "PONG 7 QEMU-NONG nong", "still the old firmware after the refusal")

        # ---- settings survive a power cycle --------------------------
        t.contains(b.cmd("SET NAME bench-one"), "name=bench-one", "SET NAME answers")
        long_r = b.cmd("SET NAME " + "A" * 200)
        t.ok(long_r.count("A") <= 31, "a 200-letter name is cut short, not stored whole", long_r[:120])
        b.cmd("SET NAME bench-one")
        t.ok(b.reboot(), "REBOOT comes back to ready", b.log[-400:])
        t.eq(b.cmd("PING"), "PONG 7 bench-one nong", "the name saved to NVS survives the reboot")

        # ---- a good image switches the boot slot ---------------------
        t.contains(b.cmd("FWBEGIN %d %s" % (len(img), md5)), "OK FWBEGIN", "begin the good image")
        for _, ln in lines.items():
            b.cmd(ln)
        mark = len(b.log)
        t.contains(b.cmd("FWEND"), "OK FWEND", "FWEND accepts the good image")
        t.ok(b.wait_for("SENTINEL-SLOT-B", 20, since=mark),
             "the board reboots INTO the new app slot (sentinel printed)", b.log[mark:][-300:])

    if Q.images(GACHA_ENV):
        _gacha(t)
    else:
        t.ok(True, "SKIPPED gacha: no %s build here (pio run -e %s)" % (GACHA_ENV, GACHA_ENV))
