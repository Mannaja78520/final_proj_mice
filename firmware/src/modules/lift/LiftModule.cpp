#include "modules/lift/LiftModule.h"
#include "core/SDStore.h"
#include "core/HwConfig.h"
#include "core/Util.h"
#include <driver/gpio.h>

void LiftModule::applySettings(JsonVariant s) {
    if (s.isNull()) return;
    // Validate before casting: zero/negative/NaN/overflow never disable the guard.
    for (const char* key : {"travel_timeout_ms", "home_timeout_ms"}) {
        if (s[key].isNull()) continue;
        const double value = s[key].as<double>();
        if (!(value >= LIFT_TIMEOUT_MIN_MS && value <= LIFT_TIMEOUT_MAX_MS)) continue;
        if (String(key) == "travel_timeout_ms") travelTimeoutMs_ = (uint32_t)value;
        else homeTimeoutMs_ = (uint32_t)value;
    }
    hasEnc_        = s["encoder"] | hasEnc_;
    speed_         = s["speed"] | speed_;
    speedMms_      = s["speed_mms"] | speedMms_;
    stages_        = s["stages"] | stages_;
    stageMm_       = s["stage_mm"] | stageMm_;
    mmPerRev_      = s["mm_per_rev"] | mmPerRev_;
    countsPerRev_  = s["counts_per_rev"] | countsPerRev_;
    maxRpm_        = s["max_rpm"] | maxRpm_;
    numLeds_       = s["leds"] | numLeds_;
    volume_        = s["volume"] | volume_;
    if (!s["counts_per_stage"].isNull()) { // explicit override beats stage_mm
        countsPerStage_ = s["counts_per_stage"].as<long>();
        cpsExplicit_ = true;
    }
    if (speed_ < 100) speed_ = 100;
    if (speed_ > PWM_Max) speed_ = PWM_Max;
    if (stages_ < 2) stages_ = 2;
}

float LiftModule::cpm() const {
    return (mmPerRev_ > 0.01f) ? countsPerRev_ / mmPerRev_ : 1.0f;
}

float LiftModule::maxMms() const {
    return maxRpm_ / 60.0f * mmPerRev_;
}

float LiftModule::estMms(int pwm) const {
    return maxMms() * pwm / PWM_Max;
}

int LiftModule::travelPwm() const {
    if (speedMms_ > 0 && maxMms() > 1) {
        int p = (int)lroundf(speedMms_ / maxMms() * PWM_Max);
        return constrain(p, 100, PWM_Max);
    }
    return speed_;
}

float LiftModule::posMm() const {
    return counts() / cpm();
}

void LiftModule::deriveGeometry() {
    if (!cpsExplicit_) countsPerStage_ = lroundf(stageMm_ * cpm());
    if (countsPerStage_ < 1) countsPerStage_ = 1;
    tolCounts_ = max(4L, (long)lroundf(LIFT_TOL_MM * cpm()));
    slowCounts_ = max(tolCounts_ * 4, (long)lroundf(LIFT_SLOW_MM * cpm()));
}

void LiftModule::begin() {
    if (hw.pins.limitTop >= 0 && HwConfig::pinUsable(hw.pins.limitTop, false)) pinMode(hw.pins.limitTop, INPUT_PULLUP);
    if (hw.pins.limitDown >= 0 && HwConfig::pinUsable(hw.pins.limitDown, false)) pinMode(hw.pins.limitDown, INPUT_PULLUP);

    if (hasEnc_) {
        ESP32Encoder::useInternalWeakPullResistors = puType::up;
        enc_.attachFullQuad(hw.pins.encA, hw.pins.encB);
        enc_.setCount(0);
    }

    motor_ = new Controller(Controller::Drive2pin, PWM_FREQUENCY, PWM_BITS,
                            MOTOR_INV, MOTOR_BRAKE, hw.pins.motorPwm, hw.pins.motorA, hw.pins.motorB);
    motor_->spin(0);

    rgb_.begin(numLeds_);
    audio_.begin(sd_);
    audio_.setVolume(volume_);
    deriveGeometry();
}

long LiftModule::counts() const {
    if (!hasEnc_) return 0;
    int64_t c = const_cast<ESP32Encoder&>(enc_).getCount();
    return MOTOR_ENCODER_INV ? (long)-c : (long)c;
}

int LiftModule::currentStage() const {
    if (faultReason_) return -1;
    if (!hasEnc_) {
        // without an encoder the position is only known at the endpoints
        if (limitDown()) return 0;
        if (limitTop()) return stages_ - 1;
        return -1;
    }
    if (!homed_ || countsPerStage_ <= 0) return -1;
    long c = counts();
    int st = (int)((c + countsPerStage_ / 2) / countsPerStage_);
    if (st < 0) st = 0;
    if (st > stages_ - 1) st = stages_ - 1;
    return st;
}

