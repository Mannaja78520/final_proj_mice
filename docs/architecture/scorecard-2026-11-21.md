# Scorecard (2026-11-21): speed, architecture, ease of change

Honest status per program. "Measured" = a number from a run; "read" = from the
code only; "not measured" = nobody has run it on the real PC yet.

| Program | Speed | Architecture / ease of change | Verdict |
|---|---|---|---|
| Hub pages (Home, Studio, Help) | Measured 2026-11-20 (PRs #135-#149): Studio 1447 -> 430 KB, Home 266 -> 86 KB, Studio 22 fps in 3D, 13 fps playing a sequence on Chrome 75 TV VM | Pages are built from `parts/` (good). `main_python/main.py` is still 3050 lines, but its `Handler` already mixes in route modules (`hub_api_*`), so a new route is a new file | Fast enough; not finished: `main.py` is the largest remaining file |
| Voice helper (`apps/voice`) | LLM: Typhoon 4B answered in 0.12 s in the 2026-11-04 bench. TTS: Edge 0.6-1.0 s, Spark on GPU 2.6-7.5 s per line. STT: not measured. End to end: not measured | Was the weak spot: one 2700-line `Brain` class. Now split into `face_link`, `translator`, `langs`, `listener`, `speaker`, `faq`, `local_llm`, `answerer` (one job each, Brain inherits them); `service.py` 3913 -> 1125 lines (Brain core, health, HTTP handler) | Done for this app; the rest of the weight is `main_python/main.py` |
| Local AI (Ollama) | Measured on the PC 2026-11-21: first question on an unloaded model 45 s, then 0.18 s per answer (155 tokens/s). Fixed: `keepAlive` 1h and a warm-up at helper start (warm-up call 3.0 s with a hot disk cache) | Settings are data (`config/local_ai.json`), validated by a QC check | Improved; run `tools/ai_latency.py` on the PC for numbers |
| Answer path | `openai_think` waits for the whole answer, then speaks it (no streaming). A streamed answer could start speaking after the first sentence; the gain is `total - first word`, which `ai_latency.py` measures | Provider calls are one function per kind in `providers.py` (easy to add) | Streaming LLM->TTS NOT built: warm answers take 0.18 s, so it would save about 0.15 s. TTS is the real cost (Edge 0.6-1 s, Spark 2.6-7.5 s); Edge also failed on the PC (silent Premwadee voice), now covered by a spare-voice fallback |
| Faces app (`apps/faces`) | Not measured here | 1138-line `service.py` | Not reviewed this round |
| Firmware (4 boards) | Only A1-1, A1-2 tested on real hardware; the rest runs on QEMU or fakes | Shared core in `src/core/` once, not copied per module | Lab session still owes real numbers |

## What was changed in this pass

1. `config/local_ai.json`: `keepAlive` 1h, `numParallel` 1 (validated in `tools/ollama_serve.py`, QC `ollama_kv`).
2. `apps/voice/face_link.py`: the face-app link moved out of `Brain` with no behaviour change (QC: 1048 voice/face checks pass).
3. `tools/ai_latency.py`: measures cold and warm first-word and full-answer time against the PC's Ollama.

## Not done, and why

* Splitting `main_python/main.py` (3183 lines; `Handler` alone is 1304, with `api` 321, `route` 237, `dev_route` 213 lines): needs a route-table design and the hub is being edited by other threads, so it is its own task.
* STT speed: needs a real voice (the bench ran typed text). Lab list.
* Spark TTS timing: not re-measured.
