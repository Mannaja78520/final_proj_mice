# Built so far (moved out of HANDOFF.md, 2026-11-26)

Owner: none (a status log, not a task)
Updated: 2026-11-26
Branch: -
Last commit: see git log
Plan: -

Moved from HANDOFF.md to keep it under its 150-line cap (Size rule, same file). It is a status log, not a rule.

As of main c859601 (2026-10-21): all merged, PRs #1-#40. Verified on the PC:
- Faces: photo test 16/16; face history follows the friend's node_id/seq cursor (A45-16); friend's server now runs dual/CUDA concurrent inference (A45-17).
- Studio: save to robot, robot settings, palm/back per hand (fake robot only); Video tab (YouTube, public Google Drive, Dropbox, direct links) makes moves; real dance video checked (A45-19).
- Voice (PR #39, #40): login on every voice route, no name blink on 429, 30 s speech, Thai/English/Japanese/Chinese hearing and answers, a fast installed-voice option that races server speech after 650 ms. Cached answer-to-audio 0.2-0.4 s; new Thai phrasing can take ~5 s. Detail: `docs/voice-validation-2026-10-20.md`.
- Show/timeline/music/SD upload played on the real nong 2026-10-12.
- Prize machines (gachapon, A47, 2026-10-22, fakes only): firmware `mice_gacha`, hub app /app/gacha/, Voice prizes + Questions tab. Open: handoff/tasks/gachapon.md (bench A47-5).
- Lab day (2026-10-22): every test that needs a board, the robot or a person is ONE checklist, handoff/tasks/lab-day.md. Nothing else is open without hardware, the user's keys or the friend.
