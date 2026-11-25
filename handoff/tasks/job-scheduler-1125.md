# Shared priority job scheduler for all apps

Owner: claude
Updated: 2026-11-25 13:25 +0000
Branch: claude/project-thread-q4yvte
Last commit: 9d66f67
Plan: (none yet; user ask 2026-11-25 "work like CPU/GPU: slice, queue, let urgent jump, no single bottleneck, stay easy to change")

## Goal
Every heavy job goes through shared priority queues in front of the GPU/CPU so a live voice answer / face match is never stuck behind background work; classes, priorities, slots are data.

## Doing now
Hub lease built (quick-checked). Next: commit/push, then full QC + real all-apps measurement on the PC when the QC thread frees it, then merge.

## File status
Baseline: origin/main at branch start

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/jobsched.py` | new Scheduler/Gate (priority, aging, re-entrant, checkpoint pre-emption, live config reload, stats) | done | check_job_scheduler (quick, cloud, sabotage-proven) | 9d66f67 |
| `config/scheduler.json` | resources (gpu 1 slot, cpu 4) and classes live/speech/normal/helper/translate/background | done | same | 9d66f67 |
| `tools/bench_sched.py` | plain lock vs scheduler under same load | done | simulated: live wait p50 1077->150 ms | 9d66f67 |
| `qc/checks/check_job_scheduler.py` | order, aging, reentrancy, checkpoint, reload, shipped config, no plain voice lock left | done | 8 ok | 9d66f67 |
| `apps/voice/{service,answerer,listener,local_llm,translator}.py` | `self._lock` replaced by `self._gpu(<class>)`; scheduler in /status | done | check_voice_fast, check_voice_gpu_and_ask_speed pass (quick) | 9d66f67 |
| `apps/voice/help/{en,th,zh,ja}.html` | one sentence on queue order | done | not run in browser | 9d66f67 |
| `main_python/hub_api_scheduler.py`, `main_python/main.py` | hub lease endpoints (loopback only, ttl 60 s), hub's own `gate()` | done | check_job_scheduler_lease 7 ok, sabotage-proven (quick, cloud) | this checkpoint |
| `tools/jobsched.py` | + LeaseTable/LeaseClient, timeout, cross-thread gate | done | same | this checkpoint |
| `main_python/hub_video.py` | sound extraction runs under class `encode` (cpu) | done | not run (no ffmpeg here) | this checkpoint |
| `qc/checks/check_job_scheduler_lease.py`, `docs/friend/gpu_lease_request_2026-11-25.md` | new check; friend request | done | quick | this checkpoint |
| `docs/systems.json`, `docs/systems/*`, `MiceHub.spec` | new system job-scheduler; jobsched.py shipped in exe | done | check_systems pass | 9d66f67 |

## Facts found
- apps/voice/service.py (Brain.__init__): was `self._lock = threading.Lock()` "one GPU" shared by ask, listen, helper, translate, unload; plain Lock = FIFO, no overtaking.
- apps/voice/resources.py `map()`: translation pool; each item re-enters the gate, so it is already sliced per item.
- Voice, Faces (friend), hub are SEPARATE processes: this scheduler is per process. A cross-process GPU gate is not built.
- Friend repos untouched. Friend must-change list: let our scheduler / a shared lease decide when their GPU jobs start (see Next).

## Done
- Library + Voice wiring + QC + Help (this commit).

## Next
1. Hub port is hardcoded 8642 in config/scheduler.json lease.hubUrl; pass the real port via env if the hub moves.
2. Cameras: hub relay only pipes ffmpeg bytes (no decode in hub); camera GPU decode is in the friend app (see docs/friend/gpu_lease_request_2026-11-25.md).
3. PC measurement: `python tools/perf_load.py` before/after with all apps running; chart.

## Blocked
- Nothing for the library. PC measurement waits for a free PC session (QC thread is using it).
