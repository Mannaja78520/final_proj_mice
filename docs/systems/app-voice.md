# app-voice

The voice helper: speech in (faster-whisper), answers (saved Q&A, then a local
model), speech out.

## Rules and traps

- Conversation caps speech at 30 s after onset, waits up to 10 s for speech,
  and uses 1.5 s of elapsed quiet to finish a turn. It is turn-taking; it
  waits for its own reply and the rig to finish before reopening the mic.
- Fast device voice is a visible Voice setting (`tts.fastDeviceVoice`). A
  cached server reply wins first; after 650 ms an installed same-language
  voice may start. Named/scenario/mixed voice choices stay with the helper.
  Both playback and Stop own their callbacks; 650 ms is not audible latency.
- Local hearing batches ten-second windows (`local.hear` batchSize and
  chunkSeconds). Specialist pipelines are reused and released with models;
  a lazy CUDA failure replaces the actual specialist on CPU.
- A saved answer's `wholeQuestion` switch limits short social replies to
  whole questions, so an incidental greeting cannot trigger a greeting move.

- Settings are DATA in `config/voice.json`. The unsure-language second pass is
  `stt.fallback` (language, when_not_in, min_probability); no key, no pass.
- An empty store language means DETECT: no language and no bias prompt
  (`check_voice_stt`).
- The HELPER picks the voice (scenario, one voice, two-language line, then the
  map). The page sends a voice only for Try (`check_voice_source`).
- edge-tts options go as `--rate=-10%`: a split `-10%` is read as an option and
  the flat backup voice speaks. A backup wav is never cached under a neural
  voice's name (`check_voice_sound`).
- Answers are a sheet (A42-1): cells edited in place, one Save. Settings must
  not wait for `/api/modules/all` (10 s on a cold scan).
- Questions per language (A42-2): the sheet splits ONE `questions` list by
  script (service.py `detect_lang`, mirrored as `VoiceApp.askLang`) and joins
  it back on edit; the store shape does not change.
- The backup voice is never silent (A42-2): `/health` `voice` says natural
  or not and why; the page shows `#voiceWarn` (`check_voice_sound`).
- Who is there comes from the face watcher's live feed. Watcher down = their
  history, 2.5 s a look (PC, 2026-10-15): `/face` says `watcher:false` and the
  page POSTs `/api/faces/start?only=watcher` once (A42-4).
- `face.on` false (the page's Use faces) = no lookup, presence fails open,
  /camera and /identify refuse; missing = on (`check_voice_view`).
- Show the camera (A42-2): this device = getUserMedia shown only; a rig
  camera = `/api/dev/cam.stream?dev=` from faces.json `look.cameras`; it stops
  with the switch and a hidden tab, and never posts a frame (`check_voice_view`).
- Nothing picked = the "pc:" station the hub shares (`camPicked`), so the page
  never takes the PC webcam from the face app (user 2026-10-15). The picture
  shows only with Show the camera ticked, even while Check by itself reads it.
- Who does each job (A45-1): `use.hear/think/speak` in voice.json is an
  ordered list of ids from `config/voice_providers.json`; the first that
  works answers, a 429 or dead line rests it `restSeconds`. A new service in
  a known wire shape (providers.py WIRES) is one registry entry
  (`check_voice_services`).
- Keys never go in voice.json (GET /config is open on the WiFi, the repo is
  public): `main_python/voice_keys.json`, git-ignored and in SKIP_FILES;
  an old `googleApiKey` is moved there at start. POST /api/voice/keys is gated.
- Every answering service gets the local model's prompt (nearest saved
  answers, scenario, name) and the same guards; a reply in the wrong
  language goes to the next in line.
- Edge speaks in-process (`_edge_speak`), not `python -m edge_tts` per line.
- A scenario's `language` is the main language for that event: the unsure
  hearing pass, the voice fallback and fixed-language asks follow it.
- A45-24: `config/voice_intents.json` (read by `apps/voice/intents.py`) holds
  reply-language requests, read-aloud, new-verse, loanwords and the mixed
  Thai-English second hearing. Write `{3,4000}`, never `{3,}`: the JSONC
  loader drops a comma before `}` (`check_voice_intents`).
- The second hearing runs only when no saved answer fits AND part of the clip
  sounds English (`_language_share`): asked for English, whisper translates.
- A45-25: speaking manner = `config/voice_styles.json`; what a service can do
  is its speak job's `styles` (instruct / prosody / none). The manner is part
  of the cache name; the page's device voice is off while one is chosen
  (`check_voice_styles`). Gemini's manner is untested until a key exists.
- The feeling voice (`apps/voice/tts_spark/server.py`, provider `feeling`)
  runs in its OWN venv in `code/.local/tts_spark` (never under apps/: served
  with no login), transformers 4.57 vs 5.x here; started
  by the helper on first use; `prefer` in voice_styles puts it first. Its
  decode is one captured CUDA graph: HF generate was 50 ms/token on Windows.
  Tests stub `feeling_ready`: a real server on 8779 must not leak into QC.
