# Panel review - 2026-08-24 02:55

**Question.** A20-12 QC-green, review before promote. Voice settings for a designer on apps/voice/index.html: Answers (add/edit/delete saved answers with questions, answer, move dropdown from /api/list kind=sequences and robot NAME dropdown from /api/modules/all, hear via POST /api/voice/say), Voice and language (tts/stt switches, voice pick + Try it, whisper model as Fast/Balanced/Most accurate), Words it gets wrong (bias chips per language), Advanced behind the technical switch. Saves: helper apps/voice/service.py gained GET/POST config+faq; hub gates both POSTs like /api/settings; Brain.maybe_reload stats voice.json per request and drops cached stt/llm whose model id changed - no restart. Read apps/voice/service.py, apps/voice/index.html, qc/checks/check_voice_settings.py. What is NOT true? One finding per line.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 546560 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/service.py:61` maybe_reload() clears self._stt without self._lock, crashing concurrent listen() on NoneType.
 - **real** `apps/voice/index.html:702` collectAdvanced() parses empty threshold as NaN which serializes as null, crashing match_faq() on float(None).
 - **real** `apps/voice/index.html:603` cfg.tts is undefined on fresh config, crashing fillVoices().
 - **real** `apps/voice/index.html:517` fillPick() clears dropdowns for offline robots, silently deleting move and module on edit.
 - **real** `apps/voice/service.py:83` maybe_reload() ignores enabled:false, leaving disabled instances answering.
 - **real** `apps/voice/service.py:85` maybe_reload() compares missing model to small, dropping and reloading model every request.
 - **real** `apps/voice/index.html:276` speak() omits lang, making tryVoice() test saved language instead of selected language.

## What each model said

### gemini-3.1-pro-high  _(305.3s, 123428 tokens)_

 - **real** `apps/voice/service.py:85` want is None when config omits model, dropping loaded default model every save.
 - **real** `apps/voice/index.html:603` cfg.tts is undefined on fresh config, crashing fillVoices.

### gemini-3.7-flash-high  _(506.8s, 362867 tokens)_

 - **unchecked** `:` apps/voice/index.html:276, `speak()` omits `lang` in `POST /api/voice/say`, so `tryVoice()` and `hear()` speak with store default language instead of selected language.
 - **unchecked** `:` apps/voice/service.py:83, `maybe_reload()` checks model id but ignores `enabled: false`, so disabling STT or LLM fails to stop cached instances from answering.
 - **unchecked** `:` apps/voice/service.py:83, `maybe_reload()` evaluates missing `model` key as `None` instead of `"small"`, causing model drop and reload on every request.
 - **unchecked** `:` apps/voice/service.py:61, `maybe_reload()` clears `self._stt` and `self._llm` without acquiring `self._lock`, causing `NoneType` race condition crashes during concurrent `listen()` or `generate()`.
 - **unchecked** `:` apps/voice/index.html:702, `collectAdvanced()` parses empty threshold inputs as `NaN` which serializes as JSON `null`, crashing `Brain.match_faq()` on `float(None)`.
 - **unchecked** `:` apps/voice/index.html:517, `fillPick()` resets dropdown value to empty when saved sequence or robot is missing from live lists, silently clearing `move` and `module` on edit.
