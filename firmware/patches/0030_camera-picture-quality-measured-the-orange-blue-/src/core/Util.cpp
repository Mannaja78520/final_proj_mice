#include "core/Util.h"

namespace Util {

int tokenize(const String& line, String argv[], int maxTok) {
    int argc = 0;
    int i = 0, n = line.length();
    while (i < n && argc < maxTok) {
        while (i < n && line[i] == ' ') i++;
        if (i >= n) break;
        int start = i;
        while (i < n && line[i] != ' ') i++;
        argv[argc++] = line.substring(start, i);
    }
    return argc;
}

String joinFrom(String argv[], int argc, int start) {
    String out;
    for (int i = start; i < argc; i++) {
        if (i > start) out += ' ';
        out += argv[i];
    }
    return out;
}

String jsonEscape(const String& s) {
    String out;
    out.reserve(s.length());
    for (size_t i = 0; i < s.length(); i++) {
        char c = s[i];
        if (c == '"' || c == '\\') out += '\\';
        if ((uint8_t)c >= 0x20) out += c;
    }
    return out;
}

bool safePath(const String& p) {
    if (p.length() < 2 || p.length() > 100) return false;
    if (p[0] != '/') return false;
    if (p.indexOf("..") >= 0) return false;
    return true;
}

} // namespace Util
