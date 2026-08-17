# Patch 0026

- **when:** 2026-08-04 03:28
- **change:** Servo presets now come from the ONE shared table (firmware/config/servos.json) fetched from the hub, with the old literals kept only as an offline fallback - the firmware compiles the same file into a header at build time, so the two sides can no longer drift.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 26`
