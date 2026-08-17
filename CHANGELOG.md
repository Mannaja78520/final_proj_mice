# Changelog

Everything notable that changes in this repository, newest first. Each entry
says what changed, **why**, and what you have to do differently because of it.

Folder-level history also exists in two other places and is not repeated here:
`nong/main_python_set_nong/PATCHES.md` (every Nong Studio web-app snapshot) and
`scient_test/PATCHES.md` (every test-plan snapshot).

---

## 2026-08-09

### Changed — "update over WiFi" now asks which firmware

It used to send whatever the board already was. That is the common case, not
the only one: this is also how a board becomes a different kind of module
without finding a cable. The row now opens a picker of everything this PC has
built, with the board's current type marked and preselected.

Choosing a **different** type warns you, and then the hub finishes the job —
because a board flashed with another type still has the old one in its own
memory and would come back as `blank`, running firmware that does not carry the
module it is told to be. So after the update it waits for the board to answer,
sends `SET TYPE`, and reboots it once more.

### Fixed — the orange and blue lines in the camera picture

They are not noise. They are **corrupted scanlines**: whole rows arriving
wrong, single pixels high, straight across the frame. Sensor noise looks like
grain everywhere; this looks like ruled lines, and it has a cause.

Two of them, both measured by counting rows that differ sharply from *both*
their neighbours:

**The sensor clock was too fast for this board.** Every ESP32-CAM example uses
20 MHz. At VGA that gave ~37 corrupted rows a frame; at **10 MHz, 0 to 4**. The
camera's parallel bus is simply being clocked faster than this board's wiring
carries reliably. It halves the sensor's frame-rate ceiling, which costs
nothing here — the live view is limited by WiFi, not by the sensor.

**And it depends strongly on the frame size.** At 10 MHz, corrupted rows per
frame, five frames each:

| size | corrupted rows |
|---|---|
| qqvga 160×120 | 0.8 |
| **qvga 320×240** | **26.4** |
| vga 640×480 | 12.8 (erratic) |
| **svga 800×600** | **1.6** |

The damage tracks the size, not the clock, which points at the sensor's own
downscaler. So the camera now **starts on SVGA** and enables the OV2640's
built-in corrections (`bpc`, `wpc`, `lenc`, raw gamma), which the driver leaves
off. Result on the bench: **7 of 10 frames with zero corrupted rows**, average
1.5 against 26.

Two things that were tried and did **not** help, so they are not worth trying
again: lowering the radio's transmit power made it *worse* (22.4 rows against
12.4 — a weaker link retransmits more), and SVGA cannot be the *init* size on a
board with no PSRAM. That last one is worth remembering: the frame buffer is
allocated for the init size, and asking for SVGA there fails outright with
`camera init failed 0x105`. The board starts at QVGA and moves the sensor up
afterwards.

**Where it stands, measured in the live view** (25 frames each, streaming):

| size | fps | frames with NO corruption | bad rows per frame |
|---|---|---|---|
| qqvga 160×120 | 12.5 | **80%** | 0.5 of 120 |
| qvga 320×240 | 12.4 | 62% | 2.2 of 240 |
| svga 800×600 | 6.0 | 60% | **1.4 of 600** (0.2% of the picture) |

Not zero, and the rest looks like hardware. Three more software levers were
tried and rejected **with evidence**, so nobody spends an evening on them
again:

* `CAMERA_GRAB_WHEN_EMPTY` (wait for a complete frame instead of taking the
  latest) — the driver refuses it with one frame buffer: `camera init failed
  0x105`.
* Lower WiFi transmit power — made it **worse** (22.4 corrupted rows against
  12.4): a weaker link retransmits more.
* PSRAM, which would give two frame buffers and should fix this properly —
  **re-tested with every later fix in place and it still kills every large HTTP
  response.** The 31 KB module page and the picture both returned nothing,
  instantly. Not worth a third attempt without a different board or a newer
  web server library.

What is left to try is not code: the ESP32-CAM's 3.3 V rail is known to sag
when the radio transmits, so a proper 5 V supply instead of a laptop USB port
is the next thing worth changing.

Also fixed, found while measuring: a live viewer whose connection died without
a clean disconnect **latched the camera forever** — nobody could watch again
until the board rebooted. A stream that has produced nothing for three seconds
is now treated as gone.

### Fixed — the hub made every browser open a new connection for everything

You said all four of these felt 2-3 seconds slow: dragging a slider, pressing
Play, the camera view, and opening a page. One cause sits under all four.

`BaseHTTPRequestHandler` speaks **HTTP/1.0** unless told otherwise, so the hub
closed the socket after every response. A browser therefore opened a **brand
new TCP connection for every single request** — every page asset, every status
poll, every pose a slider sends, every camera frame. My earlier measurements
never showed it, because a Python script opens a fresh connection anyway; a
browser doing dozens of requests per interaction pays that cost on every one.

`protocol_version = "HTTP/1.1"`, measured on this PC:

| | new connection each time | connection reused |
|---|---|---|
| an API call | 12.1 ms | **1.8 ms** |
| a pose sent over USB | 19.2 ms | **10.4 ms** |

On this machine a connection costs ~10 ms. **From a phone or another laptop
across the hotspot it costs far more**, and a page load is dozens of them — so
that is where seconds were going.

This is only safe because every response here carries a `Content-Length`; with
keep-alive, one that does not would leave the browser waiting for an end that
never comes. The single exception is the camera stream, which cannot have a
length and says `Connection: close` for itself.

### Fixed — "it lags" was four separate things, and only one was the network

Every number below was measured on your boards, before and after.

**1. A dragged slider asked for a slow move.** Studio sent `POSE …` with no
time, so the module fell back to its `SPEED` setting: a 20° slider move became
a **166 ms eased move**, and the next update arrived before it finished. The arm
was permanently easing towards where your hand *used to be* — and sending faster
could not fix it, because every command asked for a slow move. A live pose now
carries the time it actually has, measured from the round trip of the traffic
itself (so it self-tunes to USB or WiFi) and clamped to 80–300 ms. The firmware
still floors it per joint, so asking for less than the servos can do is safe.

