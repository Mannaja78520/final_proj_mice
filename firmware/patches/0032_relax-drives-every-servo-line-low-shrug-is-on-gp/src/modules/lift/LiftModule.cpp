#include "modules/lift/LiftModule.h"
#include "core/SDStore.h"
#include "core/HwConfig.h"
#include "core/Util.h"

void LiftModule::applySettings(JsonVariant s) {
    if (s.isNull()) return;
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
    pinMode(hw.pins.limitTop, INPUT_PULLUP);
    pinMode(hw.pins.limitDown, INPUT_PULLUP);

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
    switch (state_) {
        case MOVE_UP:   return "up";
        case MOVE_DOWN: return "down";
        case MOVE_GOTO: return "goto";
        case HOMING:    return "homing";
        default:        return "idle";
    }
}

bool LiftModule::busy() {
    return state_ != IDLE;
}

void LiftModule::stopMotor() {
    motor_->spin(0);
    state_ = IDLE;
    targetStage_ = -1;
}

void LiftModule::startGoto(int stage) {
    targetStage_ = stage;
    targetCounts_ = (long)stage * countsPerStage_;
    state_ = MOVE_GOTO;
}

bool LiftModule::handleCommand(String argv[], int argc, String& reply) {
    String& cmd = argv[0]; // already uppercased by the router

    if (cmd == "UP") {
        pendingStage_ = -1;
        state_ = MOVE_UP;
        reply = "OK up";
        return true;
    }
    if (cmd == "DOWN") {
        pendingStage_ = -1;
        state_ = MOVE_DOWN;
        reply = "OK down";
        return true;
    }
    if (cmd == "STOP") {
        pendingStage_ = -1;
        stopMotor();
        reply = "OK stopped";
        return true;
    }
    if (cmd == "HOME") {
        pendingStage_ = -1;
        state_ = HOMING;
        reply = "OK homing";
        return true;
    }
    if (cmd == "GOTO") {
        if (argc < 2) { reply = "ERR usage: GOTO <stage>"; return true; }
        int stage = argv[1].toInt();
        if (stage < 0 || stage > stages_ - 1) {
            reply = "ERR stage 0-" + String(stages_ - 1);
            return true;
        }
        if (!hasEnc_) {
            // no encoder: only the endpoints are reachable (limit switches)
            pendingStage_ = -1;
            if (stage == 0) {
                state_ = MOVE_DOWN; // travel speed; bottom limit stops + homes
                reply = "OK going down to the bottom limit";
            } else if (stage == stages_ - 1) {
                state_ = MOVE_UP;
                reply = "OK going up to the top limit";
            } else {
                reply = "ERR no encoder: only stage 0 or " + String(stages_ - 1);
            }
            return true;
        }
        if (!homed_) {
            // no position reference yet: home first, then run the goto
            pendingStage_ = stage;
            state_ = HOMING;
            reply = "OK homing first, then goto " + String(stage);
        } else {
            startGoto(stage);
            reply = "OK goto " + String(stage);
        }
        return true;
    }
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
    if (cmd == "PLAY") {
        if (argc < 2) { reply = "ERR usage: PLAY <file>|STOP"; return true; }
        String a = argv[1];
        a.toUpperCase();
        if (a == "STOP") {
            audio_.stop();
            reply = "OK audio stopped";
            return true;
        }
        String path = Util::joinFrom(argv, argc, 1);
        if (!path.startsWith("/")) path = "/music/" + path;
        if (!audio_.play(path)) {
            reply = "ERR cannot play " + path;
            return true;
        }
        reply = "OK playing " + path;
        return true;
    }
    if (cmd == "VOL") {
        if (argc < 2) { reply = "ERR usage: VOL <0-100>"; return true; }
        audio_.setVolume((uint8_t)constrain(argv[1].toInt(), 0, 100));
        reply = "OK vol=" + String(audio_.volume());
        return true;
    }
    return false;
}

void LiftModule::updateMotion() {
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
