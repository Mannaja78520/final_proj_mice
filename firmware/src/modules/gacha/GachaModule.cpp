#include "modules/gacha/GachaModule.h"
#include "core/HwConfig.h"
#include "core/Util.h"
#include <Preferences.h>

// Text the person types (event name, item type, who) is stored and echoed in
// JSON: keep it short so an NVS slot and a status push stay small.
static const int TEXT_MAX = 40;

static String clip(const String& s) {
    String t = s;
    t.trim();
    return t.length() > TEXT_MAX ? t.substring(0, TEXT_MAX) : t;
}

void GachaModule::begin() {
    load();
    // GPIO33 has an internal pull-up; 34-39 do not, and need one on the board.
    if (hw.pins.hall >= 0) pinMode(hw.pins.hall, INPUT_PULLUP);
    makeMotor();
    hall_ = gachamath::HallCounter();
}

void GachaModule::makeMotor() {
    if (hw.pins.motorA < 0 || hw.pins.motorB < 0) return;   // no driver wired yet
    const Controller::driver kind = hw.pins.motorPwm >= 0 ? Controller::Drive3pin
                                                          : Controller::Drive2pin;
    motor_ = new Controller(kind, PWM_FREQUENCY, PWM_BITS, false, true,
                            hw.pins.motorPwm, hw.pins.motorA, hw.pins.motorB);
    motor_->spin(0);
}

bool GachaModule::hallActive() const {
    if (hw.pins.hall < 0) return false;
    const bool low = digitalRead(hw.pins.hall) == LOW;
    return activeLow_ ? low : !low;
}

void GachaModule::motorOff() {
    if (motor_) motor_->spin(0);
}

void GachaModule::startTurn(Job job, int passes) {
    job_ = job;
    want_ = passes < 0 ? -passes : passes;
    sign_ = passes < 0 ? -1 : 1;
    got_ = 0;
    settleUntil_ = 0;
    settlePhase_ = SETTLE_NONE;
    phaseUntil_ = 0;
    startMs_ = lastPassMs_ = millis();
    state_ = job == JOB_HOME ? HOMING : TURNING;
    if (motor_) motor_->spin(sign_ * dir_ * speed_);
}

// Every motion ends here, whatever ended it: the motor is off and a dispense
// leaves a record an app can read back with G? (seq, result, who).
void GachaModule::finish(const char* result) {
    motorOff();
    settlePhase_ = SETTLE_NONE;
    phaseUntil_ = 0;
    const bool wasDispense = state_ != IDLE && job_ == JOB_DISPENSE;
    state_ = IDLE;
    if (job_ == JOB_HOME && !strcmp(result, "done")) pos_ = 0;
    if (wasDispense) {
        lastResult_ = result;
        lastMs_ = millis() - startMs_;
    }
    saveCounts();                             // magnet count + the dispense record
}

