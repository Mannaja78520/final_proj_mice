# Patch 0007

- **when:** 2026-07-27 16:42
- **change:** Per-joint servo FRAME RATE (Hz): PDI-1181MG shoulders now driven at 330Hz (was 50) — likely the self-disable cause; RATE command + servo rows Hz column + preset carries rate; module website rate control
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 7`
