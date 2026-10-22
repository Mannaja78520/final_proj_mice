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
    #define GACHA_DROP_SLOTS       2      // pockets from receive to drop - measure on the bench (A47-5)
    #define GACHA_SPEED            600    // motor PWM 0-1023
    #define GACHA_SLOT_TIMEOUT_MS  4000   // no magnet for this long while turning = jammed
    #define GACHA_DEBOUNCE_MS      5      // hall must read the same this long to count
    #define GACHA_SETTLE_MS        0      // keep turning this long after a magnet, to centre the pocket
#endif
