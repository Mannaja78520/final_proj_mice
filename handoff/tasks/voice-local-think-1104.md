# Local Thai think model (Typhoon 2.5 4B)

Owner: claude (cloud thread "Judge local AI and voice from Short")
Updated: 2026-11-04
Branch: claude/project-thread-vevw1p

## Goal
User 2026-11-04: try a better local "think" model for all languages; "ถ้าดีก็จัด".

## Doing now
Full QC running, then merge PR #116 and rebuild the hub on the PC. Bench ran on the PC (.local/think_bench_2026-11-04, PC only).

## Facts found
- Typhoon 2.5 4B Q4_K_M: Thai 24/30 (Qwen 0.5B 10/30), "ครับ" 15/15, 0.12 s, 3.2 GB VRAM. 30B-A3B models only +2 points, 5x slower.
- Lao is weak in every model tried.
- Bench ran WITHOUT the friend's face app: re-run with it on (VRAM share).
- llama.cpp download was blocked; second Ollama on 127.0.0.1:11435, models in D:\local-ai\ollama-models (not autostart).

## After a PC reboot (manual, no autostart: user rule)
Start the second Ollama before the Voice app needs "think", PowerShell:
`$env:OLLAMA_HOST="127.0.0.1:11435"; $env:OLLAMA_MODELS="D:\local-ai\ollama-models"; ollama serve`
Models there: typhoon25-4b (used), typhoon25-30b, qwen3-30b-a3b. GGUF files: D:\local-ai\models.
Without it, think falls back to the local Qwen 0.5B by itself.

## Next
1. PC: keep the 11435 Ollama running (or move models into the 11434 one), re-bench with the face app on.
2. Add answer_ko / answer_lo and Korean/Lao prompts (service.py _think_prompt has en/ja/zh only).

## File status
| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `config/voice_providers.json` | ollama think = typhoon25-4b on :11435 | done | voice QC 774/0 | this PR |
| `config/voice.json` | think order ollama, local | done | voice QC | this PR |
| `apps/voice/service.py` | local retry keeps FAQ | done | check_voice_intents + sabotage caught | this PR |
| `llm/qa_data.json` | answer_en/ja/zh for 4 FAQs | done | voice QC | this PR |
| `qc/checks/check_voice_intents.py` | _retry_keeps_faq | done | sabotage caught | this PR |
