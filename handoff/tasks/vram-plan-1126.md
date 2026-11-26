# VRAM planner measurement (spill / swap / hybrid) on the real PC

Owner: claude
Updated: 2026-11-26 09:50 +0700
Branch: claude/project-thread-q4yvte
Last commit: 6ceaa289
Plan: user ask 2026-11-25 "if the card has 2, 4, 6, 8, 10 or 12 GB do it dynamically, nothing slower than needed; is spilling to the CPU or queueing everything through the GPU better? measure and write a report"

## Goal
Measured proof of how the dynamic GPU-memory planner (tools/vramplan.py) behaves per card size, and which strategy is best for live latency (p95/p99): spill (shipped), swap, hybrid.

## Doing now
The REDUCED run is done and reported (docs/perf_vram_2026-11-26.md): one Voice budget (2 GB) with the real Voice left running. A final full QC is running in E:/work/sched_259 (started 09:43).

## Next
1. The FULL 2 to 12 GB run is NOT done. It needs the real Voice stopped for about an hour. The PC permission check refused that twice because the user's own yes was only relayed; it needs the user to type a clear yes in the PC session, or to run it themselves:
   `cd E:\work\vram_260` then `python tools\vram_measure.py all` (holds the QC lock, stops the real Voice, always starts it again with the same command and checks it is back; `smoke` is a 10 minute dry run first).
2. Then `python tools\chart_vram.py .local\perf\vram_<date> --out docs\img\perf_vram.png --md docs\img\perf_vram_tables.md`, update docs/perf_vram_2026-11-26.md (remove the REDUCED banner for what is measured), append the raw numbers to docs/experiments/experiment-records.md, push, one full QC.
3. Swap did not swap at the 2 GB budget (same placement as spill): find out why the local model and the Thai hearing model never took the GPU alone in swap mode (the Voice asks its own resource plan, which reads the real card, before the planner), or change the experiment so that it does.
4. `config/vram_bench.json` still has estimates for the GPU times; fill them from the full run and rerun `tools/bench_vram.py`.

## File status
Baseline: origin/main at branch start

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `tools/vramplan.py` | MICE_VRAM_STRATEGY (spill/swap/hybrid), MICE_VRAM_VOICE_BUDGET_MIB | done | check_vram_plan (budget case) | 97ab810 |
| `apps/voice/{local_llm,service,translator}.py` | CPU copy of the local model for hybrid, planner view in /health | done | check_voice_stt, check_voice_gpu_and_ask_speed | 833d7ba |
| `tools/vram_measure.py` | calibrate, caps, strategies, all, reduced (QC lock, real Voice restart in finally) | done, `all` not run | reduced phase run on the PC | 97ab810 |
| `tools/chart_vram.py` | p95/p99 per strategy chart and table | done | used for the reduced report | 97ab810 |
| `docs/perf_vram_2026-11-26.md` | REDUCED report | done | numbers from .local/perf/vram_2026-11-26 | 97ab810 |
| `shared/web/lang/help/{en,zh,ja}.json`, `config/layout.json`, `docs/LAYOUT.md` | help translation of the VRAM paragraph, layout line | done | final full QC (running) | 6ceaa28 |

## Open
- Full QC on 97ab810: 10768 passed, 6 failed (firmware mice_gacha compile = env, layout, 3 x Thai on help = fixed in 6ceaa28, check_dev_tools sabotage self-test timed out in the cold vram_260 tree: `run_qc.py --only check_panel` alone took 198 s there). The final run is in the warm tree.
- docs/systems/qc.md lists git-ignored QC artifacts present on disk (qc/last_timing.json), so check_systems fails right after a QC run; delete the file before running it.
