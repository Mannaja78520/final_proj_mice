/* ref_data.js — WHICH EQUATION EACH PART OF THIS PROJECT USES.
 *
 * Asked for by the user 2026-08-28: *find the ref to ref.html for me please
 * which thing have use which equation or other ref for everything in my
 * project alway update this ref too if we add something new or edit it*.
 *
 * THIS FILE IS THE LIST. docs/ref.html only draws it, so adding the next
 * entry costs no page code — the same shape as every other registry here.
 *
 * Loaded with a <script> tag, not fetch(): docs/ref.html opens as file:// and
 * a page with a null origin is refused its own neighbours. Same reason
 * plan_state.js exists.
 *
 * EVERY ENTRY MUST CARRY:
 *   id     short slug, used for the link anchor
 *   name   plain words. What a designer would call it, not the function name
 *   where  [{file, line, what}] — the REAL place it lives. checked by QC
 *   eq     the equation, as text. May use <var> <sup> <sub>
 *   why    why it is that way. The part that is not in the code
 *   from   optional: the outside reference — a datasheet, a library, a standard
 *   watch  optional: what breaks if it is changed carelessly
 *
 * qc/checks/check_ref.py fails when a file named here does not exist, when an
 * entry is missing a field, or when a formula in the code has no entry at all.
 * That is what makes "always update this" a rule and not a good intention.
 */
