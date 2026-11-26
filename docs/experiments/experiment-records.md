# Experiment records (raw numbers)

One section per lab session. Raw values only; conclusions go in the plan task.
Hardware = real nong #67 (chip B4BFE91C5A74) on hotspot "manny"; sim = tools/nong_sim.

## 2026-10-28 lab (PC, nong #67 at 192.168.137.92)

### Setup
- main 14fa8fc; firmware `pio run -e mice_nong` 1,638,416 bytes, md5 b9d7e744390aceae3f692c179405bea6.
- OTA over WiFi: 200 `OK updated, rebooting into the new firmware`; after reboot `OTA running=app0 size=1638416`.
- Board config after flash: `CFG safe_dps=190`, `PACE NORMAL cap=190 deg/s`.

### Sim, v5 cheer dances (MuJoCo 3.17.0, default rig, 1 robot)
| Dance | hits | near | behind music | worst follow |
| --- | --- | --- | --- | --- |
| come_and_cheer_left_v5 | 0 | 0 | 0.00 s | 45.7 deg L_EL_P |
| come_and_cheer_center_v5 | 0 | 0 | 0.00 s | 44.5 deg L_EL_P |

### Hardware 1: slow joint sweep (person watching, 18:52 Bangkok)
Each joint home +15, -15, home (SHRUG +-5), `JOINT <n> <deg> T 1500`, over WiFi /api/cmd.
- 30/30 commands answered `OK`; command round trip 54-150 ms (median ~95 ms).
- PERF after: loop_avg_us=2003, frame_max_ms=21, heap_min=130796, lock_max_us=473945 (by OTA query, not a move).

### Hardware 2: palm turn + A48-6 poses (camera 0 side view, 19:00 Bangkok)
- Palm turn proxy per hand: EL_P 60 then EL_R 135 / 45 / 90, `POSE ... T 1500`: 10/10 `OK`.
- A48-6: home, A arms forward, B arms out, C elbows bent + waist 110, T 2500, hold 5 s: 5/5 `OK`.
  PERF after: loop_max_us=5013, frame_max_ms=21, lock_max_us=3050.
- Waist facing camera 0: WAIST 50 = front view; 90 = three-quarter; 130 = side. Snapshots in .local/lab_1028/w*.jpg (not in git).

### BUG: MOVE of a large show file crashes the board
- `MOVE ccl_v5_p060.yaml` (come_and_cheer_left_v5, 447 poses, ~30 KB): /api/cmd gives no reply in 60 s,
  then the board restarts: `PERF? ... boots=4 reset=CRASH` (twice: boots 2 -> 4). Session cookie lost (401).
- `MOVE bench-check.yaml` (231 B): `OK playing` in 114 ms. LhongMarePing.show.yaml is 3.8 KB.
- Suspect: SequencePlayer::startAt -> SDStore::loadYaml deserializeYml of the whole file under the
  router lock in the async_tcp task (firmware/src/core/SequencePlayer.cpp:54, SDStore.cpp:68): watchdog or heap
  (heap_big=110580). Not fixed today.
- Workaround used: split into 30-pose files chained with `next:` (15 files, ~2 KB each), `pace: music N` in each.

### Hardware 3: A48-23 pace ladder, come_and_cheer_left_v5 (no music file on SD; WAIST -40 to face camera 0)
Planned length 134.9 s (sum of T). 15 chained files of 30 poses, `pace: music N`. Video .local/lab_1028/ccl_v5_cap*.mp4.

| cap deg/s | wall s | x planned | PACE? during | PACE? after | loop_max_us | frame_max_ms | lock_max_us | heap_min | seen on camera |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 360.3 | 2.67 | MUSIC cap=60 | NORMAL cap=190 | 70397 | 85 | 65360 (MOVE) | 127664 | full dance, no knock seen (24-frame sheet) |
| 90 | 262.1 | 1.94 | MUSIC cap=90 | NORMAL cap=190 | 73060 | 87 | 71156 (loop) | 124300 | full dance, no knock seen; right hand passes close in front of the wooden cabinet |
| 180 | 171.3 | 1.27 | MUSIC cap=180 | NORMAL cap=190 | 87469 | 98 | 83816 (MOVE) | 124300 | full dance, no knock seen; motion blur on the hands |
| 270 | 163.4 | 1.21 | MUSIC cap=270 | NORMAL cap=190 | 98158 | 107 | 94356 (MOVE) | 124300 | full dance, no knock seen |
| 0 (servo max) | 136.9 | 1.01 | MUSIC cap=servo max only | NORMAL cap=190 | 97366 | 111 | 93625 (loop) | 124300 | full dance, no knock seen; a person reached in near the end (frames 21-23) |

come_and_cheer_center_v5 (planned 137.4 s, 15 files of 33 poses, same WAIST -40):

| cap deg/s | wall s | x planned | loop_max_us | frame_max_ms | lock_max_us | seen on camera |
| --- | --- | --- | --- | --- | --- | --- |
| 180 | 173.0 | 1.26 | 109040 | 125 | 105125 (loop) | full dance, no knock seen |
| 0 (servo max) | 139.8 | 1.02 | 124041 | 129 | 118883 (MOVE) | full dance, no knock seen; waist hit 30 (clamp) in the turns |

CAVEAT on both tables above: WAIST -40 (to face camera 0) was clamped at the 30 deg limit for
398/447 left poses and 228/485 center poses, so the waist barely moved: the arm speeds were
tested, the waist speed was NOT. Re-run without the offset below.
- frame_max_ms and loop_max_us grow with the cap (85 -> 129 ms, 70 -> 124 ms): chained file loads
  (`lock_by=MOVE`) and the module loop; no reboot in any run (boots stayed 4).
| 0, NO waist offset (true dance) | 136.8 | 1.01 | MUSIC cap=servo max only | NORMAL cap=190 | 120089 | 132 | 115728 (MOVE) | 124300 | full dance incl. waist, no knock seen |

### A48-24 servo delay (NOT measured)
- 40 deg steps `JOINT <j> <deg> T 80` on L_SH_P, L_EL_P, R_SH_P, R_EL_P, WAIST: board raised every T to
  330 ms (`OK L_SH_P=130.0 T=330ms`, the physical floor). The camera motion detector (cam0 ~30 fps,
  frame difference) saw no motion: threshold or crop wrong. Needs a 240 fps film or a better detector.

### Not run today
- last.yaml from http://nong.local/ (no last.yaml on the SD; /moves has LhongMarePing.show.yaml, bench-check.yaml, all.yaml).
- TALK ON with the phone mic, Studio Video tab sound on the robot, Studio palm flip button (needs the hub
  login in a browser), gachapon board (not on the bench), A26-99/A26-71/A26-92/A16-1/A20-3.

### RL compare (tools/rl_compare, RTX 5070 Ti Laptop GPU, cuda)
- `--quick`: 998 s wall (RC 0), out .local/rl_compare/quick/index.html.
- Full run started 19:07 Bangkok, stopped by hand at 19:35 (user leaving) during
  come_and_cheer_left_v2 / firmware_5mm round 12/20: ~115 s per training round
  (round 5 reward 0.905, round 12 reward 0.939, boneMusicDeg ~18.9, boneShapeDeg ~17.5).
  Estimate for the full config (4 dances x 3 scenarios x 20 rounds): ~8 h.
- Saved per round: .local/rl_compare/come_and_cheer_left_v2/firmware_5mm/round_NN/{policy.pt,motion.npz,round.json}.
  run.py only skips a run whose round_20/round.json exists, so this run restarts from round 1 (no resume yet).

### RL compare full run (PC, 2026-10-28 19:47 to 2026-10-29 12:49 Bangkok)
Same GPU, cuda, torch 2.11.0+cu128; 4 dances x 3 scenarios x 20 rounds x 60 updates. Detached driver
`.local/rl_compare/run_rest.ps1`; come_and_cheer_left_v2/firmware_5mm ran last and RESUMED from round 12
(PR #102 resume), so its set wall is the second leg only. Full tables per set (all metrics, both planner
variants): docs/experiments/rl_compare_results.md. Curves: docs/experiments/figures/rl_curve_*.png.

TIMING CAVEAT: the GPU/CPU was shared all night (nong_sim record 19:57-21:30, Codex MuJoCo renders
22:30-23:55, YOLO training 01:50-11:35), so s/round ranges 137-438 s; the clean rate on this GPU is
~115 s/round (2026-10-28 19:07 run). Use RL train seconds only as an upper bound.

