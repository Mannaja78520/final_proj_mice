#include "core/ConfigStore.h"

// yaml key -> NVS key (NVS keys are limited to 15 chars), plus the range the
// value has to be inside.
//
// Every other setting command validates: SERVO, RATE, RANGE and JCFG all
// refuse a value outside what the hardware can do. CFG did not — it wrote any
// float straight to NVS. `CFG max_dps 100000` therefore survived a reboot and
// then made NongModule::minDuration() collapse to the floor, so every POSE
// slammed all ten joints at full servo speed. A number typed into a console
// should never be able to do that.
struct KeyMap { const char* yaml; const char* nvs; float lo; float hi; };
static const KeyMap MAP[] = {
    {"encoder", "encoder", 0, 1},          // 1 = encoder fitted, 0 = limits-only lift
    {"leds", "leds", 0, 1000},
    {"speed", "speed", 0, 255},            // travel PWM
    {"speed_mms", "spdmms", 0, 5000},      // travel speed mm/s (overrides pwm when > 0)
    {"stages", "stages", 0, 64},
    {"stage_mm", "stagemm", 0, 100000},    // rack travel between stages
    {"mm_per_rev", "mmrev", 0.01f, 10000}, // rack mm per pinion rev (PI*module*teeth)
    {"counts_per_rev", "cpr", 1, 1000000}, // encoder counts per pinion rev
    {"max_rpm", "maxrpm", 1, 100000},      // pinion RPM at full PWM
    {"counts_per_stage", "cps", 0, 10000000},  // explicit override, normally derived
    {"volume", "volume", 0, 100},
    {"speed_dps", "spddps", 1, 1000},      // nong: deg/s used when a POSE has no T
    // nong: physical servo limit, and the floor for every move time. A big
    // value here does not make the arm faster, it removes the protection.
    {"max_dps", "maxdps", 1, 1000},
    {"link", "link", 0, 1},                // nong: 1 = leader, repeat poses on RS485
    {"peer", "peer", 0, 247},              // nong: partner module id (0 = broadcast)
};

String ConfigStore::keys() const {
    String out;
    for (auto& m : MAP) {
        if (out.length()) out += " ";
        out += m.yaml;
    }
    return out;
}

void ConfigStore::begin() {
    prefs_.begin("modcfg", false);
}

const char* ConfigStore::nvsKey(const String& yamlKey) const {
    for (auto& m : MAP)
        if (yamlKey == m.yaml) return m.nvs;
    return nullptr;
}

bool ConfigStore::set(const String& key, float value) {
    return set(key, value, nullptr);
}

bool ConfigStore::set(const String& key, float value, String* why) {
    for (auto& m : MAP) {
        if (key != m.yaml) continue;
        // NaN fails every comparison, so test for the good case, not the bad
        // one: `!(value >= lo && value <= hi)` rejects NaN, `value < lo ||
        // value > hi` would let it through.
        if (!(value >= m.lo && value <= m.hi)) {
            if (why) *why = "ERR " + key + " must be between " + String(m.lo) +
                            " and " + String(m.hi);
            return false;
        }
        prefs_.putFloat(m.nvs, value);
        return true;
    }
    if (why) *why = "ERR unknown setting " + key;
    return false;
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
