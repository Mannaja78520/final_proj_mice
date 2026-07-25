#include "modules/nong/NongModule.h"
#include "core/SDStore.h"
#include "core/HwConfig.h"

static const char* JOINT_NAMES[NongModule::N] = {
    "L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
    "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R",
    "WAIST",  "SHRUG",
};

void NongModule::applySettings(JsonVariant s) {
    if (s.isNull()) return;
    JsonArray a;
    a = s["servo_pins"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) pins_[i++] = v.as<int>(); }
    a = s["joint_min"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) minDeg_[i++] = v.as<float>(); }
    a = s["joint_max"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) maxDeg_[i++] = v.as<float>(); }
    a = s["trim"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) trim_[i++] = v.as<float>(); }
    a = s["invert"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) invert_[i++] = v.as<int>() != 0; }
    a = s["neutral"].as<JsonArray>();
    if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) neutral_[i++] = v.as<float>(); }
    // per-joint arrays (a scalar in the YAML applies to every joint)
    auto arrOrScalarI = [&](const char* key, int* dst) {
        JsonArray a = s[key].as<JsonArray>();
        if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) dst[i++] = v.as<int>(); }
        else if (!s[key].isNull()) { int v = s[key].as<int>(); for (int i = 0; i < N; i++) dst[i] = v; }
    };
    auto arrOrScalarF = [&](const char* key, float* dst) {
        JsonArray a = s[key].as<JsonArray>();
        if (!a.isNull()) { int i = 0; for (JsonVariant v : a) if (i < N) dst[i++] = v.as<float>(); }
        else if (!s[key].isNull()) { float v = s[key].as<float>(); for (int i = 0; i < N; i++) dst[i] = v; }
    };
    arrOrScalarI("gear_pinion", gearPinion_);
    arrOrScalarI("gear_gear", gearGear_);
    arrOrScalarI("pulse_min", pulseMin_);
    arrOrScalarI("pulse_max", pulseMax_);
    arrOrScalarF("max_dps", maxDps_);
    arrOrScalarF("servo_range", servoRange_);   // 180 normal servo, 270 wide

    speedDps_ = s["speed_dps"] | speedDps_;
    link_     = (s["link"] | (link_ ? 1 : 0)) != 0;
    peer_     = s["peer"] | peer_;
    if (peer_ < 0 || peer_ > 247) peer_ = 0;
    for (int i = 0; i < N; i++) {
        if (gearPinion_[i] < 1) gearPinion_[i] = 1;
        if (gearGear_[i] < 1) gearGear_[i] = 1;
        if (pulseMin_[i] < 100) pulseMin_[i] = 100;
        if (pulseMax_[i] <= pulseMin_[i] + 100) pulseMax_[i] = pulseMin_[i] + 100;
        if (maxDps_[i] < 30) maxDps_[i] = 30;
        servoRange_[i] = constrain(servoRange_[i], (float)NONG_RANGE_MIN_DEG,
                                                  (float)NONG_RANGE_MAX_DEG);
    }
    if (speedDps_ < 5) speedDps_ = 5;
    if (speedDps_ > slowestMaxDps()) speedDps_ = slowestMaxDps();
    reclamp();
}

// the slowest joint caps the show speed
float NongModule::slowestMaxDps() const {
    float m = maxDps_[0];
    for (int i = 1; i < N; i++) m = min(m, maxDps_[i]);
    return m;
}

void NongModule::reclamp() {
    for (int i = 0; i < N; i++) {
        minDeg_[i] = constrain(minDeg_[i], 0.0f, 180.0f);
        maxDeg_[i] = constrain(maxDeg_[i], minDeg_[i], 180.0f);
        neutral_[i] = clampJoint(i, neutral_[i]);
    }
}

// persist calibration so it survives a reboot. NEEDS the SD card — without a
// card the nong still runs fine on live commands, the calibration just isn't
// remembered across reboots.
void NongModule::saveCal() {
    if (!sd_ || !sd_->available()) return;
    String y = "# nong calibration — written by LIMIT/GEAR/SETZERO (Nong Studio).\n";
    y += "joint_min: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(minDeg_[i], 0); }
    y += "]\njoint_max: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(maxDeg_[i], 0); }
    y += "]\ntrim: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(trim_[i], 1); }
    y += "]\nneutral: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(neutral_[i], 0); }
    y += "]\ngear_pinion: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(gearPinion_[i]); }
    y += "]\ngear_gear: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(gearGear_[i]); }
    y += "]\npulse_min: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(pulseMin_[i]); }
    y += "]\npulse_max: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(pulseMax_[i]); }
    y += "]\nmax_dps: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(maxDps_[i], 0); }
    y += "]\nservo_range: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(servoRange_[i], 0); }
    y += "]\n";
    sd_->saveText("/data/nong_cal.yaml", y);
}

