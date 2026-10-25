# Nong acceptance and independent Gemini/source audit

Owner: codex:10241515-audit
Updated: 2026-10-25T21:54:27.805757+07:00
Branch: codex/nong-gemini-audit-1024
Tree: E:/final_proj/mice/code/.staging-nong-gemini-audit-1024
Last commit: this checkpoint; priorf4841d8
Plan: A48-13 (robot); related A47-20/A48-14 source, A45-11 Lab, A48-16 rules

## Goal
Finish the authorized pending Gemini/Claude work, independently review exact source/evidence and test every implemented Nong feature where possible. Preserve manual trim and distinguish software proof from real-device acceptance.

## Doing now
LatestGemini REVIEW COMPLETE, NOT ACCEPTED: exactHEADffff102/runtimee9127bb, baseline645143e;30ledgerrows=30Gitpaths,0missing/0commitpatherrors. Actual methods with realsharedApp/API in isolatedNode (no realnetwork): P1Voice say() assigns getter-only inheritedstatus and throwsTypeError (baseline645passes); P1Gacha saveAllPreset reports success after all4HTTP403/okfalse replies and continues; P2TV latehidden reply recreates1500ms polling (baseline645noschedule). Also301/0 is6selectedchecks per actualnativeQCcommand, NOT full as handoffStep5claims; old8258@8da not applicable. Evidence in scratch/nong-gemini-audit-1024/latest-ui-*.json. Source unmodified, hardware USER-NOTREADY. Main metadata/report only, releases after checkpoint.

## File status
Baseline: own9351b2c; reviewed runtime files belong to source owner and are not main's changes.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/nong-gemini-audit-1024.md | Current review/status/next; historical detail linked | latest review failed; fixes pending | priorPR79 verified; latestffff102 three functional regressions reproduced | this checkpoint |
| scratch/nong-gemini-audit-1024/review-1025.md | Exact independent source review and findings | done, private |978r2rawhashes+receipt exact; runtime/verification source approved | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-method-proof-1025.json | Actual sharedApp/Voice/Gacha/TV regression proof+645 baseline | done, private | 3 current defects reproduced; baselineVoice/TV pass; no realnetwork | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-ledger-proof-1025.json | NewGemini per-file Git coverage | done, private | 30/30 paths;0missing/0wrongcommitpath | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-qc-commands-1025.json | Exact recent nativeGemini QC commands | done, private | selected named checks; no latestfull command | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-301-provenance-1025.json | Actual301/0 provenance | done, private | sixselectedchecks8.7s; handoffFull claim unsupported | uncommitted, ignored |
| docs/PLAN.html | Only own audit notes/status | pending, shared | serialized plan tool; latest review findings open; physical userpaused | uncommitted, mixed owners |
| docs/plan_state.js | Generated live status | pending, shared | plan tool; preserve other actors | uncommitted, mixed owners |
| docs/BRIDGE.md | Only own metadata/coordination entries | done, shared | mutex/release recorded; no main driver | uncommitted, mixed owners |

## Facts found
- Saved Nong HOME=[90,140,90,90,90,40,90,90,90,90.5] predates CAD/Gemini. Native CAD0, Studio0, command90 and savedHOME differ. Controller angles are commands, not physical measured angles.
- USER skipped right elbow trim/centering diagnosis; Lab restored R_EL_P90/STOP, never95 or persistent trim/HOME changes. Do not resume probes, restore oldtrim or demand observations.
- USER25Oct explicitly NOTREADY for realrobot. Lab20cf4c5 checkpoint USER-PAUSED; all physical/COM/camera/QC resources released. New connection alone is not resume consent.
- Lab readiness25Oct: Hub5c3513666e8d healthy/modulesempty; oldNongINFO502, PCdifferentLAN, onlyBluetoothCOM. No current identity/trim read. Details scratch/nong-acceptance-1025/readiness.md/json.
- Prior24Oct32verb+19feature matrix is inventory, not51passes. SDfixture5checks/deletion, combinedspeaker hearing, WAV/UDP/STREAM/web/TALK evidence partial only; phoneMIC/OTA/video/motion/RRT/RELAX/absentNongUSBRS485 unverified.
- Gemini handoff a56c177 now75rows/123lines; compared baselinee30bc36 to actualHEAD:75Gitpaths,0missing,0SHA/path errors. Initial4wrongSHA and19omittedrule/image rows corrected. Rules/templates live + Claude instructions; A48-16 complete. File handoff works; nativeCodex tool/API parity does not transfer to Gemini.
- Gemini raw5716 and5735 results were --quick, not full. Exact5735proof: scratch/nong-gemini-audit-1024/gemini-5735-provenance.json; no oldreceipt accepted for newsource.

## Done / independent review
- Prior9e46ad0: bounded nonblocking Gacha motion/STOP/faults, per-pocket GTEST, strict GSPIN, timedfallback, truthful two UIs; TV selected nativeHOME/telemetry/progress/restart; Studio idle mutation invalidation; reconciled singleReceiveHall Help. Old affected1566/0/build69/0/sabotage27 historical, not final4d41a3c proof.
- Final4d41a3c resolves reference invalidation after validated layout/dir/polarity/CLEAR, preserves rejected/no-op state; corrects GTEST default1 docs; shows real boardERRbusy. Actual command extraction and Hub/fake browser assertions reviewed; focused223/0 log checked; final affected/build1667/0 and33restoredsabotages now checked. No further actionable source finding.
- Source may run fullgate only after all current deliberate regressions restored, builds/affected green, fresh input freeze/no-driver inventory. No additional paid reviewer/model needed. No hardware/deployment approval implied.
- Passive Face takeover after authorusage limit: f1573bc and private readiness report; corePC JSONhealth200/Faceweb200, delivery8123listener but previous APIhealth404. No inference/person/full-load proof or runtime changes. Main passive claim released.

## Next
1. Fix latest3reproduced regressions under a source owner: Voice getter-onlystatus, Gacha responsevalidation/openafterallsaves, TV hidden/inflight polling. Add integration regressions using realsharedApp/API; affectedchecks then current fullgate required. Correct latestGemini301Full claim to selected checks.
2. Software PR79+rootintegration complete. Any later runtime deployment needs separate idle/resource claim and relevant current-tree checks; no deploy/restart under hardware pause.
3. Keep physical tests paused until human explicitly ready; then fresh identity/config preserving trim and coordinated missing-feature matrix, never reuse staleacceptance.
4. Historical reasoning: scratch/nong-gemini-audit-1024/latest-gemini-review.md and candidate-backend-review.md; current review-1025.md. Full chronology is in prior task commits, not repeated here.

## Blocked
Realhardware acceptance USER-PAUSED; phone/person/absenttransports need actual prerequisites. LatestGemini UI/OOP NOT accepted:3reproducedregressions and unsupportedFull301 claim. Originalsourceowner hitusage limit after remotePR80metadata merge; root has newerGemini commits, preserve them and do not blindff oldclosure. Not all work complete. No main process or testdriver held.
