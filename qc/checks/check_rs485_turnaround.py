"""The RS485 driver stays enabled until the last bit has actually left.

Measured at the bench on 2026-08-20: every reply arriving over RS485 was
corrupted with runs of NUL bytes replacing runs of characters - even a twenty
byte PONG came back as `PO` then four NULs then `ined cam` - while two boards on
plain USB cables, on the same PC and through the same hub process, answered
byte-identically every time.

The five-model panel was given the measurements and found the cause in
`RS485Bus::send`: `Serial2.flush()` empties the transmit FIFO, but the byte
already being clocked out lives in the shift register BEYOND it. The code then
waited 20us and dropped the driver enable - and at 115200 one byte takes 86.8us,
so the wait was less than a quarter of the character still going out. Cutting a
character in half is a framing error at the receiver, and a framing error
arrives as 0x00: a NUL where a letter should be.

The timing is derived from `RS485_BAUD` rather than typed, so a faster bus
cannot leave it behind. That is what this checks - not the number, which would
just be the same magic constant written twice.
"""
import re

import qc as F

AREA = "connection"
TITLE = "the RS485 driver is held long enough for the last character"


def run(t):
    src = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")

    # ---- the timings are derived, not typed -------------------------
    t.contains(src, "RS485_BYTE_US",
               "a byte's duration is worked out from the baud rate")
    m = re.search(r"RS485_BYTE_US = \(10UL \* 1000000UL\) / RS485_BAUD", src)
    t.ok(m, "one byte is ten bits divided by the baud rate",
         "8N1 is 8 data bits plus a start and a stop bit; anything else "
         "under-counts and the hold is short again")

    hold = re.search(r"RS485_HOLD_US = RS485_BYTE_US \* (\d+)", src)
    if t.ok(hold, "the hold is a multiple of a byte"):
        t.ok(int(hold.group(1)) >= 2,
             "and it is at least two of them (%s)" % hold.group(1),
             "one byte is the minimum that can be in the shift register; two "
             "leaves room for the driver's own turn-off time")

    # ---- and the send path really uses them -------------------------
    send = src[src.find("void RS485Bus::send("):]
    send = send[:send.find("\n}") + 2]
    t.contains(send, "Serial2.flush()",
               "the FIFO is drained before the line is released")
    t.contains(send, "delayMicroseconds(RS485_HOLD_US)",
               "and then the shift register is waited for")
    t.ok(not re.search(r"delayMicroseconds\(\s*\d+\s*\)", send),
         "no raw microsecond number is left in the send path",
         "a typed number is what went wrong: 20us, when a byte is 86.8us. "
         "found %s" % re.findall(r"delayMicroseconds\([^)]*\)", send))

    # The order is the whole point: enable, send, drain, WAIT, disable.
    i_flush = send.find("Serial2.flush()")
    i_hold = send.find("delayMicroseconds(RS485_HOLD_US)")
    i_low = send.find("rs485De, LOW")
    t.ok(0 < i_flush < i_hold < i_low,
         "the wait sits between the flush and dropping the driver",
         "flush at %d, hold at %d, release at %d - releasing before the wait "
         "is the bug with extra steps" % (i_flush, i_hold, i_low))

    # ---- the setup side too -----------------------------------------
    # Enabling the driver too late clips the START of a frame in the same way.
    t.contains(send, "delayMicroseconds(RS485_SETUP_US)",
               "the driver is given time to turn on before the first byte")
    setup = re.search(r"RS485_SETUP_US = RS485_BYTE_US / (\d+)", src)
    t.ok(setup, "and that time is derived from the baud rate as well")
