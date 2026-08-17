#ifndef ESP32_HARDWARE_NONG_MODULE_H
#define ESP32_HARDWARE_NONG_MODULE_H

    // ================= NONG hardware module (humanoid upper body) =================
    // Nong hardware = 8 MG90S servos + the microSD card, nothing else (no
    // encoder, no RGB strip, no speaker — those pins belong to the lift
    // wiring, and a board boots as either lift or nong, never both).
    // One pin per LOGICAL joint (order in NongModule.h):
    //   1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P
    //   8 R_EL_R  9 WAIST   10 SHRUG
    // Joints 1-8 are the two arms (universal joint = 2 servos each). Joint 9
    // WAIST yaws the whole upper body left/right (TianKongRC 35kg, 270 deg).
    // Joint 10 SHRUG lifts both shoulders a few degrees (MG90S, ~6 deg).
    // These pins are the compile-time DEFAULTS — each board overrides them at
    // runtime from its own NVS pin map (Hardware pins on the website).
    // Joints 1-8 reuse lift-only pins (motor/encoder/limits/I2S). WAIST/SHRUG
    // default to 13 (lift's RGB pin — unused on a nong board) and 15; both are
    // usable as outputs, but SD (5,18,19,23) and RS485 (16,17,4) stay live on
    // nong, so if you wire those, set the two new servos to your real GPIOs in
    // the web pin config.
    // Set a pin to -1 when that joint is wired to ANOTHER board (2-ESP
    // humanoid — see the "link"/"peer" settings in NongModule.h).
    #define NONG_SERVO_PINS        {32, 33, 25, 26, 21, 22, 27, 14, 13, 15}

    // ===== Per-joint servo + gear =====
    // Each joint can use a DIFFERENT servo and a different reduction, so the
    // pulse range, speed and gear are arrays in joint order:
    //   1 L_SH_P  2 L_SH_R  3 L_EL_P  4 L_EL_R  5 R_SH_P  6 R_SH_R  7 R_EL_P
    //   8 R_EL_R  9 WAIST   10 SHRUG
    // As built: SHOULDERS = PDI-1181MG (270 deg) through a 15:18 reduction,
    //           ELBOWS    = MG90S      (180 deg) through a 12:13 reduction,
    //           WAIST     = TianKongRC 35kg 270 deg, direct 1:1,
    //           SHRUG     = MG90S 180 deg, direct 1:1 (small ~6 deg travel).
    // All of it is changeable at runtime from the web / Nong Studio
    // (GEAR, PULSE, SERVO, RANGE commands) — these are only the power-on defaults.
    // Generic single-servo fallbacks (used when an array entry is missing):
    #define NONG_PULSE_MIN_US      500    // MG90S pulse range
    #define NONG_PULSE_MAX_US      2400
    // Per-joint pulse range (us) — PDI-1181MG 500..2500, MG90S 500..2400,
    // TianKongRC 270 deg 500..2500. VERIFY against the datasheet, adjust in web.
    #define NONG_PULSE_MIN_DEF     { 500,  500,  500,  500,  500,  500,  500,  500,  500,  500}
    #define NONG_PULSE_MAX_DEF     {2500, 2500, 2400, 2400, 2500, 2500, 2400, 2400, 2500, 2400}
    // Per-joint physical speed limit (deg/s of the JOINT) — the move-time floor.
    // WAIST is a big geared 35kg servo (slower); SHRUG barely moves.
    #define NONG_MAX_DPS_DEF       { 375,  375,  400,  400,  375,  375,  400,  400,  200,  400}
    // Per-joint SERVO TRAVEL (deg): how far the servo itself turns from its
    // pulse minimum to its pulse maximum. A normal hobby servo is 180; wide
    // servos are 270 (some 300/360). This is the servo's own travel, NOT the
    // joint's — the joint stays in JOINT degrees (neutral 90, limits
    // joint_min/joint_max) and the gear maps between them. Fitting a 270 servo
    // to a joint means changing ONLY this number (RANGE command / Nong Studio),
    // never the poses or the sequences.
    // 270 deg servos: the 4 SHOULDERS (PDI-1181MG) and WAIST (TianKongRC).
    // 180 deg servos: the 4 ELBOWS and SHRUG (MG90S).
    #define NONG_SERVO_RANGE_DEF   { 270,  270,  180,  180,  270,  270,  180,  180,  270,  180}
    #define NONG_RANGE_MIN_DEG     60     // sanity bounds for the RANGE command
    #define NONG_RANGE_MAX_DEG     360
    // Per-joint SERVO FRAME RATE (Hz). DEFAULT 50 for every joint — this is the
    // rate the robot ran at BEFORE, and it works. The PDI-1181MG datasheet lists
    // 330 Hz as its rate, and 330 Hz IS available (RATE command / Studio), BUT
    // driving the shoulder PDIs at 330 Hz made a marginal unit pull too much
    // current on a move and trip its protection ("disable itself"), so 330 is
    // NOT the default. Only raise a joint's rate if that servo actually needs it
    // AND the current draw stays safe. (ESP32: servos sharing an LEDC timer
    // share their rate, so keep servos of the same rate together.)
    #define NONG_FRAME_HZ_DEF      {  50,   50,   50,   50,   50,   50,   50,   50,   50,   50}
    #define NONG_FRAME_HZ_MIN      40
    #define NONG_FRAME_HZ_MAX      400
    // Per-joint reduction gear: pinion (on the servo) : gear (on the joint).
    // WAIST and SHRUG are direct-driven (1:1) by default.
    #define NONG_GEAR_PINION_DEF   {  15,   15,   12,   12,   15,   15,   12,   12,    1,    1}
    #define NONG_GEAR_GEAR_DEF     {  18,   18,   13,   13,   18,   18,   13,   13,    1,    1}
    #define NONG_DEFAULT_SPEED_DPS 120.0f // deg/s used when a POSE has no T
    #define NONG_MAX_SPEED_DPS     400.0f // physical servo limit (MG90S ~0.15s/60deg
                                          // under load). A commanded T shorter than
                                          // largest-delta/max_dps is raised to it, so
                                          // the real arm always reaches the pose.
    #define NONG_MIN_MOVE_MS       80     // shortest interpolated move
    #define NONG_DEFAULT_NEUTRAL   90.0f  // neutral angle for every joint
    // Per-servo travel limits (deg). The universal joint cannot reach the
    // full 0..180 — the middle of a 2-servo universal joint binds — so each
    // servo is clamped to [min,max]. These are the defaults; set the real
    // range per joint (joint_min/joint_max in module.yaml, the LIMIT command,
    // or the Rig setup in Nong Studio).
    #define NONG_DEFAULT_MIN       30.0f
    #define NONG_DEFAULT_MAX       150.0f
    // Per-joint JOINT limits / trim / invert / neutral (10 joints). The two
    // BODY joints differ from the arms: WAIST (9) yaws the body left/right so
    // it wants a wide range; SHRUG (10) only lifts the shoulders a little, so
    // its range is deliberately tiny (~6 deg total, 87..93). All are overridable
    // from module.yaml / LIMIT / Nong Studio.
    #define NONG_MIN_DEF      { 30,  30,  30,  30,  30,  30,  30,  30,  30,  87}
    #define NONG_MAX_DEF      {150, 150, 150, 150, 150, 150, 150, 150, 150,  93}
    #define NONG_TRIM_DEF     {  0,   0,   0,   0,   0,   0,   0,   0,   0,   0}
    #define NONG_INVERT_DEF   {  0,   0,   0,   0,   0,   0,   0,   0,   0,   0}
    #define NONG_NEUTRAL_DEF  { 90,  90,  90,  90,  90,  90,  90,  90,  90,  90}
    // Servo->joint reduction gear (pinion on the servo, gear on the joint).
    // The joint turns pinion/gear of the servo travel. Stored + reported so
    // Nong Studio can show the true joint angle; commands stay in servo deg.
    #define NONG_GEAR_PINION       12
    #define NONG_GEAR_GEAR         13

#endif