void GachaModule::loop() {
    const uint32_t now = millis();
    const bool arrived = hall_.feed(hallActive(), now, (uint32_t)debounceMs_);
    if (state_ == IDLE) return;

    if (settlePhase_ != SETTLE_NONE) {
        if (settlePhase_ == SETTLE_ROCK_FWD) {
            // Phase 1: Forward overshoot past drop lip (slowly)
            if ((int32_t)(now - phaseUntil_) >= 0) {
                if (returnMs_ > 0) {
                    settlePhase_ = SETTLE_ROCK_BACK;
                    phaseUntil_ = now + (uint32_t)returnMs_;
                    const int rSpeed = returnSpeed_ > 0 ? returnSpeed_ : 360;
                    if (motor_) motor_->spin(-sign_ * dir_ * rSpeed); // reverse rock past magnet to other side
                } else {
                    motorOff();
                    settlePhase_ = SETTLE_CENTER;
                    centerStartMs_ = now;
                    phaseUntil_ = now + 40;
                }
            }
            return;
        }

        if (settlePhase_ == SETTLE_ROCK_BACK) {
            // Phase 2: Reverse rock past magnet to the other side to agitate prize
            if ((int32_t)(now - phaseUntil_) >= 0) {
                // Now on reverse side: micro-step forward to center dead-on Hall magnet
                motorOff();
                settlePhase_ = SETTLE_CENTER;
                centerStartMs_ = now;
                phaseUntil_ = now + 40;
            }
            return;
        }

        if (settlePhase_ == SETTLE_CENTER) {
            // Phase 3: Micro-step forward onto Hall sensor dead-center (zero coasting)
            if (hallActive()) {
                motorOff();
                if (pauseMs_ > 0) {
                    settlePhase_ = SETTLE_PAUSE;
                    phaseUntil_ = now + (uint32_t)pauseMs_;
                } else {
                    finish("done");
                }
                return;
            }

            // Fallback safety timeout if hall sensor is disconnected or broken
            if ((int32_t)(now - centerStartMs_) >= 3500) {
                motorOff();
                if (pauseMs_ > 0) {
                    settlePhase_ = SETTLE_PAUSE;
                    phaseUntil_ = now + (uint32_t)pauseMs_;
                } else {
                    finish("done");
                }
                return;
            }

            if ((int32_t)(now - phaseUntil_) >= 0) {
                // Inch forward in tiny 20ms micro-step (zero momentum)
                const int cSpeed = centerSpeed_ > 0 ? centerSpeed_ : 260;
                if (motor_) {
                    motor_->spin(sign_ * dir_ * cSpeed);
                    delay(20);
                    motorOff();
                }
                phaseUntil_ = now + 35; // wait 35ms mechanical rest before re-checking
            }
            return;
        }

        if (settlePhase_ == SETTLE_PAUSE) {
            // Phase 4: Stationary hold at dead-center for user / admin inspection
            motorOff();
            if ((int32_t)(now - phaseUntil_) >= 0) {
                settlePhase_ = SETTLE_NONE;
                finish("done");
            }
            return;
        }
    }

    if (settleUntil_) {                       // last magnet seen: centre the pocket
        if ((int32_t)(now - settleUntil_) >= 0) finish("done");
        return;
    }
    if (arrived) {
        hits_++;
        got_++;
        lastPassMs_ = now;
        const int ps = perSlot();
        if (ps > 0 && got_ % ps == 0) pos_ = ((pos_ + sign_) % slots_ + slots_) % slots_;
        if (got_ >= want_) {
            // Overshoot past drop lip to ensure prize drops, then rock back and center
            if (overshootMs_ > 0) {
                settlePhase_ = SETTLE_ROCK_FWD;
                phaseUntil_ = now + (uint32_t)overshootMs_;
                const int s = overshootSpeed_ > 0 ? overshootSpeed_ : speed_;
                if (motor_) motor_->spin(sign_ * dir_ * s);
            } else if (returnMs_ > 0) {
                settlePhase_ = SETTLE_ROCK_BACK;
                phaseUntil_ = now + (uint32_t)returnMs_;
                const int rSpeed = returnSpeed_ > 0 ? returnSpeed_ : speed_;
                if (motor_) motor_->spin(-sign_ * dir_ * rSpeed);
            } else if (pauseMs_ > 0) {
                motorOff();
                settlePhase_ = SETTLE_PAUSE;
                phaseUntil_ = now + (uint32_t)pauseMs_;
            } else if (settleMs_ > 0) {
                settleUntil_ = now + (uint32_t)settleMs_;
            } else {
                finish("done");
            }
            return;
        }
    }

    // Timed slot fallback if hall sensor is disconnected / broken
    if (fallbackSlotMs_ > 0 && (now - lastPassMs_ >= (uint32_t)fallbackSlotMs_)) {
        hits_++;
        got_++;
        lastPassMs_ = now;
        const int ps = perSlot();
        if (ps > 0 && got_ % ps == 0) pos_ = ((pos_ + sign_) % slots_ + slots_) % slots_;
        if (got_ >= want_) {
            motorOff();
            finish("done");
            return;
        }
    }

    if (now - lastPassMs_ > (uint32_t)timeoutMs_) finish("jam");
}

