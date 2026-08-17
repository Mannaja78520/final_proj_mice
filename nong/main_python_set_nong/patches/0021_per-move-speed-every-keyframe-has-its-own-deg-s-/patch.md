# Patch 0021

- **when:** 2026-08-03 13:48
- **change:** Per-move speed: every keyframe has its own deg/s box (blank = the sequence's speed). Setting it re-times only that move; typing a time clears the override. The exported file emits a speed step before the move and restores the sequence speed after, and parseSeqYaml reads mid-file speed steps back onto the right move so it survives a round trip.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 21`
