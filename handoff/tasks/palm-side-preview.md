# Palm side preview in Studio

Owner: claude:10221240-e1f5
Updated: 2026-10-22 12:50 +0000
Branch: claude/project-thread-xv9ny0
Last commit: (first WIP)
Plan: A45-28

## Goal
User 2026-10-22: "เราสามารถเลือก ฝ่ามือยกขึ้นหรือหลังมือยกขึ้นได้แต่มันจะลักษณะไม่เหมือนกันไหมตอนทำจริงๆ
เพราะมันแค่ไปใกล้ที่สุดเท่าที่ทำได้ เอาแบบเลือกได้ตอน drag หรือแก้ค่าด้วยจะได้เห็นว่าไปถึงไหนอย่างไร
แล้วกดเซฟท่าตามนั้นได้". Palm up / back up held while dragging a hand and while
typing a wrist position; live view of the pose the arm really reaches (gap to
the target, palm angle, joints at their stop, self-collision); save exactly that.

## Doing now
QC setup + new check. Built: in Studio web (nong/main_python_set_nong/web):
- hand_side.json (new data file): drag window/step, thresholds.
- ik_4_dof_arm.js: facePalm(p, arm, want, opts) gains opts {range, step, safe}.
- sliders.js renderHands: per hand "keep while moving" select (free/palm/back),
  reach readout (side + degrees from straight up, gap to target mm, joints at
  their stop, hits itself), Save as new move / Save into selected move.
- picking_drag.js: wrist drag applies the hold (local window per frame, full on release).
- sliders.js gotoXyz: applies the hold after reaching.
- 3D: ghost target ball + line to the reached wrist.
- qc/checks/check_palm_hold.py (new), help.html entry.

## Done
- Answered the user's question in the thread (Thai).
- Code written and built (hand_hold.js, hand_side.json, facePalm opts, drag/goto
  hold, readout + save buttons). Syntax ok; not yet run in a browser.

## Next
1. Cloud QC setup (pip install pyserial psutil platformio; pio run -e mice_nong).
2. Write qc/checks/check_palm_hold.py; run it + check_palm_side, check_studio_cost.
3. help.html entry, docs/systems/studio.md trap line, full QC, PR, merge.

## Blocked
- nothing (real-arm test needs the robot; fake only)