bool GachaModule::handleCommand(String argv[], int argc, String& reply) {
    String& cmd = argv[0];   // already uppercased by the router

    if (cmd == "G?") { reply = statusJson(); return true; }
    if (cmd == "GCFG?") { reply = cfgJson(); return true; }

    if (cmd == "GNUDGE") {
        if (argc < 3) { reply = "ERR GNUDGE <pwm> <ms>"; return true; }
        const int pwm = argv[1].toInt();
        const int ms = argv[2].toInt();
        if (motor_) {
            motor_->spin(dir_ * pwm);
            delay(ms);
            motorOff();
        }
        delay(30);
        reply = "OK at_hall=" + String(hallActive() ? "1" : "0");
        return true;
    }

    if (cmd == "STOP") {
        const bool moving = state_ != IDLE;
        if (moving) finish("stopped");
        else motorOff();
        reply = moving ? "OK stopped" : "OK already stopped";
        return true;
    }

    // GSPIN <n> [MAG]: n pockets (or n magnets with MAG), negative = backwards.
    // A test tool: it never touches stock or the dispense count.
    if (cmd == "GSPIN") {
        if (argc < 2) { reply = "ERR GSPIN <pockets> [MAG]"; return true; }
        if (state_ != IDLE) { reply = "ERR busy"; return true; }
        const int n = argv[1].toInt();
        const bool mag = argc >= 3 && argv[2].equalsIgnoreCase("MAG");
        const int ps = perSlot();
        if (!mag && ps == 0) { reply = "ERR magnets must be a multiple of pockets"; return true; }
        const int passes = mag ? n : n * ps;
        if (passes == 0 || passes > 100 || passes < -100) { reply = "ERR 1-100 either way"; return true; }
        if (!motor_) { reply = "ERR no motor pins (PIN motor_a / motor_b)"; return true; }
        startTurn(JOB_SPIN, passes);
        reply = "OK turning " + String(passes) + " magnet(s)";
        return true;
    }

    // GHOME: turn to the next magnet so a pocket sits at the receive position.
    if (cmd == "GHOME") {
        if (state_ != IDLE) { reply = "ERR busy"; return true; }
        if (hall_.stable) { pos_ = 0; reply = "OK already at a magnet"; return true; }
        if (!motor_) { reply = "ERR no motor pins (PIN motor_a / motor_b)"; return true; }
        startTurn(JOB_HOME, 1);
        reply = "OK finding the next magnet";
        return true;
    }

    // GDISPENSE [FORCE] [who...]: the prize falls. FORCE is the admin's extra
    // item (event closed or stock says empty) and is still counted.
    if (cmd == "GDISPENSE") {
        int at = 1;
        const bool force = argc > 1 && argv[1].equalsIgnoreCase("FORCE");
        if (force) at = 2;
        const char* no = gachamath::refusal(state_ != IDLE, open_, stock_, force);
        if (no) { reply = String("ERR ") + no; return true; }
        const int ps = perSlot();
        if (ps == 0) { reply = "ERR magnets must be a multiple of pockets"; return true; }
        if (!motor_) { reply = "ERR no motor pins (PIN motor_a / motor_b)"; return true; }
        seq_++;
        given_++;
        total_++;
        if (force) forced_++;
        stock_ = gachamath::stockAfter(stock_);
        lastWho_ = at < argc ? clip(Util::joinFrom(argv, argc, at)) : String("");
        lastForced_ = force;
        lastResult_ = "turning";
        saveCounts();
        startTurn(JOB_DISPENSE, drop_ * ps);
        reply = "OK dispensing seq=" + String(seq_) + " stock=" + String(stock_);
        return true;
    }

    if (cmd == "GSTOCK") {
        if (argc < 2) { reply = "ERR GSTOCK <n>|ADD <n>|OFF"; return true; }
        if (argv[1].equalsIgnoreCase("OFF")) { stock_ = -1; saveCounts(); reply = "OK stock not counted"; return true; }
        const bool add = argv[1].equalsIgnoreCase("ADD");
        if (add && argc < 3) { reply = "ERR GSTOCK ADD <n>"; return true; }
        const int n = (add ? argv[2] : argv[1]).toInt();
        if (n < 0 || n > 9999) { reply = "ERR 0-9999"; return true; }
        if (add) { stock_ = (stock_ < 0 ? 0 : stock_) + n; loaded_ += n; }
        else { stock_ = n; loaded_ = n; }
        saveCounts();
        reply = "OK stock=" + String(stock_);
        return true;
    }

    if (cmd == "GEVENT") {
        if (argc < 2) { reply = "ERR GEVENT NAME <text>|OPEN|CLOSE|RESET"; return true; }
        String a = argv[1];
        a.toUpperCase();
        if (a == "NAME") {
            event_ = argc > 2 ? clip(Util::joinFrom(argv, argc, 2)) : String("");
            saveCfg();
            reply = "OK event \"" + event_ + "\"";
        } else if (a == "OPEN" || a == "CLOSE") {
            open_ = a == "OPEN";
            saveCfg();
            reply = open_ ? "OK event open" : "OK event closed";
        } else if (a == "RESET") {      // a new event: this event's counts start over
            given_ = forced_ = loaded_ = 0;
            seq_ = 0;
            lastResult_ = "none";
            lastWho_ = "";
            saveCounts();
            reply = "OK event counts cleared";
        } else reply = "ERR GEVENT NAME <text>|OPEN|CLOSE|RESET";
        return true;
    }

    if (cmd == "GITEM") {
        item_ = argc > 1 ? clip(Util::joinFrom(argv, argc, 1)) : String("");
        saveCfg();
        reply = "OK item \"" + item_ + "\"";
        return true;
    }

    if (cmd == "GCOUNT") {
        if (argc < 2 || !argv[1].equalsIgnoreCase("RESET")) { reply = "ERR GCOUNT RESET"; return true; }
        hits_ = total_ = 0;
        saveCounts();
        reply = "OK lifetime counts cleared";
        return true;
    }

    if (cmd == "GCFG") {
        if (argc == 2 && argv[1].equalsIgnoreCase("CLEAR")) {
            Preferences p;
            if (p.begin("gacha", false)) { p.remove("cfg"); p.end(); }
            magnets_ = GACHA_MAGNETS; slots_ = GACHA_SLOTS; drop_ = GACHA_DROP_SLOTS;
            speed_ = GACHA_SPEED; dir_ = 1; timeoutMs_ = GACHA_SLOT_TIMEOUT_MS;
            debounceMs_ = GACHA_DEBOUNCE_MS; settleMs_ = GACHA_SETTLE_MS;
            activeLow_ = GACHA_HALL_ACTIVE_LOW;
            saveCfg();
            reply = "OK settings back to defaults";
            return true;
        }
        if (argc < 3) { reply = "ERR GCFG <key> <value>|CLEAR"; return true; }
        if (state_ != IDLE) { reply = "ERR busy"; return true; }
        String k = argv[1];
        k.toLowerCase();
        const int v = argv[2].toInt();
        // [key, field, min, max]: one table, so a new setting is one line.
        struct Num { const char* key; int* field; int lo, hi; };
        int low = activeLow_ ? 1 : 0;
        const Num nums[] = {
            {"magnets", &magnets_, 1, 64}, {"slots", &slots_, 1, 64}, {"drop", &drop_, 1, 64},
            {"speed", &speed_, 50, PWM_Max}, {"dir", &dir_, -1, 1},
            {"timeout", &timeoutMs_, 200, 60000}, {"debounce", &debounceMs_, 0, 200},
            {"settle", &settleMs_, 0, 2000}, {"active_low", &low, 0, 1},
            {"overshoot", &overshootMs_, 0, 3000}, {"overshoot_speed", &overshootSpeed_, 50, PWM_Max},
            {"return", &returnMs_, 0, 3000}, {"return_speed", &returnSpeed_, 50, PWM_Max},
            {"center_speed", &centerSpeed_, 50, PWM_Max},
            {"pause", &pauseMs_, 0, 30000}, {"fallback", &fallbackSlotMs_, 0, 5000},
        };
        for (const Num& n : nums) {
            if (k != n.key) continue;
            if (v < n.lo || v > n.hi || (k == "dir" && v == 0)) {
                reply = "ERR " + k + " " + String(n.lo) + "-" + String(n.hi);
                return true;
            }
            const int old = *n.field;
            *n.field = v;
            if (perSlot() == 0) {           // 6 magnets on 4 pockets cannot be counted
                *n.field = old;
                reply = "ERR magnets must be a multiple of pockets";
                return true;
            }
            activeLow_ = low != 0;
            saveCfg();
            reply = "OK " + k + "=" + String(v);
            return true;
        }
        reply = "ERR key magnets slots drop speed dir timeout debounce settle active_low overshoot overshoot_speed return return_speed center_speed pause fallback";
        return true;
    }
    return false;
}

