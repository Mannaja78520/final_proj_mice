#include "core/Identity.h"

String Identity::defaultName() {
    uint64_t mac = ESP.getEfuseMac(); // byte 0 first; last 3 bytes are unique per chip
    char buf[16];
    snprintf(buf, sizeof(buf), "MOD-%02X%02X%02X",
             (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
    return String(buf);
}

void Identity::begin() {
    prefs_.begin("module", false);
    // MAC-derived defaults so freshly flashed boards don't collide on the bus
    uint8_t defId = (uint8_t)((ESP.getEfuseMac() >> 40) % 247) + 1; // 1..247
    id_    = prefs_.getUChar("id", defId);
    name_  = prefs_.getString("name", defaultName());
    type_  = prefs_.getString("type", "blank");
    wssid_ = prefs_.getString("wssid", "");
    wpass_ = prefs_.getString("wpass", "");
    wmode_ = prefs_.getString("wmode", "on");
}

void Identity::setId(uint8_t id) {
    if (id < 1) id = 1;
    if (id > 247) id = 247;
    id_ = id;
    prefs_.putUChar("id", id_);
}

void Identity::setName(const String& n) {
    name_ = n.length() ? n : defaultName();
    prefs_.putString("name", name_);
}

void Identity::setType(const String& t) {
    type_ = t;
    type_.toLowerCase();
    prefs_.putString("type", type_);
}

void Identity::setWifi(const String& ssid, const String& pass) {
    wssid_ = ssid;
    wpass_ = pass;
    prefs_.putString("wssid", wssid_);
    prefs_.putString("wpass", wpass_);
}

void Identity::setWifiMode(const String& m) {
    wmode_ = (m == "off" || m == "ap") ? m : "on";
    prefs_.putString("wmode", wmode_);
}

String Identity::hostname() const {
    String h;
    for (size_t i = 0; i < name_.length(); i++) {
        char c = name_[i];
        if (isalnum(c)) h += (char)tolower(c);
        else if (h.length() && h[h.length() - 1] != '-') h += '-';
    }
    while (h.length() && h[h.length() - 1] == '-') h.remove(h.length() - 1);
    if (!h.length()) h = "module-" + String(id_);
    return h;
}
