"""Every firmware log line is ONE write, through ONE helper.

The bug this guards was seen on the bench and is in main.cpp's own comment:
Serial.println(x) is print(x) followed by a SEPARATE print of the line ending,
so a WiFi event — which runs on another FreeRTOS task — can land between the
two and glue its log onto the end of a command reply:

    OK joining lift-test now (WIFI for progress)[wifi] disconnected, reason=8

The hub then reads that as the reply. It also tells a log line from a JSON
reply by the bracket tag alone (main.py:_LOG_LINE), so the tag is a machine
contract, not decoration — getting it wrong once made pin config answer
unsupported over USB while WiFi worked.

The BYTES the helper produces are asserted on the PC by the native tests in
firmware/test/test_logic (run by check_firmware_build). What this file guards
is that nothing goes around the helper.
"""
import re

import qc as F

AREA = "logging"
TITLE = "one logging helper, one write per line"
SLOW = False

SRC = F.FIRMWARE / "src"

# Nothing writes to the port directly any more. Both paths — a LOG through
# mlog::line and a REPLY through emitLine — go through mice::writeOnce, so the
# "one line, one write" rule lives in ONE file (core/PortWrite.h) instead of
# being restated in two places where half of it could be lost.
ALLOWED = {"PortWrite.h"}


def _code(path):
    """Source with comments removed — a comment may say Serial.println freely,
    and both Log.h and main.cpp explain the bug in prose."""
    s = path.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"//.*", "", s)
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def run(t):
    # ---- nothing logs behind the helper's back ------------------------
    strays = []
    for f in sorted(SRC.rglob("*.cpp")) + sorted(SRC.rglob("*.h")):
        code = _code(f)
        for m in re.finditer(r"Serial\.(print|println|printf)\s*\(", code):
            if f.name in ALLOWED:
                continue
            strays.append("%s: %s" % (f.name, m.group(0)))
    t.ok(not strays, "every log goes through the helper",
         "these write to the port directly, so another task can split them: %s"
         % strays[:6])

    # The REPLY path goes through the same one-write call as the logs.
    main_code = _code(SRC / "main.cpp")
    t.ok(not re.search(r"Serial\.(print|println|printf|write)\s*\(", main_code),
         "main.cpp does not write to the port itself",
         "the reply path shares mice::writeOnce; a second way to write is a "
         "second place the one-write rule can be lost")
    t.contains(main_code, "mice::writeOnce",
               "and the reply goes out through the shared write")

    # ---- the shared write really is one write --------------------------
    port_h = _code(F.FIRMWARE / "src/core/PortWrite.h")
    t.ok(len(re.findall(r"Serial\.write\s*\(", port_h)) == 1,
         "the shared write issues exactly one write per line",
         "two writes is the bug the whole arrangement exists to remove")
    t.ok(not re.search(r"Serial\.print(ln)?\s*\(", port_h),
         "and does not use println, which is two")

    log_cpp = _code(F.FIRMWARE / "src/core/Log.cpp")
    t.contains(log_cpp, "mice::writeOnce",
               "the log path goes out through the shared write too")

    # ---- the tag list lives in ONE place ------------------------------
    log_h = (F.FIRMWARE / "src/core/Log.h").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#define MICE_LOG_TAGS\(X\)((?:[^\n]|\\\n)*)", log_h)
    if not t.ok(m, "Log.h declares the tag list once"):
        return
    tags = re.findall(r"X\((\w+)\)", m.group(1))
    t.ok(len(tags) >= 7, "the list carries every subsystem", tags)
    # The enum and the name table are BOTH generated from that list, so a hand
    # written second copy of either is the drift this design removes.
    t.eq(len(re.findall(r"enum Tag", log_h)), 1, "one enum, generated from the list")
    t.ok(not re.search(r"NAMES\[\]\s*=\s*\{\s*\"", log_h),
         "and no hand-written name table beside it")

    # ---- every tag a call site uses actually exists --------------------
    used = set()
    for f in sorted(SRC.rglob("*.cpp")):
        used.update(re.findall(r"LOGF\(\s*(\w+)\s*,", _code(f)))
    unknown = sorted(used - set(tags))
    t.ok(not unknown, "every tag used is in the list",
         "unknown tags %s — the list is meant to be the one place" % unknown)
    t.ok(len(used) >= 5, "the helper is actually used across the firmware", sorted(used))

    # ---- and the format still matches what the HUB parses --------------
    # main.py:_LOG_LINE is how a log line is told from a JSON reply. If the
    # helper stopped emitting a bracket tag, the hub would read logs as replies.
    hub = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    pat = re.search(r"_LOG_LINE = re\.compile\(r\"([^\"]+)\"\)", hub)
    if t.ok(pat, "the hub's log-line rule was found"):
        rule = re.compile(pat.group(1))
        for tag in tags:
            t.ok(rule.match("[%s] something happened" % tag),
                 "the hub reads a [%s] line as a log, not as a reply" % tag)
        t.contains(log_h, '"[%s] "',
                   "the helper writes the bracket tag the hub looks for")
