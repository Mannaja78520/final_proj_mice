# Gachapon prize dispenser (firmware + hub app + voice)

Owner: claude:gacha-3pztbe
Updated: 2026-10-22 17:20Z
Branch: claude/project-thread-3pztbe
Last commit: (none yet)
Plan: A47-1 firmware, A47-2 hub app, A47-3 voice, A47-4 friend list, A47-5 [hw] bench

## Goal
User 2026-10-22 (Thai, summarised): a new ESP32 module that hands out prizes.
Motor + everything the other modules have (RS485, WiFi/AP, web admin/admin123,
OTA, module name, many machines at once) except the SD card. One hall sensor
on GPIO33 at the receive position; 4 magnets on a 4-slot holder (= all slots
now, configurable). The item arrives from the back into the slot at the hall
and does NOT drop yet; "dispense" turns hall-to-hall, counting magnet passes,
until it drops. Module web page: rotate 1 / N slots, dispense, count, set
magnets, event name, event open/closed, stock (loaded, add more). Simple
external API (HTTP + RS485). Then: hub app (several machines, item type per
machine, fallback to a same-type machine + tell the person, out-of-stock /
dispense-done webhooks, per-event rules incl. times per person, special
Face_Regonize names, admin force still counted, rules local or from Google
Sheets with a sample layout, log everything); voice (which answers give
which item, question topics to CSV + charts in a Voice tab); list for friend.
SolidWorks: E:\final_proj\mice\model\gachapong (read only, never in git).
Lab window ended 14:00Z 2026-10-22: do NOT flash; the PC RC session flashes.

## Doing now
A47-1: firmware module `gacha` (firmware/src/modules/gacha/), env mice_gacha.

## Done
- plan rows A47-1..5 added.

## Next
1. firmware: modules.json entry, GachaModule, hardware header, commands.json, WebUI card, COMMANDS.md, env, QC check.
2. hub app apps/gacha/ (A47-2), voice (A47-3), friend list (A47-4).

## Blocked
- A47-5 needs the board on the bench (user).
