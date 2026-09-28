#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// Login accounts for the module's Setup page, stored in the ESP32's own
// memory (NVS) so they persist and work from any device — no SD card needed.
// super_admin/admin123 and admin/admin123 are added on every boot where they are
// missing (an old board keeps its own accounts too). Any logged-in
// user can add more users. Passwords must not contain spaces (the command
// tokenizer splits on them).
class UserStore {
public:
    static constexpr const char* ROLE_SUPER = "super_admin";
    static constexpr const char* ROLE_USER = "user";

    void begin();
    bool verify(const String& user, const String& pass);
    bool add(const String& user, const String& pass, const String& role = "user"); // false if exists / invalid
    bool remove(const String& user);                     // false if last / not found / last super_admin
    bool rename(const String& oldName, const String& newName);
    bool setPass(const String& user, const String& pass);
    String listJson(const String& caller = "");          // [{"name":"...","role":"...","mustChange":...}]
    String namesJson();                                  // ["admin","super_admin"]

    String role(const String& user);
    bool isSuper(const String& user);
    int countSupers();
    bool mustChange(const String& user);

    // True while ANY account still has the password the firmware ships with.
    //
    // Checked by VALUE, not by a flag set when the account was created. A flag
    // only knows about boards this firmware set up: a board that has been in
    // service for a year already had its account, so it would have kept
    // 12345678 and never been asked — the boards most likely to be running the
    // shipped password are exactly the ones a flag would miss.
    bool firstPassword();
    static const char* shippedPassword() { return "admin123"; }   // must match UserStore.cpp seeds
    static int minPassLength() { return 8; }

private:
    Preferences prefs_;
    JsonDocument users_;   // { "super_admin": {"role": "super_admin", "salt": "...", "hash": "..."}, ... }
    void save();
    static bool validName(const String& s);
    static bool validPass(const String& s);
};

extern UserStore users;
