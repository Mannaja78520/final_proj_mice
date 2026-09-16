# Panel review - 2026-08-23 12:38

**Question.** Review a small change in .staging/nong/main_python_set_nong/web/app.js. selectKey(i) now also parks the show clock: playT = keyStartMs(i) and the scrub slider follows. New helper keyStartMs(i) walks playKeys() (the PLAYED timeline: suspended keyframes dropped, moves after a gap re-timed) and returns hold0 + sum of t+hold for played entries before that keyframe; a suspended target lands where the next played move begins, or totalMs(). Claim: pressing Play after clicking a move starts AT that move at its own speed; holds counted; suspended skipped exactly as playback skips them; keyframe 0 gives 0. Check what is NOT true: the sum, the suspended fallback, interaction with delKey (calls selectKey), scrubTo, togglePlay reset at playT>=totalMs, and hub-driven mode which passes from_ms to ShowPlayer. Answer in at most 18 lines.

**Files.** none
**Cost.** 523891 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **FAILED** Error: timeout waiting for response

## What each model said

### gemini-3.1-pro-high  _(262.4s, 71120 tokens)_

 - **unchecked** `:` app.js:keyStartMs, sum adds hold0, keyframe 0 gives hold0 not 0.
 - **unchecked** `:` Suspended fallback fine.
 - **unchecked** `:` app.js:delKey, calls selectKey, jumps playhead on deletion.
 - **unchecked** `:` app.js:scrubTo, calls selectKey, snaps playhead preventing smooth scrub.
 - **unchecked** `:` app.js:togglePlay, resets at totalMs, playing last suspended rewinds.
 - **unchecked** `:` app.js:ShowPlayer, selectKey modifies playT, desyncs hub-driven playback.
 - **unchecked** `:` app.js:keyStartMs, sum adds hold0, keyframe 0 gives hold0 not 0.
 - **unchecked** `:` Suspended fallback fine.

### gemini-3.7-flash-high  _(223.8s, 225901 tokens)_

 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:keyStartMs: returns `hold0` for keyframe 0; violates claim of 0 whenever `hold0 > 0`.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:keyStartMs: sum lands at start of move towards $i$ (pose $i-1$), but `selectKey(i)` poses robot at $i$.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:keyStartMs: moves following gap run at re-timed gap speed rather than move's own speed.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:keyStartMs: trailing suspended key fallback returns `totalMs()`, causing `togglePlay` to reset to 0 instead of staying.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:selectKey: suspended key parks `playT` at next played move while editor displays suspended pose, desyncing viewport from clock.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:delKey: calling `selectKey` overwrites `playT` and moves scrub slider mid-playback, discarding user playhead.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:scrubTo: keyframe selection triggering `selectKey` snaps `playT` to `keyStartMs(i)`, breaking smooth scrub.
 - **unchecked** `:` .staging/nong/main_python_set_nong/web/app.js:togglePlay: selecting final keyframe sets `playT = totalMs()`, causing `playT >= totalMs` check to rewind show to 0 on Play.
