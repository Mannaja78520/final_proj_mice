# Architecture — what the code actually does

Written 2026-08-18 from three independent read-only explorations of the real
tree. Every claim carries a `file:line`. Where a comment, a README or the
original brief disagreed with the code, **the code won** and the disagreement is
recorded.

These notes exist so a later session — or a different model — does not have to
re-derive the architecture from scratch after a context reset.

| file | covers |
|---|---|
| [firmware.md](firmware.md) | ESP32 modules, the shared core, duplication, discovery, OTA, the board website |
| [hub.md](hub.md) | `main_python/main.py`: every route, port ownership, discovery, the show clock, identity |
| [web.md](web.md) | the six user-facing surfaces, workflows, the five states, duplicated UI |

## The five corrections that matter most

The refactor brief made five assumptions the code does not support. Anyone
picking this work up should read these first, because acting on the brief's
version would mean building or merging things that do not exist.

| assumed | actual | evidence |
|---|---|---|
| `connect()` duplicated per module | WiFi, discovery, OTA, RS485 and SD exist **once**, in `src/core/`. No per-module copy exists. | grep across `firmware/src` |
| module management tangled with flashing | **Already separate** in Python. Flashing is one block, `main_python/main.py:955-1231`. They touch in exactly 3 places, all correct coordination over one cable. | `main.py:394`, `:1367`, `:1173` |
| a "Sub-PC" tier exists | **No such concept in the codebase.** The only match for "sub-pc" anywhere is `promt.md`, the prompt log. | grep, whole repo |
| two Python servers | `nong/main_python_set_nong/main.py` is a **13-line stub** that `runpy`s the hub. | that file, lines 12-13 |
| version redundancy (`module.`/`device.`/`app.version`) | **Two version fields exist and both are legitimate**: `FW_VERSION` (firmware build) and `CAL_VERSION` (calibration blob layout). | `firmware/config/esp32_hardware.h:14`, `NongModule.h:122` |

## The real topology

```
phone / browser  ──HTTP──>  hub (a PC, port 8642)  ──HTTP or serial──>  board
                                                                          │
                            board <──mDNS + AP probe + REACH + RS485──> board
```

* The hub **always initiates**. No board ever dials the hub; nothing in the
  firmware knows port 8642 exists (`PeerDiscovery.cpp:35` and
  `WebPortal.cpp:328` are the only outbound HTTP calls, and both are
  board-to-board).
* **A board needs no PC.** It serves its own site, runs shows on its own clock,
  and works with no SD card and no WiFi (`main.cpp:69`, `WebPortal.cpp:122-129`,
  `SequencePlayer.cpp:14-38`).
* **Boards find each other** two ways, because one is not enough: mDNS
  (`PeerDiscovery.cpp:9-26`) plus a walk of the module's own AP subnet
  (`:65-84`), which exists because mDNS cannot see boards sitting on our own AP.
* **Group is the trust boundary.** The AP password is
  `SHA-256("mice-group:" + group)` truncated to 16 hex chars
  (`Identity.cpp:87-107`), so same-group boards can join each other and nothing
  else can. It is explicitly *not* a defence against someone who knows the
  group name (`Identity.cpp:82-86`).

## The two things most worth fixing

1. **There is no authentication anywhere.** `WebPortal::setupRoutes`
   (`WebPortal.cpp:519-875`) never calls `users.verify`; the module website's
   login is browser-side state only (`WebUI.h:775`) and the login card **prints
   the default password** (`WebUI.h:135-137`). The hub binds `0.0.0.0` with no
   auth at all. Anyone on the venue WiFi can reflash a board or drive servos.
2. **A phone cannot discover the hub.** Its address exists only as a console
   `print` (`main.py:1958`) — on no web page, with no QR and no mDNS, while the
   whole product is built to be used from a phone.