void NongModule::loadCal() {
    if (!sd_ || !sd_->available()) return;
    JsonDocument doc;
    if (sd_->loadYaml("/data/nong_cal.yaml", doc))
        applySettings(doc.as<JsonVariant>()); // reuses the array/gear parsing
}

void NongModule::begin() {
    // saved calibration (LIMIT/GEAR from Nong Studio) overrides module.yaml
    loadCal();

    // ESP32Servo shares the LEDC timers; claim all four so 10 servos fit
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    for (int i = 0; i < N; i++) {
        cur_[i] = from_[i] = target_[i] = neutral_[i];
        if (pins_[i] < 0) continue;
        servos_[i].setPeriodHertz(50);
        servos_[i].attach(pins_[i], pulseMin_[i], pulseMax_[i]);
    }
    attached_ = true;
    writeServos();
}

int NongModule::jointIndex(const String& token) const {
    for (int i = 0; i < N; i++)
        if (token.equalsIgnoreCase(JOINT_NAMES[i])) return i;
    int v = token.toInt();
    if (v >= 1 && v <= N && token[0] >= '0' && token[0] <= '9') return v - 1;
    return -1;
}

float NongModule::clampJoint(int i, float deg) const {
    return constrain(deg, minDeg_[i], maxDeg_[i]);
}

float NongModule::maxDelta(const float tgt[N]) const {
    float dmax = 0;
    for (int i = 0; i < N; i++) dmax = max(dmax, fabsf(tgt[i] - cur_[i]));
    return dmax;
}

uint32_t NongModule::durationFor(const float tgt[N]) const {
    uint32_t ms = (uint32_t)(maxDelta(tgt) / speedDps_ * 1000.0f);
    return max((uint32_t)NONG_MIN_MOVE_MS, ms);
}

// physical floor: no servo can move faster than ITS OWN max_dps, so the move
// must be at least as long as the slowest joint needs for its own travel
uint32_t NongModule::minDuration(const float tgt[N]) const {
    float need = 0;                                  // seconds
    for (int i = 0; i < N; i++)
        need = max(need, fabsf(tgt[i] - cur_[i]) / maxDps_[i]);
    return max((uint32_t)NONG_MIN_MOVE_MS, (uint32_t)(need * 1000.0f));
}

void NongModule::startMove(const float tgt[N], uint32_t ms) {
    float clamped[N];
    for (int i = 0; i < N; i++) clamped[i] = clampJoint(i, tgt[i]);
    uint32_t minMs = minDuration(clamped);
    for (int i = 0; i < N; i++) {
        from_[i] = cur_[i];
        target_[i] = clamped[i];
    }
    moveStart_ = millis();
    moveDur_ = max(ms, minMs);
    moving_ = true;
}

void NongModule::writeServos() {
    if (!attached_) return;
    // angles (cur_, limits, POSE/JOINT) are JOINT degrees. Each joint has its
    // OWN reduction gear, its OWN servo pulse range and its OWN servo travel,
    // so a 180 deg MG90S elbow and a 270 deg servo in the shoulder are driven
    // correctly side by side.
    // Both spaces are measured from their CENTRE: joint neutral 90 sits at the
    // middle of the servo's travel (90 for a 180 servo, 135 for a 270), so
    // swapping a 180 servo for a 270 does not move the arm or change a single
    // pose — the servo just turns further per joint degree it is asked for.
    for (int i = 0; i < N; i++) {
        if (pins_[i] < 0) continue;
        float range = servoRange_[i] > 1.0f ? servoRange_[i] : 180.0f;
        float mid = range * 0.5f;
        float sPerJoint = (float)gearGear_[i] / (float)gearPinion_[i];
        float servo = mid + (cur_[i] - 90.0f) * sPerJoint;   // joint -> servo
        float a = constrain(servo + trim_[i], 0.0f, range);
        if (invert_[i]) a = range - a;
        int us = pulseMin_[i] +
                 (int)lroundf(a / range * (pulseMax_[i] - pulseMin_[i]));
        servos_[i].writeMicroseconds(us);
    }
}