const char* LiftModule::stateName() const {
    if (faultReason_) return "fault";
    switch (state_) {
        case MOVE_UP:   return "up";
        case MOVE_DOWN: return "down";
        case MOVE_GOTO: return "goto";
        case HOMING:    return "homing";
        default:        return "idle";
    }
}

bool LiftModule::busy() {
    return faultReason_ || state_ != IDLE;
}

void LiftModule::stopMotor() {
    if (motor_) motor_->spin(0);
    motionArmed_ = false;
    state_ = IDLE;
    targetStage_ = -1;
}

void LiftModule::startGoto(int stage) {
    startMotion(MOVE_GOTO);
    targetStage_ = stage;
    targetCounts_ = (long)stage * countsPerStage_;
}

bool LiftModule::limitsValid() const {
    return hw.pins.limitTop >= 0 && hw.pins.limitDown >= 0 &&
        hw.pins.limitTop != hw.pins.limitDown &&
        GPIO_IS_VALID_GPIO(hw.pins.limitTop) && GPIO_IS_VALID_GPIO(hw.pins.limitDown) &&
        HwConfig::pinUsable(hw.pins.limitTop, false) && HwConfig::pinUsable(hw.pins.limitDown, false);
}

void LiftModule::startMotion(State next) {
    state_ = next;
    targetStage_ = -1;
    motionStartedMs_ = millis();
    motionTimeoutMs_ = next == HOMING ? homeTimeoutMs_ : travelTimeoutMs_;
    motionArmed_ = true;
}

void LiftModule::latchFault(const char* reason) {
    stopMotor();
    pendingStage_ = -1;
    targetCounts_ = 0;
    homed_ = false;
    faultReason_ = reason;
}

bool LiftModule::motionReady(String& reply) {
    if (!faultReason_ && !motor_) latchFault("not_ready");
    if (!faultReason_ && !limitsValid()) latchFault("limits_missing");
    if (!faultReason_ && limitTop() && limitDown()) latchFault("limits_conflict");
    if (faultReason_) { reply = String("ERR lift fault ") + faultReason_ + "; inspect, STOP, then FAULT CLEAR"; return false; }
    if (state_ != IDLE) { reply = "ERR lift moving; STOP before a new motion"; return false; }
    return true;
}

bool LiftModule::handleMotionCommand(String argv[], int argc, String& reply) {
    if (argc < 1) return false;
    const String& cmd = argv[0];
    if (cmd == "FAULT?") {
        reply = faultReason_ ? String("FAULT ") + faultReason_ : String("OK no fault");
        return true;
    }
    if (cmd == "STOP") {
        pendingStage_ = -1;
        stopMotor();
        silence();
        reply = "OK stopped";
        return true;
    }
    if (cmd == "FAULT") {
        if (argc != 2 || !argv[1].equalsIgnoreCase("CLEAR")) { reply = "ERR usage: FAULT CLEAR"; return true; }
        if (state_ != IDLE) { reply = "ERR STOP before FAULT CLEAR"; return true; }
        if (!motor_ || !limitsValid()) { latchFault("limits_missing"); reply = "ERR limit inputs not configured"; return true; }
        if (limitTop() && limitDown()) { latchFault("limits_conflict"); reply = "ERR both limits asserted; inspect before clearing"; return true; }
        stopMotor(); pendingStage_ = -1; homed_ = false;
        faultReason_ = nullptr;
        reply = "OK fault cleared; HOME required for position reference";
        return true;
    }
    if (cmd != "UP" && cmd != "DOWN" && cmd != "HOME" && cmd != "GOTO") return false;
    if (!motionReady(reply)) return true;
    if (cmd == "GOTO") {
        char* end = nullptr;
        const long stage = argc == 2 ? strtol(argv[1].c_str(), &end, 10) : -1;
        if (argc != 2 || !argv[1].length() || !end || *end || stage < 0 || stage >= stages_) {
            reply = "ERR usage: GOTO <stage 0-" + String(stages_ - 1) + ">";
            return true;
        }
        pendingStage_ = -1;
        if (!hasEnc_) {
            if (stage != 0 && stage != stages_ - 1) { reply = "ERR no encoder: only endpoint stages"; return true; }
            startMotion(stage == 0 ? MOVE_DOWN : MOVE_UP);
        } else if (!homed_) {
            pendingStage_ = (int)stage;
            startMotion(HOMING);
        } else startGoto((int)stage);
        reply = "OK goto " + String(stage);
        return true;
    }
    pendingStage_ = -1;
    startMotion(cmd == "UP" ? MOVE_UP : cmd == "DOWN" ? MOVE_DOWN : HOMING);
    reply = "OK " + String(cmd == "HOME" ? "homing" : cmd == "UP" ? "up" : "down");
    return true;
}

