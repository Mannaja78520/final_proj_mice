# Firmware test cases: ESP32 QEMU sim and fakes

Brainstormed 2026-11-22. SIM = runnable now in QEMU (`*_sim` envs, `qc/lib/qemu_board.py`, `~PIN/~ADC/~PWM?` hooks in `firmware/src/sim/MiceSim.h`) or fake serial / native tests. LAB = needs real hardware or a radio (goes to the lab list). QEMU has no WiFi radio, ESP-NOW, SD, audio, servos or real hall pulses. Code citations were grepped, not exhaustively read. Note: RS485 lines carry no CRC (grep of RS485Bus.cpp found none): integrity is md5 on firmware, base64 validity, and an 8-byte tag on mesh frames.

| ID | Area | Steps | Expected | SIM/LAB | How to automate |
|---|---|---|---|---|---|
| FW-001 | Boot | Flash seeded image (id 7, nong) in QEMU, read UART | `[boot] ready` printed, `INFO` shows id 7 type nong | SIM | qemu_board; extend check_qemu_firmware (firmware/src/main.cpp, core/Identity.cpp) |
| FW-002 | Boot | Boot each of mice_nong/lift/gacha/dummy/blank `_sim` env | Each reaches `[boot] ready` with its own type in INFO; blank has no module verbs | SIM | parametrise check_qemu_firmware over envs in platformio.ini |
| FW-003 | Boot | Boot mice_cam in QEMU | Cannot: ESP32-CAM driver needs a sensor; boot reaches core ready, CAM verbs answer an error not a crash | LAB | real board; QEMU has no camera (CamModule.cpp) |
| FW-004 | Boot | Boot with blank NVS (no identity) | Default id = efuse MAC derived 1..247, type blank, no crash (Identity.cpp:25) | SIM | flash image with NVS erased |
| FW-005 | Boot | Boot with NVS id byte 0 or 255 (corrupt) | Id clamped into 1..247 (Identity.cpp:103), never answers as 0 | SIM | seed NVS via qemu_board nvs builder, then INFO |
| FW-006 | Boot | Boot with stored type not compiled into this binary (lift in nong build) | Falls back to blank/known type, boots, no loop reset | SIM | seed NVS type=lift on nong image |
| FW-007 | Boot | `SET TYPE lift` on nong build | Replies `ERR unknown type (nong,blank)` (CommandRouter.cpp:274) | SIM | serial command, assert reply |
| FW-008 | Boot | `SET TYPE nong` then reboot | Type persists across reboot and module starts | SIM | send, `REBOOT`, re-read INFO |
| FW-009 | Boot | Count resets via `PERF?` after software reboot | reset reason `reboot`, counter +1 (Perf.cpp) | SIM | PERF? before/after |
| FW-010 | Boot | Boot loop timing: time from reset to ready | Under budget (e.g. 5 s) in QEMU; regression guard only | SIM | timestamp UART output |
| FW-011 | Boot | Brownout reset behaviour | BrownoutGuard marks brownout, boot into safe state (BrownoutGuard.cpp) | LAB | power supply dip with bench PSU |
| FW-012 | Boot | PERF? fields present (loop, heap, stack, lock_by, resets) | All keys present and numeric | SIM | parse reply |
| FW-013 | WiFi/AP | Board with no saved WiFi starts its own AP with SSID from id/name | AP visible; AP pass 8-63 chars | LAB | needs radio; QEMU has no WiFi (WebPortal.cpp) |
| FW-014 | WiFi/AP | `SET WIFI "ssid" pass` then reboot, router in range | Joins router, gets IP, `INFO` shows IP | LAB | real router |
| FW-015 | WiFi/AP | `SET WIFI "my ssid"` (no pass) open network | Accepted, joins open net | LAB | real AP |
| FW-016 | WiFi/AP | `SET WIFI` with no args | `ERR need an ssid` (CommandRouter.cpp:332) | SIM | serial command |
| FW-017 | WiFi/AP | AP password shorter than 8, longer than 63, with spaces | `ERR 8-63 characters, no spaces` (CommandRouter.cpp:181) | SIM | serial `SET APPASS` |
| FW-018 | WiFi/AP | Router vanishes mid-session | Board keeps servo/RS485 loop running, falls back to AP, no reboot (W_ONLINE watchdog, WebPortal.cpp:1399) | LAB | switch router off |
| FW-019 | WiFi/AP | Wrong WiFi password stored | Board does not lock boot; AP reachable for fixing | LAB | real radio |
| FW-020 | WiFi/AP | PEERPASS wrong arg count / bad name | `ERR usage` / `ERR bad name or password (8-63, no spaces)` (CommandRouter.cpp:211) | SIM | serial |
| FW-021 | WiFi/AP | Command that needs WiFi on a no-radio sim build (`REACH`, `MESH`) | `ERR no radio on this build` or usage error, no crash | SIM | serial; (WebPortal::instance null) |
| FW-022 | WiFi/AP | REACH through busy module | `ERR busy` while moving (WebPortal.cpp:372) | SIM | start POSE then REACH (needs radio hooks) else fake-wire unit via native env |
| FW-023 | WiFi/AP | 20 phones join AP at once | Page still loads, servo frames stay on 50 Hz | LAB | many clients, PERF? loop gap |
| FW-024 | Web | GET `/` returns board page with header, three tabs Move it / Shows & files / Setup & wiring | All tabs present, only cards of this type shown (WebUI.h:142) | SIM | fake board HTTP server serving generated page, qc browser check (check_responsive pattern) |
| FW-025 | Web | Newcomer walk-through step 1: open page, English only, no jargon on first tab | No banned words (qc/data/designer_words.json); no non-ASCII language strings | SIM | check_designer_first on generated ModuleUI.h |
| FW-026 | Web | Newcomer walk-through step 2: log in (loginCard) with default account | Login works, cards unlock; wrong pass refused | SIM | check_board_auth / check_accounts_firmware against fake |
| FW-027 | Web | Newcomer step 3: Move it tab, press a pose/move button | Command reaches module (`fake_serial.wire`), UI shows result in plain words | SIM | browser click, assert wire |
| FW-028 | Web | Newcomer step 4: Shows & files tab, upload a small sequence file | File listed, then play works | SIM | fake /api/upload with browser |
| FW-029 | Web | Newcomer step 5: Setup & wiring tab, rename board, change id | Rename persisted, id change warns about collisions | SIM | fake board, assert SET NAME/ID wire |
| FW-030 | Web | Technical details hidden by default (ids, ports, errors) | Behind the technical switch only | SIM | check_designer_first |
| FW-031 | Web | Per-type cards: nong build has no liftCard/gachaCard/camCard | Guarded blocks `<!--#type-->` stripped (gen_tables.py) | SIM | inspect generated `.pio/build/<env>/generated` |
| FW-032 | Web | mice_blank page | Only core cards, no module controls | SIM | gen_tables --types blank |
| FW-033 | Web | Page size vs flash slot | Generated page fits, each env under OTA slot (check_ota) | SIM | existing check_ota |
| FW-034 | Web | `/api/status`, `/api/peers`, `/api/whoami` JSON shape | Valid JSON, expected keys | SIM | fake board contract test |
| FW-035 | Web | `/api/cmd?c=` with malformed/very long/URL-encoded junk | One reply line, 4xx on empty, no crash (WebPortal.cpp:873) | LAB | HTTP needs radio; logic unit via fake |
| FW-036 | Web | `/api/download` path traversal `../` | Refused | SIM | fake handler / native test of path sanitiser |
| FW-037 | Web | `/api/delete` of nonexistent file | Plain error | LAB | needs SD |
| FW-038 | Web | `/api/upload` interrupted mid-file | Partial file removed or flagged, no corruption | LAB | SD + WiFi |
| FW-039 | Web | `/api/cam.jpg` and `/api/cam.stream` on cam build | Frames served; 503-style when camera absent | LAB | real ESP32-CAM |
| FW-040 | Web | Unknown URL | Friendly 404 via onNotFound (WebPortal.cpp:1261) | LAB | WiFi |
| FW-041 | Web | Session cookie expiry and logout | `/api/logout` clears it, next cmd needs login | SIM | check_board_auth |
| FW-042 | Web | Two browsers command at once | Router lock serialises, replies not interleaved (fw-core one reply line rule) | SIM | two fake clients on fake_serial |
| FW-043 | Web | Help parity: help.html covers every card in WebUI.h | Rule 11 parity | SIM | existing help QC checks |
| FW-044 | RS485 | Valid `#7 PING` on bus | `@7 PONG`-style reply, one line | SIM | check_qemu_bus |
| FW-045 | RS485 | Command for id nobody has | Ignored silently, module unharmed (check_qemu_bus) | SIM | existing |
| FW-046 | RS485 | Broadcast `#* PING` census with 3 boards | Answers in id order with id*6 ms gap (BusSlot.h) | SIM | check_qemu_census |
| FW-047 | RS485 | `#* PING` with 255 boards | Last answers at ~1530 ms, none overlap | LAB | needs many boards; model only in SIM (tools/bench/bus_census_model.py) |
| FW-048 | RS485 | Line with no terminator (partial frame) then silence | No action; buffer kept until `\n` or cleared on >4096 (RS485Bus.cpp:80) | SIM | write half a line on Rs485Bus, then valid line, assert both behave |
| FW-049 | RS485 | Partial frame then valid frame appended (no newline between) | Treated as one garbage line, ERR or ignore, next line OK | SIM | Rs485Bus inject |
| FW-050 | RS485 | Line longer than 4096 bytes | Buffer wiped, tail only; board alive (RS485Bus.cpp:76-80) | SIM | inject 5000 bytes, then PING |
| FW-051 | RS485 | Reply longer than 4096 from bridging board | Dropped by next reader (fw-core note, AMP VALID) | SIM | check_amp_kind style on QEMU |
| FW-052 | RS485 | Binary garbage including NUL bytes | Ignored, no crash, PING still answered after (NUL from framing error, RS485Bus.cpp:279) | SIM | random bytes from Rs485Bus |
| FW-053 | RS485 | Lone `\r`, `\r\n` endings, empty lines | Handled, empty line ignored | SIM | inject |
| FW-054 | RS485 | Invalid UTF-8 / 0xFF bytes in command | No crash, `ERR` or ignore | SIM | inject |
| FW-055 | RS485 | Missing id: `# PING`, `#abc PING`, `#999 PING`, `#-1 PING` | Ignored or ERR, never executed | SIM | inject, check wire silent |
| FW-056 | RS485 | Id 0 and 248-255 addressed | Not answered by id-validated boards (valid 1..247) | SIM | inject |
| FW-057 | RS485 | No CRC on lines: flipped bit in command text | Documented: executed as-is (plain text) or ERR; test pins the behaviour | SIM | inject mutated lines; note no CRC exists in RS485Bus.cpp (grep found none) |
| FW-058 | RS485 | Corrupt base64 in FWDATA | `ERR chunk is not valid base64` (BusUpdate.cpp:75) | SIM | check_qemu_firmware |
| FW-059 | RS485 | Two boards with the same id | Both answer same slot; test pins that census detects duplicate and `#~<chip>` addressing can fix (RS485Bus.cpp:52) | SIM | two QEMU gachas same id, `#~chip SET ID` |
| FW-060 | RS485 | Collision resolved by chip-address `SET ID` | Only that chip changes id, persisted | SIM | check_qemu_bus extension |
| FW-061 | RS485 | Gateway path `#>12>7 CMD` with wrong first hop | Ignored (RS485Bus.cpp:67) | SIM | 3 boards |
| FW-062 | RS485 | Gateway path deeper than limit / loop `#>7>7>7` | No endless forward | SIM | 3 boards |
| FW-063 | RS485 | Driver enable hold: TX end does not corrupt last byte | No NUL byte at end of frames (RS485_HOLD_US) | LAB | logic analyser; QEMU UART is unpaced |
| FW-064 | RS485 | Two tasks send at once | Frames never interleave (sendMtx_) | SIM | check_rs485_frame (existing) |
| FW-065 | RS485 | Bus at wrong baud on one board | Garbage ignored, others unaffected | LAB | real transceivers |
| FW-066 | RS485 | Bus shorted / floating (no termination) noise | Board stays responsive | LAB | real wire |
| FW-067 | RS485 | 100 commands back to back | All answered once, in order, no lost reply | SIM | check_qemu_bus loop |
| FW-068 | RS485 | Command while module moving | `ERR busy` or queued as documented | SIM | POSE then command on bus |
| FW-069 | Router | Empty line / whitespace only | `ERR empty` (CommandRouter.cpp:116) | SIM | serial |
| FW-070 | Router | 17+ words in a command | `ERR too many words (max 16)` (CommandRouter.cpp:115) | SIM | serial |
| FW-071 | Router | Unknown command | `ERR unknown cmd` | SIM | check_qemu_firmware |
| FW-072 | Router | Very long USB line (10 KB) | One error or ignored, alive | SIM | serial |
| FW-073 | Router | Command with unmatched quotes `SET WIFI "abc` | Clean ERR, no crash | SIM | serial |
| FW-074 | Router | Case variations `ping`, `Ping` | As documented in COMMANDS.md | SIM | serial |
| FW-075 | Router | SET ID 0, 248, -3, abc, 1.5 | `ERR id must be 1-247` (CommandRouter.cpp:263) | SIM | serial |
| FW-076 | Router | SET NAME 33+ chars, empty, with quotes | Refused / trimmed per docs (CommandRouter.cpp:157) | SIM | serial |
| FW-077 | Router | SET MESH/RELAY with bad word | `ERR usage` (CommandRouter.cpp:284,292) | SIM | serial |
| FW-078 | Router | Every verb in commands.json with no args | Answers one `ERR usage` line, none crash | SIM | iterate config/commands.json, serial |
| FW-079 | Router | Every verb with args out of range (NaN, huge, negative) | Clamped or ERR, no watchdog reset | SIM | fuzz over commands.json |
| FW-080 | Router | Reply written in one call under USB log spam | No log line lands inside a reply (writeOnce) | SIM | enable debug logs, assert reply line intact |
| FW-081 | Router | Lock held by slow task | `PERF?` lock_by names holder | SIM | PERF? |
| FW-082 | OTA | FWBEGIN without md5 | Refused (BusUpdate.cpp:42) | SIM | check_qemu_firmware |
| FW-083 | OTA | FWBEGIN md5 not 32 hex | `ERR that md5 is not 32 hex characters` | SIM | serial |
| FW-084 | OTA | FWBEGIN size 0 / 0xFFFFFFFF / larger than slot | `ERR no room` / needs size | SIM | serial |
| FW-085 | OTA | FWDATA out of order, short, too long, bad length token | Each refused; old firmware keeps running (BusUpdate.cpp:61-102) | SIM | check_qemu_firmware |
| FW-086 | OTA | FWDATA without FWBEGIN, FWEND without FWBEGIN | `ERR no update started` | SIM | serial |
| FW-087 | OTA | FWEND with fewer bytes than promised | `ERR only N of M` | SIM | serial |
| FW-088 | OTA | FWEND wrong md5 | Refused, board stays on old slot | SIM | check_qemu_firmware |
| FW-089 | OTA | Valid full image over bus, reboot into other slot | `OK FWEND restarting`, boots new app slot | SIM | check_qemu_bus |
| FW-090 | OTA | Update over RS485 while target moves | Refuse or defer (flash write stalls servo) | SIM | POSE then FWBEGIN, observe |
| FW-091 | OTA | Second FWBEGIN while one running | Aborts the first cleanly, starts new | SIM | serial |
| FW-092 | OTA | Power cut mid-FWDATA | Boots old slot, no brick (two app slots, check_ota) | SIM | kill QEMU mid-update, reboot same flash image, INFO |
| FW-093 | OTA | Power cut during FWEND commit | Boots either old or new valid slot, never a broken one | SIM | kill QEMU at random point, repeat N times |
| FW-094 | OTA | Image for the wrong type (lift binary onto nong) | Accepted by md5 but board boots with identity mismatch; document behaviour | SIM | flash cross-type image, read INFO |
| FW-095 | OTA | HTTP `/api/ota` POST with valid image | Update, reboot, new version in INFO | LAB | needs WiFi (WebPortal.cpp:1158) |
| FW-096 | OTA | HTTP OTA without md5 / wrong md5 | Refused, `Update.abort()` (WebPortal.cpp:1217-1241) | LAB | WiFi; logic covered by check_ota against fake |
| FW-097 | OTA | HTTP OTA while module busy | `ERR busy` style refusal | LAB | WiFi |
| FW-098 | OTA | HTTP OTA, WiFi drops mid-upload | Old firmware keeps booting | LAB | walk away from AP |
| FW-099 | OTA | Image bigger than 1.875 MB slot | Refused before writing | SIM | check_ota size gate on every env |
| FW-100 | Servo | POSE within limits changes LEDC duty for joint 1 | Duty differs by expected amount | SIM | check_qemu_peripherals (~PWM?) |
| FW-101 | Servo | POSE beyond joint min/max | Clamped to limit, reply says so (JointRules.h) | SIM | ~PWM? duty equals clamped duty |
| FW-102 | Servo | POSE with NaN/inf/non-number angle | Refused, servo not moved | SIM | serial + ~PWM? |
| FW-103 | Servo | Negative speed, zero speed, huge speed | Clamped; zero does not divide by zero (NongMath.h ease) | SIM | serial + native tests |
| FW-104 | Servo | Change gear/pulse range then POSE | Duty follows new table `fields_` | SIM | serial |
| FW-105 | Servo | Limit config out of range (ConfigStore KeyMap lo/hi) | Rejected at ConfigStore.cpp:13 bounds | SIM | serial set + read back |
| FW-106 | Servo | All 10 joints commanded at once | Frames still 50 Hz, loop gap under budget | SIM | PERF? servo frame gap |
| FW-107 | Servo | STOP mid-move | Motion halts, `busy()` false | SIM | ~PWM? stable after STOP |
| FW-108 | Servo | Peer link forwards pose over RS485 to partner | Partner receives resolved pose | SIM | two-QEMU bus (check_qemu_bus) |
| FW-109 | Servo | Physical servo reaches angle, stalls, over-current | Behaves, no brownout | LAB | real servos, ammeter |
| FW-110 | Servo | Servo jitter at hold | Within tolerance | LAB | scope |
| FW-111 | Servo | Dummy pot-to-angle maths with ~ADC 0, 2048, 4095 | Angle monotonic, ends match calibration | SIM | check_qemu_peripherals |
| FW-112 | Builds | `pio run` each env: nong, lift, cam, cam_s3, blank, dummy, gacha | All compile; flash size under slot | SIM | check_firmware_build, check_build_split |
| FW-113 | Builds | Command table per type (`scope` in commands.json) | nong build rejects lift verbs `ERR unknown cmd` | SIM | serial on each _sim env |
| FW-114 | Builds | Type guard BuildTypes.h with no types | Compile error clear, not silent | SIM | pio compile with edited config (native) |
| FW-115 | Builds | Lift: HOME with both limits pressed | Fault latched until released (check_qemu_peripherals) | SIM | ~PIN |
| FW-116 | Builds | Lift: bottom limit ends HOME, zeroes stage | Motor pins released | SIM | ~PIN, ~PWM? |
| FW-117 | Builds | Lift: neither limit ever hit (timeout) | Fault after timeout, motor off | SIM | ~PIN none, wait |
| FW-118 | Builds | Lift: RGB strip refresh count | `~RGB?` increases on colour change | SIM | ~RGB? |
| FW-119 | Builds | Lift with encoder off by default | No encoder verbs/errors (check_no_encoder) | SIM | existing |
| FW-120 | Builds | Cam: board pin map entries valid | No missing pin / invalid GPIO (gen_tables) | SIM | check_cam_boards_data |
| FW-121 | Builds | Cam: real sensor init, JPEG quality, stream | Image returned, not noise | LAB | real ESP32-CAM |
| FW-122 | Builds | Cam: PSRAM absent | Clear error not crash | LAB | board without PSRAM |
| FW-123 | Builds | Blank: boots and answers core commands only | PING/INFO ok; module verbs error | SIM | mice_blank sim env |
| FW-124 | Builds | Module hot-change `SET TYPE` via bus then reboot | Factory builds the new module (ModuleTable.h generated) | SIM | two-board bus |
| FW-125 | Gacha | Dispense with hall pulse | Counted, stock -1, motor pins driven then released | SIM | check_qemu_peripherals (~PIN pulse) |
| FW-126 | Gacha | Dispense with no hall pulse | Finishes `jam` after timeout (GachaModule.cpp:353) | SIM | no ~PIN, wait timeoutMs_ |
| FW-127 | Gacha | Hall stuck high at start | Jam or refuse (hall_.stable check, line 114/219) | SIM | ~PIN 1 constantly |
| FW-128 | Gacha | Hall stuck low whole turn | Jam | SIM | ~PIN 0 |
| FW-129 | Gacha | Hall bounces (chatter 1-2 ms) | Debounced to one pocket count | SIM | ~PIN toggle fast, count==1 |
| FW-130 | Gacha | Hall pulse too short/long vs spanOnMs_ | Jam when advance span exceeds GACHA_ADVANCE_MAX_MS (line 197) | SIM | ~PIN timed pulses |
| FW-131 | Gacha | Pulse arrives after timeout | Reported jam, later pulse does not start motion | SIM | late ~PIN |
| FW-132 | Gacha | Stock 0 then GDISPENSE | Refused `empty`, motor not driven (A47-1) | SIM | serial + ~PWM? |
| FW-133 | Gacha | GSTOCK set to negative / huge / non-number | Rejected or clamped | SIM | serial |
| FW-134 | Gacha | Stock persists after reboot | Same count after power cycle | SIM | GSTOCK, reboot, read |
| FW-135 | Gacha | Closed (door) refuse | `ERR closed` when closed flag set | SIM | serial |
| FW-136 | Gacha | GDISPENSE twice quickly | Second refused busy, one turn only | SIM | serial pair |
| FW-137 | Gacha | STOP mid-dispense | Motor stops, state idle, stock unchanged | SIM | serial + ~PWM? |
| FW-138 | Gacha | Config change while dispensing (concurrency) | No crash, applied after (check_gacha_config_concurrency) | SIM | extend to QEMU |
| FW-139 | Gacha | Event total caps stock; random box weighted by counts | Hub logic correct (check_gacha_stock) | SIM | existing fakes |
| FW-140 | Gacha | Real magnet/pocket alignment, motor torque with prize | Prize drops, no double drop | LAB | real machine, 100-cycle soak |
| FW-141 | Gacha | Motor stall current / thermal | No overheat in soak | LAB | ammeter |
| FW-142 | Mesh | ESP-NOW broadcast frame accepted/dedup (src+seq ring) | Second copy ignored (MeshLogic.h) | SIM | native tests on MeshLogic.h |
| FW-143 | Mesh | Frame with bad 8-byte tag | Dropped | SIM | native MeshNode test |
| FW-144 | Mesh | Replay: seq more than 8 behind newest | Dropped (MeshLogic.h:26) | SIM | native |
| FW-145 | Mesh | Frame longer than MAX_FRAME (219) / len 0 | Ignored (MeshLink.cpp:35) | SIM | native |
| FW-146 | Mesh | TTL 0 / hop count 5 exhausted | Not relayed | SIM | native |
| FW-147 | Mesh | Sender reboot: seq must rise (seqStart in flash) | New frames accepted after reboot | SIM | native with persisted seqStart |
| FW-148 | Mesh | Reply longer than 200 bytes | Truncated with `...` (MeshLink.cpp:112) | SIM | native |
| FW-149 | Mesh | Retries stop after 3 (MAX_TRIES) | Wait slot freed | SIM | native |
| FW-150 | Mesh | `MESH * cmd` with 2 boards over radio | Both execute, replies return | LAB | two real boards (esp_now needs radio) |
| FW-151 | Mesh | Range and interference (WiFi channel clash) | Delivery rate acceptable | LAB | field test |
| FW-152 | Mesh | `SET MESH OFF` | Frames ignored and not sent | SIM | serial; wire check native |
| FW-153 | Persist | SET NAME, reboot | Name kept | SIM | QEMU reboot with same flash |
| FW-154 | Persist | ConfigStore value set, reboot | Value back (ConfigStore.cpp putFloat/getFloat) | SIM | serial + reboot |
| FW-155 | Persist | Config reset command removes all keys (ConfigStore.cpp:87) | Defaults restored | SIM | serial |
| FW-156 | Persist | Write NVS key out of bounds lo/hi | Rejected, old value kept | SIM | serial |
| FW-157 | Persist | NVS full / many writes (1000 SETs) | No crash; write wear note | SIM | loop in QEMU |
| FW-158 | Persist | Power cut mid NVS write | Board boots with old or new value, never garbage | SIM | kill QEMU while writing loop; read all keys valid |
| FW-159 | Persist | Power cut during SD sequence save | File absent or complete | LAB | real SD |
| FW-160 | Persist | Accounts/users store survive reboot (UserStore.cpp) | Login still works | SIM | check_accounts_firmware on QEMU |
| FW-161 | Persist | Corrupted NVS partition (random bytes) | Boot falls back to defaults, no loop | SIM | corrupt flash image |
| FW-162 | Watchdog | Task watchdog reset recorded | `PERF?` reset reason WATCHDOG (Perf.cpp:27) | SIM | sim hook that hangs loop (add `~HANG`), check reboot reason |
| FW-163 | Watchdog | Long command under router lock | lock_by names holder; servo gap grows but no reset | SIM | PERF? |
| FW-164 | Watchdog | Brownout counter across reboot (RTC memory) | Survives reset, clears on power cut | LAB | power cycle; QEMU RTC may not model |
| FW-165 | Watchdog | Infinite loop in module loop() | Watchdog reboots board, bus alive after | SIM | ~HANG hook |
| FW-166 | Memory | Heap after 1 hour of PING loop | Free heap flat within 5% | SIM | PERF? sampled, QEMU time |
| FW-167 | Memory | Heap while 255 board census replies arrive at master | Master heap stays above floor, no String leak (BusSlot.h) | SIM | 2 QEMU + scripted fake 255 replies via Rs485Bus |
| FW-168 | Memory | Master hub table with 255 boards (peers JSON) | `/api/peers` size bounded, no OOM | LAB | WiFi; unit via fake |
| FW-169 | Memory | Many simultaneous HTTP clients/uploads | Heap above low-water, 503 not crash | LAB | real radio |
| FW-170 | Memory | Mesh seen-ring and wait slots full | Oldest evicted, no overflow | SIM | native MeshLogic test |
| FW-171 | Memory | Stack high-water on deep command (16 words, long strings) | Stack margin positive per `PERF?` | SIM | serial fuzz, PERF? stack |
| FW-172 | Memory | Runaway RS485 buffer | Capped at 4096 (RS485Bus.cpp:80) | SIM | inject |
| FW-173 | Bench | PERF? loop time budget after all above | Loop under 20 ms (50 Hz servo) | SIM | tools/bench_perf.py on QEMU |
