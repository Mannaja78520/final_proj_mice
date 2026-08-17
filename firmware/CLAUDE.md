# Project rules

- **COMMANDS.md is the authoritative command/API reference.** Whenever a change
  touches anything commandable — CommandRouter core commands, a module's
  `handleCommand` verbs, WebPortal HTTP/WebSocket endpoints, RS485 framing, or
  sequence YAML step keys — update COMMANDS.md (and the quick table in
  README.md if affected) **in the same change**. Never leave them out of sync.
- `promt.md` is an auto-appended log of user prompts (UserPromptSubmit hook in
  `.claude/settings.json`). Don't edit or reorder it except when asked.
- **One binary per module type** (PlatformIO, ESP32 nodemcu-32s):

  ```
  pio run -e mice_nong             the humanoid
  pio run -e mice_lift             the lift
  pio run -e mice_cam              the camera (ESP32-CAM — its own board)
  pio run -e mice_blank            core only — a board that is not a module yet
  pio run -e mice_module_firmware  lift + nong in one binary (legacy, kept for now)
  ```

  Always verify the build compiles after firmware changes. QC builds
  `mice_nong` (`qc/checks/check_firmware_build.py`) and every env
  (`check_build_split.py`), so a compile break cannot pass unnoticed — but run
  it by hand too while iterating. Each env has its own `.pio/libdeps/<env>/`,
  downloaded once.
- Architecture: the module type is chosen at BUILD time and confirmed at boot
  from NVS identity (`SET TYPE nong` + reboot). A binary only accepts the types
  it was built with — `SET TYPE lift` on a nong build answers
  `ERR unknown type (nong,blank)`.
  **A new module type is one entry in `config/modules.json`**, plus its class in
  `src/modules/<type>/` and an env in `platformio.ini`. The build guards
  (`BuildTypes.h`) and the factory (`ModuleTable.h`) are GENERATED from that
  file — do not hand-list a type in `ModuleFactory.cpp` again.
- **Anything that belongs to ONE module type must be behind its guard**, or
  every board pays for it:
  | what | how |
  |---|---|
  | C++ (module class, pin entries, includes) | `#if MICE_HAS_NONG` — `src/core/BuildTypes.h` |
  | web page cards and script | `<!--#type nong-->` … `<!--#end-->` in `src/web/WebUI.h` |
  | commands | `"scope": "nong"` in `config/commands.json` |
  `src/web/WebUI.h` is the MASTER page and is not compiled: `tools/gen_tables.py`
  generates this env's page (`web/ModuleUI.h`), command table and servo table
  into `.pio/build/<env>/generated/`. The hub still serves the master whole.
  Run it by hand with `python tools/gen_tables.py [--types nong] [--out DIR]`;
  with no arguments it writes the all-types tree to `firmware/generated/`,
  which is what QC reads.
- This folder is `code/firmware` (moved from `code/lift/firmware`), shared by
  the whole installation. The nong pose/sequence editor lives in
  `code/nong/main_python_set_nong` — its YAML export format must stay in sync
  with the `pose` sequence step and the `POSE` command here.
