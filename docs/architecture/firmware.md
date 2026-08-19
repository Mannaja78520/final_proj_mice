# Firmware architecture

`code/firmware` — about 4,900 lines of hand-written source in `src/`, `config/`,
`tools/`, `lib/`, `test/`, `platformio.ini`.

**Not live code, and it will wreck any duplication scan:** `patches/` (33 dated
full-tree snapshots — this is why `NongModule.cpp` appears ~30 times), `.pio/`
(build output), `build/` (a stale CMake tree unrelated to PlatformIO).

## Module types

Declared once in `config/modules.json:28-50`. One class each.

| type | class | board | exclusively its own |
|---|---|---|---|
| `lift` | `LiftModule` | `nodemcu-32s` | `src/modules/lift/*`, `config/esp32_hardware_lift_module.h` |
| `nong` | `NongModule` | `nodemcu-32s` | `src/modules/nong/*`, `config/esp32_hardware_nong_module.h` |
| `cam` | `CamModule` | `esp32cam` | `src/modules/cam/*`, `config/esp32_hardware_cam_module.h` |

A fourth exists only in C++: `BlankModule`, an anonymous-namespace class at
`ModuleFactory.cpp:18-21`. It is the fallback when NVS holds a type this binary
was not built with — it keeps identity, RS485, WiFi and the website alive so the
type can be corrected remotely. It is not a buildable type.

`flashable` is documented as a field (`modules.json:25-26`) and **no entry uses
it**; `gen_tables.py:91` does not require it. Dead field.

## The shared core — `src/core/`, 18 files

Used by **every** module type: `Identity`, `ConfigStore`, `HwConfig`,
`UserStore`, `SDStore`, `SequencePlayer`, `CommandRouter`, `RS485Bus`,
`WebPortal`, `PeerDiscovery`, `Util`, `WifiArgs.h`, `WifiLink.h`.

**Used by lift only, despite living in core:** `RgbStrip` and `AudioPlayer`.
They are members of `LiftModule` (`LiftModule.h:56-57`) and every other env
excludes them explicitly (`platformio.ini:77,107,128`). Core by folder, lift by
fact — move them.

**Core that leaks module knowledge (the opposite problem):**

* `SequencePlayer::execStep` (`SequencePlayer.cpp:125-167`) hard-codes lift verbs
  (`goto/up/down/rgb/effect/bright/play/vol`) and nong verbs
  (`pose/joint/relax/attach`) in core.
* `HwConfig::memberFor` (`HwConfig.cpp:59-82`) lists every type's field unguarded.
* `ConfigStore.cpp:13-31` mixes lift and nong keys in one table.
* `WebPortal.cpp` includes and downcasts to `CamModule` (`:11-13, 24-28, 666-792`).

## Duplication — real, and worth sharing

All inside `NongModule.cpp` unless noted. **There is no per-module duplication of
WiFi, discovery, OTA, RS485 or SD handling** — that part of the architecture is
clean.

| what | where | ≈lines |
|---|---|---|
| joint-selector preamble, 5 identical 3-line copies | `:605,631,666,702,738` | 15 |
| `applyToOneOrAll` loop, 5 copies | `:608,635,669,706,742` | 15 |
| `changed → reattach else writeServos`, 3 copies | `:634,705,741` | 12 |
| sanity-clamp block, 2 byte-identical copies | `:53-62`, `:137-146` | 10 |
| **JCFG re-implements five validators** | `:457-472` vs `:581,604,627,661,733` | 30 |
| per-joint field list serialized **five** ways | `:15-66,98-149,160-185,556-574,783-807` | 70 |
| `cosf` ease inline instead of calling the tested `nongmath::ease` | `:297` vs `NongMath.h:98-102` | 1 |
| dead `NongModule::maxDelta`, never called | `:230-232`, `.h:166` | 3 |
| `jsonEscape` hand-inlined | `SDStore.cpp:103-107` vs `Util.cpp:27-36` | 5 |
| `.part`-then-rename written twice | `SDStore.cpp:137-176` vs `WebPortal.cpp:632-663` | 25 |
| WiFi scan-result formatting, 2 copies | `WebPortal.cpp:912-915`, `:920-923` | 8 |
| "stand the radio down before scanning", 2 copies | `WebPortal.cpp:402-405`, `:980-983` | 6 |
| `CFG` key list in three places — **one is already wrong** | `ConfigStore.cpp:13-31`, `CommandRouter.cpp:252-254`, `ConfigStore.h:13-14` | 5 |

