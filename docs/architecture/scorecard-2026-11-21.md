# Scorecard (2026-11-21): speed, architecture, ease of change

Honest status per program. "Measured" = a number from a run; "read" = from the
code only; "not measured" = nobody has run it on the real PC yet.

| Program | Speed | Architecture / ease of change | Verdict |
|---|---|---|---|
| Hub pages (Home, Studio, Help) | Measured 2026-11-20 (PRs #135-#149): Studio 1447 -> 430 KB, Home 266 -> 86 KB, Studio 22 fps in 3D, 13 fps playing a sequence on Chrome 75 TV VM | Pages are built from `parts/` (good). `main_python/main.py` is still 3050 lines, but its `Handler` already mixes in route modules (`hub_api_*`), so a new route is a new file | Fast enough; not finished: `main.py` is the largest remaining file |
| Voice helper (`apps/voice`) | LLM: Typhoon 4B answered in 0.12 s in the 2026-11-04 bench. TTS: Edge 0.6-1.0 s, Spark on GPU 2.6-7.5 s per line. STT: not measured. End to end: not measured | **Weak spot.** `service.py` held one 2700-line `Brain` class (152 methods). This review moved the face-app link (about 580 lines) to `face_link.py`; `Brain` is still about 2200 lines | Needs more splitting (translate, STT, TTS, FAQ are next) |
| Local AI (Ollama) | The first question after 5 idle minutes paid a full model reload (Ollama default `keep_alive` 5m). Fixed by config: `keepAlive: 1h`. Effect not measured yet | Settings are data (`config/local_ai.json`), validated by a QC check | Improved; run `tools/ai_latency.py` on the PC for numbers |
| Answer path | `openai_think` waits for the whole answer, then speaks it (no streaming). A streamed answer could start speaking after the first sentence; the gain is `total - first word`, which `ai_latency.py` measures | Provider calls are one function per kind in `providers.py` (easy to add) | Streaming is the next AI speed step, only worth it if the numbers show a gap |
| Faces app (`apps/faces`) | Not measured here | 1138-line `service.py` | Not reviewed this round |
| Firmware (4 boards) | Only A1-1, A1-2 tested on real hardware; the rest runs on QEMU or fakes | Shared core in `src/core/` once, not copied per module | Lab session still owes real numbers |

## What was changed in this pass

1. `config/local_ai.json`: `keepAlive` 1h, `numParallel` 1 (validated in `tools/ollama_serve.py`, QC `ollama_kv`).
2. `apps/voice/face_link.py`: the face-app link moved out of `Brain` with no behaviour change (QC: 1048 voice/face checks pass).
3. `tools/ai_latency.py`: measures cold and warm first-word and full-answer time against the PC's Ollama.

## Not done, and why

* Streaming answer to speech: wait for `ai_latency.py` numbers first (budget 4 rounds, stop under 10 % gain).
* Splitting `main.py` and the rest of `Brain`: one slice per PR so QC stays readable.
* No real-PC speed numbers exist for this pass: this review ran in the cloud (no GPU, no Ollama).
