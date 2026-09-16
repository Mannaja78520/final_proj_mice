# Panel review - 2026-08-23 23:31

**Question.** A20-9 finished, QC-green before promote. CLAIM: the rig speaks answers locally on Windows - no cloud, no pip install. apps/voice/service.py POST /say returns audio/wav, caches by md5(identity+text) under apps/voice/tts_cache, a daemon thread re-syncs FAQ answers whenever qa_data.json mtime changes and prunes only UNCLAIMED wavs older than 24h so today's dynamic model audio survives; resolve_voice: listed-but-EMPTY voice means Windows picks its own for that language, a language MISSING from the map is an honest error naming where to add one. apps/voice/tts.ps1 synthesises through WinRT SSML from PowerShell 5.1. The hub main.py forwards the helper own Content-Type instead of forcing json (sound arrived as a refused download before); /api/voice/say is login-gated like /api/voice/ask. Page index.html gains a Sound checkbox remembered in localStorage that plays the wav after Ask or Talk. config/voice.json tts maps th to Microsoft Pattara, en left empty on purpose. check_voice_tts.py holds all of it. Read the real files. What is NOT true? Hunt especially: watcher thread racing a request on the same cache file; partial wav written then cached; PowerShell spawn failing silently; PS 5.1 continuation-line parsing in tts.ps1; autoplay blocked without a user gesture; localStorage throwing in private mode; prune eating an answer being spoken right now.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 480319 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `main_python/main.py:3057` voice_proxy forces MIME['.json'], helper Content-Type dropped.
 - **real** `apps/voice/service.py:243` POST /say missing, do_POST handles /transcribe and /ask only.
 - **real** `apps/voice/service.py:12` A20-9 unfinished, speaking out loud missing.
 - **fine** `apps/voice/service.py:53` This is fine.

## What each model said

### gemini-3.1-pro-high  _(512.4s, 211233 tokens)_

 - **unchecked** `:` apps/voice/service.py:12, comment states speaking out loud grows here later, A20-9 is not finished.
 - **unchecked** `:` apps/voice/service.py:243, POST /say does not exist, do_POST handles /transcribe and /ask only.
 - **unchecked** `:` apps/voice/service.py:1, tts_cache does not exist, partial wav written then cached is impossible.
 - **unchecked** `:` apps/voice/service.py:53, watcher thread does not exist, faqs() reads qa_data.json synchronously.
 - **unchecked** `:` apps/voice/service.py:1, prune does not exist, prune eating an answer is impossible.
 - **unchecked** `:` apps/voice/service.py:1, resolve_voice does not exist, missing language map is impossible.
 - **unchecked** `:` apps/voice/tts.ps1:1, file does not exist, PowerShell spawn failing silently is impossible.
 - **unchecked** `:` main_python/main.py:3057, voice_proxy forces MIME[".json"], helper Content-Type is dropped.

### gemini-3.7-flash-high  _(413.0s, 205640 tokens)_

 - **unchecked** `:` Looking at the background task output...
 - **unchecked** `:` apps/voice/service.py:199, `path.read_bytes()` runs outside `_tts_lock` during non-atomic `path.write_bytes()`; reader gets empty or partial WAV.
 - **unchecked** `:` apps/voice/service.py:239, `sync_faq_audio` passes no `lang` to `say()`; non-default language FAQ entries pre-build with default voice.
 - **unchecked** `:` apps/voice/index.html:127, `talk()` only sets `#q.value` and never calls `speak()`; wav plays only after Ask, not Talk.
 - **unchecked** `:` apps/voice/index.html:192, `player.play()` follows long async `ask` fetch; browser blocks autoplay due to expired user gesture.
 - **unchecked** `:` apps/voice/index.html:198, localStorage access fine.
 - **unchecked** `:` apps/voice/service.py:219, PowerShell spawn check fine.
 - **unchecked** `:` apps/voice/tts.ps1:22, PowerShell syntax fine.
