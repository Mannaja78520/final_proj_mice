#pragma once
// Which saved WiFi to try next, with no Arduino in it so it runs on a PC
// (`pio test -e native`). User 2026-11-21: "if more than one WiFi is entered,
// does the board fall back to the other?" Until then the module kept ONE home
// network: a second SET WIFI replaced the first and a dead router meant AP-only
// until someone typed the other name by hand.
//
// A board holds up to MAX_NETS networks, slot 0 first. A slot is "present"
// when it has an ssid. After a join times out the board moves to the next
// present slot; when the last present slot has failed the whole list has been
// tried and the caller falls back to its own AP and retries from slot 0.
namespace wifilist {

const int MAX_NETS = 3;

// Next present slot after `cur`, or -1 when none is left (the list is spent).
inline int next(int cur, const bool present[MAX_NETS]) {
    for (int i = cur + 1; i < MAX_NETS; i++)
        if (present[i]) return i;
    return -1;
}

// First present slot, or -1 when nothing is saved.
inline int first(const bool present[MAX_NETS]) {
    for (int i = 0; i < MAX_NETS; i++)
        if (present[i]) return i;
    return -1;
}

}  // namespace wifilist
