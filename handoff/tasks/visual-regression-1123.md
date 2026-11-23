# Screenshot regression + numeric 3D check + Thai-leak QC

Owner: codex:11232030-35b8
Updated: 2026-11-23T20:39+07:00
Branch: codex/visual-regression-1123
Last commit: this checkpoint
Plan: none (user ask 2026-11-23: "ได้เช็คทั้งหมดแล้วจริงปะ ทำไมยังเหลือพังอีกเยอะ")

## Goal
Look at every page like a person (screenshots, 4 languages, dark/light, phone/desktop), check the 3D robot
numerically against the URDF, list visual bugs, add what a script can decide to QC.

## Doing now
Item 1, round 1 comparison in progress: compare Edge screenshots from 8865359 and 06db461a using the same fixtures, viewports and locale. Check Japanese desktop/phone in dark/light and indigo/carnival. Budget one capture matrix and one review of largest changes. Stop after three rounds per item, retaining evidence.
Round 2 hypothesis: text translates but the document language stays English/blank. Set the language after the selected pack loads; verify the unchanged Japanese phone fixture before/after and add a QC assertion. Limit: one patch and one targeted browser rerun.

## File status
Baseline: 06db461a (PRs #215, #217, #219, #220 and #229 already landed).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/visual-regression-1123.md | Item 1 capture and reproduction | doing | Edge phone probe, 28 rows | this checkpoint |
| shared/web/mice-lang.js | Set root language after pack load | pending | not run | uncommitted |
| qc/checks/check_dialog_language.py | Assert root language | pending | not run | uncommitted |
| main_python/web/help/parts/bytask.html | Explain language and screen reader behavior | pending | not run | uncommitted |
| main_python/web/help.html | Rebuild Help | pending | not run | uncommitted |
| shared/web/lang/help/th.json | Translate Help language guidance | pending | not run | uncommitted |
| shared/web/lang/help/zh.json | Translate Help language guidance | pending | not run | uncommitted |
| shared/web/lang/help/ja.json | Translate Help language guidance | pending | not run | uncommitted |

## Facts found
- Edge 157, current 06db461a, 390 ? 844: Home, Help, Studio, TV, Camera, Voice, and Gacha selected all four themes correctly and stayed at 390 px. Japanese titles appeared, but root language was en or empty in all 28 cases. Private evidence: .local/visual-regression-1123/phone-theme-check.json.
- First visual diff review (Midnight, desktop): Help 46.8%, Reports 40.7%, Settings 31.0%; content changes are locale, Help art, and different stored report fixtures. Studio differences include header wrapping and panel height; still checking reachability.
- Screenshots taken mid-fade show a dim selected tab that is not a bug: shoot.js disables transitions.
- Committed nong.urdf names meshes/*.stl but the STLs sit in models/ (404 in CAD look) and torso/fore STLs are in assembly-world coordinates: CAD look in a clean checkout shows fragments. Studio 3D thread's area.
- haveRobot() in Studio means "connected to a robot", not "3D ready".

## Done
- PR #215, #217 (visual tool, phone/theme/contrast fixes), #219 (reports paging, Esc closes Report box, Studio texts translate), #220 (blank/negative number boxes). Each has a QC check proven by breaking it.
- Old-vs-new screenshots compared: desktop dark/light and zh desktop+phone (old build was untranslated; new is fine). ja and carnival/indigo not compared.

## Next (handed to GPT Codex 2026-11-23, user: Claude is near its limit; Claude reviews after reset)
Work in a branch off main, one PR per item, QC per CLAUDE.md (`python qc/run_qc.py --quiet <checks>`, full QC once before merge), every fix needs a check proven by breaking the fix. Merge per standing approval (cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv). Never edit friend repos.
1. Old-vs-new screenshots: ja desktop+phone (dark/light) are already taken in the cloud only; redo on PC: `python tools/visual/serve_hub.py` for old (git worktree of 8865359) and new, `node tools/visual/shoot.js <base> <out> --lang=ja`, `python tools/visual/compare.py old new cmp --min 0.02`; LOOK at the biggest diffs, fix real regressions. Also indigo and carnival themes (pages.json `themes`). Done when no unexplained diff remains and findings are listed in this file.
2. Module page (/mod, firmware/src/web/WebUI.h, generated firmware/generated/web/ModuleUI.h): for ~100 ms-seconds before the board answers, Lift controls (Up/Down/Stop) AND nong controls show together on a nong (found 2026-11-23: all cards visible until applyTabs runs). Hide capability cards until identified. FIRMWARE RULE: needs the ESP32 QEMU sim incl. phone-width walkthrough before merge (`tools/qemu_esp32.py`), cloud has no pio.
3. Network drop during playback (GPT case 35): Studio/hub show a stale status, Stop stays reachable, no duplicate playback on recovery. Write a QC check with the fake hub (block /api/* mid-play), fix what breaks.
4. Remaining GPT list in PC `.local/visual_review/out/codex62_cases.md` (cases 2-7, 12-14, 16-23, 25, 29-31): pick those testable with the fake hub, one check each, fix bugs found. Skip 36-38 (real Android TV).
5. Tooltip ratchet: lower `attrLeakBaseline` in tools/visual/pages.json by translating English tooltips (use tools/lang_add.py; check_visual_language shows which).
6. PC cleanup (low): E:\final_proj\mice\mice_sim_wt has a locked qemu-system-xtensa.exe; stop the QEMU processes under that folder, delete it, `git worktree prune`.
Stop rule: max 3 rounds per item; if stuck, write the theory in this file and take the next.

## Blocked
- Real URDF check needs the PC (E:\final_proj\mice\mice_system) to run tools/visual/urdf_numeric.py with MICE model.
- PC leftover: E:\final_proj\mice\mice_sim_wt still holds a locked qemu-system-xtensa.exe (4 QEMU processes under that folder: PIDs seen 2026-11-23 11780, 32752, 48392, 53372). The PC refused Stop-Process/Remove-Item from a remote session; close those QEMU processes, delete the folder, then `git worktree prune` in mice_system. Low priority.
