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
