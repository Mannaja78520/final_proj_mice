# UX/UI usability sweep and residual quality follow-through

Owner: codex:10260449-5ec2
Updated: 2026-10-27T00:41:11.315268+07:00
Branch: codex/usability-review-1026
Tree: E:/final_proj/mice/code/.staging-usability-review-1026
Last commit: this checkpoint; baseline3298e36
Plan: A48-19 (robot); related A48-13 (Lift/physical), A48-18 done

## Goal
Finish all own UI usability and residual software gaps. No duplicated Help in Tools (global entry exists). Continue autonomously; preserve root dirty files and immutable proof trees. Physical USER-NOTREADY.

## Doing now
Step10 private packaging: current full-r3@03bc3a6 PASS8774/0, qualifiedfreeze_stop passedalone2/2;1004inputs/CAD/guard unchanged. Runtime1fd2c0d matches approved23a5e65. Build reviewed isolated spec into scratch/.../package only, exclude QC PYTHONPATH from binary, verify archiveassets/native modules/images; never start/install/rootexe/spec. Then scopedPR/rootintegration. Physical/model load unmeasured.

## File status
Current baseline-to-worktree Git paths reconciled; generated unrelated4outputs and other headers touched raw EOL only, no Git content delta. Private evidence under scratch/usability-review-1026 (not source/public).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| MiceHub.spec | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| apps/all-jao/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/all-jao/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| apps/camera/app.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| apps/camera/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/camera/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| apps/faces/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/gacha/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/gacha/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| apps/help/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/photobooth/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/studio/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/tv/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/tv/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| apps/voice/app.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| apps/voice/app.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| apps/voice/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| docs/shots/hub-tools-card.png | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b2752c5 |
| docs/systems/agents.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| docs/systems/fw-core.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| docs/systems/fw-lift.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| docs/systems/fw-registry.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| docs/systems/hub-apps.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| docs/systems/hub-show.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| docs/systems/hub-web.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| docs/systems/qc.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| docs/systems/shared-web.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| firmware/COMMANDS.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/README.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/config/commands.json | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/config/esp32_hardware_lift_module.h | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/sd_card_example/data/module.yaml | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/src/core/ConfigStore.cpp | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/src/modules/lift/LiftModule.cpp | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/src/modules/lift/LiftModule.h | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| firmware/src/web/WebUI.h | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| handoff/tasks/usability-review-1026.md | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | this checkpoint |
| main_python/build_stamp.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 38858e5 |
| main_python/hub_api_play.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| main_python/hub_auth.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| main_python/hub_show.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| main_python/main.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| main_python/web/help.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| main_python/web/help/parts/all-jao.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/help/parts/camera.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/help/parts/firmware.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/help/parts/gacha.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/help/parts/hub.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 38858e5 |
| main_python/web/help/parts/lift.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| main_python/web/help/parts/modsite.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/help/parts/studio.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| main_python/web/help/parts/tv.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| main_python/web/help/parts/voice.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/firmware.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/home.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| main_python/web/home/parts/home.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/modules.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/network.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/network.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| main_python/web/home/parts/tools.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| main_python/web/home/parts/tools.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| main_python/web/home/parts/top.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| main_python/web/home/style.css | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| main_python/web/hub.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| nong/main_python_set_nong/web/app.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| nong/main_python_set_nong/web/app_parts/project_save_load.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| nong/main_python_set_nong/web/html_parts/header.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| nong/main_python_set_nong/web/index.html | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| qc/checks/check_docs.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| qc/checks/check_faces_loopback.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 70a0feb |
| qc/checks/check_flash_remote.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 23a5e65 |
| qc/checks/check_guards_armed.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/checks/check_help_links.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| qc/checks/check_lift_motion.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| qc/checks/check_mdns.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/checks/check_name_claim.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/checks/check_one_hub.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 23a5e65 |
| qc/checks/check_onefile.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| qc/checks/check_play_stop_order.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| qc/checks/check_race_guards.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | c2fff7a |
| qc/checks/check_registries.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| qc/checks/check_responsive.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| qc/checks/check_short_name.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 5d2d4ed |
| qc/checks/check_tools_list.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| qc/checks/check_tv_remote.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| qc/checks/check_usability_browser.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 9ebd817 |
| qc/checks/check_usability_states.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| qc/checks/check_voice_multi.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/data/app_lifecycle.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/data/lift_motion.cpp | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 38858e5 |
| qc/data/tools_launcher.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 873f81b |
| qc/data/usability_apps.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 1fd2c0d |
| qc/data/usability_browser.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | dc112da |
| qc/data/usability_dom.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| qc/data/usability_hub.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | b908c98 |
| qc/lib/qc.py | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | 5d2d4ed |
| shared/web/mice-ui.js | UI/Lift/Help/QC | verified software; package/integration next | full8774/0@03bc;freeze_stop2/2qualified;see Done | c2fff7a |
| scratch/usability-review-1026/package/MiceHub.exe | Private package; excluded from PR | pending | not run | uncommitted |

