"""A module on the RS485 bus is found however high its id is.

THE BUG THIS EXISTS FOR, measured on the bench 2026-08-19 and not before:

A board answers a broadcast after a delay proportional to its own id, so that
several boards do not talk over each other. The hub then listened for a fixed
0.8 seconds. With the old stagger of `id x 20 ms` that made every board above
id 40 invisible - and default ids run to 247, so most boards were. A nong on
id 67 answered after 1344 ms and simply did not exist as far as the hub was
concerned: no error, no warning, an empty bus.

Nothing on a PC could have shown it. The fake answered a broadcast instantly
and always as id 1, so the census looked perfect against 2122 passing checks.
The fake now staggers like a real bus, which is the part of this fix that
matters most: the same mistake cannot be made again without something failing.

Both halves are checked here:

  * the HUB waits for the bus to go quiet rather than for a clock, so a late
    board is still found;
  * the FIRMWARE bounds its stagger, so no board is late by more than a
    quarter of a second whatever its id.
"""
import json
import re
import time

import fake_serial
import qc as F

AREA = "connection"
TITLE = "a board on the bus is found however high its id is"


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT

    # A cable someone is DRIVING is not censused - the hub answers from its
    # cached identity instead, rather than taking the port away mid-show. That
    # is right, and it means this check has to start from a port nobody is
    # holding. Run alone it passes either way; run after a check that drove the
    # module it silently measured the cache, which is a check that proves
    # nothing.
    main._usb_touch.clear()               # noqa: SLF001 - test setup
    main._usb_ident.pop(port, None)       # noqa: SLF001
    main._usbscan_cache["at"] = 0         # noqa: SLF001

    slow_id = int(re.search(r"@(\d+)", fake_serial.BUS_SLOW).group(1))
    t.ok(fake_serial.BUS_SLOW_DELAY > 0.8,
         "the fake bus has a board slower than the old fixed window",
         "if the fake answers instantly this check proves nothing, which is "
         "exactly how the bug survived")

    t0 = time.time()
    r = json.loads(F.get(base + "/api/scanusb?port=" + port)[1])
    took = time.time() - t0
    usb = (r.get("usb") or [{}])[0]

    ids = [b.get("id") for b in (usb.get("rs485") or [])]
    t.ok(slow_id in ids,
         "the slow board on the bus is found (id %d)" % slow_id,
         "the census saw %r. A board that answers late does not answer never - "
         "and the hub reports no error either way, so this looks like an empty "
         "bus" % (ids,))

    names = [b.get("name") for b in (usb.get("rs485") or [])]
    t.ok(any(n for n in names),
         "and it is named, not just counted", "%r" % (names,))

    # ...without paying the worst case every time. The read stops when the bus
    # goes quiet, so a fast bus costs a fraction of a second.
    t.ok(took < 4.0, "and a scan does not wait out the worst case (%.1fs)" % took,
         "the census stops once the bus is quiet; if this creeps up, the quiet "
         "rule has been lost and every port probe pays for it")

    # ---- the two halves, in the source ------------------------------
    main_py = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = main_py.find("ser.write(b" + chr(34) + "#* PING")
    # Wide enough to reach the call past its comment: the comment IS the
    # explanation of the bug, so it will only get longer.
    window = main_py[i:i + 2000]
    t.contains(window, "quiet=",
               "the hub waits for the bus to go quiet, not for a fixed time")
    m = re.search(r"_read_lines\(ser,\s*([\d.]+)", window)
    t.ok(m and float(m.group(1)) >= 5.0,
         "with a cap that covers a board running the old firmware",
         "the old stagger was id x 20 ms and ids reach 247, so anything under "
         "5 s still hides the boards with the highest ids")

    bus = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    j = bus.find("pendingAt_ =")
    line = bus[j:j + 120]
    t.contains(line, "%",
               "and a board's own delay is bounded, not proportional to its id")
    m2 = re.search(r"%\s*(\d+)\)\s*\*\s*(\d+)", line)
    if t.ok(m2, "the stagger is a slot times a gap", line.strip()):
        slots, gap = int(m2.group(1)), int(m2.group(2))
        worst = slots * gap
        t.ok(worst <= 300,
             "so every board has answered within %d ms" % worst,
             "%d slots x %d ms. The hub probes every port on every scan, and "
             "pays this each time" % (slots, gap))
        # A PONG is about 30 characters: 2.6 ms at 115200. A gap under that
        # means two boards can overlap in the middle of a line.
        t.ok(gap >= 4,
             "and two boards in neighbouring slots cannot overlap",
             "%d ms between slots, against 2.6 ms for a PONG at 115200" % gap)
