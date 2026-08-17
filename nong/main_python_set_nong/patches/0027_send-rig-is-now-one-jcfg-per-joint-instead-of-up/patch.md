# Patch 0027

- **when:** 2026-08-04 09:03
- **change:** Send rig is now one JCFG per joint instead of up to five commands each - 50 round trips down to 10, about 1.6s to 0.3s - with an automatic fallback to the individual commands on a board older than JCFG. playKeys() is cached behind a self-validating signature so tick() stops rebuilding it four times a frame; the signature covers exactly the fields the play list reads, so it cannot go stale.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 27`