| dance | scenario | set wall s | RL train s | s/round | RL music deg | RL shape deg | planner_music music deg | planner_music shape deg | planner_music plan s / board s |
|---|---|---|---|---|---|---|---|---|---|
| come_and_cheer_center_v2 | firmware_10mm | 4613 | 3578 | 179 | 19.0 | 17.1 | 50.1 | 12.3 | 11.5 / 467 |
| come_and_cheer_center_v2 | firmware_5mm | 3354 | 2779 | 139 | 18.9 | 16.8 | 50.1 | 12.3 | 11.7 / 467 |
| come_and_cheer_center_v2 | servo_5mm | 4172 | 3321 | 166 | 12.8 | 11.1 | 42.2 | 13.0 | 12.9 / 167 |
| come_and_cheer_left_v2 | firmware_10mm | 3448 | 2871 | 144 | 18.8 | 17.3 | 45.4 | 11.2 | 12.8 / 475 |
| come_and_cheer_left_v2 | firmware_5mm | 1696+1843 (2 legs) | 2744 | 137 | 19.0 | 17.4 | 45.4 | 11.2 | 10.2 / 475 |
| come_and_cheer_left_v2 | servo_5mm | 3477 | 2915 | 146 | 11.8 | 10.8 | 40.3 | 11.9 | 12.7 / 169 |
| witsawa_kriangkrai_center_v2 | firmware_10mm | 9703 | 8763 | 438 | 19.5 | 18.3 | 51.1 | 12.7 | 6.8 / 272 |
| witsawa_kriangkrai_center_v2 | firmware_5mm | 7636 | 6932 | 347 | 18.9 | 18.0 | 51.1 | 12.7 | 6.5 / 272 |
| witsawa_kriangkrai_center_v2 | servo_5mm | 6128 | 5521 | 276 | 13.2 | 12.8 | 46.7 | 13.4 | 7.3 / 92 |
| witsawa_kriangkrai_left_v2 | firmware_10mm | 6421 | 5621 | 281 | 23.3 | 20.4 | 47.4 | 12.4 | 8.4 / 280 |
| witsawa_kriangkrai_left_v2 | firmware_5mm | 3883 | 3321 | 166 | 20.4 | 18.5 | 47.4 | 12.4 | 7.3 / 280 |
| witsawa_kriangkrai_left_v2 | servo_5mm | 6139 | 5389 | 269 | 13.0 | 12.6 | 44.5 | 13.1 | 9.0 / 92 |

"music deg" = bone error on the song's own clock; "shape deg" = bone error ignoring timing.
Songs: come_and_cheer 158 s; board s = how long the planner's show runs on the board.

## 2026-10-29 lab (PC): 30 FPS pose, gap bridging, hybrid, smoothing

User 2026-10-29: arms drop and miss the flicks; 43-45 s the planner matched better than RL; 45-46 s the
dancer's arm swings behind the body; asked for 30 FPS measurement, no speed cap ("if the song is fast,
move fast"), one smoothing stage for every method, and a record of RL's training cost against its gain.

### Causes found (come_and_cheer_center_v2, 6 FPS)
- Pose sampled at 6 FPS (951 samples / 158 s): a swing shorter than ~0.2 s falls between samples.
- Untrusted arm samples: arm 0 18.1 %, arm 1 17.0 % of the song (e.g. 43.83-44.83 s, 45.17-47.17 s).
  The reference held the last trusted direction there and the RL reward gave those frames weight 0,
  so the policy was free to let the arm fall.
- Studio's pose smoother (video_follow.json smoothing, maxTargetDps/accel limits, reversal removal)
  feeds the planner only: 30 FPS full song reversals 1112 -> 0 (90 after repair), largest step 130 -> 8 deg.
  Not separated into noise vs real flicks. The smoother thread (A54) reports fixing this config.

### Changes (tools/rl_compare, config/rl_compare.json)
- Pose re-measured at 29.97 FPS (every 2nd frame of the 59.94 FPS source; same YOLO + MediaPipe crops,
  appearance and re-id as cheer_rig_1027) -> 5044 frames, CPU, ~16 min; Studio retarget (current
  qc/data/video_group.cjs) -> 4751 samples, 2 min. Private: .local/cheer_rig_1029_30fps.
- `data.fillGapS` 1.0: untrusted runs up to 1 s are bridged between the trusted samples on both sides;
  `rl.fillWeight` 0.5 = weight of a bridged arm in the RL reward. Scores still use trusted samples only.
  30 FPS: trusted arm 0 83.5 % / arm 1 78.0 %, bridged 9.1 % / 18.1 %; 42-48 s fully covered on arm 0.
- `hybrid`: RL with planner_music spliced in where its 0.5 s mean per-frame error is > 5 deg lower,
  0.3 s cross-fade.
- `smooth` (prototype): zero-phase Savitzky-Golay, 0.24 s window, order 3, on the 50 Hz board commands,
  then the same servo model. To be replaced by the shared A54 smoother once merged.
- run.py `--data-dir`, `--out` to run a second data set without touching the v2 results.

### Results: come_and_cheer_center, servo_5mm (no board cap, servo max ~375-400 deg/s, 5 mm gap)
Same GPU (RTX 5070 Ti Laptop, cuda), nothing else running: RL 20 rounds x 60 updates = 2417 s train
(121 s/round), 18.5 s to perform the song. Wall 3151 s for the whole set incl. planners and videos.

| reference | contender | music deg | P95 deg | shape deg | jerk RMS deg/s^3 | drift end s | min gap mm | Studio flags | compute |
|---|---|---|---|---|---|---|---|---|---|
| 6 FPS v2 | planner_shape | 44.0 | 122.1 | 9.3 | 15125 | 32.9 | 6.0 | 1 | 18.4 s plan |
| 6 FPS v2 | planner_music | 42.2 | 122.1 | 13.0 | 16835 | 8.7 | 24.2 | 0 | 12.9 s plan |
| 6 FPS v2 | rl | 12.8 | 71.0 | 11.1 | 17437 | -0.1 | 13.0 | 0 | 3321 s train (shared GPU) |
| 30 FPS | planner_shape | 38.7 | 114.5 | 12.7 | 34116 | 9.5 | 10.2 | 2 | 12.3 s plan |
| 30 FPS | planner_music | 28.1 | 97.4 | 14.9 | 25691 | 1.9 | 15.2 | 0 | 15.3 s plan |
| 30 FPS | rl | 15.1 | 68.9 | 12.9 | 25626 | 0.0 | 17.6 | 0 | 2417 s train |
| 30 FPS | hybrid (3 % planner) | 14.5 | 61.3 | - | 26369 | 0.0 | 17.6 | 0 | rl + plan |
| 30 FPS | planner_shape + smooth | 38.7 | 114.6 | 12.7 | 11482 | 9.5 | 9.3 | 1 | +<1 s |
| 30 FPS | planner_music + smooth | 28.1 | 97.2 | 15.0 | 10244 | 1.9 | 14.1 | 0 | +<1 s |
| 30 FPS | rl + smooth | 15.1 | 68.9 | 13.0 | 9638 | 0.0 | 17.5 | 0 | +<1 s |
| 30 FPS | hybrid + smooth | 14.5 | 61.4 | - | 10121 | 0.0 | 15.6 | 0 | +<1 s |

Per-second music error, 30 FPS (deg): 42-43 / 43-44 / 44-45 / 45-46 / 46-47 / 47-48 s
- planner_music: 19 / 31 / 28 / 31 / 38 / 30
- rl:            19 / 52 / 30 / 21 / 10 / 5

Notes
- 6 FPS and 30 FPS rows score against different references (30 FPS holds faster, more detailed
  motion and more trusted samples), so "music deg" is not comparable across the two blocks. The
  30 FPS RL also had gap bridging on; the two changes were not run apart (no time at the lab).
- Cost vs gain at 30 FPS: RL needs ~40 min GPU training per dance and setting once, then 18 s per
  performance; the planner needs ~15 s. RL halves the music error (15.1 vs 28.1 deg) and is on the beat
  (0.0 vs 1.9 s late). Same direction as motion-imitation RL work (peng2018deepmimic,
  peng2020imitating in rl_compare_references.bib), where a tracking policy beats keyframe
  retargeting on timing at the cost of per-clip training.
- Smoothing cut jerk 59-66 % on every method with music error unchanged to 0.1 deg; planner_shape
  Studio flags 2 -> 1, min gap 10.2 -> 9.3 mm (still above the 5 mm gap).
- 43-44 s is still RL's worst second (52 deg); the hybrid takes the planner there.
- Sim only. Not run on the robot. RL output is 50 Hz sim commands, not yet a board sequence.

### Smoothing stage swapped for the shared smoother (cloud, 2026-10-29)

The Savitzky-Golay prototype (tools/rl_compare/smooth.py, windowS 0.24, order 3)
was replaced by the project smoother (main_python/motion_smooth.py, A54-1):
commands thinned to keys within tolDeg 3 (minKeyMs 120), keys on their music
time, the arm passing through a key where a joint keeps going. to_sequence now
writes `pass:` steps, worked out per ramp cap. The `_smooth` rows above were
made with Savitzky-Golay; they need a PC re-run (private 30 FPS data) to get
numbers for the shared smoother. Cloud QC only (synthetic): a 40 deg/s ramp's
slowest frame 17.9 deg/s passing through vs 2.4 stopping at each key.

