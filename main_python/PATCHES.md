# Hub pages patches

Every change to the hub pages is saved here as a numbered patch. Old patches are never removed — each row is a snapshot you can restore with `python save_hub_patch.py --restore <n>`.

| # | when | change |
|---|---|---|
| 0001 | 2026-08-10 16:50 | baseline: the hub pages as they are on 2026-08-10, so future changes have an 'old' to compare against |
| 0002 | 2026-08-18 09:46 | one shared design system: pages link /mice.css instead of each carrying a copy |
| 0003 | 2026-08-18 10:31 | delete module.html; its URL is now a 302 to the module's real website |
| 0004 | 2026-08-19 02:18 | one tab component across the hub, the module site and Studio |
| 0005 | 2026-08-19 03:11 | the hub gets accounts: add and remove people, the way the module already works |
| 0006 | 2026-08-19 04:01 | Firmware gets its own screen: one place writes firmware over a cable or WiFi, unbuilt types are shown with the command that builds them, and a finished write tells the board what it now is |
| 0007 | 2026-08-19 04:44 | Flash from a PC that never built the firmware: the image travels to the hub holding the cable, which writes it; destructive controls carry the shared danger style |
| 0008 | 2026-08-19 08:28 | Open the hub on a phone: a QR of its own address drawn by the hub itself, and mice.local answered over mDNS |
| 0009 | 2026-08-19 09:05 | One board is one row: the hub merges what it finds on a cable and on the WiFi by the board chip id |
| 0010 | 2026-08-19 09:53 | Addresses, cable ports and signal strengths hide behind one switch in Settings; names, types and module numbers always show |
| 0011 | 2026-08-19 10:12 | Help documents the board page saying when something failed |
| 0012 | 2026-08-19 10:26 | Help documents the way back to the hub from a board page |
| 0013 | 2026-08-19 12:59 | Colour themes: one file holds every colour, the picker discovers them, dark stays default |
| 0014 | 2026-08-19 13:37 | The hub finds a module on the RS485 bus however high its id is |
