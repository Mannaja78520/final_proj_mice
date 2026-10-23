# Native SolidWorks axes and planes audit

Owner: codex:10231404-5229
Updated: 2026-10-23T14:13:46.321152+07:00
Branch: codex/native-axis-1023
Tree: E:/final_proj/mice/code/.staging-native-axis-1023
Last commit: 9ba8e85 (initial metadata checkpoint)
Plan: robot A48-12

## Goal
Check all 10 native SolidWorks joint axes, left/right mirrors and XY/XZ/YZ planes against exported URDF and Studio servo90/CADzero/Home. Read-only native audit authorized by parent chat 01a16787-933e-7d81-97a1-0a3561d110b9.

## Doing now
Analyze captured read-only native geometry: all ten axis lines match actual analytic cylinder geometry at micrometre-scale residual. Inspect saved assembly mates to explain native pose, then compute independent centers/mirrors/XY/XZ/YZ projections and recommendations. No runtime source or CAD edits.

## Facts found
- model/nong_urdf/solidworks/setup_native.py:24-26,93-96 creates URDF reference frames from earlier STEP-derived joints_review.json; agreement with these refs alone is not independent physical-axis proof.
- Parent private axis-audit.json is the preliminary URDF/Studio measurement, not native mate evidence.
- root scratch/native-axis-1023/native_capture.json: native COM read-only true, dirty false before/after; 264 components, 1519 analytic cylinder faces, 11 ref frames, 10 ref axes, zero capture errors. All 10 exported axes independently match intended gear-hub/shaft/bearing cylinder lines. Native saved geometry contains the observed skew; no exporter axis-line defect found.
- open_native.py/capture_native.py call read methods only; initial OpenDoc6 options67, load errors0. Canonical native assembly hash unchanged. COM is held in own Python session63476 to retain access; do not save/close user docs.
- No active SolidWorks COM object was available on first read; no user CAD document closed or saved.
- Main baseline is dirty and older than parent source; this metadata branch does not change runtime code.

## Done
- Read project handoff, coordination, communication skills and relevant systems headers.
- Claimed only own task/scratch and read-only COM; registered A48-12.
- Captured refs, component transforms and analytic geometry independently; no QC/fakes/robot/services used.

## Next
1. Finish native mate audit and independent numeric report; validate provenance, every joint/projection, model bytes unchanged.
2. Separate native pose/export/Studio findings; send bounded evidence and actionable recommendation to parent.
3. Update task and plan, push metadata checkpoints, release own claims.

## Blocked
- Nothing. No hardware calibration claims are possible from this audit.
