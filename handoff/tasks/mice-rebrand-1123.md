# Rebrand to MICE (events), replace the mouse mascot

Owner: GPT Codex (gpt-6.2-sol medium) on the PC. Claude reviews after its limit resets.
Updated: 2026-11-23
Branch: separate branch from main, one PR, merge per standing approval when QC green.

## Goal (user 2026-11-23, in Thai)
"MICE" is all capitals: Meetings, Incentives, Conferences, Exhibitions, the
event/entertainment business. It is NOT "Mice" the animal. Every name the user
sees must be written MICE. The mouse mascot must go and be replaced by an
event-themed one.

## Do
1. User-visible name -> "MICE" (uppercase) in: hub title (`web/home/parts/top.html:41`
   "Mice Control Hub" -> "MICE Control Hub"), every page <title> (e.g.
   `web/help/index.template.html:6` "Help — Mice"), Help (`main_python/web/help/parts/`),
   About, launchers in `main_python/launchers`, exe window title, all 4 languages
   (`shared/web/lang/{th,en,zh,ja}.json`, tools/lang.py). Grep "Mice", "mice", "mouse", "หนู", "老鼠", "ネズミ".
2. Keep internal names unchanged: paths, ports, MiceHub.exe filename, `Mice.*` JS namespace, `mice-ui.js`, repo.
3. Mascot: `main_python/web/home/parts/top.html:41` uses `/img/mascot.webp` (class `brand-mouse`).
   Replace with the robot "Nong" as an event host (cartoon style, same as the tool icon set),
   light + dark versions. Remove any other mouse imagery/emoji. Rename the CSS class (e.g. `brand-mascot`).
4. Add a short plain-words explanation in Help and About: MICE = Meetings, Incentives,
   Conferences, Exhibitions, all 4 languages (Rule 11: Help parity in the same step).
5. Never edit built files (hub.html, help.html, app.js): edit parts/, run `python tools/build_web.py`.
6. QC: `python qc/run_qc.py --quiet <checks>`; full QC once before merge; visual check of Home light/dark,
   phone + desktop (tools/visual). Add/adjust a check that no user-visible "Mice" remains.
7. Exe rebuild is done by the coordinator after merge. Do not rebuild.

## Doing now
(nothing yet, not picked up)

## Done
- Task written by Claude.

## Next
All of "Do".

## File status
File | Change | State | Verification | Commit
(none yet)
