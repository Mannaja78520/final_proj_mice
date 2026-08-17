# Patch 0009

- **when:** 2026-07-31 13:18
- **change:** Fix pin config over USB in Nong Studio: its own Web Serial reader also skipped any line starting with '[' (ate the PIN VALID array); now skips only log tags. (Hub had the same bug — MiceHub.exe rebuilt; module page error now points at a stale hub, not firmware.)
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 9`
