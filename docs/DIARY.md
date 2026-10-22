# Mice — diary

One entry per day, built from the patch logs by `python tools/make_diary.py`. Every change is snapshotted with its date when it lands, so this is the record rather than a recollection. Re-run it any time to bring the diary up to date.

**2026-07-24 → 2026-10-22 · 192 changes over 36 days**

---

## 2026-10-22

- **studio 0056** — A46-1: safe paths (straight, else RRT-Connect) for video, dummy follow and recording; Make and save; Moves while talking card

## 2026-10-21

- **studio 0056** — Distances: shoulder to elbow and shoulder to hand on each side (A45-26)

## 2026-10-19

- **studio 0056** — Moves from a video: MediaPipe skeleton to arm moves (A44-4)
- **studio 0056** — Video tab: person, skeleton and robot side by side; links fetched by the hub; video sound to robot music
- **studio 0056** — palm or back of each hand on top (A44-1), replaces front/back arm
- **studio 0057** — Moves from a video: say when a hand cannot show the asked side
- **studio 0057** — every Run kept on the robot as last.yaml, Save to robot buttons, This robot settings (A44-2, A44-3)
- **studio 0058** — Moves from a video: force hand side, stay with the music, keep / leave out / replace each move
- **studio 0059** — Moves from a video: forced hand side kept on part-way moves (Stay with the music); misses counted on the final pose (A44-7)

## 2026-10-14

- **studio 0056** — web step 3 (A41-4): shared head, one name and Save, 3D view room, side tabs, phone view buttons, html cut into parts

## 2026-09-28

- **studio 0116** — bug sweep: project rig before clamp, no NaN times, pinned time kept on peak-limit change, duplicate drops cues, YAML move names reload, serial commands one at a time, Run/hand-off check the robot's answer, WiFi download checks status
- **studio 0117** — Dummy card in the Robot tab: the hand-posed dummy poses Studio and the robot

## 2026-09-27

- **studio 0108** — RS485 adapter connect: Studio remembers the bus id per port, no blind INFO retry, one Connect at a time, 15 s fetch timeout
- **studio 0109** — Shows: one clock with the robot, gentler joins between sequences, show music
- **studio 0110** — Shows: music stop time, per-sequence speed in a show
- **studio 0111** — Shows: add the show's music from this PC
- **studio 0112** — Shows: From PC says why when the robot is not connected; music row wraps
- **studio 0113** — Music upload: say to log in again after a hub restart; ask before a big track over the cable
- **studio 0114** — Music upload: sent by the hub in the background with a percent wheel and cancel
- **studio 0115** — Music upload: rename non-English track names; hub reads the body before refusing

## 2026-09-24

- **studio 0107** — A31-23/A31-24: save-changes question centred, no don't-ask-again box (switch is in Setup > Saving); cards in Sequence, Robot and Setup fold to their title like the Pose tab's

## 2026-09-23

- **studio 0103** — shows run with no gap between sequences and can repeat by times or seconds; a whole show loads onto the time bar; the timing limit that holds a move is named and the peak limit is editable offline; a move can be given to the front or back arm and mirrored properly;

## 2026-09-22

- **studio 0100** — Keep peer targeting compatible with fastest-route Studio

## 2026-09-21

- **hub 0015** — Home: last opened says hours/days, not thousands of minutes (A26-82)
- **hub 0016** — Home/Modules: last opened on each board's own row, keyed by chip (A26-87)
- **hub 0017** — Studio opens with a live fastest-route target
- **studio 0099** — Studio and monitor follow the fastest route while open

## 2026-09-18

- **studio 0098** — Shows tab: saved sequences played one after another by name, the hub runs the show (A26-40)

## 2026-09-17

