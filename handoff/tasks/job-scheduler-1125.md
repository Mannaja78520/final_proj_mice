# Shared priority job scheduler for all apps

Owner: claude
Updated: 2026-11-25 13:25 +0000
Branch: claude/project-thread-q4yvte
Last commit: 9d66f67
Plan: (none yet; user ask 2026-11-25 "work like CPU/GPU: slice, queue, let urgent jump, no single bottleneck, stay easy to change")

## Goal
Every heavy job goes through shared priority queues in front of the GPU/CPU so a live voice answer / face match is never stuck behind background work; classes, priorities, slots are data.

## Doing now
Full cloud QC on the branch, then PR. Next: real all-apps measurement on the PC.

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
| `docs/systems.json`, `docs/systems/*`, `MiceHub.spec` | new system job-scheduler; jobsched.py shipped in exe | done | check_systems pass | 9d66f67 |

## Facts found
- apps/voice/service.py (Brain.__init__): was `self._lock = threading.Lock()` "one GPU" shared by ask, listen, helper, translate, unload; plain Lock = FIFO, no overtaking.
- apps/voice/resources.py `map()`: translation pool; each item re-enters the gate, so it is already sliced per item.
- Voice, Faces (friend), hub are SEPARATE processes: this scheduler is per process. A cross-process GPU gate is not built.
- Friend repos untouched. Friend must-change list: let our scheduler / a shared lease decide when their GPU jobs start (see Next).

## Done
- Library + Voice wiring + QC + Help (this commit).

## Next
1. Cross-process: hub-hosted lease (`/api/scheduler/lease`) so Voice STT, face match and camera encode share one GPU order; friend apps need a tiny change to ask it.
2. Move hub report/image jobs (main_python/report_images.py) onto class `background`.
3. PC measurement: `python tools/perf_load.py` before/after with all apps running; chart.

## Blocked
- Nothing for the library. PC measurement waits for a free PC session (QC thread is using it).
