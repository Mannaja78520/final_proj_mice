# The hub — `main_python/main.py`

One stdlib-only `ThreadingHTTPServer` on `0.0.0.0:8642`. About 2,000 lines. It is
five programs in one file:

1. a static server for four web UIs,
2. a transport proxy to boards (WiFi HTTP / USB serial / RS485 / hotspot relay),
3. **the single owner of every COM port on the PC**,
4. an esptool + OTA flasher,
5. Nong Studio's file backend.

`nong/main_python_set_nong/main.py` is **not** a second server — it is 13 lines
that `runpy` this one.

## Routes — 40 API endpoints, 13 static branches

| group | paths |
|---|---|
| pages | `/` `/hub` `/mod` `/mice.css` `/module.html` (302 &rarr; `/mod`) `/rgb.html` `/help` `/studio/*` `/models/*` `/hubweb/*` `/app/<id>/*` `/pinout.svg` `/rig_default.js` |
| device proxy | `/api/dev/{cmd,status,files,peers,cam.stream,cam.jpg,download,delete,upload}` — all take `?dev=` |
| discovery | `/api/scan` `/api/ports` `/api/scanusb` `/api/hubs` `/api/servos` `/api/apps` |
| USB | `/api/usb/cmd` `/api/usb/close` |
| flashing | `GET/POST /api/flash` `GET /api/flash/images` `POST /api/ota` |
| show clock | `GET/POST /api/play` `/api/play/stop` |
| Studio files | `/api/list` `/api/load` `/api/loadseq` `/api/save` `/api/export` `/api/model/upload` `/api/rigdefault` |
| settings transfer | `GET/POST /api/settings` `/api/settings/peer` |
| legacy WiFi proxy | `/api/robot/{cmd,status,files,download,delete,upload}` |

There is no `GET /api/ota` — OTA progress is read from `GET /api/flash`.

**No authentication on anything.** A grep for `Authorization|auth|token|password`
returns nothing, and it binds all interfaces. Any device on the LAN can flash a
board or open a COM port.

## Module management vs flashing — separate in code, fused in the UI

Flashing is one contiguous block: constants `:955-962`, `_flash_ports` `:964`,
`flash_env`/`flash_image`/`flash_images`/`esptool_cmd` `:968-1035`, `class
Flasher` `:1038-1231`, routes `:1739-1758`.

Module management is elsewhere: `probe_module` `:231`, `scan_modules` `:273`,
`probe_usb_port` `:1262`, `probe_usb_all` `:1359`, `dev_*` `:635-714`.

They touch in exactly **three** places, all correct coordination over one cable:
`_usb_get` refuses a flashing port (`:394`), `probe_usb_all` skips them
(`:1367`), `Flasher._run` stops the show and closes the handle (`:1173`).

**The fusion is entirely in HTML.** `hub.html:560` appends a flash picker to
every USB port slot; `hub.html:493-501` appends the OTA button to every module
row. Splitting them needs **no server change**. It also removes the reason
`flashActive`/`flashBusy` exist (`hub.html:731`) — the module list rebuilding on
a timer and destroying the row a flash reports into.

## Device addressing

```
dev   := ("wifi:" host | "usb:" port [":" [busid]]) ["@" peer]
busid := 1..247; empty or absent means 0 (direct, not RS485-framed)
peer  := a module NAME or bus id, sent verbatim inside "REACH <peer> <cmd>"
```

Undocumented reality: the `@peer` split happens **before** the scheme check, so
`@` in a port name breaks parsing; `wifi:1.2.3.4:5` keeps the colon and
`robot_get`'s regex accepts it as host:port; extra colons are silently dropped.
`PEER_WAIT = 8.0` replaces the 2 s budget whenever a peer is present.

Only `/api/dev/*` and `POST /api/play` accept a `dev`. `/api/usb/*` and
`/api/robot/*` take `port`/`ip` instead — which is exactly why they are clones.

**Peer capability holes:** `cam.stream`/`cam.jpg` reject any peer or non-wifi
dev; `download`/`delete`/`upload` take the fast HTTP path only when
`kind == "wifi" and not peer`, so a `wifi:<ip>@peer` module falls back to the
slow base64 command loop.

**`hub:<ip>/<inner>`** (added 2026-08-17) forwards the whole HTTP call to another
hub with `X-Mice-Forwarded: 1` as the loop breaker. Genuinely different from
`@peer`: an HTTP hop between PCs versus a `REACH` hop between boards.

## Discovery — six mechanisms

| # | what | scans | cache |
|---|---|---|---|
| 1 | `scan_modules` | `/24` × `/api/status`, 96 threads, then a patient re-probe | 10 s |
| 2 | `scan_hubs` | `/24` × `:8642/api/settings` | 20 s |
| 3 | `serial_ports` | pyserial, else Windows registry, else `/dev/tty*` | none |
| 4 | `probe_usb_port` | opens the port, `INFO`, `#* PING` census, `#<id> INFO` | identity: no TTL; all-ports: 8 s |
| 5 | board peers | delegated to the board (`/api/peers` or `PEERS`) | none |
| 6 | `/api/allmods` | `scan_hubs` then `/api/mine` on each | inherits 2 and 4 |