**JCFG is the dangerous one.** `:456` states the requirement — a batch must not
smuggle in a value the individual commands would refuse — and enforces it by
copy. The two copies can silently disagree, and the result reaches a servo.

## Looks duplicated, is NOT — do not merge

`SPEED`/`SPEED?`, `TIME`/`TIME?`, `STOP`, `HOME` across nong and lift share a
user-facing verb and nothing else: deg/s bounded by the slowest joint vs
PWM-or-mm/s with an open-loop rpm model; freezing an interpolation vs stopping a
motor; moving to a neutral pose vs seeking a limit switch and zeroing an encoder.
`begin()`/`loop()`/`status()` are genuinely disjoint — `Module.h`'s empty
defaults already are the shared boilerplate.

## The module interface — `src/modules/Module.h`

Only `type()` is pure virtual (`:12`). Everything else has a default. Nong and
Lift override all of it; **Cam does not override `busy()`**, so `reach()`
(`WebPortal.cpp:296`) and the OTA guard (`:823`) can never refuse on a camera.

Two real bypasses:
1. `WebPortal` downcasts to `CamModule` for `take()`/`give()` — camera API not in
   `Module`. Now guarded by a runtime type check; an earlier unguarded
   `static_cast` caused an out-of-bounds write reachable from an unauthenticated
   GET (`WebPortal.h:95-105`).
2. `SequencePlayer` bypasses the interface by string, above.

Stale doc: `ModuleFactory.h:9-10` still says to register a type in
`ModuleFactory.cpp`. Wrong — the factory is generated, and `KNOWN_TYPES` no
longer exists.

## Generated code — `tools/gen_tables.py`

Runs as a PlatformIO `pre:` script (`platformio.ini:42`) and standalone.

| output | from | read by |
|---|---|---|
| `core/BuildTypes.h` | `modules.json` | `WebPortal.*`, `HwConfig.cpp`, `esp32_hardware.h:48` |
| `modules/ModuleTable.h` | `modules.json` | `ModuleFactory.cpp` |
| `modules/nong/ServoPresets.h` | `servos.json` | `NongModule.cpp:3` |
| `core/CommandHelp.h` | `commands.json` | `CommandRouter.cpp:2` |
| `web/ModuleUI.h` | `src/web/WebUI.h` | `WebPortal.cpp:32` |

Which types are carried comes from `-D MICE_TYPE_*`, read from **both**
`CPPDEFINES` and `BUILD_FLAGS` (`:442-457`) — reading `CPPDEFINES` alone silently
produced an all-types page for every env.

**Hand-editing a generated file is silently reverted** by `write_if_changed`
(`:106-115`) on the next build. Editing `firmware/generated/` does nothing at all
(builds read `$BUILD_DIR`). Editing `BuildTypes.h` is the sharpest: it decides
which hardware header is included, which pin fields exist, and which class the
factory can build — a mismatch gives link errors or a board that boots blank.

## OTA, from the firmware side

`POST /api/ota`, `WebPortal.cpp:805-870`. Refuses while the module is moving or a
sequence is playing (unless `force=1`), aborts a stale `Update` left by a dead
upload, registers `onDisconnect → Update.abort()`, and validates with
`Update.end(true)`.

**No authentication on any route.** `users.verify` never appears in
`WebPortal.cpp`. `/api/ota`, `/api/cmd`, `/api/delete` and `/api/upload` are open
to anyone who can reach the IP or join the group AP. No signature or version
check beyond what `Update.end` does. WiFi credentials are printed in clear to
serial (`:147-150`).