## 2026-10-29 shared smoother, A54-1 (cloud, no hardware)

Cheer v5 dances (`/mnt/project-files/cheer/*_v5.json`, 158/87 s, their own rig), commanded path
sampled at the board's 50 Hz, finite differences over all 10 joints. "stops" = keyframes where a
joint keeps its direction (> 0.25 deg each side) yet every such joint stops (the stutter).
Script + raw JSON: `/mnt/project-files/experiments/2026-10-29_motion_smooth/` (measure.py,
results.json); Studio column from headless Studio with the real collision check (`collisionAt`,
clearMm 10 + musicGapMm 7) via a QC driver. main_python/motion_smooth.py, config
nong/main_python_set_nong/web/motion_smooth.json (maxOffLineDeg 6, unchecked 1, velScale 0.85).

| dance | keys | stops cosine | stops Studio | stops tool (1 deg) | RMS acc deg/s2 cosine / Studio | RMS jerk deg/s3 cosine / Studio | p95 jerk cosine / Studio | Studio compute s |
|---|---|---|---|---|---|---|---|---|
| come_and_cheer_center_v5 | 485 | 429 | 101 | 275 | 978 / 782 | 37349 / 28792 | 69916 / 46906 | 6.1 |
| come_and_cheer_left_v5 | 447 | 397 | 71 | 255 | 968 / 745 | 36069 / 25877 | 68757 / 43769 | 7.0 |
| witsawa_kriangkrai_center_v5 | 253 | 226 | 45 | 163 | 910 / 687 | 33241 / 22721 | 67411 / 42159 | 2.2 |
| witsawa_kriangkrai_left_v5 | 260 | 238 | 35 | 179 | 973 / 681 | 36376 / 22785 | 73058 / 43523 | 3.0 |

- Studio (collision-checked) = within 1 stop of the no-collision bound (100/71/45/35): the curves almost never touch.
- Peak speed and peak speed-up are unchanged (618.6 deg/s, 13639 deg/s2 on center): the fastest moves are
  rest-to-rest flicks and stay the cosine. Keyframe times unchanged (music).
- Board model (tools/nong_sim/board_clock, pass rules of NongModule::passMove), tool output: 207/485,
  191/447, 85/253, 83/260 moves played as the curve; board length unchanged (159.4 s center).
