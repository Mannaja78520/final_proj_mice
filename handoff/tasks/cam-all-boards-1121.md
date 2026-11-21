# Camera firmware for every camera board (ESP32 and ESP32-S3)

Owner: claude (cloud thread "Support every camera board in firmware")
Updated: 2026-11-21
Branch: claude/project-thread-66drm1 (on top of claude/project-thread-xgdvmp, PR #151)

## Goal
User 2026-11-21: "เอา cam ให้ใช้ได้กับทุกกล้อง ... cam s3 ได้ด้วย ... เลือกก็ได้ auto ก็ได้".

## Done
- Merged PR #151 branch (chip field, 3 S3 boards, mice_cam_s3 env).
- gen_tables.py: CAM_CHIP_RULES + cam_check_pins refuse duplicate GPIOs, flash/PSRAM/USB lines, input-only outputs, unknown chip.
- cam_boards.json: fixed ttgo-journal (GPIO 36 twice), added wrover-kit and esp32s3-cam-lcd.
- CamModule: `CAM BOARD [<name>|AUTO]` stored in NVS "cam"/"board", tried first at boot, others still tried; order logic in CamPick.h.
- Tests: 4 native tests (54 pass), qc/checks/check_cam_boards_data.py, check_camera updated.
- `pio run -e mice_cam` and `-e mice_cam_s3` build (cloud, 2026-11-21).

## Not tested on hardware
All pin maps except ai-thinker/esp-eye. See lab-day.md section 4b.
No QEMU for cam: QEMU has no camera model; native tests cover the choice logic only.
