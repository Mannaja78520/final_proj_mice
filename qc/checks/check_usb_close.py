"""A cable is never closed out from under a command that is using it.

`usb_close` takes each port's own lock before closing its handle. If it cannot
get that lock, something is still mid read/write on the port - and a `@peer`
command waits up to eight seconds for a reply, longer than the three this waits.
Closing anyway pulls the handle out from under it, which on Windows surfaces as
a ClearCommError in the reader, or as a hang.

So a port it could not lock is put BACK and left for the next sweep. A cable
held open a little longer is not a problem; a command dying mid-flight is - and
it dies in a way that looks like the board's fault.

The plan listed this as work to do and the code already did it, with the reason
written down. What was missing was anything to stop it being undone: the
dangerous version is SHORTER and looks tidier, which is exactly the kind of
change a cleanup makes. So this drives the real function with a lock somebody
else is holding, and checks the port survived.
"""
import threading
import time

import qc as F

AREA = "connection"
TITLE = "a busy cable is left open, not closed under the command using it"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    port = "COM_QC_CLOSE"
    lock = threading.Lock()
    closed = []

    class FakeSerial:
        def close(self):
            closed.append(port)

    entry = {"ser": FakeSerial(), "lock": lock, "at": time.time()}

    # ---- somebody is mid-command: the port stays ---------------------
    with main._usb_mgr_lock:                                # noqa: SLF001
        main._usb_open[port] = entry                        # noqa: SLF001
    lock.acquire()                                          # a command holds it
    try:
        t0 = time.time()
        main.usb_close(port)
        waited = time.time() - t0
    finally:
        lock.release()

    t.eq(closed, [],
         "a handle somebody is using is NOT closed")
    with main._usb_mgr_lock:                                # noqa: SLF001
        back = port in main._usb_open                       # noqa: SLF001
    t.ok(back,
         "and the port is put back, for the next sweep to try",
         "dropping it from the table leaks the handle: nothing will ever close "
         "it, and the next open of that cable fails as access denied")
    t.ok(waited >= 1.0,
         "it really waited for the lock rather than giving up at once (%.1fs)"
         % waited,
         "a command in flight usually finishes in well under a second; not "
         "waiting at all would close almost every busy port")
    t.under(waited, 8.0, "and did not wait for ever", "s")

    # ---- nobody is using it: the port closes -------------------------
    del closed[:]
    main.usb_close(port)
    t.eq(closed, [port], "a free handle IS closed")
    with main._usb_mgr_lock:                                # noqa: SLF001
        gone = port not in main._usb_open                   # noqa: SLF001
    t.ok(gone, "and is taken out of the table")

    # ---- and the reason stays written down ---------------------------
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    fn = src[src.find("def usb_close"):]
    fn = fn[:fn.find("\ndef ", 5)]
    t.contains(fn, "setdefault",
               "the code puts an unlockable port back")
    t.ok("timeout" in fn,
         "and waits with a timeout rather than for ever",
         "waiting without one turns a stuck reader into a hub that never "
         "shuts down")
