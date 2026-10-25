# Nong acceptance and independent Gemini/source audit

Owner: codex:10241515-audit
Updated: 2026-10-26T01:23:18.533322+07:00
Branch: codex/nong-gemini-audit-1024
Tree: E:/final_proj/mice/code/.staging-nong-gemini-audit-1024
Last commit: this checkpoint; softwarePR81merged69fd19ed
Plan: A48-13 (robot); related A47-20/A48-14 source, A45-11 Lab, A48-16 rules

## Goal
Finish the authorized pending Gemini/Claude work, independently review exact source/evidence and test every implemented Nong feature where possible. Preserve manual trim and distinguish software proof from real-device acceptance.

## Doing now
26Oct user asks residual bugs/odd behavior, useful additions for each subsystem and whether PC/ESP32 hardware is fully utilized. Read-only current-source/config/evidence assessment only; record facts vs unmeasured gaps vs optional improvements. No source/runtime edits, load tests or real-device access; previous accepted PR81/full evidence retained, physical USER-NOTREADY and elbowtrim deferred. Wide firmware/Studio/UI reading delegated to existing audit_latest_ui; main reviews PC Voice/Face/resource evidence. Update this ledger/private assessment and ownplan only after evidence.

## File status
Baseline: own9351b2c; reviewed runtime files belong to source owner and are not main's changes.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/nong-gemini-audit-1024.md | Current review/status/next; historical detail linked | software accepted; physical userpaused | PR81/root69fd19ed independentlyverified;8335/0 qualifiedgesture retry | this checkpoint |
| scratch/nong-gemini-audit-1024/review-1025.md | Exact independent source review and findings | done, private |978r2rawhashes+receipt exact; runtime/verification source approved | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-method-proof-1025.json | Actual sharedApp/Voice/Gacha/TV regression proof+645 baseline | done, private | 3 current defects reproduced; baselineVoice/TV pass; no realnetwork | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-ledger-proof-1025.json | NewGemini per-file Git coverage | done, private | 30/30 paths;0missing/0wrongcommitpath | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-qc-commands-1025.json | Exact recent nativeGemini QC commands | done, private | selected named checks; no latestfull command | uncommitted, ignored |
| scratch/nong-gemini-audit-1024/latest-ui-301-provenance-1025.json | Actual301/0 provenance | done, private | sixselectedchecks8.7s; handoffFull claim unsupported | uncommitted, ignored |
| docs/PLAN.html | Only own audit notes/status | pending, shared | serialized plan tool; software accepted; physical userpaused | uncommitted, mixed owners |
| docs/plan_state.js | Generated live status | pending, shared | plan tool; preserve other actors | uncommitted, mixed owners |
| docs/BRIDGE.md | Only own metadata/coordination entries | done, shared | final source/driver release recorded | uncommitted, mixed owners |
| scratch/nong-gemini-audit-1024/latest-ui-acceptance-1025.json | Exact latest source/gate/package/integration acceptance | done, private |8335/0; one isolatedretry2/2;3726protectedrawfiles unchanged | uncommitted, ignored |

## Facts found
- Latest source is merged root69fd19ed/PR81. This audit branch carries review metadata only; never promote its older runtime. Final source ledger/history58883c2; exact proofs in latest-ui-acceptance-1025.json.
- Saved Nong HOME=[90,140,90,90,90,40,90,90,90,90.5] predates CAD/Gemini. Native CAD0, Studio0, command90 and savedHOME differ. Controller angles are commands, not physical measured angles.
- USER skipped right elbow trim/centering diagnosis; Lab restored R_EL_P90/STOP, never95 or persistent trim/HOME changes. Do not resume probes, restore oldtrim or demand observations.
- USER25Oct explicitly NOTREADY for realrobot. Lab20cf4c5 checkpoint USER-PAUSED; all physical/COM/camera/QC resources released. New connection alone is not resume consent.
- Lab readiness25Oct: Hub5c3513666e8d healthy/modulesempty; oldNongINFO502, PCdifferentLAN, onlyBluetoothCOM. No current identity/trim read. Details scratch/nong-acceptance-1025/readiness.md/json.
- Prior24Oct32verb+19feature matrix is inventory, not51passes. SDfixture5checks/deletion, combinedspeaker hearing, WAV/UDP/STREAM/web/TALK evidence partial only; phoneMIC/OTA/video/motion/RRT/RELAX/absentNongUSBRS485 unverified.
- Gemini handoff a56c177 now75rows/123lines; compared baselinee30bc36 to actualHEAD:75Gitpaths,0missing,0SHA/path errors. Initial4wrongSHA and19omittedrule/image rows corrected. Rules/templates live + Claude instructions; A48-16 complete. File handoff works; nativeCodex tool/API parity does not transfer to Gemini.
- Gemini raw5716 and5735 results were --quick, not full. Exact5735proof: scratch/nong-gemini-audit-1024/gemini-5735-provenance.json; no oldreceipt accepted for newsource.

## Done / independent review
- LatestUI/OOP: fixed Voice bootstrap/status; checked Gacha preset ordering/acknowledgements/rollback+serialization and instance row metadata; theme picker, TV hidden/storage, overlappingTools. Gate correctness improved without disablingchecks.13iterative reversions caught/restored; affected1028/0 all5firmware, finalfocused186/0, full8335/0 qualifiedgesture retry. Finaldelta and33rootactions independently reviewed.
- Prior9e46ad0: bounded nonblocking Gacha motion/STOP/faults, per-pocket GTEST, strict GSPIN, timedfallback, truthful two UIs; TV selected nativeHOME/telemetry/progress/restart; Studio idle mutation invalidation; reconciled singleReceiveHall Help. Old affected1566/0/build69/0/sabotage27 historical, not final4d41a3c proof.
- Final4d41a3c resolves reference invalidation after validated layout/dir/polarity/CLEAR, preserves rejected/no-op state; corrects GTEST default1 docs; shows real boardERRbusy. Actual command extraction and Hub/fake browser assertions reviewed; focused223/0 log checked; final affected/build1667/0 and33restoredsabotages now checked. No further actionable source finding.
- Source may run fullgate only after all current deliberate regressions restored, builds/affected green, fresh input freeze/no-driver inventory. No additional paid reviewer/model needed. No hardware/deployment approval implied.
- Passive Face takeover after authorusage limit: f1573bc and private readiness report; corePC JSONhealth200/Faceweb200, delivery8123listener but previous APIhealth404. No inference/person/full-load proof or runtime changes. Main passive claim released.

## Next
1. Software fixes/audit/integration complete. Keep realhardware/person acceptance paused until the human explicitly ready; connection alone is not consent. Do not repeat scans/probes while paused.
2. On explicit readiness, use existing Lab A45-11 handoff and32verb+19feature missing-evidence matrix with fresh identity/config; preserve manualtrim/HOME and coordinate one driver. User owns elbowtrim adjustment.
3. Any future runtime deployment needs its own idle/resource claim/current-tree validation; no Hub/service restart under this pause. Isolated EXE is built but not installed/executed.
4. Historical findings/provenance are retained in prior commits and scratch reports. Handoff-first per-file rules remain mandatory for all AIs; historical301/0 selected-notFull corrected.

## Blocked
Realhardware/person/absenttransports USER-PAUSED. LatestGemini software has no remaining confirmed actionable issue in the reviewed scope and passed its currentfull; source integrated. One qualified test reliability issue: check_gestures failed under parallel load but passed alone2/2; preserve that evidence. No live-deployment or physical acceptance claim. No main driver/source/runtime/hardware resources held after finalrelease.
