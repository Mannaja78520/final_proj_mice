# Every app alone, and together (user 2026-11-23)

> *Every app must work fully on its own, with nearly the same functions, because
> someone may open only the face app, or only Voice, with no hub. And when the
> hub or other apps run, they join up: Voice + Reconize greets the person, a game
> + a prize machine gives prizes.*

## The rule

1. **Alone.** `MiceHub.exe --alone <app>` (or `python main_python/main.py --alone <app>`)
   runs ONE app: its own port (`alonePort` in its `app.json`, `--port` moves it), its
   page as the front door, and nothing started that it does not need (no hub hunt,
   no `mice.local` name, no friend programs resumed). It never looks for a hub and
   never needs one. One code base, so a fix is made once; the "hub" is the same
   program with every app switched on.
2. **Together.** Every running Mice program (the full hub or an app alone) writes
   one small file into `<temp>/mice-peers` (`main_python/peers.py`, override with
   `MICE_PEERS_DIR`) and deletes it on exit; a crashed one is dropped when read
   (its port no longer answers). A program finds a neighbour by what it can DO
   (`caps` in `app.json`: `prize`, `speak`, `camera`, ...), never by name or port:
   `GET /api/peers?cap=prize`, or `peers.find("speak")`.
3. **One owner per camera.** `peers.claim_camera(dev, port)` creates one file with
   O_EXCL. First asker owns the webcam; every other Mice program READS the owner's
   `/api/dev/cam.stream?dev=...` through the same ffmpeg link reader
   (`cam_sources._pc_or_peer`). Second opens gave black frames (measured 2026-10).
   The claim is released when the owner exits; a claim whose owner is gone is
   taken over. A friend's app cannot claim (see friend file section G).

## Audit: what each app needs, alone and together (tested against fakes only)

| App | Alone (`--alone`) | What it still needs | Joins up with |
|---|---|---|---|
| Nong Studio `studio` :8651 | 3D editor, saved moves, play to boards over USB/WiFi | boards only to move a real robot | TV remote (`show`), Voice (gestures) |
| Voice `voice` :8652 | page + helper on 8767 started by itself | helper models; a robot only to speak on it | Reconize: `FaceLink` calls their app directly, no hub; speaks through any `speak` neighbour |
| Cameras `camera` :8653 | boards by WiFi/USB, this PC's webcams, added links | ffmpeg for webcams/links | one-owner claim; face watcher reads any `camera` neighbour |
| Prize machines `gacha` :8654 | machines, rules, logs, Sheet, AND the game proxy `/play/all-jao/` (same code) | boards to give a real prize | games: a win from the proxied page reaches the machines; `GET /api/peers?cap=prize` |
| TV remote `tv` :8655 | show control | a show to run | Studio |
| Help `help` :8656 | the offline guide | nothing | all |
| Face watcher (`apps/faces/service.py`) | already its own process | Reconize running; a speaker + camera source | greets through the hub OR any neighbour with `speak` (`peers.where`), reads cameras from the hub OR any `camera` neighbour |
| Reconize, Photobooth, All-Jao Games | friend's programs: start from their own folder, always | - | linked by `config/partners.json`; edits are NEVER made on their side |

## Not done / honest limits

- Two Mice programs on one PC do not share a USB cable: the first to open it owns it
  (hub_usb). Boards by WiFi are shared freely. Alone apps started together that both
  want the same cable: the second says the cable is busy.
- Prize wins are given by the process that serves the game page. Two prize
  processes on one PC read the same `config/gacha.json` and `.local/gacha` files but
  are not merged; use one.
- The hub's Home page does not yet list alone apps (that card list belongs to the
  Tools-page thread); `GET /api/peers` is ready for it.
- Nothing here ran on the real exe, real webcams or real boards.
