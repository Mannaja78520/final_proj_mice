# Gachapon prize dispenser (firmware + hub app + voice)

Owner:
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
nothing: A47-1..4 merged; only A47-5 (bench) left, owner free.

## Done
- A47-1 firmware written: firmware/src/modules/gacha/, env mice_gacha builds (71.3% flash), web cards, COMMANDS.md, commands.json, native tests. Not on hardware.
- plan rows A47-1..5 added (heading # A47 in PLAN).
- QC full 7682/6 then the 6 fixed or flaky: plan heading, systems map (fw-gacha), designer-first crash (parallel file race), rs485 census + show clock timing (pass alone).

- PR #57 merged (firmware A47-1).
- A47-2 hub app: main_python/gacha.py (brain), hub_api_gacha.py (routes /api/gacha/*), apps/gacha/index.html, config/gacha.json, docs/gacha/ (README API + webhooks, sample CSV = sheet layout, apps_script.gs write-back), help section. Rules + logs in .local/gacha/ (names, git-ignored).
- A47-3 voice: hub voice_proxy -> hub_api_gacha.voice_after_ask -> voice_prizes.py: topic per question (config/voice_topics.json), CSV .local/voice/questions.csv, prize rules config/voice_prizes.json (off by default; switch on the Prize machines page), Voice > Questions tab charts (/api/questions).
- A47-4: docs/gacha/friend_requests.md (+ copy in project files friend_api/).
- check_gacha (24 asserts, fake boards ids 70/71 in fake_serial) proven by sabotage (fallback, auth).

## Next
1. After PR #60 (A47-6..9: game wins, app keys, Voice topics) on the PC: rebuild MiceHub.exe with
   the spec, open /app/all-jao/, add a row on Prize machines > Games that give a prize, spin the
   wheel and see the toast + the board turn. Their :8080 settings do not carry to /play/all-jao/.
   Friend asks (Thai): docs/gacha/friend_requests.md.
   A47-10 (audit, PR after #60): a kind may name substitutes (Kinds > When it runs out, give
   instead); each machine row has "its own page"; Google Form sample docs/gacha/form_sample.gs.
   Audit table: /mnt/project-files/gacha/audit_2026-10-22.md.
2. A47-5 on the bench (PC RC session): flash mice_gacha over USB/OTA, PIN motor_a/motor_b if not 25/26, measure drop pockets (GCFG drop), speed, settle; add the machine on the Prize machines page; rebuild MiceHub.exe (spec) so the new page and routes ship.

## Blocked
- A47-5 needs the board on the bench (user).
