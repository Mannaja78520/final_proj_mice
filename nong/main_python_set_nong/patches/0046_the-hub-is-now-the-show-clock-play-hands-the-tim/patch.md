# Patch 0046

- **when:** 2026-08-09 04:03
- **change:** The hub is now the show clock: Play hands the timeline to the hub (POST /api/play) whenever the link goes through it, so a rehearsal keeps running with the tab hidden or the browser closed; the page only draws, returning to it re-syncs the play head, and the module hand-off is skipped while the hub drives.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 46`
