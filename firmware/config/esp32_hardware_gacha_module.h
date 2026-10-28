#ifndef ESP32_HARDWARE_GACHA_MODULE_H
#define ESP32_HARDWARE_GACHA_MODULE_H

    // ================= GACHA module (prize dispenser) =================
    // A holder with GACHA_SLOTS pockets turns on one motor. One hall sensor
    // sits at the RECEIVE position (the item comes in from the back there and
    // does not fall yet); a magnet under every pocket passes it. Turning
    // GACHA_DROP_SLOTS pockets on from the receive position lets the item fall.
    // Everything below is a power-on default only: GCFG changes it from the
    // module page and stores it in the board's NVS (user 2026-10-22: 4 magnets
    // = all 4 pockets today, more pockets later).
    // No SD card on this module (user 2026-10-22); the core still runs without one.

    // Motor driver: 2-pin H-bridge (IN_A/IN_B, PWM on both) by default.
    // GPIO33 is the hall, so the lift's motor pins (33/32) cannot be reused.
    #define GACHA_MOTOR_IN_A       25
    #define GACHA_MOTOR_IN_B       26
    #define GACHA_MOTOR_PWM        -1     // 3-pin drivers (EN + IN1/IN2) set this
    #define GACHA_HALL_PIN         33     // user 2026-10-22; ADC1 pin with an internal pull-up
    #define GACHA_HALL_ACTIVE_LOW  1      // A3144/US1881 pull LOW when a magnet is over them

    #define GACHA_MAGNETS          4      // magnets around the holder (one turn)
    #define GACHA_SLOTS            4      // pockets; magnets must be a multiple of this
    #define GACHA_DROP_SLOTS       1      // pockets per dispense (1 = normal vending; 2 = initial empty wheel prime)
    #define GACHA_INTAKE_DWELL_MS  300    // dwell time at receive position before rotating to let gravity feed capsule (ms)
    #define GACHA_SPEED            500    // travel speed between pockets (0-1023)
    #define GACHA_SLOT_TIMEOUT_MS  5000   // no magnet for this long while turning = jammed
    #define GACHA_DEBOUNCE_MS      5      // hall must read the same this long to count
    #define GACHA_SETTLE_MS        0      // keep turning this long after a magnet, to centre the pocket
    #define GACHA_OVERSHOOT_MS     180    // 1. forward overshoot past drop lip (ms)
    #define GACHA_OVERSHOOT_SPEED  380    // gentle forward overshoot speed (0-1023)
    #define GACHA_RETURN_MS        250    // 2. reverse rock duration past magnet to agitate prize (ms)
    #define GACHA_RETURN_SPEED     360    // gentle reverse rock speed (0-1023)
    #define GACHA_CENTER_SPEED     260    // 3. gentle forward steps to a debounced Hall stop (0-1023)
    #define GACHA_CENTER_PULSE_MS   15    // motor-on step; loop stays responsive to Hall and STOP
    #define GACHA_CENTER_REST_MS    35    // motor-off rest between steps
    #define GACHA_CENTER_WAIT_MS    40    // settle before accepting debounced Hall
    #define GACHA_REVERSE_REST_MS   60    // additional nonblocking rest after reversing
    #define GACHA_CENTER_ADVANCE_MS 18    // estimate into Hall band; GCALIB may update it
    #define GACHA_ADVANCE_MAX_MS    100   // cap learned/manual advance
    #define GACHA_NUDGE_MAX_MS      1000  // maximum duration of one manual GNUDGE
    #define GACHA_MAX_PASSES        100   // maximum arrivals in one GSPIN/GTEST
    #define GACHA_DRAIN_MAX         999   // cap on one drain request
    #define GACHA_CALIB_MAX_MS      5000  // deadline for the entire calibration
    #define GACHA_CALIB_REVERSE_MS  260
    #define GACHA_CALIB_REVERSE_PWM 320
    #define GACHA_CALIB_REST_MS     100
    #define GACHA_CALIB_FIND_STEPS  50
    #define GACHA_CALIB_SPAN_STEPS  20
    #define GACHA_CALIB_SPAN_MS     10
    #define GACHA_PAUSE_MS         5000   // 4. stationary pause after Hall found (ms, user requested 5s)
    #define GACHA_FALLBACK_SLOT_MS 0      // timed slot backup if sensor fails (0 = disable, ms per slot)
    // Hardware note: Motor has anti-back-EMF Schottky diode (drop ~0.187V). Future INA219 sensor on I2C.
#endif
