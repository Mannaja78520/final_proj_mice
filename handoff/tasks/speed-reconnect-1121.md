# Test every speed and every reconnect (cloud sim + PC list)

Owner: claude
Updated: 2026-11-21
Branch: claude/project-thread-yvuzk1
Last commit: this checkpoint
Plan: none (user 2026-11-21: "ความเร็วต่างๆ การรีคอนเนคต่างๆ ลองให้หมด", then many boards / 255 / WiFi backup / far boards / hub order)

## Goal
Measure hub/voice/faces speed and recovery, the RS485 bus and hub list at 5..255 boards,
WiFi backup networks and relay, and fix what is slow or does not recover.

## Doing now
Full cloud QC on this branch, then PR. Friend apps + Ollama + real timing need the PC (Remote Control).

## Done (raw numbers: docs/experiments/2026-11-21_speed_reconnect.md)
- Listen backlog 5 -> 256 on hub, voice, faces. 200 clients p95 1.4-2 s -> 75-260 ms, 0 errors.
- Hub list: natural order + heading per kind (hub_modules.board_order, modules.js, tabs.js filter).
- RS485 census: one slot per id (BusSlot.h, 6 ms). Old rule lost most answers past ~30 boards (model).
- Saved backup WiFi: SET WIFI2/3, WifiList.h, WebPortal rotate. Native + QC proven.
- Tools: tools/bench/chaos_services.py, hub_many_boards.js, bus_census_model.py, wifi_topology_model.py.
- QC: check_scale_robust, check_qemu_census; check_rs485_census updated.

## Next
- Relay rule (WifiLink.h mayJoin): joins only a hotspot whose NAME sorts after its own. In the model a line of
  10 boards away from the router strands 9 when names grow outward. Needs a design (user decision).
- Multi-hop relay cannot route (every hotspot is 192.168.4.1/24); hub REACH is one hop.
- Census INFO ask is limited to the first 6 boards per bus (hub_probe.py): boards 7+ show no chip/group.
- /api/ports at 200 clients: p95 3.5 s (serial probing). Not changed.
- PC: friend apps (8000/5173) run-only speed + kill/restart; Ollama down/up and cloud think fallback timing.
- Lab: real WiFi radio, real RS485 timing with 30+ boards, real OTA.

## Facts found
- main_python/main.py:2984 hub server is ThreadingHTTPServer (default listen queue 5).
- firmware/src/core/RS485Bus.cpp census: `#* PING` reply delay now busslot::censusDelayMs(id).
- firmware/src/core/WebPortal.cpp savedNets/selectNet: slot 0 = SET WIFI (or config.h), 1-2 = SET WIFI2/3.
- QEMU in the cloud needs `apt-get install libslirp0` after `python tools/qemu_esp32.py install`.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| main_python/main.py, apps/voice/service.py, apps/faces/service.py | listen queue 256 | done | check_scale_robust quick, sabotage caught | pushed branch |
| main_python/hub_modules.py, web/home/parts/modules.js, tabs.js, style.css | order + headings | done | check_scale_robust, UI sim 5/30/255 screenshots | pushed branch |
| firmware/src/core/BusSlot.h, RS485Bus.cpp | per-id census slot | done | native test, check_qemu_census, check_rs485_census (QEMU = emulator) | pushed branch |
| firmware/src/core/WifiList.h, Identity.*, WebPortal.*, CommandRouter.cpp | backup WiFi | done | native test, wifi_relay QC (no radio in QEMU) | pushed branch |
| tools/bench/*, qc/checks/check_scale_robust.py, check_qemu_census.py | benches + checks | done | run | pushed branch |