- A45-26 (2026-10-22): every feeling clip gets a quiet lead + 450 ms tail (the
  last word was cut by the speaker); knobs are the speak job's `tune`, part of
  the cache name (`check_voice_tail`). Clarity first: `prefer` is empty, so
  Edge at -10% speaks (2.9% letters wrong vs 6.1% feeling at its best); a
  manner may still `prefer` the feeling voice. Each scenario has a `style`.
- A45-29: saved voices of the feeling voice (`config/voice_people.json`,
  "person:<id>", 32 invented speaker tokens, same-gender Edge `backup`); the
  speed reaches it as a tempo; the Thai ending/self-word follows the voice's
  gender (`agree`), a manner's own wins. Voice tab quick tiles: `featured`
  tones, `speeds`, women/men voices per language; a click saves
  (`check_voice_people`). `featured`/`speeds` fall back to the shipped
  voice_styles when a character's snapshot predates them.
- `compose` is a registry job with `sameAs: think`; a new verse is checked
  for shape (lines, length, script, list, greeting, saved answer), not rhyme.

- A45-27: named characters live under the voice store's `voice_profiles/` folder
  (location and allowed assets in `config/voice_profiles.json`). The first use
  snapshots existing settings, manners and answers into `default`, then starts
  an editable `current` copy. Main stores and default never receive character saves.
  Each folder has `voice.json`, `qa_data.json`, `voice_styles.json`, `gestures.json`, `audio/`, `motions/`.
- Selection persists in local `active.json`; config and manner edits on disk reload
  on the next request. API saves carry a content revision so stale tabs cannot
  overwrite a new character or external edits. Switching and requests share a lock;
  the audio warm-up uses its own settings snapshot and character cache directory.
- Recorded answer audio travels through `/say` and the single rig speech queue.
  Character YAML moves use the existing hub parser through POST `/api/seqsteps`;
  only `/api/play` moves a robot. Profiles are private, ignored by Git, promotion,
  build stamping and executable packaging.

<!-- generated by tools/systems.py below this line - edit docs/systems.json -->

## Files (24)

- `apps/voice/app.js`
- `apps/voice/app.json`
- `apps/voice/bench/cases.json`
- `apps/voice/bench/run_bench.py`
- `apps/voice/index.html`
- `apps/voice/index.template.html`
- `apps/voice/intents.py`
- `apps/voice/profiles.py`
- `apps/voice/providers.py`
- `apps/voice/qa_data.json`
- `apps/voice/service.py`
- `apps/voice/style.css`
- `apps/voice/tts.ps1`
- `apps/voice/tts_spark/server.py`
- `apps/voice/tts_spark/setup.py`
- `config/voice.json`
- `config/voice_intents.json`
- `config/voice_people.json`
- `config/voice_profiles.json`
- `config/voice_providers.json`
- `config/voice_styles.json`
- `llm/qa_data.json`
- `llm/test.py`
- `qc/data/voice_conversation.mjs`

## Depends on

- nothing

## Used by

- [app-gacha](app-gacha.md)

## Checks that test it (38)

- `check_build_web`
- `check_face_photos`
- `check_faces_cursor`
- `check_faces_loopback`
- `check_faces_presence`
- `check_friend_api`
- `check_login_anywhere`
- `check_no_console_window`
- `check_page_frame`
- `check_qc_receipt`
- `check_speak`
- `check_stale_build`
- `check_translate`
- `check_voice`
- `check_voice_answers`
- `check_voice_bench`
- `check_voice_conversation`
- `check_voice_fast`
- `check_voice_gestures`
- `check_voice_guard`
- `check_voice_identify`
- `check_voice_intents`
- `check_voice_move`
- `check_voice_multi`
- `check_voice_one_voice`
- `check_voice_people`
- `check_voice_profiles`
- `check_voice_reconize`
- `check_voice_services`
- `check_voice_settings`
- `check_voice_sound`
- `check_voice_source`
- `check_voice_stt`
- `check_voice_styles`
- `check_voice_tail`
- `check_voice_talkover`
- `check_voice_tts`
- `check_voice_view`

Run them: `python qc/run_qc.py --no-build check_build_web check_face_photos check_faces_cursor check_faces_loopback check_faces_presence check_friend_api check_login_anywhere check_no_console_window check_page_frame check_qc_receipt check_speak check_stale_build check_translate check_voice check_voice_answers check_voice_bench check_voice_conversation check_voice_fast check_voice_gestures check_voice_guard check_voice_identify check_voice_intents check_voice_move check_voice_multi check_voice_one_voice check_voice_people check_voice_profiles check_voice_reconize check_voice_services check_voice_settings check_voice_sound check_voice_source check_voice_stt check_voice_styles check_voice_tail check_voice_talkover check_voice_tts check_voice_view`
