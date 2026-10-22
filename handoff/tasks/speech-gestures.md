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
Step 1: safe paths in Studio. Files: app_parts/safe_path.js (built after
collisions.js), web/safe_path.json, qc/checks/check_safe_path.py (browser:
a straight move through the body must come back as a way round with no hit;
an unreachable/hitting pose must be refused). Then hook into video + dummy.

## Done
- safe_path.js written (not yet in tools/web_build.json, not tested).
- HANDOFF/CLAUDE/AGENTS/GEMINI: "update the task file and push WIP after every step".

## Next
1. Add safe_path.js to tools/web_build.json, safe_path.json, hook into video
   (vidBuild/vidUse + one-click save), dummy follow (live + record).
2. config/gestures.json, main_python/gestures.py, hub routes, Studio card, Voice page.
3. QC: check_safe_path (colliding cases on the fake rig), check_gestures; full QC; PR.

## Blocked
- nothing (real-arm test needs the robot).