**#1 and #2 are the same sweep written twice** — `:213-221` and `:296-303` are
line-for-line identical but for the probe function. Two full 254-host sweeps can
run back to back.

**`/api/scan` overlaps `/api/ports`** (it returns `serial_ports()` too), and both
the hub page and Studio call both.

**`hub.html:193-271` re-implements `/api/mine` in the browser** — same job, two
languages.

## Who is server, who is client

* **A phone connects to the hub**, not to a board. Boards are reachable only
  through hub routes (except the explicit "direct" button).
* **The hub connects to boards. Boards never dial the hub.** Nothing in the
  firmware knows port 8642 exists.
* **If the hub dies mid-show:** `ShowPlayer` runs on a daemon thread, so it dies
  with the process and **no `STOP` is sent**. The board finishes its current
  interpolated move and holds that pose forever. There is no shutdown hook.
  Mitigation is architectural: Studio hands a hidden tab's show to the module's
  own clock via `MOVE <file>`, which survives the PC being switched off.
* **If a board dies mid-show:** `_say` raises, `_run` records the error and the
  thread exits. **No retry, no reconnect.** For USB only, `usb_cmd` throws away a
  stale handle and retries once — which is what makes replugging work.

**Takeover:** `check_takeover` (`:921-936`) stops the hub's show when a live
motion command hits the same device. The motion list is read from
`commands.json` — the same registry the firmware compiles from. It is called
from three routes and deliberately **not** inside `dev_cmd`, or the player would
stop itself. Device match is exact-string, so a show started as `wifi:<ip>` is
**not** stopped by a command sent to the same board as `usb:COM7`.

## Serial port ownership

Only `_usb_get` (`:392-423`) ever opens a port. Two lock levels: a global lock
guarding the dict only (held briefly, so a wedged Bluetooth port cannot block
other ports), and one lock per port held across the whole write-then-read.

Five release paths, all via `usb_close`: the 10 s idle reaper, `/api/usb/close`,
stale-handle recovery, flashing, and probe errors.

**Bug (fixed in the 2026-08-17 staging work):** `usb_close` acquired the per-port
lock with a 3 s timeout and closed **whether or not it got it**, while a `@peer`
command is allowed 8 s.

**Three things can reach a port besides the hub:** esptool as a subprocess
(interlocked by `_flash_ports`), the browser's Web Serial in Studio's "USB
direct" mode (**uncoordinated** — the hub only finds out by failing to open), and
any outside program like the Arduino IDE.

## Identity

| field | stable? |
|---|---|
| `id`, `name`, `group` | stable until changed; `name` is not unique |
| `type` | **can flip to `blank`** when the stored type is not in the running binary |
| `ip` | changes; `192.168.4.1` in AP mode |
| `port` | changes on replug |
| `dev` | **not stable** — one board has 2-4 valid devs |

Three concrete problems:

1. **RS485 modules never carry a group.** `probe_usb_port` builds bus entries
   without one (`:1316-1317`), so the Network tab renders *every* RS485 module as
   "not linked" even when grouped.
2. **The Network tab dedupes by `name|type`.** Two boards with the same name
   collapse to one row, and `applyGroup` then writes a permanent group identity
   to only one of them.
3. **The same board is genuinely listed twice** — once from `/api/scan`, once
   from `/api/scanusb` — with different `dev` strings and different caches.

Also: **Studio cannot follow a `@peer` dev.** `hub.html` builds
`usb:COM7@nong2` and Studio parses it as `dev.slice(4).split(":")`, producing the
port `"COM7@nong2"`, which it then tries to open literally.

## Registries — declared once, generated

`firmware/config/{servos,commands,modules}.json` read by `tools/registry.py`;
`apps/*/app.json` is the fourth. `check_registries.py` proves the mechanism by
adding a real app at runtime.

Still hand-maintained in more than one place: the `platformio.ini` env names
(reconstructed by string rule in `flash_env`), `blank` special-cased in Python
with a fallback list that is now wrong (it omits `cam`), the `FLASH_PARTS`
offsets, the README's module table (stale — omits `cam`), and the firmware
log-line regex, which exists once in Python and once in JS with no test tying
them together.

## Duplication worth removing

1. **`/api/robot/*` is a WiFi-only clone of `/api/dev/*`** (`:1888-1935`).
   Studio uses it exclusively and never calls `/api/dev/*` at all.
2. **`/api/usb/cmd` is a cable-only clone of `/api/dev/cmd`**.
3. The `/24` sweep, twice.
4. Multipart bodies built by hand three times (`:694`, `:1099`, `:1925`).
5. SD transfer over serial implemented in Python and again in JS — and they
   **disagree on chunk size** (120 vs 180 bytes).
6. "port held by another program" advice written twice.
7. Two serial line readers; the probe path keeps the old rule that drops anything
   starting with `[`, which was a real bug for JSON arrays.

Keep the URLs when consolidating — Studio and `rgb.html` depend on them. Rewrite
the bodies as thin shims onto the `dev_*` helpers.
