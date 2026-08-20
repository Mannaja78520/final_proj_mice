#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// Module settings stored on the chip (NVS) so a module works and keeps its
// configuration WITHOUT an SD card. Same keys as /data/module.yaml.
//
// Precedence at boot: built-in defaults < /data/module.yaml (if a card is
// present) < CFG values stored here — an explicit "CFG leds 60" always wins.
//
// Commands: CFG            -> list stored overrides
//           CFG <key> <n>  -> store; keys: leds speed speed_mms stages stage_mm
//                             mm_per_rev counts_per_rev max_rpm counts_per_stage volume
//           CFG CLEAR [key]-> remove one / all
class ConfigStore {
public:
    void begin();
    bool set(const String& key, float value);
    // Same, but says WHY it refused — an unknown key and an out-of-range value
    // are different problems and need different words.
    bool set(const String& key, float value, String* why);
    bool clear(const String& key);
    void clearAll();
    // Copy stored overrides into doc (same shape as module.yaml). True if any.
    bool applyTo(JsonDocument& doc);
    String list();
    // Every key this store accepts, from the one table that defines them.
    // The CFG command used to print a hand-typed list, which is a second
    // copy of a list that already exists - and the kind that goes stale
    // silently, because a missing key only shows up when somebody is
    // already lost enough to have asked for help.
    String keys() const;

private:
    Preferences prefs_;
    const char* nvsKey(const String& yamlKey) const;
};
