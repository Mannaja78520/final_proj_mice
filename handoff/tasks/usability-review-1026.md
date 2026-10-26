# UX/UI usability sweep and residual quality follow-through

Owner: codex:10260449-5ec2
Updated: 2026-10-26T08:41:01.256161+07:00
Branch: codex/usability-review-1026
Tree: E:/final_proj/mice/code/.staging-usability-review-1026
Last commit: this checkpoint; baseline3298e36
Plan: A48-19 (robot); related A48-13 (Lift/physical), A48-18 done

## Goal
Finish all own UI usability and residual software gaps. No duplicated Help in Tools (global entry exists). Continue autonomously; preserve root dirty files and immutable proof trees. Physical USER-NOTREADY.

## Doing now
Tools checkpoint: flat registry grid, native safe newtab links, Thai manifest descriptions, hidden launcher Help, truthful states/focus, same-step Help. Design consultation tools_design gpt-6-astra high completed. First443/1 was inline fixture closing-script; fixed474/0. Visual8layouts/0overflow/realEnter newtab passed; last button/globalHelp polish awaits rerun/screenshot refresh. Next bounded step all-page source findings with exact claims before edits, then Lift P1 repair/native/build separately.

## File status
Current baseline-to-worktree Git paths reconciled; generated unrelated4outputs and other headers touched raw EOL only, no Git content delta. Private evidence under scratch/usability-review-1026 (not source/public).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/all-jao/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/camera/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/faces/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/gacha/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/help/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/photobooth/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/studio/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/tv/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| apps/voice/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| docs/shots/hub-tools-card.png | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| docs/systems/agents.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| docs/systems/hub-web.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| docs/systems/qc.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| docs/systems/shared-web.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| handoff/tasks/usability-review-1026.md | Current per-file ledger | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | this checkpoint |
| main_python/web/help.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/help/parts/hub.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/home/parts/home.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/home/parts/tools.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/home/parts/tools.js | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/home/parts/top.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/home/style.css | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| main_python/web/hub.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| qc/checks/check_help_links.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| qc/checks/check_registries.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| qc/checks/check_tools_list.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |
| qc/data/tools_launcher.js | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | uncommitted |

## Facts found
- Dynamic CPU/GPU/RAM/Voice/browser policy DONE in PR82/root3298e36; previous full8418/0 qualified4isolated retries+994inputs stable. Do not rework or reuse old receipt.
- Tools Help duplicate removed via apps/help/app.json show:false; registry route/global #helpLink still works. Unknown apps preserved, no extra catalog/API/spec changes needed. Manifest icon previously unescaped; native DOM now text-safe; malformed/HTTP errors distinct from empty.
- All-page source review (same-provider) found candidates: modules stale handlers/scan race; network label dedup/probe failures/result reset; camera failure-as-empty; TV unchecked play/stop/speech; Voice stuck modelbuttons; Gacha silent logs; WebUI Run refusal; AllJao async popup; Studio projectlist silent error; Home failure-as-empty; remote firmware bus address stripped (P1). Must reproduce/fix, not merely report.
- Lift design review confirms UP/DOWN/HOME AND encoder/endpoint GOTO lack independent deadlines. Use finite configurable phase limits, latched fault, explicit clear, busy semantics preventing sequence continuation; native executed production methods plus mice_lift build. No actual hardware fault observed.
- Root dirty Studio relocates CAD look controls setup/view and CSS. Read-only inspected; preserve setup/view/style/generatedindex, configs, spec processkill helper, exe, projects/settings/privatefiles. Never run root spec.
- USER-NOTREADY: no robot probes/COM/network/camera/motion/HOME/trim/flash or Hub/helper service cutover. Driver uses private Python socket guard: isolated loopback fakes only; no existing helper ports. No inference load; combined real Voice/Face load unmeasured.
- One claimed software QC/fake/browser/build/timing driver; inventory before each run. Claim integration separately. Source only isolated, parts only; Help parity mandatory. Root discovery task mirrors own ledger.

## Done
Task/A48-19 taken as own session; source/design and allpage/Lift consultations complete. Tools functional affected474/0 and8visual layouts+realEnter verified before final minor affordance polish. Initial failing fixture evidence preserved. No physical/runtime/model actions.

## Next
1. Refresh Tools final proof/screenshot, deliberately regress and restore launcher guards. Address reproduced allpage UI findings through sources with tests/Help in same step.
2. Separate Lift deadlines/fault/config/command/UI/native tests/build step; no hardware actions.
3. Affected+deliberate regressions, independent exact final review, stable current full gate once final batch complete; safe isolated spec package/archive proof, scoped PR/rootintegration preserving dirty bytes. Do not stop at plan/report.

## Blocked
Physical/user matrix paused. Actual combined inference performance unmeasured; no real hardware/bugfree/100% claim. No software blocker.