- **studio 0085** — Save YAML under its own name with a replace warning; picking a saved YAML opens it in the timeline (A0-20)
- **studio 0086** — Timeline panel drags taller or shorter, keeps its height, arrow keys and double-click reset (A0-17)
- **studio 0087** — Studio login is the hub login: wrong password refused by the hub, a hub session logs Studio in (A26-32)
- **studio 0088** — Safety speed cap in move timing (SAFE_DPS from the robot) and RS485 adapter bus id found by itself (A26-31, A26-33)
- **studio 0089** — Robot home separate from show neutral, joint-limit mismatch warning, delete saved YAML, freeze report (A26-35..38)
- **studio 0090** — Loop travels back to the start as a timed move; hub waits the board's real move time (A26-41)
- **studio 0091** — Zero position lock uses the hub login (A26-43); removed browser-only change-login
- **studio 0092** — Music picker stays open when clicked and works without live follow (A26-49)
- **studio 0093** — Studio preview waits for the arm to reach keyframe 0 before its clock starts (A26-50)
- **studio 0094** — Distances in mm between elbows and hands: click Distances or hold D (A26-44)
- **studio 0095** — Monitor connects by itself and polls one at a time over RS485 (A26-42)
- **studio 0096** — Shrug preview turns by the real angle, not x3 (A26-45)
- **studio 0097** — A frozen Studio page stops the hub show; hidden or closed does not (A26-46)

## 2026-09-16

- **studio 0084** — Clicking a move during Play travels from where the arm is at show speed and carries on; time-bar jumps move at show speed (A0-18 safety)

## 2026-09-10

- **studio 0082** — Time bar in its own row, music can repeat, per-joint start pose
- **studio 0083** — Per-joint servo offset: nudge one joint without re-zeroing the rest

## 2026-09-08

- **firmware 0045** — checkpoint before Codex starts on the interface
- **firmware 0046** — Codex starting A25-1; existing staging handover tool and dev-tools check preserved. UI work has not started.
- **firmware 0047** — handover tool landed; Codex has the brief and has not started
- **firmware 0048** — Codex resuming A25-1 after prior promotion finished; checking snapshot histories before UI edits
- **firmware 0049** — Codex is working in staging; bridge opened
- **firmware 0050** — A25-1 shared rainbow removed, warmer neutral palette, quieter hub tools and module header; Studio and light tool next
- **firmware 0051** — Codex's interface work gated and promoted
- **firmware 0052** — A25 landed: rainbow guarded, shortcuts tab named
- **studio 0073** — checkpoint before Codex starts on the interface
- **studio 0074** — Codex starting A25-1; existing staging handover tool and dev-tools check preserved. UI work has not started.
- **studio 0075** — handover tool landed; Codex has the brief and has not started
- **studio 0076** — Codex resuming A25-1 after prior promotion finished; checking snapshot histories before UI edits
- **studio 0077** — Codex is working in staging; bridge opened
- **studio 0078** — A25-1 shared rainbow removed, warmer neutral palette, quieter hub tools and module header; Studio and light tool next
- **studio 0079** — A25-1 calmer Studio with optional precise posing, short guidance and helpful empty timeline
- **studio 0080** — Codex's interface work gated and promoted
- **studio 0081** — A25 landed: rainbow guarded, shortcuts tab named

## 2026-09-07

- **studio 0069** — shows keep their music: play/vol steps survive load, hub play and export (A24-22)
- **studio 0070** — reword the load status so it is not read as a failure message
- **studio 0071** — a music button on every keyframe: pick a track from the robot /music and a volume, no music removes it (A24-24)
- **studio 0072** — hear it and add it from the music picker: play/stop the track on the robot, and upload one from this PC (A24-26)

## 2026-08-28

- **studio 0068** — Run and tab-hide handover continue from the clicked keyframe instead of sweeping back to pose 1, and the first move of a resumed file is never quicker than the distance needs

## 2026-08-26

- **studio 0062** — moveKey retimes the keyframe after the swapped pair; Monitor ends the hub show; apps pages use real tokens (--sans/--card); dup-as-hold comment corrected
- **studio 0063** — export writes a first move's own speed; two stray notice() calls removed
- **studio 0064** — notice() is the FAIL banner only: first-move speed exported, happy-path strays cut across limits/sequence/zero-set flows
- **studio 0065** — notice() is the FAIL banner only: first-move speed exported, happy-path strays cut, connect-first guards raise the banner
- **studio 0066** — panel batch5: connModeChanged dangling notice braced into its failure branch
- **studio 0067** — Hub names and the echoed export file name reach the page as TEXT, never as markup (A24-8): findHubs builds its options with createElement/textContent like every other picker, and the saved-sequence status line dropped innerHTML - a renamed machine on the venue WiFi could otherwise write HTML, and sc…

