# Group cheer video rig follow-up

Owner: codex:10270037-9c0d
Updated: 2026-10-27T05:58:12.227579
Branch: codex/cheer-video-1027; isolated tree .staging-cheer-video-1027
Last commit: this checkpoint; root HEAD3298e36 and unrelated dirty work preserved
Plan: A48-21, fixes rejected A48-20 v1

## Goal
Follow two supplied group cheer videos with real waist/shrug, stable actor identity across camera changes, separate choreography, collision-aware paths and genuine supplementary RL. Deliver four checked editable rigs/previews and the Studio feature fix.

## Doing now
User clarified automatic reusable routine discovery for future clips (no manual representative choice) and explicitly reports unsmooth thrashing. Preserve prior v2 outputs as provisional. Add reusable choreography discovery + quality/smoothing with measured reversal/jump regressions, stronger IK continuity and conservative handling of unsupported motion; re-run retargetings. Full-r1 finished8275/18, source hashes unchanged; baseline firmware/loopback fixture failures retained, no promotion. Two review agents hit usage limit after earlier approvals; failed calls are not approvals. No active QC driver now. No hardware/services.

## File status
Exact owned source paths below. Private v1 is rejected and preserved, not completion evidence; old inventory/status is .local/cheer_rig_1027/task_previous.md. Private v2 files stay local; full exact inventory will accompany final validation.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/cheer-rig-1026.md | current handoff | doing | manually reconciled | this checkpoint |
| nong/main_python_set_nong/web/app_parts/video_motion_smooth.js | general motion smoothing + quality | planned | not run | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_routines.js | automatic choreography discovery | planned | not run | uncommitted |
| main_python/web/help.html | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| main_python/web/help/parts/studio.html | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/train_video_policy.py | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/collision_shapes.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/collisions.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/pose_from_video.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/safe_path.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_body_motion.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_page.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_rig_fit.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_tracking.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/html_parts/video.html | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/video_follow.json | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/video_motion_policy.json | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| qc/checks/check_video_group.py | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| qc/checks/check_video_moves.py | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| qc/data/video_group.cjs | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| tools/web_build.json | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/app_parts/video_checked_playback.js | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| nong/main_python_set_nong/web/index.html | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| qc/checks/check_gestures.py | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |
| qc/lib/qc.py | group rig / physical checks / learning / Help | pending final | focused185/0; full pending | uncommitted |

## Facts found
- v1 canonicalization destroyed raw hip/shoulder geometry; old reference previews bypassed full physical checks. All v2 previews use the exact checked exported sequence.
- Full geometry includes hand OBBs, joint spheres, nonadjacent same-arm bars and actual SHRUG. Legacy fkPoints readout remains unchanged. Final rounded RRT* legs rechecked using the most recent waypoint.
- Slow motion must map source time to checked robot time. Extremely slow sections frame-step the video; original unwarped song attachment is blocked. Private warped MP3s will be supplied.
- Detector order is not identity; selected actor loss holds until plausible re-acquisition. No incompatible choreography averaging or gender inference. User explicitly requires automatic discovery for future videos; do not make manual positional labels the feature. Group choreography directly, not guessed gender.
- Synthetic sequential Q-learning updates accepted pose and future states. Serialized/pruned table passes heldout400episodes and blind500episodes; improvement is small and does not prove real-video accuracy.
- Root setup/view/style, tests, configs, spec/EXE and all other user work are protected. Source baseline HEAD versions of five unowned dirty inputs were restored ONLY in own staging; backups .local/cheer_rig_1027/protected_root_inputs.json. Never bulk promote/reset.
- A48-19 stopped-without-handoff scoped software-QC/shared-output lease takeover recorded BRIDGE1006; its frozen tree/full8774/package and unrelated claims remain preserved.

## Done
- Four new independent full retargetings: Come left567keys/RRT31, center569/RRT30; Witsawa left273/RRT10, center279/RRT17. Every final pose/leg/time and HOME entry checked. Arm mean7.5/7.8/9.9/8.9deg; residual limits remain.
- Full raw YOLO+MediaPipe tracks retain waist/shoulders; 4 useful people in wide shots. Positional actor sets remain independent.
- Four native Blender files built with 10 animated controls and actual checked curves. No final v2 video rendering/audio/package yet.
- Native33/0 and affected185/0 passed (private .staging-final-focused.log); broader prior1736/2 failures diagnosed and fixed in focused run. Final full QC pending.
- Review: collision_review approved geometry/path scope; tracking_review APPROVED after realistic seek-resume fix.

## Next
1. Full QC frozen gate; fix genuine failures without skipping assertions. Snapshot0117 saved privately.
2. Delegate full QC under own loopback-only guard, frozen source, no heavy jobs.
3. Render four checked sequences; compose time-matched video/audio; native/file/visual validation and ZIP. Install uniquely named projects without overwrite.
4. Scoped review/integration only own files; preserve root user templates and regenerate their built outputs. Complete required source packaging/PR checks, no live restart or hardware.

## Blocked
Full-r1 failed18 baseline environment/firmware/loopback checks; diagnose after current motion fix. No source promotion before green. Reviewer quota unavailable; follow documented provider fallback.
 Hardware untested. Camera-only yaw ambiguity cannot always be resolved from one recording; conservative holds and quality reports remain visible.
