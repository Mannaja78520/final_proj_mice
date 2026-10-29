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
