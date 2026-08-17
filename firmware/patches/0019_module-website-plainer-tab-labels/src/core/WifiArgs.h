#pragma once
// Parsing the arguments of `SET WIFI <ssid> [pass]`, with NO Arduino
// dependency — so it can be compiled and RUN on a PC (`pio test -e native`,
// see firmware/test/test_logic/).
//
// This is here because getting it wrong does not crash and does not look
// wrong. Both of these were real, and both were found by flashing a board
// and watching it fail to join a network that was working perfectly:
//
//   SET WIFI MSI 3058 mypass       -> ssid "MSI", password "3058 mypass"
//   SET WIFI "manny" "qwertyui"    -> password stored as  "qwertyui"
//                                     WITH the quote characters in it
//
// The second is the nastier one: every read-back shows the password you
// meant, the module simply never connects. Network names contain spaces all
// the time ("MSI 3058", "BT Hub 5"), so quoting has to work, and anyone who
// quotes the name will quote the password too.
//
// Rules:
//   * a quoted first argument is the ssid, spaces and all; the rest is the
//     password
//   * an unquoted first argument is the ssid up to the first space
//   * the password is trimmed, and unquoted if it is wrapped in quotes
//   * an empty password means an open network
#include <string>

namespace wifiargs {

inline std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    size_t b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

inline std::string unquote(const std::string& s) {
    if (s.size() >= 2 && s.front() == '"' && s.back() == '"')
        return s.substr(1, s.size() - 2);
    return s;
}

// `rest` is everything after "SET WIFI ". Returns false when there is no ssid.
inline bool parse(const std::string& rest, std::string& ssid, std::string& pass) {
    std::string r = trim(rest);
    if (r.empty()) return false;
    if (r[0] == '"') {
        size_t end = r.find('"', 1);
        if (end == std::string::npos) return false;   // unclosed quote
        ssid = r.substr(1, end - 1);
        pass = trim(r.substr(end + 1));
    } else {
        size_t sp = r.find(' ');
        if (sp == std::string::npos) {
            ssid = r;
            pass = "";
        } else {
            ssid = r.substr(0, sp);
            pass = trim(r.substr(sp + 1));
        }
    }
    pass = unquote(pass);
    return !ssid.empty();
}

}  // namespace wifiargs
