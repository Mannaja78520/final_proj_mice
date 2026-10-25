# Gacha safety — full green, source integration pending

Owner: codex:10231901-f6cc
Updated: 2026-10-25T17:08:17+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: this metadata-only checkpoint; full gate8da4e169; runtime4d41a3c; verificationf037d3a
Plan: A47-20 (robot); A0-35 audit done

## Goal
Preserve Gemini Gacha features; bound motion, make completion/reference/refusals truthful, verify and prepare source integration. No physical calibration or runtime changes.

## Doing now
R2 full finished8258/0 in686.0s; exact978raw inputs stable at8da4e169/db76249b...d90c7. Existing main independently accepted receipt with3crowdFLAKY each alone2/2. Prepare sourcePR and scoped integration handoff; keep runtime unchanged, root user work intact. Software driver explicitly released with postflight0. No hardware/runtime actions.

## Facts found
- Preserved incoming root C++AAAE3506 and WebUI1e3b2e features (intake/GCALIB/GTEST/GDRAIN/tuning) in corrected branch. Earlier quick5716/5735 are proven quick, not full.
- Motion uses debounced/resting Hall, bounded nonblocking phases, STOP, per-pocket GTEST and explicit timedfallback without known-position claims. Hall proves neither geometric centre/mass nor a dropped capsule.
- Final review fixes: actual GCFG accepted true magnets/slots/dir/polarity changes and CLEAR invalidate/reset logical reference; polarity/CLEAR reset Hall. Rejected/no-op/non-reference settings preserve reference.
- GTEST omitted count remains1 (production assertion); doc corrected. Actual HTTP200 ERRbusy from board is preferred over generic Api says; browser verifies real Hub->fake boundary.

## Done
- Current FULL8258/0 in686.0s,313checks at8da4e169; freeze/before/after978raw inputs identical db76249bd51ffa8a06ddbe8413f47a03455acda12b8008206321f086b11d90c7, changedinputs[]. Receipt fulltrue, main independently accepted.
- Existing crowdFLAKY check_gestures/check_game_prize/check_studio_auto_route each passed alone2/2 under unchanged runner; retained raw symptoms. Gacha SOLO passed. All5actual firmware hashes match approved build; unflashed.
- Final affected+actual5firmwareenvironment/native suite1667/0 (94.8s), including actual private CAD, both Gacha pages, TV/Studio/Help, layout360–1920, contracts/generators/handoff. This is affected, not full.
- New focused native195 + browser24 + parse4 =223/0; uncorrected old production209/10 demonstrated new review symptoms. Across iteration33 deliberate cases caught/restored (old27 + config/default5 + board-error1).
- Existing main review source4d41a3c approved all3final corrections; no other actionable source finding in reviewed scope. This approval is not fullQC, hardware or deployment acceptance.
- Evidence current: scratch/gacha-safety-1025/full-gate-4d41a3c/affected-build.log and affected-build-details.log; firmware-artifacts.json records all5 binary hashes/sizes. Gacha image is unflashed.

## Next
1. Open and attach sourcePR with exact8da full certificate, approvals and3crowd retry qualification.
2. Coordinate scoped root integration separately; preserve newer live metadata and all unrelated dirty source/user data. No deployment or service restart.
3. Hardware USER-NOTREADY: no device reads/retries, motion, flash, network, trim/calibration, camera or Hub/service actions.

## Blocked
No software test blocker; sourcePR/integration pending. Hardware acceptance remains explicitly paused by human; source fullpass is not physical acceptance.

