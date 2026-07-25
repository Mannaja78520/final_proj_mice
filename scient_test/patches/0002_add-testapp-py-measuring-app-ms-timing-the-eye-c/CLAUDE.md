# Project rules

- This folder is the **experiment plan** for the installation, not code that
  runs on the robot. Nothing here may modify firmware, Nong Studio or the hub —
  if a test reveals a bug, fix it in the owning folder and note the fix here.
- **Every test states its Independent Variable, Dependent Variable and Control
  Variables**, and changes exactly **one IV per test**. A test that moves two
  knobs at once is not a test — split it. New tests follow the existing table
  layout (`ID | IV setting | Command / action | Measure (DV) | Expected |
  Pass if`) so the results CSVs keep matching.
- **Every "Expected" value must be derived from the code**, with the source
  named: `code/firmware/src/modules/{nong,lift}/…`, `config/esp32_hardware_*.h`,
  `src/core/{RS485Bus,WebPortal,PeerDiscovery}.cpp`, `src/main.cpp`,
  `code/nong/main_python_set_nong/web/app.js`. `code/firmware/COMMANDS.md` is
  the authoritative reference for command syntax and replies — quote it, never
  paraphrase a reply string from memory.
- **When the firmware changes, the affected tests change in the same edit.**
  Formulas that appear in both places (nong move time = largest joint delta ÷
  speed, floor `max(Δi ÷ max_dps_i)`, min 80 ms; lift `counts_per_stage`,
  `cpm`, `est_mms`) must stay identical to the code they predict.
- **The three transports stay in separate files** — `T3_rs485.md`,
  `T4_wifi.md`, `T5_usb.md`. They are not one test with a transport column:
  each has its own IVs and its own failure modes, and each is run once per
  module type. Never merge them.
- **Patch after every change.** Run `python save_patch.py "<what changed>"`
  after editing `tests/`, `tools/`, `README.md` or this file. Snapshots go to
  `patches/NNNN_<slug>/` and a row is appended to `PATCHES.md`; old patches are
  never overwritten (`--list`, `--show <n>`, `--restore <n>`; restore
  auto-saves the current version first). Don't hand-edit `patches/` or
  `PATCHES.md`.
- `results/*.csv` are **data, not source** — they are never patched and never
  wiped. Recorded measurements are only ever appended to or corrected by the
  person who took them; a test-plan edit must not silently invalidate a filled
  sheet (bump the test ID instead, e.g. `NONG-03` → `NONG-03b`).
- `promt.md` is an auto-appended log of user prompts (UserPromptSubmit hook in
  `.claude/settings.json`, same convention as `code/firmware`,
  `code/main_python` and `code/nong/main_python_set_nong`). Don't edit or
  reorder it except when asked.
- `tools/bench.py` and `tools/testapp.py` are **stdlib-only for WiFi and sim
  mode**; `pyserial` may be required for USB/RS485 but must fail with a clear
  message when missing. Both share one transport layer (`bench.open_link`) —
  don't fork it.
- **Millisecond DVs belong to the app, never to the eye.** Any new test row
  whose DV is under ~1 s must name the `testapp.py` command that measures it.
  Rows the eye *can* do (angle, tape, mass, current, drop-outs) stay manual and
  say so. Every app command must keep printing the **sample rate it achieved** —
  that is the result's resolution, and a duration must never be quoted finer
  than it.
- `tools/simulator.py` mirrors the firmware's motion maths (cosine ease, 20 ms
  tick, `max(80 ms, Δ ÷ max_dps)` floor, lift counts/tolerance). When the
  firmware's maths changes, change the simulator in the same edit or it starts
  teaching the wrong thing. It has no friction, lag or supply sag — it is never
  a result, and its output goes to `results/sim/`, never into `results/`.
- Commands written into tests are **UPPERCASE**: core commands are
  case-insensitive but module commands (`POSE`, `GOTO`, `RGB`…) are matched
  case-sensitively in the module's `handleCommand`, so lowercase returns
  `ERR unknown cmd`. Test USB-05 documents this deliberately.
- Safety text stays in the tests: nong joint limits before powering servos,
  lift limit switches verified before any speed run, current-limited bench
  supply. Don't trim it for brevity.
