# Native SolidWorks axes and planes audit — completed

Owner: codex:10231404-5229
Updated: 2026-10-23T19:05:05.792433+07:00
Branch: codex/native-axis-1023
Tree: E:/final_proj/mice/code/.staging-native-axis-1023
Last commit: ee9c0ed (native geometry checkpoint); final completion commit follows
Plan: robot A48-12

## Goal
Check all 10 native SolidWorks joint axes, left/right mirrors and XY/XZ/YZ planes against exported URDF and Studio command90/CADzero/Home. Read-only native audit authorized by parent chat 01a16787-933e-7d81-97a1-0a3561d110b9; status/results sent to main 01a1689b-5608-7123-b8c2-a6f489b5b675 and dedicated hardware owner 01a167a0-2a75-7c93-89ea-81df71a29ff4.

## Doing now
Audit and report complete. Final checkpoint/plan closure/resource release only. No source promotion or CAD change is part of this task.

## Facts found
- model/nong_urdf/solidworks/setup_native.py:24-26,93-96 creates URDF reference frames from STEP-derived joints_review.json; matching refs alone was insufficient independent proof.
- Root scratch/native-axis-1023/native_capture.json is independent in-context COM evidence from intended native analytic cylinders via component Transform2: all ten axes agree with URDF; paired shoulder/elbow hinges are perpendicular. No exporter axis-line correction is indicated.
- Carrier-plane differences are already in the saved native pose. Shoulder center asymmetry is consistent with a shared saved shrug rotation; it does not establish an intrinsically asymmetric mount. Detailed numeric angles/positions remain private scratch only.
- Underlying subassembly document mate dimensions are not flexible-root-instance angles or physical servo calibration. Native COM capture and mate enumeration had zero API errors.
- Parent fit snapshot swaps both shoulder pitch/roll bindings. Command90, saved Home and native drawn0 are distinct; saved shrug Home does not equal exact native0. Preserve warnings where native/proxy chains differ.
- Software fit does not verify hardware channel, sense, gear ratio or horn neutral. Dedicated hardware chat owns real testing; this task did not move or calibrate the robot.
- Canonical native assembly remained read-only, clean and hash-identical before/after. Python COM client63476 exited; no explicit save/export/close/pose calls were made.

## Done
- Independent native audit: 264 components, 241 active leaves, 1519 analytic cylindrical faces, 11 coordinate frames, 10 reference axes, 12 unique native assembly documents and 384 mate features.
- Private numeric report: root scratch/native-axis-1023/native-axis-audit.md + .json; actual center/axis/plane/mirror/projection and command/Home mapping tables, bounded recommendations and primary API references.
- Private three-view figure: native-axis-projections.png + .svg, visually inspected; diagrams share an origin only for direction comparison, with this convention explicit.
- Bounded evidence verification: native geometry agreement, all paired angles, all ten projections/control mappings, identity visual transforms, uniform native ref/export sign, root proper rotation, zero capture errors and clean unchanged CAD. See verification.json and native_end_state.json. These are PC/native checks, not QC/fake or hardware tests.
- All geometry evidence remains git-ignored scratch. Only this task metadata is committed/pushed; no runtime source, model, URDF, mesh or calibration data was committed.

## Next
1. Parent source owner incorporates command/Home/native-zero wording and retains faithful axes; dedicated hardware owner verifies actual channel/direction/neutral before any mapping change.
2. If a different geometric neutral is desired, agree an explicit native CAD configuration and datum/angle constraints in a separate authorized modelling task; no silent cosmetic correction.
3. No remaining audit work. Keep this completed metadata until parent closure integration; remove task file only in a merging PR per HANDOFF.md.

## Blocked
- None for this completed read-only audit. Physical neutral remains outside its evidence; hardware owner is separately authorized and active.
