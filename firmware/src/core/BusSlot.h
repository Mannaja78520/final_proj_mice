#pragma once
// When a module answers the broadcast "#* PING" census, with no Arduino in it
// so the arithmetic is unit-tested on a PC (`pio test -e native`).
//
// A bus has no collision detection: two modules talking at once garble both.
// Each module therefore waits its own turn. The old turn was (id % 24) * 10 ms,
// so ids 24 apart shared a slot - fine for the 5 boards of a bench, wrong for a
// real installation. Measured 2026-11-21 in the bus model (tools/bench/
// bus_census_model.py): 30 boards with ordinary ids already lose several
// answers per sweep, 255 boards lose about nine in ten.
//
// One slot per id instead: id * SLOT_MS. A reply line is at most ~60 characters
// = 5.2 ms at 115200 baud (10 bits per character), so 6 ms slots can never
// overlap. The last board (255) answers at 1530 ms, inside the hub's 1.6 s
// minimum listening time (hub_probe.py); the hub keeps listening until the bus
// has been quiet for 300 ms after that.
#include <stdint.h>

namespace busslot {

const uint32_t SLOT_MS = 6;
const uint32_t BAUD = 115200;

inline uint32_t censusDelayMs(uint32_t id) { return id * SLOT_MS; }

// Milliseconds a line of `chars` characters occupies the wire (8N1 = 10 bits).
inline uint32_t lineMs(uint32_t chars, uint32_t baud = BAUD) {
    return (chars * 10UL * 1000UL + baud - 1) / baud;
}

}  // namespace busslot
