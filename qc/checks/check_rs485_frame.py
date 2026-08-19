"""An RS485 frame reaches the bus whole, or the board says it cannot promise that.

Every module on the bus listens to the same wire. A frame that goes out in two
pieces with another task's frame wedged between them is not a garbled message —
it is two messages that both look valid and are both wrong, and the modules act
on them.

RS485Bus::send writes the line and its terminator as two calls, which on the USB
port was a real bug (see core/Log.h). Here it is safe, and this pins down the
three things that MAKE it safe, because each one is a line someone could delete
without noticing:

  * Serial2 is written in exactly one function;
  * that function serialises on sendMtx_;
  * and the driver enable is held across the whole frame.

It also checks the narrow hole that was actually open: the lock is applied as
`if (sendMtx_)`, so a board that never created it would have skipped locking in
silence. Now it says so.
"""
import re

import qc as F

AREA = "protocol"
TITLE = "an RS485 frame cannot be split by another task"
SLOW = False

SRC = F.FIRMWARE / "src/core/RS485Bus.cpp"


def _code(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"//.*", "", s)
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def run(t):
    code = _code(SRC)

    # ---- one writer -----------------------------------------------------
    writes = [m.start() for m in re.finditer(r"Serial2\.(print|println|write)\s*\(", code)]
    t.ok(writes, "the bus is written somewhere at all")

    send = re.search(r"void RS485Bus::send\([^)]*\)\s*\{", code)
    if not t.ok(send, "RS485Bus::send exists"):
        return
    # the body of send(), by brace matching
    i, depth = send.end(), 1
    while i < len(code) and depth:
        depth += (code[i] == "{") - (code[i] == "}")
        i += 1
    body = code[send.end():i]

    outside = [p for p in writes if not (send.end() <= p < i)]
    t.ok(not outside,
         "every write to the bus goes through send()",
         "a write outside send() is not covered by the lock and can land in the "
         "middle of someone else's frame")

    # ---- serialised ------------------------------------------------------
    t.contains(body, "xSemaphoreTake",
               "send() takes the lock before it writes")
    t.contains(body, "xSemaphoreGive",
               "and gives it back")
    take = body.find("xSemaphoreTake")
    first_write = min((body.find(w) for w in ("Serial2.print", "Serial2.write")
                       if body.find(w) >= 0), default=-1)
    give = body.find("xSemaphoreGive")
    t.ok(0 <= take < first_write < give,
         "the lock is held ACROSS the writes, not around one of them",
         "take=%d first write=%d give=%d" % (take, first_write, give))

    # ---- the driver is held for the whole frame --------------------------
    t.eq(len(re.findall(r"digitalWrite\(hw\.pins\.rs485De", body)), 2,
         "the driver is raised and lowered exactly once per frame")
    t.contains(body, "Serial2.flush",
               "and the last byte is out before the driver is released",
               )

    # ---- a missing lock is not silent ------------------------------------
    # `if (sendMtx_)` means a board that never created the mutex would skip
    # locking without a word. It can only happen on a failed boot, but a bus
    # that quietly stopped being safe is the worst way to find that out.
    t.ok(re.search(r"warnedNoMtx_|LOGF\(sys", body),
         "a missing lock is reported, not silently ignored",
         "without the lock two tasks can interleave halves of two frames")

    # ---- and neither line reader can be grown without limit -------------
    # Found by the multi-model review, 2026-08-18: the RS485 reader has bounded
    # its buffer for a long time, and the USB reader beside it never did. A host
    # that sends bytes and never a terminator — wrong baud, half-open terminal,
    # noisy cable — grew a String until the heap was gone and the board died
    # silently. Both readers are asserted here so the pair cannot drift again.
    for name, path, var in (("RS485", SRC, "buf_"),
                            ("USB", F.FIRMWARE / "src/main.cpp", "serialBuf")):
        code = _code(path)
        m = re.search(r"%s\.length\(\)\s*>\s*(\d+)" % var, code)
        if t.ok(m, "the %s line reader bounds its buffer" % name,
                "an unterminated stream grows it until the heap is gone"):
            t.ok(int(m.group(1)) <= 512,
                 "and bounds it somewhere sane (%s chars)" % m.group(1))
