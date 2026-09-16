"""A bus reached through a plain USB-RS485 dongle, with no board on the cable.

There are two ways to put the hub on an RS485 bus:

  * through a MODULE — the board on the cable hears the bus and re-emits every
    frame on USB (main.cpp's `rs485.onBusLine` → `emitLine`), which wraps it in
    the usual `\\n<reply>\\n`;
  * through a plain USB-RS485 DONGLE — a CH340 and a MAX485, no firmware at
    all. It is just wire, so the frame arrives exactly as it was on the pair:
    `@1 PONG 1 lift lift`, with nothing in front of it.

`_usb_cmd_once` used to require the blank line before ANY reply. That marker
earns its place — it is what tells a real reply from the orphaned tail of a log
line, and it fixed a bug where hammering commands during a WiFi reconnect
answered `PING` with `son=8`, the tail of `[wifi] disconnected, reason=8`, 49
times in 60. But a dongle cannot produce it, and the fallback that covers older
firmware was deliberately limited to replies with no bus id.

So the hub read `@1 PONG 1 lift lift` off the wire and threw it away, then said
`no reply from COM23 (bus id 1)`. Measured 2026-08-20, and it is the worst shape
a bug can take: the message points at the bus, and the bus was working.

The fix is that a bus reply carries its OWN marker. `@<id> ` is the RS485 frame
format itself — a log tail cannot begin with it — so it identifies a reply at
least as well as the blank line does. That is asserted here along with the thing
it must not break: a reply with no bus id still needs the marker, or the log-tail
bug comes straight back.
"""
import threading
import time

import qc as F

AREA = "connection"
TITLE = "an RS485 dongle's replies are read, not discarded"


class Dongle:
    """A USB-RS485 dongle: whatever is on the pair, raw, with no board on the
    cable to wrap it in the firmware's blank-line marker."""

    def __init__(self, says):
        self.says = says
        self.out = b""
        self.i = 0

    def write(self, b):
        # a dumb dongle answers only because a MODULE on the bus did
        self.out += self.says
        return len(b)

    @property
    def in_waiting(self):
        return max(0, len(self.out) - self.i)

    def read(self, n=1):
        got = self.out[self.i:self.i + n]
        self.i += len(got)
        if not got:
            time.sleep(0.02)
        return got

    def reset_input_buffer(self):
        pass

    is_open = True


def _ask(t, main, says, bus_id, cmd="PING"):
    """What the hub makes of that wire traffic — or why it gave up.

    A timeout comes back as text rather than an exception on purpose. When the
    fix is removed this check should FAIL with the reason on screen, not crash:
    proved with tools/sabotage.py, where the first version did exactly that and
    reported nothing more useful than "crashed".
    """
    port = "COM_QC_DONGLE"
    main._usb_open[port] = {"ser": Dongle(says),               # noqa: SLF001
                            "lock": threading.Lock(), "last": time.time()}
    try:
        return main._usb_cmd_once(port, cmd, bus_id, wait=1.2)  # noqa: SLF001
    except TimeoutError as e:
        return "GAVE UP: %s" % e
    finally:
        main._usb_open.pop(port, None)                          # noqa: SLF001


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415

    # ---- the case that was broken -----------------------------------
    got = _ask(t, main, b"@1 PONG 1 lift lift\n", 1)
    t.eq(got, "PONG 1 lift lift",
         "a raw bus frame with no blank line in front of it is the reply")

    # It really is the DONGLE shape that matters, so the bridging-board shape
    # must keep working too — that is the common case and the one with the
    # marker.
    got = _ask(t, main, b"\n@1 PONG 1 lift lift\n", 1)
    t.eq(got, "PONG 1 lift lift",
         "and a bridging board's wrapped frame still works")

    # ---- and the log-tail protection is NOT lost --------------------
    # This is the assertion that keeps the fix honest. The blank-line marker
    # exists because an orphaned log tail was being returned as a reply — 49
    # times in 60 while the radio was reconnecting. A reply with no bus id must
    # still require the marker, or that comes straight back.
    # An unmarked line is still only a LAST RESORT — it exists so a board on
    # older firmware keeps working. What must never happen is an orphaned tail
    # being preferred to a real reply that arrived after it.
    got = _ask(t, main, b"son=8\n\nPONG 1 lift lift\n", 0)
    t.eq(got, "PONG 1 lift lift",
         "a marked reply still beats an orphaned log tail that arrived first")
    got = _ask(t, main, b"son=8\n@1 PONG 1 lift lift\n", 1)
    t.eq(got, "PONG 1 lift lift",
         "and on the bus the PREFIX beats the tail, without needing the marker")

    # A frame from another module must never answer for ours.
    got = _ask(t, main, b"@7 PONG 7 other nong\n", 1)
    t.ok(got.startswith("GAVE UP"),
         "a frame from a DIFFERENT bus id is ignored",
         "the whole point of the prefix is that it names who answered; "
         "matching any frame would hand back another module's status as this "
         "one's, which is worse than no answer. Got: %s" % got[:70])

    # ---- the reason is written down where it will be read ------------
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    fn = src[src.find("def _usb_cmd_once"):]
    fn = fn[:fn.find("\n# ---------------- unified device access")]
    t.contains(fn, "dongle",
               "the code says why a bus reply needs no blank line")
    t.ok("startswith(want)" in fn,
         "and the prefix is what it matches on")
