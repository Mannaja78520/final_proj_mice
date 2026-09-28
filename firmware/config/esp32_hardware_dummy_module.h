#ifndef ESP32_HARDWARE_DUMMY_MODULE_H
#define ESP32_HARDWARE_DUMMY_MODULE_H

    // ================= DUMMY module (hand-posed copy of the nong) =================
    // The same 10 joints as the robot, in the same order (NONG_JOINT_NAMES),
    // with a potentiometer on each joint instead of a servo. Nothing moves:
    // a person bends the dummy and the board reports the angles.
    //
    // ADC: only ADC1 works while WiFi is on (ADC2 belongs to the radio), and a
    // nodemcu-32s breaks out six ADC1 pins (36 39 34 35 32 33). Ten joints do
    // not fit, so the default wiring is ONE 16-channel analog multiplexer
    // (CD74HC4067): SIG on GPIO36, select lines S0-S3 on 25 26 27 14. Each
    // joint's "ch" is then its mux channel 0-15.
    // Without a mux (DMUX OFF), "ch" is the joint's own ADC1 GPIO instead, and
    // at most six joints can be wired. -1 = this joint has no pot.
    // SD (5 18 19 23) and RS485 (16 17 4) stay free, same as on the robot.
    // All of this is changeable at runtime (DMUX, DCAL) - these are power-on
    // defaults only.
    #define DUMMY_MUX_SIG          36
    #define DUMMY_MUX_SEL          {25, 26, 27, 14}
    #define DUMMY_CH_DEF           {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}

    // One pot's electrical travel, in degrees, across the whole ADC range.
    // Common B10K rotary pots are 270-300 deg; 270 is the usual datasheet.
    #define DUMMY_SPAN_DEF         270.0f
    // Raw ADC reading (0-4095) where the joint is at 90 deg. The middle of the
    // range until the dummy is zeroed (DZERO).
    #define DUMMY_ZERO_DEF         2048
    // The joint limits start as the ROBOT's limits (NONG_MIN_DEF/NONG_MAX_DEF),
    // so a fresh dummy can never ask for an angle the robot would refuse.

    #define DUMMY_ADC_MAX          4095     // 12-bit ESP32 ADC
    #define DUMMY_OVERSAMPLE       4        // reads averaged per channel per tick
    #define DUMMY_TICK_MS          20       // 50 Hz, same rate as the robot's servo loop
    #define DUMMY_SMOOTH           0.35f    // low-pass weight of each new reading

#endif
