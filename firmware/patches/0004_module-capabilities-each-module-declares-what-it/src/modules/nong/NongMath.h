#pragma once
// The nong's pure arithmetic, with NO Arduino, servo or storage dependency.
//
// Split out of NongModule so it can be compiled and RUN on a PC
// (`pio test -e native`, see firmware/test/test_logic/). Everything here is a
// free function of its arguments: no globals, no hardware, no time.
//
// This is the maths that decides where a servo is told to go and how long a
// move takes. Getting it wrong does not crash — it quietly drives the arm to
// the wrong angle or finishes a move before the arm arrives, which is exactly
// the class of bug that source-reading cannot catch.
//
// NongModule includes this and calls these; it must never keep a second copy.
#include <math.h>
#include <stdint.h>

namespace nongmath {

// ---- joint angle -> servo pulse ---------------------------------------
// Two different spaces, both measured from their CENTRE:
//   joint degrees  — the physical joint, neutral 90, what poses are written in
//   servo degrees  — how far the servo shaft turns, 0..range
// The gear maps between them, so a 270 deg servo behind a 15:18 reduction and
// a 180 deg servo behind 12:13 are driven correctly side by side, and every
// saved pose keeps working when a servo is swapped.
//
//   servo = range/2 + (joint - 90) * gear/pinion  (+ trim, then invert)
//
// `servoRange` is the SERVO's own travel — NOT the joint's limits.
inline float jointToServoDeg(float jointDeg, float servoRange,
                             int gearPinion, int gearGear, float trim) {
    if (servoRange <= 1.0f) servoRange = 180.0f;
    if (gearPinion < 1) gearPinion = 1;
    if (gearGear < 1) gearGear = 1;
    const float ratio = (float)gearGear / (float)gearPinion;
    return servoRange * 0.5f + (jointDeg - 90.0f) * ratio + trim;
}

inline int servoDegToUs(float servoDeg, float servoRange,
                        int pulseMin, int pulseMax, bool invert) {
    if (servoRange <= 1.0f) servoRange = 180.0f;
    float a = servoDeg;
    if (a < 0.0f) a = 0.0f;
    if (a > servoRange) a = servoRange;
    if (invert) a = servoRange - a;
    return pulseMin + (int)lroundf(a / servoRange * (float)(pulseMax - pulseMin));
}

// the whole chain, as writeServos() performs it
inline int jointToUs(float jointDeg, float servoRange, int gearPinion,
                     int gearGear, float trim, int pulseMin, int pulseMax,
                     bool invert) {
    return servoDegToUs(jointToServoDeg(jointDeg, servoRange, gearPinion, gearGear, trim),
                        servoRange, pulseMin, pulseMax, invert);
}

// ---- how long a move must take ----------------------------------------
// The PHYSICAL floor: no servo may be asked to turn faster than its own
// max deg/s, so the slowest joint on this move sets the time. Asking for less
// would let the interpolation "finish" before the arm has arrived, and the
// next step would start from a pose that was never reached.
inline uint32_t minDuration(const float from[], const float to[],
                            const float maxDps[], int n, uint32_t minMoveMs) {
    float need = 0.0f;                                   // seconds
    for (int i = 0; i < n; i++) {
        const float dps = maxDps[i] > 1.0f ? maxDps[i] : 1.0f;
        const float t = fabsf(to[i] - from[i]) / dps;
        if (t > need) need = t;
    }
    const uint32_t ms = (uint32_t)(need * 1000.0f);
    return ms > minMoveMs ? ms : minMoveMs;
}

inline float maxDelta(const float from[], const float to[], int n) {
    float d = 0.0f;
    for (int i = 0; i < n; i++) {
        const float x = fabsf(to[i] - from[i]);
        if (x > d) d = x;
    }
    return d;
}

// The SHOW speed: biggest joint change / speed. Still floored by minDuration()
// at the call site — this is the requested time, not the achievable one.
inline uint32_t durationFor(const float from[], const float to[], int n,
                            float speedDps, uint32_t minMoveMs) {
    const float sp = speedDps > 1.0f ? speedDps : 1.0f;
    const uint32_t ms = (uint32_t)(maxDelta(from, to, n) / sp * 1000.0f);
    return ms > minMoveMs ? ms : minMoveMs;
}

// ---- cosine ease, the shape of every move -----------------------------
inline float ease(float t) {
    if (t <= 0.0f) return 0.0f;
    if (t >= 1.0f) return 1.0f;
    return 0.5f - 0.5f * cosf((float)M_PI * t);
}

} // namespace nongmath