String GachaModule::cfgJson() const {
    JsonDocument d;
    d["magnets"] = magnets_; d["slots"] = slots_; d["drop"] = drop_;
    d["speed"] = speed_; d["dir"] = dir_; d["timeout"] = timeoutMs_;
    d["debounce"] = debounceMs_; d["settle"] = settleMs_; d["active_low"] = activeLow_ ? 1 : 0;
    d["overshoot"] = overshootMs_; d["overshoot_speed"] = overshootSpeed_;
    d["return"] = returnMs_; d["return_speed"] = returnSpeed_;
    d["center_speed"] = centerSpeed_; d["pause"] = pauseMs_;
    d["fallback"] = fallbackSlotMs_;
    d["per_slot"] = perSlot();
    String out;
    serializeJson(d, out);
    return out;
}

String GachaModule::statusJson() {
    JsonDocument d;
    status(d.to<JsonObject>());
    String out;
    serializeJson(d, out);
    return out;
}

void GachaModule::status(JsonObject o) {
    o["state"] = state_ == IDLE ? "idle" : (state_ == HOMING ? "homing" : (job_ == JOB_DISPENSE ? "dispensing" : "turning"));
    o["at_hall"] = hallActive() || hall_.stable;
    o["hits"] = hits_;
    o["pos"] = pos_;
    o["item"] = item_;
    o["event"] = event_;
    o["open"] = open_;
    o["stock"] = stock_;
    o["empty"] = stock_ == 0;
    o["loaded"] = loaded_;
    o["given"] = given_;
    o["forced"] = forced_;
    o["total"] = total_;
    JsonObject last = o["last"].to<JsonObject>();
    last["seq"] = seq_;
    last["result"] = lastResult_;
    last["who"] = lastWho_;
    last["forced"] = lastForced_;
    last["ms"] = lastMs_;
    if (state_ != IDLE) {
        o["want"] = want_;
        o["got"] = got_;
        if (settlePhase_ == SETTLE_ROCK_FWD) o["phase"] = "rock_fwd";
        else if (settlePhase_ == SETTLE_ROCK_BACK) o["phase"] = "rock_back";
        else if (settlePhase_ == SETTLE_CENTER) o["phase"] = "center";
        else if (settlePhase_ == SETTLE_PAUSE) o["phase"] = "pause";
        else o["phase"] = "turning";
    }
    JsonDocument cfg;
    deserializeJson(cfg, cfgJson());
    o["cfg"] = cfg.as<JsonObject>();
    o["motor"] = motor_ != nullptr;
}

