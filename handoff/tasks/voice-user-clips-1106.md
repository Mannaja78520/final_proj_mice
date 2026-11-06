# User's own voice clips: Spark-TTS reference + fixed per-event clips

Owner: claude:voice-clips-1106
Updated: 2026-11-06 (Bangkok)
Branch: claude/project-thread-2u4m3f
Last commit: 6d94a50 (baseline)
Plan: none yet (not added to PLAN.html: coordinator task)

## Goal
User recorded their own speech (.local/voice_source/recording_20261105.m4a). Cut all speech
into 3-15 s clips, transcribe, rank, then make two switchable uses as DATA (default off):
(a) Spark-TTS reference set, (b) per-event fixed clips. Audio + transcripts stay in .local only.
Test Spark-TTS with the best reference vs Edge by whisper CER; record in experiment-records.md.

## Doing now
Step 1: re-cut with ffmpeg silencedetect into .local/voice_source/clips_all/ (tools/voice_clips.py).

## File status
Baseline: 6d94a50

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-user-clips-1106.md` | this task | in progress | n/a | this checkpoint |

## Facts found
- .local is git-ignored (.gitignore:105) and lives in the MAIN repo root E:/final_proj/mice/mice_system/.local, not in this worktree.
- Recording is 962.8 s (16 min), not 43 min.
- Spark runtime: .local/tts_spark (venv, Spark-TTS, reference.wav). Reference clip -> 32 global tokens (server.py load/prompt); saved voices = config/voice_people.json `speaker` tokens.

## Done
- nothing yet

## Next
1. cut, 2. transcribe, 3. rank, 4. config + QC, 5. Spark test.

## Blocked
- nothing