## 2026-08-25

- **studio 0061** — timeline edits keep hand-typed times (retimeAt); Pause stops the hub show with Live off; project keeps seqNext; export/load/play surface hub errors

## 2026-08-24

- **studio 0060** — A21-2 technical-detail switch: typed IP and bus id inputs hide behind .tech until Show technical details is on; toggle lives on the Robot link card, preference shared via mice.js hub_adv

## 2026-08-23

- **studio 0058** — clicking a move parks the play clock and scrubber at that move's start time (keyStartMs over the played list, suspended skipped as playback skips them)
- **studio 0059** — Play saved: play a saved sequence (hub or SD) without loading it for editing first

## 2026-08-21

- **studio 0056** — Studio can drive a module on another PC: the hub:<ip>/ prefix survives the ?dev= parse and rides every command
- **studio 0057** — keyboard-only: the keyframe number is a real button, and the move name keeps its focus ring

## 2026-08-19

- **firmware 0036** — board auth: nothing that changes anything answers a stranger
- **firmware 0037** — the board stops publishing its own password, and demands a real one
- **firmware 0038** — Boards report their chip id, so the hub can tell one board met twice from two boards that share a default id
- **firmware 0039** — The board page admits when something failed: the re-login after a password change, the password prompt, logout and the file list
- **firmware 0040** — A way back to the hub from the board page: the hub names itself on every request, the board offers the last one that spoke to it
- **firmware 0041** — The board carries the shared theme file and script, so a board page wears the same theme as the hub
- **firmware 0042** — Bounded RS485 broadcast stagger, and the camera says which sensor it found
- **firmware 0043** — A grouped board with no neighbours looks for its group, so a room of boards can find each other
- **firmware 0044** — The camera says which board and sensor it is, and finds its own pin layout
- **hub 0004** — one tab component across the hub, the module site and Studio
- **hub 0005** — the hub gets accounts: add and remove people, the way the module already works
- **hub 0006** — Firmware gets its own screen: one place writes firmware over a cable or WiFi, unbuilt types are shown with the command that builds them, and a finished write tells the board what it now is
- **hub 0007** — Flash from a PC that never built the firmware: the image travels to the hub holding the cable, which writes it; destructive controls carry the shared danger style
- **hub 0008** — Open the hub on a phone: a QR of its own address drawn by the hub itself, and mice.local answered over mDNS
- **hub 0009** — One board is one row: the hub merges what it finds on a cable and on the WiFi by the board chip id
- **hub 0010** — Addresses, cable ports and signal strengths hide behind one switch in Settings; names, types and module numbers always show
- **hub 0011** — Help documents the board page saying when something failed
- **hub 0012** — Help documents the way back to the hub from a board page
- **hub 0013** — Colour themes: one file holds every colour, the picker discovers them, dark stays default
- **hub 0014** — The hub finds a module on the RS485 bus however high its id is
- **studio 0055** — Studio uses the shared tab

## 2026-08-18

- **firmware 0034** — module website links /mice.css, which the board now serves from flash
- **firmware 0035** — one logging helper: every log line is one write through LOGF, tags in one list
- **hub 0002** — one shared design system: pages link /mice.css instead of each carrying a copy
- **hub 0003** — delete module.html; its URL is now a 302 to the module's real website
- **studio 0054** — style.css keeps only Studio's own rules; tokens and components come from /mice.css
- **studio 0055** — sliders shrink with their track, so the side panel stops clipping the joint boxes

## 2026-08-10

