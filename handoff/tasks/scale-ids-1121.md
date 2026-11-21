# Scale boards past 255, many companies, chained buses

Owner: claude:scale-ids-1121
Updated: 2026-11-21 (Bangkok afternoon)
Branch: claude/project-thread-gx4fzr
Last commit: this checkpoint
Plan: none (user ask in thread "Scale boards past 255 and many companies")

## Goal
User: go past 255 RS485 boards, many companies, RS485+WiFi+USB together, mass power-on, and chained buses (247 -> bridge -> 247 ...) incl. odd topologies "a genius customer builds".

## Doing now
Nothing in flight; waiting for merge of the PR.

## File status
Baseline: 71803e9 (main with #150 #154)

| File | Change | State | Verification | Commit |
| --- | --- | --- | --- | --- |
| `firmware/src/core/BusAddr.h` | ranged PING, CHIPS, chip addressing maths | done | host g++ parity in check_bus_scale (simulated) | this checkpoint |
| `firmware/src/core/BusPath.h` | path address `#>12>7`, MAX_DEPTH 4 | done | host compile only | this checkpoint |
| `firmware/src/core/RS485Bus.cpp/.h` | ranged PING, CHIPS (+G), `#~chip`, gateway forward/relay | done, NOT compiled (no pio here) | check_bus_scale, check_bus_topology read it; no board | this checkpoint |
| `main_python/bus_ids.py` | census/chips/duplicates/fix per bus | done | check_bus_scale (simulated) | this checkpoint |
| `main_python/bus_net.py` | tree walk over bridges, loops, depth cap | done | check_bus_topology (simulated) | this checkpoint |
| `main_python/hub_probe.py`, `hub_modules.py` | ranged census on crowded bus, chips for all, bus-qualified key | done | quick QC | this checkpoint |
| `qc/lib/bus_sim.py`, `qc/checks/check_bus_scale.py`, `check_bus_topology.py` | collision model + checks | done | quick QC green for these | this checkpoint |
| `docs/architecture/scaling-ids.md`, `docs/experiments/2026-11-21_bus_*.json`, `firmware/COMMANDS.md`, `docs/systems.json` | design, numbers, protocol | done | n/a | this checkpoint |

## Facts found
- `firmware/src/core/BusSlot.h` (#154): plain PING = id x 6 ms slot, fine while ids are unique; blind where two boards share an id.
- `main_python/hub_modules.py` board_key: chip first; chipless bus boards now keyed with their cable.
- Old firmware reads `#<text>` with toInt(): `#12/7` would run as `#12`; so new prefixes `~` and `>` read as 0.

## Done
Simulated numbers in docs/architecture/scaling-ids.md. Quick QC: only environment failures (no pio/mujoco/partition table).

## Next
1. Lab: compile `pio run -e mice_nong -e mice_cam -e mice_lift -e mice_blank`, QEMU check_qemu_bus.
2. Hardware owner for a gateway's second UART (calls setDownstream / onDownstreamLine).
3. Hub: wire Topology paths into usb_cmd routes and show duplicate ids / the tree in the Modules page (then help page parity).
4. Measure real relay-hop delay (sim assumes 4 ms), MAX485 32-node limit, WiFi join storm.

## Blocked
- Real boards and a second UART: lab only.
