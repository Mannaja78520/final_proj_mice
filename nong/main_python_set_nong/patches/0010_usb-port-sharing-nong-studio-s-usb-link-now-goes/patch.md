# Patch 0010

- **when:** 2026-07-31 15:00
- **change:** USB port sharing: Nong Studio's USB link now goes through the hub (which owns and shares the cable), so Studio and the module website can be open on the SAME COM port at once instead of 'serial port already in use'. New port picker, old Web Serial kept as 'USB direct (exclusive)', ?dev=usb:COMx auto-connect.
- **files:** app.js, index.html, style.css

Restore this exact version with:  `python save_patch.py --restore 10`
