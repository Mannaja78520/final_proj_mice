# Panel review - 2026-08-24 00:29

**Question.** A20-10 QC-green, review before promote. A voice answer may carry move+module; service.py /ask passes them through; main.py seq_steps() parses sequence yaml into play steps (route /api/seqsteps); page index.html fetches steps then POSTs /api/play itself and shows Stop. Read apps/voice/service.py, apps/voice/index.html, and seq_steps in main_python/main.py. What is NOT true? One finding per line.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 568472 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/index.html:149` ask() overwrites $('wait') during motion, destroys visible 'Stop the move' control.
 - **real** `apps/voice/index.html:216` mvTimer assignment lacks clearInterval(), subsequent moves leak background status polling intervals.
 - **real** `main_python/main.py:1182` seq_steps() persists cur_speed across poses, motion speeds diverge from Studio keyframe scoping.
 - **real** `main_python/main.py:1188` seq_steps() drops wait: lines preceding first pose, initial hold timing lost.
 - **real** `main_python/main.py:1189` seq_steps() overwrites hold on consecutive wait: entries, fails to accumulate delays.
 - **real** `main_python/main.py:1209` seq_steps() truncates duration with int(), creates 1 ms divergence from Studio autoTime().
 - **real** `apps/voice/qa_data.json:1` FAQ omits move and module, rig answers fail to trigger motion.
 - **fine** `apps/voice/service.py:379` logic is fine.

## What each model said

### gemini-3.1-pro-high  _(609.6s, 214477 tokens)_

 - **FAILED** Error: timeout waiting for response

### gemini-3.7-flash-high  _(266.6s, 303810 tokens)_

 - **unchecked** `:` apps/voice/qa_data.json:1, no FAQ entry defines `move` or `module`, rig answers never trigger motion out of the box.
 - **unchecked** `:` apps/voice/service.py:379, `service.py` passes lone `move` or `module` on FAQ hit, `index.html:168` drops motion unless both exist.
 - **unchecked** `:` main_python/main.py:1182, `seq_steps()` persists `cur_speed` across subsequent poses, motion speeds diverge from Studio keyframe scoping.
 - **unchecked** `:` main_python/main.py:1189, `seq_steps()` overwrites `hold` on consecutive `wait:` entries instead of accumulating delays.
 - **unchecked** `:` main_python/main.py:1188, `seq_steps()` drops `wait:` lines preceding first pose, initial hold timing is lost.
 - **unchecked** `:` main_python/main.py:1209, `seq_steps()` truncates duration with `int()` instead of rounding, creating 1 ms divergence from Studio `autoTime()`.
 - **unchecked** `:` apps/voice/index.html:216, `mvTimer` is overwritten without `clearInterval()`, subsequent moves leak background status polling intervals.
 - **unchecked** `:` apps/voice/index.html:149, `ask()` overwrites `$("wait")` content during active motion, destroying visible "Stop the move" control.