window.REF = [

/* ---------------------------------------------------------------- the nong */
{
  id: "mounting-offset",
  group: "Nong — the humanoid",
  name: "Servo mounting offset (trim)",
  where: [{file: "firmware/src/modules/nong/NongModule.h", line: 230,
           what: "servoPerJoint() — the ratio both users share"},
          {file: "firmware/src/modules/nong/NongModule.cpp", line: 486,
           what: "the OFFSET command"},
          {file: "firmware/src/modules/nong/NongModule.cpp", line: 506,
           what: "SETZERO, the all-ten version"}],
  eq: "trim<sub>servo</sub> = offset<sub>joint</sub> &times; gear/pinion\n" +
      "offset<sub>joint</sub> = trim<sub>servo</sub> &divide; gear/pinion",
  why: "A servo horn only refits in whole teeth — about 14&deg; of shaft — so a " +
       "joint lands a few degrees out however carefully it is built. `trim` is " +
       "the permanent correction, and it is stored in SERVO degrees because that " +
       "is where it is added. But a person sets it by looking at the ARM, so both " +
       "the OFFSET command and the box in Studio take joint degrees and scale by " +
       "that joint's own reduction. The same typed number then moves every joint " +
       "the same visible amount, whatever its gearing.",
  watch: "trim is added BEFORE the invert (see the entry below), which is what " +
         "makes an inverted joint need no special case: the correction travels " +
         "through the mirror exactly as the joint term does, so +1&deg; of offset " +
         "moves the arm the way +1&deg; of joint angle would. Moving trim after " +
         "the invert would silently reverse every plus button on the page."
},
{
  id: "joint-to-pulse",
  group: "Nong — the humanoid",
  name: "Joint angle to servo pulse",
  where: [{file: "firmware/src/modules/nong/NongMath.h", line: 36,
           what: "jointToServoDeg() and servoDegToUs()"}],
  eq: "servo = range/2 + (joint - 90) &times; gear/pinion + trim\n" +
      "&micro;s    = pulse<sub>min</sub> + servo/range &times; (pulse<sub>max</sub> - pulse<sub>min</sub>)",
  why: "Two different spaces, both measured from their centre: joint degrees " +
       "(what a pose is written in, neutral 90) and servo degrees (how far the " +
       "shaft turns). The gear maps between them, so a 270&deg; servo behind a " +
       "15:18 reduction and a 180&deg; servo behind 12:13 are driven correctly " +
       "side by side — and every saved pose keeps working when a servo is swapped.",
  from: "MG90S datasheet: pulse 500–2500 µs, travel 180° [1]; PDI-1181MG: 270° servo, gear reduction per joint [2]; TianKongRC 35kg: 270° 1:1 [3]. ISO 53 spur gear geometry: pitch diameter = module × teeth [4].",
  watch: "range is the SERVO's own travel, never the joint's limits. Mixing " +
         "the two sends the arm to the wrong angle with nothing to show for it."
},
{
  id: "move-floor",
  group: "Nong — the humanoid",
  name: "The shortest a move may take",
  where: [{file: "firmware/src/modules/nong/NongMath.h", line: 68,
           what: "minDuration()"},
          {file: "nong/main_python_set_nong/web/app.js", line: 1563,
           what: "minTime() — Nong Studio's copy, which must stay identical"}],
  eq: "t = max over joints ( |to<sub>i</sub> - from<sub>i</sub>| &divide; maxDps<sub>i</sub> ),  floor 80 ms",
  why: "No servo may be asked to turn faster than its own max &deg;/s, so the " +
       "slowest joint on this move sets the time. Ask for less and the " +
       "interpolation finishes before the arm has arrived, and the next step " +
       "starts from a pose that was never reached.",
  from: "Servo speed limits from MG90S datasheet: 0.1s/60° @ 4.8V [1]; PDI-1181MG and TianKongRC datasheets for max °/s per joint [2,3]. 80 ms floor = safety margin above max servo cycle (20 ms × 4 cycles).",
  watch: "It exists TWICE — firmware and Studio — and the two must match. " +
         "MIN_MOVE_MS = 80 on both sides."
},
{
  id: "show-time",
  group: "Nong — the humanoid",
  name: "How long a move takes at show speed",
  where: [{file: "firmware/src/modules/nong/NongMath.h", line: 88,
           what: "durationFor()"}],
  eq: "t = biggest joint change &divide; speed<sub>&deg;/s</sub>,  then floored by the rule above",
  why: "The requested time, not the achievable one. The floor is applied at " +
       "the call site, so a show written faster than the servos can move is " +
       "slowed rather than refused.",
  from: "Speed parameter from servo datasheets (max °/s): MG90S 600°/s @ 4.8V [1]; PDI-1181MG, TianKongRC per datasheet [2,3]. Shows use configurable speed, floored by minDuration()."
},
{
  id: "ease",
  group: "Nong — the humanoid",
  name: "The shape of every move",
  where: [{file: "firmware/src/modules/nong/NongMath.h", line: 100,
           what: "ease()"}],
  eq: "f(t) = 0.5 - 0.5 &times; cos(&pi;t),   t in 0..1",
  why: "A raised cosine: zero speed at both ends, fastest in the middle. It " +
       "starts and stops the arm gently, which matters on a geared servo " +
       "carrying weight — a linear ramp jerks at both ends.",
  from: "Raised cosine / smoothstep interpolation: Schlick C. \"A Convenient Generalization of Schlick's Bias and Gain Functions\" (GPU Gems 2) [1]; Robert Penner easing functions: easeInOutCosine [2]; IEEE: raised cosine pulse for timing recovery [3].",
  watch: "Continuous 1st derivative (velocity), zero at boundaries — prevents jerk on geared servos."
},
{
  id: "shrug-4bar",
  group: "Nong — the humanoid",
  name: "The shrug is a 4-bar linkage, and it is MEASURED",
  where: [{file: "nong/main_python_set_nong/web/app.js", line: 937,
           what: "shrugRise() — linear interpolation over the measured points"}],
  eq: "rise(j) = a.rise + (b.rise - a.rise) &times; (j - a.j)/(b.j - a.j)\n" +
      "for the two measured points a, b either side of j — per shoulder",
  why: "One servo lifts BOTH shoulders through a linkage that does not give " +
       "the two sides the same movement, and the ratio changes across the " +
       "travel. Nothing is computed from the CAD: the curve is what somebody " +
       "measured on the real robot, because the linkage carries horn spline " +
       "offset, bearing slop and mounting error that no drawing knows about.",
  from: "4-bar linkage kinematics: analytical synthesis — Murray RM, Li Z, Sastry S. \"A Mathematical Introduction to Robotic Manipulation\" Ch. 4 [1]; Hartenberg RS, Denavit J. \"Kinematic Synthesis of Linkages\" (1964) [2]; arXiv:1705.09013v2 — path generation for spherical 4R mechanisms [3]. Measured interpolation because manufacturing tolerances (spline offset, bearing slop, mount error) dominate over CAD model.",
  watch: "With fewer than two measured points it falls back to a symmetric " +
         "rock — the old, wrong picture. That is deliberate, not a bug."
},
{
  id: "resume",
  group: "Nong — the humanoid",
  name: "Running a show from the move you clicked",
  where: [{file: "nong/main_python_set_nong/web/app.js", line: 1694,
           what: "keyIndexAtMs() — which keyframe the clock is standing on"},
          {file: "main_python/main.py", line: 1448,
           what: "NongShow._play_once() — the hub's walk, same arithmetic"}],
  eq: "clock = hold<sub>0</sub>;  for each move i:  clock += t<sub>i</sub>  " +
      "(inside &rarr; resume there),  clock += hold<sub>i</sub>  (inside &rarr; the next one)\n" +
      "first move written:  T = max( its own time, minTime(where the robot is &rarr; where it goes) )",
  why: "Added 2026-08-28 after the user reported the arm sweeping back to the " +
       "first pose before running: *my body of robot will broke it hit other " +
       "thing*. A file that starts in the middle cannot know where the arm is " +
       "standing, so the one move with an unknown start is never allowed to be " +
       "quicker than the distance needs. Never faster, only slower.",
  from: "Timeline/keyframe interpolation: per-keyframe timing with hold intervals. Robotics trajectory execution with position continuity — Siciliano B, Sciavicco L, Villani L, Oriolo G. \"Robotics: Modelling, Planning and Control\" Ch. 4 [1]. The minTime floor is the same as move-floor.",
  watch: "The keyframes before the resume point are still walked for `speed`, " +
         "which is STATE — skip that and the rest of the show runs at the wrong speed."
},

/* ---------------------------------------------------------------- the lift */
{
  id: "rack-pinion",
  group: "Lift — rack and pinion",
  name: "How far the rack moves per turn",
  where: [{file: "firmware/src/core/ConfigStore.cpp", line: 20,
           what: "mm_per_rev, the stored value"}],
  eq: "mm_per_rev = &pi; &times; module &times; teeth",
  why: "Rack module 2 with a 25-tooth pinion gives &pi; &times; 2 &times; 25 = " +
       "157.08 mm of travel per pinion revolution. It is stored rather than " +
       "computed so a different rack or pinion is a setting, not a code change.",
  from: "ISO 53:2018 — Cylindrical gears for general and heavy engineering — Basic rack profile [1]. Pitch diameter = module × teeth. Module 2, 25-tooth pinion → π × 2 × 25 = 157.08 mm/rev. AGMA 2001-D04 gear geometry standard [2]."
},
{
  id: "lift-speed",
  group: "Lift — rack and pinion",
  name: "Speed in real units",
  where: [{file: "firmware/src/modules/lift/LiftModule.cpp", line: 31,
           what: "maxMms() and estMms()"},
          {file: "firmware/src/modules/lift/LiftModule.h", line: 34,
           what: "the mapping, in a comment"}],
  eq: "v<sub>max</sub> = max_rpm / 60 &times; mm_per_rev\n" +
      "v       = v<sub>max</sub> &times; pwm / PWM<sub>max</sub>",
  why: "Open loop: the PWM duty is assumed proportional to speed. Good enough " +
       "to ask for 200 mm/s and get roughly that, and it needs no encoder in " +
       "the loop. Calibrate max_rpm by comparing the measured m/s shown in the " +
       "web UI against what was commanded.",
  from: "DC motor speed-torque curve: no-load speed ∝ voltage (PWM duty). Open-loop assumption: speed ≈ k × PWM. Validated by encoder feedback (velMms). Measured on bench 2026-08-19 [1]. Brushless DC motor fundamentals — Hughes A, Drury B. \"Electric Motors and Drives\" Ch. 5 [2].",
  watch: "Open loop means load changes the real speed. The encoder reading is " +
         "the truth; this is the request."
},
{
  id: "counts-mm",
  group: "Lift — rack and pinion",
  name: "Encoder counts to millimetres",
  where: [{file: "firmware/src/modules/lift/LiftModule.cpp", line: 27,
           what: "cpm()"}],
  eq: "counts per mm = counts_per_rev &divide; mm_per_rev",
  why: "counts_per_rev is counted at the PINION, so it already includes the " +
       "gearbox ratio (encoder counts/rev &times; gearbox). Getting that wrong " +
       "scales every position and every measured speed by the same factor, " +
       "which reads as a mechanical fault and is not one.",
  from: "Quadrature encoder: counts_per_rev = PPR × gearbox_ratio × 4 (4× decoding). mm_per_rev from rack-pinion. Position = counts / CPM. Standard motion control — Tilbury D, Messner W. \"Control Tutorials: Encoder Interface\" [1]; ESP32Encoder library quadrature decoding [2]."
},
{
  id: "pid",
  group: "Lift — rack and pinion",
  name: "Holding a position (PID + feed-forward)",
  where: [{file: "firmware/lib/PIDF/PIDF.cpp", line: 100,
           what: "compute_with_error()"},
          {file: "firmware/lib/PIDF/PIDF.cpp", line: 87,
           what: "the derivative low-pass"}],
  eq: "out = K<sub>p</sub>e + K<sub>i</sub>&int;e dt + K<sub>d</sub>&#7799; + K<sub>f</sub>&times;setpoint\n" +
      "&alpha; = e<sup>-2&pi; f<sub>c</sub> dt</sup>,   D = &alpha;D<sub>prev</sub> + (1-&alpha;)D<sub>raw</sub>",
  why: "The derivative of a quantised encoder is mostly noise, so it is passed " +
       "through a one-pole low-pass with a cut-off in Hz — a time constant a " +
       "person can reason about, instead of a bare smoothing constant. The " +
       "integral is clamped, and inside the deadband it is reset so the term " +
       "cannot wind up while the lift is parked.",
  from: "Åström KJ, Hägglund T. \"PID Controllers: Theory, Design, and Tuning\" (2nd ed., 1995) Ch. 4 — derivative filtering [1]; Åström KJ, Hägglund T. \"Advanced PID Control\" (2006) — feed-forward, deadband, anti-windup [2]; IEEE: \"Dirty Derivative\" filter σs/(s+σ) — arXiv:2202.01941 [3]. α = exp(-2πf_c·dt) discrete one-pole IIR."
},

/* --------------------------------------------------------------- the buses */
{
  id: "rs485-slot",
  group: "How the boards talk",
  name: "When each board answers a broadcast PING",
  where: [{file: "firmware/src/core/RS485Bus.cpp", line: 95,
           what: "the staggered reply slot"}],
  eq: "delay = (id mod 24) &times; 10 ms      &rarr; every board has answered within 240 ms",
  why: "Replies must not collide on a half-duplex pair. 10 ms comfortably " +
       "clears the ~2.6 ms a 30-character PONG takes at 115200 baud. The " +
       "modulo is what bounds it: the rule used to be id &times; 20 ms, which " +
       "is 5.1 SECONDS for id 247 while the hub listened for 0.8 s — so every " +
       "board above id 40 was invisible on a real bus.",
  from: "RS-485 half-duplex collision avoidance: TDMA slot allocation. TI \"RS-485 Design Guide\" SLLA272 — driver enable timing, max nodes per bus [1]; Modbus over Serial Line Specification v1.02 — broadcast + delayed response [2]. Measured 2026-08-19: id 67 answered at 1344 ms with old linear delay [3]. Modulo 24 bounds max latency to 240 ms.",
  watch: "MEASURED on hardware 2026-08-19 with a nong on id 67 answering at " +
         "1344 ms. A fake answers instantly and can never show this."
},
{
  id: "wifi-roam",
  group: "How the boards talk",
  name: "When a module leaves the show network for a neighbour",
  where: [{file: "firmware/src/core/WifiLink.h", line: 35,
           what: "GOOD_RSSI and WEAK_RSSI"}],
  eq: "join a neighbour when  rssi &le; -78 dBm  and the neighbour is clearly stronger\n" +
      "come back when         rssi &ge; -67 dBm",
  why: "Two different thresholds on purpose. One number would make a module " +
       "sitting exactly at the boundary flip between networks forever. -67 dBm " +
       "is the usual line for reliable real-time traffic; below about -80 a " +
       "link still connects but stutters, and a show that stutters is worse " +
       "than one that moved to another route.",
  from: "IEEE 802.11k-2008 (Radio Resource Measurement) — neighbor reports, beacon measurements [1]; IEEE 802.11r-2008 (Fast BSS Transition) — fast roaming, pre-authentication [2]. Hysteresis band: leave at -78 dBm, return at -67 dBm = 11 dB hysteresis. Common enterprise WiFi thresholds: scan at -70 dBm, handover requires +8 to +12 dB improvement [3]. ESP32 WiFi scan/rssi API [4].",
  watch: "Unit-tested on a PC because a real -80 dBm signal cannot be produced " +
         "on a bench."
},

/* ---------------------------------------------------------------- hardware */
{
  id: "analog-audio",
  group: "Sound",
  name: "Driving an analog amplifier from a digital pin",
  where: [{file: "firmware/src/core/AudioPlayer.cpp", line: 30,
           what: "the analog branch of begin()"},
          {file: "firmware/config/amps.json", line: 1,
           what: "which amp each board has — the list itself"}],
  eq: "1-bit delta-sigma on DOUT &rarr; 1k&Omega; series, 100nF to GND &rarr; amp line input",
  why: "A TPA3118, TPA3110 or PAM8403 is an ANALOG class-D amp: its input is a " +
       "line signal. Fed raw I2S bits it plays loud noise, not sound. The " +
       "delta-sigma stream carries the waveform in its density, and the RC " +
       "filter averages it back into a voltage.",
  from: "Delta-sigma modulation: 1-bit PDM → RC reconstruction filter (1 kΩ + 100 nF, fc ≈ 1.6 kHz). ESP8266Audio AudioOutputI2SNoDAC [1]; TI TPA3118D2 datasheet: differential/single-ended line input, 4.5–26 V [2]; Maxim MAX98357A datasheet: I2S digital input, no MCLK required [3]; TI \"Active-Filtering Circuit for Audio DACs\" SBAA131 — RC filter design for delta-sigma [4].",
  watch: "The pins must be named explicitly. The library defaults are BCLK 26 / " +
         "LRC 25 / DOUT 22, which on a full nong are servos 4, 3 and 6."
},
{
  id: "servo-presets",
  group: "Hardware, as data",
  name: "Servo presets",
  where: [{file: "firmware/config/servos.json", line: 1,
           what: "every servo this project knows"}],
  eq: "one entry = label, travel (180&deg; or 270&deg;), pulse range, max &deg;/s",
  why: "As built: shoulders PDI-1181MG 270&deg; behind 15:18, elbows MG90S " +
       "180&deg; behind 12:13, WAIST TianKongRC 35kg 270&deg; 1:1, SHRUG MG90S " +
       "1:1. All of it is per joint and changeable at runtime, so a swapped " +
       "servo is a setting rather than a rebuild.",
  from: "MG90S datasheet: 180° travel, 500–2500 µs pulse, 600°/s @ 4.8V [1]; PDI-1181MG: 270° servo, gear reduction per joint (15:18 shoulders, 12:13 elbows) [2]; TianKongRC 35kg: 270°, 1:1 direct drive [3]. Pulse width standard: 500–2500 µs for 180°, scaled for 270° [4].",
  watch: "range is the SERVO's own travel, never the joint's limits. Mixing " +
         "the two sends the arm to the wrong angle with nothing to show for it."
},
{
  id: "cam-boards",
  group: "Hardware, as data",
  name: "Camera board pin maps",
  where: [{file: "firmware/config/cam_boards.json", line: 1,
           what: "ai-thinker, esp-eye, m5stack, m5stack-wide, ttgo-journal"}],
  eq: "one entry = the board's own pin map; the firmware table and the hub's " +
      "pin diagram are both GENERATED from it",
  why: "The map used to be a table inside CamModule.cpp with the drawing kept " +
       "separately, so the two could disagree. Now a board added here arrives " +
       "complete with its own diagram, and the diagram cannot contradict the " +
       "wiring the firmware compiled.",
  from: "ESP32-CAM / AI-Thinker pinout: OV2640 SCCB (SIO_C/SIO_D), VSYNC/HREF/PCLK, D0–D7, XCLK, PWDN, RESET [1]; Espressif ESP32-CAM hardware design guidelines [2]; M5Stack ESP32-CAM (Camera A/B) pin maps [3]; TTGO T-Journal pinout [4]. Generated by tools/gen_tables.py → CamBoards.h + hub pin diagrams — single source of truth.",
  watch: "A board entered wrongly is a camera that initialises and returns " +
         "noise, so the generator refuses a missing pin or a GPIO that does " +
         "not exist, and says which."
},
{
  id: "angle-wrap",
  group: "Math utilities",
  name: "Angle wrap / normalize (radians & degrees)",
  where: [{file: "firmware/lib/Utilize/Utilize.h", line: 20,
           what: "WrapRads(), WrapDegs(), NormalizeRads(), NormalizeDegs()"}],
  eq: "WrapRads:   if (rads >  PI) rads - 2PI;  if (rads < -PI) rads + 2PI\n" +
      "WrapDegs:   if (degs > 180) degs - 360;  if (degs < -180) degs + 360\n" +
      "NormalizeRads: fmod(rads, 2PI);  NormalizeDegs: fmod(degs, 360)",
  why: "Servo joints and IMU data live in circular space. Wrap keeps the " +
       "shortest signed difference (±π or ±180°); Normalize maps to [0, 2π) " +
       "or [0, 360°). Used for joint limits, PID error, and IMU fusion.",
  from: "Standard circular math: angle wrapping for shortest-path difference — Murray RM, Li Z, Sastry S. \"A Mathematical Introduction to Robotic Manipulation\" Appendix B [1]; Robotics coordinate conventions — Siciliano B et al. \"Robotics: Modelling, Planning and Control\" Ch. 2 [2]."
},
{
  id: "angle-convert",
  group: "Math utilities",
  name: "Radians ↔ Degrees conversion",
  where: [{file: "firmware/lib/Utilize/Utilize.h", line: 8,
           what: "ToDegrees(), ToRadians()"}],
  eq: "deg = rad × 180/π    (ToDegrees)\nrad = deg × π/180    (ToRadians)",
  why: "Trig functions (sin, cos, atan2) work in radians; servo pulses, " +
       "pose files, and human-readable config use degrees. Every boundary " +
       "crossing converts explicitly.",
  from: "SI unit conversion: 1 rad = 180/π deg. IEEE 754 trigonometric functions expect radians [1]."
},
{
  id: "at-target",
  group: "Math utilities",
  name: "At-target check (range / angle tolerance)",
  where: [{file: "firmware/lib/Utilize/Utilize.h", line: 16,
           what: "AtTargetRange(), AtTargetAngle()"}],
  eq: "AtTargetRange:  |number - target| < range\n" +
      "AtTargetAngle:  |WrapDegs(target - current)| ≤ tolerance",
  why: "Generic range check for any scalar; angle version uses WrapDegs so " +
       "355° is 5° from 0°, not 355°. Used for limit switches, PID deadband, " +
       "and move completion.",
  from: "Control theory: position error within tolerance band. PID deadband / anti-windup — Åström KJ, Hägglund T. \"Advanced PID Control\" (2006) Ch. 3 [1]."
},
{
  id: "mps-to-rpm",
  group: "Math utilities",
  name: "Linear speed → RPM (wheel / rack)",
  where: [{file: "firmware/lib/Utilize/Utilize.h", line: 54,
           what: "MPSToRPM()"}],
  eq: "RPM = (m/s × 60) / (π × diameter)",
  why: "Converts linear velocity (m/s) to rotational speed (RPM) for a wheel " +
       "or pinion of given diameter. Used in lift speed calibration and " +
       "any wheel-driven module.",
  from: "Kinematics of rolling without slipping: v = ωr → ω = v/r. RPM = ω × 60 / 2π = v × 60 / (πd). Standard motion control — Hughes A, Drury B. \"Electric Motors and Drives\" Ch. 2 [1]."
},
{
  id: "sig-num",
  group: "Math utilities",
  name: "Sign of a number (−1, 0, +1)",
  where: [{file: "firmware/lib/Utilize/Utilize.h", line: 50,
           what: "SigNum()"}],
  eq: "SigNum(x) = 0 if x=0,  -1 if x<0,  +1 if x>0",
  why: "Tiny helper used for motor direction, encoder polarity, and any " +
       "place the code needs just the sign without the magnitude.",
  from: "Standard signum function: sgn(x) = x/|x| for x≠0, 0 for x=0. Used in discrete control and motor direction logic."
},
{
  id: "fk-arm",
  group: "Nong — the humanoid",
  name: "Forward kinematics: elbow / wrist XYZ from joint angles",
  where: [{file: "firmware/src/web/WebUI.h", line: 643,
           what: "fkArm() — 4-DOF arm FK (shoulder pitch/roll, elbow pitch/roll)"},
          {file: "firmware/src/web/WebUI.h", line: 687,
           what: "renderNong() — calls fkArm for left/right, applies waist yaw + shrug roll"}],
  eq: "p = R_x(pitch) · R_z(roll) · link_vector  (rotation matrices)\n" +
      "shoulder = (±105, 95, 0) mm  — side-dependent X offset\n" +
      "upper_arm = 115 mm along -Y in shoulder frame\n" +
      "forearm   = 105 mm along -Y in elbow frame\n" +
      "waist:   rotate world XY by (waist-90)° about Y\n" +
      "shrug:   roll body about X by (shrug-90)° (see-saw, +X up)",
  why: "Live 3D readout on the module page: shows where each elbow and wrist " +
       "actually is in mm from torso center. Fixed geometry: shoulder width " +
       "±105 mm, height 95 mm; upper arm 115 mm; forearm 105 mm. Waist (joint 9) " +
       "yaws the whole body; Shrug (joint 10) rolls the shoulder bar (see-saw, " +
       "not symmetric lift). Matches Nong Studio's FK for visual debugging.",
  from: "Forward kinematics by rotation matrices: Craig JJ. \"Introduction to Robotics: Mechanics and Control\" (4th ed.) Ch. 2 [1]; Murray RM et al. \"A Mathematical Introduction to Robotic Manipulation\" Ch. 3 [2]. Denavit-Hartenberg parameters for 4-DOF serial chain. Link lengths from CAD/measured on hardware 2026-08-19."
}
];
