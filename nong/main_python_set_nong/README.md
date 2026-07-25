# Nong Studio — pose & sequence editor for the nong humanoid

Blender-style desktop tool to pose the **nong** robot (upper body, 2 arms —
universal joint from 2 servos in each shoulder and each elbow, no fingers —
PDI-1181MG shoulders (270°), MG90S elbows (180°), plus a **waist** that turns
nong left/right (TianKongRC 35kg 270°) and a **shrug** that lifts both
shoulders (MG90S ~6°); every joint's servo is changeable)
and to build **movement sequences like a video editor**: start pose →
keyframes → export a YAML file for the robot's SD card.

```
python main.py            # opens http://127.0.0.1:8642 in your browser
```

…or just double-click **run_nong_studio.bat**. No pip installs needed
(Python 3.8+, standard library only). The 3D engine (three.js) is vendored
in `web/vendor/` so it also works offline.

**Use it from other devices:** the server listens on the whole local network —
the console prints a second URL like `http://192.168.1.20:8642/` that any
phone/laptop **on the same WiFi** can open (allow Python through the Windows
firewall the first time it asks). WiFi robot control works from any device;
only the USB/Web-Serial transport is limited to the browser on the host PC.

**Do I need the PC every time?** Only to *edit*. The editor is a local app:
whenever you want to make or change movements, start `main.py` (or the .bat)
on any PC that has this folder. The **robot never needs the PC** to perform —
sequences live on its SD card and are selected/run from the module's own
website, USB, or RS485.

## Workflow

1. **Pose the robot** in the 3D viewport:
   - click an arm segment → two colored rings appear (the 2 servo axes of
     that universal joint) — drag a ring to rotate that servo,
   - or drag the green **wrist ball** — inverse kinematics moves the whole
     arm (all 4 servos) to follow it,
   - or use the 8 sliders on the right (servo degrees 0–180, neutral 90).
2. **Keyframe 0 is the start pose.** Select it any time, change the pose,
   press **Update selected** to re-edit it.
3. Pose → **+ Add keyframe** → pose → add… The **time between keyframes is
   calculated automatically** from the servo speed (deg/s, Timing card):
   `time = biggest joint change ÷ speed` — exactly the formula the firmware
   uses. Every keyframe's `T` (ms) and `hold` (pause after the move) can be
   edited by hand on its chip.
4. **▶ Play** previews the motion with the same smooth ease-in/out the
   firmware uses; the scrub bar works like a video editor.
5. **Export YAML (SD card)** writes `sequences/<name>.yaml`. Copy it into
   `/moves/` on the module's SD card. On the robot, open the module website
   and pick the sequence in the **Sequences** card (or send `MOVE <name>.yaml`).

## Keyframe times: automatic, editable, physically safe

Every keyframe shows its time `T` and a **min** value. The min is the
physical limit: for each joint `that joint's change ÷ that joint's servo
speed`, and the **slowest** joint on the move wins. Each joint has its own
`max °/s` in Setup ▸ rig (as built: 375 °/s shoulders, 400 °/s elbows); the
Timing card's *servo max* caps them all, so lowering it only ever makes moves
safer. You can always type a **longer** time; typing a
shorter one snaps back to the minimum — otherwise the plan would say the arm
arrived while the real arm is still moving, and the next move would start
from a pose that was never reached. The firmware enforces the same rule
(`max_dps` in module.yaml / `CFG max_dps`), so plan and real robot stay
matched. Changing either speed recalculates the times.

## Editing a saved sequence

- **Local file:** timeline bar → "Edit saved…" dropdown → *Load for editing*
  brings any YAML from `sequences/` back into the timeline.
- **From the robot SD:** Robot SD card card → *✎ Edit* next to a file
  downloads it from the module and loads it into the timeline.
  Edit, then *Export* / *Upload current* again.

## Robot link (WiFi, USB, or RS485)

Pick the transport in the **Robot link** card:

- **WiFi** — type the module IP (or `name.local`), press Connect.
- **USB / RS485 (Web Serial)** — press *Connect USB* and pick the COM port
  (Chrome/Edge). The **bus id** field selects how the port is used:
  - *empty* — the cable goes straight into the nong module's own USB;
  - *set to the nong's id* — commands are framed `#<id> …` (the RS485
    protocol), which works with a **USB-RS485 dongle** wired to the bus,
    **or** through **any other module's USB port** (every module bridges
    `#` lines onto the bus — same trick as the firmware's usb-console).

  **Everything works on every transport** — poses, running sequences, the
  monitor, and also SD file upload / download(edit) / delete: over WiFi the
  editor uses the module's HTTP file API, over USB/RS485 it uses the
  firmware's `FBEGIN/FDATA/FEND/FREAD/FDEL` text commands (base64 chunks
  sized to fit RS485 frames).

