# Group cheer video dance + MuJoCo player

Owner: claude:3z5k (took over from codex:10270037-9c0d, 2026-10-27)
Updated: 2026-10-27T16:53Z
Branch: claude/project-thread-3z5kgn (carries codex/cheer-video-1027 + PC staging r2)
Last commit: this checkpoint
Plan: A48-21 (Codex), A48-22, A48-23 (music pace), A48-24 (servo model + waist/shrug)

## Goal
User 2026-10-27: *ทำท่าเต้นของน้องให้หน่อย และ RL ขอจำลองในโลกจำลอง ฟิสิกส์ ได้ไหม*
and *อยากเห็นตอนจำลองด้วยให้ดูเป็น visual*. Nong follows the two group cheer
videos; answer whether RL/physics sim helps; optional sim the user can watch.

## Doing now
Clearance rounds: scratchpad cheer/rounds.sh re-makes the 4 v3 dances at SAFE.musicGapMm
0/6/12/18 and runs the sim (3 robots, lagScale 0.5-2). Then: pick musicGapMm, full QC, PR.

## File status
Baseline: origin/main ecf48c2. Codex's committed work (681bc4c and earlier) is
in the branch history; rows below are what this session changed on top.

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| nong/main_python_set_nong/web/app_parts/video_routine_sections.js + 13 files | Codex staging r2 (scene-section fallback) brought from PC | done | PC focused 1961/0; cloud full 8785/6 (6 = browser timeouts, same on main) | 61f54fd |
| nong/main_python_set_nong/web/video_follow.json | "Group dance â€”" garbled label fixed | done | check_no_mojibake | this checkpoint |
| config/resource_policy.json | Thai labels were cp1252-garbled | done | check_no_mojibake, broken-fix fails | this checkpoint |
| qc/checks/check_no_mojibake.py | new: no UTF-8-read-as-cp1252 text in served files | done | sabotage: fails on old file | this checkpoint |
| tools/nong_sim/*.py | new optional MuJoCo player | done | check_nong_sim 9/0 | this checkpoint |
| config/nong_sim.json | sim settings (data, not code) | done | check_nong_sim | this checkpoint |
| qc/checks/check_nong_sim.py | sim FK == Studio scene on bent rigs, clock == minTime, hit/home | done | sabotage: after-turn and sense breaks fail | this checkpoint |
| docs/systems.json, docs/systems/*.md | nong-sim system; rebuilt | done | systems build | this checkpoint |
| docs/PLAN.html, docs/plan_state.js | A48-22 | done | plan.py | this checkpoint |

## Facts found
- A48-23 pace: firmware NongModule PACE MUSIC [N] / NORMAL, paceCap() (NongModule.cpp ~271),
  ends on showRunning(false) / STOP. Studio music_pace.js (box "Speed limit with music",
  project musicDps, cue `pace: music N`, late() list), timing.js paceCapDps -> musicPace.cap().
  Video keys carry musicMs (pose_from_video.js after safeKeys) = the song's time per move.
- A48-24 servo model: servo_follow.js ServoFollow (lag filter -> accel-limited speed -> top speed),
  rig servoLagMs/servoAccel (guesses); tools/nong_sim/world.py _servo_step is the same model
  (check_nong_sim compares them). config/nong_sim.json servo.lagScale + robots.vary.lagScale.
- Waist/shrug from video already exist (video_rig_fit.js setBody(8 twist)/(9 roll), boxes ticked
  by default); v3 dances use waist 30-150 and shrug 80-100 (full ranges).
- Sim on v3 at music pace with the accel model: 0-4 hand hits per dance, worst follow 27-63 deg
  (elbows): servos cut corners at full speed. Clearance rounds decide musicGapMm.
- Board timing: NongModule.cpp:271 minDuration = max(max_dps floor, safety floor);
  NONG_SAFE_DPS 60 (firmware/config/esp32_hardware_nong_module.h:94) x pi/2 ease.
  This is why the v2 dances run ~3.9x slower than the song (618 s for 158 s).
- Studio tree: build_rig.js buildArm/applyPose: group = tilt * R(axis, delta) * after;
  delta = (pose-zero)*BASE_DIR*(invert?-1:1) (rig_data.js:20,383). tools/nong_sim/kinematics.py mirrors it.
- MuJoCo: explicit Euler blew up on stiff servos; `integrator="implicitfast"` is required.
- Sim on the 4 v2 sequences: no lengthened steps (Studio already planned for 60 deg/s),
  but L_hand/R_hand touch by 0.0-0.4 mm once per dance: servo lag + gravity sag use up
  Studio's 4 mm gap. Sim hand = 16 mm sphere (Studio uses hand boxes), so a lead, not proof.
- Cross-shot identity stays ambiguous in both clips (automatic_conservative.log: eligible []);
  Codex's fix = scene sections, not a weaker trust gate. Do not weaken it.
- Private v2 outputs on PC: code/.local/cheer_rig_1027/{come_and_cheer,witsawa_kriangkrai}_{left,center}_v2.{json,yaml,blend}.

## Done
- Codex staging work brought in, main merged, garbled labels fixed + check, review of
  safe_path/collision changes (post-validation of shortened legs is sound).
- RL answer to the user: no RL; deterministic checks + trajectory planning beat it here.
- tools/nong_sim: `python -m tools.nong_sim.play SEQ.yaml [more.yaml] --robots N --view`.

## Next
1. PC: `pip install mujoco`, then view the v2 dances:
   `python -m tools.nong_sim.play .local/cheer_rig_1027/*_v2.yaml --view`.
2. PC: retimed MP3s for the v2 yaml (`play:` names a file that does not exist yet) and
   the Blender previews (Codex Next 3); copy v2 json/yaml into Studio with new names.
3. Consider rig extraClearanceMm +3 for these dances (sim hand touch above).
4. Lab day: measure servo lag (config/nong_sim.json servo.lagMs is a guess) and the
   real safe_dps the user accepts; both decide how close to song speed the dance can run.

## Blocked
Cloud full QC: check_board_frame, check_link_states, check_studio_boot, check_tools_list,
check_view time out in this container's browser on main too. Hardware untested.
