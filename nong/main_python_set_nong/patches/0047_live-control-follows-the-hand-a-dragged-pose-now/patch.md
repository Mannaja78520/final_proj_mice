# Patch 0047

- **when:** 2026-08-09 17:34
- **change:** Live control follows the hand: a dragged pose now carries the time it has (measured from the link's own round trip, clamped 80-300ms) instead of letting the module ease at its SPEED setting, which made the arm trail the slider by 166ms per move.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 47`
