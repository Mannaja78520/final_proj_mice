#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

// RS485 addressing helpers that scale past "one bus, ids 1..247, everyone
// answers at once". Pure C++ (no Arduino) so `pio test -e native` can pin it.
//
// THE PROBLEM (measured by qc/lib/bus_sim.py, 2026-11-21): a plain `#* PING`
// puts every board into one of 24 slots by id % 24. With 247 boards that is
// ~10 boards per 10 ms slot - they talk over each other, the hub reads wreckage,
// and only a handful of boards are found. Worse, the default id comes from one
// MAC byte, so two boards of the same box can share an id and neither a ping
// nor a command can tell them apart.
//
// THE FIX, three small additions that old boards simply ignore:
//   #* PING <lo> <hi>   only ids lo..hi answer. A range of 24 gives each id its
//                       OWN slot, so unique ids never collide.
//   #* CHIPS <lo> <hi> <salt>
//                       every board in the range reports its chip (the eFuse
//                       MAC, globally unique) as "@<id> CHIP <chip>". Two boards
//                       that share an id land in different LANES by a hash of
//                       their chip and the salt, so the hub can see both.
//   #~<chip> <cmd>      address a board by its chip. Works when ids collide;
//                       this is how the hub gives a duplicate a new id.
// The reply to a chip-addressed line is "@~<chip> <reply>".
namespace BusAddr {

constexpr uint32_t SLOT_MS = 10;   // gap that beats one reply's time on the wire
constexpr int SLOTS = 24;          // slots per lane == the widest useful id range
constexpr int LANES = 2;           // duplicates are split across this many lanes

// FNV-1a over the chip text, seeded by the salt (a new salt = a new shuffle),
// then an avalanche step. WITHOUT the last step the lowest bit of FNV is only
// the parity of the input bits and the salt flips it for every board alike, so
// two chips of equal parity shared a lane under EVERY salt: found by
// qc/lib/bus_sim.py, 2026-11-21 (duplicates were missed 60% of the time).
inline uint32_t hash(const char* s, uint32_t salt) {
    uint32_t h = 2166136261u ^ (salt * 16777619u);
    for (; *s; s++) { h ^= (uint8_t)toupper((unsigned char)*s); h *= 16777619u; }
    h ^= h >> 16; h *= 0x85ebca6bu; h ^= h >> 13; h *= 0xc2b2ae35u; h ^= h >> 16;
    return h;
}

// Read "<lo> <hi>" (and an optional third number) from the text after a command.
// False when there are no two numbers, lo > hi, or they leave 1..247.
inline bool parseRange(const char* args, int& lo, int& hi, long* third = nullptr) {
    char* e = nullptr;
    long a = strtol(args, &e, 10);
    if (e == args) return false;
    const char* p = e;
    long b = strtol(p, &e, 10);
    if (e == p) return false;
    if (third) { const char* q = e; long c = strtol(q, &e, 10); *third = (e == q) ? 0 : c; }
    if (a < 1 || b > 247 || a > b) return false;
    lo = (int)a; hi = (int)b;
    return true;
}

// Slot of a ranged PING reply, or -1 when this id is outside the range.
inline int pingSlot(int id, int lo, int hi) {
    if (id < lo || id > hi) return -1;
    return (id - lo) % SLOTS;
}

// Slot of a CHIPS reply: the id's own slot, shifted into a lane by the chip hash.
inline int chipsSlot(int id, int lo, int hi, const char* chip, uint32_t salt) {
    if (id < lo || id > hi) return -1;
    return (id - lo) % SLOTS + SLOTS * (int)(hash(chip, salt) % LANES);
}

// "#~<addr>" matches this chip? Case-insensitive, whole string.
inline bool chipIs(const char* addr, const char* chip) {
    if (strlen(addr) != strlen(chip)) return false;
    for (; *addr; addr++, chip++)
        if (toupper((unsigned char)*addr) != toupper((unsigned char)*chip)) return false;
    return true;
}

}  // namespace BusAddr
