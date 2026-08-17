#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Encoder.h>
#include <motor.h>
#include <config.h>
#include "modules/Module.h"
#include "core/HwConfig.h"
#include "core/RgbStrip.h"
#include "core/AudioPlayer.h"

class SDStore;

// Lift module: motor up/down between stages, RGB strip, speaker.
//
// Stage tracking: encoder counts, zeroed at the bottom limit switch.
// stage = round(counts / counts_per_stage); -1 until homed.
// GOTO auto-homes first if the position reference is unknown.
//
// Commands (via CommandRouter, so identical over RS485 / web / serial):
//   UP | DOWN | STOP | HOME
//   GOTO <stage>
//   STAGE?                    -> current stage number
//   SPEED <pwm>               -> travel speed as raw PWM (100..1023)
//   SPEED <v> MS|MMS          -> travel speed in m/s (or mm/s); e.g. SPEED 0.2 MS
//   SPEED?                    -> current speed, both units + time per stage
//   TIME? [stage]             -> estimated travel time (to <stage>, or per stage)
//   RGB <r> <g> <b> [bright]
//   RGB BRIGHT <0-255>
//   RGB EFFECT solid|rainbow|chase|breathe|off
//   PLAY <file>|PLAY STOP     -> file in /music if no absolute path given
//   VOL <0-100>
//
// Speed <-> m/s mapping is open loop: v = pwm/PWM_Max * (max_rpm/60 * mm_per_rev).
// Calibrate max_rpm (pinion RPM at full PWM) for accurate m/s; the status JSON
// reports the encoder-measured speed (vel_mms) to help with that.
class LiftModule : public Module {
public:
    explicit LiftModule(SDStore* sd) : sd_(sd) {}
    const char* type() const override { return "lift"; }

    void begin() override;
    void loop() override;
    bool handleCommand(String argv[], int argc, String& reply) override;
    void addCapabilities(JsonArray caps) override;
    void status(JsonObject o) override;
    bool busy() override;
    void applySettings(JsonVariant s) override;

private:
    enum State { IDLE, MOVE_UP, MOVE_DOWN, MOVE_GOTO, HOMING };

    SDStore* sd_;
    Controller* motor_ = nullptr;
    ESP32Encoder enc_;
    RgbStrip rgb_;
    AudioPlayer audio_;

    State state_ = IDLE;
    long targetCounts_ = 0;
    int targetStage_ = -1;
    int pendingStage_ = -1; // GOTO issued before homing: run after HOME finishes
    bool homed_ = false;

    // settings (see /data/module.yaml and the CFG command)
    bool hasEnc_ = LIFT_HAS_ENCODER;      // no encoder: limits-only motion
    int speed_ = LIFT_DEFAULT_SPEED;      // travel PWM, used when speedMms_ == 0
    float speedMms_ = 0;                  // travel speed in mm/s (0 = PWM mode)
    int stages_ = LIFT_DEFAULT_STAGES;
    float stageMm_ = LIFT_STAGE_MM;       // rack travel between stages
    float mmPerRev_ = PINION_MM_PER_REV;  // rack mm per pinion revolution
    float countsPerRev_ = COUNTS_PER_REV * GEAR_RATIO; // encoder counts per pinion rev
    float maxRpm_ = PINION_MAX_RPM;       // pinion RPM at full PWM
    long countsPerStage_ = 0;             // derived from stage_mm unless set explicitly
    bool cpsExplicit_ = false;
    uint16_t numLeds_ = RGB_DEFAULT_LEDS;
    uint8_t volume_ = 70;

    long tolCounts_ = 40;                 // derived from LIFT_TOL_MM
    long slowCounts_ = 800;               // derived from LIFT_SLOW_MM
    float velMms_ = 0;                    // encoder-measured rack speed
    long velLastCounts_ = 0;
    uint32_t velLastMs_ = 0;

    bool limitTop() const { return digitalRead(hw.pins.limitTop) == LOW; }
    bool limitDown() const { return digitalRead(hw.pins.limitDown) == LOW; }
    long counts() const;
    int currentStage() const;
    const char* stateName() const;
    float cpm() const;             // encoder counts per mm of rack travel
    float maxMms() const;          // estimated rack speed at full PWM
    float estMms(int pwm) const;   // estimated rack speed at a given PWM
    int travelPwm() const;         // effective travel PWM from the speed settings
    float posMm() const;
    void deriveGeometry();
    void measureVelocity();
    void stopMotor();
    void startGoto(int stage);
    void updateMotion();
};
