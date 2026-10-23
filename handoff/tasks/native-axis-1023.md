# Native SolidWorks axes and planes audit

Owner: codex:10231404-5229
Updated: 2026-10-23T14:07:36.117746+07:00
Branch: codex/native-axis-1023
Tree: E:/final_proj/mice/code/.staging-native-axis-1023
Last commit: 45dac39 baseline, metadata only
Plan: robot A48-12

## Goal
Check all 10 native SolidWorks joint axes, left/right mirrors and XY/XZ/YZ planes against exported URDF and Studio servo90/CADzero/Home. Read-only native audit authorized by parent chat 01a16787-933e-7d81-97a1-0a3561d110b9.

## Doing now
Read saved native assembly through COM without any save/export/pose changes. Compare actual analytic geometry and reference frames with private native URDF. Numeric evidence stays ignored in root scratch/native-axis-1023. Parent owns source, QC/fakes, build/restart and deployment.

## Facts found
- model/nong_urdf/solidworks/setup_native.py:24-26,93-96 creates URDF reference frames from earlier STEP-derived joints_review.json; agreement with these refs alone is not independent physical-axis proof.
- Parent private axis-audit.json is the preliminary URDF/Studio measurement, not native mate evidence.
- No active SolidWorks COM object was available on first read; no user CAD document closed or saved.
- Main baseline is dirty and older than parent source; this metadata branch does not change runtime code.

## Done
- Read project handoff, coordination, communication skills and relevant systems headers.
- Claimed only own task/scratch and read-only COM; registered A48-12.

## Next
1. Load canonical native review assembly read-only, compare all ten ref axes and actual analytic cylindrical faces, inspect native component transforms/mates.
2. Separate native pose/export/Studio findings; send bounded evidence and actionable recommendation to parent.
3. Update task and plan, push metadata checkpoints, release own claims.

## Blocked
- Nothing. No hardware calibration claims are possible from this audit.
