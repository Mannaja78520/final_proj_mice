# 2026-10-27 — Cheer dances at the music pace: speed cap, servo lag, clearance

Plan ids A48-23, A48-24. Owner claude:3z5k. All results come from fakes and the physics
player, with no real robot. Raw data is private: the project files at `experiments/2026-10-27_music_pace/`,
and on the PC `code/.local/experiments/2026-10-27_music_pace/` (git-ignored). The dances are
made from YouTube videos, so they are not stored in this public repo.

## Question
User 2026-10-27 asked two things. First, the cheer dances ran 3.9x slower than their songs; can they keep
time with no speed cap while following music? Second, does the real robot then stay clear of
itself? For the clearance, the user asked for 5 mm for servo backlash, then chose 10 mm on a decision card
because backlash adds up over the shoulder and elbow joints.

## Setup
- Dances: 4 cheer dances, two songs × two dancers (come_and_cheer 158.3 s, witsawa_kriangkrai 85 s),
  made by Studio's video pipeline (`vidBuild`, "Stay with the music" on, waist and shrug on).
- Robot: Studio's `rig_default.json`, with joint min/max and servo top speed per joint (MG90S about 400 °/s,
  PDI-1181MG 375 °/s, waist 200 °/s).
- Board clock: `tools/nong_sim/board_clock.py`, the same floor as the firmware's `nongmath::moveFloor`.
- Servo model: a first-order delay, then an acceleration-limited speed, then the top speed. Delay is 40 ms per joint (60 ms on the waist),
  and acceleration is 3000–4000 °/s² (1500 on the waist). **Both are guesses until the lab measures them.** In MuJoCo the
  joints are then held by a PD loop with stall torque from `tools/make_urdf.py`, under gravity, with printed-part density 1250 kg/m³.
- Each dance runs on 3 robots with delay scale 0.5×, 1.25× and 2×. That bounds the guess.
- A hit means a real overlap between parts of one robot (`mj_geomDistance` < 0). Hands are boxes 34×46×5 mm, as in Studio.

## Results

### Speed cap
| cap | board time / song (come_and_cheer) | board time / song (witsawa) |
|---|---|---|
| 60 °/s (safe_dps, before) | 618 s / 158.3 s (3.9×) | n/a |
| music pace, no cap (servo max) | 159.4 s / 158.3 s | 86.1–86.8 s / 85 s |

### Clearance rounds (12 sim runs per round: 4 dances × 3 delay scales)
| round | Studio base gap | extra gap with music | real-servo lengthening | runs with a hit | hits | closest mm | worst follow error ° |
|---|---|---|---|---|---|---|---|
| g0 | 4 | 0 | no | 8 / 12 | 18 | −9.6 | 27–63 |
| g6 | 4 | 6 | no | 2 / 12 | 3 | −5.9 | 28–56 |
| g12 | 4 | 12 | no | 0 / 12 | 0 | +3.1 | 39–62 |
| g0s | 5 | 0 | yes | 4 / 12 | 5 | −6.4 | 28–65 |
| g6s | 5 | 6 | yes | 1 / 12 | 1 | −0.4 | 28–55 |
| g12s (v4) | 5 | 12 | yes | 0 / 12 | 0 | > 5 | 40–57 |
| c10g7s (v5, now) | 10 | 7 | yes | 0 / 12 | 0 | > 10 (1 run within 10) | 33–55 |

The follow error is how far the simulated horn trails the board's target. It is largest on the elbows (MG90S).
Rounds g0/g6/g12 ran with Studio's base gap still at 4 mm; the s rounds at 5 mm, v5 at the
user's 10 mm. At the music pace v4 and v5 keep the same 17 mm total gap.

