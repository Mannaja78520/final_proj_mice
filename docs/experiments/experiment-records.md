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
- The recording is a talk with at least one other person ("ใช่ครับ ถูกไหม"): speaker identity of each clip is NOT verified. 19 clips say ครับ, 3 say ค่ะ/คะ.
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
