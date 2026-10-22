# Gachapon ask: line-by-line audit and the gaps it found

Owner: claude:10qzvx
Updated: 2026-10-22 19:45Z
Branch: claude/project-thread-10qzvx
Last commit: (none yet)
Plan: A47-10

## Goal
User 2026-10-22 19:36Z: "ทุกอย่างเสร็จหมดแล้วหรอ งานมีตั้งเยอะไม่ใช่หรอทำแอพของ gachapong ยัง".
Audit the original ask (thread "Gachapon prize dispenser module", 13:47Z) against main
4825c50 and build every gap.

## Facts found
- Module web (firmware/src/web/WebUI.h:441-492): give / force / stop, turn 1/N/back/1 magnet,
  find loading place, event name, start/close/new event, kind, balls set/add/off, Setup card
  (GCFG rows: magnets, pockets, drop, speed). Commands GachaModule.cpp:95-210.
- Hub (main_python/gacha.py): candidates() only machines of the SAME kind (:396); near list
  orders them. No substitute kind when a kind is out. machines_view has no address for a link.
- Sheet: pull (CSV) + push (docs/gacha/apps_script.gs); samples items/people CSV; no Form sample.

## Doing now
Building: items.<kind>.instead (gacha.dispense tries a substitute kind, a near machine first,
message key "instead"), Kinds table column, machine "its own page" link (/mod?dev=), Google Form
sample docs/gacha/form_sample.gs; check_gacha asserts.

## Done

## Next
1. QC check_gacha + sabotage, quick QC, full QC, PR, merge; post the Thai audit table.

## Blocked
- Bench (A47-5) and SolidWorks reading need the PC/board.
