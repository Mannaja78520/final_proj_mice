# Gacha: bounded centering, nudge and truthful fault reporting

Owner: codex:10231901-f6cc
Updated: 2026-10-25T07:46:24+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: a176f3a (merged8530dbf +9b57ee9); current changes in this checkpoint
Plan: A47-20 (robot); A0-35 audit done

## Goal
Carry confirmed Gemini safety gaps through isolated fix, actual-source regression, sabotage, independent existing-main review and exact full gate. Preserve user5s pause and queued gacha webUI/autocalibration work. Main owns HOME/physical explanation; user defers physical elbow trim to themselves. No CAD/calibration edits.

## Doing now
Checkpoint current source/docs/generated mappings, then deliberately sabotage native/UI/render/TV fixes, restore green, compile actual gacha firmware/native and run affected checks. Reconcile active HelpUI owner before final exact snapshot to existing main reviewer; full gate only after source freeze. No hardware/runtime/userconfig changes.

## Facts found
- Private snapshots separate23Oct, frozen15:38 and late17:33 Gemini sources. Latestfeatures intake/GCALIB/GTEST/GDRAIN retained; command registry is now complete. Quick5716 and5735 provenance is explicit --quick, not full.
- Current implementation runs actual-source C++ through fake IO; Hall-rest verification also applies with no rocking, pause0 and legacysettle. Explicit fallback completes as timed and invalidates position.
- Current UI uses one-pocket units GSPIN1 at8magnets/4slots and reads async motion_result/progress; Hall alone proves neither mass/geometry nor a dropped capsule.

## Done
- Current203/0 native+browser/syntax batch, then637/0 command/docs/systems/affected batch. Detailed logs in scratch/continue-urdf-1023; neither is full.
- LatestGemini8530dbf partialfixes reconciled aa5ecaa; newrules9b57ee9 merged a176f3a. Own valid-target guards and measured regressions preserved.
- QC-only rights released Lab22:12 and claimed22:16. Physical remains stopped/reserved; no transfer of hardware/flash/camera/Hub rights.

## Next
Run deliberate sabotage, gacha firmware/native/affected checks on current source; inspect final diff and resolve independent findings. Send stable full diff and evidence to existing main for independent review, then exact full gate. Preserve root user data/latest features; no physical promotion/flash permission.

## Blocked
No physical testing, camera, Hub restart or firmware deployment acquired. User physical elbow centering is deferred, not passed. Root main/source features must be reconciled before any later authorized integration; do not overwrite with old snapshot.

## Latest snapshot
- Current root cpp late24Oct SHAaaae3506d77d3a8fe828e4baa3d8a95619d717102bc33ba5985cfc9b4b117d74 differs again; immutable snapshot in root scratch/gemini-audit-1024/late-24oct. Own candidate90847e8 is NOT validated/deployed; no source write or execution in root by this chat.

## File status
Baseline: e30bc36; preserve inherited latest Gemini2bd3299/8530dbf and rules9b57ee9; ledger lists own changes only.
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| firmware/config/esp32_hardware_gacha_module.h | Bounded timing/default constants | pending | prior native135/0; final build pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaMath.h | Nonblocking bounded CenterMotion | pending | prior native135/0; sabotage pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaModule.h | Async jobs/phases, progress, learned advance | pending | prior native135/0; final build pending | 3bb6c07 |
| firmware/src/modules/gacha/GachaModule.cpp | Bounded jobs/STOP, strict args, per-pocket verification; no-rock/settle/fallback truthful | pending | latest native162/0 incl no-rock/settle/pause0/timedfallback; no full signoff | fa6c986 |
| firmware/config/commands.json | Preserve latest features; truthful async Hall contract | pending | generation/docs checks pending | fa6c986 |
| firmware/COMMANDS.md | Limits/progress/timed result, no mass/centre guarantee | pending | contract checks pending | fa6c986 |
| apps/gacha/index.html | Parse fixes, motion status, per-pocket units, STOP | pending | current Gacha16/0 + syntax4/0,8magnets/4slots, GSPIN1; sabotage/review pending | uncommitted |
| apps/gacha/motion.js | Separate async polling class | pending | browser demonstrated phase/jam/STOP; sabotage pending | fa6c986 |
| qc/checks/check_gacha_motion.py | Compile actual source methods/commands with fake IO | pending | native162/0 after physical-phase fixture update | 3bb6c07 |
| qc/data/gacha_motion.cpp | Motor/deadline/args/calib/drain/test/default/no-rock regressions | pending | native162/0, incl persistent Hall during rest and verified each pocket | 17809df |
| qc/checks/check_gacha_ui.py | Actual page->Hub->fake board;8magnets/4pockets | pending | current16/0 with8magnets/4slots; sabotage pending | fa6c986 |
| qc/checks/check_remote_scripts.py | Parse shipped inline/helper JS | pending |current4/0; sabotage pending | fa6c986 |
| docs/urdf_nong.md | Separate native zero/Studio zero/90/HOME | done | independent source review earlier; no geometry edits | 90847e8 |
| handoff/tasks/gacha-safety-1024.md | Reconciled per-file current state | pending | explicit file ledger; final completion later | this checkpoint |

- Current combined evidence: scratch/continue-urdf-1023/ui-native-affected-1025-v1.log =203/0 (25.5s), not full QC.
