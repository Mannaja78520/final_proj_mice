"""A command with no bus id to an RS485 adapter fails at once, not after 2 s.

User 2026-09-27, COM21 (CH340 dongle, nong #67 behind it): "USB / RS485
(shared)" connected only after pressing Find and rescanning, and the page kept
hanging. The hub log was ten `/api/usb/cmd?port=COM21&id=0&c=INFO -> 502` in a
row with `id=67` answering in between. An adapter has no board of its own, so an
unaddressed command can never be answered - yet each one held the port lock for
the full 2 s wait, and every #67 command queued behind it.

The hub's probe already knows the cable is an adapter (no module, boards on the
bus). With that on record, an id=0 command must fail immediately, name the bus
id to use, and never touch the port lock. An addressed command must still go
through, and a cable that IS a board must still be asked.
"""
import threading
import time

import qc as F

AREA = "connection"
TITLE = "an unaddressed command to an RS485 adapter fails at once and names the bus id"


class Silent:
    """A port with nothing on it that answers unaddressed lines."""

    def __init__(self):
        self.sent = []

    def write(self, b):
        self.sent.append(b)
        return len(b)

    in_waiting = 0
    is_open = True

    def read(self, n=1):
        time.sleep(0.02)
        return b""

    def reset_input_buffer(self):
        pass


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    port = "COM_QC_ADAPTER"
    ser = Silent()
    lock = threading.Lock()
    main._usb_open[port] = {"ser": ser, "lock": lock, "last": time.time()}  # noqa: SLF001
    main._usb_ident[port] = {"port": port, "module": None, "error": "",      # noqa: SLF001
                             "rs485": [{"id": 67, "name": "nong", "type": "nong"}]}
    try:
        lock.acquire()          # a busy cable: a real attempt would wait here
        threading.Timer(1.0, lambda: lock.locked() and lock.release()).start()
        t0 = time.time()
        try:
            main.usb_cmd(port, "INFO", 0, wait=2.0)
            t.ok(False, "an unaddressed INFO to an adapter is refused", "it returned")
        except TimeoutError as e:
            t.contains(str(e), "bus id 67", "the refusal names the bus id to use")
        took = time.time() - t0
        time.sleep(1.1)         # the timer has let go of the lock by now
        t.ok(took < 0.3, "it is refused at once, without waiting on the cable",
             "took %.2f s - each one froze the port for 2 s (COM21, 2026-09-27)" % took)
        t.ok(not ser.sent, "and nothing was written to the adapter", repr(ser.sent))

        # an addressed command still goes down the cable
        try:
            main.usb_cmd(port, "INFO", 67, wait=0.2)
        except TimeoutError:
            pass
        t.ok(any(b"#67 INFO" in b for b in ser.sent),
             "a command WITH the bus id still reaches the bus", repr(ser.sent))

        # a cable that is a board of its own is still asked directly
        main._usb_ident[port] = {"port": port, "module": {"id": 5}, "error": "",  # noqa: SLF001
                                 "rs485": [{"id": 67}]}
        ser.sent.clear()
        try:
            main.usb_cmd(port, "INFO", 0, wait=0.2)
        except TimeoutError:
            pass
        t.ok(any(b.strip() == b"INFO" for b in ser.sent),
             "a board on the cable itself is still asked", repr(ser.sent))
    finally:
        if lock.locked():
            lock.release()
        main._usb_open.pop(port, None)                             # noqa: SLF001
        main._usb_ident.pop(port, None)                            # noqa: SLF001
