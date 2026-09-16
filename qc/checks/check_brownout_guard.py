"""A board whose supply cannot start it must not be an inert brick.

Measured at the bench 2026-08-20, on a 30-pin ESP32. It booted, got as far as
the SD check, and reset — four brownouts and four boots in eight seconds, and it
never once reached the command loop:

    [sd] no card found, SD features disabled
    Brownout detector was triggered
    ets Jul 29 2019 12:21:46
    rst:0xc (SW_CPU_RESET)

The reset lands immediately after `sdstore.begin()` in main.cpp, and the next
thing is `portal.begin()` — the radio starting, which is the current spike a
marginal supply cannot deliver. It still did it with the MAX485 unplugged, so
the transceiver was never the load.

The cost was not the board. It was that the board could not be TALKED to. USB
serial and RS485 need no radio at all, and both were dead anyway, because the
board reset before reaching the loop that reads them. Half an afternoon went
into checking bus wiring that was never wrong.

Nothing in software fixes an undervoltage — that is a cable, a port, or a
regulator. What software can do is stop the board walking into the same wall on
every boot: after two brownout resets in a row it comes up with the radio OFF,
answers on USB and RS485 as normal, and says why. `WIFI ON` still turns the
radio on, because refusing the operator's own command would make a careful
board feel like a broken one.

The three properties that actually matter, and what breaking each would mean:

  * **two in a row, not one.** A single brownout can be a stalled servo or a
    motor's inrush. Tripping on one would leave boards radio-less for a
    momentary dip;
  * **the count survives a reset and NOT a power cut.** A reset is the event
    being counted. A power cut is somebody having just changed the cable, and
    they are owed a board that tries again;
  * **an explicit WIFI ON still works.** Otherwise the fix is a board that
    cannot be told to try, which is worse than the fault.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "a board that keeps browning out comes up reachable, not silent"


def run(t):
    fw = F.FIRMWARE
    hdr = (fw / "src" / "core" / "BrownoutGuard.h").read_text(encoding="utf-8")
    src = (fw / "src" / "core" / "BrownoutGuard.cpp").read_text(encoding="utf-8")
    main_cpp = (fw / "src" / "main.cpp").read_text(encoding="utf-8")
    portal = (fw / "src" / "core" / "WebPortal.cpp").read_text(encoding="utf-8")

    # ---- two in a row, not one --------------------------------------
    m = re.search(r"TRIP_AT = (\d+)", src)
    if t.ok(m, "the threshold is a named number"):
        t.ok(int(m.group(1)) >= 2,
             "it takes more than one brownout to turn the radio off (%s)"
             % m.group(1),
             "a single dip can be a stalled servo or a motor's inrush; "
             "tripping on one would cost every board its radio for a moment "
             "of bad luck")

    # ---- the count outlives a reset, but not the power ---------------
    t.contains(src, "RTC_NOINIT_ATTR",
               "the count lives in RTC memory")
    t.ok("ESP_RST_POWERON" in src and "g_count = 0" in src,
         "and a power cycle clears it",
         "somebody who has just changed the cable is owed a board that tries "
         "again — a count that survived the power would punish the fix")
    t.contains(src, "MAGIC",
               "with a magic word, since RTC memory is rubbish on a cold start")
    # A brownout must INCREASE it; anything else must not silently clear it.
    inc = src[src.find("if (why == ESP_RST_BROWNOUT)"):]
    inc = inc[:inc.find("count_ =")]
    t.contains(inc, "g_count++",
               "a brownout reset counts")
    t.ok("ESP_RST_SW" not in inc,
         "and an ordinary reboot does NOT clear the count",
         "this path reboots the board itself after an update; clearing there "
         "would hide a supply that had been failing all afternoon")

    # ---- it runs before anything draws current -----------------------
    i_guard = main_cpp.find("brownout.begin()")
    i_hw = main_cpp.find("hw.begin()")
    i_portal = main_cpp.find("portal.begin(")
    t.ok(0 < i_guard < i_hw,
         "the guard runs first in setup, before any hardware is brought up")
    t.ok(i_guard < i_portal,
         "and well before the radio, which is what the decision is about")

    # ---- the radio really stays off, and only at boot -----------------
    beg = portal[portal.find("void WebPortal::begin("):]
    beg = beg[:beg.find("\n}") + 2]
    t.contains(beg, "brownout.tripped()",
               "boot asks the guard before choosing a radio mode")
    t.ok('String("off")' in beg,
         "and picks off when it has tripped",
         "the whole point is a board that answers on USB and RS485 instead of "
         "resetting forever")
    apply_mode = portal[portal.find("void WebPortal::applyMode("):]
    apply_mode = apply_mode[:apply_mode.find("\n}") + 2]
    t.ok("brownout" not in apply_mode,
         "but applyMode itself is NOT gated, so WIFI ON still works",
         "a guard that refused the operator's own command would leave no way "
         "to try again once the cable was changed — that is worse than the "
         "fault it protects against")

    # ---- it says why, where somebody will actually see it -------------
    for word in ("POWER", "VIN", "WIFI ON"):
        t.ok(word in src, "the boot log names %s" % word,
             "a radio that is off for no stated reason reads as a setting "
             "somebody changed, and sends the next half hour to the wrong "
             "place entirely")
    t.contains(portal, 'brownout.why()',
               "and the WIFI command repeats it")
    wc = portal[portal.find("String WebPortal::wifiCommand("):]
    wc = wc[:wc.find("\n    if (a == \"ON\"")]
    t.contains(wc, "brownout.tripped()",
               "on the one command a person types when they notice",
               )
    t.ok("scrolled" in wc or "boot log" in wc,
         "because a board resetting for ten minutes has scrolled its boot log "
         "away")
