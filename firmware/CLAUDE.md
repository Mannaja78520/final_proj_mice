# Project rules

- **COMMANDS.md is the authoritative command/API reference.** Whenever a change
  touches anything commandable — CommandRouter core commands, a module's
  `handleCommand` verbs, WebPortal HTTP/WebSocket endpoints, RS485 framing, or
  sequence YAML step keys — update COMMANDS.md (and the quick table in
  README.md if affected) **in the same change**. Never leave them out of sync.
- `promt.md` is an auto-appended log of user prompts (UserPromptSubmit hook in
  `.claude/settings.json`). Don't edit or reorder it except when asked.
- Build with `pio run -e lift_module` (PlatformIO, ESP32 nodemcu-32s). Always
  verify the build compiles after firmware changes. (The env name is historic —
  the one binary serves every module type, lift and nong alike; keeping the
  name avoids re-downloading `.pio/libdeps/lift_module/`.)
- Architecture: one binary for all module types; module type is selected at
  boot from NVS identity (`SET TYPE lift|nong` + reboot — flash once, choose
  later). New module types go in `src/modules/<type>/` and are registered in
  `src/modules/ModuleFactory.cpp`.
- This folder is `code/firmware` (moved from `code/lift/firmware`), shared by
  the whole installation. The nong pose/sequence editor lives in
  `code/nong/main_python_set_nong` — its YAML export format must stay in sync
  with the `pose` sequence step and the `POSE` command here.
