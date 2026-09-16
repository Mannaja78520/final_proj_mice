#pragma once
// Deciding WHICH WiFi a module should be on, with no Arduino in it — so it can
// be compiled and RUN on a PC (`pio test -e native`, firmware/test/test_logic).
//
// Why this is a separate, tested thing: you cannot make a real -80 dBm signal
// appear on a bench on demand. The behaviour that matters most is the one that
// only shows up in a big venue, so the decision has to be provable without the
// venue.
//
// THE PROBLEM
// A module far from the router may still *connect* to it — badly. Commands
// arrive late, status polls time out, and a show stutters. Meanwhile another
// module ten metres away has a strong link and is already hosting its own
// access point. The far module should lean on its neighbour instead.
//
// Falling back only when the connect FAILS is not enough: a weak link does not
// fail, it just performs badly. This decides on signal strength as well.
//
// THE RULE
//   * a link at or above GOOD_RSSI is fine — never move
//   * below WEAK_RSSI, a neighbour worth MARGIN dB more is better; move
//   * once relaying, only go back when the real network is comfortably good
//     again (GOOD_RSSI), not merely better than terrible
//
// The gap between "weak enough to leave" and "good enough to return" is
// deliberate. Without it a module sitting near the threshold flips between two
// networks forever, and every flip drops its connection for a second — which
// at a show looks exactly like the robot randomly freezing.
#include <stdint.h>

namespace wifilink {

// dBm. -67 is the usual "good enough for real-time" line; below about -80 a
// 2.4GHz link is unusable in a crowded room.
const int GOOD_RSSI = -67;
const int WEAK_RSSI = -78;
const int MARGIN = 12;      // a neighbour must be this much better to be worth it

enum Action {
    STAY,        // nothing to do
    RELAY,       // leave the show network, join the neighbour's hotspot
    RETURN,      // come back to the show network
};

// `onRelay`   are we currently connected via another module's hotspot?
// `mainRssi`  signal of the show network (0 = not visible at all)
// `bestPeer`  signal of the strongest neighbouring module's hotspot (0 = none)
inline Action decide(bool onRelay, int mainRssi, int bestPeerRssi) {
    const bool haveMain = mainRssi != 0;
    const bool havePeer = bestPeerRssi != 0;

    if (onRelay) {
        // Only leave a working relay for a main network that is genuinely
        // good. "Slightly less bad" is how flapping starts.
        if (haveMain && mainRssi >= GOOD_RSSI) return RETURN;
        return STAY;
    }
    if (!havePeer) return STAY;             // nowhere better to go
    if (haveMain && mainRssi >= WEAK_RSSI) return STAY;   // the link is fine
    // the main network is weak or gone; is the neighbour clearly better?
    if (!haveMain) return RELAY;
    if (bestPeerRssi - mainRssi >= MARGIN) return RELAY;
    return STAY;
}

// Picking WHICH scan result to aim at — the other half of the same question,
// with the same excuse to be pure and PC-tested: the interesting case needs a
// neighbour order no bench can arrange.
//
// Rule: a module we have MET beats every guess, whatever the signal difference
// — its hotspot password is derived from the group, so we can actually get in;
// a stronger guess may simply refuse us. Within one kind, the stronger signal
// wins. rssi 0 means "not seen".
//
// Names are COPIED into std::string members on purpose: the caller feeds
// c_str() of a scan-loop String that is reassigned every iteration, so a
// borrowed pointer would silently end up naming whatever was scanned last.
#include <string>
struct PeerPick {
    int knownRssi = 0;  std::string knownName;
    int guessRssi = 0;  std::string guessName;

    void feed(bool known, int rssi, const char* name) {
        if (rssi == 0 || !name) return;
        if (known) {
            if (!knownRssi || rssi > knownRssi) { knownRssi = rssi; knownName = name; }
        } else {
            if (!guessRssi || rssi > guessRssi) { guessRssi = rssi; guessName = name; }
        }
    }

    // The candidate to aim at, or nullptr for none. Valid while *this lives.
    const char* best(int& rssi, bool& known) const {
        if (knownRssi) { rssi = knownRssi; known = true;  return knownName.c_str(); }
        if (guessRssi) { rssi = guessRssi; known = false; return guessName.c_str(); }
        rssi = 0; known = false; return nullptr;
    }
};

}  // namespace wifilink
