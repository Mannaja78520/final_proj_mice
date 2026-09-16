"""A board that reboots mid-command is not a corrupted reply.

Measured at the bench on 2026-08-20, and it cost most of an afternoon chasing
the wrong thing. Replies from one board came back with runs of NUL bytes
replacing characters - `PO` then four NULs then `ined cam` - while other boards
on other cables answered perfectly. It looked exactly like an RS485 fault, and a
five-model panel found a real defect in the RS485 turnaround that fitted the
evidence beautifully.

It was not that. The same board on the same port, read DIRECTLY, answered ten
times out of ten with nothing lost. The A/B, same minute, same cable:

    direct from the port   10/10 clean,   0 NUL bytes,  ~500 bytes
    through the hub         0/10 clean, 679 NUL bytes,  ~300 bytes

Opening the port RESET the board - on that FTDI adapter it happens however
carefully DTR and RTS are cleared first - and the ESP32's first-stage ROM log is
printed at a different rate from the firmware's 115200, so it arrives as NULs
and fragments. `usb_cmd` handed that back as the answer.

Two things fix it and both are held here: a fresh handle waits for the line to
go quiet before anything is asked, and boot output is recognised rather than
parsed as a reply. A board that restarted is then REPORTED as having restarted,
because "no reply" sends somebody to check wiring that was never wrong - which
is exactly what happened here.
"""
import re
import threading
import time

import qc as F

AREA = "connection"
TITLE = "boot output is never mistaken for a reply"

BOOT = (b"\nets Jul 29 2019 12:21:46\n"
        b"rst:0x1 (POWERON_RESET),boot:0x13\n"
        b"configsip: 0, SPIWP:0xee\n")


