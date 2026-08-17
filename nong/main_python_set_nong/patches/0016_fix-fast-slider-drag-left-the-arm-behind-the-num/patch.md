# Patch 0016

- **when:** 2026-07-31 22:01
- **change:** FIX: fast slider drag left the arm behind the numbers. Live sends were fire-and-forget fetches with no ordering, so an older pose could arrive last, and a time throttle dropped the final value when the drag ended inside its window (mouse released off the bar = no commit event). Now ONE command in flight: liveQueue keeps ordered work (playback segments, keyframe 0, STOP) in order, livePending keeps only the NEWEST drag pose. Also fixes a race where segment 1 could overtake the keyframe-0 send at the start of Play.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 16`
