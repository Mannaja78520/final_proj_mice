# Gacha safety fixes — frozen for existing independent review

Owner: codex:10231901-f6cc
Updated: 2026-10-25T09:11:23+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: this checkpoint; functional source9e46ad0, prior metadata cf23113
Plan: A47-20 (robot); A0-35 audit done

## Goal
Preserve latest Gemini features while making Gacha motion bounded/nonblocking, STOP effective and completion truthful. No calibration/CAD/physical-pose changes.

## Doing now
Human/main resumed review. After explicit Lab09:06 release, claim software-only final review fixes: invalidate logical pocket reference on accepted layout/reference changes/CLEAR; refresh Hall on polarity change, preserve rejected-config state; actual whole-GCFG branch regression. Correct GTEST documented default1 with omitted-arg production assertion, and prefer actual board ERRbusy in GachaMotion.error with real Hub/fake browser refusal. Add focused fixture; then deliberate failures/restored green, affected builds and exact new review before fullgate. No hardware/runtime/userdata writes.

## Facts found
- Frozen runtime-source basis: late24Oct C++AAAE3506 and root WebUI SHA1e3b2e10278a692769fbe439a9dac40679dfe614e82dc7d3dba6fd12b6b1aa5b. Intake/GCALIB/GTEST/GDRAIN and module-page controls preserved.
- Center/calibration use debounced Hall at rest, bounded timers and STOP. No-rock, pause0 and legacysettle also verify Hall. Explicit fallback reports timed and invalidates position; already-at-Hall HOME resets stale motion_result.
- GTEST verifies each pocket; GSPIN validates signed tokens/bounds before multiplication. UI one-pocket command is GSPIN1 at8magnets/4slots. Hall does not prove mass, geometric centre or a dropped capsule.
- Original quick5716 and5735 are proven --quick in raw Gemini transcripts, not full; old device4cycle result had HallFalse2/4. Nong11config arrays match earlier snapshots, physical pose unmeasured. User handles/deferred elbowtrim.

## Done
- Actual firmware5environments + native logic/build69/0 (61.5s). Gacha image1416752bytes,71.7% flash; artifacts/source hashes recorded. Compiled, not flashed.
- Current affected suite1566/0 (50.3s): both Gacha pages, TV, idle Studio, actual private CAD, Help,360–1920layout, contracts/generators/rules. Functional9e46ad0 unchanged.
- Across iteration27/27 deliberate regressions caught and restoredgreen: native9+HOME1,syntax1,HubUI2,TV4,Studio6,Help2,moduleUI2. Current affected suite ran after all restores.
- Per-file state pending means review/full/landing remains, not an unresolved test failure. Earlier203/637 batches are historical; use latest1566 and69 evidence.

## Next
1. Human resumes existing main chat01a1689b-5608-7123-b8c2-a6f489b5b675; independent review of exact functional9e46ad0 plus frozen checkpoint. No approval exists yet.
2. Apply actual findings in this branch, recheck affected behavior/build and update ledgers; freeze current source/input hashes.
3. Run full QC once on the exact stable candidate, with source fingerprints before/after and fresh no-driver inventory. Then source PR/integration only with required review/authorization.
4. Physical/runtime deployment is separate: no flash, Hub restart, camera, HOME/motion/RELAX/calibration command or trim write authorized by this task.

## Blocked
Independent review found3final deltas; authorized corrections in progress. Full QC NOT RUN for this candidate; no source promotion/PR/deploy. Physical elbow centering remains user-deferred and unpassed. Software-only driver lease reclaimed after Lab09:06 release; no transfer of physical rights.

## File status
Baseline:e30bc36; preserved Gemini2bd3299/8530dbf/6db1aeb, rules9b57ee9 and Help8064292. One latest row per owned file; imported owner597a design is attributed above.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| firmware/config/esp32_hardware_gacha_module.h | Bounded timing/default constants | pending | current actual-source native164/0; firmware/native build69/0; iterative native/HOME10 sabotages caught; full/review pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaMath.h | Nonblocking bounded CenterMotion | pending | current actual-source native164/0; firmware/native build69/0; iterative native/HOME10 sabotages caught; full/review pending | 0dc1d06 |
| firmware/src/modules/gacha/GachaModule.h | Async jobs/phases, progress, learned advance | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| firmware/src/modules/gacha/GachaModule.cpp | Bounded jobs/STOP/args/per-pocket/Hall verification, timedfallback, already-at-Hall HOME result | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| firmware/config/commands.json | Preserve latest features; truthful async Hall contract | pending | current affected1566/0 (docs/contracts/generators/layout/actual CAD); full/review pending | fa6c986 |
| firmware/COMMANDS.md | Limits/progress/timed result, no mass/centre guarantee | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| apps/gacha/index.html | Parse fixes, motion status, per-pocket units, STOP | pending | current both-page browser24/0 + syntax4/0 within affected1566/0; HubUI2/moduleUI2 sabotages caught; full/review pending | 9e46ad0 |
| apps/gacha/motion.js | Separate async polling class | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| qc/checks/check_gacha_motion.py | Compile actual source methods/commands with fake IO | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| qc/data/gacha_motion.cpp | Motor/deadline/args/calib/drain/test/default/no-rock regressions | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| qc/checks/check_gacha_ui.py | Actual page->Hub->fake board;8magnets/4pockets | pending | final review correction planned; prior9e46ad0 proof historical, rerun required | next checkpoint |
| qc/checks/check_remote_scripts.py | Parse shipped inline/helper JS | pending | current parse4/0 and deliberate broken quote caught; affected1566/0; full/review pending | fa6c986 |
| docs/urdf_nong.md | Separate native zero/Studio zero/90/HOME | done | independent source review earlier; no geometry edits | 90847e8 |
| handoff/tasks/gacha-safety-1024.md | Reconciled per-file current state | pending | current affected1566/0 (docs/contracts/generators/layout/actual CAD); full/review pending | this checkpoint |
| firmware/src/web/WebUI.h | Preserve root20line module-page features, truthful Hall/progress | pending | current both-page browser24/0 + syntax4/0 within affected1566/0; HubUI2/moduleUI2 sabotages caught; full/review pending | 9e46ad0 |

## Evidence / preserved data
- Current logs/artifact manifest and27sabotage proofs: scratch/continue-urdf-1023/*1025*; frozen review package: scratch/gacha-safety-1025/candidate-cf23113/ in own tree and root.
- nong/main_python_set_nong/projects/qc_chain_proj.json, settings_shared.json and old reports remain preexisting/other QC data, unstaged/unpromoted. Camera/Voice and generated-header EOL-only status noise has no content diff; not owned changes.
- No actual physical centering/drop/name-recognition proof from these simulated checks. Ordinary Hub/friend/Voice processes were left alone.

- Review findings: config keeps stale pos_known/pos after layout/CLEAR; GTEST actually defaults1, not slots; API200 generic says hides board ERRbusy. Earlier1566/69/27 proof applies to functional9e46ad0; changed files need new proof.
| qc/data/gacha_config.cpp | Focused actual-GCFG accepted/rejected/CLEAR/polarity reference cases | pending | planned before code; native check and deliberate regressions required | uncommitted |
