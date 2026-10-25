# Gacha safety — approved source, full gate next

Owner: codex:10231901-f6cc
Updated: 2026-10-25T16:48:55+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: this checkpoint; approved functional source4d41a3c
Plan: A47-20 (robot); A0-35 audit done

## Goal
Preserve Gemini Gacha features; bound motion, make completion/reference/refusals truthful, verify and prepare source integration. No physical calibration or runtime changes.

## Doing now
Verification delta f037d3a complete: focused144/0; real Tools/theme/Gacha/receipt/plan/devtools+integrity325/0; all3original CRLF source hashes unchanged. Integrity5/5 deliberate reversions caught/restored. Metadata-only Gemini75-row handoff a56c177 merged; generator headers current. Existing main must inspect exact verification delta before justified second full. Product runtime4d41a3c unchanged/approved; first failed8217/1 and input-drift evidence preserved, no PR/fullgreen claim.

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
1. Fix verification only: canonical plan resolver using existing plan tool; exact bytes in manifest/theme/sabotage cleanup; CRLF/error-path regression. Isolate long Gacha journey in existing SOLO lane without dropping assertions or changing timeout budgets.
2. Focused checks + deliberate failures/restoredgreen, generator headers, exact verification delta review by existing main. No hardware-state changes or guard exclusions.
3. Freeze corrected input manifest and rerun full for this diagnosed failure once approved; preserve first run evidence. Then PR/PCintegration preparation.

## Blocked
Fullgate NOT GREEN; no valid completion/PR/merge/deploy. Product runtime4d41a3c remains source-approved, but verification repairs/delta review + stable fullgate required. Human hardware notready; no actual hardware/network/service action.

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

- First-gate exact evidence: full-gate-4d41a3c/full.log,full-details.log,full-result.json,inputs-before/after.json,input-drift-analysis.json. Gacha crowd failed with noGUI marks, then2/2 greenalone; startup/resource explanation is inference, not proven product fault. All assertions retained.
| qc/checks/check_packing_list.py | Resolve only canonical live plan, not stale published worktree copy | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| qc/checks/check_tools_list.py | Restore manifest probe original bytes | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| qc/checks/check_themes.py | Restore theme probe original bytes | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| tools/sabotage.py | Always restore original source bytes | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| qc/checks/check_dev_tools.py | Actual byte comparison for sabotage cleanup | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| qc/checks/check_qc_probe_integrity.py | Stale published plan + CRLF/exception probe regressions | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |
| qc/run_qc.py | Complete Gacha journey in existing SOLO isolation lane | pending | focused144/0, real probes325/0, integrity5/5 caught/restored, exact3source bytes; review/r2full pending | f037d3a |

- Latest verification evidence: gate-integrity-focused-1025.log144/0, gate-integrity-real-probes-1025.log325/0, probe-restoration-result-1025.json all_exacttrue, sabotage-integrity-1025.log5/5 caught/restored. These repair verification only; original product runtime4d remains unchanged.
