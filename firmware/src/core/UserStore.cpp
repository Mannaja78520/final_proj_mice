#include "core/UserStore.h"
#include <mbedtls/md.h>
#include <vector>

UserStore users;

static String genSalt() {
    char salt[17];
    for (int i = 0; i < 8; i++) {
        uint32_t r = esp_random();
        snprintf(salt + i * 2, 3, "%02x", (uint8_t)(r & 0xFF));
    }
    salt[16] = 0;
    return String(salt);
}

static String hashPassword(const String& pass, const String& salt) {
    uint8_t out[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 0);
    mbedtls_md_starts(&ctx);
    mbedtls_md_update(&ctx, (const uint8_t*)salt.c_str(), salt.length());
    mbedtls_md_update(&ctx, (const uint8_t*)pass.c_str(), pass.length());
    mbedtls_md_finish(&ctx, out);
    mbedtls_md_free(&ctx);
    char hex[65];
    for (int i = 0; i < 32; i++) snprintf(hex + i * 2, 3, "%02x", out[i]);
    hex[64] = 0;
    return String(hex);
}

static bool constantTimeEquals(const String& a, const String& b) {
    if (a.length() != b.length()) return false;
    int diff = 0;
    for (size_t i = 0; i < a.length(); i++) {
        diff |= (a[i] ^ b[i]);
    }
    return diff == 0;
}

void UserStore::begin() {
    prefs_.begin("auth", false);
    String blob = prefs_.getString("users", "");
    if (blob.length()) deserializeJson(users_, blob);
    if (!users_.is<JsonObject>()) users_.clear();

    bool changed = false;
    // Migrate legacy plain-text accounts (is<const char*>())
    std::vector<String> keys;
    for (JsonPair kv : users_.as<JsonObject>()) keys.push_back(kv.key().c_str());
    for (const String& name : keys) {
        if (users_[name].is<const char*>()) {
            String plain = users_[name].as<String>();
            String r = (name == "super_admin") ? ROLE_SUPER : ROLE_USER;
            String s = genSalt();
            String h = hashPassword(plain, s);
            JsonObject u = users_[name].to<JsonObject>();
            u["role"] = r;
            u["salt"] = s;
            u["hash"] = h;
            changed = true;
        } else if (users_[name].is<JsonObject>()) {
            JsonObject u = users_[name].as<JsonObject>();
            if (!u["role"].is<const char*>() ||
                (strcmp(u["role"], ROLE_SUPER) != 0 && strcmp(u["role"], ROLE_USER) != 0)) {
                u["role"] = (name == "super_admin") ? ROLE_SUPER : ROLE_USER;
                changed = true;
            }
        }
    }

    // Every board carries both default logins (user 2026-09-17). A board set up
    // earlier (e.g. only manny) gets the MISSING ones added; an existing account
    // is never deleted, and its password is never overwritten.
    bool added = false;
    for (const char* name : {"super_admin", "admin"}) {
        if (!users_[name].is<JsonObject>() && !users_[name].is<const char*>()) {
            String r = (strcmp(name, "super_admin") == 0) ? ROLE_SUPER : ROLE_USER;
            String s = genSalt();
            String h = hashPassword(shippedPassword(), s);
            JsonObject u = users_[name].to<JsonObject>();
            u["role"] = r;
            u["salt"] = s;
            u["hash"] = h;
            added = true;
        }
    }

    if (countSupers() == 0 && users_.as<JsonObject>().size() > 0) {
        const char* first = users_.as<JsonObject>().begin()->key().c_str();
        if (users_["super_admin"].is<JsonObject>()) first = "super_admin";
        users_[first]["role"] = ROLE_SUPER;
        changed = true;
    }

    if (added || changed) save();
}

// Any account still on the shipped password means this board opens to anyone
// who has seen any other board.
bool UserStore::firstPassword() {
    for (JsonPair kv : users_.as<JsonObject>()) {
        if (verify(kv.key().c_str(), shippedPassword())) return true;
    }
    return false;
}

bool UserStore::mustChange(const String& user) {
    return verify(user, shippedPassword());
}

String UserStore::role(const String& user) {
    if (users_[user].is<JsonObject>() && users_[user]["role"].is<const char*>()) {
        return users_[user]["role"].as<String>();
    }
    if (users_[user].is<const char*>()) {
        return (user == "super_admin") ? ROLE_SUPER : ROLE_USER;
    }
    return "";
}

bool UserStore::isSuper(const String& user) {
    return role(user) == ROLE_SUPER;
}

int UserStore::countSupers() {
    int count = 0;
    for (JsonPair kv : users_.as<JsonObject>()) {
        if (kv.value().is<JsonObject>()) {
            if (kv.value()["role"].is<const char*>() &&
                strcmp(kv.value()["role"].as<const char*>(), ROLE_SUPER) == 0) {
                count++;
            }
        } else if (kv.value().is<const char*>()) {
            if (strcmp(kv.key().c_str(), "super_admin") == 0) count++;
        }
    }
    return count;
}

