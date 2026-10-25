# Latest Gemini Studio rendering and TV control correctness

Owner: codex:10231901-f6cc
Updated: 2026-10-25T07:41:54+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: 3bb6c07; source below uncommitted
Plan: A48-14 (same verified-source batch as A47-20)

## Goal
Main delegates confirmed latest Gemini Studio/TV regressions from ce0aeb0/b5a161b/2bd3299. Preserve all new features and idle render saving. No physical pose/calibration/CAD changes.

## Doing now
25Oct handoff reconciliation before code: keep current UI/render fixes, migrate per-file ledger, then native fixture/docs/system generation and browser sabotage. Main independent exact-source review before final full gate. Help overlap owner codex:10242258-597a messaged with exact correctness hunks; await merge-safe reconciliation. No hardware/config/runtime actions.

## Facts found
- Main static review: applyPose URDF early return skips bottom markDirty3d, so after60 idle frames CAD pose/monitor can fail to redraw. Hand/grid/late mesh and resize lack invalidation. Mark mutation callbacks, retain zero idle renders.
- TV goHome posts all90 via /api/play, unsafe relative to actual savedHOME; use chosen valid Nong nativeHOME, no generic auto/first-module fallback.
- TV poll uses nonexistent Hub/api/status instead of/api/modules and pose field instead of module.joints. Play status uses at_ms/total_ms, not ms/total.
- TV pause is actually stop; resume plays sequences[0]. Must truthfully represent supported behavior or preserve exact paused clip semantics, no surprise first sequence.

## Next
Implement focused invalidation and TV API/target guards; fake browser tests idle CAD pose/monitor/grid/hand/late mesh/resize and idle zero rendering; TV selected HOME/no-all90/no-device+telemetry/progress. Existing main independent review exact final batch then full gate after source freeze.

## Evidence / limits
Only source inspection so far for this task. A47-20 native135/0 is backend-only. QC-only lease is ours after Lab22:12 release; physical remains stopped/reserved, no hardware, camera, restart or flash. User deferred actual elbow trim; no physical centering pass.

## File handoff
File | Change | State | Verification/evidence | Commit
--- | --- | --- | --- | ---
apps/tv/index.html | Valid selectedNong, nativeHOME, module.joints, progress, exactclip restart | pending | real fake browser11/0; final sabotage/review pending | uncommitted
nong/main_python_set_nong/web/app_parts/build_rig.js | Invalidate before CAD early return | pending | idle browser10/0; sabotage pending | uncommitted
nong/main_python_set_nong/web/app_parts/main_loop.js | Resize invalidates renderer | pending | idle browser10/0; sabotage pending | uncommitted
nong/main_python_set_nong/web/app_parts/urdf_view.js | Hand/grid/non-tip late mesh invalidate | pending | idle browser10/0; sabotage pending | uncommitted
nong/main_python_set_nong/web/app_parts/stl_meshes.js | Immediate and late mesh invalidate | pending | idle browser10/0; sabotage pending | uncommitted
nong/main_python_set_nong/web/app.js | Builder output | pending | generated then actual browser10/0 | uncommitted
nong/main_python_set_nong/web/index.html | Builder output/EOL | pending | generation consistency pending | uncommitted
main_python/web/help/parts/studio.html | SavedHOME/limits/RELAX wording, idle rendering | pending | correctness edits; docs check pending | uncommitted
main_python/web/help/parts/tv.html | Target/nativeHOME/restart description | pending | matches browser11/0; docs check pending | uncommitted
main_python/web/help/parts/gacha.html | Async Hall estimate vs false mass/deadcentre claims | pending | overlap owner contacted; preserve their layout | uncommitted
main_python/web/help.html | Builder output | pending | regenerate after correctness+owner reconciliation | uncommitted
main_python/web/hub.html | Builder sync10lines inherited source feature | pending | inspect provenance+generation check before stage | uncommitted
qc/checks/check_studio_render_idle.py | Real browser idle>60frames then mutations and idlezero | pending |10/0; deliberate sabotage pending | uncommitted
qc/checks/check_tv_remote.py | Real page->Hub->fake HOME/target/joints/progress/restart | pending |11/0; deliberate sabotage pending | uncommitted
handoff/tasks/gemini-studio-tv-1024.md | Reconciled per-file current state | pending | explicit ledger; final completion later | next WIP

## Preserved unrelated files
apps/camera/index.html and apps/voice/index.html: builder EOL-only, not staged. qc_chain_proj.json/settings_shared.json and old reports: preexisting QC/user data, not owned or promoted.
