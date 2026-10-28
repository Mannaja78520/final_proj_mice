# RL vs planner dance comparison (separate experiment)

Owner: claude:v7zr
Updated: 2026-10-27T20:30Z
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
Merging PR #92; then the PC runs it (steps sent to the coordinator, README_TH.md).

## File status
Baseline: origin/main 4c230e0.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| handoff/tasks/rl-compare-1027.md | this task | done | n/a | this checkpoint |
| docs/PLAN.html, docs/plan_state.js | A50 heading + A50-1 doing | done | check_plan_areas 43/0 | this checkpoint |
| tools/rl_compare/{reference,kin,servo,planner,metrics,env,ppo,rl,render,report,run}.py | new experiment package | done | check_rl_compare 14/0; cloud --quick run end to end (CPU) | this checkpoint |
| tools/rl_compare/{planner,studio_eval}.cjs | Studio planner + Studio collision check headless | done | planner reproduces Studio 7.49 deg | this checkpoint |
| tools/rl_compare/README_TH.md, run_compare.bat | Thai guide, one-click run | done | read through | this checkpoint |
| config/rl_compare.json | all settings (data) | done | check_rl_compare | this checkpoint |
| qc/checks/check_rl_compare.py | FK, clearance vs Studio, warp, servo, caps, board clock | done | sabotage 6/6 caught | this checkpoint |
| docs/systems.json, docs/systems/*.md | rl-compare system; rebuilt | done | systems build | this checkpoint |
| docs/experiments/{rl_compare.md,rl_compare_references.bib} | method, literature, refs | done | read through | this checkpoint |

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

- Collision gap (user 2026-10-27): 4 mm flags 0/567 v2 keys, 5 mm 23, 8 mm 56, 10 mm 70 (left v2,
  Studio checker); user chose 10 mm as Studio default (dance thread owns safe_path.json clearMm).
- Studio boxesHit inflates corners: approx clearance agrees with Studio on 3000 random poses within 1.5 mm.
- RRT is random: planner results vary a little run to run (7.49 vs 7.59 deg).
- CPU sanity (servo scenario, 1024 envs): RL song-clock error 26 -> 19 deg in 3 rounds; planner_music 26, planner_shape 46.

## Done
- Package + QC + Thai guide; --quick pipeline ran end to end in the cloud (no source video here).
- Experiment record (experiments.jsonl + docs/experiments/rl_compare_results.md), references .bib,
  literature comparison docs/experiments/rl_compare.md (user 2026-10-27: keep everything for a thesis).
- Full QC 8804/12: 4 = PlatformIO "download limit exceeded" (cloud), 6 browser timeouts + bus-scan
  timing (red on main here too), 2 = A50 plan heading (fixed, check_plan_areas 43/0).

## Next
1. PC: `pip install torch --index-url https://download.pytorch.org/whl/cu128` + opencv-python pillow;
   `python -m tools.rl_compare.run --quick`, then the full run (README_TH.md). Report verdict.

## Blocked
- Training/videos need the PC (RTX 5070 Ti) via the coordinator's Remote Control session.
