# Gacha safety — approved source, full gate next

Owner: codex:10231901-f6cc
Updated: 2026-10-25T16:04:28+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: this checkpoint; approved functional source4d41a3c
Plan: A47-20 (robot); A0-35 audit done

## Goal
Preserve Gemini Gacha features; bound motion, make completion/reference/refusals truthful, verify and prepare source integration. No physical calibration or runtime changes.

## Doing now
Freeze immutable inputs, confirm fresh matching-driver inventory0, send exact evidence/fingerprint to existing main, then run full QC ONCE as explicitly authorized. Main independently APPROVED source4d41a3c; all current affected/build checks passed and deliberate reversions restored. No runtime source change beyond4d41a3c without delta review. Software-only QC lease active; hardware USER NOT READY.

## Facts found
- Preserved incoming root C++AAAE3506 and WebUI1e3b2e features (intake/GCALIB/GTEST/GDRAIN/tuning) in corrected branch. Earlier quick5716/5735 are proven quick, not full.
- Motion uses debounced/resting Hall, bounded nonblocking phases, STOP, per-pocket GTEST and explicit timedfallback without known-position claims. Hall proves neither geometric centre/mass nor a dropped capsule.
- Final review fixes: actual GCFG accepted true magnets/slots/dir/polarity changes and CLEAR invalidate/reset logical reference; polarity/CLEAR reset Hall. Rejected/no-op/non-reference settings preserve reference.
- GTEST omitted count remains1 (production assertion); doc corrected. Actual HTTP200 ERRbusy from board is preferred over generic Api says; browser verifies real Hub->fake boundary.

## Done
- Final affected+actual5firmwareenvironment/native suite1667/0 (94.8s), including actual private CAD, both Gacha pages, TV/Studio/Help, layout360–1920, contracts/generators/handoff. This is affected, not full.
- New focused native195 + browser24 + parse4 =223/0; uncorrected old production209/10 demonstrated new review symptoms. Across iteration33 deliberate cases caught/restored (old27 + config/default5 + board-error1).
- Existing main review source4d41a3c approved all3final corrections; no other actionable source finding in reviewed scope. This approval is not fullQC, hardware or deployment acceptance.
- Evidence current: scratch/gacha-safety-1025/full-gate-4d41a3c/affected-build.log and affected-build-details.log; firmware-artifacts.json records all5 binary hashes/sizes. Gacha image is unflashed.

## Next
1. Full gate on this exact frozen input manifest; record before/after fingerprints and receipt, no concurrent driver or source mutation.
2. After fullgreen prepare source PR/PCintegration handoff with exact source/build/evidence; reconcile any later root handoff-only prose once without runtime changes.
3. Any actual runtime source finding invalidates approval/proof and needs affected checks + existing main delta review before release.
4. USER NOT READY for hardware: no device retries/checks, motion, HOME/RELAX, network, flash, trim/calibration or Hub/service restart.

## Blocked
Full QC NOT RUN yet; PR/merge/source promotion/runtime deployment not done. Source review is approved4d41a3c; software gate may proceed autonomously only after input/inventory conditions. No physical/runtime rights acquired.

## File status
Baseline:e30bc36; preserved Gemini2bd3299/8530dbf/6db1aeb, rules9b57ee9, Help8064292. Only owned changes below; imported Help design attributed above.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| firmware/config/esp32_hardware_gacha_module.h | Bounded timing/default constants | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaMath.h | Nonblocking bounded CenterMotion | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaModule.h | Async jobs/phases, progress, learned advance | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 4d41a3c |
| firmware/src/modules/gacha/GachaModule.cpp | Bounded jobs/STOP/args/per-pocket/Hall verification, timedfallback, already-at-Hall HOME result | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 4d41a3c |
| firmware/config/commands.json | Preserve latest features; truthful async Hall contract | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | fa6c986 |
| firmware/COMMANDS.md | Limits/progress/timed result, no mass/centre guarantee | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | 4d41a3c |
| apps/gacha/index.html | Parse fixes, motion status, per-pocket units, STOP | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | 9e46ad0 |
| apps/gacha/motion.js | Separate async polling class | pending | actual Hub/fake browser24/0 incl HTTP200 ERRbusy; error-priority sabotage1/1 caught/restored; affected1667/0; full pending | 4d41a3c |
| qc/checks/check_gacha_motion.py | Compile actual source methods/commands with fake IO | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 4d41a3c |
| qc/data/gacha_motion.cpp | Motor/deadline/args/calib/drain/test/default/no-rock regressions | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 4d41a3c |
| qc/checks/check_gacha_ui.py | Actual page->Hub->fake board;8magnets/4pockets | pending | actual Hub/fake browser24/0 incl HTTP200 ERRbusy; error-priority sabotage1/1 caught/restored; affected1667/0; full pending | 4d41a3c |
| qc/checks/check_remote_scripts.py | Parse shipped inline/helper JS | pending | parse4/0 and quote sabotage caught; affected1667/0; full pending | fa6c986 |
| docs/urdf_nong.md | Separate native zero/Studio zero/90/HOME | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | 90847e8 |
| handoff/tasks/gacha-safety-1024.md | Reconciled per-file current state | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | this checkpoint |
| firmware/src/web/WebUI.h | Preserve root20line module-page features, truthful Hall/progress | pending | approved runtime4d41a3c; current affected+actual firmware/native1667/0; full/landing pending | 9e46ad0 |
| qc/data/gacha_config.cpp | Focused actual-GCFG accepted/rejected/CLEAR/polarity reference cases | pending | actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0; full pending | 4d41a3c |

## Evidence / preserved data
- Earlier dc5a953/input82527a snapshot stays historical under scratch/gacha-safety-1025/candidate-cf23113/. Current gate folder is full-gate-4d41a3c/; runtime source approved4d41a3c.
- Existing qc_chain_proj.json/settings_shared.json and old reports remain unstaged/unpromoted QC/user data. EOL-only status noise in generated files has no content diff. Root other-owner files and ordinary services preserved.
- Main may receive later Gemini own-handoff prose only; no additional full/affected rerun solely for that metadata, per explicit main instruction. Keep gate source frozen during run.
