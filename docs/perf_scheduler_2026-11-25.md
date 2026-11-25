# Shared job scheduler: measurements, 2026-11-25

Branch `claude/project-thread-q4yvte` (PR #259: `tools/jobsched.py`, `config/scheduler.json`,
`main_python/hub_api_scheduler.py`). No model, setting or quality was changed for these runs.

![live wait before and after](img/perf_scheduler_2026-11-25.png)

## 1. Simulation (`tools/bench_sched.py`)

4 background workers each run 12 pieces of 0.25 s on one GPU, 8 live questions of 0.15 s arrive
every 0.6 s. "Before" is a plain lock (what Voice had), "after" is the scheduler with `config/scheduler.json`.

| | plain lock | scheduler |
|---|---|---|
| live question wait p50 | 5039 ms | 110 ms |
| live question wait max | 9313 ms | 235 ms |
| all background work done | 13.20 s | 13.31 s |

A live question waits about 46x less. Background work finishes 0.1 s later (under 1%), so it is
delayed a little and never starved. Raw: `.local/perf/sched_sim.json`.

## 2. Real apps (`tools/perf_load.py --seconds 20`)

Everything running together: the branch hub, the branch Voice (real Whisper on the GPU), the real
face app (`/api/look`), and the PC camera stream. Each workload runs as fast as it is answered.
Workloads: face, voice `/ask`, stt `/transcribe`, camera. The local LLM (`llm`) was not running on
this PC, so it was left out. The STT clips were three short English sentences made with Windows
speech (the PC had no clips in `apps/voice/tts_cache`).

"Scheduler off" is `lease.enabled=false` and every class at priority 5 (plain FIFO).

"together", median / p95 in ms (calls in 20 s):

| workload | alone | scheduler OFF | scheduler ON (run 1) | scheduler ON (run 2) |
|---|---|---|---|---|
| voice `/ask` | 49 / 1069 | 624 / 1910 (23) | 677 / 1699 (23) | 661 / 1686 (23) |
| stt `/transcribe` | 512 / 605 | 644 / 1791 (23) | 651 / 1756 (23) | 631 / 1791 (23) |
| face `/api/look` | 74 / 177 | 76 / 185 (210) | 75 / 178 (209) | 77 / 185 (204) |
| camera frame | 94 / 125 | 94 / 126 (201) | 95 / 112 (201) | 94 / 124 (201) |

Reading it honestly:

* The scheduler adds no measurable cost. ON and OFF are inside run-to-run noise (voice p50 624 to 677,
  p95 1686 to 1910; the two ON runs differ from each other by about as much as ON differs from OFF).
* It does not speed these workloads up, and it was not expected to. In this test every GPU job is the
  same kind: `/ask` and `/transcribe` are both class `live`. Priority only helps when a lower class
  (translation, helper, warm-up) is in the queue at the same time. That case is section 1.
* The big slowdown from "alone" to "together" (voice `/ask` 49 ms to about 650 ms) is Whisper and the
  face app sharing one GPU with the workloads running flat out. It is the cost of the single GPU,
  not of the queue.
* The face app is a separate program that does not ask the hub for a GPU turn yet, so its jobs are not
  ordered by this scheduler. Only Voice and hub tools are.

## 3. How this was run

* The real hub (`MiceHub.exe` on 8642), the real Voice (8767) and the face app (8000) were left
  running and untouched. The branch hub ran on port 8650 and the branch Voice on 8768, started by a
  small harness (not in the repo) that sets the port and turns off mDNS, the port-80 name, the peer
  registry, module scanning and the browser tab, so nothing reached real boards or names.
  `config/scheduler.json` `lease.hubUrl` and `config/perf_load.json` `voice`/`stt_clips` were pointed
  at the side ports for the runs and put back afterwards.
* The camera load read the real hub's shared stream (`pc:FHD Camera`), the same in every run.
* Chart: `python tools/chart_sched.py --sim .local/perf/sched_sim.json --on .local/perf/sched_on.json --off .local/perf/sched_off.json --out docs/img/perf_scheduler_2026-11-25.png`.

## 4. QC status on this PC (not final)

Three full `python qc/run_qc.py --quiet` runs on the pre-merge branch each stopped making progress
after about 340 of 415 checks, with idle worker processes and no child processes. Full runs by other
sessions on main finished in that window, so this looks like a hang in the process pool, not a
failing check. The checks no run had reported were run as one filtered run (77 checks, 412 s):
2131 passed, 8 failed. Failures seen across these runs, as printed (causes not yet confirmed):

* firmware: `mice_lift compiles` and `the all-types build still compiles`, `spiram-fast.h: No such file`
  in the ESP8266Audio library (the pre-merge branch has no firmware cache).
* hub: this PC's camera is opened once by the hub (4 assertions). The real hub was running and
  holding the webcam during the run.
* web: Report pictures, `th` (3 assertions).
* tooling: `the system map is sound` (stale map; main rebuilt it in #260).
* hub: `api_index.json and docs/HUB_API.md match the code` (seen on the pre-merge branch only).
* persistence: `a 21 MB save is refused` (one of three runs).

None of these names the scheduler. A final full run on the merged branch, through the PC QC lock,
decides the verdict.
