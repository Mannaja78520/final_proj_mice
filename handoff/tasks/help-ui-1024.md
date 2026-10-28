# Help matches the actual prize and recognition screens

Owner: codex:10281554-9dc6
Updated: 2026-10-28 16:08 +0700
Branch: codex/help-ui-1024
Tree: E:/final_proj/mice/code/.staging-help-ui-1024
Last commit: e2d0346 (HEAD and local origin/codex/help-ui-1024; last pushed by coordinator; Round 2 changes uncommitted)
Plan: A48-15

## Goal
Human: Help is broken and confusing; prize app and FaceReg differ from Help.
Human correction: ONE fixed Hall at Receive; FOUR magnets on wheel; Drop has no Hall; Receive and Drop are on the same side.
Round 2: finish remaining offline work in this tree only; coordinator owns Git writes and publication.

## Doing now
Round 2 offline work and final diff inspection finished; awaiting coordinator review/commit/push. No service, browser, hardware or full QC driver was run. No shared resource claim taken or released. All Round 2 edits remain uncommitted as instructed.

## File status
Historical source baseline: 2bd3299; original Help implementation e79ea8a is included in merged main. Round 2 baseline: e2d0346, initially clean. main...HEAD differs only in this task file. Round 2 tracked edits are exactly docs/systems/agents.md and this task; earlier source rows below are retained for continuity. No other owner's source edited.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| main_python/web/help/parts/gacha.html | Actual tabs; one Receive Hall/four magnets; bounded commands | merged; no Round 2 edit | current Help output equality; earlier static preview is historical, no hardware | e2d0346 (merged) |
| main_python/web/help/parts/faces.html | Actual three tabs and greeting steps | merged; no Round 2 edit | current Help output equality; browser regression not run this round | e2d0346 (merged) |
| main_python/web/help/parts/search.js | Search full topic without neighbour links | merged; no Round 2 edit | output equality; browser/search sabotage pending | e2d0346 (merged) |
| main_python/web/help/style.css | Hide technical paths; contain phone overflow | merged; no Round 2 edit | output equality; current browser/layout checks pending | e2d0346 (merged) |
| main_python/web/help.html | Built Help | unchanged | source/output equality 1/1; Help links 26/26; builder 14/14 | e2d0346 (merged) |
| qc/checks/check_help_topics.py | Content/browser regressions | unchanged; full execution blocked | Python syntax 1/1; hub/browser portion not run | e2d0346 (merged) |
| docs/systems/hub-web.md | Generated check index | unchanged | check_systems 13/13 | e2d0346 (merged) |
| docs/systems/qc.md | Generated file index | unchanged; main resolved stale index | check_systems 13/13 | e2d0346 (merged) |
| docs/systems/agents.md | Remove missing task from generated inventory; 38 to 37 files | done; coordinator review pending | check_systems 13/13; generated-only diff; authored text/line endings preserved | uncommitted |
| handoff/tasks/help-ui-1024.md | Round 2 scope, current evidence and remaining boundaries | done | check_handoff_first 45/45; git diff --check clean | uncommitted |
| scratch/help-ui-1024/offline-round2.log | Current offline evidence, ignored | done | 100 passed, 0 failed, 0 crashes | uncommitted; do not commit |

Evidence stays in this tree's ignored scratch/help-ui-1024/offline-round2.log. Earlier offline-checks.log and root preview evidence are historical and do not cover the merged tree. Root PLAN/BRIDGE, runtime data and private files were not edited.

## Facts found
- docs/systems/agents.md:19 now indexes 37 existing files. The generated list still named absent handoff/tasks/usability-review-1026.md after merge; removing that stale entry fixes the sole remaining map error.
- tools/systems.py:164 validates source ownership/header freshness; :214 rebuilds headers from docs/systems.json while preserving authored prefixes. Builder emits LF, so original per-file line endings were restored afterward.
- qc/checks/check_help_links.py:35 checks Help anchors offline; qc/checks/check_build_web.py:12 uses temporary build fixtures. qc/lib/qc.py:384 runs selected checks without the full driver.
- qc/checks/check_help_topics.py:38-40 requires a browser and starts a hub. Its complete regression and search sabotage need a separately authorized round; Python parsing is not behavior proof.
- tools/build_web.py:38-55 renders Help in memory, allowing source/output equality without rewriting other web pages.
- main_python/web/help/parts/gacha.html:51-66 documents one fixed Receive Hall, no Drop Hall, same-side stations and four magnets. The original misleading diagram was corrected before this round.
- main_python/web/help/parts/faces.html:14-33 names Open it and What the rig says and places Move/on on each camera row. Earlier incorrect captions are historical, not current findings.
- tools/plan.py:62-79 redirects staging progress writes to the root unless MICE_PLAN is overridden. Root writes are forbidden; local merged PLAN has no A48-15. Coordinator must reconcile the real plan, not create a duplicate staging plan.

## Done
- Final diff inspected: exactly two tracked edits (agents.md and this task), no untracked source, no whitespace errors. Scratch evidence remains ignored. No Git metadata writes; all changes left uncommitted.
- Round 2 read HANDOFF, Codex entry AGENTS, this task, CLAUDE, coordination and relevant skills. Retained the existing named task owner under the user's continuation authority.
- Read-only Git reconciliation: main 023c644 is an ancestor of HEAD e2d0346, matching local origin/codex/help-ui-1024. Coordinator committed the earlier handoff as fe206c9 and merged/pushed main. No merge/add/commit/push attempted this round.
- Diagnosed the remaining stale header with tools/systems.py verify. Ran python tools/systems.py build; only agents.md content changed. All 35 other header/index files remained byte-identical. Authored prefixes and original line endings were preserved.
- Current merged-tree focused results: check_help_links 26/26, check_build_web 14/14, check_handoff_first 45/45, check_systems 13/13. Help source/output equality 1/1 and regression Python syntax 1/1. Total 100 passed, 0 failed, 0 crashes; direct qc.run_check only. Evidence: scratch/help-ui-1024/offline-round2.log.
- Test temporary files stayed inside this tree's ignored scratch/help-ui-1024. Existing builder/system negative fixtures passed. No test was disabled; full browser/search sabotage was not run.
- Prior implementation e79ea8a corrected menus, geometry, full-topic search and hidden technical paths. It had manual static preview evidence; that historical evidence is not a current browser gate. Source is already included in main and was not changed this round.

## Next
1. Coordinator reviews and commits/pushes only docs/systems/agents.md and handoff/tasks/help-ui-1024.md. Keep scratch evidence ignored. Do not reapply already merged Help source.
2. Coordinator reconciles A48-15 in the real plan and existing independent-review status for the merged source.
3. In a separately authorized round, run complete check_help_topics, browser/search sabotage and required full QC; coordinate any remaining prize-app usability work with its owner.

## Blocked
- Git merge/add/commit/push prohibited by Round 2 instructions; coordinator handles publication. Earlier lock/credential failures were not retried. Last pushed commit recorded locally is e2d0346.
- Complete Help browser regression/sabotage and full QC are outside current authorization. Hardware, robot, ESP32/USB, camera/person checks, live services, MiceHub.exe rebuild and deployment also remain out of scope; no such evidence claimed.
- Root PLAN/BRIDGE/shared mutex writes are forbidden. A48-15 reconciliation and shared coordination bookkeeping remain with the coordinator.
- Existing independent review and original prize-app usability acceptance need their owners. No new review, full gate, integration or deployment approval claimed.
