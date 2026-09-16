# Panel review - 2026-08-25 17:28

**Question.** A22-1 triage. Read docs/a22_sweep_findings.json - a code sweep found 60 confirmed findings. For each finding NOT yet fixed, judge REAL or FALSE by reading the actual code it names, one line of reason each. AI models sometimes report false bugs, so be strict: a finding is REAL only if the code truly behaves badly as described. Cover especially: firmware/src/web/WebUI.h module site, main_python/main.py auth surface, shared/web/mice.js, nong studio app.js, help accuracy. End with the 5 most damaging REAL findings.

**Files.** CHANGELOG.md, CLAUDE.md, NEXT_SESSION.doc.js, NEXT_SESSION.html, NEXT_SESSION.md, PATCHES.md, README.md, apps/camera/app.json, apps/camera/index.html, apps/help/app.json, apps/studio/app.json, apps/voice/app.json, apps/voice/bench/cases.json, apps/voice/bench/run_bench.py, apps/voice/index.html, apps/voice/qa_data.json, apps/voice/service.py, auto_click/auto_click.py, config/voice.json, docs/DIARY.md, docs/PLAN.html, docs/TWO_WEEKS_27JUL-10AUG.md, docs/architecture/README.md, docs/architecture/firmware.md, docs/architecture/hub.md, docs/architecture/web.md, docs/panel_a20_1.md, docs/panel_a20_10.md, docs/panel_a20_11.md, docs/panel_a20_11_design.md, docs/panel_a20_12.md, docs/panel_a20_12_design.md, docs/panel_a20_2.md, docs/panel_a20_5.md, docs/panel_a20_6.md, docs/panel_a20_7.md, docs/panel_a20_7_design.md, docs/panel_a20_7_mic.md, docs/panel_a20_8.md, docs/panel_a20_9.md, docs/panel_a20_9_design.md, docs/panel_a21_1_design.md, docs/panel_a21_2_design.md, firmware/CLAUDE.md, firmware/COMMANDS.md, firmware/PATCHES.md, firmware/README.md, firmware/config/PIDF_config.h, firmware/config/cam_boards.json, firmware/config/cam_controls.json, firmware/config/commands.json, firmware/config/conf_network.h, firmware/config/config.h, firmware/config/esp32_hardware.h, firmware/config/esp32_hardware_cam_module.h, firmware/config/esp32_hardware_lift_module.h, firmware/config/esp32_hardware_nong_module.h, firmware/config/modules.json, firmware/config/servos.json, firmware/lib/Encoder/Encoder.cpp, ...and 4124 more under .staging
**Cost.** 801123 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:4188` /api/stopall blocks on USB scan lock before sending MOVE STOP, delaying emergency halt.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:4148` hub_auth.GATED omits /api/flash/bus, allowing unauthenticated firmware overwrite.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/WebPortal.cpp:658` WebSocket /ws passes text to router without auth, allowing unauthenticated command execution.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/WebPortal.cpp:823` Body handler writes to SD card before auth check, allowing unauthenticated disk writes.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:3855` time field allows path traversal, writing JSON files outside reports directory.
 - **real** `E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js:2261` i > 0 condition drops speed override on first move, making robot run at default speed.
 - **fine** `E:/final_proj/mice/code/.staging/firmware/src/web/WebUI.h:1` File is fine.
 - **fine** `E:/final_proj/mice/code/.staging/shared/web/mice.js:1` File is fine.

## What each model said

### gemini-3.1-pro-high  _(149.1s, 119680 tokens)_

 - (nothing to report)

### gemini-3.7-flash-high  _(278.1s, 508982 tokens)_

 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/WebPortal.cpp:658` WebSocket /ws executes commands directly through router without login check.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:4148` POST /api/flash/bus omitted from hub_auth.GATED, allowing unauthenticated firmware overwrite.
 - **real** `E:/final_proj/mice/code/.staging/firmware/src/core/WebPortal.cpp:823` /api/upload writes file to SD card in body handler before checking auth.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:3855` POST /api/report time field path traversal writes JSON files outside reports/.
 - **real** `E:/final_proj/mice/code/.staging/main_python/main.py:4188` Emergency /api/stopall blocks on 20s USB scan lock before sending MOVE STOP.
 - **fine** `E:/final_proj/mice/code/.staging/firmware/src/web/WebUI.h:1` WebUI.h is fine.
 - **fine** `E:/final_proj/mice/code/.staging/shared/web/mice.js:1` mice.js is fine.
 - **fine** `E:/final_proj/mice/code/.staging/nong/main_python_set_nong/web/app.js:2261` buildYaml speed override on move index 1 works correctly.
