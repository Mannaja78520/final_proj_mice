# No-robot work 2026-10-28: big-show MOVE, RL resume, robot pose from camera

Owner: claude:nr28
Updated: 2026-10-28 20:10 (Bangkok)
Branch: claude/project-thread-whxuft
Last commit: this checkpoint
Plan: A52-1, A52-2, A52-3

## Goal
User 2026-10-28 (back at the dorm): do all the work that needs no robot.
1. A52-1: `MOVE` of a v5 dance (447 poses, 30 KB) crashes nong; fix it properly.
2. A52-2: RL training stopped at round 12/20; a rerun starts at round 1. Resume.
3. A52-3: "like YOLO pose" for nong: from any camera find each joint, tell
   front/back/left/right, check a move is right, auto-calibrate sizes later,
   health checks. Config-driven from Studio's rig. Split pieces for Codex.

## Doing now
A52-3 first slice: tools/robot_pose (keypoints from Studio's rig via NongTree.frames,
pinhole camera, numpy LM solver, camera/pose fit with facing + left/right swap,
compare with BoardClock, calibration suggestions, synthetic YOLO-pose labels),
config/robot_pose.json, qc/checks/check_robot_pose.py. A52-1/A52-2 code is in
(WIP commits), host checks pass; sabotage + full QC still to do.

## File status
Baseline: 14fa8fc (origin/main).

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/norobot-1028.md` | task file | done | n/a | this checkpoint |
| `handoff/tasks/robot-pose-data.md` | Codex task: render, label, train, first video | done | n/a | WIP pushed |
| `docs/PLAN.html`, `docs/plan_state.js` | A52-1..3 rows | done | plan.py | WIP pushed |
| `firmware/src/core/SeqScan.h` | new: line scanner, one step at a time | done | g++ host test 29/29 (check_seq_stream) | WIP pushed |
| `firmware/src/core/SequencePlayer.cpp`, `.h` | stream steps; RAM shows use the same scanner | done | `pio run -e mice_nong` OK (cloud); not on the board | WIP pushed |
| `qc/checks/check_seq_stream.py`, `qc/data/seq_stream.cpp` | new check | done | 29 ok (direct run) | WIP pushed |
| `tools/rl_compare/rl.py`, `run.py` | resume from last round, train_state.pt | done | check_rl_compare 18 ok (CPU torch) | WIP pushed |
| `qc/checks/check_rl_compare.py` | resume test | done | 18 ok | WIP pushed |
| `tools/nong_sim/kinematics.py` | `frames()` split out of forward() | done | check_robot_pose; check_nong_sim not run yet | WIP pushed |
| `tools/robot_pose/*` (13 files) | new package | done | check_robot_pose 17 ok (direct run) | WIP pushed |
| `config/robot_pose.json` | new config | done | check_robot_pose | WIP pushed |
| `qc/checks/check_robot_pose.py` | new check | done | 17 ok | WIP pushed |
| `docs/experiments/2026-10-28_robot_pose.md` | synthetic numbers + papers | done | numbers from bench | WIP pushed |
| `docs/systems.json`, `docs/systems/*` | robot-pose system | done | systems.py build | WIP pushed |

## Facts found
- One camera cannot see depth flips (elbow toward/away) or a small waist turn
  (shoulders move in depth only): fit_pose lands nearest its start; 2 cameras fix it.
- A waist zero offset is indistinguishable from the camera standing elsewhere;
  torsoH fixes the scale. Calibrator fits neither.
- Cloud full QC: heavy CPU work in parallel makes browser checks time out
  (150 s): run nothing heavy while it runs.
- PlatformIO libs for other envs: `git clone` from GitHub works (archives do not);
  a hand-written `.piopm` ({"type":"library","name","version","spec":{"owner","name"}})
  in .pio/libdeps/<env>/<lib> makes pio accept it.
- Cloud PlatformIO: the registry says "Download limit exceeded". Workaround that
  built `mice_nong` OK: platform by git URL, toolchain/framework from GitHub
  release assets, esptool + scons from PyPI, unpacked into ~/.platformio/packages
  with a hand-written package.json (name + version that platform.json asks for).
- firmware/src/core/SequencePlayer.cpp:54 startAt parses the WHOLE file
  (SDStore::loadYaml, SDStore.cpp:68 deserializeYml) into one JsonDocument;
  loop() indexes `(*doc_)["steps"]`. Only file/next/loop are read from the header.
- SDStore::readChunk (SDStore.cpp:178) opens, seeks, reads, closes under the SD
  lock: safe to call per refill.
- check_lift_motion.py compiles a host C++ test with plain g++ (no pio test).
- Studio writes block style: `steps:` then `  - pose: "..."  # note` (2-space indent);
  top-level `next:` / `loop:` may sit before steps. No generator writes `steps: [`.

## Done
- PR #100 (lab results from the PC) opened; system map rebuilt on that branch.

## Next
1. Finish A52-1, `pio run -e mice_nong`, QC sequences checks, sabotage the fix.
2. A52-2 RL resume in tools/rl_compare.
3. A52-3 design + first slice; Codex task files for data generation / eval.

## Blocked
- Flashing the fix waits for the next lab day.