- Shape choice (center, before the final rules): quintic with speed-up 0 at keys RMS jerk 40571 (worse than
  the cosine's 37349: it overshoots and its vias shrink), cubic Hermite 28421. Off-line limit sweep:
  3 deg -> 136 stops, 6 -> 100, 12 -> 98.
- Video clean-up (QC, synthetic 30 fps): a 230 ms 22 deg flick kept at 20 deg (the old 240 deg/s,
  900 deg/s2 limits stall it at about 10); a one-frame 20 deg spike drops to 0.
- Paper comparison: the via speeds are Fritsch & Carlson (1980) monotone tangents, so no joint passes a
  keyframe (no overshoot into the 5 mm gap); rest to rest the cosine is kept rather than Flash & Hogan's
  (1985) minimum-jerk quintic, because at fixed music times the quintic needs 17% more peak speed-up
  (5.77 vs 4.93 x D/T^2) and measured rougher here.
- NOT run on hardware: firmware PASS builds (`pio run -e mice_nong`) and passes `pio test -e native`
  (48 cases) only.

## 2026-10-29/30 night (PC): following the dancer's lifts, reach fitting and five ideas

User 2026-10-29: the robot stays low when the dancer lifts an arm. Cause measured: shoulder pitch at its
25 deg stop (180 deg servo through 14:19 gears = ~132 deg joint). Static best fit of the missed frames
reached the dancer's height in 28 % of them, every fit at a joint limit (L_SH_P min 95 %, R_SH_P min 77 %).
A copied-rig sim of the gears turned 40 deg (SH_P -15..115): mean bone error 7.6 -> 4.0 deg, lifts
reached 38 -> 81 %, Studio flags 74 -> 90 of 1585 (static per-frame fits, not collision-avoiding). The user
chose NOT to change the gears and asked for lifts that look like the dancer's: reach.py (reach fitting).

Yardstick for every row below: come_and_cheer_center_30fps, servo_5mm, scored against the dancer's own
arms (rawMusicDeg), liftCorr = correlation of upper-arm height robot vs dancer, "lift follow" = share of
dancer samples with the upper arm > 30 deg up where the robot's is > 15 deg up. All rows: 0 Studio flags,
drift at the end within 0.13 s. jerk = RMS 3rd derivative of servo angles, deg/s^3.

| run | change | lift follow % | liftCorr | vs dancer deg | jerk | rl_smooth jerk | train s |
|---|---|---|---|---|---|---|---|
| 30 FPS, no reach | - | 57 | 0.903 | 15.1 | 25626 | 9638 | 2417 |
| reach (default) | reach fitting on | 89 | 0.961 | 15.2 | 27297 | 10306 | 2585 |
| 1 lead | commands sent 20 / 40 / 60 ms early (post-hoc) | 86.9 / 84.6 / 81.5 | 0.958 / 0.952 / 0.943 | 15.3 / 15.7 / 16.3 | - | - | 0 |
| A_lift03 | rl.reward.lift 0.3 (upper-arm height term) | 92 | 0.979 | 15.9 | 29797 | 11297 | 7916* |
| B_reach95m2 | reach.dancerTopPct 95, marginDeg 2 | 97 | 0.960 | 15.2 | 28476 | 10905 | 8001* |
| C_shrugfree | shrug left out of the body reward | 86 | 0.961 | 15.3 | 27250 | 10363 | 8059* |
| D_fill2s | data.fillGapS 2.0 | 90 | 0.952 | 15.5 | 27280 | 10444 | 8065* |
| E_smooth05 | rl.reward.smooth 0.5 | 92 | 0.950 | 15.9 | 21041 | 7837 | 8075* |

\* A-E ran six at once on one GPU (plus come_and_cheer_left): 355 s/round instead of ~120 s alone; GPU 83 %,
4.7 of 12 GB, 79 C; RAM was the limit (3.1 of 31 GB free). The PC rebooted at 23:03 mid-run; runs resumed
from their saved rounds.

Notes
- Lead hurts: the policy already looks 0.2-0.8 s ahead and was trained through the servo model's lag.
- A's hybrid touched (min gap -21.8 mm approx): the splice between RL and planner_music is not
  collision-aware. to_sequence refuses such a file; use rl there.
- Best for the user's goal (follow AND smooth): B + A + E together -> the final run below.
- Commands: `python -m tools.rl_compare.run --set <key>=<json>` (new) for each variant; scripts in the
  private .local/cheer_rig_1029_30fps (lead_check.py, compare_reach.py, lift_exps.sh).

### Final: B + A + E on all four dances (PC, 2026-10-30 02:06-04:01 Bangkok)
`--set reach.dancerTopPct=95 --set reach.marginDeg=2 --set rl.reward.lift=0.3 --set rl.reward.smooth=0.5`,
main c67e631 + this branch, four runs at once on the RTX 5070 Ti Laptop (~320 s/round, 6273-6333 s train each).
Same yardstick as above (vs the dancer's own arms). "before" = reach default (.local/rl_compare_30fps_reach).

| dance | method | lift follow % | liftCorr | vs dancer deg | jerk | Studio flags |
|---|---|---|---|---|---|---|
| come_and_cheer center | planner_music | 44 | 0.668 | 28.8 | 25798 | 0 |
| come_and_cheer center | rl before | 89 | 0.961 | 15.2 | 27297 | 0 |
| come_and_cheer center | rl final | 98 | 0.979 | 15.8 | 25033 | 0 |
| come_and_cheer left | planner_music | 57 | 0.623 | 30.7 | 27357 | 0 |
| come_and_cheer left | rl before | 96 | 0.967 | 13.2 | 27229 | 0 |
| come_and_cheer left | rl final | 100 | 0.985 | 16.6 | 23096 | 0 |
| witsawa center | planner_music | 44 | 0.677 | 36.9 | 31270 | 0 |
| witsawa center | rl before | 84 | 0.968 | 15.8 | 33324 | 0 |
| witsawa center | rl final | 98 | 0.981 | 16.0 | 29813 | 0 |
| witsawa left | planner_music | 58 | 0.695 | 32.0 | 30552 | 0 |
| witsawa left | rl before | 95 | 0.976 | 14.9 | 32402 | 0 |
| witsawa left | rl final | 99 | 0.984 | 15.2 | 30275 | 0 |

Notes
- Lift follow 84-96 % -> 98-100 %, liftCorr 0.961-0.976 -> 0.979-0.985, policy jerk down 6-15 %, at a cost of
  +0.2 to +3.4 deg vs the dancer (largest on come_and_cheer left).
- The hybrid touched on three of four dances (Studio flags 5-8; min gap approx down to -21.7 mm): the
  RL/planner splice is not collision-aware. to_sequence refused those and the board files use rl;
  witsawa center's hybrid was clear and is used.
- The shared smoother (main, keys + pass vias) RAISED jerk on these dense RL motions: rl 25033 -> rl_smooth
  33168 (come_and_cheer center), 29813 -> 39922 (witsawa center). Thinning to keys every ~190 ms and
  stopping where a joint turns back adds stops the 50 Hz policy did not have. The SG prototype gave
  27297 -> 10306 on the same kind of motion. The board files are this keyed, pass-smoothed motion
  (board jerk 31753-40010 in sim). Open question for the smoother thread: a denser key budget for RL.
- witsawa left drift end -4.97 s is the DTW tail (music-clock error 15.2 deg is normal); not a timing slip.
- Board files (private): .local/robot_1030/{moves,music} + README_TH.md; prefixes fc/fl/wc/wl, caps 120/240/0,
  14-15 chained files each, largest 8.1 KB (come_and_cheer). Studio 0 flags at 5 mm for every file set.
- Sim only. Nothing run on the robot.

## 2026-11-04 think-model bench (PC, voice "think" job, no robot)

Setup: RTX 5070 Ti Laptop 12 GB (0 MiB used before each run, face app not running), Core Ultra 9 275HX, 31 GB RAM.
Same system prompts as apps/voice/service.py, 4 FAQ items (llm/qa_data.json), greedy, budget th 96 / en 48 /
ja,zh 64 / ko,lo 96, one wrong-language retry. 38 questions: th 15, en 5, zh 5, ja 5, ko 5, lo 3.
Runner: Ollama 0.34.2 second instance 127.0.0.1:11435, models on D:\local-ai, num_ctx 2048. llama.cpp download
was blocked (permissions), so the 30B MoE models were split by layers (num_gpu 14/48), not --n-cpu-moe.
Raw rows + answers: .local/think_bench_2026-11-04/*.json (not in git), script bench.py, SUMMARY.md.

| model | GPU layers | VRAM MB | median 1st token s | median tok/s | median answer s | lang ok 1st try | Thai ends ครับ | Thai grade /30 | other grade /46 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen2.5-0.5B-Instruct (transformers) | all | 1214 | 0.13 | 35 | 0.45 | 35/38 | 8/15 | 10 | - |
| typhoon-ai/typhoon2.5-qwen3-4b-gguf q4_k_m | all | 3198 | 0.03 | 169 | 0.12 | 37/38 | 15/15 | 24 | 33 |
| typhoon-ai/typhoon2.5-qwen3-30b-a3b-gguf q4_k_m | 14/48 | 5598 | 0.19 | 33 | 0.82 | 31/38 | 15/15 | 23 | 29 |
| same, Ollama auto split (54% GPU) | auto | 10184 | 0.12 | 58 | 0.57 | 15/15 (th only) | 15/15 | - | - |
| unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF Q4_K_M | 14/48 | 5598 | 0.20 | 32 | 0.80 | 32/38 | 15/15 | 26 | 33 |

Notes
- Grade = 2 right / 1 weak / 0 wrong or invented, on the answer the robot would speak (after retry). By hand, one grader.
- Wrong-language answers of both 30B models are the Thai FAQ answer copied: qa_data.json has Thai answers only.
- The retry sends no FAQ, and retries invented facts (wifi refused, opens 9:00, parking in basement).
- All three new models invented a coffee shop for "แถวนี้มีร้านกาแฟไหม". Lao weak in all models.

### Re-run with the jerk-guarded smoother (main 5bc6d2e, PC, 2026-10-30 05:47-05:52 Bangkok)
Same trained policies as the four-dance final (no retrain); rl_compare re-scored with
jerkGuard + followDensePath, then to_sequence rebuilt the board files. jerk = RMS 3rd derivative of the
servo-model angles at 50 Hz. "board" = the chained board files played on BoardClock + servo model.

| dance | rl (policy) | rl_smooth before fix | rl_smooth after fix | board before fix | board after fix | Studio flags (board) |
|---|---|---|---|---|---|---|
| come_and_cheer center | 25033 | 33168 | 29989 | 33168 | 29976 | 0 |
| come_and_cheer left | 23096 | 31751 | 28225 | 31753 | 28215 | 0 |
| witsawa center (hybrid) | 29812 | 39922 | 37685 | 39827 | 37582 | 0 |
| witsawa left | 30274 | 40008 | 38394 | 40010 | 38393 | 0 |

- The fix lowers the board jerk 4-11 %, but the keyed, pass-smoothed file is still 20-27 % rougher than
  the 50 Hz policy itself (checked 2026-11-05 against rl_final_1030/*_score.json jerkRms) (keys every ~190 ms; a joint that turns back still stops). Music-clock error
  vs the fitted target moved +0.3 to +0.7 deg. All board files stay collision-free at 5 mm.
- Hybrids still touch on three dances (Studio 17-32 flagged frames); those board files use rl.
- New board files replace .local/robot_1030 (the previous set kept in .local/robot_1030_old_smoother).
- The new files are bigger: largest 9.9 KB (fc000_00; was 8.1 KB). Old firmware hung on a 30 KB show and
  played 2 KB; 5-10 KB is untested on old firmware (the PASS firmware streams per step). README_TH.md
  in .local/robot_1030 still says 8 KB.

## Ollama KV-cache quantization, typhoon25-4b (PC, 2026-11-05)
Ollama 0.34.2, RTX 5070 Ti Laptop 12 GB, model typhoon25-4b Q4_K_M, temp 0, 2 runs per config (both gave identical VRAM and
identical answers). Bench = 38 questions (th/en/zh/ja/ko/lo, num_ctx 2048); VRAM test = 8192 ctx (4098 prompt tokens).
Raw: .local/kv_bench_2026-11-05/ (PC only). Backend log confirmed the KV type each time. TurboQuant itself is not in Ollama;
q8_0/q4_0 KV with flash attention is the closest built-in.

| cfg | KV in log | VRAM @2k (MB over idle) | VRAM @8k | 8k prefill s | tok/s | first token s | lang ok /38 | Thai ครับ | invented (Thai unknowns) |
|---|---|---|---|---|---|---|---|---|---|
| A flash0 f16 (old default) | 576 MiB | 3276 | 5574 | 4.53 / 4.56 | 68 / 63 | 0.052 / 0.054 | 37 / 37 | 15/15 | 0 |
| B flash1 f16 | 576 MiB | 3188 | 5018 | 1.84 / 1.67 | 59 / 62 | 0.047 / 0.045 | 37 / 37 | 15/15 | 0 |
| C flash1 q8_0 | 306 MiB | 2922 | 3942 | 1.69 / 1.87 | 64 / 63 | 0.047 / 0.049 | 37 / 37 | 15/15 | 0 |
| D flash1 q4_0 | 162 MiB | 2778 | 3366 | 1.71 / 1.90 | 65 / 63 | 0.046 / 0.058 | 36 / 36 | 14/15 | 0 |

- C equals A on the Thai score, ครับ and invented facts. 5 of 38 replies differ in wording (th10 still correct; ko01, ko04, lo01, lo03):
  flash attention changes numerics slightly. Lao answers were not graded (Lao is weak in every model). Not byte-identical to A.
- D REJECTED: 19/38 replies differ, th03 garbled, ko01 says right instead of left (wrong fact), ครับ 14/15.
- Saving of C: ~350 MB at 2k ctx, ~1.6 GB at 8k ctx (5574 -> 3942); 8k prefill 2.5x faster. Robot normally uses ctx 2048, so the gain is modest there.
- tok/s ~63 here vs 169 in an earlier run: same for all configs (comparison holds); cause not chased.
- Decision: config/local_ai.json default = flash on + q8_0. Takes effect when Ollama is restarted with tools/ollama_serve.py.
- Not applicable: Face_Regonize (ONNX CNNs, no KV cache; see docs/friend/face_regonize_perf_2026-11-05.md) and Whisper/TTS (their
  decoder cache is small; faster-whisper/CT2 has no KV-quant option; not measured).

## 2026-11-06 Spark-TTS with the user's recorded voice as reference (PC, CPU only)

### Setup
- Recording: `.local/voice_source/recording_20261105.m4a`, 962.8 s. `tools/voice_clips.py cut`: 88 clips, 946 s, 4.26-14.46 s, mono 24 kHz
  (ffmpeg silencedetect -35 dB / 0.3 s; runs over 15 s split at the quietest 20 ms point).
- Hearing: Thaweewat/whisper-th-medium-ct2, CPU int8, beam 1, 7-16 s per clip. No GPU path on this PC today:
  torch is `2.15.0+cpu` (no `cublas64_12.dll`), so faster-whisper falls back to CPU by itself.
- Filter (`config/voice_clips.json` keep): 36 of 88 kept. Reasons (a clip can have several): unsure words 37, uneven level 23,
  looping text 6, no words 4, maybe no speech 4, too quiet 4. Level spread over all 88: p10 11.7, median 15.5, p90 20.0 dB.
- The recording is a talk with at least one other person (question and answer turns in the text): speaker identity of each clip is NOT verified. 19 clips say ครับ, 3 say ค่ะ/คะ.
- Spark server: `apps/voice/tts_spark/server.py --device cpu`, emotion neutral, temperature 0.3, gender male, speaker tokens from
  `apps/voice/tts_spark/speaker.py` (clips joined with 0.3 s pause, 30 s at most). Edge baseline: th-TH-NiwatNeural.
- Env fix needed to run it at all: the Spark venv's `torchaudio 2.11.0+cu128` cannot load its native lib against the user-site torch 2.15
  (`OSError: Could not load this library ... libtorchaudio.pyd`), so the feeling server does NOT start on this PC as is. For this test a
  `sitecustomize.py` (scratchpad, not in the repo) swallowed that OSError; MelSpectrogram is pure Python and worked. Not a fix for the helper.
- Sentences (3): "สวัสดีครับ ยินดีต้อนรับสู่ตู้มหัศจรรย์ วันนี้ให้ผมช่วยอะไรดีครับ" / "ห้องน้ำอยู่ชั้นสองทางซ้ายมือ เดินตรงไปแล้วเลี้ยวซ้ายได้เลยครับ" / "ขอบคุณที่มาร่วมสนุกกับเรา แล้วพบกันใหม่นะครับ".
- CER = character edit distance / reference length, spaces and punctuation ignored, heard by the same Thai whisper (`tools/voice_spark_test.py`).

### Variants (budget 3)
- A = clip_0059 (rank 1, 11.9 s). B = clip_0059 + clip_0082 (ranks 1-2, 24.7 s). C = clip_0046 + clip_0047 + clip_0087 (ranks 4, 5, 6; 27.1 s).

### Raw numbers
| voice | CER s1 | CER s2 | CER s3 | mean CER % | make s (s1/s2/s3) | audio s (s1/s2/s3) |
| --- | --- | --- | --- | --- | --- | --- |
| Edge Niwat (this run) | 19.0 | 0.0 | 0.0 | 6.3 | 1.0 / 0.7 / 0.6 | 5.1 / 4.2 / 3.7 |
| Spark ref A | 7.1 | 8.7 | 0.0 | 5.3 | 14.5 / 12.7 / 8.4 | 6.1 / 5.5 / 3.7 |
| Spark ref B | 9.5 | 4.3 | 0.0 | 4.6 | 17.6 / 13.4 / 10.3 | 6.2 / 5.2 / 3.9 |
| Spark ref C | 16.7 | 0.0 | 5.9 | 7.5 | 10.1 / 15.0 / 10.4 | 4.1 / 5.5 / 4.0 |

- Noise floor: an earlier run of the same Edge files gave 11.9 / 0.0 / 0.0 (mean 4.0) for sentence 1, so whisper's hearing alone moves a 3-sentence mean by about 2 points.
- Best gain over Edge: B, 6.3 - 4.6 = 1.7 points (A 1.0, C -1.2). Under the 2% stop rule and inside the noise: stopped, no further variants.
- Speed: Spark on CPU 8-18 s for a 4-6 s line; Edge 0.6-1.0 s.
- C's first line came out as "สวัสดีค่ะ" (whisper heard ค่ะ): the reference mix (one clip may be a different speaker or a woman) leaked into the sentence ending. Not verified by ear.
- Not measured: whether it sounds like the user (CER only tests clarity). Needs a person's ear.

### 2026-11-06 rerun on GPU (one round, same sentences and references)
- Spark venv repaired first: torch 2.11.0+cu128 + torchvision 0.26.0+cu128 in `.local/tts_spark/venv`; server on cuda:0 (RTX 5070 Ti), `tools/voice_spark_test.py --device cuda`.
| voice | CER s1 | CER s2 | CER s3 | mean CER % | make s (s1/s2/s3) | audio s (s1/s2/s3) |
| --- | --- | --- | --- | --- | --- | --- |
| Edge Niwat | 11.9 | 0.0 | 0.0 | 4.0 | 0.8 / 0.6 / 0.8 | 5.1 / 4.2 / 3.7 |
| Spark ref A | 16.7 | 8.7 | 0.0 | 8.5 | 7.5 / 4.1 / 2.6 | 6.6 / 5.6 / 3.8 |
| Spark ref B | 16.7 | 15.2 | 5.9 | 12.6 | 4.2 / 3.4 / 2.7 | 5.5 / 4.7 / 3.9 |
| Spark ref C | 16.7 | 8.7 | 0.0 | 8.5 | 3.7 / 3.4 / 2.7 | 4.9 / 4.9 / 3.7 |
- Spark is sampled: the same references gave A 5.3 / B 4.6 / C 7.5 on CPU and 8.5 / 12.6 / 8.5 here, so run-to-run spread (about 8 points) is larger than any gap between references. No reference beats Edge in either run on both.
- GPU speed: 2.6-7.5 s per line (first line includes warm-up) against 8-18 s on CPU; Edge 0.6-0.8 s.

## 2026-11-21 Local AI latency (keep-alive)
- Question: does the first answer after a quiet spell cost a model reload?
- Change: `keepAlive` 1h and `numParallel` 1 in `config/local_ai.json` (Ollama default is 5m).
- Measuring tool: `python tools/ai_latency.py --out docs/experiments/2026-11-21_ai_latency.json`
  (1 cold round after unload + 3 warm rounds, Thai + English, first word and whole answer).
- Budget: 4 rounds. Stop rule: stop tuning under 10 % gain.
- Raw numbers: NOT RUN yet. This was prepared in the cloud (no GPU, no Ollama); needs the PC. No speed claim is made until then.

### 2026-11-21 result (PC, RTX 5070 Ti, Ollama q8_0 KV, typhoon25-4b; `tools/ai_latency.py --rounds 3`, short answers of 13-23 tokens)
| state | lang | first word s | whole answer s | tokens/s |
| --- | --- | --- | --- | --- |
| cold (model not loaded) | th | 44.97 | 46.31 | 17.1 |
| cold, model already loaded by the call before | en | 0.04 | 0.14 | 128.7 |
| warm x3 | th | 0.022-0.032 | 0.178-0.205 | 133-155 |
| warm x3 | en | 0.021-0.035 | 0.114-0.178 | 91-141 |
- Reading: the only slow part is the first model load (about 45 s). Warm answers are under 0.2 s, so streaming LLM->TTS would save at most about 0.15 s: NOT worth building (under the 2% / no-gain stop rule). The speech part (TTS 0.6-7.5 s, STT not measured) is where time goes.
- Change made from this: `local_ai.warm()` loads the model when the voice helper starts (if Ollama is already up) and on the Load-the-AI button; keepAlive 1h keeps it loaded. Effect of the warm-up itself not yet re-measured on the PC.
- Not measured: STT on a 3 s clip; TTS Edge vs Spark in this run.

### 2026-11-21 Edge TTS silent on the PC
- edge-tts 7.3.1 (newest), network to speech.platform.bing.com:443 ok. th-TH-PremwadeeNeural: NoAudioReceived (with and without rate/pitch, 3 runs). th-TH-NiwatNeural same text: 19008 bytes in 0.89 s. CLI with Niwat: 11232 bytes. Cause: the service returned nothing for Premwadee at that moment (temporary or not: not tested).
- Fix: `tts.fallbackVoices` in config/voice.json + retry in `_edge_speak` (QC voice_edge_fallback). Niwat is a male voice: the robot may say ค่ะ in it; set the fallback list to taste.
### 2026-11-21 PC re-measure after warm-up (main 0dd9955, same PC)
- `local_ai.warm()` after unloading the model (keep_alive 0): 3.04 s (returned loaded). One Thai chat right after: 0.184 s. Earlier cold first call: about 45 s. CAUTION: this load was with a hot file-system cache, so 3 s is a re-load; the 45 s run was a true first load from disk. Both are real; the warm-up moves either off the visitor's first question.
- `ai_latency.py --rounds 1` right after warm: Thai first word 0.025 s, whole 0.173 s, 155 tok/s; English 0.038 / 0.124 s.
- `run_bench.py` (voice helper up): all 25 cases typed text, so STT NOT measured. Answer median 46 ms. Answer hits 1/25: wording differs from the expected saved answer (scoring, not speed; not investigated).
- TTS: POST /say Thai sentence, 3 runs: 4.99 / 4.73 / 4.69 s, each a JSON error "edge: NoAudioReceived ... local: it gave back an empty sound". Edge TTS was FAILING on the PC at this moment (cause not investigated: offline, edge_tts version, or voice name), so these are time-to-failure, not speech. Spark not timed.


### Round 2: q8_0 vs f16 with the face app running, 93 extra cases, real browser (PC, 2026-11-05)
Same Ollama 0.34.2 / typhoon25-4b. A = flash off + f16 (old), C = flash on + q8_0 (new). Cases went through the voice helper `/ask`
(33 own + 60 proposed by Codex CLI 0.166 and reviewed by hand: mixed languages, long context, 8-turn history, exact copy, noise,
injection, language switch). Face_Regonize backend (port 8000) was running; an extra read-only loop of its det+rec models
(~12 ms/image) ran on the same GPU during the "face" runs. Raw: .local/kv_bench_2026-11-05/verify2/ (PC only).
- Answers: 81 of 93 identical A vs C; the 12 that differ are wording, except one price case (see below). Language of reply equal in both.
- Unknown-price questions (25 asks, run twice per config): invented-looking numbers A 10 and 3, C 4 and 4. A is not repeatable at
  temperature 0 either (11 of 25 same on repeat), so one case where C invented a price (x02) is noise, not a q8_0 effect.
  Both configs invent a number when the prompt forces "exact baht"; wifi password asked in Lao is wrong in both.
- Speed: median /ask 2.98 s (C) vs 3.89 s (A) alone; 3.29 s vs 4.50 s beside the face loop. 6 asks at once: same wall time (15.4 s).
- VRAM total on the 12 GB card (face backend + voice helper Qwen + Ollama): peak 10.44 GB (C) vs 10.87 GB (A) with the face loop;
  idle-ish 9.72 vs 10.54 GB. Headroom with face load: C ~1.8 GB, A ~1.4 GB. Face speed unaffected (12.1 vs 12.5 ms median).
- Browser (Edge via Playwright, throwaway QC hub, Voice page): 13 typed questions th/en/lo/zh/ja/ko/mixed, repeat, language
  switch, injection: all replied, language and source badge right, text box cleared, no console error except favicon 404.
  Ollama stopped: saved answers unchanged, model questions answered by the Qwen fallback (slower, 4-7 s, weaker Lao/injection reply).
- Verdict: nothing clearly worse on q8_0; config/local_ai.json stays q8_0 + flash.

## 2026-11-25 QC wall time: slowest-first ordering and timing report
Question (user): why does full QC take so long, could the checks run at once? Finding: `qc/run_qc.py` already runs them in a pool
(plain checks on `workers`, browser checks on `browserLanes`=6); 29 SOLO checks (shared port 80/5353, shared files, or timing-sensitive
with a measured starved-margin history, see the comments in run_qc.py) run one by one after the pool. Nothing was weakened.
Change: each full run saves per-check seconds (qc/last_timing.json, seed qc/data/qc_durations.json) and starts the slowest checks first;
the run prints phase/lane times and the 12 slowest checks.
Setup: cloud container, 4 cores (so 2 plain workers, 6 browser lanes), same tree, same env-only failures (no PlatformIO/torch/mujoco).
- Old runner (main 8452142): wall 675.3 s, 10456 passed, 15 failed (13 env-only + 2 system-map headers stale, fixed here).
- New runner: wall 651.2 s, 10458 passed, 14 failed (all env-only except the same stale headers). Same pass/fail per check.
- Gain 24 s (3.6%) on this box: within run-to-run noise, so not a proven speed-up.
- Where the time goes (new runner): pool phase 400 s, solo phase 250 s (38% of wall). Sum of check time 2100 s (x3.2 overlap).
  Browser lane: 128 checks, 1452 s of work over 6 lanes (~242 s lower bound); longest single check_video_page 233 s,
  check_visual_language 109 s, check_theme_contrast 92 s, check_network_tab 69 s. Plain lane: 254 checks, only 405 s of work.
- Conclusion: the wait is the browser lane + the serial SOLO tail, not the plain checks. Next levers, each needing a measured
  3-green-run proof: split check_video_page (233 s alone = the floor of the pool phase), move SOLO checks whose only reason is a
  port to a free port, and widen browserLanes only on a PC with free cores.
Live mode: `python tools/qc_live.py` (read-only GETs at the running hub/voice/faces/friend app, alone then all together, p50/p95/max,
errors, contention factor). Self-test against local servers: 2 apps x 3 clients, p95 7 ms alone and 7 ms together, 0 errors.
Not yet run against the real apps on the PC.
### 2026-11-25 All apps at once on the PC (hub + voice + Ollama + Face_Regonize + camera + Chrome)
Tools: tools/perf_profile.py (RAM/VRAM per app, GPU enc/dec), tools/perf_load.py (alone, together, --real). Raw: .local/perf/ (PC only). Report with charts: docs/experiments/2026-11-25_all_apps_together.md.
- Before: torch 2.15.0+cpu, so Whisper's GPU check said no GPU; also cublas64_12.dll missing. 3 Whisper models CPU int8. STT /transcribe median 3086 ms, p95 6164 ms (tts_cache clips). Direct th-medium 6.5 s clip: CPU int8 44-58 s vs GPU float16 0.6 s.
- After (CTranslate2 probe + pip nvidia-cublas-cu12 12.9.2.10 + DLL dirs): STT median 751 ms, p95 2242 ms. VRAM voice 0 -> 4712 MiB, RAM voice 4331 -> 3093 MiB. Total VRAM 4.2 -> 9.0 GB of 12.
- /ask: 2615 ms median before; 3.07 s vs 0.73 s with a name given proved the sync face look; after (worker + prefetch on /transcribe, askWaitSeconds 0.4): 61 ms median, 554 ms p95. Ollama think itself 197 ms.
- Face /api/look t1.jpg (1280x886, 6 faces): 73 ms alone (server took_ms 42); together stress 139 ms before, 204 ms after (voice now on the GPU too); --real (face 10/s) 87 ms. STT together: --real 1151 ms, stress 2832 ms.
- Rejected: Whisper th-medium int8_float16: VRAM 2069 -> 1149 MiB, but text vs float16 only 0.72 mean similarity (min 0.44), 10 clips: quality drop.
- GPU encoder/decoder 0% in every run: PC camera gives raw nv12/yuyv (no H.264/MJPEG), hub re-encodes 640 px 10 fps q6 JPEG on CPU. Encode test (lavfi): 720p30 q4 1.61 MB/s RSS 212 MB; 1080p30 2.73 MB/s RSS 411 MB.
- Second opinions: Gemini 4 Neon medium and Codex gpt-6.2-sol medium both ranked cublas fix and Ollama-first /ask on top.

### 2026-11-25 round 2: Video page waited 210 s for nothing
Per-phase profile of check_video_page alone (4-core cloud): hub half 0.8 s, page half 11.5 s, LAN page half 210.1 s. The LAN driver
never sent its `VL~done` mark, so browser.page() sat out `seconds + grace` (60 + 150 s) after the page had already reported
("QC SLOW ... waited for nothing"). Fix: send `VL~done` at the end of that driver. Same 62 assertions, all green.
- check_video_page: 233.0 s -> 22.5 s in the full run (15.9 s alone).
- Full QC, same box, same env-only failures: 651.2 s -> 516.5 s (-20.7%); old runner on main was 675.3 s (-23.5% in total).
  Pool phase 400 -> 264 s; SOLO phase unchanged at 252 s. 10476 passed, 13 failed (all env-only: no PlatformIO, torch, mujoco, branch `app`).
- Checked the next slowest browser checks alone for the same bug (visual_language 107 s, theme_contrast 89 s, network_tab 69 s):
  none prints QC SLOW; their time is real work.
- SOLO tail: 29 checks, 245 s of work. Port-only ones (short_name, name_claim, mdns, build_split) total under 7 s; the 250 s is
  clock-sensitive browser checks (flash_type 43 s, flash_confirm 42 s, chatty_board 29 s, report_pictures 23 s ...) whose history
  of starved-margin failures is in run_qc.py. Moving them into the pool would trade time for flakes, so not done.
- Stop rule: round 3 (splitting visual_language by language) is estimated at under 10% and is left for a measured follow-up.

### 2026-11-25 PC (24 threads, 31 GB, SSD): why a full gate is 25 min here, 8.6 min in the cloud
Raw runs, fresh worktree, PC otherwise idle (other threads' QC not running):
- Run 1 (baseline, cold firmware tree): wall 1524 s. Parallel phase 782 s, SOLO phase 320 s, check_build_split 414 s run alone FIRST.
- Run 2 (shared PlatformIO object cache): wall 1541 s but not comparable: 4 browser checks failed in the crowd and were re-run
  alone twice each (parallel phase 882 s of which the pool itself ended at 491 s), and check_report_pictures spent 270 s in a
  page that never reported (QC SILENT). build_split fell from 414 s to 2 s (build dirs kept from run 1).
- Process start cost is NOT the cause: python start 0.03 s, `import qc` 0.07 s, powershell -NoProfile 0.21 s, one Get-CimInstance
  0.7 s, SSDs. Defender real-time protection is on (exclusions not readable without admin) but nothing measured points at it.
- Firmware, measured directly (5 envs at once, `pio run`): no cache cold 474 s; shared `PLATFORMIO_BUILD_CACHE_DIR` populating
  477 s (same); same build with the cache warm 42 s (-91%). One env alone cold: 55 s (cam) - five at once is 8.6x slower than one,
  so the five compilers contend for something (not CPU: 24 threads). Cause not found; the warm cache avoids it.
- Fix landed: check_build_split passes a machine-wide cache dir (`~/.platformio/qc_object_cache`) to pio (keyed on compile command
  + source content, so a hit is the object a fresh compile would make). Same assertions; new assertion proven by breaking it.
  Every new worktree / staging tree used to pay the cold 414-474 s before any other check could start (it runs first, alone).
- Timing file now stores `end` (seconds into the run) per check, so lane idle gaps can be read: plain lane finished at 169 s,
  browser lane pool at 491 s; 10 plain workers idle for ~320 s while 6 browser lanes work. Browser work is 2233 s of checks.
- Where the rest goes: (a) browser checks that fail in the crowd and are re-run alone twice (4 flaky in run 2, 1 in run 1;
  real failures on main cost 2 extra alone runs each, e.g. visual_language 2 x ~110 s); (b) QC SILENT waits: a page that never
  reports sits out seconds+grace (190 s, 270 s, 478 s seen in run 2); (c) SOLO tail 232 s of clock-sensitive checks.
- SOLO list kept, with the measured reason: short_name (port 80), name_claim + mdns (5353): real single resources, all under 8 s
  together. themes + tools_list (edit shared files while others read them), systems (lists the tree). The starved-margin set
  (hub_clock, studio_playback, flash_*, crash_gate, voice*, translate, gacha_ui, chatty_board, report_pictures) was NOT moved: moving
  needs three green crowded runs each (25 min a run) and run 2 already showed the crowd is at its limit (4 flakes at 6 lanes).
  Next lever: give those pages a readiness signal instead of a connect/timer margin, then move one at a time.
- Not done (stop rule): widening workers/browserLanes (run 2 flaked more than run 1 at the current width).

### 2026-11-25 later: why the crowd failed, one run at a time, firmware built once
- Run 3 (full, 993 s wall, 26 failed) was overlapped by another thread's full run and a `--only check_panel` run: log shows
  `WinError 10048` and `{'_raw': '[]'}` (pages reporting nothing). The QC SILENT waits (190-478 s) and report_pictures 278 s in
  run 2 fit the same cause: a second run on the fake serial port / port 80. Not proven for every case: run 2's log was overwritten.
- Fix: `qc/lib/runlock.py` (lock file in the temp dir with pid + start; a second run waits and names the holder; dead holder taken
  over; `--no-lock` / `--list` skip). `check_run_lock` proves wait + takeover; two sabotages (takeover off, wait off) were caught.
- Firmware artifact cache `qc/lib/fw_cache.py`, outside the repo (`~/.platformio/qc_artifact_cache/<key>/`), key = sha256(firmware +
  config + shared-web inputs, PlatformIO + every platform/package version, env). Restore verifies size + sha256 per file; stored only
  after check_build_split's own assertions passed; `--rebuild-firmware` / MICE_QC_REBUILD=1 forces a build. `check_fw_cache` proves
  hit, miss on input / toolchain / env change, corrupt and truncated entry rejected; three sabotages caught.
  Measured (check_build_split + 3 small checks, `--jobs 1`): first run, cache empty (pio object cache warm) 136 s; same tree
  with build dirs removed, cache hit 31 s. Cold fresh tree without any cache stays 414-474 s once per machine per firmware change.
- promote.py gate: left as is. It runs run_qc.py, so it uses the cache; the key covers every input and the toolchain, a hit
  still runs every assertion on the restored binaries, and an unknown key always builds for real.
- Not done: SOLO checks stay SOLO; three green crowded runs each is not measurable while other threads run QC on this PC.

### 2026-11-25 final full run on the branch (PC to itself, lock held, artifact + object caches warm)
- Wall 832 s (13.9 min), against 1524 s for the baseline run 1 (same PC, cold firmware tree): -45%. Parallel phase 524 s, SOLO phase 297 s,
  check_build_split 1.8 s. 10682 passed, 9 failed, no FLAKY, no QC SILENT, no QC SLOW. A filtered `check_settings_transfer` run
  from another thread started 9 s before it (seconds of overlap).
- The 9 failures are the failures main already has (th/ja/zh text leaks, "no page threw", the camera-reader checks); the system-map
  failure of that run was my own new files and is fixed in the next commit (check_systems green).
- The remaining wall is real work: browser lane 2233 s of checks on 6 lanes, plus the SOLO tail (~297 s). Not touched.

### 2026-11-26 twelve SOLO checks moved into the pool (PC to itself, lock held, three crowded full runs)
Moved: check_hub_clock, check_studio_playback, check_gacha_ui, check_translate, check_voice, check_voice_stt, check_voice_tts,
check_flash_remote, check_crash_gate, check_flash_type, check_flash_confirm, check_chatty_board. All their assertions are unchanged.
- Round 1: 536 s wall (parallel 302 s, SOLO 231 s). All 12 green. Red only on two guard assertions in check_qc_parallel (they
  encoded the old policy for hub_clock and studio_playback; removed with the move) and check_dev_tools (QC lock deadlock, fixed in #262).
- Round 2: 605 s, 10799 passed, 0 failed; check_gestures flaked (passed alone 2/2), one QC SILENT 190 s on a page (not one of the 12).
- Round 3: 549 s, 10799 passed, 0 failed, no flake, no SILENT.
- Before (same tree, same PC, those 12 in the SOLO tail): 832 s. After: 536-605 s (-27 to -36%). The earlier "starved margin" reds
  in the crowd coincided with overlapping QC runs on this PC (see the lock entry above); with one run at a time they did not recur in 3 runs.
- Still SOLO, with the real reason: short_name (port 80), name_claim + mdns (5353), build_split (writes firmware/.pio), themes (rewrites
  the shared stylesheet), tools_list (breaks an app.json), systems (lists the tree), report_pictures + visual_language (shared report data),
  and the module-level SOLO ones (faces_* fake ports, camera_hub, pc_camera, alone_apps). SOLO tail is now ~228 s; check_visual_language is 111 s of it.

### 2026-11-26 combined tree, and the "page reports nothing" flake (investigation, no fix merged)
- #265 (12 checks out of SOLO) on top of the watchdog: full QC PASS, 10814 passed, 0 failed, 658 s wall (parallel 417 s, SOLO 228 s),
  no QC STALL, no timed out. One FLAKY: check_video_page (passed alone 2/2) with one QC SILENT line.
- QC SILENT / empty-marks flakes seen in 7 of 8 crowded full runs today, on different checks: gestures (x3), video_page (x2),
  responsive, studio_peer, page_frame, music_ui. Always: marks list empty, "6-16 bytes on the wire", passes alone.
- Stress, PC to itself, 8 copies of one check at once: check_gestures 8/8 green in 28 s (no SILENT) => load alone does not reproduce it.
- Tried: relaunch the browser once when a page has reported nothing after 75 s (branch claude/qc-page-relaunch, check_page_relaunch
  proves the rule). Full run PASS 10823, 835 s. The relaunch fired once, on check_video_page, and the second browser was also silent
  => the silent page there is not a dead browser, and a fixed 75 s rule can misfire on a page that is quiet on purpose.
  NOT recommended for merge.
- check_video_page x8 at once: 7 of 8 fail, ~31-37 s, "the video and its choices are saved in the project file": every copy saves the
  project under the same name (`qc_video_page`), so concurrent copies overwrite each other's file. A different failure from the
  crowd's silent page, but a real shared-name collision (a unique work name per run would remove it).
- Open: why the page of check_video_page (and gestures) sends no mark in a full run. Next step: capture the browser console of a
  silent page (--enable-logging, or the DevTools protocol) the moment QC SILENT fires.

### 2026-11-26 GPU-memory planner at a 2 GB Voice budget: spill vs swap vs hybrid (REDUCED run, real PC, real Voice left running)
Setup: branch claude/project-thread-q4yvte (planner 17788d89 + MICE_VRAM_STRATEGY and MICE_VRAM_VOICE_BUDGET_MIB switches, default
unchanged). RTX 5070 Ti Laptop 12227 MiB; 9060 MiB already used by the real Voice, face app and others before the side Voice started.
Side Voice 8768 and side hub 8650; face look 10 Hz, ask and hearing 0.5 Hz, camera stream, 4 background helper threads flat out;
60 s per run, 2 runs per setting, PC QC lock held. Full write-up: docs/perf_vram_2026-11-26.md (marked REDUCED).
- Planner placement at 2 GB (same in all 3 settings): Whisper small on the GPU; Whisper Thai medium (1.9 GB), Whisper medium
  and the local model (Qwen2.5-0.5B, 1.2 GB) on the CPU. Headroom 384 MiB, room 1664 MiB.
- Mean of 2 runs, ms (p50 / p95 / p99), background jobs in 60 s:
  - spill:  ask 137/6788/8521, hearing 4644/7165/7636, face 75/179/197, camera 114/136/146, jobs 36
  - swap:   ask 144/6230/8250, hearing 4571/7028/7588, face 74/176/193, camera 114/136/146, jobs 36
  - hybrid: ask  88/6765/7763, hearing 7177/8100/8602, face 82/198/215, camera 114/137/147, jobs 80
- Per run (ask p95 / hearing p50): spill 8623/4287, 4953/5001; swap 7648/4174, 4811/4969; hybrid 7747/7147, 5783/7207.
  Run-to-run spread inside one setting (3.7 s on ask p95) is larger than the spill-swap gap (0.6 s): equal within noise.
- Calibration (CPU alone, whole Voice on a 300 MiB budget): hearing 2789 ms, helper 786 ms, ask needing the model 3219 ms,
  ask from saved answers 35 ms, Spark speech 9450 ms per line (15.2 s load). Reload from disk cache after /unload: Thai hearing
  7873 ms, local model 5169 ms (both loaded to the CPU). The "GPU alone" calibration at 2 GB timed the CPU (hearing 2837 ms,
  helper 846 ms): the Thai hearing model does not fit 2 GB even alone.
- Comparison with the same PC when the models are on the GPU (other session, real Voice, CUDA torch): hearing 445 ms, helper 256 ms.
  Hearing on the CPU is about 6 times slower, which is the cost of a 2 GB budget here.
- Result: spill (shipped) is the choice by live p95/p99. Swap did not swap in this test (identical placement), so it is
  not measured. Hybrid gave 2.2 times more background jobs but +55% hearing p50 and +13% hearing p95, because the CPU copies of the
  local model compete with the Thai hearing model that sits on the CPU at this budget.
- Not done: 4 to 12 GB, GPU service times, real swap cost to the GPU, GPU Spark, bench_vram rerun with measured times.
  `python tools\vram_measure.py all` (needs the real Voice stopped) completes it.
### 2026-11-26 final summary: full QC on this PC, 1524 s -> 406 s
| step | wall | what changed |
|---|---|---|
| baseline (fresh tree, cold firmware, other threads' runs overlapping at times) | 1524 s | check_build_split compiled 5 envs alone first (414 s) |
| PlatformIO object cache + firmware artifact cache + run lock | 832 s | build 474 s -> 42 s warm / 2 s hit; one run at a time |
| 12 starved-margin SOLO checks into the pool | 536-605 s (3 runs) | hub_clock, studio_playback, gacha_ui, translate, voice*, flash_*, crash_gate, chatty_board |
| watchdog + combined | 658 s | hard limit per check, heartbeat, died/timeout = FAIL |
| isolate_data + sweep fix (SILENT root cause) | 551-569 s | per-check projects/sequences/shows; sweep keeps live pids |
| 5 more out of SOLO + per-check reports folder | 406 s | visual_language, report_pictures, camera_hub, alone_apps, pc_camera |

Root causes found on the way (all in the records above): the stalled scheduler runs = my own lock deadlocking nested runs;
the "page reports nothing" flake = browser.sweep() of a nested run deleting live driver pages/profiles (QC DIAG: page GET 404);
checks overwriting each other's fixed-name saves = shared projects/sequences/shows/reports folders.

Still serial (SOLO) and why: check_short_name (port 80), check_name_claim + check_mdns (5353): real single resources;
check_build_split (writes firmware/.pio, reads by flash/OTA/QEMU checks); check_themes (rewrites the shared stylesheet in the
tree), check_tools_list (breaks an app.json in the tree), check_systems (lists the tree); the faces_* checks (a fake port each, 1-3 s).
SOLO tail is now ~53 s.

How to run: `python qc/run_qc.py --quiet --done-file F` (takes the PC-wide lock, first come first served, prints who holds it);
`--no-lock` skips the lock; `--rebuild-firmware` or MICE_QC_REBUILD=1 forces a real firmware build (default reuses a green build keyed on
inputs + toolchain); `python tools/qc_live.py` and qc/last_progress.json show what is running; QC SILENT now prints a `QC DIAG` line;
a check past max(600 s, 3x its slowest healthy time) is killed and fails "timed out after N s".

Last three crowded full runs on claude/qc-solo-2: 406 s, 405 s, 459 s, all PASS (10863 passed, 0 failed). One FLAKY in the last:
check_freeze_stop ("a Studio page on screen keeps its show alive past the timeout by beating - 'playing-true' not found"; passed alone 2/2),
the same check that flaked in an earlier round: it is the next candidate for a readiness signal instead of a timer.

### 2026-11-26 GPU-memory planner, full run: card sizes 2 to 12 GB and spill / swap / hybrid at 2, 4, 6 GB (real PC, real Voice stopped for the run)
Setup: merged main (planner #269), RTX 5070 Ti Laptop 12227 MiB, CUDA torch 2.11.0+cu128; real Voice stopped for the run and
restarted after (all four models on the GPU again). `python tools\vram_measure.py all`, PC QC lock held. Side Voice 8768, side hub 8650;
face look 10 Hz, ask and hearing 0.5 Hz, camera, 4 background helper threads; 60 s runs, 2 per setting, 0 request errors in 26 runs.
Full write-up: docs/perf_vram_2026-11-26.md. All numbers measured; the simulator was only rerun with measured inputs.
- Calibration alone: hearing (Thai medium, 3 s clip) GPU 422 ms / CPU 2877 ms; helper translation GPU 466 / CPU 821 ms; ask needing the
  local model 1842 / 3232 ms; ask from saved answers 31 / 42 ms; reload to the GPU 5290 ms (Thai hearing), 4694 ms (local model);
  Spark CPU 9450 ms per line (15.2 s load), Spark GPU NOT measured (stale CPU server answered).
  Learned sizes: Whisper small 576 MiB, Thai medium 1856, medium 1792, local model 1029 (all four: about 5.4 GB).
- Spill (planner as shipped) by card size, mean of 2 runs, ms (ask p50/p95/p99 | hearing p50/p95/p99 | background jobs in 60 s | on the GPU):
  - 2 GB:  64/4236/5508 | 3991/4641/4782 | 14 | none
  - 4 GB:  65/3621/4190 | 3669/4347/4383 | 15 | none
  - 6 GB:  88/4949/5167 | 4292/4875/4970 | 14 | small
  - 8 GB:  70/1872/2202 | 1087/1390/1594 | 66 | local model, small, Thai medium
  - 10 GB: 71/2142/2797 | 1235/1793/2154 | 44 | small, Thai medium, medium
  - 12 GB: 62/1460/1733 |  855/1229/1299 | 90 | all four
  - whole card: 64/1841/2221 | 1113/1436/1539 | 64 | all four
  Face look p95 168 to 214 ms and camera p95 under 141 ms at every size.
- Strategies at 2 / 4 / 6 GB (ask p95 | hearing p50 | background jobs): spill 4236/3991/14, 3621/3669/15, 4949/4292/14;
  swap 2124/4796/12, 3379/4627/12, 4421/4128/14; hybrid 9009/12022/79, 8393/14312/73, 6292/12476/78.
- Findings: (1) hearing is 4 s on the CPU (2 to 6 GB) and about 1 s from 8 GB; (2) spill at 6 GB pins Whisper small, not the Thai hearing model
  that serves Thai visitors: hearing no better than at 2 GB, about 6.8 times slower than the 422 ms the Thai model needs on the GPU; (3) at 10 GB the local model went to
  the CPU although it was on the GPU at 8 GB (a busy model refused to be unloaded); (4) at 2 and 4 GB nothing fits with this face app (room -89 and 441 MiB
  against 576 MiB); (5) swap did not swap (same placement as spill, within noise); (6) hybrid is 3 times slower for hearing and about 5 times faster for
  background jobs at 2 to 6 GB; (7) the simulator with measured inputs says swap is 4 to 6 times worse and hybrid best at 6 to 8 GB: both wrong against the measurement.
- Winner by live p95/p99: spill (shipped default). Not measured: Spark on the GPU, hybrid with the live models on the GPU (8 GB and up), the planner's memory use by speech.
