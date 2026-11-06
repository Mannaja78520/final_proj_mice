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
Step 2 running: `python tools/voice_clips.py transcribe` (CPU, resumable, ~10 min) -> clips_all/clips.json; then `rank`. Next: speaker.py + Spark test (step 5).

## File status
Baseline: 6d94a50

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `handoff/tasks/voice-user-clips-1106.md` | this task | in progress | n/a | this checkpoint |
| `tools/voice_clips.py` | cut / transcribe / rank CLI | done | cut run (88 clips, 4.3-14.5 s); QC voice_user_clips quick | this checkpoint |
| `config/voice_clips.json` | switches + thresholds as DATA, both OFF | done | QC voice_user_clips, sabotage 6/6 | this checkpoint |
| `config/voice_profiles.json` | asset kind `voice` (.wav) | done | QC voice_profiles quick | this checkpoint |
| `apps/voice/user_voice.py` | UserVoice: reference person + event clip | done | QC voice_user_clips | this checkpoint |
| `apps/voice/service.py` | people() lists person:user-voice; /speak `event` | done | QC voice_people, voice_profiles quick | this checkpoint |
| `apps/voice/tts_spark/speaker.py` | clips -> speaker.json (Spark venv) | written, not run | not run | this checkpoint |
| `qc/checks/check_voice_user_clips.py` | new check | done | 6/6 + traversal sabotage caught | this checkpoint |
| `docs/systems.json`, `docs/systems/app-voice.md`, `docs/systems/qc.md` | register new files | done | tools/systems.py build | this checkpoint |

## Facts found
- .local is git-ignored (.gitignore:105) and lives in the MAIN repo root E:/final_proj/mice/mice_system/.local, not in this worktree.
- Recording is 962.8 s (16 min), not 43 min.
- Spark runtime: .local/tts_spark (venv, Spark-TTS, reference.wav). Reference clip -> 32 global tokens (server.py load/prompt); saved voices = config/voice_people.json `speaker` tokens.

## Done
- Cut: 88 clips, 946 s, 4.3-14.5 s (cut.json). Torch here is CPU-only (no cublas64_12.dll): whisper and Spark run on CPU; tools/voice_clips.py falls back by itself (cpu_threads=16: 7 s/clip).
- QC voice_user_clips passes; sabotage caught all 7 breaks.

## Next
1. cut, 2. transcribe, 3. rank, 4. config + QC, 5. Spark test.

## Blocked
- nothing
