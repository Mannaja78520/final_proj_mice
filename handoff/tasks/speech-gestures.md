# Gestures that match speech (Voice + Studio) + safe paths (RRT)

Owner: claude:10220724-db22 (cloud thread "Gestures that match speech")
Updated: 2026-10-22 07:35 +0000
Branch: claude/project-thread-jb3dyr
Last commit: (see branch head)
Plan: A46-1

## Goal
User 2026-10-22: ขอแบบลองสุ่มท่าทางออกมาให้เข้ากับคำที่พูดแล้วส่งทำพร้อมกันด้วย ...
เอาตัวขนาดของหุ่นมาใส่แล้วทำท่าทางได้ อาจจะโคกับ nong studio ดึงข้อมูลจากกันได้.
Then: RRT because of self-collision, also for copying a person (video, dummy follow);
copied moves saved; "drop a video, get a safe saved move" in one step. No RL.

## Design (decided)
- Studio owns the body: FK, IK, collisionAt() on the live rig sizes.
- `app_parts/safe_path.js` (+ `web/safe_path.json`): straight joint path first;
  if it hits, RRT-Connect + shortcuts; `safeKeys(keys)` pass for key lists.
  Live follow: plan with `liveBudgetMs`, no path = hold the last safe pose.
- `config/gestures.json`: library (hand targets in arm-reach units, words per
  language, manners -> tempo/beats, events on/off). Studio fits it to the rig
  (IK + safe paths) and POSTs the fit to the hub (`/api/gestures/fit`).
- Hub `main_python/gestures.py`: picks gestures by words + random beats over the
  speech length, builds /api/play steps from the fit. Voice page starts them
  when the sound starts (2 inserted lines in speakAndWait/speak only: the PC
  thread "Clear natural voice per event" owns the TTS code).
- Studio "Moves while talking" card: try a sentence, show a gesture, save the
  time bar as a gesture, per-event switch.

## Doing now
Step 4: full QC (python qc/run_qc.py --quiet), then PR, merge when green.

## Done
- Voice page: 👋 Gestures switch; doGestures() posts /api/gestures/play when THIS
  answer's sound starts (player.onplaying / utterance.onstart hooks, one line each),
  with the audio's ms, manner, event; not awaited (never holds the next question).
  check_voice_gestures (node, 9 asserts, sabotage 2/2).
- help.html (Studio + Voice), docs/systems (hub-studio, studio traps), plan area A46.
- Quick QC: only failures were mine (fixed: plan heading, Audio hook, awaited gestures).
- Talk gestures: config/gestures.json, main_python/gestures.py (planner),
  /api/gestures (+/fit, /plan open; /play gated), Studio fit + "Moves while
  talking" card (app_parts/talk_gestures.js, html_parts/talk.html).
  check_gestures 36 asserts (browser fit on QC rig 0.7 s, words, seeds, manners,
  events, play asserted on fake_serial.wire, clear at 1 deg), check_gesture_legs
  (800 random plans use only checked legs). Sabotage 2/3 caught (the 3rd, a hitting
  key kept, is caught twice over by safeKeys - redundant guard).
- safe_path.js + web/safe_path.json: straight first, else RRT-Connect + shortcuts
  (8-30 ms on the QC rig). check_safe_path (19 asserts, browser): ways round clear
  at 1 deg, hitting pose refused, video keys safe, dummy live follow holds on a
  hitting pose (asserted on fake_serial.wire), recording saved as a safe move.
  Sabotage: 3 of 3 caught. check_video_moves still green (keepTime for music).
- Video tab: "▶ Make and save" = one click to a safe saved move.
- Dummy: live follow plans round / holds; "● Record the dummy" -> safe saved move.
- HANDOFF/CLAUDE/AGENTS/GEMINI/TEMPLATE: Doing now + push WIP every step.

## Next
1. Full QC, PR, merge (Doing now). Then deploy notes for the PC.
2. QC check_gestures; help.html; systems.json; full QC; PR; merge.

## Blocked
- nothing (real-arm test needs the robot).
