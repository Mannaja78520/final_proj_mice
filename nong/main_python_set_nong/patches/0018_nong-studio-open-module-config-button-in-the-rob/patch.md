# Patch 0018

- **when:** 2026-07-31 23:54
- **change:** Nong Studio: '⚙ Open module config' button in the Robot link card opens the connected module's own website (pins, WiFi, users, servo type, SD files) in a new tab. It follows the same precedence as commands - cable first, WiFi otherwise - and carries the RS485 bus id, so it always configures the board you are posing. Over shared USB both stay open on one cable; direct Web Serial owns the port, so it explains how to switch.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 18`