What the 10 mm gap costs (v5, Studio's video pipeline): poses left out because they would
touch / moves held because no clear way round was found / time vs song:

| dance | moves | poses left out | moves held | board s / song s | mean bone error vs dancer ° |
|---|---|---|---|---|---|
| come_and_cheer center | 485 | 45 | 13 | 159.4 / 158.3 | 15.3 |
| come_and_cheer left | 447 | 50 | 22 | 159.4 / 158.3 | 15.1 |
| witsawa_kriangkrai center | 253 | 22 | 6 | 88.0 / 85 | 16.7 |
| witsawa_kriangkrai left | 260 | 13 | 7 | 86.8 / 85 | 16.3 |

Studio's own checks on v4 found 0 hits at the poses, 0 hits on the legs between poses, and 0 timing violations.

### Backlash arithmetic (for the 10 mm choice)
The user reports about 1° of play per joint. Each joint's play moves the hand by about angle × the distance from that joint to the hand.
Upper arm is 129 mm and forearm 183 mm (rig dims).
- Shoulder pitch and roll: 1° × 312 mm = 5.4 mm each. Elbow pitch: 1° × 183 mm = 3.2 mm. Elbow roll on the hand paddle: about 0.8 mm.
- Worst case for one arm is 14.8 mm (all joints add up). Root-sum-square for one arm is 8.3 mm, and for two arms facing each other it is 11.7 mm.
- So 5 mm covers less than one arm's typical play. 10 mm covers about one arm's worst case and two arms' typical play.

### Saved sequences at 4 / 5 / 10 mm (Studio checker, shipped rig_default.json)
Poses that touch, then legs that touch, out of all poses. The shipped rig is not the PC's
calibrated rig, so even 4 mm flags many: a lead, to re-check on the PC.

| sequence | poses | 4 mm | 5 mm | 10 mm |
|---|---|---|---|---|
| Looooooooooooooooooooong | 52 | 21 + 6 | 23 + 4 | 32 + 4 |
| VongSungKhwa | 4 | 0 | 0 | 4 |
| hello | 3 | 1 + 1 | 1 + 1 | 3 |
| NONO | 5 | 1 + 1 | 1 + 1 | 2 + 2 |
| WonderWomen | 6 | 0 | 0 | 1 |
| all_move | 10 | 2 | 2 | 3 |
| yakyai | 9 | 7 + 2 | 8 + 1 | 8 + 1 |
| NookYung, SeiyngSung | 6, 4 | 0 | 0 | 0 |

## Compared with published work
- Santiago et al., *Overcoming Motor-Rate Limitations in Online Synchronized Robot Dancing*,
  IJCIS 2012: on a low-cost humanoid, motor speed limits break beat sync. They adapt the actuator speed and switch to a slower
  beat level. We keep the beat and instead let each move go only part of the way (`vidReachSide`), and we name the
  moves that still fall behind. https://www.atlantis-press.com/journals/ijcis/25868002
- Ahn et al. (2020, RA-L), *Generative Autoregressive Networks for 3D Dancing Move Synthesis from Music*: on NAO, replanning
  for joint speed limits and self-collision made the robot's dance differ from the original. This is the
  same trade-off we see: a bigger gap means more detours and part-way moves. https://arxiv.org/abs/1911.04069
- Sousa et al. (2011), *Humanized Robot Dancing* (NAO): they adapt mocap trajectories to the robot's
  kinematic limits, synchronised to the metre of the music. https://repositorio.inesctec.pt/items/066ffc4e-3142-4d9d-9b41-a164f4c784d4
- PlaCo humanoid solver docs: an example self-collision margin of 1 cm, with the constraint switching on at 5 cm. This is
  in line with the user's 10 mm. https://placo.readthedocs.io/en/latest/kinematics/avoid_self_collisions_constraint.html
- Servo model: a first-order lag plus dead time is the usual servo approximation. A vendor note gives a hobby-servo dead time
  of 5–20 ms (not peer-reviewed; https://www.kpower.com/insight_servo/7415.html). Identification
  from a step test is in León de la Barra et al. (IFAC 2008) and Bi et al. (robust FOPDT from step response).
  Our 40 ms delay sits above that range on purpose (it is conservative) until the bench measurement (lab-day.md A48-24).

## Settings now in the repo
`safe_path.json` has clearMm (every collision check) and musicGapMm 12 (added at the music pace). The rig has servoLagMs and
servoAccel. `config/nong_sim.json` has lagScale and vary.lagScale.

## Open
- Measure the delay and acceleration per joint on the bench, then rerun these rounds with the measured values.
- Run the real-robot speed ramp from lab-day.md and record the last good music cap here.