void GachaModule::addCapabilities(JsonArray caps) {
    caps.add("dispense");   // the prize dispenser card
}

void GachaModule::saveCfg() {
    Preferences p;
    if (!p.begin("gacha", false)) return;
    JsonDocument d;
    deserializeJson(d, cfgJson());
    d.remove("per_slot");
    d["item"] = item_;
    d["event"] = event_;
    d["open"] = open_;
    String s;
    serializeJson(d, s);
    p.putString("cfg", s);
    p.end();
}

// Counts change on every dispense: their own small key, so a busy event
// rewrites a few bytes and not the settings.
void GachaModule::saveCounts() {
    Preferences p;
    if (!p.begin("gacha", false)) return;
    p.putInt("stock", stock_);
    p.putInt("loaded", loaded_);
    p.putInt("given", given_);
    p.putInt("forced", forced_);
    p.putUInt("total", total_);
    p.putUInt("hits", hits_);
    p.putUInt("seq", seq_);
    p.end();
}

void GachaModule::load() {
    Preferences p;
    if (!p.begin("gacha", true)) return;
    JsonDocument d;
    if (!deserializeJson(d, p.getString("cfg", "{}"))) {
        magnets_ = d["magnets"] | magnets_;
        slots_ = d["slots"] | slots_;
        drop_ = d["drop"] | drop_;
        speed_ = d["speed"] | speed_;
        dir_ = (d["dir"] | dir_) < 0 ? -1 : 1;
        timeoutMs_ = d["timeout"] | timeoutMs_;
        debounceMs_ = d["debounce"] | debounceMs_;
        settleMs_ = d["settle"] | settleMs_;
        overshootMs_ = d["overshoot"] | overshootMs_;
        overshootSpeed_ = d["overshoot_speed"] | overshootSpeed_;
        returnMs_ = d["return"] | returnMs_;
        returnSpeed_ = d["return_speed"] | returnSpeed_;
        centerSpeed_ = d["center_speed"] | centerSpeed_;
        pauseMs_ = d["pause"] | pauseMs_;
        fallbackSlotMs_ = d["fallback"] | fallbackSlotMs_;
        activeLow_ = (d["active_low"] | (activeLow_ ? 1 : 0)) != 0;
        item_ = (const char*)(d["item"] | "");
        event_ = (const char*)(d["event"] | "");
        open_ = d["open"] | open_;
        if (perSlot() == 0) { magnets_ = GACHA_MAGNETS; slots_ = GACHA_SLOTS; }
    }
    stock_ = p.getInt("stock", -1);
    loaded_ = p.getInt("loaded", 0);
    given_ = p.getInt("given", 0);
    forced_ = p.getInt("forced", 0);
    total_ = p.getUInt("total", 0);
    hits_ = p.getUInt("hits", 0);
    seq_ = p.getUInt("seq", 0);
    p.end();
}
