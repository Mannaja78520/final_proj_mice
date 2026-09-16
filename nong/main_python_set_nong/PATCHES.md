# Web app patches

Every change to the Nong Studio web app is saved here as a numbered patch. Old patches are never removed — each row is a snapshot you can restore with `python save_patch.py --restore <n>`.

| # | when | change |
|---|---|---|
| 0001 | 2026-07-24 15:47 | Add WAIST (270deg TianKongRC) + SHRUG (MG90S ~6deg) body servos -> 10 joints; PDI-1181MG shoulders corrected to 270deg; per-group servo presets incl tiankong35; waist yaws body / shrug lifts shoulders in 3D |
| 0002 | 2026-07-24 16:14 | Rescale Studio 3D model to real STEP dimensions (joints r42, upper 110 / fore 130 bars, shoulderX 120, slim spine torso); IK self-test tolerance now scales with arm reach |
| 0003 | 2026-07-24 16:32 | FIX: model invisible with an old saved rig — mergeRig now migrates 'zero' (and any per-joint array) to length 10; applyPose is NaN-safe; new ?selftest=migrate regression |
| 0004 | 2026-07-24 16:45 | Shrug corrected to a see-saw ROLL (top-center joint rocks the shoulder bar: left up / right down), not a forward-back tilt; module website readout + labels updated to match |
| 0005 | 2026-07-24 17:07 | Shrug pivot adjustable in mm: the see-saw now rocks about a bearing ABOVE the shoulder line (Rig setup > shrug pivot, default 60mm), not at the servo |
| 0006 | 2026-07-26 00:32 | Save current tuned rig as your default: new star-Save-current-as-default button locks the cached tune into a protected slot; Reset now returns to YOUR default (factory only if none saved). Does NOT overwrite tuned dims. |
| 0007 | 2026-07-27 16:42 | Per-joint servo FRAME RATE (Hz): PDI-1181MG shoulders now driven at 330Hz (was 50) — likely the self-disable cause; RATE command + servo rows Hz column + preset carries rate; module website rate control |
| 0008 | 2026-07-27 18:05 | Revert servo frame rate default to 50Hz everywhere (was 330 on shoulders): 330Hz over-currented a marginal L_SH_R on moves and tripped it; 50Hz is the pre-update rate that worked. 330 still available via RATE / Hz box |
| 0009 | 2026-07-31 13:18 | Fix pin config over USB in Nong Studio: its own Web Serial reader also skipped any line starting with '[' (ate the PIN VALID array); now skips only log tags. (Hub had the same bug — MiceHub.exe rebuilt; module page error now points at a stale hub, not firmware.) |
| 0010 | 2026-07-31 15:00 | USB port sharing: Nong Studio's USB link now goes through the hub (which owns and shares the cable), so Studio and the module website can be open on the SAME COM port at once instead of 'serial port already in use'. New port picker, old Web Serial kept as 'USB direct (exclusive)', ?dev=usb:COMx auto-connect. |
| 0011 | 2026-07-31 15:41 | FIX: Play did not move the robot over USB/RS485 - the live-follow branch tested robotIp() (the WiFi field), so segments were only ever sent over WiFi. Now any open link counts. Also send keyframe 0 when playback starts: segments are the moves INTO a keyframe, so keyframe 0 was never sent and the robot's first move started from wherever it stood. |
| 0012 | 2026-07-31 16:44 | Pause now really stops the robot: a segment is handed to the module as one whole move (POSE ... T) and the firmware interpolates it, so pausing the editor used to let the robot run the move to the end. Pause (and scrubbing) sends STOP to freeze it where it is; resuming re-sends the segment with only the time still left. |
| 0013 | 2026-07-31 18:04 | Update (send rig to robot) is no longer 50 blind round trips: read LIMIT? once and send only the lines that differ. An unchanged push is now 1 command instead of 50 (12.8s -> 0.24s measured on the real board); a shoulder-only edit is 8. |
| 0014 | 2026-07-31 18:37 | Editor opens on the Neutral pose from Setup instead of a flat 90 90 90: keyframe 0 (built at boot from the start pose) now matches the robot's own HOME. Uses RIG.neutral, not RIG.zero - zero is the angle at which a joint RENDERS straight, a model calibration, not the pose the robot rests at. |
| 0015 | 2026-07-31 18:55 | FIX: hold now happens BETWEEN moves, not all at the end. segmentAt() had no 'in a hold' branch (poseAt does), so the moment a hold began it returned the NEXT segment and the robot was told to move straight away - it finished early and stood still for the rest of the run. Also live drag throttle 180ms -> 70ms now that a command costs ~30ms instead of ~250ms. |
| 0016 | 2026-07-31 22:01 | FIX: fast slider drag left the arm behind the numbers. Live sends were fire-and-forget fetches with no ordering, so an older pose could arrive last, and a time throttle dropped the final value when the drag ended inside its window (mouse released off the bar = no commit event). Now ONE command in flight: liveQueue keeps ordered work (playback segments, keyframe 0, STOP) in order, livePending keeps only the NEWEST drag pose. Also fixes a race where segment 1 could overtake the keyframe-0 send at the start of Play. |
| 0017 | 2026-07-31 23:34 | Responsive: Nong Studio now lays out for phones, tablets and large screens. Below 860px the 3D view stacks above the side panel (which goes full width) instead of both being squeezed; joint and rig rows get narrower grid tracks; the view cube shrinks; touch pointers get bigger targets. 1600px+ widens the side panel and joint rows. |
| 0018 | 2026-07-31 23:54 | Nong Studio: '⚙ Open module config' button in the Robot link card opens the connected module's own website (pins, WiFi, users, servo type, SD files) in a new tab. It follows the same precedence as commands - cable first, WiFi otherwise - and carries the RS485 bus id, so it always configures the board you are posing. Over shared USB both stay open on one cable; direct Web Serial owns the port, so it explains how to switch. |
| 0019 | 2026-08-01 00:05 | Sequences: suspend a keyframe (the dot on its chip) to skip it while playing, exporting and uploading without deleting it - the move that replaces it is re-timed for the bigger jump and the crash check re-tests that path. New 'then run...' box chains a sequence into another (next: in the YAML), offering the files already on the card. Playback, export and collision checking now all read one play list instead of the raw keyframe array. |
| 0020 | 2026-08-03 13:37 | Speed is now per SEQUENCE: Show speed is written into the sequence file as its first '- speed:' step and restored when re-editing, so each sequence keeps its own pace and a chain sets the speed again at every hand-over instead of sequence B inheriting whatever A left the module on. parseSeqYaml understands the speed step instead of counting it as unsupported. |
| 0021 | 2026-08-03 13:48 | Per-move speed: every keyframe has its own deg/s box (blank = the sequence's speed). Setting it re-times only that move; typing a time clears the override. The exported file emits a speed step before the move and restores the sequence speed after, and parseSeqYaml reads mid-file speed steps back onto the right move so it survives a round trip. |
| 0022 | 2026-08-03 22:16 | FIX: suspending a keyframe made the replacement move lunge. playKeys() re-timed the new move with minTime() - the servos' physical floor, ie the fastest the arm can possibly move - instead of the speed that applies. It now uses autoTime at the surviving keyframe's own deg/s (else the sequence speed), and keeps a longer hand-typed time, so suspending can only slow a move down, never speed it up. |
| 0023 | 2026-08-03 23:08 | FIX: Export / Send to robot SD / Run on robot guarded on the edit list, so with every keyframe suspended they wrote a sequence file containing no moves at all and the robot ran a do-nothing file. They now guard on what will actually be written (playKeys) and say which it is. |
| 0024 | 2026-08-04 02:49 | Plane views are now really flat: Front/Back/Left/Right/Top/Bottom switch to an OrthographicCamera so parallel edges stay parallel and dragging in a plane matches what you see; iso/free keeps perspective. activeCam() routes raycasting, OrbitControls and rendering to whichever camera is live, and the ortho frustum tracks the viewport aspect so switching never jumps. |
| 0025 | 2026-08-04 02:53 | Tuned rig can become the SHIPPED default: new 'Make this the factory default' button posts the live RIG to the hub, which writes rig_default.json into the project. /rig_default.js is loaded before app.js so DEFAULT_RIG is seeded synchronously - a fresh browser and Reset both start on the numbers that match the real robot. Missing or bad file falls back to the built-in constants. |
| 0026 | 2026-08-04 03:28 | Servo presets now come from the ONE shared table (firmware/config/servos.json) fetched from the hub, with the old literals kept only as an offline fallback - the firmware compiles the same file into a header at build time, so the two sides can no longer drift. |
| 0027 | 2026-08-04 09:03 | Send rig is now one JCFG per joint instead of up to five commands each - 50 round trips down to 10, about 1.6s to 0.3s - with an automatic fallback to the individual commands on a board older than JCFG. playKeys() is cached behind a self-validating signature so tick() stops rebuilding it four times a frame; the signature covers exactly the fields the play list reads, so it cannot go stale. |
| 0028 | 2026-08-04 10:57 | before Nong Studio restructure (Phase D) - snapshot so the current two-tab layout can be restored with --restore |
| 0029 | 2026-08-04 11:03 | Nong Studio side panel regrouped into four task tabs - Pose / Sequence / Robot / Setup - instead of Movement/Setup, which had buried the robot link, SD card and zero calibration under Movement. Cards carry data-stab and showTab shows by attribute, so nothing moved in the DOM: every id, handler and QC driver is untouched. The old 'move' name still works and an unknown name falls back to Pose rather than blanking the panel. |
| 0030 | 2026-08-04 14:28 | Playback no longer dies when the tab is hidden: the show clock is split from rendering (playTick works out its own elapsed time, so rAF and a 60ms interval can both drive it without double-counting) and Studio holds a silent audio track while playing, which keeps most browsers from throttling a background tab. NOTE: liveTimer was already taken by the collision throttle - the new interval is playClock, since a duplicate let is a SyntaxError that kills the whole script. |
| 0044 | 2026-08-07 19:01 | FIX: Studio leaked a material per mesh per rebuild - the PC crashes |
| 0045 | 2026-08-09 01:19 | Fix: the robot no longer runs two shows at once. A command that MOVES the robot (POSE/JOINT/HOME/STOP/RELAX/ATTACH) now stops the sequence the module was playing on its own clock, so Play in Studio and the board's own sequence cannot overlap; Pause really stops it; and connecting to a module that is already playing says so. |
| 0046 | 2026-08-09 04:03 | The hub is now the show clock: Play hands the timeline to the hub (POST /api/play) whenever the link goes through it, so a rehearsal keeps running with the tab hidden or the browser closed; the page only draws, returning to it re-syncs the play head, and the module hand-off is skipped while the hub drives. |
| 0047 | 2026-08-09 17:34 | Live control follows the hand: a dragged pose now carries the time it has (measured from the link's own round trip, clamped 80-300ms) instead of letting the module ease at its SPEED setting, which made the arm trail the slider by 166ms per move. |
| 0053 | 2026-08-10 21:44 | crash check warns instead of blocking - preview always plays, the robot only moves if you force it; playback lag cut; scrubbing moves the arm |
| 0054 | 2026-08-18 09:46 | style.css keeps only Studio's own rules; tokens and components come from /mice.css |
| 0055 | 2026-08-19 02:18 | Studio uses the shared tab |
| 0056 | 2026-08-21 00:12 | Studio can drive a module on another PC: the hub:<ip>/ prefix survives the ?dev= parse and rides every command |
| 0057 | 2026-08-21 22:09 | keyboard-only: the keyframe number is a real button, and the move name keeps its focus ring |
| 0058 | 2026-08-23 12:13 | clicking a move parks the play clock and scrubber at that move's start time (keyStartMs over the played list, suspended skipped as playback skips them) |
| 0059 | 2026-08-23 13:27 | Play saved: play a saved sequence (hub or SD) without loading it for editing first |
| 0060 | 2026-08-24 03:44 | A21-2 technical-detail switch: typed IP and bus id inputs hide behind .tech until Show technical details is on; toggle lives on the Robot link card, preference shared via mice.js hub_adv |
| 0061 | 2026-08-25 23:48 | timeline edits keep hand-typed times (retimeAt); Pause stops the hub show with Live off; project keeps seqNext; export/load/play surface hub errors |
| 0062 | 2026-08-26 00:35 | moveKey retimes the keyframe after the swapped pair; Monitor ends the hub show; apps pages use real tokens (--sans/--card); dup-as-hold comment corrected |
| 0063 | 2026-08-26 11:57 | export writes a first move's own speed; two stray notice() calls removed |
| 0064 | 2026-08-26 12:23 | notice() is the FAIL banner only: first-move speed exported, happy-path strays cut across limits/sequence/zero-set flows |
| 0065 | 2026-08-26 12:31 | notice() is the FAIL banner only: first-move speed exported, happy-path strays cut, connect-first guards raise the banner |
| 0066 | 2026-08-26 12:47 | panel batch5: connModeChanged dangling notice braced into its failure branch |
| 0067 | 2026-08-26 18:42 | Hub names and the echoed export file name reach the page as TEXT, never as markup (A24-8): findHubs builds its options with createElement/textContent like every other picker, and the saved-sequence status line dropped innerHTML - a renamed machine on the venue WiFi could otherwise write HTML, and script whoever picked it. |
| 0068 | 2026-08-28 17:31 | Run and tab-hide handover continue from the clicked keyframe instead of sweeping back to pose 1, and the first move of a resumed file is never quicker than the distance needs |
| 0069 | 2026-09-07 12:14 | shows keep their music: play/vol steps survive load, hub play and export (A24-22) |
| 0070 | 2026-09-07 12:17 | reword the load status so it is not read as a failure message |
| 0071 | 2026-09-07 12:59 | a music button on every keyframe: pick a track from the robot /music and a volume, no music removes it (A24-24) |
| 0072 | 2026-09-07 17:56 | hear it and add it from the music picker: play/stop the track on the robot, and upload one from this PC (A24-26) |
| 0073 | 2026-09-08 20:40 | checkpoint before Codex starts on the interface |
| 0074 | 2026-09-08 20:54 | Codex starting A25-1; existing staging handover tool and dev-tools check preserved. UI work has not started. |
| 0075 | 2026-09-08 20:55 | handover tool landed; Codex has the brief and has not started |
| 0076 | 2026-09-08 20:56 | Codex resuming A25-1 after prior promotion finished; checking snapshot histories before UI edits |
| 0077 | 2026-09-08 20:59 | Codex is working in staging; bridge opened |
| 0031 | 2026-08-04 15:27 | hub reads replies by their blank-line marker, so a log line is never mistaken for one |
| 0032 | 2026-08-04 18:18 | help page documents reach-through, live WiFi and the reply-framing fixes |
| 0033 | 2026-08-04 18:54 | hub keeps modules that answer slowly; help documents the shared-WiFi timing |
| 0034 | 2026-08-04 19:21 | hub routes through a module hotspot with usb:PORT@name; hub page lists the peers |
| 0035 | 2026-08-04 19:54 | help documents WiFi precedence, WIFI CLEAR and the weak-link relay |
| 0036 | 2026-08-04 22:47 | hub finds modules on a different subnet via their USB-reported IP |
| 0037 | 2026-08-05 01:14 | hub Network tab: see every module and link only the ones you pick |
| 0038 | 2026-08-06 11:29 | one design system across every web app: shared tokens, focus rings, honest error and stale states |
| 0039 | 2026-08-06 17:12 | background playback hands the show to the module; USB lag and 3D overlap fixed |
| 0040 | 2026-08-06 21:18 | friendlier wording on the hub, module site and Studio |
| 0041 | 2026-08-07 01:21 | splitter drags again, narrow panel scrolls, suspend re-timing can shorten a move |
| 0042 | 2026-08-07 16:13 | only one player at a time: Play and Stop now stop the module's own sequence too |
| 0043 | 2026-08-07 17:39 | shrug 4-bar calibration curve: each shoulder placed at its own measured rise |
| 0048 | 2026-08-10 10:44 | move your Studio setup to another PC: export/import a file, or share and get over the network |
| 0049 | 2026-08-10 15:40 | hub flash picker: types that are not built yet are shown disabled, with the command that builds them |
| 0050 | 2026-08-10 16:49 | playback is much lighter (slider row and painting), and dragging the timeline moves the real arm |
| 0051 | 2026-08-10 19:13 | clicking a move in the timeline travels at that move's own speed, not at drag speed |
| 0052 | 2026-08-10 19:38 | name the moves in a sequence: type a name on each timeline chip, saved with the project and written into the exported file as a comment |
| 0055 | 2026-08-18 16:31 | sliders shrink with their track, so the side panel stops clipping the joint boxes |
| 0078 | 2026-09-08 21:03 | A25-1 shared rainbow removed, warmer neutral palette, quieter hub tools and module header; Studio and light tool next |
| 0079 | 2026-09-08 21:04 | A25-1 calmer Studio with optional precise posing, short guidance and helpful empty timeline |
| 0080 | 2026-09-08 21:33 | Codex's interface work gated and promoted |
| 0081 | 2026-09-08 22:23 | A25 landed: rainbow guarded, shortcuts tab named |
| 0082 | 2026-09-10 14:50 | Time bar in its own row, music can repeat, per-joint start pose |
| 0083 | 2026-09-10 16:57 | Per-joint servo offset: nudge one joint without re-zeroing the rest |
