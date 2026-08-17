# Mice — diary

One entry per day, built from the patch logs by `python tools/make_diary.py`. Every change is snapshotted with its date when it lands, so this is the record rather than a recollection. Re-run it any time to bring the diary up to date.

**2026-07-24 → 2026-08-10 · 56 changes over 10 days**

---

## 2026-08-10

- **hub 0001** — baseline: the hub pages as they are on 2026-08-10, so future changes have an 'old' to compare against

## 2026-08-09

- **firmware 0021** — One binary per module type: pio run -e mice_nong / mice_lift / mice_blank. Module classes, pin entries, commands and web cards are chosen at BUILD time (-D MICE_TYPE_*, src/core/BuildTypes.h, <!--#type--> markers in the master src/web/WebUI.h), and gen_tables.py writes this env's page and tables int…
- **firmware 0022** — One player: a motion command from outside stops the sequence the board is playing on its own clock, so Nong Studio and the module's own sequence can never drive the servos at the same time.
- **firmware 0023** — OTA over WiFi: POST /api/ota writes new firmware into the app slot that is NOT running (min_spiffs.csv has app0+app1, 1.875MB each), so a failed or half-sent update leaves the board booting what it had. Refused while the module is moving or a sequence is playing; force=1 overrides.
- **firmware 0024** — Camera module: cam is a third module type (ESP32-CAM, board esp32cam) with SNAP/CAM commands, a /api/cam.jpg frame endpoint and its own web card, at 68.0% flash and costing nong/lift nothing.
- **firmware 0025** — Bench fixes from the first real-hardware run: blank fell out of the generated module table (tokens after #endif on one line are discarded); preemption stopped a show for a command the module could not run (now after the command, only when taken);
- **firmware 0026** — Second bench session, over WiFi: /api/cam.jpg sent the driver's frame buffer and truncated the picture to 353 of 13000 bytes (now a small private copy, frame returned before the send is queued);
- **firmware 0027** — The camera card blamed the ribbon cable for a working camera: opened from the hub, its <img src=/api/cam.jpg> bypassed the hub's fetch shim and asked the hub instead of the board. The page now fetches the frame (so it follows the page's own transport) and prints the module's real refusal;
- **firmware 0028** — Lag fixes measured on real boards: main loop now yields (delay(1)) so the web task is not starved behind the router mutex (USB POSE 30ms -> 13ms); WiFi.setSleep(false) so the radio does not doze between beacons (ping 73ms -> 17ms);
- **firmware 0029** — Camera live view is now an MJPEG stream (/api/cam.stream): many frames down one connection instead of one request per picture, 1 -> 7.3 -> 18.7 fps direct and 22.2 through the hub, because capture costs 25ms while a separate request cost 120ms on a server that closes every connection.
- **firmware 0030** — Camera picture quality, measured: the orange/blue lines were corrupted scanlines, not noise. Sensor clock 20 -> 10 MHz (VGA: ~37 corrupted rows per frame -> 0-4), the OV2640's bpc/wpc/lenc/raw-gamma corrections enabled, and the sensor starts on SVGA because corruption tracks frame size (qqvga 0.8, q…
- **firmware 0031** — Camera picture quality, second pass: reverted the GRAB_WHEN_EMPTY experiment (the driver refuses it with one frame buffer, init 0x105) and re-tested PSRAM with every later fix in place - it still kills every large HTTP response, so it stays off.
- **studio 0045** — Fix: the robot no longer runs two shows at once. A command that MOVES the robot (POSE/JOINT/HOME/STOP/RELAX/ATTACH) now stops the sequence the module was playing on its own clock, so Play in Studio and the board's own sequence cannot overlap; Pause really stops it;
- **studio 0046** — The hub is now the show clock: Play hands the timeline to the hub (POST /api/play) whenever the link goes through it, so a rehearsal keeps running with the tab hidden or the browser closed;
- **studio 0047** — Live control follows the hand: a dragged pose now carries the time it has (measured from the link's own round trip, clamped 80-300ms) instead of letting the module ease at its SPEED setting, which made the arm trail the slider by 166ms per move.

## 2026-08-07

- **studio 0044** — FIX: Studio leaked a material per mesh per rebuild - the PC crashes

## 2026-08-04

- **firmware 0001** — baseline before Phase A firmware work (env rename, batch command, SETZERO guard)
- **firmware 0002** — Extensible firmware: servo presets moved to config/servos.json and generated into ServoPresets.h by tools/gen_tables.py at build time (zero runtime cost, flash unchanged at 65.1%);
- **firmware 0003** — Commands declared once in config/commands.json, generated into CommandHelp.h at build time. New HELP / HELP <cmd> answers from that table so the board cannot advertise a command it lacks.
- **firmware 0004** — Module capabilities: each module declares what it can do (addCapabilities), status carries a caps list, and the module website shows each card by capability instead of switching on the module type - so a new type shows the right controls with no site edit.
- **firmware 0005** — JCFG batch command: one joint's whole setup (gear, pulse, dps, travel, hz, limits) in a single line, validated exactly as the five individual commands are, re-attaching only that joint.
- **firmware 0006** — WiFi can no longer stall the servo loop: applyHostname deferred its STA restart instead of delay(150), which ran from loop() and would stop a joint mid-move. The connect path was already a polled state machine; a QC check now keeps it that way.
- **firmware 0007** — before module website restructure (Phase C) - snapshot so the current single-column layout can be restored with --restore
- **firmware 0008** — Module website restructured into three tabs (Control / Sequences & files / Setup) instead of thirteen cards in one column.
- **firmware 0009** — TWO bugs found on real hardware: (1) HELP answered with 54 lines but every channel here is one-command-one-line, so its extra lines arrived after the next command's buffer flush and CAL came back as a fragment of HELP - bare HELP now lists names on one line and HELP <name> explains one.
- **firmware 0010** — The robot can run a sequence with NO SD card: FBEGIN/FDATA/FEND fall back to an 8KB memory buffer when no card is fitted, and MOVE plays that. SequencePlayer.startText + SDStore.parseYaml parse YAML straight from memory, touching no SD hardware.
- **studio 0024** — Plane views are now really flat: Front/Back/Left/Right/Top/Bottom switch to an OrthographicCamera so parallel edges stay parallel and dragging in a plane matches what you see; iso/free keeps perspective.
- **studio 0025** — Tuned rig can become the SHIPPED default: new 'Make this the factory default' button posts the live RIG to the hub, which writes rig_default.json into the project.
- **studio 0026** — Servo presets now come from the ONE shared table (firmware/config/servos.json) fetched from the hub, with the old literals kept only as an offline fallback - the firmware compiles the same file into a header at build time, so the two sides can no longer drift.
- **studio 0027** — Send rig is now one JCFG per joint instead of up to five commands each - 50 round trips down to 10, about 1.6s to 0.3s - with an automatic fallback to the individual commands on a board older than JCFG.
- **studio 0028** — before Nong Studio restructure (Phase D) - snapshot so the current two-tab layout can be restored with --restore
- **studio 0029** — Nong Studio side panel regrouped into four task tabs - Pose / Sequence / Robot / Setup - instead of Movement/Setup, which had buried the robot link, SD card and zero calibration under Movement.
- **studio 0030** — Playback no longer dies when the tab is hidden: the show clock is split from rendering (playTick works out its own elapsed time, so rAF and a 60ms interval can both drive it without double-counting) and Studio holds a silent audio track while playing, which keeps most browsers from throttling a back…

## 2026-08-03

- **studio 0020** — Speed is now per SEQUENCE: Show speed is written into the sequence file as its first '- speed:' step and restored when re-editing, so each sequence keeps its own pace and a chain sets the speed again at every hand-over instead of sequence B inheriting whatever A left the module on.
- **studio 0021** — Per-move speed: every keyframe has its own deg/s box (blank = the sequence's speed). Setting it re-times only that move; typing a time clears the override.
- **studio 0022** — FIX: suspending a keyframe made the replacement move lunge. playKeys() re-timed the new move with minTime() - the servos' physical floor, ie the fastest the arm can possibly move - instead of the speed that applies.
- **studio 0023** — FIX: Export / Send to robot SD / Run on robot guarded on the edit list, so with every keyframe suspended they wrote a sequence file containing no moves at all and the robot ran a do-nothing file. They now guard on what will actually be written (playKeys) and say which it is.

## 2026-08-01

- **studio 0019** — Sequences: suspend a keyframe (the dot on its chip) to skip it while playing, exporting and uploading without deleting it - the move that replaces it is re-timed for the bigger jump and the crash check re-tests that path.

## 2026-07-31

- **studio 0009** — Fix pin config over USB in Nong Studio: its own Web Serial reader also skipped any line starting with '[' (ate the PIN VALID array); now skips only log tags. (Hub had the same bug — MiceHub.exe rebuilt; module page error now points at a stale hub, not firmware.)
- **studio 0010** — USB port sharing: Nong Studio's USB link now goes through the hub (which owns and shares the cable), so Studio and the module website can be open on the SAME COM port at once instead of 'serial port already in use'.
- **studio 0011** — FIX: Play did not move the robot over USB/RS485 - the live-follow branch tested robotIp() (the WiFi field), so segments were only ever sent over WiFi. Now any open link counts.
- **studio 0012** — Pause now really stops the robot: a segment is handed to the module as one whole move (POSE ... T) and the firmware interpolates it, so pausing the editor used to let the robot run the move to the end. Pause (and scrubbing) sends STOP to freeze it where it is;
- **studio 0013** — Update (send rig to robot) is no longer 50 blind round trips: read LIMIT? once and send only the lines that differ. An unchanged push is now 1 command instead of 50 (12.8s -> 0.24s measured on the real board); a shoulder-only edit is 8.
- **studio 0014** — Editor opens on the Neutral pose from Setup instead of a flat 90 90 90: keyframe 0 (built at boot from the start pose) now matches the robot's own HOME. Uses RIG.neutral, not RIG.zero - zero is the angle at which a joint RENDERS straight, a model calibration, not the pose the robot rests at.
- **studio 0015** — FIX: hold now happens BETWEEN moves, not all at the end. segmentAt() had no 'in a hold' branch (poseAt does), so the moment a hold began it returned the NEXT segment and the robot was told to move straight away - it finished early and stood still for the rest of the run.
- **studio 0016** — FIX: fast slider drag left the arm behind the numbers. Live sends were fire-and-forget fetches with no ordering, so an older pose could arrive last, and a time throttle dropped the final value when the drag ended inside its window (mouse released off the bar = no commit event).
- **studio 0017** — Responsive: Nong Studio now lays out for phones, tablets and large screens. Below 860px the 3D view stacks above the side panel (which goes full width) instead of both being squeezed; joint and rig rows get narrower grid tracks; the view cube shrinks; touch pointers get bigger targets.
- **studio 0018** — Nong Studio: '⚙ Open module config' button in the Robot link card opens the connected module's own website (pins, WiFi, users, servo type, SD files) in a new tab.

## 2026-07-27

- **studio 0007** — Per-joint servo FRAME RATE (Hz): PDI-1181MG shoulders now driven at 330Hz (was 50) — likely the self-disable cause; RATE command + servo rows Hz column + preset carries rate; module website rate control
- **studio 0008** — Revert servo frame rate default to 50Hz everywhere (was 330 on shoulders): 330Hz over-currented a marginal L_SH_R on moves and tripped it; 50Hz is the pre-update rate that worked. 330 still available via RATE / Hz box

## 2026-07-26

- **studio 0006** — Save current tuned rig as your default: new star-Save-current-as-default button locks the cached tune into a protected slot; Reset now returns to YOUR default (factory only if none saved). Does NOT overwrite tuned dims.

## 2026-07-24

- **studio 0001** — Add WAIST (270deg TianKongRC) + SHRUG (MG90S ~6deg) body servos -> 10 joints; PDI-1181MG shoulders corrected to 270deg; per-group servo presets incl tiankong35; waist yaws body / shrug lifts shoulders in 3D
- **studio 0002** — Rescale Studio 3D model to real STEP dimensions (joints r42, upper 110 / fore 130 bars, shoulderX 120, slim spine torso); IK self-test tolerance now scales with arm reach
- **studio 0003** — FIX: model invisible with an old saved rig — mergeRig now migrates 'zero' (and any per-joint array) to length 10; applyPose is NaN-safe; new ?selftest=migrate regression
- **studio 0004** — Shrug corrected to a see-saw ROLL (top-center joint rocks the shoulder bar: left up / right down), not a forward-back tilt; module website readout + labels updated to match
- **studio 0005** — Shrug pivot adjustable in mm: the see-saw now rocks about a bearing ABOVE the shoulder line (Rig setup > shrug pivot, default 60mm), not at the servo
