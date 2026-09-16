# Panel review - 2026-08-23 23:51

**Question.** A20-10 design review BEFORE code. CLAIM: a saved voice answer can also MOVE the robot. Plan: qa_data.json entries gain optional move (a saved sequence file name) + module (target dev); apps/voice/service.py /ask just PASSES those two fields through on a FAQ hit - the service never touches the password or the show clock. New hub GET /api/seqsteps?name= parses the SAME yaml /api/loadseq serves into ready steps {pose10,t,hold}, loop - read-only, ungated like loadseq; parser mirrors Studio semantics: T explicit on exports, wait becomes hold, speed step remembered, old 8-value pose padded to 10 with 90s, missing T computed as max joint delta over speed like firmware durationFor. Voice page then POSTs /api/play {dev:module, steps, loop, name} itself - the page holds the login, so gating stays intact. QUESTIONS: 1) AUTO-play the movement when the answer carries one, or only behind a button? My lean: AUTO with a big visible Stop (visitors at a robot show expect the robot to act when asked; /api/play/stop stays ungated for safety) - argue either way. 2) Is a SECOND yaml parser in main_python justified vs duplicating Studio JS parseSeqYaml into the voice page - or is there a third place I missed? 3) Traps in seqsteps: chain field next, skipped rgb/music steps, pose count validation against the target module type? Answer in at most 18 lines.

**Files.** app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py
**Cost.** 309596 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `apps/voice/service.py:80` match_faq extracts string answer, drops move and module preventing movement dispatch.
 - **real** `apps/voice/service.py:370` do_POST hardcodes JSON keys, omits move and module breaking client sequences.
 - **real** `apps/voice/index.html:164` ask ignores movement data, lacks /api/play POST needed to animate rig.
 - **fine** `app.json:` app.json is fine.
 - **fine** `bench/cases.json:` bench/cases.json is fine.
 - **fine** `bench/run_bench.py:` bench/run_bench.py is fine.
 - **fine** `qa_data.json:` qa_data.json is fine.

## What each model said

### gemini-3.1-pro-high  _(75.0s, 49090 tokens)_

 - **real** `apps/voice/service.py:80` saves string answer, drops move and module fields.
 - **real** `apps/voice/service.py:370` hardcodes JSON keys, omits move and module.
 - **real** `apps/voice/index.html:164` lacks /api/play POST, ignores movement data.
 - **real** `hub:` Hub /api/seqsteps: reject new endpoint, backend parser adds useless layer.
 - **real** `studio:` Parser: export Studio JS parser, share via new file.
 - **maybe** `voice:` Auto-play: play automatically, visitors expect immediate action. Add stop button.
 - **real** `seqsteps:` Traps: chain next causes infinite loops. Skipped rgb/music steps corrupt pose indices. Pose count mismatch crashes target module.

### gemini-3.7-flash-high  _(115.1s, 205806 tokens)_

 - **real** `E:\final_proj\mice\code\apps\voice\service.py:80` match_faq returns answer string, drops move and module from qa_data.json
 - **real** `E:\final_proj\mice\code\apps\voice\service.py:370` do_POST serializes only answer, must pass move and module payload
 - **real** `E:\final_proj\mice\code\apps\voice\index.html:167` ask ignores move fields, needs sequence dispatch and stop UI
 - **fine** `E:\final_proj\mice\code\apps\voice\app.json:1` fine
 - **fine** `E:\final_proj\mice\code\apps\voice\bench\cases.json:1` fine
 - **fine** `E:\final_proj\mice\code\apps\voice\bench\run_bench.py:1` fine
