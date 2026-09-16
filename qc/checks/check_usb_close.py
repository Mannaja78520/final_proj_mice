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

    # ---- and the caller can TELL which happened ----------------------
    # This is what the flasher needed and did not have. It called usb_close,
    # slept 300ms and ran esptool into a handle that was still open; measured
    # at the bench 2026-08-20, the flash died at 21% with "the chip stopped
    # responding" and left the board in the bootloader. The same flash from a
    # command line with the hub stopped worked first try.
    lock2 = threading.Lock()
    entry2 = {"ser": FakeSerial(), "lock": lock2, "at": time.time()}
    with main._usb_mgr_lock:                                # noqa: SLF001
        main._usb_open[port] = entry2                       # noqa: SLF001
    lock2.acquire()
    try:
        shut = main.usb_close(port)
        t.eq(shut, [],
             "usb_close reports that it closed nothing")
        t.ok(not main.usb_free(port),
             "and usb_free agrees the cable is still held",
             "the flasher asks this before it runs esptool; if it lies, the "
             "board ends up half-written")
    finally:
        lock2.release()
    # And the POSITIVE case: an empty list means nothing closed, so a function
    # that always returns an empty list would have passed the assertion above.
    freed = main.usb_close(port)
    t.eq(freed, [port],
         "and it names the cable when it really did close one")
    t.ok(main.usb_free(port), "once it is free, usb_free says so")

    # The flasher must WAIT for that, not sleep and hope.
    src_f = (F.HUB / "main.py").read_text(encoding="utf-8")
    run = src_f[src_f.find("def _run(self, cmd, im)"):]
    run = run[:run.find("write_flash")]
    t.contains(run, "usb_free(port)",
               "the flasher checks the cable is really free")
    t.contains(run, "still in use by this hub",
               "and says so plainly rather than flashing anyway")

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
