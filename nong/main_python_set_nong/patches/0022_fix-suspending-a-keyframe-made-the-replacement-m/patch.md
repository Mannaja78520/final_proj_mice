# Patch 0022

- **when:** 2026-08-03 22:16
- **change:** FIX: suspending a keyframe made the replacement move lunge. playKeys() re-timed the new move with minTime() - the servos' physical floor, ie the fastest the arm can possibly move - instead of the speed that applies. It now uses autoTime at the surviving keyframe's own deg/s (else the sequence speed), and keeps a longer hand-typed time, so suspending can only slow a move down, never speed it up.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 22`
