#include "core/Log.h"

#include <Arduino.h>

// The half that needs a board. Everything about WHAT the line looks like is in
// Log.h, where the PC test can reach it; this is only how it reaches the wire.
//
// 256 bytes on the stack, deliberately: mlog::line is called from the WiFi
// event task and from the async web server task, whose stacks are ~4 KB. A
// bigger buffer would have to be checked against the task high-water marks
// first. A message longer than this is truncated with a visible ... rather
// than dropped — see vformat.
//
// ONE write. Serial.write(buf, len) puts the whole line into the UART queue
// under one lock, so no other task can get inside it. That is the entire point
// of this file: Serial.println is two writes, and the second one is where a
// WiFi event used to glue its log onto the end of a command reply.
void mlog::line(Tag tag, const char* fmt, ...) {
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    const size_t n = vformat(buf, sizeof(buf), tag, fmt, ap);
    va_end(ap);
    if (n) Serial.write(reinterpret_cast<const uint8_t*>(buf), n);
}
