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
Nothing: finished (stop rule reached after 2 rounds). Waiting only for the docs PR to merge.

## Done
- Round 3: q4_0 vs q8_0 beside the Voice helper and a face-model loop, 118 cases: q4_0 saves 72 MiB (2.8 %) but 40 of 118 answers differ and some are wrong
  (invented opening hours, lost Wi-Fi password, wrong person). Rejected again.
- Round 4: smaller context. The model's Modelfile num_ctx 2048 wins over OLLAMA_CONTEXT_LENGTH (the setting I first added to tools/ollama_serve.py was removed: it did nothing).
  Real prompts: max 1026 tokens, with answer 1282; ctx 1536 would save 38 MiB = 1.5 % < 2 % stop rule; ctx 1024 would cut off 6 of 81 calls.
- Numbers, setup and a paper comparison: docs/experiments/experiment-records.md (section 2026-11-27 KV cache rounds 3-4). Raw files: .local/kv2_2026-11-27/ (PC only).
- No code or config change. q8_0 + flash attention stays. All my test services (Ollama on 11436, the logging proxy, the Voice helper, the face loop) are stopped; GPU back to 0 MiB.

## Next
Nothing planned. A future round could re-create the model with num_ctx 1536 only if long-conversation history is proven short in real use.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| docs/experiments/experiment-records.md | new section | committed | check_changelog, check_systems | see git log |
| handoff/tasks/kv-cache-1127.md | new | committed | n/a | see git log |
| docs/changelog/entries/2026-11-27-kv-cache-rounds-3-4.md | new | committed | check_changelog | see git log |
