# KV cache: shrink it further without quality loss (round 3 of the thread's KV work)

Owner: claude (project thread, branch claude/kv-cache)
Updated: 2026-11-27
Branch: claude/kv-cache
Last commit: see git log
Plan: A58-2 (user ask 2026-11-27, via the coordinator: max 3 rounds, stop below 2% gain, p95/p99 first, with Voice + faces running together)

## Goal
Ollama already runs flash attention + q8_0 KV (q4_0 rejected 2026-11-05). Try to shrink KV memory more with NO quality loss,
measured beside the other apps (voice helper + the friend's face models in a loop; no real cameras on this PC bench).

## Facts measured today (Ollama 0.34.2, typhoon25-4b, RTX 5070 Ti Laptop 12 GB)
- The model gets n_ctx 2048 (not Ollama's vram default 4096). KV q8_0 = 153 MiB of 2605 MiB device use (model 2375, compute 77).
  So even a 2x smaller KV is about 3% of the model's GPU memory: the rounds below test whether that is worth any risk.

## Rounds (budget 3; stop rule: a round that gains less than 2% of GPU memory AND no p95/p99 gain ends it)
1. q8_0 (now) vs q4_0 again (this Ollama build prints attn_rot: rotated KV may have changed the 2026-11-05 verdict).
2. q8_0 with a smaller context (contextLength in config/local_ai.json, new key, default unset): 1536 / 1024 / 768 vs prompt sizes in real cases.
3. Only if 1-2 leave something above the stop rule.
Harness: .local/kv_bench_2026-11-05/verify2/run_kv2.py (PC only); raw: .local/kv2_2026-11-27/.

## Doing now
Round 1 running (C = q8_0 baseline, D = q4_0, each beside the face-model loop, 118 cases through the voice helper /ask).

## Done
- tools/ollama_serve.py: contextLength config key + --ctx flag (new; default unset = unchanged behaviour).

## Next
Read res_C_face.json / res_D_face.json; compare answers (compare script), p50/p95/p99, VRAM; record in docs/experiments/experiment-records.md.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| tools/ollama_serve.py | contextLength + --ctx | uncommitted | --show output checked by hand; QC check_ollama_kv not run yet | - |
| handoff/tasks/kv-cache-1127.md | new | uncommitted | n/a | - |
