# RL vs planner dance comparison (separate experiment)

Owner: claude:v7zr
Updated: 2026-10-27T19:30Z
Branch: claude/project-thread-v7zrsg
Last commit: this checkpoint
Plan: A50-1

## Goal
User 2026-10-27: *ถ้าอยากลองเทียบจริง ผมให้ทำ RL เป็นการทดลองแยกไว้ แล้วอัดวิดีโอเทียบกับแบบที่ใช้อยู่ได้ครับ*,
*ทำๆๆ ขอแบบเทียบทำเทียบมาหน่อยแล้วเช็คว่าแบบไหนดีกว่ากัน*, *เก็บให้ผมดูด้วยนะและบอกเวลาเทรน*.
Fair test on the same input (cheer v2 analysis: human bone targets): RL imitation policy
vs the Studio planner. Metrics table, side-by-side multi-angle videos with music, one clip
per training round, all kept on the PC (git-ignored, < 20 GB) with an index page; report
training wall time per run and per round, the GPU, and the planner's compute time.
Must NOT change the main dance pipeline. Dance thread (cmsg_...BZPUoy331) owns Studio files.

## Doing now
Writing tools/rl_compare/ (reference loader, torch kinematics + servo env, metrics).

## File status
Baseline: origin/main 4c230e0.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/rl-compare-1027.md | this task | done | n/a | this checkpoint |
| docs/PLAN.html, docs/plan_state.js | A50-1 added, doing | done | plan.py | this checkpoint |
| tools/rl_compare/* | new experiment package | pending | not run | uncommitted |
| config/rl_compare.json | settings (data) | pending | not run | uncommitted |
| qc/checks/check_rl_compare.py | FK/metrics/servo checks | pending | not run | uncommitted |

## Facts found
- Reference = `<name>_analysis.json` (PC .local/cheer_rig_1027): `fit.times` ms (6 fps, 951),
  `fit.targets[i].arms[a].{ok,upper,fore}` unit bone dirs in bodyGroup (waist) frame,
  `fit.poses` = IK fit per sample (waist/shrug from the human), `tracks` = 2D landmarks.
- Studio's score: video_rig_fit.js:137 assess() = angle(robot bone, human bone) per bone,
  bodyGroup-local, planner evaluated at the SOURCE time warped onto its own clock
  (clockForSource) = shape only, no timing. v2 left: 7.5 deg mean.
- Planner = pose_from_video.js:484 vidBuild(fit, picks, opts): picks from vidPicksFor(fit, tol);
  opts.music=true keeps music time by cutting moves part-way (vidReachSide); false slows.
  Runs headless in Node through qc/data/video_group.cjs context() (SAFE_DPS var = 60).
- Kinematics/servo/board clock to reuse: tools/nong_sim/{kinematics,board_clock,studio}.py.
- Source video + audio: PC .local/cheer_rig_1026/{I0lCxX8373M,CLG7VdVhhLM}.mp4; v2 source.from/to.
- PC VM (device_bash) has no torch and no GPU: training must go through Remote Control on Windows.

## Done
- Read handoff, nong_sim, v2 files on the PC.

## Next
1. Package + QC check, then PC run steps.

## Blocked
- Training/videos need the PC (RTX 5070 Ti) via the coordinator's Remote Control session.
