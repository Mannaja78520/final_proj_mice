# Latest Gemini Studio rendering and TV control correctness

Owner: codex:10231901-f6cc
Updated: 2026-10-24T22:51:43.017840+07:00
Branch: codex/gacha-safety-1024-f6cc
Tree: E:/final_proj/mice/code/.staging-continue-urdf
Last commit: ba80ca8 latest2bd merge; WIP checkpoint follows
Plan: A48-14 (same verified-source batch as A47-20)

## Goal
Main delegates confirmed latest Gemini Studio/TV regressions from ce0aeb0/b5a161b/2bd3299. Preserve all new features and idle render saving. No physical pose/calibration/CAD changes.

## Doing now
Claimed isolated Studio app_parts/build_rig,urdf_view,main_loop,stl_meshes,scene if needed and generated bundles only via builder; apps/tv/index.html; new meaningful fake-browser regressions. No root source writes or physical operations. Current latest2bd merged, not olde30 baseline.

## Facts found
- Main static review: applyPose URDF early return skips bottom markDirty3d, so after60 idle frames CAD pose/monitor can fail to redraw. Hand/grid/late mesh and resize lack invalidation. Mark mutation callbacks, retain zero idle renders.
- TV goHome posts all90 via /api/play, unsafe relative to actual savedHOME; use chosen valid Nong nativeHOME, no generic auto/first-module fallback.
- TV poll uses nonexistent Hub/api/status instead of/api/modules and pose field instead of module.joints. Play status uses at_ms/total_ms, not ms/total.
- TV pause is actually stop; resume plays sequences[0]. Must truthfully represent supported behavior or preserve exact paused clip semantics, no surprise first sequence.

## Next
Implement focused invalidation and TV API/target guards; fake browser tests idle CAD pose/monitor/grid/hand/late mesh/resize and idle zero rendering; TV selected HOME/no-all90/no-device+telemetry/progress. Existing main independent review exact final batch then full gate after source freeze.

## Evidence / limits
Only source inspection so far for this task. A47-20 native135/0 is backend-only. QC-only lease is ours after Lab22:12 release; physical remains stopped/reserved, no hardware, camera, restart or flash. User deferred actual elbow trim; no physical centering pass.
