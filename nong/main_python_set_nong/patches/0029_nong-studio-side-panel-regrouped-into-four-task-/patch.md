# Patch 0029

- **when:** 2026-08-04 11:03
- **change:** Nong Studio side panel regrouped into four task tabs - Pose / Sequence / Robot / Setup - instead of Movement/Setup, which had buried the robot link, SD card and zero calibration under Movement. Cards carry data-stab and showTab shows by attribute, so nothing moved in the DOM: every id, handler and QC driver is untouched. The old 'move' name still works and an unknown name falls back to Pose rather than blanking the panel.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 29`
