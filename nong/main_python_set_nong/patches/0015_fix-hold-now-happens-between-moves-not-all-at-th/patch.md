# Patch 0015

- **when:** 2026-07-31 18:55
- **change:** FIX: hold now happens BETWEEN moves, not all at the end. segmentAt() had no 'in a hold' branch (poseAt does), so the moment a hold began it returned the NEXT segment and the robot was told to move straight away - it finished early and stood still for the rest of the run. Also live drag throttle 180ms -> 70ms now that a command costs ~30ms instead of ~250ms.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 15`
