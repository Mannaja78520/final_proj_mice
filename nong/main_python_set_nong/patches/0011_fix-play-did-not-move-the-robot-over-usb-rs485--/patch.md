# Patch 0011

- **when:** 2026-07-31 15:41
- **change:** FIX: Play did not move the robot over USB/RS485 - the live-follow branch tested robotIp() (the WiFi field), so segments were only ever sent over WiFi. Now any open link counts. Also send keyframe 0 when playback starts: segments are the moves INTO a keyframe, so keyframe 0 was never sent and the robot's first move started from wherever it stood.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 11`