## Boot: how a board decides what it is

`Identity::begin()` reads NVS `module/type`, defaulting to `"blank"`
(`Identity.cpp:19`); id and name default from the eFuse MAC. `main.cpp:71` calls
`ModuleFactory::create`, which calls the **generated** `makeModule` — containing
only the types this binary was compiled with — and falls back to `BlankModule`.
`SET TYPE` is validated against the same generated list
(`CommandRouter.cpp:188`), so a nong binary answers
`ERR unknown type (nong,blank)` for `lift`.

## Discovery and peer-to-peer

**Every board is an HTTP server; boards are HTTP clients only of each other.
No central server. No PC required.**

* mDNS: advertises `_module._tcp` with id/name/type TXT, queried every 20 s from
  its own FreeRTOS task (`PeerDiscovery.cpp:9-26, 86-113`).
* AP-subnet probe: mDNS cannot see boards on *our own* AP, so `scanAp()`
  (`:65-84`) walks `192.168.4.2…` and GETs `/api/status`.
* Radio `"on"` means `WIFI_AP_STA` — joins the show network *and* keeps its own
  AP up, deliberately, so a distant module can lean on it.
* Relaying: `wifilink::decide()` returns STAY/RELAY/RETURN from RSSI with
  hysteresis (`WifiLink.h:35-64`).
* **Group is the trust boundary.** AP password is
  `SHA-256("mice-group:" + group)` truncated to 16 hex (`Identity.cpp:87-107`).
  Explicitly not a defence against someone who knows the group name.
* `REACH` (`WebPortal.cpp:293-346`) resolves a name/id/ip via peers, then GETs
  `/api/cmd`, 3 tries × 700 ms. **Blocks the router mutex up to 2.1 s**, which
  stalls the 50 Hz servo loop; it refuses while `busy()`, but `busy()` is false
  between sequence steps.
* RS485 is masterless multi-drop: `#<addr> CMD` in, `@<id> reply` out, broadcast
  `#*`, PING replies staggered by `id*20 ms`.

## The board website — `src/web/WebUI.h`, 1,108 lines

Not compiled; it is the **master**. `gen_tables.py` strips other types' regions
into `web/ModuleUI.h`. Roughly 62% JS, 27% HTML, 6% CSS.

Per-type content is excluded two ways, deliberately layered: **build time**
(marker regions physically deleted) and **runtime capabilities** (`render()`
reads `st.caps`). The runtime layer survives because the hub serves the *master*
over USB, where every card is present and only the board knows which are real.

## Error handling — one convention, unevenly applied

`ERR ` prefix means failure, `OK ` means success. Three places pattern-match the
prefix (`CommandRouter.cpp:49,54`, `WebUI.h:933`), coupled by magic string.

Documented inconsistencies: queries answer with a bare noun (`PONG`, `EST …`);
`INFO`/`PEERS`/`FILES`/`PIN?`/`LIMIT?` return raw JSON with no envelope;
`HELP <bad>` reports failure **without** `ERR` (`CommandHelp.h:108`); `FREAD`
returns naked base64 or the bare token `EOF`; the RS485 bridge returns neither;
the camera HTTP routes return plain English with no `ERR` while `/api/ota` uses
`ERR` in the same file; `ERR` is used for a non-error at `LiftModule.cpp:222`;
three different phrasings of the same joint-range usage string;
`ConfigStore::set` distinguishes causes and `CommandRouter.cpp:250` has to
**sniff the message text** to tell them apart.

## Contradiction worth fixing

`SNAP <name>` cannot work on a cam build. `esp32_hardware_cam_module.h:61-68`
undefines the SD pins to `-1`; `SDStore::begin()` returns false; `CamModule::saveTo`
always returns `"no sd card"`. There is no `SD_MMC` path anywhere. But
`modules.json:46`, `commands.json:101`, `CamModule.h:21` and `COMMANDS.md:546`
all claim it saves to the card. The hardware header's comment is the honest one.