bool LiftModule::handleCommand(String argv[], int argc, String& reply) {
    if (handleMotionCommand(argv, argc, reply)) return true;
    String& cmd = argv[0];
    if (cmd == "STAGE?" || cmd == "STAGE") {
        reply = String(currentStage());
        return true;
    }
    if (cmd == "SPEED" || cmd == "SPEED?") {
        if (cmd == "SPEED?" || argc < 2) {
            int p = travelPwm();
            float v = estMms(p);
            reply = String(speedMms_ > 0 ? "SPEED m/s mode" : "SPEED pwm mode") +
                    ": pwm=" + String(p) + " ~" + String(v / 1000.0f, 2) + " m/s, " +
                    String(stageMm_, 0) + "mm stage in ~" + String(v > 1 ? stageMm_ / v : 0, 1) + "s" +
                    " (max " + String(maxMms() / 1000.0f, 2) + " m/s)";
            return true;
        }
        float v = argv[1].toFloat();
        String unit = argc >= 3 ? argv[2] : String();
        unit.toUpperCase();
        if (unit == "MS" || unit == "M/S" || unit == "MPS") { v *= 1000.0f; unit = "MMS"; }
        if (unit == "MMS") {
            if (v < 1 || v > maxMms() * 1.01f) {
                reply = "ERR range 0.001-" + String(maxMms() / 1000.0f, 2) + " m/s";
                return true;
            }
            speedMms_ = v;
            reply = "OK speed=" + String(v / 1000.0f, 2) + " m/s (pwm " + String(travelPwm()) +
                    ", " + String(stageMm_, 0) + "mm in ~" + String(stageMm_ / v, 1) + "s)";
            return true;
        }
        int pv = (int)v;
        if (pv < 100) pv = 100;
        if (pv > PWM_Max) pv = PWM_Max;
        speed_ = pv;
        speedMms_ = 0; // back to raw PWM mode
        reply = "OK speed pwm=" + String(speed_) + " (~" + String(estMms(speed_) / 1000.0f, 2) + " m/s)";
        return true;
    }
    if (cmd == "TIME?" || cmd == "TIME") {
        float v = estMms(travelPwm());
        if (v < 1) { reply = "ERR speed/mechanics not configured"; return true; }
        float dist = stageMm_; // default: one full stage
        String what = String((int)stageMm_) + " mm";
        if (argc >= 2) {
            int st = argv[1].toInt();
            if (st < 0 || st > stages_ - 1) { reply = "ERR stage 0-" + String(stages_ - 1); return true; }
            float from = 0; // assumes bottom when the position is unknown
            if (hasEnc_ && homed_) from = posMm();
            else if (limitTop()) from = (stages_ - 1) * stageMm_;
            dist = fabsf(st * stageMm_ - from);
            what = String(dist, 0) + " mm to stage " + String(st);
        }
        reply = "EST " + String(dist / v, 1) + " s (" + what + " @ " + String(v, 0) + " mm/s)";
        return true;
    }
    if (cmd == "RGB") {
        if (argc < 2) { reply = "ERR usage: RGB r g b | RGB EFFECT <name> | RGB BRIGHT <n>"; return true; }
        String sub = argv[1];
        sub.toUpperCase();
        if (sub == "EFFECT") {
            if (argc < 3 || !rgb_.setEffect(argv[2])) {
                reply = "ERR effects: solid rainbow chase breathe off";
                return true;
            }
            reply = "OK effect=" + rgb_.effect();
            return true;
        }
        if (sub == "BRIGHT") {
            if (argc < 3) { reply = "ERR usage: RGB BRIGHT <0-255>"; return true; }
            rgb_.setBrightness((uint8_t)constrain(argv[2].toInt(), 0, 255));
            reply = "OK bright=" + String(rgb_.brightness());
            return true;
        }
        if (argc < 4) { reply = "ERR usage: RGB <r> <g> <b> [bright]"; return true; }
        rgb_.setColor((uint8_t)constrain(argv[1].toInt(), 0, 255),
                      (uint8_t)constrain(argv[2].toInt(), 0, 255),
                      (uint8_t)constrain(argv[3].toInt(), 0, 255));
        if (argc >= 5) rgb_.setBrightness((uint8_t)constrain(argv[4].toInt(), 0, 255));
        reply = "OK rgb set";
        return true;
    }
    // The PLAY/VOL bodies live in AudioPlayer itself (core/AudioPlayer.cpp) so
    // every type that wires a speaker parses them identically.
    if (cmd == "PLAY") { audio_.playCmd(argv, argc, reply); return true; }
    if (cmd == "VOL")  { audio_.volCmd(argv, argc, reply);  return true; }
    if (cmd == "AMP")  { audio_.ampCmd(argv, argc, reply);  return true; }
    if (cmd == "AMP?") { audio_.ampCmd(argv, argc, reply);  return true; }
    if (cmd == "STREAM" || cmd == "STREAM?") { audio_.streamCmd(argv, argc, reply); return true; }
    return false;
}

