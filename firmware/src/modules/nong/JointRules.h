#pragma once
#include <Arduino.h>
#include <config.h>   // the hardware limits, the way every other file reaches them

// WHAT A JOINT FIELD IS ALLOWED TO BE — in one place, for every command.
// =====================================================================
// Six numbers describe a joint: the gear ratio, the pulse range, the maximum
// speed, the servo's own travel, the frame rate, and the joint's limits. Each
// can be set one at a time (GEAR, PULSE, SERVO, RANGE, HZ, LIMIT) or all at
// once (JCFG), and until 2026-08-20 every rule was written out twice - once in
// the single-field command and once in JCFG.
//
// The two copies had ALREADY drifted in wording: the pulse rule said
// `need 100<=pmin, pmax>pmin+100, pmax<=5000` in one and
// `need 100<=min, max>min+100, max<=5000 (us)` in the other. Wording drifting
// is harmless; it is the warning that the NUMBERS drift next, and JCFG's own
// comment says exactly what that would cost - a batch must never be a way to
// smuggle in a value the single command would have refused.
//
// So each rule is one function, and the message lives with the rule that
// rejects it. A rule nobody can restate is a rule that cannot disagree with
// itself.
namespace jointrule {

// The gearbox between the servo and the joint. Zero or negative would divide
// by zero downstream, which is why this is the one rule with no upper bound:
// a strange ratio is somebody's odd mechanism, not a fault.
inline bool gear(int pinion, int gearTeeth, String& err) {
    if (pinion < 1 || gearTeeth < 1) {
        err = "ERR pinion/gear must be >=1";
        return false;
    }
    return true;
}

// The servo's pulse window, in microseconds. The gap of 100us is not taste: a
// window narrower than that maps the whole joint onto a few counts, and the
// arm then jumps between positions it cannot hold.
inline bool pulse(int lo, int hi, String& err) {
    if (lo < 100 || hi <= lo + 100 || hi > 5000) {
        err = "ERR need 100<=min, max>min+100, max<=5000 (us)";
        return false;
    }
    return true;
}

// Degrees per second. Below 30 the arm is slower than the show clock can
// follow, and a move that never finishes looks like a crash.
inline bool dps(float value, String& err) {
    if (value < 30) {
        err = "ERR max_dps must be >= 30";
        return false;
    }
    return true;
}

// How far the SERVO itself travels - not the joint, which has its own limits.
inline bool travel(float deg, String& err) {
    if (deg < NONG_RANGE_MIN_DEG || deg > NONG_RANGE_MAX_DEG) {
        // The fuller wording, kept from the single-field RANGE command: JCFG
        // used to say only the numbers. Where the two messages differed, the
        // more helpful one wins - that is the point of having one.
        err = "ERR servo travel must be " + String(NONG_RANGE_MIN_DEG) + ".." +
              String(NONG_RANGE_MAX_DEG) + " deg (180 normal, 270 wide)";
        return false;
    }
    return true;
}

// Frame rate. Measured on this hardware: 330Hz destroyed L_SH_R, which is why
// the ceiling is in the hardware header and not a number typed here.
inline bool hz(int value, String& err) {
    if (value < NONG_FRAME_HZ_MIN || value > NONG_FRAME_HZ_MAX) {
        err = "ERR frame rate " + String(NONG_FRAME_HZ_MIN) + ".." +
              String(NONG_FRAME_HZ_MAX) + " Hz (50 normal, 330 for PDI-1181MG)";
        return false;
    }
    return true;
}

// The joint's own travel limits, in joint degrees.
inline bool limits(float lo, float hi, String& err) {
    if (hi <= lo) {
        err = "ERR joint max must exceed min";
        return false;
    }
    return true;
}

}  // namespace jointrule
