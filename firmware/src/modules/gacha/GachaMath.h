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
