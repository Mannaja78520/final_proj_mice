# Panel review - 2026-08-24 03:22

**Question.** A21-1 puts two rules into CLAUDE.md: every screen is for a designer not a programmer; anything the user asks goes into the plan STATE block the moment it is asked, before work starts. It also adds qc/checks/check_designer_first.py holding rule 1. Proposal: banned-word list in DATA at qc/data/designer_words.json shaped {banned:[exception,traceback,stack trace,stderr,stdout,status code,http 500,undefined,nan,payload,regex], allow_files:[main_python/web/help.html]} - help.html is technical by job until A21-4 rewrites it. The check strips script/style/comment blocks then scans remaining text of every served page (main_python/web/*.html, apps/*/index.html, nong/main_python_set_nong/web/index.html) so JS identifiers never false-hit; adding a word costs no code. It also asserts both rules sit in CLAUDE.md so neither rots away. Measured today: hub/rgb/camera/voice/nong pages are clean against that list; only help.html trips it. What breaks this or makes it wrong? One finding per line, at most 12 lines.

**Files.** help.html, hub.html, rgb.html, app.json, index.html, app.json, bench/cases.json, bench/run_bench.py, index.html, qa_data.json, service.py, README.md, checks/check_advanced.py, checks/check_app_handout.py, checks/check_board_auth.py, checks/check_board_password.py, checks/check_boot_noise.py, checks/check_brownout_guard.py, checks/check_browser_budget.py, checks/check_build_split.py, checks/check_bus_dongle.py, checks/check_bus_flash.py, checks/check_bus_group.py, checks/check_calibration.py, checks/check_cam_controls.py, checks/check_cam_panel.py, checks/check_cam_viewers.py, checks/check_camera.py, checks/check_chatty_board.py, checks/check_connection.py, checks/check_contracts.py, checks/check_crash_gate.py, checks/check_danger.py, checks/check_design_system.py, checks/check_dev_tools.py, checks/check_diagnostics.py, checks/check_discovery.py, checks/check_docs.py, checks/check_edge_cases.py, checks/check_firmware_build.py, checks/check_flash.py, checks/check_flash_confirm.py, checks/check_flash_remote.py, checks/check_flash_type.py, checks/check_groups.py, checks/check_guards_armed.py, checks/check_help_links.py, checks/check_history.py, checks/check_hub_api.py, checks/check_hub_auth.py, checks/check_hub_clock.py, checks/check_hub_nav.py, checks/check_hub_pair.py, checks/check_hub_reach.py, checks/check_hub_users.py, checks/check_identity.py, checks/check_joint_fields.py, checks/check_joint_rules.py, checks/check_joint_select.py, checks/check_key_click.py, checks/check_key_clock.py, checks/check_keyboard_only.py, checks/check_latency.py, checks/check_line_protocol.py, checks/check_link_states.py, checks/check_livedoc.py, checks/check_logging.py, checks/check_mdns.py, checks/check_modsite_back.py, checks/check_modsite_errors.py, checks/check_modsite_glance.py, ...and 85 more under qc
**Cost.** 267398 tokens across 3 models

## The head reviewer (gemini-3.1-pro-high)

 - **unchecked** `:` nong/main_python_set_nong/web/app.js real, check globs html only, JS strings bypass check.
 - **unchecked** `:` apps/*/index.html real, check strips <script>, dynamic error strings bypass check.
 - **unchecked** `:` qc/checks/check_designer_first.py:1 real, check strips <script>, dynamic UI text bypasses check.
 - **unchecked** `:` qc/checks/check_designer_first.py:1 real, check ignores API layer, backend errors bypass check.
 - **unchecked** `:` CLAUDE.md:353 real, check scans hidden elements, prevents hiding diagnostics behind toggle.
 - **unchecked** `:` qc/checks/check_designer_first.py real, check asserts plan rule, violates single concern in CLAUDE.md:337.
 - **unchecked** `:` qc/checks/check_designer_first.py:1 maybe, check verifies text exists, cannot ensure agent updates STATE block.
 - **unchecked** `:` qc/data/designer_words.json maybe, allow_files ignores whole file, future forbidden terms bypass help.html.

## What each model said

### gemini-3.1-pro-high  _(38.9s, 22553 tokens)_

 - **real** `qc/checks/check_designer_first.py:1` strips scripts, misses UI text rendered dynamically by JS
 - **real** `qc/checks/check_designer_first.py:1` ignores API layer, backend errors shown on screen bypass check
 - **real** `qc/checks/check_designer_first.py:1` verifies CLAUDE.md text, fails to ensure agent actually updates STATE block
 - **real** `qc/data/designer_words.json:1` lacks word boundaries, nan matches banana
 - **real** `qc/data/designer_words.json:1` hardcodes HTML globs, new UI directories silently bypass validation
 - **real** `qc/data/designer_words.json:1` uses exact allow paths, moving help.html breaks whitelist

### gemini-3.7-flash-high  _(168.2s, 148224 tokens)_

 - **unchecked** `:` `firmware/src/web/WebUI.h:31`: check scans only `.html` files, misses module website served over WiFi and USB.
 - **unchecked** `:` `apps/*/index.html`: stripping `<script>` ignores dynamic DOM updates, runtime error strings bypass check undetected.
 - **unchecked** `:` `nong/main_python_set_nong/web/app.js`: check ignores external JS files, UI text in standalone scripts never scanned.
 - **unchecked** `:` `CLAUDE.md:353`: static text ban blocks technical switch content, prevents hiding diagnostics behind toggle.
 - **unchecked** `:` `main_python/web/help.html:118`: "exception" matches valid English prose, causes false failure on non-programming usage.
 - **unchecked** `:` `qc/checks/check_designer_first.py`: asserts plan STATE block rule in UI check, violates single concern rule in `CLAUDE.md:337`.
 - **unchecked** `:` `CLAUDE.md:33`: both rules already exist in `CLAUDE.md:33` and `CLAUDE.md:346`, task A21-1 premise is redundant.
 - **unchecked** `:` `qc/data/designer_words.json`: `allow_files` ignores whole file, lets future forbidden terms bypass `help.html` undetected.
