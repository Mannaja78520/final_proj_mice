# Voice Conversation Mode — Second-Round Codex Fixes Review

## Goal
Review the three fixes applied to `apps/voice/index.html` after the second
claudex-loop finding pass (VOICE-01, VOICE-02, VOICE-03 from the second round).

## Changes under review

1. **`convRms()` centering fix** (line ~263): Subtract 128 from each byte sample
   so silence (value 128) maps to 0.0, not ~0.5. Formula: `c = (buf[i]/128.0) - 1.0`.

2. **`speakAndWait()` function** (line ~521): New function that resolves only
   on `player.onended` (playback complete), not `player.play()` (play-start).
   Takes an `AbortSignal` to cancel during playback. Used in the conversation
   loop so the microphone doesn't capture the assistant's answer as a question.

3. **Session-ID tracking** (`convSession`): Replaces `convToken` with a
   monotonically-increasing session ID checked after each `await` in
   `startConv()` and `convListenOnce()`. `stopConv()` bumps it on Stop.
   `convAbort` (AbortController) is passed to all `fetch()` calls so in-flight
   requests are cancelled on Stop.

## Acceptance criteria
- Silence is detected correctly (RMS < 0.01 when quiet, > 0.01 when speech)
- `speakAndWait` resolves only after audio playback finishes
- Stop immediately halts transcribe/ask/speak phases (no stale requests)
- Recording stops if session changes mid-await

## Verification
- `python qc/run_qc.py --quick --only voice` — voice checks pass
- `python qc/run_qc.py --quick` — all quick checks pass

## Files
- `apps/voice/index.html` (already promoted to main tree)
