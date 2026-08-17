# Patch 0023

- **when:** 2026-08-03 23:08
- **change:** FIX: Export / Send to robot SD / Run on robot guarded on the edit list, so with every keyframe suspended they wrote a sequence file containing no moves at all and the robot ran a do-nothing file. They now guard on what will actually be written (playKeys) and say which it is.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 23`
