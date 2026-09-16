"""One board that never stops talking must not hang the hub.

FOUND ON THE BENCH, 2026-08-21, and nothing else could have found it. A board
on COM26 was wedged: it sent 23,395 lines in three seconds and never paused.
Probing six ports never returned — five minutes, no answer, no error — and the
reason was four lines in `_usb_get`:

    quiet = time.time() + 1.2
    while time.time() < quiet:
        if ser.in_waiting:
            ser.read(ser.in_waiting)
            quiet = time.time() + 0.25   # still talking; wait again

The wait is right: opening a port can reset the board, and its boot noise
should land before the first command rather than in the middle of the first
reply. What was missing is that every arriving byte pushed the deadline
forward, so a cable that never goes quiet pushed it forever.

WHY IT MATTERS MORE THAN ONE CABLE. The scan walks every port in turn, so the
FIRST wedged board stops the module list for all of them. At a venue that is a
hub that looks dead, with every other board working perfectly.

WHY 3120 PASSING CHECKS SAID NOTHING. No fake had ever flooded. Every fake
board here answers a command and goes quiet, which is the one case the old
code handled. So the fake gained a cable that never stops (`FLOOD_PORT`), and
this is the check that reads it.

The assertion is a CLOCK, not a value: the only thing that distinguishes the
bug from the fix is whether the call comes back at all.
"""
import threading
import time

import fake_serial
import qc as F

AREA = "hub"
TITLE = "a board that never stops talking cannot hang the hub"
# Every probe of a flooding cable is seconds of real waiting, and there is no
# honest way to fake that away: the thing under test IS the clock.
SLOW = True

# Generous on purpose. The real wait is 1.2s of settling plus the 4s cap; this
# only has to be shorter than "forever", and a busy parallel gate is slow.
PATIENCE = 25.0


def _with_deadline(fn, seconds):
    """Run fn on a thread and say whether it finished.

    -> (done, took, err, value). The VALUE comes back with it so a caller
    never has to run the same probe twice just to look at the answer — each
    probe of a flooding cable costs several seconds of real waiting.

    A daemon thread, because the whole point is that the call may never
    return: joining with a timeout is the only way to fail this check rather
    than hang the suite along with the hub.
    """
    box = {}

    def go():
        t0 = time.time()
        try:
            box["value"] = fn()
        except Exception as e:                   # noqa: BLE001
            box["error"] = "%s: %s" % (type(e).__name__, e)
        box["took"] = time.time() - t0

    th = threading.Thread(target=go, daemon=True)
    th.start()
    th.join(seconds)
    return (not th.is_alive(), box.get("took"), box.get("error"),
            box.get("value"))


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    fake_serial.flood_listed[0] = True
    port = fake_serial.FLOOD_PORT

    # ---- the flood is real, or this check proves nothing ---------------
    # A fake that quietly stopped talking would make every assertion below
    # pass while testing the opposite of what it claims.
    import serial                                # the fake, installed by F
    s = serial.Serial()
    s.port, s.timeout = port, 0.15
    s.open()
    lines = 0
    end = time.time() + 0.5
    while time.time() < end:
        lines += s.read(4096).count(b"\n")
    s.close()
    if not t.ok(lines > 200,
                "the fake cable really floods (%d lines in half a second)" % lines,
                "with a quiet fake this check passes whatever the hub does"):
        return

    # ---- opening it comes back ----------------------------------------
    done, took, err, _ = _with_deadline(lambda: main._usb_get(port), PATIENCE)
    t.ok(done, "opening a flooding cable returns",
         "it never came back — the settle loop pushes its own deadline "
         "forward on every byte, so a cable that never goes quiet holds it "
         "forever (main.py _usb_get)")
    if done:
        t.ok((took or 0) < 12.0, "and quickly enough to be a scan step (%.1fs)"
             % (took or 0),
             "4s is the whole wait, not 4s after the settle: both clocks start "
             "together, so a quiet board costs 1.2s and a talking one 4")
    try:
        main.usb_close(port)
    except Exception:                            # noqa: BLE001
        pass

    # ---- and so does a full probe of it -------------------------------
    # The real failure was not one open: it was the scan, which walks every
    # port and stopped at this one.
    done2, took2, err2, _ = _with_deadline(lambda: main.probe_usb_port(port),
                                           PATIENCE)
    t.ok(done2, "probing it returns too", err2 or "it never came back")
    if done2:
        t.ok((took2 or 0) < PATIENCE,
             "in bounded time (%.1fs)" % (took2 or 0))
    try:
        main.usb_close(port)
    except Exception:                            # noqa: BLE001
        pass

    # ---- THE ONE THAT MATTERS: the other cables still work -------------
    # A hub that survives the noisy cable but stops listing the good ones has
    # not fixed anything a person would notice.
    done3, took3, err3, quiet = _with_deadline(
        lambda: main.probe_usb_port(fake_serial.PORT), PATIENCE)
    t.ok(done3, "and the QUIET board on another cable is still reachable",
         err3 or "it never came back")
    got = (quiet or {}).get("module")
    t.ok(bool(got and got.get("id")),
         "and still identifies itself",
         "one wedged board must not cost the whole module list: %r" % (got,))