class Rebooting:
    """A port that says what an ESP32 says when opening it caused a reset."""

    def __init__(self, then=b""):
        self.out = BOOT + then
        self.i = 0

    def write(self, b):
        return len(b)

    @property
    def in_waiting(self):
        return max(0, len(self.out) - self.i)

    def read(self, n=1):
        got = self.out[self.i:self.i + n]
        self.i += len(got)
        if not got:
            time.sleep(0.02)          # nothing more is coming; do not spin
        return got

    def reset_input_buffer(self):
        pass

    # _usb_get reuses a cached handle only while it says it is open.
    is_open = True


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test
    src = (F.HUB / "main.py").read_text(encoding="utf-8")

    # ---- the real pattern knows boot output from an answer ----------
    t.ok(hasattr(main, "_BOOT_NOISE"),
         "the hub knows what a rebooting board sounds like")
    boot = main._BOOT_NOISE                                  # noqa: SLF001
    for line in ("ets Jul 29 2019 12:21:46",
                 "rst:0xc (SW_CPU_RESET),boot:0x17 (SPI_FAST_FLASH_BOOT)",
                 "configsip: 0, SPIWP:0xee",
                 "Brownout detector was triggered"):
        t.ok(boot.search(line), "a real boot line is caught: %s" % line[:36])
    for line in ('{"id":89,"chip":"3076F5E61544","type":"cam"}',
                 "PONG 67 nong nong",
                 "@67 PONG 67 nong nong",
                 "OK servo travel 1 = 270 deg"):
        t.ok(not boot.search(line),
             "a real reply is NOT caught: %s" % line[:36],
             "matching a reply would throw good answers away, which is worse "
             "than the bug being fixed")

    # ---- DRIVEN: a port that reboots, with and without an answer ----
    # Asserting that the words "rebooted[0] = True" appear in the source passed
    # with the whole condition replaced by `if False` - caught by
    # tools/sabotage.py. So the reader is handed a port that behaves the way
    # the real one did.
    port = "COM_QC_BOOT"
    for tail, what in ((b"\nPONG 7 test nong\n", "and then answers"),
                       (b"", "and says nothing else")):
        main._usb_open[port] = {"ser": Rebooting(tail),       # noqa: SLF001
                                "lock": threading.Lock(), "last": time.time()}
        try:
            got = main._usb_cmd_once(port, "PING", 0, wait=1.5)   # noqa: SLF001
            t.eq(got, "PONG 7 test nong",
                 "a board that reboots %s gives the REPLY, never boot output"
                 % what)
        except TimeoutError as e:
            t.contains(str(e), "restarted",
                       "a board that reboots %s is reported as restarted" % what)
        finally:
            main._usb_open.pop(port, None)                     # noqa: SLF001

    # ---- and the two failures stay different ------------------------
    fn = src[src.find("def _usb_cmd_once"):]
    fn = fn[:fn.find("\n# ---------------- unified device access")]
    t.contains(fn, "restarted while answering",
               "a reboot is named as a reboot")
    t.ok("no reply from" in fn,
         "while a silent board still says that instead",
         "they are different problems with different fixes: one is wiring, "
         "the other is asking again")
    t.contains(fn, "not rebooted[0]",
               "and the old-firmware fallback cannot smuggle boot text back")

    # ---- the GARBLED form, which is the one it actually takes --------
    # _BOOT_NOISE matches clean ASCII, and the whole point is that the ROM log
    # comes out at ANOTHER BAUD - so in real life it arrives as NULs and
    # fragments and matches none of those patterns. It then became the
    # `fallback` and was returned as the reply: the exact bug, surviving in its
    # commonest form. Found by a model review 2026-08-20. Measured on the bench
    # the same day: 679 NUL bytes across ten reads of one board.
    main._usb_open[port] = {                                   # noqa: SLF001
        "ser": Rebooting(b"\x00\x00PO\x00\x00\x00\x00ined cam\x00\n"),
        "lock": threading.Lock(), "last": time.time()}
    try:
        got = main._usb_cmd_once(port, "PING", 0, wait=1.2)     # noqa: SLF001
        t.ok(False, "a NUL-garbled boot line is never returned as a reply",
             "got %r" % got)
    except TimeoutError:
        t.ok(True, "a NUL-garbled boot line is never returned as a reply",
             "no reply the firmware sends contains a NUL - every one is a "
             "single line written in one call - so refusing them cannot cost "
             "a real answer, and accepting them hands back a reset as data")
    finally:
        main._usb_open.pop(port, None)                          # noqa: SLF001

    # ---- a board that reboots ONCE is not a board that never stops ---
    # Measured at the bench 2026-08-20, on the 30-pin ESP32 with a MAX485
    # attached: 5 brownouts and 4 boots in 8 seconds, resetting about every
    # 1.6 s, always immediately after the SD check - which is where
    # portal.begin() starts the radio (firmware/src/main.cpp:105). It never
    # reached the command loop, so RS485 could not see it and neither could
    # USB. The hub said "no reply from COM10", and that sent most of an
    # afternoon into checking bus wiring that was never wrong. One reset means
    # ask again; a loop means look at the power, and nothing else will do.
    loop = Rebooting(b"")
    loop.out = (BOOT + b"\nBrownout detector was triggered\n") * 4
    main._usb_open[port] = {"ser": loop,                       # noqa: SLF001
                            "lock": threading.Lock(), "last": time.time()}
    try:
        main._usb_cmd_once(port, "PING", 0, wait=1.5)          # noqa: SLF001
        t.ok(False, "a boot-looping board times out rather than answering")
    except TimeoutError as e:
        said = str(e)
        t.contains(said, "restarting over and over",
                   "a board that never stops rebooting is named as such")
        t.ok("POWER" in said,
             "and the message says where to look",
             "the operator's next move is a power rail, not a meter on the "
             "bus - saying 'no reply' points at exactly the wrong thing")
        t.contains(said, "Brownout",
                   "quoting the board's own word for it when it gave one")
        t.ok("Ask again" not in said,
             "and it does NOT suggest simply asking again",
             "asking a board in a boot loop again is the one thing that "
             "cannot work, and it is what the single-reset message advises")
    finally:
        main._usb_open.pop(port, None)                         # noqa: SLF001

    # A loop with NO brownout line still has to be recognised as a loop, and
    # that is what makes the boot COUNT do work rather than decorate. Proved
    # with tools/sabotage.py: with only the brownout case above, deleting the
    # counter entirely left this check green. Plenty of reset loops never print
    # the word - a watchdog, a panic, a bad pin config - and every one of them
    # is still "look at the board", never "ask again".
    quiet_loop = Rebooting(b"")
    quiet_loop.out = BOOT * 4
    main._usb_open[port] = {"ser": quiet_loop,                 # noqa: SLF001
                            "lock": threading.Lock(), "last": time.time()}
    try:
        main._usb_cmd_once(port, "PING", 0, wait=1.5)          # noqa: SLF001
        t.ok(False, "a silent boot loop times out rather than answering")
    except TimeoutError as e:
        t.contains(str(e), "restarting over and over",
                   "a reset loop is caught by COUNTING boots, not by the word "
                   "brownout")
        t.ok(str(e).count("rst:0x") == 0 and "4 times" in str(e),
             "and it says how many times it saw the board come up",
             "a number is what turns 'it is not answering' into 'it reset four "
             "times while I waited', which is the whole diagnosis")
    finally:
        main._usb_open.pop(port, None)                         # noqa: SLF001

    # ---- a fresh handle waits for the line to go quiet ---------------
    op = src[src.find("        ser.open()"):]
    op = op[:op.find("except", 1)]
    t.contains(op, "in_waiting",
               "a freshly opened port is drained before anything is asked")
    m = re.search(r"quiet = time[.]time[(][)] [+] ([0-9.]+)", op)
    if t.ok(m, "the drain waits for a real moment"):
        t.ok(float(m.group(1)) >= 0.5,
             "long enough for a boot log to arrive (%ss)" % m.group(1),
             "an ESP32 takes the better part of a second to print its ROM log; "
             "a shorter wait leaves the tail of it in the first reply")
    t.contains(op, "+ 0.25",
               "and it keeps waiting while the board is still talking")
