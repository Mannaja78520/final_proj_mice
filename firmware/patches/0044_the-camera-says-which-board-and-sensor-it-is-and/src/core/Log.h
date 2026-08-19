#pragma once
// One log line, one write, one list of subsystem names.
//
// WHY THIS EXISTS
// ---------------
// The firmware logged with Serial.println and Serial.printf at 36 call sites,
// each one typing its own prefix — [boot] [sys] [wifi] [sd] [seq] [ota] [cam].
// Two things went wrong with that, and both were seen on the bench:
//
//   1. Serial.println(x) is print(x) followed by a SEPARATE print of the line
//      ending. A WiFi event runs on another FreeRTOS task and can land between
//      those two writes, gluing its log onto the end of a command reply:
//
//        OK joining lift-test now (WIFI for progress)[wifi] disconnected, reason=8
//
//      main.cpp:emitLine already solved this for REPLIES by building one String
//      and issuing one write. Logs never got the same treatment.
//
//   2. A prefix typed by hand is a prefix that can be typed differently. Anyone
//      reading the port has to match all of them.
//
// So: the tag list lives here once, and mlog::line formats the whole line into
// a single buffer and hands it to the UART in ONE write, which goes into the
// queue under one lock and cannot be split by another task.
//
// ADDING A SUBSYSTEM IS ONE LINE — the list below. The enum and the name table
// are both generated from it, so they cannot disagree.
//
// The formatting half is deliberately free of Arduino: it is plain C, defined
// in this header, so `pio test -e native` can execute it on the PC and assert
// the actual bytes. Only the write itself needs a board.
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

#define MICE_LOG_TAGS(X) X(boot) X(sys) X(wifi) X(sd) X(seq) X(ota) X(cam)

namespace mlog {

enum Tag : unsigned char {
#define MICE_LOG_ENUM(name) name,
    MICE_LOG_TAGS(MICE_LOG_ENUM)
#undef MICE_LOG_ENUM
    TAG_COUNT
};

inline const char* tagName(Tag t) {
    static const char* const NAMES[] = {
#define MICE_LOG_NAME(name) #name,
        MICE_LOG_TAGS(MICE_LOG_NAME)
#undef MICE_LOG_NAME
    };
    return t < TAG_COUNT ? NAMES[t] : "?";
}

// Build "[tag] message\n" into `out`. Returns the length written (not counting
// the NUL). The result ALWAYS ends with exactly one line ending and NEVER
// contains another one:
//
//   * a newline inside a log line reads as two lines to anything parsing this
//     port, and every command here answers with exactly one line (see
//     qc/checks/check_line_protocol.py) — so an embedded newline becomes a
//     space rather than a second, fake reply;
//   * a message too long for the buffer ends in ... so the truncation is
//     visible. Silently losing the end of a diagnostic is how you debug the
//     wrong problem for an hour.
inline size_t vformat(char* out, size_t cap, Tag tag, const char* fmt, va_list ap) {
    if (!out || cap < 8) return 0;
    const size_t room = cap - 2;            // leave the line ending and the NUL

    int n = snprintf(out, room + 1, "[%s] ", tagName(tag));
    size_t len = (n < 0) ? 0 : ((size_t)n > room ? room : (size_t)n);

    int m = vsnprintf(out + len, room - len + 1, fmt, ap);
    bool cut = false;
    if (m < 0) m = 0;
    if ((size_t)m > room - len) { m = (int)(room - len); cut = true; }
    len += (size_t)m;

    for (size_t i = 0; i < len; i++)
        if (out[i] == '\n' || out[i] == '\r') out[i] = ' ';
    if (cut && len >= 3) { out[len - 3] = '.'; out[len - 2] = '.'; out[len - 1] = '.'; }

    out[len++] = '\n';
    out[len] = '\0';
    return len;
}

// The one call site everything else uses. Defined in Log.cpp, which is the only
// part that needs a board.
void line(Tag tag, const char* fmt, ...) __attribute__((format(printf, 2, 3)));

}  // namespace mlog

// LOGF(wifi, ...) rather than mlog::line(mlog::wifi, ...) — short enough that
// nobody is tempted to reach past it for Serial.printf.
#define LOGF(tag, ...) ::mlog::line(::mlog::tag, __VA_ARGS__)
