# Palm side preview in Studio

Owner: claude:10221240-e1f5
Updated: 2026-10-22 13:00 +0000
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
Full QC (`python qc/run_qc.py --quiet`), then PR + merge.

## Done
- Answered the user's question in the thread (Thai).
- Built: hand_hold.js + hand_side.json, facePalm(..., {range, step, safe}),
  hold in wrist drag and gotoXyz, readout (side + degrees, gap, stops, self-hit),
  orange target mark, Save as a new move / Save into the selected move.
- check_palm_hold (17 asserts) green; sabotage caught 5/5 (drag hold, safe
  search, typed hold, stale target, save). check_palm_side, check_ref,
  check_designer_first, check_safe_path, check_studio_cost green.
- help (main_python/web/help/parts/studio.html), docs/ref_data.js palm-side,
  docs/systems/studio.md trap line. Screenshots at 1280 and 390 looked right.

## Next
1. Full QC, PR, merge; delete this file in the PR; plan.py done A45-28.

## Blocked
- nothing (real-arm test needs the robot; fake only)
