#include "core/UserStore.h"

UserStore users;

void UserStore::begin() {
    prefs_.begin("auth", false);
    String blob = prefs_.getString("users", "");
    if (blob.length()) deserializeJson(users_, blob);
    if (!users_.is<JsonObject>() || users_.as<JsonObject>().size() == 0) {
        users_.clear();
        users_["manny"] = "12345678";  // default admin
        save();
    }
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
    if (s.length() < 1 || s.length() > 32) return false;
    return s.indexOf(' ') < 0;  // spaces would break the tokenizer
}

bool UserStore::verify(const String& user, const String& pass) {
    if (!users_[user].is<const char*>()) return false;
    return pass == users_[user].as<String>();
}

bool UserStore::add(const String& user, const String& pass) {
    if (!validName(user) || !validPass(pass)) return false;
    if (users_[user].is<const char*>()) return false;  // already exists
    if (users_.as<JsonObject>().size() >= 16) return false;
    users_[user] = pass;
    save();
    return true;
}

bool UserStore::remove(const String& user) {
    if (!users_[user].is<const char*>()) return false;
    if (users_.as<JsonObject>().size() <= 1) return false;  // never lock everyone out
    users_.remove(user);
    save();
    return true;
}

bool UserStore::setPass(const String& user, const String& pass) {
    if (!users_[user].is<const char*>() || !validPass(pass)) return false;
    users_[user] = pass;
    save();
    return true;
}

String UserStore::listJson() {
    String out = "[";
    bool first = true;
    for (JsonPair kv : users_.as<JsonObject>()) {
        if (!first) out += ",";
        first = false;
        out += "\"" + String(kv.key().c_str()) + "\"";
    }
    return out + "]";
}
