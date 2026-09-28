#pragma once
// The dummy's arithmetic, with no Arduino in it, so `pio test -e native`
// runs it on the PC (test/test_logic) and the QC fake dummy and Nong Studio's
// simulated dummy can be held to the same numbers (docs/ref_data.js).

namespace dummymath {

// A pot reading -> a joint angle.
//   raw   filtered ADC reading, 0..adcMax
//   zero  the reading at which the joint is at 90 deg (set by DZERO)
//   span  the pot's electrical travel in degrees across 0..adcMax
//   dir   +1, or -1 when the pot is mounted the other way round
// The result is clamped to the joint's limits, so the robot is never handed
// an angle it would refuse.
inline float potToDeg(float raw, float zero, float span, int dir,
                      float lo, float hi, float adcMax) {
    const float deg = 90.0f + (float)(dir < 0 ? -1 : 1) * (raw - zero) * span / adcMax;
    return deg < lo ? lo : (deg > hi ? hi : deg);
}

// The other way: which zero makes the CURRENT reading mean `deg`. This is
// DZERO - hold the dummy in a known pose (the robot's neutral), and every
// joint learns where it is without anyone reading a number off the ADC.
inline float zeroFor(float raw, float deg, float span, int dir, float adcMax) {
    if (span <= 0.0f) return raw;
    return raw - (float)(dir < 0 ? -1 : 1) * (deg - 90.0f) * adcMax / span;
}

// One low-pass step. A pot on a long wire is noisy by a few counts; without
// this the robot following the dummy would twitch while the dummy sits still.
inline float smooth(float prev, float next, float weight) {
    return prev + (next - prev) * weight;
}

}  // namespace dummymath
