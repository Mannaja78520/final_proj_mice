#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// Bridged buses: a bus board that has a SECOND link (its own RS485 port, or a
// UART to another board that runs a bus) is a GATEWAY. A board behind it is
// addressed by a PATH of ids, one per bus crossed:
//
//   #>12>7 SET NAME x       board 7 on the bus behind gateway 12
//   #>12>7>3 GOTO 2         board 3 behind gateway 7 behind gateway 12
//   #>12>* PING 1 24        broadcast on the bus BEHIND 12 (never forwarded further)
//   #>12>~A0B1C2D3E4F5 ... chip address on the bus behind 12
//   reply: @>12>7 OK ...    the same path, so the hub knows who answered
//
// Why '>' in front: an older board reads "#<text up to the space>" with toInt().
// "12/7" would read as 12 and run the command itself; ">12>7" reads as 0, which
// is not its id, so old boards stay silent. (BusAddr.h uses '~' for the same reason.)
//
// Loops cannot run away on the wire: each gateway removes one hop, so a line dies
// after MAX_DEPTH. Broadcasts are never forwarded, so no storm either.
// Pure C++ so the host test (qc/checks/check_bus_topology.py) compiles it.
namespace BusPath {

constexpr int MAX_DEPTH = 4;      // '>' hops in an address (3 gateways + the board); more is refused

// "<>12>7>3" -> first=12, rest=">7>3" (rest points into addr; "" when last).
// False when addr is not a path (no leading '>') or a hop is not 1..247.
inline bool first(const char* addr, int& id, const char*& rest) {
    if (addr[0] != '>') return false;
    char* e = nullptr;
    long v = strtol(addr + 1, &e, 10);
    if (e == addr + 1 || v < 1 || v > 247) return false;
    id = (int)v;
    rest = e;                      // "" or ">..."
    return *e == '\0' || *e == '>';
}

// Number of '>' hops: ">12>7" = 2.
inline int depth(const char* addr) {
    int n = 0;
    for (; *addr; addr++) if (*addr == '>') n++;
    return n;
}

}  // namespace BusPath
