# Patch 0030

- **when:** 2026-08-04 14:28
- **change:** Playback no longer dies when the tab is hidden: the show clock is split from rendering (playTick works out its own elapsed time, so rAF and a 60ms interval can both drive it without double-counting) and Studio holds a silent audio track while playing, which keeps most browsers from throttling a background tab. NOTE: liveTimer was already taken by the collision throttle - the new interval is playClock, since a duplicate let is a SyntaxError that kills the whole script.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 30`
