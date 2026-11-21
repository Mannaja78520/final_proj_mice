# Architecture review + AI speed (2026-11-21)
Owner: claude (thread "Review architecture and speed up AI")
Updated: 2026-11-21
Branch: claude/project-thread-0qwlfz
Last commit: this checkpoint
Plan: none

## Goal
User 2026-11-21: is the architecture good, OOP, easy to change and fast; any way to make every program and the AI faster?

## Doing now
Branch claude/project-thread-0qwlfz: PR with keepAlive, face_link split, ai_latency tool, scorecard.

## Done
- keepAlive/numParallel (tools/ollama_serve.py, config/local_ai.json, QC ollama_kv)
- Brain face block -> apps/voice/face_link.py (mixin FaceLink)
- tools/ai_latency.py (not run: no Ollama in cloud)
- docs/architecture/scorecard-2026-11-21.md

## Next
- Run tools/ai_latency.py on the PC, record numbers in experiment-records.md
- Split more of Brain (translate, STT, TTS, FAQ); then main.py
- Streaming answer to speech only if numbers show a gap

## Facts found
- apps/voice/providers.py:258 openai_think blocks for the whole reply (no stream).
- apps/voice/service.py Brain was lines 513-3222 (2700 lines, 152 methods).

## File status
File | Change | State | Verification | Commit
--- | --- | --- | --- | ---
tools/ollama_serve.py | keepAlive/numParallel | done | quick QC ollama_kv pass | this checkpoint
config/local_ai.json | keepAlive 1h | done | same | this checkpoint
apps/voice/face_link.py | new, moved from service.py | done | voice/face QC 1048 pass (cloud, fakes) | this checkpoint
apps/voice/service.py | face block removed | done | same | this checkpoint
qc/checks/check_voice_identify.py | source path to face_link.py | done | pass | this checkpoint
qc/checks/check_ollama_kv.py | keepAlive asserts | done | pass | this checkpoint
tools/ai_latency.py | new | done | not run (no Ollama) | this checkpoint
docs/systems.json, docs/systems/ | register ai_latency | done | build ok | this checkpoint
docs/architecture/scorecard-2026-11-21.md, docs/experiments/experiment-records.md | docs | done | n/a | this checkpoint

## Update 2026-11-21 (branch claude/brain-split-translate, off #150)
- Moved Translator (translate, translate_text, translate_all) to apps/voice/translator.py and detect_lang/scripts_in to apps/voice/langs.py; Brain(FaceLink, Translator). service.py 3913 -> 3200 lines. Voice/resource/systems QC 1251 pass (cloud, fakes). check_resource_policy now parses translator.py too.
- PC latency run requested via Remote Control (numbers pending).

## Update 2026-11-21 (branch claude/brain-split-speaker)
- Brain now Brain(FaceLink, Translator, Listener, Speaker). Speaker (voices, cache, manner, Edge/Windows engines, scenarios) in apps/voice/speaker.py; speaker uses self._m().CODE / .subprocess = the Brain's own module globals, so checks that swap mod.CODE keep working. service.py 3913 -> ~2000 lines.
- Next: FAQ/answer prompt (_think_prompt, generate, faq_*) out of Brain; main.py (3050 lines).
