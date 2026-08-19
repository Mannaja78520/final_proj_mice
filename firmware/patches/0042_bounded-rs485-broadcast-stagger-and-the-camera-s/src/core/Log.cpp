#include "core/Log.h"

#include "core/PortWrite.h"

// The half that needs a board. Everything about WHAT the line looks like is in
// Log.h, where the PC test can reach it; this is only how it reaches the wire.
//
// 256 bytes on the stack, deliberately: mlog::line is called from the WiFi
// event task and from the async web server task, whose stacks are ~4 KB. A
// bigger buffer would have to be checked against the task high-water marks
// first. A message longer than this is truncated with a visible ... rather
// than dropped — see vformat.
//
// ONE write, through mice::writeOnce — the same call the REPLY path uses. That
// rule and the reason for it live in core/PortWrite.h, once, rather than being
// restated here and in main.cpp where half of it could be lost.
void mlog::line(Tag tag, const char* fmt, ...) {
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    const size_t n = vformat(buf, sizeof(buf), tag, fmt, ap);
    va_end(ap);
    if (n) mice::writeOnce(buf, n);
}
