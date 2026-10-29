# Smooth every robot move (shared smoother)

Owner: claude:10290804-014c
Updated: 2026-10-29 08:20Z
Branch: claude/project-thread-239u63
Last commit: this checkpoint
Plan: A54-1

## Goal
User 2026-10-29 (Thai): "the non-RL moves are jerky too, isn't there a smoother
to use, like a plugin; make every move not jerky". One reusable smoothing stage
that every motion source passes through: planner, RL, video dances, Studio
sequences, talking gestures, live moves to the board. Keep music timing, real
flicks, the 5 mm gap; never change servo numbers/axes/zero/home.

## Design (decided)
- WHY jerky: every POSE is a cosine ease that STOPS at its key
  (NongModule.cpp loop, NongMath.h ease). Dense keys (167-500 ms in the cheer
  dances) = stop-start at every key.
- Fix: pass THROUGH keys. Per key and joint an end velocity (monotone
  Fritsch-Carlson tangent, 0 at holds / reversals / ends, so flicks keep
  their peak), each move a quintic Hermite (accel 0 at keys = C2, rest to
  rest = minimum jerk). Times never change (music).
- Limits: via speed <= servo max dps x scale, peak accel <= servoAccel x
  scale (else via speeds shrink), joint never leaves its key box, and the
  path leaves the straight (checked) line by at most maxOffLineDeg; Studio
  also checks touching with collisionAt and rests that move if it touches.
- Delivery: `via: "v1..v10"` step before a pose (old boards skip an unknown
  key, logged), VIA command; board blends the next POSE as Hermite starting at
  the previous move's end on its clock. Hub streams VIA only to boards that
  declare the "via" capability.
- Config: config/motion_smooth.json (per source on/off, scales, limits).

## Doing now
Writing the Python core shared/motion? -> see File status.

## File status
Baseline: 1283955

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `docs/PLAN.html` | A54-1 row | done | plan.py | this checkpoint |
| `docs/plan_state.js` | plan mirror | done | plan.py | this checkpoint |

## Facts found
- firmware/src/modules/nong/NongModule.cpp:340-362 loop(): 50 Hz, cur = from + (target-from)*ease(t); every move ends at rest.
- firmware/src/core/SequencePlayer.cpp:150-216 steps on one deadline clock (due_), POSE reply `T=` sets the next deadline; unknown step keys are logged and skipped (safe for old boards).
- firmware/config/commands.json: step keys per command -> SeqSteps.h via firmware/tools/gen_tables.py.
- nong/.../app_parts/timeline.js:774 easeKeys(K, ms) = Studio's one path shape (preview, collision checks, ServoFollow.trace, video page).
- tools/nong_sim/board_clock.py: Python mirror of the board's clock and ease (BoardClock.target).
- main_python/hub_show.py:472 _pose_cmd: hub streams `POSE .. T ms` per step; gestures.py plan() makes steps {pose,t,hold}.
- Cheer v5 dances (/mnt/project-files/cheer/*.json): 485 keys, t 167-1333 ms.

## Done
- Plan row A54-1, this task file.

## Next
1. Python core + config, measure jerk on cheer v5.
2. JS mirror in Studio (easeKeys), YAML export via steps, parity QC.
3. Firmware VIA + native test; board_clock + hub_show + gestures.
4. QC checks + sabotage, experiment-records, full QC, PR, merge.

## Blocked
- Firmware cannot be flashed from the cloud: VIA untested on hardware.