## Facts found
- Dynamic CPU/GPU/RAM/Voice/browser policy DONE in PR82/root3298e36; previous full8418/0 qualified4isolated retries+994inputs stable. Do not rework or reuse old receipt.
- Tools Help duplicate removed via apps/help/app.json show:false; registry route/global #helpLink still works. Unknown apps preserved, no extra catalog/API/spec changes needed. Manifest icon previously unescaped; native DOM now text-safe; malformed/HTTP errors distinct from empty.
- All-page source review (same-provider) found candidates: modules stale handlers/scan race; network label dedup/probe failures/result reset; camera failure-as-empty; TV unchecked play/stop/speech; Voice stuck modelbuttons; Gacha silent logs; WebUI Run refusal; AllJao async popup; Studio projectlist silent error; Home failure-as-empty; remote firmware bus address stripped (P1). All reproduced and fixed; proof21/0+affected274/0; final independent review pending.
- Lift design review confirms UP/DOWN/HOME AND encoder/endpoint GOTO lack independent deadlines. Use finite configurable phase limits, latched fault, explicit clear, busy semantics preventing sequence continuation; native executed production methods plus mice_lift build. No actual hardware fault observed; implemented; native proof + compile recorded; latest incremental build pending.
- Root dirty Studio relocates CAD look controls setup/view and CSS. Read-only inspected; preserve setup/view/style/generatedindex, configs, spec processkill helper, exe, projects/settings/privatefiles. Never run root spec.
- USER-NOTREADY: no robot probes/COM/network/camera/motion/HOME/trim/flash or Hub/helper service cutover. Driver uses private Python socket guard: isolated loopback fakes only; no existing helper ports. No inference load; combined real Voice/Face load unmeasured.
- One claimed software QC/fake/browser/build/timing driver; inventory before each run. Claim integration separately. Source only isolated, parts only; Help parity mandatory. Root discovery task mirrors own ledger.

## Done
Current frozen full-r3@03bc3a6 PASS8774/0 in506.3s; onequalifiedcrowd failurecheck_freeze_stop greenalone2/2. All1004sourceinputs, CAD20 andapprovedguard unchanged. Failedfulls retained. Onlyown handoff metadata maychange aftergate; prove every othertestedinput stable beforepackage/integration.
Full-r2@2bc2157 stable1004/CAD/guard FAIL8763/2. Remaining AST child HOST fixed afterexec; oversized negativefixture sends only advertised headers (actualHTTP rejection stillrequired). Boundary capture29thread abort vs100header-onlyHTTP401; unchangedremote20/0twice. Finalaffected241/0; no runtimefix/sourceguarantee inferred fromTCPabort.
Functional Tools/allpage/Lift/TV implementations and same-step Help complete; reviews approved through416709f. Latest tiny port-fixture delta needs bounded review; runtime unchanged from1fd2c0d.
Full-r1@d4f2039 FAIL8503/25;1004inputs/CAD unchanged.19failed checks now999/0 under strict guard; final port/short-name fixtures112/0. Failure evidence preserved; no assertion skipped. Source/fixture causes and guard parsing/binding fixes recorded in BRIDGE/logs.
32deliberate mutations caught/restored: initial25 +AST3/notice1/fakeBind1/portPool1/shortName1. Earlier weak wrap/HOMEepoch fixtures strengthened, then caught; raw bytes restored. Logs scratch/usability-review-1026/regressions*.
Final_review approved source70a0feb+416709f and guard SHA2c3a84f6; direct17guard checks passed with no dispatch. tools_design Codex limit11:27PM; Gemini3.8FlashHigh inline design only (initial headless read denied/empty never approval). Codex final review resumed after reset.
Visual17pages136theme-width cases overflow0; keyboard17/17 plus real Enter newtab; refreshed public Tools shot. Latest mice_lift compile SUCCESS1590129bytes80.9%; native actual methods green; no physical test.
Private fake reports archived; isolated test-generated settings/projects restored to pre-gate Git baseline; root dirty files protected. Dynamic resource policy already donePR82; actual combined inference load unmeasured.

## Next
1. Exact independent correction review +4regressions; frozen full-r2 with corrected envelope.
2. Green full -> private spec package/archive -> PR/guarded rootintegration; preserve user dirty files, physical pause.

## Blocked
Physical/user matrix paused. Actual combined inference performance unmeasured; no real hardware/bugfree/100% claim. No software blocker.
