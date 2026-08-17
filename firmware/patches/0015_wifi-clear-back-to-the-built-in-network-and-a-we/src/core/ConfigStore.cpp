#include "core/ConfigStore.h"

// yaml key -> NVS key (NVS keys are limited to 15 chars)
struct KeyMap { const char* yaml; const char* nvs; };
static const KeyMap MAP[] = {
    {"encoder", "encoder"},          // 1 = encoder fitted, 0 = limits-only lift
    {"leds", "leds"},
    {"speed", "speed"},              // travel PWM
    {"speed_mms", "spdmms"},         // travel speed mm/s (overrides pwm when > 0)
    {"stages", "stages"},
    {"stage_mm", "stagemm"},         // rack travel between stages
    {"mm_per_rev", "mmrev"},         // rack mm per pinion rev (PI*module*teeth)
    {"counts_per_rev", "cpr"},       // encoder counts per pinion rev
    {"max_rpm", "maxrpm"},           // pinion RPM at full PWM
    {"counts_per_stage", "cps"},     // explicit override, normally derived
    {"volume", "volume"},
    {"speed_dps", "spddps"},         // nong: deg/s used when a POSE has no T
    {"max_dps", "maxdps"},           // nong: physical servo limit, floor for move times
    {"link", "link"},                // nong: 1 = leader, repeat poses on RS485
    {"peer", "peer"},                // nong: partner module id (0 = broadcast)
};

void ConfigStore::begin() {
    prefs_.begin("modcfg", false);
}

const char* ConfigStore::nvsKey(const String& yamlKey) const {
    for (auto& m : MAP)
        if (yamlKey == m.yaml) return m.nvs;
    return nullptr;
}

bool ConfigStore::set(const String& key, float value) {
    const char* k = nvsKey(key);
    if (!k) return false;
    prefs_.putFloat(k, value);
    return true;
}

bool ConfigStore::clear(const String& key) {
    const char* k = nvsKey(key);
    if (!k) return false;
    prefs_.remove(k);
    return true;
}

void ConfigStore::clearAll() {
    for (auto& m : MAP) prefs_.remove(m.nvs);
}

bool ConfigStore::applyTo(JsonDocument& doc) {
    bool any = false;
    for (auto& m : MAP) {
        if (prefs_.isKey(m.nvs)) {
            doc[m.yaml] = prefs_.getFloat(m.nvs);
            any = true;
        }
    }
    return any;
}

String ConfigStore::list() {
    String out;
    for (auto& m : MAP) {
        if (prefs_.isKey(m.nvs)) {
            if (out.length()) out += ' ';
            float v = prefs_.getFloat(m.nvs);
            // integers without decimals, fractions with two
            out += String(m.yaml) + "=" + (v == (long)v ? String((long)v) : String(v, 2));
        }
    }
    return out.length() ? out : "(no overrides stored)";
}
