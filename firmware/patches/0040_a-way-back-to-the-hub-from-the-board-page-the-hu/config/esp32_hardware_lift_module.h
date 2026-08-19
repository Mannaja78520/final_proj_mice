#ifndef ESP32_HARDWARE_LIFT_MODULE_H
#define ESP32_HARDWARE_LIFT_MODULE_H

    // ================= LIFT hardware module =================
    // Everything specific to the "lift" module type: motor driver, encoder,
    // limit switches, rack & pinion geometry, motion defaults, AND the
    // lift-only peripherals — the WS2812 RGB strip and the I2S speaker (AMP)
    // (nong boards have neither; only RS485 + SD are shared, in esp32_hardware.h).
    // Pins here are the compile-time DEFAULTS — each board overrides them at
    // runtime from its own NVS pin map (Hardware pins on the website /
    // PIN command). Included by esp32_hardware.h (one binary, all types).

    // WS2812B RGB strip (data pin fixed at compile time by FastLED — the one
    // pin that CANNOT be reassigned from the web)
    #define RGB_LED_PIN      13
    #define RGB_MAX_LEDS     120   // compile-time buffer, actual count set in module.yaml
    #define RGB_DEFAULT_LEDS 30

    // I2S audio amp (e.g. MAX98357A). GPIO2 also drives the onboard LED on most boards.
    #define I2S_BCLK_PIN 27
    #define I2S_LRC_PIN  14
    #define I2S_DOUT_PIN 2

    //define your robot' specs here
    #define MOTOR_RPM 100.0f                                            // motor's max RPM
    #define MAX_RPM_RATIO 0.85f                                             // max RPM allowed for each MAX_RPM_ALLOWED = MOTOR_MAX_RPM * MAX_RPM_RATIO
    #define MOTOR_MAX_RPM  MOTOR_RPM * MAX_RPM_RATIO
    #define MOTOR_OPERATING_VOLTAGE 12                                      // motor's operating voltage (used to calculate max RPM)
    #define MOTOR_POWER_MAX_VOLTAGE 12                                      // max voltage of the motor's power source (used to calculate max RPM)
    #define MOTOR_POWER_MEASURED_VOLTAGE 12                                 // current voltage reading of the power connected to the motor (used for calibration)
    #define ENCODER_PULSES_PER_REVOLUTION 11                                // encoder 1 pulse

    #define ENCODER_TICKS 4                                                 // encoder ticks
    #define COUNTS_PER_REV ENCODER_PULSES_PER_REVOLUTION * ENCODER_TICKS  // wheel1 encoder's no of ticks per rev

    // INVERT MOTOR DIRECTIONS
    #define MOTOR_INV false

    // INVERT ENCODER DIRECTIONS
    #define MOTOR_ENCODER_INV false

    //  Motor Brake
    #define MOTOR_BRAKE true

    // Motor 1 Parameters (default pins; override in the Hardware pins web card)
    #define MOTOR_PWM  -1
    #define MOTOR_IN_A 33
    #define MOTOR_IN_B 32

    // Encoder 1 Parameter
    // Set LIFT_HAS_ENCODER 0 for a lift without an encoder: only UP/DOWN to
    // the limit switches, GOTO limited to bottom/top stage, stage known only
    // at the limits. (Also settable per-board: "encoder: 0" in module.yaml
    // on the SD card, or "CFG encoder 0".)
    #define LIFT_HAS_ENCODER 1
    #define MOTOR_ENCODER_INCRIMENT -1
    #define MOTOR_ENCODER_PIN_A 25
    #define MOTOR_ENCODER_PIN_B 26
    #define MOTOR_ENCODER_RATIO 1.0f

    // Limit switch top (active LOW, internal pullup)
    #define LIMIT_TOP  22

    // Limit switch bottom (active LOW, internal pullup)
    #define LIMIT_DOWN 21

    // ===== Lift mechanics: rack & pinion =====
    // Rack module 2, pinion 25 teeth -> pitch dia 50 mm -> 157.08 mm per rev
    #define RACK_MODULE       2.0f
    #define PINION_TEETH      25
    #define PINION_MM_PER_REV (PI * RACK_MODULE * PINION_TEETH)   // mm of rack per pinion rev
    #define GEAR_RATIO        1.0f    // motor(encoder) revs per pinion rev (gearbox)
    #define PINION_MAX_RPM    MOTOR_RPM // pinion RPM at full PWM — calibrate for m/s accuracy
    #define LIFT_STAGE_MM     500.0f  // rack travel between stages (mm)

    // Lift motion defaults (overridable via /data/module.yaml or CFG command)
    #define LIFT_DEFAULT_SPEED 900    // travel PWM (used when speed_mms is 0)
    #define LIFT_SLOW_SPEED    350    // PWM used near target / while homing
    #define LIFT_DEFAULT_STAGES 4
    #define LIFT_TOL_MM        2.0f   // "arrived" tolerance (mm)
    #define LIFT_SLOW_MM       40.0f  // distance from target where we slow down (mm)
    
#endif
