# Latest Gemini Studio rendering and TV control correctness

Owner: codex:10231901-f6cc
Updated: 2026-10-25T08:06:21+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: bb5ad4b; functional9e46ad0 unchanged; current checkpoint records actual builds
Plan: A48-14 (same verified-source batch as A47-20)

## Goal
Main delegates confirmed latest Gemini Studio/TV regressions from ce0aeb0/b5a161b/2bd3299. Preserve all new features and idle render saving. No physical pose/calibration/CAD changes.

## Doing now
Actual5-environment firmware builds + native logic checks69/0 (61.5s), all27 deliberate regressions caught/restoredgreen. Functional9e46ad0 unchanged and sent existing main for independent review. Next run final affected browser/contract/layout/actual-CAD checks, resolve review findings, exact source freeze and full gate once. No flash/hardware/Hub/userdata writes.

## Facts found
- Main static review: applyPose URDF early return skips bottom markDirty3d, so after60 idle frames CAD pose/monitor can fail to redraw. Hand/grid/late mesh and resize lack invalidation. Mark mutation callbacks, retain zero idle renders.
- TV goHome posts all90 via /api/play, unsafe relative to actual savedHOME; use chosen valid Nong nativeHOME, no generic auto/first-module fallback.
- TV poll uses nonexistent Hub/api/status instead of/api/modules and pose field instead of module.joints. Play status uses at_ms/total_ms, not ms/total.
- TV pause is actually stop; resume plays sequences[0]. Must truthfully represent supported behavior or preserve exact paused clip semantics, no surprise first sequence.

## Next
Implement focused invalidation and TV API/target guards; fake browser tests idle CAD pose/monitor/grid/hand/late mesh/resize and idle zero rendering; TV selected HOME/no-all90/no-device+telemetry/progress. Existing main independent review exact final batch then full gate after source freeze.

## Evidence / limits
Only source inspection so far for this task. A47-20 native135/0 is backend-only. QC-only lease is ours after Lab22:12 release; physical remains stopped/reserved, no hardware, camera, restart or flash. User deferred actual elbow trim; no physical centering pass.

## File status
Baseline: e30bc36; preserve inherited latest Gemini2bd3299/8530dbf and rules9b57ee9; ledger lists own changes only.
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| apps/tv/index.html | Valid selectedNong, nativeHOME, module.joints, progress, exactclip restart | pending | real fake browser11/0; final deliberate regression caught; review pending | fa6c986 |
| nong/main_python_set_nong/web/app_parts/build_rig.js | Invalidate before CAD early return | pending | idle browser10/0; deliberate regression caught/restoredgreen | fa6c986 |
| nong/main_python_set_nong/web/app_parts/main_loop.js | Resize invalidates renderer | pending | idle browser10/0; deliberate regression caught/restoredgreen | fa6c986 |
| nong/main_python_set_nong/web/app_parts/urdf_view.js | Hand/grid/non-tip late mesh invalidate | pending | idle browser10/0; deliberate regression caught/restoredgreen | fa6c986 |
| nong/main_python_set_nong/web/app_parts/stl_meshes.js | Immediate and late mesh invalidate | pending | idle browser10/0; deliberate regression caught/restoredgreen | fa6c986 |
| nong/main_python_set_nong/web/app.js | Builder output | pending | generated then actual browser10/0 | fa6c986 |
| nong/main_python_set_nong/web/index.html | Builder output/EOL | pending | generation consistency pending | f8a9576 |
| main_python/web/help/parts/studio.html | SavedHOME/limits/RELAX wording, idle rendering | pending | correctness edits; docs check pending | 46ad847 |
| main_python/web/help/parts/tv.html | Target/nativeHOME/restart description | pending | matches browser11/0; docs check pending | fa6c986 |
| main_python/web/help/parts/gacha.html | Async Hall estimate vs false mass/deadcentre claims | pending | merged owner597a8064292 menu and diagram in5b6f122; own command facts retained | e79ea8a |
| main_python/web/help.html | Builder output | pending | regenerate after correctness+owner reconciliation | 5b6f122 |
| main_python/web/hub.html | Builder sync10lines inherited source feature | pending | inspect provenance+generation check before stage | 46ad847 |
| qc/checks/check_studio_render_idle.py | Real browser idle>60frames then mutations and idlezero | pending | 10/0; deliberate deliberate regression caught/restoredgreen | fa6c986 |
| qc/checks/check_tv_remote.py | Real page->Hub->fake HOME/target/joints/progress/restart | pending | 11/0; deliberate deliberate regression caught/restoredgreen | fa6c986 |
| handoff/tasks/gemini-studio-tv-1024.md | Reconciled per-file current state | pending | explicit ledger; final completion later | this checkpoint |

## Preserved unrelated files
apps/camera/index.html and apps/voice/index.html: builder EOL-only, not staged. qc_chain_proj.json/settings_shared.json and old reports: preexisting QC/user data, not owned or promoted.

- Current combined evidence: scratch/continue-urdf-1023/ui-native-affected-1025-v1.log =203/0 (25.5s), not full QC.

## Done
- Native/UI203/0 then contracts/affected637/0; logs private scratch/continue-urdf-1023. Studio10/0,TV11/0 are simulated browser evidence, no physical proof.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| docs/systems.json | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | uncommitted |
| docs/systems/agents.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 9e46ad0 |
| docs/systems/app-gacha.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/app-small.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/app-voice.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/fw-core.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | uncommitted |
| docs/systems/fw-gacha.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/fw-registry.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/hub-modules.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/hub-studio.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| docs/systems/qc.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 5b6f122 |
| docs/systems/studio.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| nong/main_python_set_nong/PATCHES.md | Generator mapping/header or snapshot index | pending | check_systems/check_build_web green637/0 before latest explicit studio mapping; rerun pending | 46ad847 |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/app.js | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/index.html | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/patch.md | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/shared/mice.css | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/shared/themes.css | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |
| nong/main_python_set_nong/patches/0057_redraw-idle-cad-updates-and-preserve-selected-na/style.css | Required local web snapshot | done | save_patch0057, ignored by existing repository rule | uncommitted (ignored) |

- Deliberate proofs: scratch/continue-urdf-1023/sabotage-{gacha,syntax,ui,tv,render}-1025.log:22/22 caught, each restoredgreen. Not full QC.

- New evidence: module-help-affected-1025.log46/0; actual generated gacha-only page controls reach fakeboard, phasecountdown, unknownposition, Halllabel, configuredzero values; Help browsersearch/navigation/tech/phone. No hardware proof.
| docs/systems/fw-web.md | Map generated Gacha page browser regression | pending | generator/check_systems pending | 1ff8409 |

- Added proofs: sabotage-home-1025.log1/1, sabotage-help-1025.log2/2, sabotage-module-ui-1025.log2/2; each restoredgreen. Source functional files now match9e46ad0.

- Actual build proof: firmware-build-1025.log69/0, firmware-build-details-1025.log, firmware-artifacts-1025.json (5image SHA/size/flash). No upload/flash.
