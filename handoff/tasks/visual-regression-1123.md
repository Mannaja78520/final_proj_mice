# Screenshot regression + numeric 3D check + Thai-leak QC

Owner: codex:11232030-35b8
Updated: 2026-11-23T20:48+07:00
Branch: codex/visual-regression-1123
Last commit: this checkpoint
Plan: none (user ask 2026-11-23: "ได้เช็คทั้งหมดแล้วจริงปะ ทำไมยังเหลือพังอีกเยอะ")

## Goal
Look at every page like a person (screenshots, 4 languages, dark/light, phone/desktop), check the 3D robot
numerically against the URDF, list visual bugs, add what a script can decide to QC.

## Doing now
Item 2, round 1: verify suppression in the full module page at 390 px while GET /api/status stays pending. Hypothesis: capability cards start allowed because their data-cap attributes are missing. Baseline reproduced: eight controls painted before JavaScript and while status was held. Mark all cards managed by showCard() as unavailable at first paint, add a structural QC check, update localized Help, then replay the same two fixtures. Build touched firmware and verify in QEMU before any merge.

## File status
Baseline: 06db461a (PRs #215, #217, #219, #220 and #229 already landed).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/visual-regression-1123.md | Item 1 evidence and item 2 start | doing | staged diff audited | this checkpoint |
| shared/web/mice-lang.js | Publish applied language on the document | done | Edge 28/28 phone cases | 10019b4 |
| qc/checks/check_dialog_language.py | Assert exact root language | done | isolated Edge failed twice at baseline; 11/11 after | 10019b4 |
| main_python/web/help/parts/bytask.html | Screen reader language guidance | done | web build and lang check | 10019b4 |
| main_python/web/help.html | Rebuilt Help | done | web build and lang check | 10019b4 |
| shared/web/lang/help/th.json | Thai Help guidance | done | lang check | 10019b4 |
| shared/web/lang/help/zh.json | Chinese Help guidance | done | lang check | 10019b4 |
| shared/web/lang/help/ja.json | Japanese Help guidance | done | lang check and Edge phone | 10019b4 |
| firmware/src/web/WebUI.h | Hide capability cards until status | pending | not run | uncommitted |
| firmware/generated/web/ModuleUI.h | Regenerate all-types module page | pending | not run | uncommitted |
| qc/checks/check_board_page_motors_first.py | Assert capability cards start hidden | pending | not run | uncommitted |
| main_python/web/help/parts/modsite.html | Document connection and control visibility | pending | not run | uncommitted |

## Facts found
- Item 2 baseline (module-before-caps.json): on the hub at 390 px, all eight control cards appeared before JavaScript and before the first nong or lift status. After status, only the correct card remained. applyTabs() permits data-cap values other than 0, including missing.
- Edge 157, current 06db461a, 390 ? 844: Home, Help, Studio, TV, Camera, Voice, and Gacha selected all four themes correctly and stayed at 390 px. Japanese titles appeared, but root language was en or empty in all 28 cases. Private evidence: .local/visual-regression-1123/phone-theme-check.json.
- Item 1 evidence (private): .local/visual-regression-1123/fast-comparison.txt and review-desk.jpg / review-phone.jpg. Edge 157 compared 220 Japanese states per SHA (390/1440, Midnight/Daylight/Indigo/Carnival). Zero capture exceptions, horizontal overflow, or corner-stuck popups. Largest desktop dark deltas: Help art/locale (46.8%), different/paged report data (40.7%), Settings locale (31.0%). Largest light deltas: CAD/grid bounds and viewport shift (up to 14.7% on desktop), firmware inventory and localized module/Settings cards on phones (up to 27.2%). Mobile Studio now scrolls the selected tab into view; narrow landscape/content reachability remains item 4. Module capture is a no-device fixture and CAD assembly fragments exist in both revisions.
- Item 1 follow-up: .local/visual-regression-1123/locale-after.log and phone-theme-after.json. Before patch the new assertion failed for th and zh; after patch 11/11 isolated browser assertions and 28/28 Japanese phone checks passed. Help rebuilt and locale packs validated.
- Screenshots taken mid-fade show a dim selected tab that is not a bug: shoot.js disables transitions.
- Committed nong.urdf names meshes/*.stl but the STLs sit in models/ (404 in CAD look) and torso/fore STLs are in assembly-world coordinates: CAD look in a clean checkout shows fragments. Studio 3D thread's area.
- haveRobot() in Studio means "connected to a robot", not "3D ready".

## Done
- Item 1: compared the Japanese matrix, reviewed the largest changes and fixed the document language for screen readers. WIP retained for full QC and review before PR/merge.
- PR #215, #217 (visual tool, phone/theme/contrast fixes), #219 (reports paging, Esc closes Report box, Studio texts translate), #220 (blank/negative number boxes). Each has a QC check proven by breaking it.
- Old-vs-new screenshots compared: desktop dark/light and zh desktop+phone (old build was untranslated; new is fine). ja and carnival/indigo not compared.

## Next (handed to GPT Codex 2026-11-23, user: Claude is near its limit; Claude reviews after reset)
Work in a branch off main, one PR per item, QC per CLAUDE.md (`python qc/run_qc.py --quiet <checks>`, full QC once before merge), every fix needs a check proven by breaking the fix. Merge per standing approval (cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv). Never edit friend repos.
2. Module page (/mod, firmware/src/web/WebUI.h, generated firmware/generated/web/ModuleUI.h): for ~100 ms-seconds before the board answers, Lift controls (Up/Down/Stop) AND nong controls show together on a nong (found 2026-11-23: all cards visible until applyTabs runs). Hide capability cards until identified. FIRMWARE RULE: needs the ESP32 QEMU sim incl. phone-width walkthrough before merge (`tools/qemu_esp32.py`), cloud has no pio.
3. Network drop during playback (GPT case 35): Studio/hub show a stale status, Stop stays reachable, no duplicate playback on recovery. Write a QC check with the fake hub (block /api/* mid-play), fix what breaks.
4. Remaining GPT list in PC `.local/visual_review/out/codex62_cases.md` (cases 2-7, 12-14, 16-23, 25, 29-31): pick those testable with the fake hub, one check each, fix bugs found. Skip 36-38 (real Android TV).
5. Tooltip ratchet: lower `attrLeakBaseline` in tools/visual/pages.json by translating English tooltips (use tools/lang_add.py; check_visual_language shows which).
6. PC cleanup (low): E:\final_proj\mice\mice_sim_wt has a locked qemu-system-xtensa.exe; stop the QEMU processes under that folder, delete it, `git worktree prune`.
Stop rule: max 3 rounds per item; if stuck, write the theory in this file and take the next.

## Blocked
- Shared fake-module slot remains occupied by the earlier demo Hub (PID 22308). Full QC and promotion pending. Isolated HTTP-only browser checks use no fake serial driver.
- Real URDF check needs the PC (E:\final_proj\mice\mice_system) to run tools/visual/urdf_numeric.py with MICE model.
- PC leftover: E:\final_proj\mice\mice_sim_wt still holds a locked qemu-system-xtensa.exe (4 QEMU processes under that folder: PIDs seen 2026-11-23 11780, 32752, 48392, 53372). The PC refused Stop-Process/Remove-Item from a remote session; close those QEMU processes, delete the folder, then `git worktree prune` in mice_system. Low priority.
