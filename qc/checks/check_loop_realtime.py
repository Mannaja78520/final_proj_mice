"""Nothing slow runs where it can hold up a servo frame.

Measured on nong 67, 2026-09-21, with PERF? (see check_perf). Each line held
here removed one measured stall; the RS485 one is check_bus_nonblocking.

  * FILES held the router lock for 20 ms while it listed the SD card, and
    loop() waits on that lock before every servo frame. SD has its own lock
    and /api/files never took the router's, so FILES, FREAD and PERF? now run
    without it.
  * the web server's task (AsyncTCP, priority 3, any core) preempted loop()
    (priority 1) on core 1: a frame 37 ms late while a page loaded. Boards
    that move build with CONFIG_ASYNC_TCP_RUNNING_CORE=0, so it shares core
    0 with the radio instead.
  * INFO read the radio (SSID, RSSI, IP) while holding the router lock; those
    driver calls need no lock, so they are read before it.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "slow work stays off the servo loop's path"


def run(t):
    fw = F.FIRMWARE
    router = (fw / "src" / "core" / "CommandRouter.cpp").read_text(encoding="utf-8")
    ini = (fw / "platformio.ini").read_text(encoding="utf-8")

    # ---- lock-free reads --------------------------------------------------
    m = re.search(r"static bool needsNoLock[^{]*\{(.*?)\n\}", router, re.S)
    if t.ok(m, "the router has a list of commands that need no lock"):
        names = set(re.findall(r'c == "([^"]+)"', m.group(1)))
        t.ok(names == {"FILES", "FREAD", "PERF?"},
             "and it is only the read-only SD commands and PERF?",
             "found %s - anything touching module, identity or sequence "
             "state must keep the lock" % sorted(names))
    h = router[router.index("String CommandRouter::handle("):]
    h = h[:h.index("\n}")]
    t.ok(h.find("needsNoLock(") >= 0 and h.find("needsNoLock(") < h.find("lock();"),
         "handle() checks that list before taking the lock",
         "after the lock it saves nothing: FILES held frames for 20 ms")

    # ---- the radio is read outside the lock ------------------------------
    b = router[router.index("void CommandRouter::buildStatus("):]
    b = b[:b.index("\n}")]
    first_lock = b.find("lock();")
    for call in ("WiFi.SSID()", "WiFi.RSSI()", "WiFi.status()"):
        i = b.find(call)
        t.ok(0 <= i < first_lock, "buildStatus reads %s before the lock" % call)

    # ---- a USB reply does not hold the loop (A26-86) ----------------------
    # One INFO over USB stalled loop() 108 ms on a real board: Serial had no
    # TX buffer. The buffer must be set BEFORE Serial.begin() or it is ignored.
    main = (fw / "src" / "main.cpp").read_text(encoding="utf-8")
    t.ok(re.search(r"Serial\.setTxBufferSize\(\s*(\d{4,})\s*\);\s*Serial\.begin\(", main),
         "USB serial has a TX buffer of at least 1 KB, set before begin()",
         "without it every reply over the cable blocks the servo loop")

    # ---- the web server stays off loop()'s core ---------------------------
    t.ok(re.search(r"realtime_flags\s*=\s*-D CONFIG_ASYNC_TCP_RUNNING_CORE=0", ini),
         "the realtime flags pin the web server to core 0")
    for env in ("mice_nong", "mice_lift", "mice_module_firmware"):
        sect = ini[ini.index("[env:%s]" % env):]
        sect = sect[:sect.find("\n[", 1)]
        t.ok("${mice_base.realtime_flags}" in sect,
             "%s builds with the realtime flags" % env,
             "without them a page load preempts the servo loop")
