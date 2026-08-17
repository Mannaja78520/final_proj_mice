# Patch 0012

- **when:** 2026-07-31 16:44
- **change:** Pause now really stops the robot: a segment is handed to the module as one whole move (POSE ... T) and the firmware interpolates it, so pausing the editor used to let the robot run the move to the end. Pause (and scrubbing) sends STOP to freeze it where it is; resuming re-sends the segment with only the time still left.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 12`
