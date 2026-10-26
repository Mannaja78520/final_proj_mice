# UX/UI usability sweep and residual quality follow-through

Owner: codex:10260449-5ec2
Updated: 2026-10-26T08:57:38.361155+07:00
Branch: codex/usability-review-1026
Tree: E:/final_proj/mice/code/.staging-usability-review-1026
Last commit: this checkpoint; baseline3298e36
Plan: A48-19 (robot); related A48-13 (Lift/physical), A48-18 done

## Goal
Finish all own UI usability and residual software gaps. No duplicated Help in Tools (global entry exists). Continue autonomously; preserve root dirty files and immutable proof trees. Physical USER-NOTREADY.

## Doing now
Step3 Lift P1: implement independent configurable travel/homing phase deadlines +latched fault/explicit clear, preserving sequence fault wait. Native fake IO runs actual class header and production motion methods, then mice_lift build. Design completed tools_design (same-provider); UI independent ui_review pending exact b908c98. No hardware/COM/network/motion/HOME/flash/service/model actions.

## File status
Current baseline-to-worktree Git paths reconciled; generated unrelated4outputs and other headers touched raw EOL only, no Git content delta. Private evidence under scratch/usability-review-1026 (not source/public).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/all-jao/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/all-jao/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/camera/app.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/camera/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/camera/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/faces/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/gacha/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/gacha/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/help/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/photobooth/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/studio/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/tv/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/tv/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/voice/app.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/voice/app.json | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| apps/voice/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| docs/shots/hub-tools-card.png | UI error/action/identity and Help parity | refresh screenshot pending | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| docs/systems/agents.md | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/generated; final metadata checks pending | b908c98 |
| docs/systems/hub-web.md | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/generated; final metadata checks pending | b908c98 |
| docs/systems/qc.md | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/generated; final metadata checks pending | b908c98 |
| docs/systems/shared-web.md | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/generated; final metadata checks pending | b908c98 |
| firmware/src/web/WebUI.h | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| handoff/tasks/usability-review-1026.md | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | this checkpoint |
| main_python/web/help.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/all-jao.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/camera.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/firmware.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/gacha.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/hub.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/modsite.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/studio.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/tv.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/help/parts/voice.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/firmware.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/home.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/home.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/modules.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/network.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/network.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/tools.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/tools.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/parts/top.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/home/style.css | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| main_python/web/hub.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| nong/main_python_set_nong/web/app.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| nong/main_python_set_nong/web/app_parts/project_save_load.js | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| nong/main_python_set_nong/web/html_parts/header.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| nong/main_python_set_nong/web/index.html | UI error/action/identity and Help parity | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/checks/check_help_links.py | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/checks/check_registries.py | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/checks/check_tools_list.py | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/checks/check_tv_remote.py | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/checks/check_usability_states.py | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/data/tools_launcher.js | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/data/usability_apps.js | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/data/usability_dom.js | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| qc/data/usability_hub.js | Production-method / browser regression | WIP; proof current | scratch/usability-review-1026/allpage-affected-r2:274/0; native UI fixtures21/0 | b908c98 |
| firmware/src/modules/lift/LiftModule.cpp | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/src/modules/lift/LiftModule.h | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/config/esp32_hardware_lift_module.h | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/src/core/ConfigStore.cpp | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/config/commands.json | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/COMMANDS.md | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/README.md | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| firmware/sd_card_example/data/module.yaml | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| main_python/web/help/parts/lift.html | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| qc/checks/check_lift_motion.py | Lift bounded motion/fault/config contract | pending | not run | uncommitted |
| qc/data/lift_motion.cpp | Lift bounded motion/fault/config contract | pending | not run | uncommitted |

## Facts found
- Dynamic CPU/GPU/RAM/Voice/browser policy DONE in PR82/root3298e36; previous full8418/0 qualified4isolated retries+994inputs stable. Do not rework or reuse old receipt.
- Tools Help duplicate removed via apps/help/app.json show:false; registry route/global #helpLink still works. Unknown apps preserved, no extra catalog/API/spec changes needed. Manifest icon previously unescaped; native DOM now text-safe; malformed/HTTP errors distinct from empty.
- All-page source review (same-provider) found candidates: modules stale handlers/scan race; network label dedup/probe failures/result reset; camera failure-as-empty; TV unchecked play/stop/speech; Voice stuck modelbuttons; Gacha silent logs; WebUI Run refusal; AllJao async popup; Studio projectlist silent error; Home failure-as-empty; remote firmware bus address stripped (P1). All reproduced and fixed; proof21/0+affected274/0; final independent review pending.
- Lift design review confirms UP/DOWN/HOME AND encoder/endpoint GOTO lack independent deadlines. Use finite configurable phase limits, latched fault, explicit clear, busy semantics preventing sequence continuation; native executed production methods plus mice_lift build. No actual hardware fault observed; repair next.
- Root dirty Studio relocates CAD look controls setup/view and CSS. Read-only inspected; preserve setup/view/style/generatedindex, configs, spec processkill helper, exe, projects/settings/privatefiles. Never run root spec.
- USER-NOTREADY: no robot probes/COM/network/camera/motion/HOME/trim/flash or Hub/helper service cutover. Driver uses private Python socket guard: isolated loopback fakes only; no existing helper ports. No inference load; combined real Voice/Face load unmeasured.
- One claimed software QC/fake/browser/build/timing driver; inventory before each run. Claim integration separately. Source only isolated, parts only; Help parity mandatory. Root discovery task mirrors own ledger.

## Done
Allpage source candidates reproduced and repaired with same-step Help, UI method fixtures21/0 and affected274/0 (13checks). Source-level before logs preserved.
Task/A48-19 taken as own session; source/design and allpage/Lift consultations complete. Tools functional affected474/0 and8visual layouts+realEnter verified before final minor affordance polish. Initial failing fixture evidence preserved. No physical/runtime/model actions.

## Next
1. Refresh Tools final proof/screenshot, deliberately regress and restore launcher guards. Address reproduced allpage UI findings through sources with tests/Help in same step.
2. Separate Lift deadlines/fault/config/command/UI/native tests/build step; no hardware actions.
3. Affected+deliberate regressions, independent exact final review, stable current full gate once final batch complete; safe isolated spec package/archive proof, scoped PR/rootintegration preserving dirty bytes. Do not stop at plan/report.

## Blocked
Physical/user matrix paused. Actual combined inference performance unmeasured; no real hardware/bugfree/100% claim. No software blocker.
