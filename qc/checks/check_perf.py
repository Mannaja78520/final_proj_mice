"""PERF? - the board says whether it is keeping up.

Asked 2026-09-21: *make sure the c++ module it have low looptime and can be
realtime and not lag or restart every task and everytime*. That cannot be
answered from the outside: a hub sees a slow reply, never WHY. So the board
times itself and reports on request:

  * **loop time** (avg/max between two passes of loop()) and the **work** one
    pass did - a long pass is what makes a servo frame late;
  * **frame_max_ms** - the widest gap between two servo frames while moving.
    50 Hz means 20 ms; anything well above it is a visible stutter;
  * **heap, heap_min, heap_big, stack_free** - the numbers that fall before a
    crash does;
  * **boots and reset** - resets since power-on, kept in RTC memory. A board
    that restarts mid-task and comes straight back looks fine to everyone
    unless something counts. `reset=CRASH|WATCHDOG|BROWNOUT` says which kind.

The figures only mean something if they are taken in the right places, and
every one of those places is a single line that is easy to lose in a refactor:
passBegin at the top of loop(), passEnd before its yield, frame() inside the
50 Hz tick, and the window reset in report(). This check holds each of them.
"""
import json
import re

import qc as F

AREA = "firmware"
TITLE = "PERF? reports loop time, frame gaps, memory and resets"


def run(t):
    fw = F.FIRMWARE
    main = (fw / "src" / "main.cpp").read_text(encoding="utf-8")
    router = (fw / "src" / "core" / "CommandRouter.cpp").read_text(encoding="utf-8")
    perf = (fw / "src" / "core" / "Perf.cpp").read_text(encoding="utf-8")
    nong = (fw / "src" / "modules" / "nong" / "NongModule.cpp").read_text(encoding="utf-8")
    doc = (fw / "COMMANDS.md").read_text(encoding="utf-8")
    cmds = json.loads(re.sub(r"^\s*//.*$", "", (fw / "config" / "commands.json")
                             .read_text(encoding="utf-8"), flags=re.M))["commands"]

    t.ok(any(c["name"] == "PERF?" and c.get("query") for c in cmds),
         "PERF? is a query in the command registry")
    t.ok("| `PERF?` |" in doc, "PERF? is documented in COMMANDS.md")
    t.ok('cmd == "PERF?") return perf::report()' in router,
         "the router answers PERF? from perf::report")

    loop = main[main.index("void loop()"):]
    body = loop[loop.index("{") + 1:].lstrip()
    t.ok(body.startswith("perf::passBegin();"),
         "passBegin is the FIRST thing loop() does",
         "anything before it is time the loop spent that nobody measured")
    t.ok(re.search(r"perf::passEnd\(\);\s*delay\(1\);", loop) is not None,
         "passEnd sits right before the yield",
         "after delay(1) it would count the scheduler's time as the loop's work")
    t.ok("perf::begin();" in main[main.index("void setup()"):main.index("void loop()")],
         "setup() counts the boot")

    tick = nong[nong.index("void NongModule::loop()"):]
    tick = tick[:tick.index("writeServos();")]
    t.ok("perf::frame(now - lastTick_)" in tick and
         tick.index("perf::frame") < tick.index("lastTick_ = now"),
         "the nong reports each servo frame's gap, before the clock moves on",
         "after lastTick_ = now the gap is always 0 and a stutter is invisible")

    rep = perf[perf.index("String perf::report()"):]
    t.ok("perf::held(" in router[router.index("void CommandRouter::unlock()"):]
         .split("\n}")[0],
         "the router reports how long its lock was held, and by what",
         "without it a stall shows up in loop time with no name on it")
    for field in ("loop_max_us", "work_max_us", "frame_max_ms", "lock_max_us",
                  "lock_by", "heap_min",
                  "heap_big", "stack_free", "boots", "reset"):
        t.ok(field + "=" in rep, "PERF? reports %s" % field)
    t.ok(re.search(r"passes\s*=\s*frames\s*=\s*0", rep) is not None and
         "periodMax = workMax = frameMax = heldMax = partMax = 0" in rep,
         "each PERF? starts a new window",
         "without it one slow moment at boot is the max forever")
    t.ok("ESP_RST_POWERON" in perf[perf.index("void perf::begin()"):],
         "a power-on clears the reset count",
         "otherwise boots only ever grows and stops meaning restarted")