void UserStore::save() {
    String out;
    serializeJson(users_, out);
    prefs_.putString("users", out);
}

bool UserStore::validName(const String& s) {
    if (s.length() < 1 || s.length() > 20) return false;
    for (size_t i = 0; i < s.length(); i++) {
        char c = s[i];
        if (!(isalnum(c) || c == '_' || c == '-')) return false;
    }
    return true;
}

bool UserStore::validPass(const String& s) {
    // Was 1 character. Forcing a change is theatre if the new password can be
    // "x", and 8 is what the shipped one already was, so nothing that works
    // today becomes invalid.
    if ((int)s.length() < minPassLength() || s.length() > 32) return false;
    return s.indexOf(' ') < 0;  // spaces would break the tokenizer
}

bool UserStore::verify(const String& user, const String& pass) {
    if (users_[user].is<const char*>()) {
        return pass == users_[user].as<String>();
    }
    if (!users_[user].is<JsonObject>()) return false;
    JsonObject u = users_[user].as<JsonObject>();
    if (!u["salt"].is<const char*>() || !u["hash"].is<const char*>()) return false;
    String salt = u["salt"].as<String>();
    String want = u["hash"].as<String>();
    String got = hashPassword(pass, salt);
    return constantTimeEquals(want, got);
}

bool UserStore::add(const String& user, const String& pass, const String& role) {
    if (!validName(user) || !validPass(pass)) return false;
    if (users_[user].is<JsonObject>() || users_[user].is<const char*>()) return false;  // already exists
    if (users_.as<JsonObject>().size() >= 16) return false;
    String r = (role == ROLE_SUPER) ? ROLE_SUPER : ROLE_USER;
    String s = genSalt();
    String h = hashPassword(pass, s);
    JsonObject u = users_[user].to<JsonObject>();
    u["role"] = r;
    u["salt"] = s;
    u["hash"] = h;
    save();
    return true;
}

bool UserStore::remove(const String& user) {
    if (!users_[user].is<JsonObject>() && !users_[user].is<const char*>()) return false;
    if (users_.as<JsonObject>().size() <= 1) return false;  // never lock everyone out
    if (isSuper(user) && countSupers() <= 1) return false;  // last super_admin protected
    users_.remove(user);
    save();
    return true;
}

bool UserStore::rename(const String& oldName, const String& newName) {
    if (!users_[oldName].is<JsonObject>() && !users_[oldName].is<const char*>()) return false;
    if (oldName == newName) return true;
    if (!validName(newName)) return false;
    if (users_[newName].is<JsonObject>() || users_[newName].is<const char*>()) return false;  // already exists

    String r = role(oldName);
    String s, h;
    if (users_[oldName].is<JsonObject>()) {
        JsonObject oldObj = users_[oldName].as<JsonObject>();
        s = oldObj["salt"].as<String>();
        h = oldObj["hash"].as<String>();
    } else {
        s = genSalt();
        h = hashPassword(users_[oldName].as<String>(), s);
    }
    users_.remove(oldName);
    JsonObject newObj = users_[newName].to<JsonObject>();
    newObj["role"] = r;
    newObj["salt"] = s;
    newObj["hash"] = h;
    save();
    return true;
}

bool UserStore::setPass(const String& user, const String& pass) {
    if ((!users_[user].is<JsonObject>() && !users_[user].is<const char*>()) || !validPass(pass)) return false;
    // Changing it TO the shipped password is not changing it.
    if (pass == shippedPassword()) return false;
    String s = genSalt();
    String h = hashPassword(pass, s);
    String r = role(user);
    JsonObject u = users_[user].to<JsonObject>();
    u["role"] = r;
    u["salt"] = s;
    u["hash"] = h;
    save();
    return true;
}

String UserStore::listJson(const String& caller) {
    String out = "[";
    bool first = true;
    bool boss = caller.length() == 0 || isSuper(caller);
    for (JsonPair kv : users_.as<JsonObject>()) {
        String name = kv.key().c_str();
        if (!boss && name != caller) continue;
        if (!first) out += ",";
        first = false;
        String r = role(name);
        bool mc = mustChange(name);
        out += "{\"name\":\"" + name + "\",\"role\":\"" + r + "\",\"mustChange\":" + (mc ? "true" : "false") + "}";
    }
    return out + "]";
}

String UserStore::namesJson() {
    String out = "[";
    bool first = true;
    for (JsonPair kv : users_.as<JsonObject>()) {
        if (!first) out += ",";
        first = false;
        out += "\"" + String(kv.key().c_str()) + "\"";
    }
    return out + "]";
}
