#pragma once
#include <string.h>
#include <strings.h>

// Which camera board rows to try, and in what order. Pure functions with no
// Arduino types, so test/test_logic can run them on the PC.
//
// A person who knows the board (CAM BOARD <name>) is believed first: that row
// is tried before anything else, so a clone whose pins match two rows is not
// settled by whichever row happens to come first. If their pick fails the
// firmware still falls back to trying every row, because a typo must not turn
// a working camera into a dead one.

// Index of `name` among `names[0..count)`, case-insensitive, or -1.
inline int camFindBoard(const char* const* names, int count, const char* name) {
    if (!name || !*name) return -1;
    for (int i = 0; i < count; i++)
        if (strcasecmp(names[i], name) == 0) return i;
    return -1;
}

// Fills order[0..count) with the row indices to try. `wanted` (or -1 for auto)
// goes first, the rest keep table order and none is repeated. Returns count.
inline int camTryOrder(int count, int wanted, int* order) {
    int n = 0;
    if (wanted >= 0 && wanted < count) order[n++] = wanted;
    for (int i = 0; i < count; i++)
        if (i != wanted) order[n++] = i;
    return n;
}