// leader in a multi-ESP humanoid: repeat the command to the partner board.
// peer > 0 addresses exactly that module (other robots on the bus stay
// untouched); peer 0 broadcasts to everyone.
void NongModule::forward(const String& cmdline) {
    if (!link_ || !busSend) return;
    busSend((peer_ > 0 ? "#" + String(peer_) : String("#*")) + " " + cmdline);
}

bool NongModule::busy() {
    return moving_;
}

void NongModule::loop() {
    if (moving_) {
        uint32_t now = millis();
        if (now - lastTick_ >= 20) { // 50 Hz servo update
            lastTick_ = now;
            float t = (float)(now - moveStart_) / (float)moveDur_;
            if (t >= 1.0f) { t = 1.0f; moving_ = false; }
            float e = 0.5f - 0.5f * cosf(PI * t); // ease in-out
            for (int i = 0; i < N; i++)
                cur_[i] = from_[i] + (target_[i] - from_[i]) * e;
            writeServos();
        }
    }
}

bool NongModule::handleCommand(String argv[], int argc, String& reply) {
    String& cmd = argv[0]; // already uppercased by the router

    if (cmd == "POSE" || cmd == "POSE?") {
        if (cmd == "POSE?" || argc == 1) {
            reply = "";
            for (int i = 0; i < N; i++) {
                if (i) reply += ' ';
                reply += String(cur_[i], 1);
            }
            return true;
        }
        // Value tokens, then an optional trailing "T <ms>". Count them so that
        // an OLD 8-joint pose (from a sequence written before WAIST/SHRUG) still
        // works: the joints it omits keep their target, exactly like '-'.
        int nvals = argc - 1;
        long ms = -1;
        if (argc >= 3) {
            String u = argv[argc - 2]; u.toUpperCase();
            if (u == "T") { ms = argv[argc - 1].toInt(); nvals = argc - 3; }
        }
        if (nvals < 1) { reply = "ERR usage: POSE <a1..a10> [T <ms>] ('-' keeps a joint)"; return true; }
        if (nvals > N) nvals = N;
        float tgt[N];
        for (int i = 0; i < N; i++) tgt[i] = target_[i];
        for (int i = 0; i < nvals; i++) {
            const String& tok = argv[1 + i];
            tgt[i] = (tok == "-" || tok == "~") ? target_[i] : clampJoint(i, tok.toFloat());
        }
        uint32_t dur = ms > 0 ? (uint32_t)ms : durationFor(tgt);
        startMove(tgt, dur);
        // forward the RESOLVED full pose so every linked board uses the same
        // values and duration (and gets all N joints even from a short command)
        String fwd = "POSE";
        for (int i = 0; i < N; i++) fwd += " " + String(tgt[i], 1);
        forward(fwd + " T " + String(moveDur_));
        reply = "OK pose T=" + String(moveDur_) + "ms";
        return true;
    }
    if (cmd == "JOINT") {
        if (argc < 3) { reply = "ERR usage: JOINT <1-10|name> <deg> [T <ms>]"; return true; }
        int j = jointIndex(argv[1]);
        if (j < 0) { reply = "ERR joint 1-10 or name (L_SH_P L_SH_R L_EL_P L_EL_R R_SH_P R_SH_R R_EL_P R_EL_R WAIST SHRUG)"; return true; }
        float tgt[N];
        for (int i = 0; i < N; i++) tgt[i] = target_[i];
        tgt[j] = clampJoint(j, argv[2].toFloat());
        long ms = -1;
        if (argc >= 5) {
            String u = argv[3];
            u.toUpperCase();
            if (u == "T") ms = argv[4].toInt();
        }
        startMove(tgt, ms > 0 ? (uint32_t)ms : durationFor(tgt));
        forward("JOINT " + String(j + 1) + " " + String(tgt[j], 1) + " T " + String(moveDur_));
        reply = "OK " + String(JOINT_NAMES[j]) + "=" + String(tgt[j], 1) + " T=" + String(moveDur_) + "ms";
        return true;
    }
    if (cmd == "HOME" || cmd == "ZERO") {  // ZERO = move to the zero position
        long ms = -1;
        if (argc >= 3) {
            String u = argv[1];
            u.toUpperCase();
            if (u == "T") ms = argv[2].toInt();
        }
        startMove(neutral_, ms > 0 ? (uint32_t)ms : durationFor(neutral_));
        forward("HOME T " + String(moveDur_));
        reply = "OK home T=" + String(moveDur_) + "ms";
        return true;
    }
    if (cmd == "SETZERO") {
        // Calibrate: "wherever the arms are now, call this the zero/home pose
        // (90 deg per joint)." No position feedback on MG90S, so jog the
        // servos straight first (sliders / ATTACH), then press Set zero.
        // trim absorbs the offset so the arm does NOT move; future 90 = here.
        for (int i = 0; i < N; i++) {
            // each joint has its own reduction, so use ITS ratio
            float sPerJoint = (float)gearGear_[i] / (float)gearPinion_[i];
            trim_[i] += (cur_[i] - 90.0f) * sPerJoint; // pre-invert servo offset
            cur_[i] = from_[i] = target_[i] = neutral_[i] = 90.0f;
        }
        moving_ = false;
        writeServos();  // holds the same physical position (trim compensates)
        saveCal();
        forward("SETZERO");
        reply = "OK zero set (this pose is now home = 90 deg)";
        return true;
    }
    if (cmd == "RELAX") {
        for (int i = 0; i < N; i++)
            if (pins_[i] >= 0 && servos_[i].attached()) servos_[i].detach();
        attached_ = false;
        moving_ = false;
        forward("RELAX");
        reply = "OK relaxed (servos limp)";
        return true;
    }
    if (cmd == "ATTACH") {
        for (int i = 0; i < N; i++) {
            if (pins_[i] < 0) continue;
            if (!servos_[i].attached()) {
                servos_[i].setPeriodHertz(50);
                servos_[i].attach(pins_[i], pulseMin_[i], pulseMax_[i]);
            }
        }
        attached_ = true;
        writeServos(); // hold the current pose
        forward("ATTACH");
        reply = "OK attached";
        return true;
    }
    if (cmd == "STOP") {
        // freeze mid-move: current interpolated pose becomes the target
        for (int i = 0; i < N; i++) target_[i] = cur_[i];
        moving_ = false;
        forward("STOP");
        reply = "OK stopped";
        return true;
    }
    if (cmd == "SPEED" || cmd == "SPEED?") {
        if (cmd == "SPEED?" || argc < 2) {
            reply = "SPEED " + String(speedDps_, 0) + " deg/s (90 deg in ~" +
                    String(90.0f / speedDps_, 2) + "s)";
            return true;
        }
        float v = argv[1].toFloat();
        if (v < 5 || v > slowestMaxDps()) {
            reply = "ERR range 5-" + String(slowestMaxDps(), 0) + " deg/s (slowest joint's max_dps)";
            return true;
        }
        speedDps_ = v;
        forward("SPEED " + String(v, 0));
        reply = "OK speed=" + String(speedDps_, 0) + " deg/s";
        return true;
    }
    if (cmd == "TIME?" || cmd == "TIME") {
        if (argc >= 1 + N) {
            float tgt[N];
            for (int i = 0; i < N; i++) {
                const String& tok = argv[1 + i];
                tgt[i] = (tok == "-" || tok == "~") ? target_[i] : clampJoint(i, tok.toFloat());
            }
            reply = "EST " + String(durationFor(tgt)) + " ms @ " + String(speedDps_, 0) +
                    " deg/s (min " + String(minDuration(tgt)) + " ms @ max " +
                    String(slowestMaxDps(), 0) + " deg/s)";
        } else {
            reply = "EST " + String((uint32_t)(90.0f / speedDps_ * 1000.0f)) +
                    " ms per 90 deg @ " + String(speedDps_, 0) + " deg/s (min " +
                    String((uint32_t)(90.0f / slowestMaxDps() * 1000.0f)) + " ms)";
        }
        return true;
    }
    if (cmd == "LIMIT" || cmd == "LIMIT?") {
        if (cmd == "LIMIT?" || argc == 1) {
            // JSON so Nong Studio / the hub can read it straight back
            reply = "{\"min\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(minDeg_[i], 0); }
            reply += "],\"max\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(maxDeg_[i], 0); }
            reply += "],\"gear_pinion\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(gearPinion_[i]); }
            reply += "],\"gear_gear\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(gearGear_[i]); }
            reply += "],\"pulse_min\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(pulseMin_[i]); }
            reply += "],\"pulse_max\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(pulseMax_[i]); }
            reply += "],\"max_dps\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(maxDps_[i], 0); }
            reply += "],\"servo_range\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(servoRange_[i], 0); }
            reply += "]}";
            return true;
        }
        if (argc < 4) { reply = "ERR usage: LIMIT <1-10|name> <min> <max>"; return true; }
        int j = jointIndex(argv[1]);
        if (j < 0) { reply = "ERR joint 1-10 or name"; return true; }
        float lo = argv[2].toFloat(), hi = argv[3].toFloat();
        if (lo < 0 || hi > 180 || lo >= hi) { reply = "ERR need 0<=min<max<=180"; return true; }
        minDeg_[j] = lo;
        maxDeg_[j] = hi;
        reclamp();
        // pull the live pose into the new range
        float tgt[N];
        for (int i = 0; i < N; i++) tgt[i] = clampJoint(i, target_[i]);
        startMove(tgt, NONG_MIN_MOVE_MS);
        saveCal();
        forward("LIMIT " + String(j + 1) + " " + argv[2] + " " + argv[3]);
        reply = "OK " + String(JOINT_NAMES[j]) + " limit " + String(lo, 0) + ".." + String(hi, 0);
        return true;
    }
    // GEAR [<1-10|name|ALL> <pinion> <gear>] — per-joint reduction
    if (cmd == "GEAR") {
        if (argc < 4) {
            reply = "GEAR";
            for (int i = 0; i < N; i++)
                reply += " " + String(JOINT_NAMES[i]) + "=" + String(gearPinion_[i]) +
                         ":" + String(gearGear_[i]);
            return true;
        }
        int p = argv[2].toInt(), g = argv[3].toInt();
        if (p < 1 || g < 1) { reply = "ERR pinion/gear must be >=1"; return true; }
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) { gearPinion_[i] = p; gearGear_[i] = g; }
        writeServos();   // re-apply the current pose through the new ratio
        saveCal();
        forward("GEAR " + argv[1] + " " + argv[2] + " " + argv[3]);
        reply = "OK gear " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) + " " +
                String(p) + ":" + String(g) + " (servo = joint x " + String((float)g / p, 3) + ")";
        return true;
    }
    // PULSE [<1-10|name|ALL> <minUs> <maxUs> [maxDps]] — per-joint servo pulse
    if (cmd == "PULSE") {
        if (argc < 4) {
            reply = "PULSE";
            for (int i = 0; i < N; i++)
                reply += " " + String(JOINT_NAMES[i]) + "=" + String(pulseMin_[i]) +
                         "-" + String(pulseMax_[i]) + "us@" + String(maxDps_[i], 0) + "dps";
            return true;
        }
        int lo = argv[2].toInt(), hi = argv[3].toInt();
        if (lo < 100 || hi <= lo + 100 || hi > 5000) {
            reply = "ERR need 100<=min, max>min+100, max<=5000 (us)"; return true;
        }
        float dps = (argc >= 5) ? argv[4].toFloat() : 0;
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) {
                pulseMin_[i] = lo; pulseMax_[i] = hi;
                if (dps >= 30) maxDps_[i] = dps;
            }
        reattach();      // the pulse range is set when the servo is attached
        saveCal();
        forward("PULSE " + argv[1] + " " + argv[2] + " " + argv[3] +
                (argc >= 5 ? (" " + argv[4]) : ""));
        reply = "OK pulse " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) + " " +
                String(lo) + "-" + String(hi) + "us";
        return true;
    }
    // RANGE [<1-10|name|ALL> <deg>] — per-joint SERVO travel (180 / 270 / ...)
    // This is how far the SERVO turns end to end, not the joint's limits (those
    // are LIMIT). Fitting a 270 deg servo = set this to 270, nothing else: the
    // joint stays in joint degrees and every saved pose keeps working.
    if (cmd == "RANGE") {
        if (argc < 3) {
            reply = "RANGE";
            for (int i = 0; i < N; i++)
                reply += " " + String(JOINT_NAMES[i]) + "=" + String(servoRange_[i], 0);
            return true;
        }
        float r = argv[2].toFloat();
        if (r < NONG_RANGE_MIN_DEG || r > NONG_RANGE_MAX_DEG) {
            reply = "ERR servo travel must be " + String(NONG_RANGE_MIN_DEG) + ".." +
                    String(NONG_RANGE_MAX_DEG) + " deg (180 normal, 270 wide)";
            return true;
        }
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) servoRange_[i] = r;
        // trim stays as it is: it is an offset in SERVO degrees and means the
        // same thing at any travel. Neutral (joint 90) sits at the middle of
        // the travel either way, so a joint parked at home does not move; away
        // from home the joint now moves the RIGHT amount instead of the amount
        // a 180 deg servo would have given.
        writeServos();   // re-apply the current pose through the new travel
        saveCal();
        forward("RANGE " + argv[1] + " " + argv[2]);
        reply = "OK servo travel " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) +
                " = " + String(r, 0) + " deg (home unchanged; check the travel "
                "away from home, then SETZERO if it needs re-trimming)";
        return true;
    }
    // SERVO [<1-10|name|ALL> <type>] — apply a known servo's pulse + speed + travel
    if (cmd == "SERVO") {
        if (argc < 3) {
            reply = "SERVO types: mg90s pdi1181mg tiankong35 generic180 generic270 | "
                    "usage: SERVO <1-10|name|ALL> <type>";
            return true;
        }
        String t = argv[2]; t.toLowerCase();
        int lo, hi; float dps, rng;
        if (t == "mg90s")           { lo = 500; hi = 2400; dps = 400; rng = 180; }
        else if (t == "pdi1181mg")  { lo = 500; hi = 2500; dps = 375; rng = 270; }
        else if (t == "tiankong35") { lo = 500; hi = 2500; dps = 250; rng = 270; }
        else if (t == "generic180") { lo = 500; hi = 2500; dps = 300; rng = 180; }
        else if (t == "generic270") { lo = 500; hi = 2500; dps = 300; rng = 270; }
        else {
            reply = "ERR unknown servo (mg90s, pdi1181mg, tiankong35, generic180, generic270) — "
                    "or set a custom one with PULSE + RANGE";
            return true;
        }
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) {
                pulseMin_[i] = lo; pulseMax_[i] = hi; maxDps_[i] = dps;
                servoRange_[i] = rng;   // trim is unchanged — see RANGE above
            }
        reattach();
        saveCal();
        forward("SERVO " + argv[1] + " " + argv[2]);
        reply = "OK " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) + " = " + t +
                " (" + String(lo) + "-" + String(hi) + "us, " + String(dps, 0) +
                " deg/s, " + String(rng, 0) + " deg travel)";
        return true;
    }
    // no RGB / PLAY / VOL here: nong hardware is 8 servos + the SD card only
    return false;
}

