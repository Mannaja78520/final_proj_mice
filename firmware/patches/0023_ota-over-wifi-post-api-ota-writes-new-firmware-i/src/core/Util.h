#pragma once
#include <Arduino.h>

namespace Util {
    // Split a command line on spaces. Returns token count (<= maxTok).
    int tokenize(const String& line, String argv[], int maxTok);
    // Re-join argv[start..argc-1] with single spaces (for names / file paths).
    String joinFrom(String argv[], int argc, int start);
    // Absolute path, no "..", sane length — for SD paths coming from the network.
    bool safePath(const String& p);
    // Escape ", \ and drop control chars for hand-built JSON strings.
    String jsonEscape(const String& s);
}
