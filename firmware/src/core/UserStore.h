#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// Login accounts for the module's Setup page, stored in the ESP32's own
// memory (NVS) so they persist and work from any device — no SD card needed.
// Seeded with the default admin manny/12345678 on first boot. Any logged-in
// user can add more users. Passwords must not contain spaces (the command
// tokenizer splits on them).
class UserStore {
public:
    void begin();
    bool verify(const String& user, const String& pass);
    bool add(const String& user, const String& pass);   // false if exists / invalid
    bool remove(const String& user);                     // false if last / not found
    bool setPass(const String& user, const String& pass);
    String listJson();                                   // ["manny","bob"]

    // True while ANY account still has the password the firmware ships with.
    //
    // Checked by VALUE, not by a flag set when the account was created. A flag
    // only knows about boards this firmware set up: a board that has been in
    // service for a year already had its account, so it would have kept
    // 12345678 and never been asked — the boards most likely to be running the
    // shipped password are exactly the ones a flag would miss.
    bool firstPassword();
    static const char* shippedPassword() { return "12345678"; }
    static int minPassLength() { return 8; }

private:
    Preferences prefs_;
    JsonDocument users_;   // { "manny": "12345678", ... }
    void save();
    static bool validName(const String& s);
    static bool validPass(const String& s);
};

extern UserStore users;
