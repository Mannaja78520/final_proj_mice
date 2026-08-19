#pragma once
#include <Arduino.h>
#include <Preferences.h>

// Persistent module identity, stored in the ESP32 NVS flash ("who am I").
// id   : RS485 address 1..247 (0 / '*' is broadcast)
// name : human readable, also used for mDNS hostname and the AP SSID
// type : which Module implementation to boot ("lift", ... future modules)
//
// First boot (nothing in NVS yet): every board gets a unique default from its
// factory MAC — name "MOD-XXXXXX" (last 3 MAC bytes) and an id derived from
// the last MAC byte, with type "blank" (no hardware assumptions). Pick the
// real type/name/id later from the website or RS485 (SET TYPE lift, ...).
class Identity {
public:
    void begin();

    static String defaultName(); // "MOD-XXXXXX" from the chip MAC

    // The chip's own MAC, as twelve hex digits. The ONE identifier on a
    // board that no one can change: the id is a byte someone sets, the
    // name is typed, the type is chosen. The hub needs it to tell that
    // the board on this cable and the board at that address are one
    // board - and to tell that two boards which share a default id are
    // not.
    static String chip();

    uint8_t id() const { return id_; }
    const String& name() const { return name_; }
    const String& type() const { return type_; }
    const String& wifiSsid() const { return wssid_; }
    const String& wifiPass() const { return wpass_; }
    const String& wifiMode() const { return wmode_; } // "on" | "off" | "ap"

    // The GROUP this module belongs to — one installation, one company.
    //
    // It is what makes automatic module-to-module linking safe: the fallback
    // access point's password is DERIVED from the group (see apPassword), so
    // a module can hunt for a neighbour to lean on and only ever get into one
    // that belongs to the same group. Someone else's modules on the same site
    // simply will not let it in, and it cannot let theirs into ours.
    //
    // Empty = ungrouped, which keeps the old shared fallback password so a
    // board that has never been set up still behaves exactly as before.
    const String& group() const { return group_; }
    void setGroup(const String& g);

    // AP password for this module: derived from the group, or the compiled-in
    // fallback when ungrouped. Same group -> same password, on every board,
    // with nothing to distribute by hand.
    String apPassword() const;

    void setId(uint8_t id);
    void setName(const String& n);
    void setType(const String& t);      // takes effect after reboot
    void setWifi(const String& ssid, const String& pass);
    void setWifiMode(const String& m);  // takes effect after reboot

    // name sanitized for mDNS / AP SSID: lowercase alnum and '-'
    String hostname() const;

private:
    Preferences prefs_;
    uint8_t id_ = 1;
    String name_, type_;
    String wssid_, wpass_, wmode_, group_;
};
