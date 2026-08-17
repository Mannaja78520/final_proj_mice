# Patch 0025

- **when:** 2026-08-04 02:53
- **change:** Tuned rig can become the SHIPPED default: new 'Make this the factory default' button posts the live RIG to the hub, which writes rig_default.json into the project. /rig_default.js is loaded before app.js so DEFAULT_RIG is seeded synchronously - a fresh browser and Reset both start on the numbers that match the real robot. Missing or bad file falls back to the built-in constants.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 25`