**2. The firmware's main loop starved its own web server.** `loop()` took the
router mutex on every pass and came straight back for more; the web task needs
that same mutex to answer a command, so it queued behind a loop doing nothing.
A `POSE` over WiFi took ~90 ms while an ICMP ping to the same board took 17 ms.
One `delay(1)` — a yield — fixed it:

| link | before | after |
|---|---|---|
| USB | 30 ms median | **13 ms** |

**3. The radio was dozing.** An ESP32 station defaults to `WIFI_PS_MIN_MODEM`
and only wakes on the access point's beacon. Ping to the board: **73 ms average
with it, 17 ms without**. `WiFi.setSleep(false)` now. It costs power, which for
a mains-powered module bolted to a set is the cheaper side of the trade.

**4. The camera's live view was one HTTP request per picture.** Capturing a
QVGA frame costs the board **~25 ms**; delivering it as its own request cost
~120 ms, because this web server closes the connection after every response
(measured: keep-alive honoured 0 times out of 15). The live view was spending
five times longer opening sockets than taking pictures — and it was doing that
on a **1 second timer**, so it managed 1 fps on hardware capable of 25.

It is now an **MJPEG stream**: many frames down one connection, which a browser
renders natively from an `<img>`.

| live view | fps |
|---|---|
| original, 1 s timer | 1.0 |
| chained single frames | 7.3 |
| **MJPEG stream** | **18.7 direct, 22.2 through the hub** |

`GET /api/cam.stream`, with `/api/dev/cam.stream` on the hub piping it through
for a module opened from there. **One viewer at a time** — the board has four
connections in total and a viewer holds one for as long as the picture is on
screen, so a second is refused rather than locking everyone out of the website.
Unticking *live view* drops the connection.

What did **not** turn out to be a cause, in case it is ever suspected again:
Nong Studio's 3D renders at a **solid 60 fps** (19 meshes, 20 draw calls, 5,140
triangles), and HTTP connection pooling in the hub was written, measured and
**removed** — the board closes every connection, so it gained nothing.

What is left on WiFi is a ~49 ms floor per command: the board closes each
connection, so every command pays a TCP open and close. Over USB a command is
13 ms. For editing, use the cable; WiFi is for the show.

`check_latency.py` guards all four, and was proven by breaking each one. The
first version of it passed against a loop with the yield deleted — it was
matching the word `delay(1)` inside the comment that explains it.

### Fixed — the camera card said "is the ribbon cable seated?" about a working camera

Opening the camera module **from the hub** and pressing *Take a picture* gave
`no picture — is the ribbon cable seated?` — while the same board handed out
perfectly good JPEGs to anything that asked it directly.

The hub serves the module's own page for a board it reaches over WiFi or a
cable, and re-addresses every `/api/*` call by patching `window.fetch`. An
`<img src="/api/cam.jpg">` never goes through `fetch`, so it asked **the hub**
for a frame, got a 404, and the card reported the one cause it knew about.

- The page now **fetches** the frame and shows it as a blob, so it follows
  whatever transport the page was opened with — and it prints the module's own
  refusal instead of guessing at the ribbon cable.
- The hub gained `/api/dev/cam.jpg?dev=`, which fetches the frame from the board
  over WiFi and **refuses with 501 over a cable**: a JPEG cannot travel on a
  one-line command channel, and saying so beats a mystery.

Verified on the board through both paths: `200` and a real 320×240 JPEG through
the hub, `501` with "open this module over WiFi to see the camera" over USB.

### Fixed — the camera works over WiFi, and OTA is proven

Second bench session, with the PC hotspot up. Both boards joined it
(`192.168.137.14` nong, `.86` camera) and the last two unproven things were
run for real.

**OTA works.** The camera board was updated **over WiFi** twice — 0→100%, "restarting
the board", back online in about 5 seconds, running the new firmware. No cable
touched. That is the whole feature, end to end, on hardware.

**And a real picture came out of it** — 320×240 JPEGs, valid `ffd8`…`ffd9`,
2.9 KB and 4.6 KB, fetched from `http://192.168.137.86/api/cam.jpg`.

Getting there took two more real faults:

**5. Sending the driver's frame buffer truncated the picture.** `/api/cam.jpg`
answered `200` with **353 bytes of a 13,000-byte frame**: the response was still
queued when the frame went back to the driver, which promptly refilled it. The
route now makes a small private copy, returns the frame immediately, and frees
the copy when the send ends. (`beginChunkedResponse` was tried in between and
panicked the board — that fork underflows its buffer size when the TCP window is
small and asks the allocator for ~4 GB.)

**6. PSRAM is now OFF on the camera build.** With `BOARD_HAS_PSRAM` set, **any**
large HTTP response killed that board — `GET /`, the 31 KB module page, died
exactly like the picture did, while the identical firmware core serves that page
happily on a board without PSRAM. So it is not the camera and not the page: it
is PSRAM plus this async server on this board. Disabling it costs frame size
(QVGA/VGA instead of SVGA and up, one frame buffer instead of two) and buys a
camera module whose website actually works. The reason is written where the flag
is, and QC fails if the flag loses its explanation.

