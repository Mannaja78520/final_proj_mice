# Patch 0003

- **when:** 2026-07-24 16:32
- **change:** FIX: model invisible with an old saved rig — mergeRig now migrates 'zero' (and any per-joint array) to length 10; applyPose is NaN-safe; new ?selftest=migrate regression
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 3`
