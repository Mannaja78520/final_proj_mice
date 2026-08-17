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

    uint8_t id() const { return id_; }
    const String& name() const { return name_; }
    const String& type() const { return type_; }
    const String& wifiSsid() const { return wssid_; }
    const String& wifiPass() const { return wpass_; }
    const String& wifiMode() const { return wmode_; } // "on" | "off" | "ap"

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
    String wssid_, wpass_, wmode_;
};
