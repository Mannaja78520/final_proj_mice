# Patch 0013

- **when:** 2026-07-31 18:04
- **change:** Update (send rig to robot) is no longer 50 blind round trips: read LIMIT? once and send only the lines that differ. An unchanged push is now 1 command instead of 50 (12.8s -> 0.24s measured on the real board); a shoulder-only edit is 8.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 13`
