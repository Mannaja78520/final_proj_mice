#pragma once
#include <stdint.h>

// The ID3v2 tag at the front of an MP3: title, artist and usually the cover
// picture, often hundreds of KB. The decoder needs none of it. The library's
// reader walked the whole tag one byte at a time on the module loop, and the
// robot answered nothing on the bus until it was through (a show's first
// song, 2026-09-28). Skipping it is one seek instead. Plain C++ so it runs in
// the native tests.
namespace id3 {

// Bytes the tag at the start of `h` (a file's first 10 bytes) takes, header
// and footer included, or 0 when it is not an ID3v2 tag. The size field is
// "syncsafe": four bytes of 7 bits each, so no byte of it can look like an
// MP3 frame sync.
inline uint32_t tagBytes(const uint8_t h[10]) {
    if (h[0] != 'I' || h[1] != 'D' || h[2] != '3') return 0;
    if (h[3] < 2 || h[3] > 4 || h[4] == 0xFF) return 0;
    if ((h[6] | h[7] | h[8] | h[9]) & 0x80) return 0;
    const uint32_t size = ((uint32_t)h[6] << 21) | ((uint32_t)h[7] << 14) |
                          ((uint32_t)h[8] << 7) | (uint32_t)h[9];
    const bool footer = h[3] == 4 && (h[5] & 0x10);   // v2.4 only
    return 10 + size + (footer ? 10 : 0);
}

}  // namespace id3
