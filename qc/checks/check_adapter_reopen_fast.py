"""Re-opening a bare RS485 adapter does not wait for a boot that cannot happen.

Measured on the real nong 2026-09-28 (CH340 dongle COM21, nong #67 behind it):
the hub releases a port after 10 s with no traffic, and every re-open waited the
1.2 s boot settle. So the first command after a pause - a pose from Studio, a
Run - left 1.2 s late: PING took 1231 ms after 20 s idle and 11 ms otherwise.

The settle exists because opening a port can reset a board wired to that cable
(FTDI, 2026-08-20). A bare adapter has no board on the cable, only modules on
the bus behind it, which the open cannot touch. With the probe's record saying
exactly that, the open must be quick; a cable that IS a board must still wait.
The settle lives in _usb_get, main_python/hub_usb.py.
"""
import sys
import time

import qc as F

AREA = "connection"
TITLE = "re-opening a bare RS485 adapter skips the boot settle; a board still gets it"


class Quiet:
    """An adapter port: opens at once, nothing arrives."""

    def __init__(self, *a, **k):
        self.port = None
        self.is_open = False
        self.in_waiting = 0

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def read(self, n=1):
        return b""


def opened_in(main, port):
    main._usb_open.pop(port, None)                      # noqa: SLF001
    t0 = time.time()
    main._usb_get(port)                                 # noqa: SLF001
    took = time.time() - t0
    main._usb_open.pop(port, None)                      # noqa: SLF001
    return took


def run(t):
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test
    import serial  # noqa: PLC0415

    port = "COM_QC_REOPEN"
    real = serial.Serial
    serial.Serial = Quiet
    try:
        main._usb_ident[port] = {"port": port, "module": None, "error": "",   # noqa: SLF001
                                 "rs485": [{"id": 67, "name": "nong", "type": "nong"}]}
        took = opened_in(main, port)
        t.ok(took < 0.3, "a bare adapter re-opens without the 1.2 s settle",
             "took %.2f s - the first move after a pause left that late (COM21, 2026-09-28)" % took)

        main._usb_ident[port] = {"port": port, "module": {"id": 5}, "error": "",  # noqa: SLF001
                                 "rs485": []}
        took = opened_in(main, port)
        t.ok(took >= 1.1, "a cable that is a board still waits out its boot",
             "took %.2f s - an open can reset that board" % took)

        main._usb_ident.pop(port, None)                 # noqa: SLF001
        took = opened_in(main, port)
        t.ok(took >= 1.1, "and so does a cable nobody has probed yet",
             "took %.2f s" % took)
    finally:
        serial.Serial = real
        main._usb_ident.pop(port, None)                 # noqa: SLF001