## File status
Baseline:e30bc36; preserved Gemini2bd3299/8530dbf/6db1aeb, rules9b57ee9, Help8064292. Only owned changes below; imported Help design attributed above.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| firmware/config/esp32_hardware_gacha_module.h | Bounded timing/default constants | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | 0dc1d06 |
| firmware/src/modules/gacha/GachaMath.h | Nonblocking bounded CenterMotion | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 0dc1d06 |
| firmware/src/modules/gacha/GachaModule.h | Async jobs/phases, progress, learned advance | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 4d41a3c |
| firmware/src/modules/gacha/GachaModule.cpp | Bounded jobs/STOP/args/per-pocket/Hall verification, timedfallback, already-at-Hall HOME result | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 4d41a3c |
| firmware/config/commands.json | Preserve latest features; truthful async Hall contract | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | fa6c986 |
| firmware/COMMANDS.md | Limits/progress/timed result, no mass/centre guarantee | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | 4d41a3c |
| apps/gacha/index.html | Parse fixes, motion status, per-pocket units, STOP | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | 9e46ad0 |
| apps/gacha/motion.js | Separate async polling class | verified; landing pending | full8258/0@8da,978stable; actual Hub/fake browser24/0 incl HTTP200 ERRbusy; error-priority sabotage1/1 caught/restored; affected1667/0 | 4d41a3c |
| qc/checks/check_gacha_motion.py | Compile actual source methods/commands with fake IO | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 4d41a3c |
| qc/data/gacha_motion.cpp | Motor/deadline/args/calib/drain/test/default/no-rock regressions | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 4d41a3c |
| qc/checks/check_gacha_ui.py | Actual page->Hub->fake board;8magnets/4pockets | verified; landing pending | full8258/0@8da,978stable; actual Hub/fake browser24/0 incl HTTP200 ERRbusy; error-priority sabotage1/1 caught/restored; affected1667/0 | 4d41a3c |
| qc/checks/check_remote_scripts.py | Parse shipped inline/helper JS | verified; landing pending | full8258/0@8da,978stable; parse4/0 and quote sabotage caught; affected1667/0 | fa6c986 |
| docs/urdf_nong.md | Separate native zero/Studio zero/90/HOME | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | 90847e8 |
| handoff/tasks/gacha-safety-1024.md | Reconciled per-file current state | pending integration | metadata-only current checkpoint; gate8da certificate recorded, no rerun for prose | this checkpoint |
| firmware/src/web/WebUI.h | Preserve root20line module-page features, truthful Hall/progress | verified; landing pending | full8258/0@8da,978stable; approved runtime4d41a3c; current affected+actual firmware/native1667/0 | 9e46ad0 |
| qc/data/gacha_config.cpp | Focused actual-GCFG accepted/rejected/CLEAR/polarity reference cases | verified; landing pending | full8258/0@8da,978stable; actual-source native195/0; restored config/default5/5 + prior native proofs; actual firmware builds in1667/0 | 4d41a3c |
| qc/checks/check_packing_list.py | Resolve only canonical live plan, not stale published worktree copy | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| qc/checks/check_tools_list.py | Restore manifest probe original bytes | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| qc/checks/check_themes.py | Restore theme probe original bytes | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| tools/sabotage.py | Always restore original source bytes | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| qc/checks/check_dev_tools.py | Actual byte comparison for sabotage cleanup | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| qc/checks/check_qc_probe_integrity.py | Stale published plan + CRLF/exception probe regressions | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |
| qc/run_qc.py | Complete Gacha journey in existing SOLO isolation lane | verified; landing pending | full8258/0@8da,978stable; approved f037d3a; real325/0, integrity5/5 restored, exact3source bytes | f037d3a |

## Evidence / preserved data
- Earlier dc5a953/input82527a snapshot stays historical under scratch/gacha-safety-1025/candidate-cf23113/. Current successful gate folder is full-gate-4d41a3c-r2/; first failed folder full-gate-4d41a3c/ remains immutable; runtime source approved4d41a3c.
- Existing qc_chain_proj.json/settings_shared.json and old reports remain unstaged/unpromoted QC/user data. EOL-only status noise in generated files has no content diff. Root other-owner files and ordinary services preserved.
- Main may receive later Gemini own-handoff prose only; no additional full/affected rerun solely for that metadata, per explicit main instruction. Keep gate source frozen during run.

- First-gate exact evidence: full-gate-4d41a3c/full.log,full-details.log,full-result.json,inputs-before/after.json,input-drift-analysis.json. Gacha crowd failed with noGUI marks, then2/2 greenalone; startup/resource explanation is inference, not proven product fault. All assertions retained.

- Latest verification evidence: gate-integrity-focused-1025.log144/0, gate-integrity-real-probes-1025.log325/0, probe-restoration-result-1025.json all_exacttrue, sabotage-integrity-1025.log5/5 caught/restored. These repair verification only; original product runtime4d remains unchanged. R2 full evidence in scratch/gacha-safety-1025/full-gate-4d41a3c-r2/{freeze,inputs-before,inputs-after,full-result,receipt,firmware-artifacts}.json plus full.log/full-details.log. Later handoff prose is metadata-only, not a new full certificate.

- Existing main reviewed exactf037d3a and20d66fe; approved for r2 with all assertions/timeouts intact. Current metadata checkpoint carries generation/ledgers only. Product runtime4d41a3c unchanged.
