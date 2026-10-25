# Fix and verify latest Gemini UI/OOP work

Owner: codex:10241515-audit
Updated: 2026-10-25T23:15:45.738615+07:00
Branch: codex/gemini-ui-fixes-1025
Tree: E:/final_proj/mice/code/.staging-gemini-ui-fixes-1025
Last commit: this checkpoint; runtimefbceae6; publicmetadata merged6da26d6
Plan: A48-13; related Gemini A48-17

## Goal
User: independently fix discovered issues and search all latest Gemini work for further problems. Preserve user data/calibration; no realhardware while user-notready.

## Doing now
Final immutable full5a6231d passed8335/0 in570.2s, no crowd retry.983source hashes stable fp17cd6b3964cc9b1732ffa1e4b38c01b3e23c3b3490ad5278797b098843ef4374;20privateCAD hashes unchanged. Independent actualdelta reviewed;13iterative reversions caught/restored. Rebuild EXE in isolated scratch via spec and inspect archive without executing it; then metadata closure/PR81 merge/scoped rootintegration. Preserve all dirtyroot bytes; hardware/userdata/runtime unchanged.

## File status
Baseline: ffff102; unrelated rootdirtywork not owned. Planned exactpaths below; remove unchanged rows or label reviewed-only at final reconciliation.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/gacha/index.html | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| apps/gacha/presets.js | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| apps/tv/index.html | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| apps/voice/app.js | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| apps/voice/index.html | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| docs/systems/agents.md | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | 6da26d6 |
| docs/systems/app-gacha.md | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| docs/systems/qc.md | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| docs/systems/shared-web.md | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | e7d20ca |
| handoff/tasks/gemini-ui-fixes-1025.md | Own per-file task | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | this checkpoint |
| handoff/tasks/ui-ux-overhaul-1025.md | Correct historical301selected-notFull claim; originalowner retained | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/gacha.py | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/web/help.html | Generated inventory or web bundle | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/web/help/parts/gacha.html | Help parity for corrected operation | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/web/help/parts/hub.html | Help parity for corrected operation | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/web/help/parts/tv.html | Help parity for corrected operation | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| main_python/web/help/parts/voice.html | Help parity for corrected operation | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| qc/checks/check_app_browser.py | Regression coverage for actual production behavior | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| qc/checks/check_app_lifecycle.py | Regression coverage for actual production behavior | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| qc/checks/check_gacha_event_order.py | Regression coverage for actual production behavior | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| qc/checks/check_remote_scripts.py | Regression coverage for actual production behavior | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| qc/data/app_lifecycle.js | Regression coverage for actual production behavior | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| shared/web/mice.js | Confirmed lifecycle/state/event-order fix | verified software | full8335/0@5a6231d; stable983inputs; hardware not run | fbceae6 |
| scratch/gemini-ui-fixes-1025/source-review.json | Independent runtime review + exact6rawhashes | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/regression-reversions.json | 9iterative original-reversion cases | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/extra-regression-reversions.json | 3extra head/metadata/backend cases | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |
| scratch/gemini-ui-fixes-1025/focused-final.log | Actual57/0 focused rawlog | done, private | exact saved evidence, no hardware proof | uncommitted, ignored |

| main_python/web/home/parts/tools.js | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| main_python/web/hub.html | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| qc/checks/check_designer_first.py | Type operand/visitor literal distinction; technical subtree stack | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| qc/checks/check_help_links.py | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| qc/checks/check_voice_settings.py | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| qc/checks/check_systems.py | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |
| docs/systems.json | Full-gate correction or tool grouping | implemented | full8335/0@5a6231d; guard reversion caught/restored | this checkpoint |

| scratch/gemini-ui-fixes-1025/full-gate-r2/full-result.json | Final immutable gate/source/CAD guard | done, private | full8335/0; no retry | uncommitted, ignored |

| scratch/gemini-ui-fixes-1025/full-gate-r2/receipt.json | Actual full8335/0 receipt | done, private | full8335/0; no retry | uncommitted, ignored |

| scratch/gemini-ui-fixes-1025/package_checked.py | Spec rebuild/archive proof driver; never start EXE | done, private | not run | uncommitted, ignored |

| scratch/gemini-ui-fixes-1025/package-proof.json | Pending packaged exe byte inventory | pending | not run | uncommitted, ignored |

## Facts found
- Prior8258full@8da predates newGemini UI/OOP and does not cover this source.
- NewGemini30rowledger matches30Gitpaths; native301/0 was sixselectedchecks, notFull. Correct factual claim within authorized scope.
- RootdirtyStudio/layout/tests/configs/executable/userdata preserved; sourcebaselineffff102 only. RootPR80remoteclosure exists but rootnewGemini commits prevent blind oldff.
- Reviewer proof: root scratch/nong-gemini-audit-1024/latest-ui-method-proof-1025.json. Voice/TV baseline645 passed; newcurrent reproduces failures. No realnetwork/device.

## Done
- Prior review784dc16 plus broad read-only audit found stale machine/Sheet aliases, theme picker sync, TV deniedstorage. Browser additionally caught eager Voice Status beforeDOM. Fixes preserve loaded metadata and serialize timed-out event operations. No additional concrete issue in other reviewed30files or rootdirtyStudio layout.
- Focused57/0, actualEdge58/0, iterative12reversions caught/restored; independent source review approved6runtime hashes. Hardware untouched; current full pending.

## Next
1. Final actualdelta independent review; fresh full gate after confirmed newfixes.
2. Isolated EXE rebuild/archive verification; update PR81 with exact certificate.
3. Scoped root source integration preserving all dirtywork; release driver, retain hardwarepause.

## Blocked
Realhardware remains USER-NOTREADY. No software blocker; source/QCdriver lease main only. No rootruntime cutover authorized by softwaretests.
