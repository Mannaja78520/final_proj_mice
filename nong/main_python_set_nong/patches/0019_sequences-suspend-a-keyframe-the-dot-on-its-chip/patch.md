# Patch 0019

- **when:** 2026-08-01 00:05
- **change:** Sequences: suspend a keyframe (the dot on its chip) to skip it while playing, exporting and uploading without deleting it - the move that replaces it is re-timed for the bigger jump and the crash check re-tests that path. New 'then run...' box chains a sequence into another (next: in the YAML), offering the files already on the card. Playback, export and collision checking now all read one play list instead of the raw keyframe array.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 19`
