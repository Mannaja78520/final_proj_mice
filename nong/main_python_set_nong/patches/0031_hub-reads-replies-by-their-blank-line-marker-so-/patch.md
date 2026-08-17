# Patch 0031

- **when:** 2026-08-04 15:27
- **change:** hub reads replies by their blank-line marker, so a log line is never mistaken for one
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 31`
