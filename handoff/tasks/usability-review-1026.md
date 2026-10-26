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
Step2: reproduce allpage source findings with actual production methods and fake APIs; fix concrete failures and Help in same step. Claimed exact Modules/Network/Home/Firmware, Camera/TV/Voice/Gacha/AllJao/Studio/WebUI sources and regressions. Tools checkpoint873f81b; latest small style/globallink polish needs final proof refresh.

## File status
Current baseline-to-worktree Git paths reconciled; generated unrelated4outputs and other headers touched raw EOL only, no Git content delta. Private evidence under scratch/usability-review-1026 (not source/public).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/all-jao/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/camera/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/faces/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/gacha/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/help/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/photobooth/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/studio/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/tv/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| apps/voice/app.json | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| docs/shots/hub-tools-card.png | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| docs/systems/agents.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| docs/systems/hub-web.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| docs/systems/qc.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| docs/systems/shared-web.md | Generated inventory / current screenshot | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| handoff/tasks/usability-review-1026.md | Current per-file ledger | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | this checkpoint |
| main_python/web/help.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/help/parts/hub.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/parts/home.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/parts/tools.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/parts/tools.js | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/parts/top.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/style.css | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/hub.html | Launcher/Help parity | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| qc/checks/check_help_links.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| qc/checks/check_registries.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| qc/checks/check_tools_list.py | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| qc/data/tools_launcher.js | Regression coverage | WIP | Tools474/0; latest polish pending; scratch/usability-review-1026/tools-affected-r2.log | 873f81b |
| main_python/web/home/parts/modules.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/home/parts/network.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/home/parts/home.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/home/parts/boot_scans.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/home/parts/firmware.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/home/parts/network.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/camera/app.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/camera/index.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/tv/index.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/voice/app.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/voice/index.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/gacha/index.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| apps/all-jao/index.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| nong/main_python_set_nong/web/app_parts/project_save_load.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| nong/main_python_set_nong/web/app.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| firmware/src/web/WebUI.h | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/firmware.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/camera.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/tv.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/voice.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/gacha.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/studio.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/all-jao.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| main_python/web/help/parts/modsite.html | Allpage error/action/identity regression | pending | not run | uncommitted |
| qc/checks/check_usability_states.py | Allpage error/action/identity regression | pending | not run | uncommitted |
| qc/data/usability_hub.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| qc/data/usability_apps.js | Allpage error/action/identity regression | pending | not run | uncommitted |
| qc/data/usability_dom.js | Allpage error/action/identity regression | pending | not run | uncommitted |

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
