#include "core/Identity.h"
#include <config.h>
#include <mbedtls/md.h>

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
    group_ = prefs_.getString("group", "");
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

void Identity::setGroup(const String& g) {
    group_ = g;
    group_.trim();
    prefs_.putString("group", group_);
}

// Turn the group name into the access-point password every module in that
// group will use. Same group -> same password on every board, so linking a
// module is one command and nothing has to be typed twice or shared by hand.
//
// This is what makes automatic linking safe. A module hunting for a neighbour
// to lean on can only ever get INTO a group-mate's access point, and another
// company's modules standing in the same room cannot get into ours: they do
// not have our group name, so they cannot derive our password.
//
// It is deliberately NOT a security boundary against an attacker who knows the
// group name — it stops the wrong modules linking up, which is the actual
// problem. Ungrouped boards keep the compiled-in fallback so nothing changes
// for a board that has never been set up.
String Identity::apPassword() const {
    if (!group_.length()) return String(AP_FALLBACK_PASS);
    uint8_t out[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 0);
    mbedtls_md_starts(&ctx);
    mbedtls_md_update(&ctx, (const uint8_t*)"mice-group:", 11);
    mbedtls_md_update(&ctx, (const uint8_t*)group_.c_str(), group_.length());
    mbedtls_md_finish(&ctx, out);
    mbedtls_md_free(&ctx);
    // 16 hex chars: comfortably above WPA2's 8-character minimum, and short
    // enough to read off a screen when someone has to type it into a phone.
    String pass;
    for (int i = 0; i < 8; i++) {
        char b[3];
        snprintf(b, sizeof(b), "%02x", out[i]);
        pass += b;
    }
    return pass;
}
