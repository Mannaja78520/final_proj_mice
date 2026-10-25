# Fix and verify latest Gemini UI/OOP work

Owner: codex:10241515-audit
Updated: 2026-10-25T22:32:36.264397+07:00
Branch: codex/gemini-ui-fixes-1025
Tree: E:/final_proj/mice/code/.staging-gemini-ui-fixes-1025
Last commit: this checkpoint
Plan: A48-13; related Gemini A48-17

## Goal
User: independently fix discovered issues and search all latest Gemini work for further problems. Preserve user data/calibration; no realhardware while user-notready.

## Doing now
Confirmed UI/OOP regressions fixed; independent same-provider read-only source review complete with no remaining actionable issue. Six runtime rawhashes frozen in scratch/gemini-ui-fixes-1025/source-review.json. ActualEdge+production-method/syntax58/0 after Voice headbootstrap fix; current production-method/backend/syntax57/0. Iterative12deliberate reversions caught/restored byteexact. Now run broad affected browser/contracts/layout/all5firmware checks, then stableinput fullgate; no runtime edits unless a genuine failure requires them. No rootsource/runtime/hardware changes; rootdirtyStudio layout reviewed and preserved.

## File status
Baseline: ffff102; unrelated rootdirtywork not owned. Planned exactpaths below; remove unchanged rows or label reviewed-only at final reconciliation.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/gacha/index.html | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| apps/gacha/presets.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| apps/tv/index.html | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| apps/voice/app.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| apps/voice/index.html | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| docs/systems/agents.md | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| docs/systems/app-gacha.md | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| docs/systems/qc.md | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| docs/systems/shared-web.md | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| handoff/tasks/gemini-ui-fixes-1025.md | Own per-file task | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| handoff/tasks/ui-ux-overhaul-1025.md | Correct historical301selected-notFull claim; originalowner retained | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/gacha.py | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/web/help.html | Generated inventory or web bundle | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/web/help/parts/gacha.html | Help parity for corrected operation | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/web/help/parts/hub.html | Help parity for corrected operation | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/web/help/parts/tv.html | Help parity for corrected operation | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| main_python/web/help/parts/voice.html | Help parity for corrected operation | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| qc/checks/check_app_browser.py | Regression coverage for actual production behavior | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| qc/checks/check_app_lifecycle.py | Regression coverage for actual production behavior | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| qc/checks/check_gacha_event_order.py | Regression coverage for actual production behavior | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| qc/checks/check_remote_scripts.py | Regression coverage for actual production behavior | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| qc/data/app_lifecycle.js | Regression coverage for actual production behavior | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
| shared/web/mice.js | Confirmed lifecycle/state/event-order fix | implemented; full pending | focused57/0; Edge58/0; review sourcehashes; full not run | uncommitted |
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
3. Affected browser/contracts/layout/build checks, independent finaldelta review, stableinput fullgate, PR/integration under exact claims.

## Blocked
Realhardware remains USER-NOTREADY. No software blocker; source/QCdriver lease main only. No rootruntime cutover authorized by softwaretests.
