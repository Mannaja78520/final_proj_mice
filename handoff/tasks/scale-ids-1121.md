# Scale boards past 255, many companies (claude, 2026-11-21)
Owner: claude  Updated: 2026-11-21  Branch: claude/project-thread-gx4fzr

## Done
Ranged PING / CHIPS / `#~chip` (firmware/src/core/BusAddr.h, RS485Bus.cpp), hub: main_python/bus_ids.py, hub_probe.py (ranged census + chips for all boards), hub_modules.board_key (bus-qualified fallback). Sim: qc/lib/bus_sim.py, check_bus_scale. Numbers + design: docs/architecture/scaling-ids.md, docs/experiments/2026-11-21_bus_scale.json.

## Next (lab / not done)
- `pio run` NOT run here (no pio): compile mice_nong/cam/lift/blank + QEMU check_qemu_bus.
- Real bus: 1/8-UL transceivers, >32 nodes, WiFi join storm, USB inrush, COM limit.
- UI to list/fix duplicate ids (hub shows dupChips only in data); help page parity when UI added.
- Full QC: this cloud env fails 11 checks that need pio/mujoco/partition table (not from this change).

## File status
All files: committed on branch, quick QC 6858 passed / 11 env-only fails, simulated only.