Then:

- **live** — the robot follows every pose change in the editor; during
  ▶ Play each segment is sent with its exact `T`.
- **monitor** — the opposite direction: the 3D model **follows the real
  robot** (its actual joint angles are polled continuously) and the status
  line shows which sequence is playing and how many ms the current move has
  left. Use it to watch a run started from the SD card.
- **Robot SD card — /moves**: list the sequences on the card, **▶ Run any
  one you pick**, upload the current timeline, ✎ edit or ✕ delete a file.

## Joints — 8 arm + 2 body

Nong has **10 joints**. Joints 1–8 are the two arms (universal shoulder + elbow,
2 servos each). Joints 9 and 10 are the **body**:

- **Waist (turn L/R)** — joint 9, a TianKongRC 35 kg 270° servo that yaws the
  whole upper body so nong can look to the side. In the 3D view it turns the
  torso, head and both arms together.
- **Shrug (shoulders up/down)** — joint 10, an MG90S that lifts both shoulders
  a little (only ~6°, so its `min/max` default to 87–93). In the 3D view the
  shoulder mount tips up/down (exaggerated ×3 so the small move is visible).

Both appear as their own sliders and their own rows in the servo/gear table.
Old 8-joint sequences still load — the two body joints just default to 90.

## Rig setup — match the model to YOUR robot (no code editing)

If the 3D model doesn't match the real robot (e.g. at all-90° the real arms
are not close to the body), open the **Rig setup** card:

- **zero°** per joint — the servo angle where that joint hangs straight along
  the body. Move the sliders until the model matches the real robot's pose,
  then type those angles as the zeros.
- **min° / max°** per joint — each joint's real travel in **joint degrees**.
  A 2-servo universal joint **cannot reach the full 0–180** (it binds near the
  middle), so every joint is clamped to `[min,max]` (default **30–150**). The
  servo itself still runs 0–180 — the gear maps joint→servo on the robot.
  Sliders, dragging, IK and playback all respect the joint limits.
- **axis** per joint — which way the joint rotates: **roll (X), pitch (Y) or
  yaw (Z)**. Pick the one that matches how your servo is mounted (not just
  invert — the whole axis is selectable).
- **axis tilt (° roll/pitch/yaw)** per joint — a real universal joint's two
  axes aren't exactly aligned to X/Y/Z or exactly 90° apart. Nudge each
  joint's rotation axis in degrees (roll/pitch/yaw) so the model matches the
  real shoulder/elbow. 0/0/0 = no tilt (the default).
- **servo & gear — per joint.** Every joint can carry a **different servo**.
  As built the nong uses **PDI-1181MG (270°) in the shoulders through 15 : 18**,
  **MG90S (180°) in the elbows through 12 : 13**, a **TianKongRC 35 kg (270°)**
  on the waist and an **MG90S (180°)** on the shrug (both 1 : 1). Each row sets
  that one joint's `pinion : gear`, its servo `pulse min / pulse max` (µs), its
  `max °/s` and its **`travel°`**. The **preset** dropdown fills a whole group
  at once (MG90S, PDI-1181MG, TianKongRC 35kg, generic 180°, generic 270° →
  shoulders / elbows / waist / shrug / all) — or type the numbers yourself for a
  servo that isn't in the list. The editor
  works in joint degrees; the gear is applied **on the robot** (firmware sends
  `servo = travel/2 + (joint − 90) × gear/pinion` using that joint's own ratio
  and travel), so each servo uses its full travel while the joint stays in its
  smaller range. Swap a servo later: change that joint's row and push.