Worth noting for anyone who reads the earlier entry: fault **3** (the SD driver
claiming the camera's data pins) was also what made PSRAM report **0 bytes free**
to the heap. With that fixed the board reports the full `4,000,091 bytes` — the
"malloc panics" symptom moved, it did not vanish, and only turning PSRAM off
settled it.

### Fixed — four things only a real board could show

All of steps 1-5 were built and checked without hardware. Then they were run on
the bench — three boards, flashed and driven — and four faults appeared that no
amount of PC-side checking would have found. Each one now has a check.

**1. `blank` fell out of the module table.** The generator wrote
`#endif    "blank",` on one line, so `"blank"` sat after a preprocessor
directive and the compiler discarded it. The source looked perfectly correct.
On the board: `types:["nong"]` and `SET TYPE blank` refused. Now
`types:["nong","blank"]`, and QC fails on any token following an `#endif`.

**2. Preemption stopped a show for a command the module could not run.** A
binary can carry a type the board is not currently set to — flash the nong
firmware, leave the board on `blank` — and then `POSE` is a motion command that
nothing can execute. The sequence stopped anyway and nothing replaced it. The
sequence is now stopped **after** the command, and only when the module took it.

**3. The SD card was mounted on the camera's data pins.** The shared SPI
defaults (5, 18, 19, 23) are the ESP32-CAM's Y2/Y3/Y4/HREF. `SDStore::begin()`
claimed them, failed to mount, and kept the bus. `SDStore` now refuses a pin
set to `-1` **before** touching SPI, and a cam board declares it has no SPI
card.

**4. The camera module must never copy a frame.** On the real ESP32-CAM a plain
`malloc(16 KB)` **panics inside the allocator** — `psramFound()` is true, the
camera happily allocates its buffers in PSRAM, and yet 0 bytes of that PSRAM
ever reached the heap. Captures were always fine; the copy was the only thing
that crashed. Frames now go straight from the driver's buffer to the response
and are handed back when the send finishes. Fewer copies, less RAM, and it
works on a board whose heap cannot be trusted. It also says so at boot.

Measured on the bench, all three boards flashed from the hub's own button:

| board | flashed as | result |
|---|---|---|
| COM9 | `nong` | `PONG 85 lift-test nong`, `types:["nong","blank"]`, `SET TYPE lift` → `ERR unknown type (nong,blank)` |
| COM16 | `lift` | `types:["lift","blank"]`, `STAGE?` → `-1`, `RGB` ok |
| COM17 | `cam` | camera up on the first try; SVGA 13,037 → VGA 7,474 → QVGA 3,847 bytes |

Also proven on the real nong board: `MOVE` plays a sequence, `SPEED 90` leaves
it running, `POSE` stops it with `(sequence stopped)` — and the hub clock drove
the board through a three-keyframe show at the right times.

Still not proven on hardware: **OTA**. The PC's hotspot was not on air during
the session (no `192.168.137.x`, hosted network `Not available`), so no board
could join a network to be updated over it.

### Added — a camera module, and module types became a registry

Third module type: **`cam`**, an AI-Thinker ESP32-CAM. Same firmware core as
everything else — identity, WiFi, RS485, SD card, sequences, OTA — with stills
and a live view on its Control card.

| build | flash | note |
|---|---|---|
| `mice_cam` | 68.0% | its own board (`esp32cam`, PSRAM) |
| `mice_nong` | 65.9% | unchanged by the camera existing |
| `mice_lift` | 72.8% | unchanged by the camera existing |

That last column is the point. The camera costs the other modules **nothing**,
because since the split each board carries only its own type — and the camera
cannot even share their binary: it is a different board.

**It can never also drive a servo.** The camera takes GPIO 0, 5, 18, 19, 21-23,
25-27, 32, 34-36, 39 and the on-board SD card takes 2, 4, 12-15. Nothing is
left for PWM, which is exactly why it is a type of its own rather than an option
on another one. Its pins are therefore **fixed in the firmware, not on the pin
page**: they are etched onto the board, so "changing" one could only break it.

- `SNAP` takes a picture; `SNAP <name>` saves it to `/photos` on the card.
  `CAM` reports and sets size, quality, flash LED, flip and mirror.
- The picture itself is `GET /api/cam.jpg` — a JPEG cannot travel as a one-line
  reply, which is what RS485 and serial are. One frame per request, deliberately:
  an MJPEG stream would hold one of the board's four connections open for as
  long as anyone watched it.
- Without PSRAM the driver falls back to one small frame buffer, so sizes above
  SVGA are **refused up front** instead of failing at capture time. `CAM` reports
  `psram=0` so a broken PSRAM chip is visible rather than mysterious.

**Module types are now a registry.** `firmware/config/modules.json` declares
what a board can be, and the rest is generated from it: the build guards
(`BuildTypes.h`), the factory (`ModuleTable.h`), which web cards survive, which
commands exist, and the list of types the hub offers to flash. Adding a type is
that one entry, the class in `src/modules/<type>/`, and an env in
`platformio.ini` — `ModuleFactory.cpp` is no longer a list anyone edits.

QC gained `check_camera.py`, which follows that chain from the one file outwards
rather than trusting it, and `check_build_split.py` now builds the camera too.

### Added — update a module over WiFi (OTA)

A module on the network now has **⚡ update over WiFi** in its hub row. The hub
sends this PC's firmware for that module's type, the board writes it and reboots
into it. No cable, no reaching behind the set.

**The blocker in the plan did not exist.** It said OTA had to wait for smaller
binaries because `min_spiffs.csv` gives one app partition. It gives **two** —
`app0` and `app1`, 1.875 MB each — and always has. So OTA was available the
whole time, and today's builds sit at 66% (nong) and 73% (lift) of a slot.

That second slot is also the safety: an update is written to the slot that is
**not running**, and only becomes the boot choice once it is complete and valid.
A dropped WiFi link, a PC that walks away, a bad image — the board keeps booting
the firmware it already had. There is no state in which it has half of each.

- Firmware: `POST /api/ota` (multipart, one `firmware.bin`) using the ESP32's
  own `Update`, then a reboot. **Refused while the module is moving or a
  sequence is playing** — a flash write stalls the servo loop, and a reboot
  mid-show is worse than an update that waited. `?force=1` overrides.
- New `OTA` command reports where an update would go and whether it fits:
  `OTA running=app0 size=1294617 target=app1 room=1966080 free=671463`.
- Hub: `POST /api/ota?ip=&type=`, sharing the one flashing job with USB
  flashing — the hub will not flash two boards, or one board two ways, at once.
- Only the app image travels. The bootloader and partition table — the parts
  that could actually brick a board — are never touched over the air.
- Costs 6 KB of flash (nong 65.5% → 65.8%).

**The first update still arrives by cable**: a board running older firmware has
no `/api/ota` to receive one. Flash each board once over USB; everything after
that can be over the air.

QC gained `check_ota.py`, proven by truncating the upload — the byte-for-byte
assertion failed, which is exactly the failure that would matter.

### Added — the hub flashes a board over its own cable

Every port in the hub's USB list now has **⚡ flash … as**: pick `nong`, `lift`
or `blank`, confirm, and the board is flashed. No PlatformIO, no command line,
and it works on a port where **nothing answered** — which is exactly the board
you need to flash.

This is what the per-type build was for. "Flash this board as a nong" only
became a real instruction once each type had its own binary.

**The cable is the whole problem, and it is handled.** The hub owns every COM
port and shares it between its pages; esptool cannot share. For the length of
the flash the hub gives that port up completely — it stops a show it was
playing on it, closes the handle, and refuses to reopen it until esptool is
done. Every `port is busy` failure on the bench was that.

- `GET /api/flash/images`, `POST /api/flash?port=&type=`, `GET /api/flash`.
- Images come from `firmware/.pio/build/mice_<type>/`, so the firmware must have
  been built once on this PC. If it has not, the page **says so and names the
  command** rather than offering a button that cannot work.
- esptool is not a new dependency: PlatformIO already ships one, and the hub
  stays stdlib-only by shelling out to it. `MICE_ESPTOOL` overrides the command.
- A board that does not answer is reported as a failure, in words that say what
  to do (hold BOOT/IO0, check the cable), not swallowed.
- The board keeps its id, name, WiFi and pins — those live in its NVS, not in
  the firmware.

Not bundled into `MiceHub.exe` yet: on a PC with no PlatformIO, esptool would
have to be vendored. The hub says so plainly instead of failing at the button.

QC gained `check_flash.py`, proven by removing the cable guard and watching the
"nothing else may open it" assertion fail.

### Added — the hub keeps the show running when you look away

Playback froze whenever the Nong Studio tab was not in front. That is not a bug
that can be fixed in the page: a hidden tab has `requestAnimationFrame` stopped
and its timers throttled to roughly once a minute, by browser policy. Handing
the whole sequence to the **module** already covered a show — but not editing,
because nothing has been uploaded yet, and that is exactly when you keep
clicking away.

The missing clock was the **hub**: a native process that already owns the
serial ports and that nothing throttles.

| clock | survives | for |
|---|---|---|
| the module (`MOVE <file>`) | the PC switched off | the show |
| **the hub** (new) | the browser closed | editing / rehearsal |
| the browser | nothing | preview |

Press Play on a link that goes through the hub — USB (shared) or WiFi — and the
hub sends the moves while the page only draws them. Hide the tab, minimise the
window: the robot keeps going. What goes down the wire is unchanged
(`POSE … T <ms>`, one whole move at a time, interpolated by the module), so the
motion is identical to a module-played show rather than merely similar. The hub
only decides *when* each move starts.

- New: `POST /api/play`, `GET /api/play`, `POST /api/play/stop`.
- **Still one clock at a time.** The hub sends `MOVE STOP` before it starts, and
  a live motion command aimed at the same device stops the hub's playback —
  read from the same `"motion": true` list the firmware compiles, so the hub and
  the board cannot disagree about what counts as taking over. Settings
  (`SPEED`, `LIMIT`, `SERVO`) still do not interrupt a running show.
- Coming back to the page **re-syncs the play head** to where the robot really
  is. Before, the preview would have sat behind the arm for the rest of the run.
- Studio no longer also hands the show to the module when the hub is driving —
  that would have been two clocks again.
- **USB direct (Web Serial) is unchanged**: the browser holds that port itself,
  so the hub cannot reach the robot; the show is still handed to the module when
  you leave the page.

QC gained `check_hub_clock.py`, proven by making the hub send the whole show at
once and by removing the takeover check — the timing and one-clock assertions
failed, as they must.

### Fixed — the robot ran two shows at once

Press **Play** in Nong Studio while the module was playing a sequence of its
own and both drove the same servos: the module fired the next keyframe on its
clock while Studio sent poses on its own, and the moves ran over each other.
Worse, **Pause** stopped only the browser — the module kept going, because
`STOP` froze the current move and the player immediately started the next one.

The board now decides, because the board is where every channel meets:

> **A command that MOVES the robot stops the sequence the board is playing.**

```
> MOVE wave.yaml
OK playing /moves/wave.yaml
> POSE 90 90 90 90 90 90 90 90 90 90 T 500
OK pose T=500ms (sequence stopped)
```

Whoever moved the robot last owns it, and the reply says so on the same line —
silence is how an app loses track of what the board is doing.

- **Which commands count is declared once**, in `config/commands.json`
  (`"motion": true`), and compiled into the same table `HELP` reads. A new
  moving command cannot be added and forgotten.
- **Settings are not motion on purpose:** `SPEED`, `LIMIT`, `SERVO`, `RANGE`,
  `CFG` and every query leave a running show alone, so a sequence can be tuned
  while it plays.
- The player's own steps go through `CommandRouter::handleFromSequence()`, so a
  sequence cannot stop itself on its first pose.
- On a two-board humanoid the leader's forwarded poses arrive at the follower
  as ordinary commands, so the follower drops its own sequence and follows —
  which is what "leader" means.
- Nong Studio still stops the module explicitly when you press Play (it is what
  makes the show start from keyframe 0, and it keeps working with older
  firmware), and it now **says** when the module it just connected to is
  already playing something.

This fixes it wherever it came from — a slider drag, the module's own website,
a script — not only the Play button. **Needs a firmware flash.**

QC gained `check_one_player.py`, proven by unmarking `POSE` as a motion command
and watching the overlap come back.

### Changed — one firmware binary per module type

A board runs one module type. Until now every board carried **all** of them: a
nong flashed the lift's motor code, its RGB strip, its MP3 support and its web
cards; a lift flashed the nong's servo code and joint sliders. Measured
2026-08-07: **74.9%** of flash used on every board (1,472,545 of 1,966,080
bytes) and the same 43.9 KB page served by every module — with three more
module types and a camera still to come.

The type is now chosen at **build** time:

```
pio run -e mice_nong             the humanoid
pio run -e mice_lift             the lift
pio run -e mice_blank            core only — a board that is not a module yet
pio run -e mice_module_firmware  every type in one binary (legacy, kept for now)
```

| build | flash | bytes | page it serves |
|---|---|---|---|
| all types (`mice_module_firmware`) | 75.0% | 1,473,861 | 43.1 KB |
| `mice_nong` | **65.5%** | 1,287,349 | 38.5 KB |
| `mice_lift` | **72.5%** | 1,424,849 | 31.9 KB |
| `mice_blank` (core only) | 62.5% | 1,228,481 | 27.2 KB |

Read the last row first: **62.5% is the floor** — WiFi, the web server, the SD
card and YAML, before any module type exists. The nong module itself is only
~58 KB on top of it; the lift is ~196 KB, because it owns the two heavy
libraries (FastLED and the MP3 decoder). So the humanoid saves 182 KB by not
being a lift, while the lift saves 48 KB by not being a humanoid — the split
helps every board, but it is the *core* that dominates the chip, not the
modules. Worth knowing before OTA (flashing over WiFi) is designed: the plan
assumed each binary would land well under 1 MB, and none of them do.

It also closes a safety hole. Only a runtime capability check kept the wrong
controls off the screen, and that check has already broken once — `isNong` was
used and never defined, which made the *right* controls vanish. The mirror of
that bug shows the *wrong* ones, on a board where the joint sliders drive
nothing. Now the other type's markup is **absent from the binary**, so no
script bug can show it.

**The source is still shared.** One marker says which type something belongs
to, and the build takes only its own:

| what | how it is marked |
|---|---|
| C++ — module class, pin entries, includes | `#if MICE_HAS_NONG` (`src/core/BuildTypes.h`) |
| web cards and their script | `<!--#type nong-->` … `<!--#end-->` in `src/web/WebUI.h` |
| commands | `"scope": "nong"` in `config/commands.json` |

`src/web/WebUI.h` is now the **master** page and is not compiled.
`firmware/tools/gen_tables.py` — the generator that already made the command
and servo tables — also writes this env's page, into
`.pio/build/<env>/generated/`. Per env, because two envs would otherwise
overwrite each other's tables; that is why those headers are no longer in
`src/`. The hub still reads and serves the master whole, since a module on a
USB cable does not say what it is until it answers.

Smaller consequences worth knowing:

- The **Hardware pins** card offers only this board's pins. A nong was being
  offered motor, encoder, limit-switch and I2S pins it does not have.
- `SET TYPE` only accepts a type this binary can boot: on a nong build,
  `SET TYPE lift` answers `ERR unknown type (nong,blank)` rather than booting a
  module that is not there.
- `HELP` lists only commands that have a handler in this binary.
- The ArduinoJson include path in `platformio.ini` named one env's `libdeps`
  folder and would have been wrong for every other env; the generator now adds
  it for whichever env is building.

**Needs a firmware flash**, and the env name in your own scripts changes.
QC gained `check_build_split.py`, which builds each type and searches the
**binary** for the other type's markup — `id="jointRows"` in a lift image is a
failure no matter what the page says at runtime.

---

## 2026-07-31

### Fixed — suspending a keyframe made the next move lunge

Suspend the middle of 1‑2‑3 and the arm shot to keyframe 3 at full speed.

The replacement move 1→3 covers more ground than the 2→3 move its stored time
was written for, so it has to be re-timed — but it was re-timed with
`minTime()`, the **physical floor**: the fastest the servos can possibly move.
That is a safety limit, not a pace.

It is now re-timed with `autoTime()` at the **speed that applies** — the
surviving keyframe's own °/s if it has one, otherwise the sequence speed — so
the arm covers the extra distance at the pace you asked for. A hand-typed time
is kept when it is already longer, so **suspending can only ever slow a move
down, never speed one up**.

Which keyframe's speed wins: the **surviving** one. A keyframe's °/s is the
speed of the move *into* it, so the destination owns the move — set a slow °/s
on keyframe 3 and the 1→3 move runs at it.

### Fixed — calibration survives a power cycle without an SD card

Sending limits + gear from Nong Studio had to be redone after every unplug on a
board with **no SD card**. It was saving — but only to `/data/nong_cal.yaml`,
and `saveCal()` gave up immediately when there was no card to write to, so the
board came back on the compile-time defaults every time.

Calibration is now saved **twice**:

| where | when | why |
|---|---|---|
| the chip's own memory (NVS) | always | a board with no card keeps its tuning |
| `/data/nong_cal.yaml` | only with a card | a readable copy to inspect, back up or move to another board |

At boot the card file is applied first and the chip copy second, so the chip
copy wins — it is written by every calibration command whether or not a card is
present, and can never be older than the file.

New `CAL` reports which copies exist, and `CAL CLEAR` forgets both. That
matters more than it sounds: the usual way to undo a bad calibration was to
delete the file from the card, which is impossible on a board that has none.

A stored blob from a different firmware is rejected by magic and version rather
than half-applied, and everything loaded is re-clamped — a corrupt blob must
not be able to drive the servos into the mechanism.

**Needs a firmware flash.**

### Changed — speed belongs to the sequence, not to the editor

**Show speed** (°/s) was an editor setting, so re-opening a sequence ran it at
whatever speed you happened to have set. It is now written into the sequence
file as its first step and restored when you re-edit it, so each sequence keeps
its own pace:

```yaml
steps:
  - speed: 150       # deg/s for THIS sequence
  - pose: "…"
```

Because each file sets its speed at the start, **a chain hands over cleanly** —
a fast sequence following a slow one runs at its own speed instead of
inheriting whatever the previous file left the module on.

The firmware already understood a `speed` step, so this is web-only. The editor
now reads that step back rather than counting it as an unsupported step.

### Added — speed per move as well

Every keyframe now has its own **°/s** box. Leave it blank and the move runs at
the sequence's speed; set it and that one gesture is slower or snappier, with
its time recalculated and its neighbours untouched.

Speed and time are two views of the same thing, so the last one you touch wins:
set a speed and the time follows, type a time and the override is dropped.

The exported file sets that speed before the move and puts the sequence speed
back after it, so the file reads exactly as the timeline runs:

```yaml
  - speed: 120
  - pose: "… T 900"
  - speed: 30        # this one gesture is slow
  - pose: "… T 3200"
  - speed: 120       # back to the sequence speed
  - pose: "… T 900"
```

The editor reads those mid-file steps back onto the right move, so a per-move
speed survives a round trip. Web-only — the firmware already accepted a `speed`
step anywhere in a sequence.

### Added — suspend a keyframe instead of deleting it

The ● button on a keyframe chip **suspends** it. It stays in the timeline where
you can still edit it, but is skipped when playing, exporting and uploading —
for trying a sequence without one move while you check something else.

Skipping the middle of 1‑2‑3 creates a **new** move 1→3 that is longer than the
one 2→3 was timed for, so its duration is raised to what the servos can really
do, and the crash check re-tests that new path. The suspended pose never
reaches the robot or the exported file.

Internally, playback, export and collision checking now all read one **play
list** rather than the raw keyframe array — anywhere still reading the raw list
would show one thing in the editor and do another on the robot.

### Added — chain one sequence into the next

A sequence can now start another when it ends:

```yaml
name: intro
next: wave.yaml      # when intro finishes, wave.yaml starts by itself
```

So a show is built from short files that can each be run and edited on their
own, instead of one long one. In Studio it is the **then run…** box beside the
sequence name, which offers the sequences already on the card.

It applies only when a sequence actually **ends** — `loop: true` never does, so
loop wins. Chains stop after 16 files, so a file pointing back at itself cannot
run forever, and `MOVE STOP` ends the whole chain.

**Needs a firmware flash** (`SequencePlayer`). Everything else in this entry is
web-only.

### Added — open the module's config straight from Nong Studio

**⚙ Open module config** in Studio's Robot link card opens the connected
board's own website in a new tab — hardware pins, WiFi, users, servo type, SD
files — so tuning the robot and configuring it no longer means going back to
the hub to work out which board you were on.

It targets the board Studio is actually talking to, following the same
precedence as every command: the cable when one is open, WiFi otherwise. An
RS485 bus id is carried through, so it opens the board *behind* the cable
rather than the one the cable is plugged into.

Over shared USB the module site and the editor stay open together on the one
cable. In direct Web Serial mode the browser owns the port exclusively, so the
button explains how to switch instead of opening a page that cannot talk.

### Added — Features &amp; help, offline, on the hub's main page

A complete feature reference for the whole system, served by the hub at
**`/help`** and linked from **Tools** on the main page. It runs from the PC, so
it needs no internet and no account. Searchable — the filter at the top hides
everything that doesn't match — and grouped by *where each feature runs*:
firmware core, lift, nong, module website, hub, Nong Studio, QC, plus the
transports, the full command language and every file format.

**It cannot go stale.** The `docs` QC check fails when a command in
COMMANDS.md, a module type, a servo preset or a QC area exists that the page
does not describe. It caught two omissions the first time it ran.

### Added — every web app works on any screen

The hub, the module website, Nong Studio and the help page previously had a
viewport tag and **no media queries at all**, so a phone got a desktop layout
scrolled sideways.

All four now lay out for phone, tablet and large screen, with bigger targets on
touch devices. The significant one is Studio: below 860px the 3D view stacks
*above* the side panel at a usable height instead of both being squeezed into a
split that fits neither, and the joint and rig rows get narrower grid tracks
rather than overflowing. Above 1600px the side panel widens, since the rig
table has six columns.

Guarded by the `responsive` QC check, which loads each page in a real browser
at 360, 390, 768, 1024 and 1920px and fails if the page scrolls sideways —
naming the widest element so it can be fixed. It found a real overflow on the
help page on its first run.

### Added — `qc/`, a QC suite that re-checks the whole system

```
python qc/run_qc.py --quick    no browser, ~3 s — while working
python qc/run_qc.py            everything, ~1 min — before calling it done
python qc/run_qc.py --list     what is covered
```

100 assertions over the USB cable, the firmware↔Studio contract, the hub's
pages and API, and Nong Studio's boot / live / playback behaviour — every one
of them a bug that actually shipped. Stdlib only, plus the installed Edge.

**It extends itself.** The runner discovers `checks/check_*.py`, so covering a
new part of the project is one new file — no registry to keep in sync. The rule
that makes a check worth having is in `qc/README.md`: *break the fix and watch
the check fail*. The live-drag check below passed against the very bug it was
written for until it reproduced the real user action.

### Fixed — a fast slider drag left the arm behind the numbers

Drag a slider quickly and release with the pointer off the bar: the number
showed where you let go, the arm stopped somewhere earlier.

Two causes, both in how live poses were sent. They went out as fire-and-forget
fetches with **no ordering**, so during a burst an older pose could be served
last and win. And the time throttle **dropped** the final update when the drag
ended inside its window — with no commit event to save it, the value you
released at was never sent at all.

Live traffic now shares one channel with a single command in flight: an ordered
queue for work that must all arrive (playback segments, the keyframe-0 send,
`STOP`) and a single-slot pending pose for drags, which is superseded rather
than queued. So the newest pose always wins, the last one always lands, and it
paces itself to the link instead of to a fixed interval.

The same change fixes a race at the start of Play, where segment 1 could
overtake the keyframe-0 pose and start the arm from the wrong place — caught by
the new QC suite, not by hand.

### Fixed — a keyframe's *hold* now happens between the moves, not at the end

`hold` was ignored on the robot. `poseAt()` sits still during a hold, but
`segmentAt()` had no matching "in a hold" branch — so the instant a hold began
it fell through and returned the **next** segment, and the arm was told to
start moving right away. Every move therefore ran back-to-back, the robot
arrived early, and all the waiting appeared as one long pause at the **end** of
the run.

`segmentAt()` and `segRemaining()` now mirror `poseAt()`'s phases exactly: hold
on keyframe 0, move into 1, hold on 1, move into 2 … A hold sends nothing,
which is right — the firmware already holds its last pose.

Measured on the wire with 1000 ms moves and 1200 ms holds: moves now leave at
0, 2198 and 4401 ms — gaps of ~2200 ms. They used to leave ~1000 ms apart.

### Changed — live control is ~8x faster (250 ms → 32 ms per command)

Every command through the hub cost ~250 ms, which is why live and monitor mode
felt like stepping rather than following. The cause was one line: the hub read
replies with `ser.read(256)`, and pyserial waits for **256 bytes or the port
timeout** — a reply like `OK POSE` is 8 bytes, so it always waited the full
150 ms. It now reads the first byte and drains whatever arrived with it.

Measured on a real board: **31.9 ms** per 10-joint `POSE`, ~31 poses/s. Nong
Studio's live drag throttle drops from 180 ms to 70 ms to match.

Live mode is still **one command per segment** with a duration `T`, interpolated
on the module — not per-frame streaming. That is deliberate: it survives link
latency and keeps linked boards in sync. But the arm now starts moving within
about a frame of the editor instead of a quarter second later.

### Changed — the editor opens on your Neutral pose, not a flat 90

Nong Studio always started at `90 90 90 …` and built keyframe 0 from it, so
every new sequence began from a pose the arm may not even rest at — you had to
press **Neutral pose** by hand before doing anything.

It now starts on the **Neutral pose** from Setup (the one behind the *Neutral
pose* / *Set neutral = current* buttons, matching the robot's own `HOME`), and
keyframe 0 with it. If your neutral is still 90 everywhere, nothing changes.

This is `neutral`, **not** the per-joint `zero°` in the rig table — `zero°` is
the angle at which a joint *renders* straight (a model calibration used by
`applyPose`), while `neutral` is the pose the robot rests at. They stay
separate settings.

### Fixed — a replugged board no longer kills the module page and Studio

Unplug the ESP32 (or let it reset) while a page is open and **everything over
that cable died until the hub was restarted** — the module website showed
nothing and Nong Studio could not connect, both with
`WriteFile failed (PermissionError(13, 'The device does not recognize the
command.'))`.

Windows leaves the handle looking open after the device re-enumerates, so
pyserial still reports `is_open` and the hub kept writing to a dead handle. The
idle reaper would have dropped it, except a page polling every ~900 ms keeps
refreshing the port's "last used" time, so it never went idle.

`usb_cmd` now recognises the stale handle, throws it away and reopens once —
which is all a replug actually needs. A command that simply gets no answer is
*not* retried, so a missing module still fails fast.

### Fixed — ❚❚ Pause now really stops the robot

Pausing stopped the editor but not the arm: it finished the move it was in and
only then stood still. That is because a segment is handed to the module as
**one whole move** (`POSE … T 1500`) which the firmware interpolates on its own
— that is what keeps the motion smooth and linked boards in step, but it also
means the module is already carrying out the move when you press Pause.

Pause (and dragging the scrub bar) now sends **`STOP`**, the firmware command
that freezes the arm at the pose it has reached. Resuming re-sends the segment
with only the **time still left** in it, so the arm and the 3D preview stay
together instead of the robot replaying the whole segment.

### Fixed — ▶ Play now moves the robot over USB, and starts at keyframe 0

Two separate reasons the robot did not follow the timeline:

1. **Play only ever worked over WiFi.** The live-follow branch in the animation
   loop tested `robotIp()` — the WiFi address field — so with the cable
   connected it was empty and **not one pose was sent**. Dragging a slider
   worked (that path asks *"is any link open?"*), which made the failure look
   random. It now tests `haveUsb() || haveWifi()` like everything else.
2. **Keyframe 0 was never sent.** A segment is the move *into* a keyframe, so
   the loop starts at segment 1 and the robot's first move ran from wherever it
   happened to be standing straight to keyframe 1. Pressing Play from the start
   of the timeline now puts the robot on keyframe 0 first. A loop restart
   re-sends the first segment too.

Reminder: Play drives the robot only with **live** ticked — that is by design,
`live` is what says "the robot follows the editor".

### Fixed — one USB cable, as many pages as you like

Plugging a module in and opening **both** its module website and Nong Studio
failed: whichever opened second said the **serial port was already in use**.
That is Windows being correct — a COM port belongs to **one program at a
time** — and there were two programs fighting for it: the hub (pyserial, for
`/mod?dev=usb:COM7`) and the browser itself (Web Serial, for Studio's USB
transport).

The hub is now the **single owner** of every cable. It opens the port once and
shares it, running each command under that port's lock so replies can never
interleave. Studio's USB link goes through it (`/api/usb/cmd`), so the module
site, Studio and the hub's own port probe all drive the same cable at once.

- Studio's Robot link card has **+ USB / RS485 (shared)** — pick the port from
  a list (⟳ rescans), no browser permission prompt, and it works from a phone
  or another laptop, where Web Serial does not exist. It is the new default.
- The old exclusive mode is kept as **+ USB direct (Web Serial, exclusive)**
  for when you deliberately want one page alone on the cable.
- The hub's **Studio + monitor** button now appears for USB-connected nong
  modules too, opening `/studio/?dev=usb:COM7[:<busid>]` in a new tab —
  alongside **⚙ Open module** on that same port.
- A port a page is actively driving is no longer re-probed by the 12 s
  auto-check (the hub answers from the identity it already has), so the probe
  cannot stutter live commands.
- If an **outside** program holds the cable (`esptool`, a serial monitor, a
  Studio tab left in direct mode), the error now names what to close instead
  of showing a pyserial traceback.

**What to do differently:** nothing — reach for *USB (shared)* and open as
many pages as you want. `MiceHub.exe` was rebuilt; an old copy still has the
one-owner-per-port behaviour.

---

## 2026-07-26

### Added — `scient_test/tools/testapp.py`, the measuring app

Most dependent variables in the test plan are milliseconds: a 20 ms servo tick,
an 80 ms minimum move, a 150 ms physical floor, a 500 ms status push. **No eye
and no hand stopwatch can measure those**, so until now the fastest and most
important rows in the plan had no honest way to be filled in.

`testapp.py` polls the module and timestamps every reply on the PC. `POSE?` is
a short reply, so over USB it samples at ~100–200 Hz (5–10 ms per sample) —
fine enough to resolve the firmware's 20 ms interpolation steps. **Every
command prints the sample rate it achieved**, so the resolution of each number
is always visible, and a duration is never quoted finer than the sampling that
produced it.

```
python tools/testapp.py info        --transport usb --port COM5
python tools/testapp.py trace-nong  --transport usb --port COM5 --joint 3 --to 150 --T 300 --html
python tools/testapp.py nong-sweep  --transport usb --port COM5 --iv T --values 1000,300,150,50
python tools/testapp.py trace-lift  --transport usb --port COM5 --stage 1 --html
python tools/testapp.py lift-sweep  --transport usb --port COM5 --values 200,400,700,900,1023
python tools/testapp.py lift-repeat --transport usb --port COM5 --stage 2 -n 10
python tools/testapp.py latency     --transport wifi --host nong.local -n 50 --rate 10
python tools/testapp.py watch       --transport usb --port COM5
```

`--html` writes a self-contained plot — that is how you finally *see* the
cosine ease, the 20 ms staircase, the lift's 3.57 mm encoder steps. `--csv`
writes the summary row straight into the results sheet; raw samples and plots
go to `results/traces/`.

`lift-repeat` (LIFT-08 arrival spread) and `latency` (every latency/loss row in
T3/T4/T5) need no eye at all and produce a finished result on their own.

### Added — `scient_test/tools/simulator.py`, a fake module

`--transport sim` talks to a Python re-implementation of the firmware's motion
maths: cosine ease, 20 ms tick, the `max(80 ms, Δ ÷ max_dps)` floor, the lift's
encoder counts and 4-count tolerance. Two reasons it exists — learn the app
without burning servo life, and tell **"the app is wrong"** apart from **"the
robot is wrong"** (a number that is right in sim and wrong on the bench is the
real hardware talking).

It has no friction, no servo lag and no supply sag, so **it is never a result**.
Its output goes to `results/sim/`, never mixed into `results/`.

### Changed — the test plan now says who measures each row

Every test file gained a note naming, per row, whether the app, your eye, or an
instrument takes the measurement:

- **the app** — anything timed in ms, plus anything the module already knows:
  reported vs executed move duration, the 20 ms tick, effective `T`, encoder
  counts and speed, arrival spread, latency, loss, throughput;
- **your eye and a hand tool** — whatever holds still once the motion stops:
  joint angle with a gauge, rack position with a tape, "did it arrive",
  drop-outs by ear;
- **an instrument** — current, rail voltage, mass, temperature.

New rule in `scient_test/CLAUDE.md`: any new test row whose DV is under ~1 s
must name the `testapp.py` command that measures it.

### Changed — `scient_test/tools/bench.py` shares its transport layer

New `open_link()` factory, so `bench.py` and `testapp.py` open WiFi / USB /
RS485 links through one piece of code instead of two copies. `bench.py` keeps
working exactly as before — it is now described as the small standalone latency
meter, handy for a quick check or a `--csv` log.

### Added — Nong Studio: save your tuned rig as *your* default

Tuning the rig to match the real robot is slow work, and **Reset defaults** used
to throw all of it away by returning to the factory scale.

New **★ Save current as default** button (Rig setup card) locks the current rig
into a separate, protected slot. **Reset to default** now returns to *your*
saved rig; it falls back to the factory rig only if you never saved one, and
asks for confirmation before it does. Tuned dimensions are never overwritten.

Stored per browser (`localStorage`), alongside the existing rig cache.

---

## 2026-07-26 — initial commit

First publication of the mice installation software:

| | |
|---|---|
| `firmware/` | ESP32 firmware — one binary for every module type (`lift`, `nong`, `blank`), chosen at boot from NVS |
| `main_python/` | Mice Control Hub — finds every module on the network and serves its page over WiFi, USB or RS485 |
| `nong/main_python_set_nong/` | Nong Studio — 3D pose and keyframe sequence editor for the humanoid |
| `scient_test/` | the experiment plan — IV/DV/CV test tables, results sheets |
| `auto_click/` | standalone screen-automation helper, unrelated to the robot |

Build output is not tracked: `.pio/` (~230 MB of PlatformIO libraries and
objects), CMake build trees, `__pycache__`, machine-specific VS Code files.
`pio run` regenerates all of it.
