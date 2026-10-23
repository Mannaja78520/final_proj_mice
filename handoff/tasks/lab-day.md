# Lab day: every test that needs a board, the robot or a person

Owner:
Updated: 2026-10-23 03:28 (Bangkok)
Branch: main
Last commit: see git log
Plan: A47-13 (this list), and the ids on each line

## Goal
User 2026-10-22 20:19Z: "ทำทุกอย่างเท่าที่ทำได้ก่อนเลยนะไม่ต้องรอบอร์ดอย่างเดียวบอร์ดมาค่อยแก้ทีเดียว"
(do everything possible first; boards come later and get fixed in one go).
Everything that does not need a board is done or waits on the user/friend (see
"Not hardware" below). This file is the ONE checklist for the combined lab
session (lab until 21:00 Thai). Tick a line here and write the measurement into
the plan task it names. Detail for a line lives in the file it points to.

## Doing now
nothing - waiting for the lab.

## Facts found
- Nothing is flashed or measured since 2026-10-12; all code below is tested against fakes only.
- The gachapon and the lift have NO encoder (user 2026-10-22, A47-12). The lift starts with
  `LIFT_HAS_ENCODER 0` (firmware/config/esp32_hardware_lift_module.h): GOTO reaches only the
  bottom and top stage. "CFG encoder 1" turns it back on if one is fitted.

## Next (in this order on the day)

### 0. PC first (no robot needed, 10 min)
- [ ] `git pull` main, `python tools/systems.py build`, rebuild MiceHub.exe with
      `python -m PyInstaller --clean --noconfirm MiceHub.spec`, restart, check /api/version.
- [ ] Gachapon hub: open /app/gacha/ and /app/all-jao/, spin the wheel, see the toast (gachapon.md Next 1).
- [ ] Friend's face app + our faces watcher + Photobooth together; time a name per source
      (friend-face-server.md).

### 1. Gachapon board (A47-5, gachapon.md Next 2)
- [ ] Flash `mice_gacha` (USB or OTA); PIN motor_a/motor_b if not 25/26; hall on GPIO33.
- [ ] Slots = 4 (CAD). Measure how many pockets until a ball drops (GCFG drop; default 2).
- [ ] Motor speed and settle time; a jam stops it (hall timeout, no encoder).
- [ ] Add the machine on Prize machines; one real dispense from the hub, from Voice, from a game win.

### 2. Nong robot (hotspot "manny", RS485 COM21) - robot-tests.md, robot-hotspot-live.md
- [ ] A45-11 / robot-tests.md 1-5: palm flip per hand, last.yaml from http://nong.local/,
      OTA, TALK ON with the phone mic after reboot, video sound on the robot.
- [ ] A46-2: saved motions, speech gestures / RRT detours, video copying, skeleton - small moves first.
- [ ] A26-99: play LhongMarePing, read PERF? right after the song starts.
- [ ] A26-77: anything still untested from the 2026-09-21 hardware list.
- [ ] A48-6 / robot-tests.md 7: Studio rig with the CAD's sizes and shoulder spots: put the robot
      at home and at 3 poses, compare with Studio (simple shapes and CAD model). If the real arms
      match the CAD better, add "joints" to urdf_view.json rigFromCad and press the button again.
- [ ] A26-71: shrug angle at full left / middle (90) / full right -> calibrate, save PDF.
- [ ] A26-92: RELAX not releasing TD8135MG (user: diagnose only, do not fix yet).
- [ ] A16-1: the 4-bar's own curve with a ruler.
- [ ] A20-3: one nong on two ESP32 boards (link + peer), needs 2 boards + RS485 pair.

### 3. Lift board
- [ ] A7-8 / A24-10: RGB strip (RGB 255 0 0, RGB EFFECT rainbow) and speaker (PLAY, VOL).
- [ ] Lift has no encoder: UP / DOWN to the limit switches, GOTO 0 and GOTO top only.

### 4. Several devices
- [ ] A13-8: update a module from a phone on WiFi.
- [ ] A13-4: second PC on the same WiFi.
- [ ] A9-2 / A9-3 (optional): TV legibility at 3 m, keyboard / remote only.

### 5. A person at the PC (person-tests.md, voice-human-tone.md)
- [ ] Real microphone: 3 Thai lines, what it heard, time to sound; room echo with the robot speaker.
- [ ] Camera-to-name time with an enrolled person (A45-12).
- [ ] Listen to the voice feeling samples; change Speaking manner if one sounds wrong.

## Not hardware, waits on someone else (not for the lab)
- A45-10 / voice-keys.md: the user's own Google AI Studio and Groq keys.
- Friend: docs/gacha/friend_requests.md (Thai list already sent through the user).
- A26-73 dropped (thesis only). A31-8 dropped: GPT made the URDF; A48-1 (Studio URDF view) uses it.
- A31-11 ai_panel / A0-33 bypass: user's tool settings.
- Thesis rows A21-17, A31-32: dropped (user 2026-10-12: no thesis work).

## Blocked
- Boards, the robot and a person: the user's lab time.
