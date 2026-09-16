---
name: mice-contract-check
description: Check Mice cross-component contracts when changing commands, registries, joint motion, calibration, persistence, or WiFi/USB/RS485 behavior.
---

All repository paths refer to the Mice root. Read only the contract affected
by the task and its producers, consumers, and existing regression checks.

- Commands and module types: inspect `firmware/config/commands.json`,
  `firmware/config/modules.json`, `firmware/tools/gen_tables.py`, and the
  affected router/module code. Change registry sources, regenerate by the
  established build path, and keep `firmware/COMMANDS.md` consistent. Do not
  patch generated output as the source of a new command or capability.
- Motion: trace joint count/order, per-joint arrays, neutral pose, angle units,
  calibration offsets, gear ratio, speed, duration floor, and hold semantics
  between Studio, hub playback, and firmware. Derive values from current code
  and configuration; do not copy defaults into a second table. Check zero,
  boundary, missing, and out-of-range inputs where behavior changes.
- Transports: preserve command meaning across WiFi, shared USB, and addressed
  RS485. Check reply framing, broadcast behavior, one owner per COM port,
  reconnect behavior, and cancellation only where the change touches them.
- Playback: check which of the board, hub, or browser owns the clock; verify
  takeover and stop behavior on the wire. Browser preview is not timing proof
  for an actual robot.
- Persistence and packaging: preserve saved projects, sequences, calibration,
  and machine-local settings. Inspect migration and round-trip checks when
  schemas change. Check bundling for new runtime assets; a source run does
  not establish that the packaged executable contains them.

Start with matching checks in `qc/checks/`, especially contracts, registries,
transports, calibration, persistence, and sequences. Confirm current filenames
with search rather than assuming every area maps to one file. Run relevant
firmware build environments when firmware or generated tables change.

Protect user data in checks with isolated fixtures or backup/restore in finally,
then verify restoration. Never change real pin maps or calibration as test data.
Keep native/simulated proof separate from real-board timing and motion results.
