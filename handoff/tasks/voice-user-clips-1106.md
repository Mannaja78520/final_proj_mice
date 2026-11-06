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
Nothing: all 5 steps done; waiting for the coordinator/user to review the branch (not merged).

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
| `apps/voice/tts_spark/speaker.py` | clips -> speaker.json (Spark venv, CPU) | done | ran for 3 variants in the Spark test (needs the torchaudio shim, see Facts) | not run | this checkpoint |
| `qc/checks/check_voice_user_clips.py` | new check | done | 6/6 + traversal sabotage caught | this checkpoint |
| `tools/voice_spark_test.py` | Edge vs Spark-reference CER test | done | run 2026-11-06, numbers in experiment-records.md | this checkpoint |
| `docs/experiments/experiment-records.md` | 2026-11-06 section appended | done | raw numbers from spark_test.log | this checkpoint |
| `docs/systems.json`, `docs/systems/app-voice.md`, `docs/systems/qc.md`, `agents.md`, `fw-registry.md`, `hub-show.md` | register new files | done | tools/systems.py build | this checkpoint |

## Facts found
- .local is git-ignored (.gitignore:105) and lives in the MAIN repo root E:/final_proj/mice/mice_system/.local, not in this worktree.
- Recording is 962.8 s (16 min), not 43 min.
- Spark runtime: .local/tts_spark (venv, Spark-TTS, reference.wav). Reference clip -> 32 global tokens (server.py load/prompt); saved voices = config/voice_people.json `speaker` tokens.

## Done
- Cut 88 clips (.local/voice_source/clips_all/, cut.json + clips.json with text, duration, rmsDb, clipFraction, levelSpreadDb, whisper avgLogprob/noSpeechProb/compression, keep/why/rank). 36 kept. Top: clip_0059, 0082, 0049, 0046, 0047.
- Two switchable uses, DATA in config/voice_clips.json (both off, empty): reference (-> person:user-voice via apps/voice/user_voice.py + tts_spark/speaker.py -> voice/speaker.json) and events (event -> clip in the character's voice/ folder, `event` field of POST /speak; falls back to TTS).
- QC voice_user_clips: 18 asserts; break-proved 7 sabotages all caught. Quick suite: 6799 pass, 6 fail then; since fixed: voice_guard 500 (service handler used a brain stub without user_voice_folder) and the system map. Remaining fail: "this PC has a full nong image" (needs `pio run -e mice_nong`, unrelated).
- Spark test (3 sentences, 3 reference variants): Edge 6.3, A 5.3, B 4.6, C 7.5 mean CER %. Best gain 1.7 < 2: stopped. Inside the whisper noise (~2 points).

- GPU rerun (1 round): Edge 4.0, Spark A 8.5, B 12.6, C 8.5 mean CER %; run-to-run spread ~8 points > gaps between references (numbers in experiment-records.md). Full QC 2026-11-06: 9431 pass, 0 fail (903 s). Both features still OFF by default.

## Next
1. A person listens to .local/voice_source/spark_test/ (spark_A/B/C_*.wav vs edge_*.wav): does it sound like the user? CER cannot say.
2. Check the recording has only the user's voice (it is a talk with another person); speaker.py joins clips blind.
3. DONE 2026-11-06 (user said go): installed torch 2.11.0+cu128 and torchvision 0.26.0+cu128 into .local/tts_spark/venv (matches its torchaudio 2.11.0+cu128); server.py now starts on cuda:0 (RTX 5070 Ti) with no shim. Old note: fix the broken Spark venv (torchaudio 2.11+cu128 vs torch 2.15 cpu in user site): the feeling server does not start today without a shim.
4. To use: copy clips to <data>/voice_profiles/<character>/voice/, run speaker.py, set reference.enabled / events in a per-PC override.

## Blocked
- nothing
