# Studio Distance: shoulder to elbow and shoulder to hand

Owner: PC session (Remote Control)
Updated: 2026-10-21 04:30 (Bangkok)
Branch: (PC session names it)
Last commit: c859601
Plan: A45-26

## Goal
Add distances shoulder->elbow and shoulder->hand, left and right separately, keeping the existing distances.

## Done
- Checked: distPoint knows only elbow and hand, so a JSON entry alone is not enough; the shoulder point must be added to the calculation. Coordinates, files and pass marks: scratch/studio-shoulder-distances-2026-10-21/HANDOFF.md (PC only).

## Next
1. Add the shoulder point to distPoint, the new entries to the data list (not hard-coded).
2. Regression + sabotage + review + quick/full QC; rebuild web (tools/build_web.py) and exe if needed; check the running app.

## Blocked
- Nothing.
