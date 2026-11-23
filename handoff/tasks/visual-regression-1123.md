# Screenshot regression + numeric 3D check + Thai-leak QC

Owner: codex:11232254-6f5e
Updated: 2026-11-24T00:12+07:00
Branch: codex/visual-regression-1123
Last commit: this checkpoint
Plan: A1123-2

## Goal
Look at every page like a person (screenshots, 4 languages, dark/light, phone/desktop), check the 3D robot
numerically against the URDF, list visual bugs, add what a script can decide to QC.

## Doing now
Checkpoint ready. Three draft PRs are open, the selected case 12 and 20 replays and focused checks passed, and item 6 is clear. Build and QC processes have exited.

## File status
Baseline: 06db461a (PRs #215, #217, #219, #220 and #229 already landed).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/visual-regression-1123.md | Evidence, draft PR heads and remaining cases | done | staged diff audited | this checkpoint |
| shared/web/mice-lang.js | Publish applied language on the document | done | Edge 28/28 phone cases at PR head | 19b50be |
| qc/checks/check_dialog_language.py | Assert exact root language | done | isolated Edge failed twice at baseline; 11/11 after on original snapshot | 19b50be |
| main_python/web/help/parts/bytask.html | Screen-reader and localized search guidance in separate PRs | done | web build and language catalog check | 19b50be, 2a9bf08 |
| main_python/web/help.html | Rebuilt Help for items 1, 2 and 4 | done | web build and language catalog check | 19b50be, 6c298e1, 2a9bf08 |
| shared/web/lang/help/th.json | Thai Help guidance | done | language catalog check | 19b50be, 6c298e1, 2a9bf08 |
| shared/web/lang/help/zh.json | Chinese Help guidance | done | language catalog check | 19b50be, 6c298e1, 2a9bf08 |
| shared/web/lang/help/ja.json | Japanese Help guidance | done | language catalog check and Edge phone | 19b50be, 6c298e1, 2a9bf08 |
| firmware/src/web/WebUI.h | Wait for status before cards and camera settings request | done | Edge failure/recovery 4/4, firmware 12/12, QEMU phone 2/2, focused QC 147/147 | 6c298e1 |
| firmware/generated/web/ModuleUI.h | Regenerate all-types module page | done | gen_tables.py; 107.2 KB; 390 px Edge all-types 4/4 | uncommitted (ignored) |
| qc/checks/check_board_page_motors_first.py | Assert capability cards start hidden | done | 11 fails at baseline, 15/15 after | 8fa77aa |
| main_python/web/help/parts/modsite.html | Document control and camera settings visibility | done | Help build and language catalog check | 6c298e1 |
| main_python/web/help/parts/search.js | Search current Help topic text | done | private Edge replay 4/4 | 2a9bf08 |
| qc/checks/check_help_topics.py | Guard late Help text in the original browser fixture | done | focused QC 24/24 | bc8b43f |
| qc/checks/check_cam_panel.py | Assert card and settings use the same camera capability | done | focused module/QEMU QC 147/147 combined | 6c298e1 |

## Facts found
- Item 2 baseline (module-before-caps.json): on the hub at 390 px, all eight control cards appeared before JavaScript and before the first nong or lift status. After status, only the correct card remained. applyTabs() permits data-cap values other than 0, including missing.
- Edge 157, current 06db461a, 390 ? 844: Home, Help, Studio, TV, Camera, Voice, and Gacha selected all four themes correctly and stayed at 390 px. Japanese titles appeared, but root language was en or empty in all 28 cases. Private evidence: .local/visual-regression-1123/phone-theme-check.json.
- Item 1 evidence (private): .local/visual-regression-1123/fast-comparison.txt and review-desk.jpg / review-phone.jpg. Edge 157 compared 220 Japanese states per SHA (390/1440, Midnight/Daylight/Indigo/Carnival). Zero capture exceptions, horizontal overflow, or corner-stuck popups. Largest desktop dark deltas: Help art/locale (46.8%), different/paged report data (40.7%), Settings locale (31.0%). Largest light deltas: CAD/grid bounds and viewport shift (up to 14.7% on desktop), firmware inventory and localized module/Settings cards on phones (up to 27.2%). Mobile Studio now scrolls the selected tab into view; narrow landscape/content reachability remains item 4. Module capture is a no-device fixture and CAD assembly fragments exist in both revisions.
- Item 1 follow-up: .local/visual-regression-1123/locale-after.log and phone-theme-after.json. Before patch the new assertion failed for th and zh; after patch 11/11 isolated browser assertions and 28/28 Japanese phone checks passed. Help rebuilt and locale packs validated.
- Screenshots taken mid-fade show a dim selected tab that is not a bug: shoot.js disables transitions.
- Committed nong.urdf names meshes/*.stl but the STLs sit in models/ (404 in CAD look) and torso/fore STLs are in assembly-world coordinates: CAD look in a clean checkout shows fragments. Studio 3D thread's area.
- haveRobot() in Studio means "connected to a robot", not "3D ready".

## Done
- Final PR #234 head `6c298e1` built all 12 PlatformIO targets on C:, passed both QEMU 390 px touch walkthroughs, and passed 147/147 focused module/QEMU assertions. Final Nong and Lift screenshots inspected. Private evidence: `%TEMP%/mice-visual-1123-e6f3b60/firmware-case20-build.log`, `phone-case20/` and `qc-case20.log`.
- Item 4 case 12 corrected official Help QC passed 24/24 on `bc8b43f` in 15.9 s. Private log: `%TEMP%/mice-visual-1123-e6f3b60/help-search-proof/help-final-qc.log`.
- Item 6 verified at 00:05 ICT on 2026-11-24. The exact `E:/final_proj/mice/mice_sim_wt` directory and Git entry were already absent. No QEMU process remained under that path. The dry run found nothing to prune and `git worktree prune --verbose` completed without removing entries. E: had 31.34 GiB free.
- Item 4 case 12 [draft PR #236](https://github.com/Mannaja78520/final_proj_mice/pull/236) at `bc8b43f` has the source patch and one late-title assertion in the existing Help QC page. The standalone four-language Edge evidence covers the same stale-index failure.
- Item 4 official Help run at `2a9bf08` scored 93 passed, 4 failed. Its original checks passed. The new driver observed an English late-title match but lost the empty-result assertion and timed out before subsequent iframe fixtures. Use the original test's loaded page for the late-title regression and retain the standalone multi-language evidence.
- Item 4 case 20 follow-up pushed to module draft PR #234 at `6c298e1`. At 390 px all 4 fixtures hid controls and sent zero commands after an initial 503. Nong and Lift sent no camera command after identification. Current and legacy camera status each sent exactly one `CAM LIST` after identification. Evidence: `%TEMP%/mice-visual-1123-e6f3b60/help-search-proof/case20-after.log`. Matching Help source, page and th/ja/zh packs updated.
- Item 4 case 20 baseline: Edge 390 px with a simulated 503 kept all capability cards hidden, then showed the correct Nong or Lift card after successful reload. Both boards received one startup `CAM LIST` before identification. Treat the command count as the assertion and ignore the probe's stale footer. Private log: `%TEMP%/mice-visual-1123-e6f3b60/help-search-proof/case20-wire.log`.
- Item 4 case 12 commit `2a9bf08` searches current topic text and omits Previous/Next captions from matches. The same private Edge component replay passed 4/4 after the patch, including the normal empty result. Language catalog check and Help generation passed. Help source, page and th/ja/zh pack variants are also at `2a9bf08`. Evidence: `%TEMP%/mice-visual-1123-e6f3b60/help-search-proof/after-navigator.log`.
- Item 4 case 12 baseline: Edge 390 px found the displayed Module website title in all four languages, then failed to match the same title after a controlled late text update in all 4/4. The private fixture needed explicit navigator initialization. The existing full-QC Help topics check passed the ordinary first-load path. Evidence: `%TEMP%/mice-visual-1123-e6f3b60/help-search-proof/before-navigator.log`.
- Item 1 [draft PR #235](https://github.com/Mannaja78520/final_proj_mice/pull/235) isolates the prior screen-reader language fix. Language catalog check passed and the exact head `19b50be` passed 28/28 Japanese states at 390 px across four themes and seven pages. Private evidence: `%TEMP%/mice-visual-1123-e6f3b60/language-proof/phone-theme-check.json`. The other host QC process occupied the shared slot, so this replay used a private loopback Hub without a fake serial driver. Help and its three translated pack variants are also at `19b50be`.
- Item 2 full QC finished on PR #234 head `8fa77aa`: 10,631 passed, 27 failed, exit 1 in 1,279.9 s. QEMU firmware 53/53, peripherals 24/24, RS485 bus 12/12 and census 4/4 passed. The stale API index check has byte-identical inputs and outputs on main. Other failures: local clone branch/results metadata, Reconize watcher startup, Help contrast, and remaining locale leakage on Home, Help and Camera. Private log: `%TEMP%/mice-visual-1123-e6f3b60/qc-module-full.log`. PR remains draft.
- Item 2 [draft PR #234](https://github.com/Mannaja78520/final_proj_mice/pull/234) contains only seven module files against main `b1c35dc0`, head `8fa77aa`. Help rebuilt with current main. Shared Help and th/ja/zh pack variants for item 2 are tracked at `8fa77aa`. Firmware inputs and the regression check are identical to the verified snapshot.
- Item 2 builds: 12/12 PlatformIO environments passed at `e6f3b60` (8 production including S3, 4 simulator). Private evidence: `%TEMP%/mice-visual-1123-e6f3b60/firmware-build.log`.
- Item 2 QEMU phone: 2/2 at 390 × 844 px using generated firmware HTML, CSS and JS with UART `PONG`/`INFO`. Both had zero visible capability controls or command requests while status was held, no sideways overflow, and touchscreen navigation between Files and Control after identification. Four screenshots inspected. Nong used its production image. Production Lift compiled but failed to reach `[boot] ready` in QEMU. Lift passed with `mice_lift_sim` and the byte-identical production page (SHA-256 `930d2c0426e3d692c257f3054eb43491da725a5c3298e4373ae8dca47446eb76`). The simulated limit fault left Stop available. Private evidence: `%TEMP%/mice-visual-1123-e6f3b60/phone/`. The HTTP bridge exercised UART status, without emulating WiFi or testing real hardware.
- Item 2 source and Help patch: all eight control cards stay hidden before JavaScript and while the first reply is held. After release, the appropriate cards appear, matching each fixture. Private evidence: module-after-caps.json. Structural QC 4/15 before, 15/15 after.
- Item 1: compared the Japanese matrix, reviewed the largest changes and fixed the document language for screen readers.
- PR #215, #217 (visual tool, phone/theme/contrast fixes), #219 (reports paging, Esc closes Report box, Studio texts translate), #220 (blank/negative number boxes). Each has a QC check proven by breaking it.
- Old-vs-new screenshots compared: desktop dark/light and zh desktop+phone (old build was untranslated; new is fine). ja and carnival/indigo not compared.

## Next (handed to GPT Codex 2026-11-23, user: Claude is near its limit; Claude reviews after reset)
Work in a branch off main, one PR per item, QC per CLAUDE.md (`python qc/run_qc.py --quiet <checks>`, full QC once before merge), every fix needs a check proven by breaking the fix. Merge per standing approval (cmsg_01R7BbYxaTb3Yv9YS3gQaaA3XEQcQQyoUgXwMT6wXgfeYv). Never edit friend repos.
1. Screen-reader language fix is draft #235. Full gate and independent review remain before merge.
2. Module page is draft #234. Review and obtain green full QC on final head `6c298e1` after the baseline and test-environment failures are resolved. The prior full gate ran on `8fa77aa`.
3. Claude completed fake-hub network loss coverage. Real cable/WiFi playback loss remains lab work (main 710bd52c).
4. Cases 12 and 20 were selected and fixed. The remaining listed cases (2-7, 13-14, 16-19, 21-23, 25, 29-31) still need targeted runs. Start with case 2 in the fake Hub, a short landscape Studio walkthrough using actual hit targets below the fixed bar. Cases 36-38 remain real Android TV work.
5. Claude landed the tooltip ratchet in PR #231.
6. Done. Verified the stale folder, QEMU process paths and Git metadata are clear.
Stop rule: max 3 rounds per item; if stuck, write the theory in this file and take the next.

## Blocked
- Draft PRs #234, #235 and #236 await a green full gate and independent review. No promotion or hardware test performed.
- The numeric review with the real CAD and `tools/visual/urdf_numeric.py` remains open.
