#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <config.h>
#include "modules/Module.h"

class SDStore;

// A hand-posed copy of the nong: the same 10 joints, a potentiometer on each
// instead of a servo. It moves nothing. It answers POSE? exactly like the
// robot does, so Nong Studio reads the dummy with the code it already uses to
// read the robot, and a person can pose the robot by bending the dummy.
// The robot's limits and speed still decide what the robot does: the dummy
// only ever REPORTS angles (clamped to its own copy of the limits).
class DummyModule : public Module {
public:
    static const int N = 10;   // the nong's joints, same order (NONG_JOINT_NAMES)

    explicit DummyModule(SDStore* sd) : sd_(sd) {}
    const char* type() const override { return "dummy"; }

    void begin() override;
    void loop() override;
    bool handleCommand(String argv[], int argc, String& reply) override;
    void addCapabilities(JsonArray caps) override;
    void status(JsonObject o) override;

    struct CalBlob {
        uint16_t magic;            // 'DC' - anything else is ignored
        uint16_t version;
        int16_t ch[N];
        float zero[N], span[N], lo[N], hi[N];
        int8_t dir[N];
        int16_t muxSig, muxSel[4];
    };
    static const uint16_t CAL_MAGIC = 0x4443;   // 'D','C'
    static const uint16_t CAL_VERSION = 1;

private:
    SDStore* sd_;
    int ch_[N] = DUMMY_CH_DEF;        // mux channel, or ADC GPIO with no mux
    float zero_[N], span_[N];
    float lo_[N] = NONG_MIN_DEF;      // the robot's own limits by default
    float hi_[N] = NONG_MAX_DEF;
    int dir_[N];
    int muxSig_ = DUMMY_MUX_SIG;      // -1 = no mux: ch_ is a GPIO
    int muxSel_[4] = DUMMY_MUX_SEL;

    float raw_[N];                    // filtered reading, -1 = no pot
    bool primed_ = false;             // first tick seeds the filter
    uint32_t lastTick_ = 0;

    int jointIndex(const String& token) const;   // "3"|"L_EL_P" -> 0-based
    bool wired(int i) const;
    int readChannel(int i);
    float degOf(int i) const;
    void setupPins();
    void defaults();
    void save();
    bool load();
    String calJson() const;
};
