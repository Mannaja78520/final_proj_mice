#pragma once
#include <stdint.h>
// The dispenser's counting, with no Arduino in it, so `pio test -e native`
// runs it on the PC (test/test_logic) and the QC fake module counts the
// same way (qc/lib/fake_serial.py).

namespace gachamath {

// Magnet passes per pocket. 4 magnets on 4 pockets = 1 (user 2026-10-22);
// 8 magnets on 4 pockets later = 2. 0 = a layout that cannot work.
inline int passesPerSlot(int magnets, int slots) {
    if (magnets < 1 || slots < 1 || magnets % slots) return 0;
    return magnets / slots;
}

// One hall sensor, debounced. A magnet ARRIVING (inactive -> active, held
// for debounceMs) is one pass. Starting ON a magnet counts nothing: the
// holder rests at the receive position with its magnet over the sensor, and
// leaving it is not an arrival.
struct HallCounter {
    bool stable = false;        // debounced state: true = magnet over the sensor
    bool raw = false;
    uint32_t rawSince = 0;
    bool primed = false;

    // Feed the sensor every loop. Returns true on the tick a pass is counted.
    bool feed(bool active, uint32_t nowMs, uint32_t debounceMs) {
        if (!primed) { primed = true; stable = raw = active; rawSince = nowMs; return false; }
        if (active != raw) { raw = active; rawSince = nowMs; }
        if (raw != stable && nowMs - rawSince >= debounceMs) {
            stable = raw;
            return stable;      // only the arrival counts
        }
        return false;
    }
};

// OPTIONAL MOTOR ENCODER (A47-11: the CAD's Namiki 22CL-3501PG has one). The
// hall stays the only truth for WHERE the holder is; the encoder only says
// whether the shaft is turning at all, and how far it is since the last
// magnet. So a wrong encoder setting can make a stop slower, never wrong.

// Stall: turning, but no encoder count for stallMs. Much sooner than the
// hall timeout (a whole pocket), so a jammed capsule stops the motor early.
struct EncWatch {
    int32_t last = 0;
    uint32_t movedMs = 0;
    void start(int32_t count, uint32_t nowMs) { last = count; movedMs = nowMs; }
    bool stalled(int32_t count, uint32_t nowMs, uint32_t stallMs) {
        if (count != last) { last = count; movedMs = nowMs; return false; }
        return stallMs > 0 && nowMs - movedMs >= stallMs;
    }
};

// Counts between two magnets, learned while turning: the latest gap, so a
// worn gearbox is followed. A gap under a quarter of the old one is a bounce.
inline int32_t learnPerPass(int32_t learned, int32_t gap) {
    if (gap < 0) gap = -gap;
    if (gap == 0 || (learned > 0 && gap * 4 < learned)) return learned;
    return gap;
}

// Slow down just before the LAST magnet of a turn: passesLeft == 1 and fewer
// than slowCounts left of a pass (perPass counts). The hall still stops it.
inline bool slowNow(int passesLeft, int32_t sinceLastPass, int32_t perPass, int32_t slowCounts) {
    if (passesLeft != 1 || perPass <= 0 || slowCounts <= 0) return false;
    if (sinceLastPass < 0) sinceLastPass = -sinceLastPass;
    return perPass - sinceLastPass <= slowCounts;
}

// Speed while slowing: pct of the running speed, never below the floor the
// motor needs to keep turning.
inline int slowSpeed(int speed, int pct, int floor) {
    int v = speed * pct / 100;
    return v < floor ? floor : (v > speed ? speed : v);
}

// Stock after one dispense. -1 = not counted (never runs out).
inline int stockAfter(int stock) { return stock < 0 ? -1 : (stock > 0 ? stock - 1 : 0); }

// Why a dispense is refused, or nullptr when it may go. FORCE (admin) skips
// "closed" and "empty" - the item still counts - but never "busy".
inline const char* refusal(bool busy, bool open, int stock, bool force) {
    if (busy) return "busy";
    if (force) return nullptr;
    if (!open) return "event closed";
    if (stock == 0) return "empty";
    return nullptr;
}

}  // namespace gachamath
