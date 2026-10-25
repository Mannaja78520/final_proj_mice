# Fix and verify latest Gemini UI/OOP work

Owner: codex:10241515-audit
Updated: 2026-10-25T22:06:43.422522+07:00
Branch: codex/gemini-ui-fixes-1025
Tree: E:/final_proj/mice/code/.staging-gemini-ui-fixes-1025
Last commit: this checkpoint
Plan: A48-13; related Gemini A48-17

## Goal
User: independently fix discovered issues and search all latest Gemini work for further problems. Preserve user data/calibration; no realhardware while user-notready.

## Doing now
Audit exactffff102 30changedfiles and relevant uncommitted rootStudio changes read-only. Fix confirmed Voice getter-only status, unchecked/early-open Gacha preset save, TV hidden/inflight polling, stale Gacha machine/Sheet deletion aliases. Read-only same-provider auditagent per HANDOFF wide-search rule; no agent edits/drivers. Actual no-network production methods + real sharedApp/API integration regressions before affected browser/full checks. No runtime/service/deploy/physical changes.

## File status
Baseline: ffff102; unrelated rootdirtywork not owned. Planned exactpaths below; remove unchanged rows or label reviewed-only at final reconciliation.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/voice/app.js | Fix inherited status access | pending | not run | uncommitted |
| apps/voice/index.html | Generated Voice bundle | pending | not run | uncommitted |
| apps/gacha/index.html | Preset save sequence and instance-owned removal state | pending | not run | uncommitted |
| apps/gacha/presets.js | Checked OOP preset coordinator | pending | not run | uncommitted |
| apps/tv/index.html | Hidden/inflight polling lifecycle | pending | not run | uncommitted |
| shared/web/mice.js | Review theme sync; change only confirmed defects | pending | not run | uncommitted |
| qc/checks/check_app_lifecycle.py | Actual shared/app integration regressions | pending | not run | uncommitted |
| qc/data/app_lifecycle.js | No-network production-method fixtures | pending | not run | uncommitted |
| main_python/web/help/parts/voice.html | Help parity for status behavior | pending | not run | uncommitted |
| main_python/web/help/parts/gacha.html | Truthful preset save/start/remove behavior | pending | not run | uncommitted |
| main_python/web/help/parts/tv.html | Help parity for paused background polling | pending | not run | uncommitted |
| main_python/web/help.html | Generated Help bundle | pending | not run | uncommitted |
| docs/systems/agents.md | Generated task/check inventory | pending | not run | uncommitted |
| docs/systems/qc.md | Generated regression inventory | pending | not run | uncommitted |
| docs/systems/shared-web.md | Generated dependency/check inventory | pending | not run | uncommitted |
| handoff/tasks/gemini-ui-fixes-1025.md | Own task/per-file checkpoint | pending | not run | uncommitted |

## Facts found
- Prior8258full@8da predates newGemini UI/OOP and does not cover this source.
- NewGemini30rowledger matches30Gitpaths; native301/0 was sixselectedchecks, notFull. Correct factual claim within authorized scope.
- RootdirtyStudio/layout/tests/configs/executable/userdata preserved; sourcebaselineffff102 only. RootPR80remoteclosure exists but rootnewGemini commits prevent blind oldff.
- Reviewer proof: root scratch/nong-gemini-audit-1024/latest-ui-method-proof-1025.json. Voice/TV baseline645 passed; newcurrent reproduces failures. No realnetwork/device.

## Done
- Initial read-only review and preexisting regressions recorded by main in784dc16.

## Next
1. Add meaningful integration regressions; demonstrate failures on oldsource, apply narrow OOP fixes and inspect finaldiff.
2. Review remaining30files + relevant dirtyStudio source; confirm and fix concrete findings, preserve unrelated data.
3. Affected browser/contracts/layout/build checks, independent finaldelta review, stableinput fullgate, PR/integration under exact claims.

## Blocked
Realhardware remains USER-NOTREADY. No software blocker; source/QCdriver lease main only. No rootruntime cutover authorized by softwaretests.
