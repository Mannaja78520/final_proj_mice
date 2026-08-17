# Project rules

- **QC after every change — and add to it.** `python ../../qc/run_qc.py --quick`
  while iterating (~3 s), the full `run_qc.py` before calling anything done
  (~1 min, drives a real browser). **Whenever we add a feature or fix a bug,
  add its check to `code/qc/checks/`** — the runner discovers `check_*.py` by
  itself, so covering something new is one new file, and the suite grows with
  the project instead of going stale. A new check only counts once you have
  **broken the fix and watched it fail**; the live-drag check passed against
  the very bug it was written for until it reproduced the real user action.
  Assert on what reached the module (`fake_serial.wire`), never on what the UI
  says about itself. See `code/qc/README.md`.
- **Document every feature in `main_python/web/help.html`** — the offline
  Features & help page the hub serves at `/help` and links from its main page.
  This is enforced: the `docs` QC check fails when a command, module type,
  servo preset or QC area exists that the page does not describe. Update the
  page in the SAME change as the feature, not afterwards.
- **Every web app must work on any screen.** Hub, module website (`WebUI.h`),
  Nong Studio and the help page all carry media queries for phone / tablet /
  large screen plus `pointer:coarse` touch targets. The `responsive` QC check
  loads each page in a real browser at 360–1920px and fails if anything
  scrolls sideways, so a new fixed-width layout is caught immediately.

- This is **Nong Studio**: the pose & sequence editor for the `nong` humanoid
  module. **10 logical joints:** 8 arm (universal joint = 2 servos in each
  shoulder and elbow) + `WAIST` (joint 9, yaws the whole upper body left/right)
  + `SHRUG` (joint 10, lifts both shoulders ~6°). As built: shoulders
  PDI-1181MG 15:18 **(270°)**, elbows MG90S 12:13 (180°), WAIST TianKongRC 35kg
  1:1 (270°), SHRUG MG90S 1:1 (180°) — but **servo type, gear ratio, pulse
  range, max °/s and servo travel (180/270°) are per joint** and changeable at
  runtime. Constants `ARMJ=8` (IK/arm-FK) and `NJ=10` (poses/sliders/timing)
  gate the loops; keep new per-joint code using `NJ`. WAIST/SHRUG are visual in
  Studio (bodyGroup yaw / shoulderMount pitch); the real angle is what's sent.
  The firmware it drives lives in
  `../../firmware` — its **COMMANDS.md is the authoritative reference** for
  the command language, the `POSE`/`JOINT` commands and the `/moves/*.yaml`
  sequence format. Whenever the export format or joint order changes here,
  change the firmware (and its COMMANDS.md) **in the same change** — never
  leave the two out of sync. Joint order everywhere:
  `L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG` (joint
  deg, neutral 90). Poses/sequences carry 10 values; an 8-value pose still
  loads (WAIST/SHRUG default to 90) so old sequences keep working.
- **Patch the web app after every change.** Each change the user asks for is
  one preserved snapshot: run `python save_patch.py "<what changed>"` after
  editing `web/`. It copies app.js/index.html/style.css into
  `patches/NNNN_<slug>/` and appends to `PATCHES.md` — old patches are never
  overwritten (`--list` to see them, `--restore <n>` to roll back; restore
  auto-saves the current version first). Don't hand-edit `patches/` or
  `PATCHES.md`.
- `promt.md` is an auto-appended log of user prompts (UserPromptSubmit hook in
  `.claude/settings.json`). Don't edit or reorder it except when asked.
- Run with `python main.py` (stdlib only — keep it free of pip dependencies).
  The UI is `web/` (three.js r147 UMD builds vendored in `web/vendor/`, no
  CDN at runtime). After changes, verify the server starts and `/`,
  `/api/list`, `/api/export` respond.
- Data folders (created on first run, contents are user data — don't wipe):
  `projects/` (editor projects, JSON), `sequences/` (exported YAML — the user
  copies these onto the module SD card `/moves/`), `models/` (user STL
  exports from SolidWorks, mm units).
- Timing rule: time between keyframes = largest joint delta ÷ speed (deg/s),
  minimum 80 ms — identical to `NongModule::durationFor()` in the firmware.
  The physical floor is **per joint**: `max over joints of (that joint's delta
  ÷ that joint's max °/s)` — matches `NongModule::minDuration()`. Keep the two
  formulas identical whenever either side changes.
  Exported pose steps always carry an explicit `T <ms>` so multi-ESP linked
  humanoids stay in sync.
