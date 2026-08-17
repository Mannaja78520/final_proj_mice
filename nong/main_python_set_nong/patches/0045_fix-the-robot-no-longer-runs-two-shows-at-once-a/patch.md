# Patch 0045

- **when:** 2026-08-09 01:19
- **change:** Fix: the robot no longer runs two shows at once. A command that MOVES the robot (POSE/JOINT/HOME/STOP/RELAX/ATTACH) now stops the sequence the module was playing on its own clock, so Play in Studio and the board's own sequence cannot overlap; Pause really stops it; and connecting to a module that is already playing says so.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 45`
