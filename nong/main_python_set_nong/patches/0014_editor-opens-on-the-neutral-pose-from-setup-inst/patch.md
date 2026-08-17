# Patch 0014

- **when:** 2026-07-31 18:37
- **change:** Editor opens on the Neutral pose from Setup instead of a flat 90 90 90: keyframe 0 (built at boot from the start pose) now matches the robot's own HOME. Uses RIG.neutral, not RIG.zero - zero is the angle at which a joint RENDERS straight, a model calibration, not the pose the robot rests at.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 14`