- **`travel°` — 180° or 270° servos.** This is how far the **servo** turns end
  to end (a property of the servo you bought), **not** how far the joint may
  turn (that's `min°`/`max°` above). Fitting a 270° servo is this one number:
  **every saved pose and sequence keeps working**, because they are all in
  joint degrees, and joint 90 sits at the middle of the travel either way, so
  the arm doesn't move at home. Each joint is independent — a 270° shoulder
  next to a 180° elbow is fine. The editor **warns under a joint's row** when
  the gear ratio and the joint's `min°`/`max°` ask for more servo travel than
  the servo has, and tells you how far the joint would actually get; on the
  robot the firmware clamps, so without the warning the joint would silently
  stop short. After pushing a travel change, check the arm away from home and
  re-run **Set zero** if it needs re-trimming.
- **inv** per joint — flip a joint that rotates the wrong way.
- **sizes (mm radius)** — **each joint ball and each bar can be a different
  size**: per universal joint (L shoulder / L elbow / R shoulder / R elbow) set
  the joint ball radius and the thickness of the bar hanging from it. The
  gizmo rings scale with the joint, and the crash check uses the real bar
  thickness.
- **dimensions (mm)** — shoulder position, arm segment **lengths** (separate
  left/right upper arm and forearm), torso size.

**Send to the robot:** *⬆ Send limits + gear to robot* pushes these to the
connected module (over WiFi or USB/RS485) one joint at a time — `LIMIT`,
`GEAR`, `PULSE` and `RANGE` per joint; the module clamps to them and saves
them to its SD card (`/data/nong_cal.yaml`), so they survive a reboot.
*⬇ Read from robot* pulls the module's current values back into the editor.

Every change applies to the 3D model instantly, is remembered by the browser,
and is saved inside each project file.

## Your own 3D model (STL from SolidWorks)

Export each body part as a separate STL in **mm** (conventions: part origin
at its joint, arm pointing down −Y). Two ways to load it:

1. **Model card → choose file → Import** — the app copies it into `models/`
   for you, or
2. drop the files into the `models/` folder yourself and press **⟳**.

Then **assign each file to a body part** (torso / head / L_upper / L_fore /
R_upper / R_fore) in the same card. Parts without a file keep the built-in
shapes — the joint math is identical either way. Also:

- the **yellow joint balls and bone lines never disappear** — even with STLs
  on, you always see where the joints are and how long each segment is;
- assigning an STL **measures its real size and sets the rig lengths**
  (upper arm / forearm / torso) automatically — the model follows your parts;
- if the STL was exported with a different origin/orientation, use the
  **rot (deg) / off (mm) / scale** boxes that appear under the part;
- each part has a **color** swatch;
- **Clothes / add-ons**: import any extra STL (shirt, hat, decoration), attach
  it to a body part with its own transform — it moves with that part and
  covers it without replacing the skeleton. Add as many pieces as you like.

Everything is remembered by the browser and saved inside project files.

## Crash check (self-collision)

Before anything runs on the real robot the sequence is checked for
self-collisions — arms against the body, the head, and each other — at every
keyframe **and along the path between keyframes** (the same eased path the
robot drives). If a collision is found:

- a popup says **"CAN'T RUN — the robot will crash"** with the reason,
- the offending keyframes turn **red** in the timeline with the reason on
  the chip (e.g. "left forearm hits the body (during the move)"),
- **Run on robot** and **Upload** are blocked until it's fixed; ▶ Play still
  works so you can watch where it goes wrong, and while posing a red banner
  appears in the viewport the moment the current pose collides.

Fix it by editing the red keyframe, or add an in-between keyframe that
steers around the obstacle, then press **⚠ Check crash** again.

## Files

```
main.py          local server (stdlib only) + robot proxy
save_patch.py    save/list/restore preserved snapshots of the web app (below)
web/             the editor app (index.html, app.js, style.css, vendor/three.js)
patches/         numbered snapshots of the web app — old versions are kept
projects/        saved editor projects (.json)  — Save/Load in the top bar
sequences/       exported .yaml sequences       — copy these to the SD card /moves/
models/          your STL exports (mm)
```

## Patches — the web app is versioned, old versions never disappear

Every change to the web app is saved as a numbered **patch** so nothing is ever
lost:

```
python save_patch.py "what this change did"   # save the current web/ as the next patch
python save_patch.py --list                    # list every saved patch
python save_patch.py --restore 3               # roll web/ back to patch 0003
```

Each patch is one snapshot in `patches/NNNN_<name>/` (app.js, index.html,
style.css) plus a row in `PATCHES.md`. Patches are append-only — a new one
never overwrites an old one, and `--restore` auto-saves the current version
first, so you can always go back.

## Joint order (everywhere: editor, firmware, YAML)

```
1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P  8 R_EL_R  9 WAIST  10 SHRUG
```

Exported step: `- pose: "90 45 120 90 90 135 60 90 60 90 T 800"` → the firmware
(`code/firmware`, module type `nong`) interpolates all 10 servos over `T` ms.
(An older 8-value step still plays — WAIST/SHRUG stay at neutral.)
Multiple ESP32 boards (e.g. one per arm) stay in sync because every step
carries an explicit `T` and the leader board re-broadcasts it on RS485 —
see `code/firmware/COMMANDS.md`, section "Multi-ESP humanoid (link mode)".