void LiftModule::updateMotion() {
    if (faultReason_) { if (motor_) motor_->spin(0); return; }
    // Timeout wins even if a switch changes exactly at the deadline; unsigned
    // subtraction handles millis wrap and a move that started at zero.
    if (state_ != IDLE && (!motionArmed_ || (uint32_t)(millis() - motionStartedMs_) >= motionTimeoutMs_)) {
        latchFault(state_ == HOMING ? "home_timeout" : "travel_timeout");
        return;
    }
    if (!limitsValid()) { latchFault("limits_missing"); return; }
    if (limitTop() && limitDown()) { latchFault("limits_conflict"); return; }
    switch (state_) {
        case MOVE_UP:
            if (limitTop()) stopMotor();
            else motor_->spin(travelPwm());
            break;

        case MOVE_DOWN:
            if (limitDown()) {
                enc_.setCount(0);
                homed_ = true;
                stopMotor();
            } else {
                motor_->spin(-travelPwm());
            }
            break;

        case HOMING:
            if (limitDown()) {
                enc_.setCount(0);
                homed_ = true;
                stopMotor();
                if (pendingStage_ >= 0) {
                    int s = pendingStage_;
                    pendingStage_ = -1;
                    if (s > 0) startGoto(s); // stage 0 == home, already there
                }
            } else {
                motor_->spin(-LIFT_SLOW_SPEED);
            }
            break;

        case MOVE_GOTO: {
            long err = targetCounts_ - counts();
            if (err > 0 && limitTop()) { stopMotor(); break; }
            if (err < 0 && limitDown()) {
                enc_.setCount(0);
                homed_ = true;
                stopMotor();
                break;
            }
            if (labs(err) <= tolCounts_) {
                stopMotor();
                break;
            }
            int pwm = (labs(err) > slowCounts_) ? travelPwm() : LIFT_SLOW_SPEED;
            motor_->spin(err > 0 ? pwm : -pwm);
            break;
        }

        case IDLE:
        default:
            break;
    }
}

void LiftModule::measureVelocity() {
    if (!hasEnc_) return;
    uint32_t now = millis();
    if (now - velLastMs_ < 100) return;
    long c = counts();
    float dt = (now - velLastMs_) / 1000.0f;
    velMms_ = (c - velLastCounts_) / cpm() / dt;
    velLastCounts_ = c;
    velLastMs_ = now;
}

void LiftModule::loop() {
    updateMotion();
    measureVelocity();
    rgb_.loop();
    audio_.loop();
}

void LiftModule::addCapabilities(JsonArray caps) {
    caps.add("motion");       // UP/DOWN/STOP/HOME and staged travel
    caps.add("stages");
    caps.add("rgb");          // the LED strip card
    caps.add("audio");        // the speaker card
    if (hasEnc_) caps.add("encoder");
}

void LiftModule::status(JsonObject o) {
    o["state"] = stateName();
    o["fault"] = faultReason_ ? faultReason_ : "";
    o["travel_timeout_ms"] = travelTimeoutMs_;
    o["home_timeout_ms"] = homeTimeoutMs_;
    o["motion_timeout_ms"] = motionArmed_ ? motionTimeoutMs_ : 0;
    o["stage"] = currentStage();
    o["target"] = targetStage_;
    o["stages"] = stages_;
    o["homed"] = homed_;
    o["enc"] = hasEnc_;
    o["encoder"] = counts();
    o["pos_mm"] = (hasEnc_ && homed_) ? posMm() : 0;
    o["stage_mm"] = stageMm_;
    o["speed"] = speed_;                    // stored PWM setting
    o["speed_mms"] = speedMms_;             // commanded mm/s (0 = PWM mode)
    o["speed_pwm"] = travelPwm();           // effective travel PWM
    o["est_mms"] = estMms(travelPwm());     // estimated speed at that PWM
    o["vel_mms"] = velMms_;                 // encoder-measured speed
    float v = estMms(travelPwm());
    o["stage_s"] = v > 1 ? stageMm_ / v : 0; // est. time for one stage
    o["limit_top"] = limitTop();
    o["limit_down"] = limitDown();
    JsonObject rgb = o["rgb"].to<JsonObject>();
    rgb["r"] = rgb_.r();
    rgb["g"] = rgb_.g();
    rgb["b"] = rgb_.b();
    rgb["bright"] = rgb_.brightness();
    rgb["effect"] = rgb_.effect();
    JsonObject audio = o["audio"].to<JsonObject>();
    audio["playing"] = audio_.playing();
    audio["file"] = audio_.current();
    audio["vol"] = audio_.volume();
}