- **firmware 0032** — RELAX drives every servo line low: SHRUG is on GPIO15 (pull-up), so detach alone left it high and the servo held
- **firmware 0033** — SHRUG is now a TianKongRC 35kg (270 deg, 250 deg/s, 500-2500us) - the 4-bar gear 1:2.25 and joint limits are unchanged
- **hub 0001** — baseline: the hub pages as they are on 2026-08-10, so future changes have an 'old' to compare against
- **studio 0048** — move your Studio setup to another PC: export/import a file, or share and get over the network
- **studio 0049** — hub flash picker: types that are not built yet are shown disabled, with the command that builds them
- **studio 0050** — playback is much lighter (slider row and painting), and dragging the timeline moves the real arm
- **studio 0051** — clicking a move in the timeline travels at that move's own speed, not at drag speed
- **studio 0052** — name the moves in a sequence: type a name on each timeline chip, saved with the project and written into the exported file as a comment
- **studio 0053** — crash check warns instead of blocking - preview always plays, the robot only moves if you force it; playback lag cut; scrubbing moves the arm

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

- **firmware 0020** — FIX: isNong was never defined, so the nong joint sliders never rendered on the module site
- **studio 0041** — splitter drags again, narrow panel scrolls, suspend re-timing can shorten a move
- **studio 0042** — only one player at a time: Play and Stop now stop the module's own sequence too
- **studio 0043** — shrug 4-bar calibration curve: each shoulder placed at its own measured rise
- **studio 0044** — FIX: Studio leaked a material per mesh per rebuild - the PC crashes

## 2026-08-06

- **firmware 0018** — module website joins the shared design system (tokens, focus ring, reduced motion)
- **firmware 0019** — module website: plainer tab labels
- **studio 0038** — one design system across every web app: shared tokens, focus rings, honest error and stale states
- **studio 0039** — background playback hands the show to the module; USB lag and 3D overlap fixed
- **studio 0040** — friendlier wording on the hub, module site and Studio

## 2026-08-05

- **firmware 0017** — groups: modules only link within their own installation, hotspot password derived from the group
- **studio 0037** — hub Network tab: see every module and link only the ones you pick

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
- **firmware 0011** — live WIFI command, shared AP while connected, atomic reply framing, quoted-password fix
- **firmware 0012** — REACH and PEERS: reach a module through another module's hotspot
- **firmware 0013** — REACH retries so a radio-sharing module is reliable over a shared hotspot
- **firmware 0014** — one cable, no venue WiFi: peers behind a module hotspot are fully controllable
- **firmware 0015** — WIFI CLEAR back to the built-in network, and a weak link relays through a stronger neighbour
- **firmware 0016** — scanning no longer damages the link; hub finds modules on another subnet
- **studio 0024** — Plane views are now really flat: Front/Back/Left/Right/Top/Bottom switch to an OrthographicCamera so parallel edges stay parallel and dragging in a plane matches what you see; iso/free keeps perspective.
- **studio 0025** — Tuned rig can become the SHIPPED default: new 'Make this the factory default' button posts the live RIG to the hub, which writes rig_default.json into the project.
- **studio 0026** — Servo presets now come from the ONE shared table (firmware/config/servos.json) fetched from the hub, with the old literals kept only as an offline fallback - the firmware compiles the same file into a header at build time, so the two sides can no longer drift.
- **studio 0027** — Send rig is now one JCFG per joint instead of up to five commands each - 50 round trips down to 10, about 1.6s to 0.3s - with an automatic fallback to the individual commands on a board older than JCFG.
- **studio 0028** — before Nong Studio restructure (Phase D) - snapshot so the current two-tab layout can be restored with --restore
- **studio 0029** — Nong Studio side panel regrouped into four task tabs - Pose / Sequence / Robot / Setup - instead of Movement/Setup, which had buried the robot link, SD card and zero calibration under Movement.
- **studio 0030** — Playback no longer dies when the tab is hidden: the show clock is split from rendering (playTick works out its own elapsed time, so rAF and a 60ms interval can both drive it without double-counting) and Studio holds a silent audio track while playing, which keeps most browsers from throttling a back…
- **studio 0031** — hub reads replies by their blank-line marker, so a log line is never mistaken for one
- **studio 0032** — help page documents reach-through, live WiFi and the reply-framing fixes
- **studio 0033** — hub keeps modules that answer slowly; help documents the shared-WiFi timing
- **studio 0034** — hub routes through a module hotspot with usb:PORT@name; hub page lists the peers
- **studio 0035** — help documents WiFi precedence, WIFI CLEAR and the weak-link relay
- **studio 0036** — hub finds modules on a different subnet via their USB-reported IP

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

