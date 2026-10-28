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