// re-attach the servos so a changed pulse range takes effect immediately
void NongModule::reattach() {
    if (!attached_) return;
    for (int i = 0; i < N; i++) {
        if (pins_[i] < 0) continue;
        if (servos_[i].attached()) servos_[i].detach();
        servos_[i].setPeriodHertz(50);
        servos_[i].attach(pins_[i], pulseMin_[i], pulseMax_[i]);
    }
    writeServos();
}

void NongModule::status(JsonObject o) {
    JsonArray joints = o["joints"].to<JsonArray>();
    JsonArray tgt = o["target"].to<JsonArray>();
    JsonArray pins = o["pins"].to<JsonArray>();
    JsonArray jmin = o["min"].to<JsonArray>();
    JsonArray jmax = o["max"].to<JsonArray>();
    for (int i = 0; i < N; i++) {
        joints.add(roundf(cur_[i] * 10) / 10);
        tgt.add(roundf(target_[i] * 10) / 10);
        pins.add(pins_[i]);
        jmin.add(minDeg_[i]);
        jmax.add(maxDeg_[i]);
    }
    // per-joint servo + gear (each joint can be a different servo)
    JsonArray gp = o["gear_pinion"].to<JsonArray>();
    JsonArray gg = o["gear_gear"].to<JsonArray>();
    JsonArray pmin = o["pulse_min"].to<JsonArray>();
    JsonArray pmax = o["pulse_max"].to<JsonArray>();
    JsonArray mdps = o["max_dps"].to<JsonArray>();
    JsonArray srng = o["servo_range"].to<JsonArray>();
    for (int i = 0; i < N; i++) {
        gp.add(gearPinion_[i]); gg.add(gearGear_[i]);
        pmin.add(pulseMin_[i]); pmax.add(pulseMax_[i]);
        mdps.add(maxDps_[i]); srng.add(servoRange_[i]);
    }
    o["moving"] = moving_;
    o["attached"] = attached_;
    o["speed_dps"] = speedDps_;
    o["link"] = link_;
    o["peer"] = peer_;
    // sequence progress for monitor mode: remaining ms of the current move
    o["move_ms"] = moveDur_;
    o["move_left"] = moving_ ? (uint32_t)max(0L, (long)(moveDur_ - (millis() - moveStart_))) : 0;
}
