# Fix and verify latest Gemini UI/OOP work

Owner: codex:10241515-audit
Updated: 2026-10-25T22:45:12.632996+07:00
Branch: codex/gemini-ui-fixes-1025
Tree: E:/final_proj/mice/code/.staging-gemini-ui-fixes-1025
Last commit: this checkpoint; runtimefbceae6; publicmetadata merged6da26d6
Plan: A48-13; related Gemini A48-17

## Goal
User: independently fix discovered issues and search all latest Gemini work for further problems. Preserve user data/calibration; no realhardware while user-notready.

## Doing now
PR81 opened; independent final runtime review approved exact6rawhashes (source-review.json). Broad affected24checks+all5actualfirmware builds1028/0 in231.8s, metadata86/0 after replaying publicmetadata closuree961 into6da26d6; runtime rawhashes unchanged. Focused57/0, realEdgejourney58/0; iterative12reversions caught/restored. Freeze final source inputs now and run actual full with realprivateCAD export through existing harness; no source edits while running. RootdirtyStudio/config/userdata/privateCAD preserved, no runtime/deploy/hardware actions. Old301/0 selected-only evidence corrected; newfull stillpending.

## File status
Baseline: ffff102; unrelated rootdirtywork not owned. Planned exactpaths below; remove unchanged rows or label reviewed-only at final reconciliation.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/gacha/index.html | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| apps/gacha/presets.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| apps/tv/index.html | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| apps/voice/app.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| apps/voice/index.html | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| docs/systems/agents.md | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | 6da26d6 |
| docs/systems/app-gacha.md | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| docs/systems/qc.md | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| docs/systems/shared-web.md | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | e7d20ca |
| handoff/tasks/gemini-ui-fixes-1025.md | Own per-file task | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | this checkpoint |
| handoff/tasks/ui-ux-overhaul-1025.md | Correct historical301selected-notFull claim; originalowner retained | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/gacha.py | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/web/help.html | Generated inventory or web bundle | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/web/help/parts/gacha.html | Help parity for corrected operation | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/web/help/parts/hub.html | Help parity for corrected operation | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/web/help/parts/tv.html | Help parity for corrected operation | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| main_python/web/help/parts/voice.html | Help parity for corrected operation | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| qc/checks/check_app_browser.py | Regression coverage for actual production behavior | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| qc/checks/check_app_lifecycle.py | Regression coverage for actual production behavior | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| qc/checks/check_gacha_event_order.py | Regression coverage for actual production behavior | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| qc/checks/check_remote_scripts.py | Regression coverage for actual production behavior | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| qc/data/app_lifecycle.js | Regression coverage for actual production behavior | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| shared/web/mice.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | affected1028/0; metadata86/0; reviewed6runtimehashes; full not run | fbceae6 |
| scratch/gemini-ui-fixes-1025/source-review.json | Independent runtime review + exact6rawhashes | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/regression-reversions.json | 9iterative original-reversion cases | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/extra-regression-reversions.json | 3extra head/metadata/backend cases | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/focused-final.log | Actual57/0 focused rawlog | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |

## Facts found
- Prior8258full@8da predates newGemini UI/OOP and does not cover this source.
- NewGemini30rowledger matches30Gitpaths; native301/0 was sixselectedchecks, notFull. Correct factual claim within authorized scope.
- RootdirtyStudio/layout/tests/configs/executable/userdata preserved; sourcebaselineffff102 only. RootPR80remoteclosure exists but rootnewGemini commits prevent blind oldff.
- Reviewer proof: root scratch/nong-gemini-audit-1024/latest-ui-method-proof-1025.json. Voice/TV baseline645 passed; newcurrent reproduces failures. No realnetwork/device.

## Done
- Prior review784dc16 plus broad read-only audit found stale machine/Sheet aliases, theme picker sync, TV deniedstorage. Browser additionally caught eager Voice Status beforeDOM. Fixes preserve loaded metadata and serialize timed-out event operations. No additional concrete issue in other reviewed30files or rootdirtyStudio layout.
- Focused57/0, actualEdge58/0, iterative12reversions caught/restored; independent source review approved6runtime hashes. Hardware untouched; current full pending.

## Next
1. Add meaningful integration regressions; demonstrate failures on oldsource, apply narrow OOP fixes and inspect finaldiff.
2. Review remaining30files + relevant dirtyStudio source; confirm and fix concrete findings, preserve unrelated data.
3. Actual full gate on immutable source, then update PR81 with exact certificate, scoped root integration preserving dirtywork, no runtime cutover.

## Blocked
Realhardware remains USER-NOTREADY. No software blocker; source/QCdriver lease main only. No rootruntime cutover authorized by softwaretests.
