# Screenshot regression + numeric 3D check + Thai-leak QC

Owner: claude
Updated: 2026-11-23 04:05 +0000
Branch: claude/project-thread-z9y1v3
Last commit: this checkpoint
Plan: none (user ask 2026-11-23: "ได้เช็คทั้งหมดแล้วจริงปะ ทำไมยังเหลือพังอีกเยอะ")

## Goal
Look at every page like a person (screenshots, 4 languages, dark/light, phone/desktop), check the 3D robot
numerically against the URDF, list visual bugs, add what a script can decide to QC.

## Doing now
Reading the full screenshot run (/tmp/vis/full, not committed) and fixing bugs outside Studio 3D / Tools page / camera threads.

## File status
Baseline: ed5bd89

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/visual/shoot.js`, `pages.json`, `probe.js`, `serve_hub.py` | screenshot + probe tool (data-driven pages) | done | ran, 4 langs, cloud fake hub | uncommitted |
| `tools/visual/urdf_fk.py`, `urdf_page.js`, `urdf_numeric.py` | independent FK vs page joints | done | repo nong.urdf: 0.000 mm; real SolidWorks model NOT run | uncommitted |
| `qc/checks/check_visual_language.py` | Thai-in-en/zh/ja + popup-at-corner scan | done | failed before fix, passes after (quick, cloud) | uncommitted |
| `main_python/web/home/parts/settings.js`, `hub.html` | settings summary in translatable pieces | done | check_visual_language | uncommitted |
| `shared/web/lang/{en,zh,ja}.json`, `lang/help/*.json` | entries for settings texts, Help Prev/Next | done | tools/lang.py check | uncommitted |
| `tools/lang_add.py` | append pack entries without reformatting | done | used | uncommitted |

## Facts found
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
3. [CLAUDE, done as far as the fake hub goes 2026-11-23, Codex skip] Network drop during playback: the /mod page shows 'No answer from the board for 4 seconds. These numbers are the last ones it sent' when /api is blocked; Studio with /api blocked throws nothing. The board plays on its own clock by design (survives a closed browser), so duplicate playback on recovery is covered by check_one_player; a real mid-play cable/WiFi drop needs the lab. Original text: Network drop during playback (GPT case 35): Studio/hub show a stale status, Stop stays reachable, no duplicate playback on recovery. Write a QC check with the fake hub (block /api/* mid-play), fix what breaks.
4. Remaining GPT list in PC `.local/visual_review/out/codex62_cases.md` (cases 2-7, 12-14, 16-23, 25, 29-31): pick those testable with the fake hub, one check each, fix bugs found. Skip 36-38 (real Android TV).
5. [CLAUDE, DONE in PR #231: ceiling now th 2 / zh 4 / ja 2, Codex skip] Tooltip ratchet: lower `attrLeakBaseline` in tools/visual/pages.json by translating English tooltips (use tools/lang_add.py; check_visual_language shows which).
6. PC cleanup (low): E:\final_proj\mice\mice_sim_wt has a locked qemu-system-xtensa.exe; stop the QEMU processes under that folder, delete it, `git worktree prune`.
Stop rule: max 3 rounds per item; if stuck, write the theory in this file and take the next.

## Round 7 (2026-11-23): themes + simulated device cases
- indigo/carnival old-vs-new compared by eye (Home, Modules, Studio Shows phone, Tools): redesign diffs only, no defect. `shoot.js --themes=indigo,carnival` added.
- Simulated in cloud (Playwright, TV-like 960x540, Chrome 75 user-agent, CDP 50 KB/s + 600 ms latency): `/` loads in 3.4 s, `/tv` 6.5 s, `/studio/` 14.7 s, no sideways scroll, no page errors. A user-agent string is NOT the Chrome 75 engine.
## Lab list (cannot be simulated)
- Real Android TV (Chrome 75 engine) timing and remote-control focus.
- Real cable/WiFi drop mid-play on a board; real 3D numeric check vs URDF (urdf_numeric.py on the PC).
- Firmware module page on a real board (capability cards before the board answers), real USB/ESP32 cameras.

## Blocked
- Real URDF check needs the PC (E:\final_proj\mice\mice_system) to run tools/visual/urdf_numeric.py with MICE model.
- PC leftover: E:\final_proj\mice\mice_sim_wt still holds a locked qemu-system-xtensa.exe (4 QEMU processes under that folder: PIDs seen 2026-11-23 11780, 32752, 48392, 53372). The PC refused Stop-Process/Remove-Item from a remote session; close those QEMU processes, delete the folder, then `git worktree prune` in mice_system. Low priority.
