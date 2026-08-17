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
    bool clear(const String& key);
    void clearAll();
    // Copy stored overrides into doc (same shape as module.yaml). True if any.
    bool applyTo(JsonDocument& doc);
    String list();

private:
    Preferences prefs_;
    const char* nvsKey(const String& yamlKey) const;
};
