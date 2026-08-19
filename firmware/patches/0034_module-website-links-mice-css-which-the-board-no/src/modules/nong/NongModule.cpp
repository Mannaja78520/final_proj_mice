#include "modules/nong/NongModule.h"
#include "modules/nong/NongMath.h"
#include "modules/nong/ServoPresets.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include "core/HwConfig.h"
#include <Preferences.h>

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
    arrOrScalarI("frame_hz", frameHz_);         // 50 normal, 330 for PDI-1181MG

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
        frameHz_[i] = constrain(frameHz_[i], NONG_FRAME_HZ_MIN, NONG_FRAME_HZ_MAX);
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

// Persist calibration so it survives a power cycle. Written to the chip's own
// NVS ALWAYS, and additionally to /data/nong_cal.yaml when a card is fitted —
// so a board with no SD card keeps its gear, limits, pulses, travel, rate and
// zero, instead of coming back on the compile-time defaults every time it is
// unplugged.
// Mark the calibration dirty; loop() writes it once the commands stop coming.
// Nong Studio's "update" pushes LIMIT+GEAR+PULSE+RANGE+RATE for all 10 joints
// in one burst — rewriting the whole YAML 50 times made it crawl and wore the
// card for nothing.
void NongModule::saveCalSoon() {
    calDirty_ = true;
    calDirtyAt_ = millis();
}

// ---- the copy that does not need a card -------------------------------
void NongModule::saveCalNvs() {
    CalBlob b{};
    b.magic = CAL_MAGIC;
    b.version = CAL_VERSION;
    b.joints = N;
    for (int i = 0; i < N; i++) {
        b.minDeg[i] = minDeg_[i];   b.maxDeg[i] = maxDeg_[i];
        b.trim[i] = trim_[i];       b.neutral[i] = neutral_[i];
        b.gearPinion[i] = gearPinion_[i]; b.gearGear[i] = gearGear_[i];
        b.pulseMin[i] = pulseMin_[i];     b.pulseMax[i] = pulseMax_[i];
        b.maxDps[i] = maxDps_[i];   b.servoRange[i] = servoRange_[i];
        b.frameHz[i] = frameHz_[i]; b.invert[i] = invert_[i] ? 1 : 0;
    }
    Preferences p;
    if (!p.begin("nongcal", false)) return;
    p.putBytes("cal", &b, sizeof(b));
    p.end();
}

bool NongModule::loadCalNvs() {
    Preferences p;
    if (!p.begin("nongcal", true)) return false;
    CalBlob b{};
    size_t n = p.getBytes("cal", &b, sizeof(b));
    p.end();
    // A blob from a different firmware (more joints, changed layout) is
    // ignored rather than half-applied — better the defaults than a mix.
    if (n != sizeof(b) || b.magic != CAL_MAGIC || b.version != CAL_VERSION) return false;
    int j = b.joints < N ? b.joints : N;
    for (int i = 0; i < j; i++) {
        minDeg_[i] = b.minDeg[i];   maxDeg_[i] = b.maxDeg[i];
        trim_[i] = b.trim[i];       neutral_[i] = b.neutral[i];
        gearPinion_[i] = b.gearPinion[i]; gearGear_[i] = b.gearGear[i];
        pulseMin_[i] = b.pulseMin[i];     pulseMax_[i] = b.pulseMax[i];
        maxDps_[i] = b.maxDps[i];   servoRange_[i] = b.servoRange[i];
        frameHz_[i] = b.frameHz[i]; invert_[i] = b.invert[i] != 0;
    }
    // the same sanity clamps applySettings uses — a corrupt blob must not be
    // able to drive the servos somewhere that damages the mechanism
    for (int i = 0; i < N; i++) {
        if (gearPinion_[i] < 1) gearPinion_[i] = 1;
        if (gearGear_[i] < 1) gearGear_[i] = 1;
        if (pulseMin_[i] < 100) pulseMin_[i] = 100;
        if (pulseMax_[i] <= pulseMin_[i] + 100) pulseMax_[i] = pulseMin_[i] + 100;
        if (maxDps_[i] < 30) maxDps_[i] = 30;
        servoRange_[i] = constrain(servoRange_[i], (float)NONG_RANGE_MIN_DEG,
                                                   (float)NONG_RANGE_MAX_DEG);
        frameHz_[i] = constrain(frameHz_[i], NONG_FRAME_HZ_MIN, NONG_FRAME_HZ_MAX);
    }
    reclamp();
    return true;
}

void NongModule::clearCal() {
    Preferences p;
    if (p.begin("nongcal", false)) { p.clear(); p.end(); }
    if (sd_ && sd_->available()) sd_->remove("/data/nong_cal.yaml");
}

void NongModule::saveCal() {
    saveCalNvs();               // always — this is the one that needs no card
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
    y += "]\nframe_hz: [";
    for (int i = 0; i < N; i++) { if (i) y += ","; y += String(frameHz_[i]); }
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
    // Saved calibration (LIMIT/GEAR/... from Nong Studio) overrides module.yaml.
    // SD first, then NVS: the chip copy is written by every calibration command
    // whether or not a card is fitted, so it is never older than the file — and
    // on a board with no card it is the only copy there is.
    loadCal();
    loadCalNvs();

    // ESP32Servo shares the LEDC timers; claim all four so 10 servos fit
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    for (int i = 0; i < N; i++) {
        cur_[i] = from_[i] = target_[i] = neutral_[i];
        if (pins_[i] < 0) continue;
        servos_[i].setPeriodHertz(frameHz_[i]);   // 50 normal, 330 for PDI-1181MG
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
    return nongmath::maxDelta(cur_, tgt, N);
}

uint32_t NongModule::durationFor(const float tgt[N]) const {
    return nongmath::durationFor(cur_, tgt, N, speedDps_, NONG_MIN_MOVE_MS);
}

// physical floor: no servo can move faster than ITS OWN max_dps, so the move
// must be at least as long as the slowest joint needs for its own travel
uint32_t NongModule::minDuration(const float tgt[N]) const {
    return nongmath::minDuration(cur_, tgt, maxDps_, N, NONG_MIN_MOVE_MS);
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
        // the whole joint -> servo -> microseconds chain lives in NongMath so
        // it can be executed and asserted on a PC (pio test -e native)
        servos_[i].writeMicroseconds(
            nongmath::jointToUs(cur_[i], servoRange_[i], gearPinion_[i],
                                gearGear_[i], trim_[i], pulseMin_[i],
                                pulseMax_[i], invert_[i]));
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
    // one SD write once the settings stop changing, instead of one per command
    if (calDirty_ && millis() - calDirtyAt_ > 800) {
        calDirty_ = false;
        saveCal();
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
        for (int i = 0; i < N; i++) {
            if (pins_[i] < 0) continue;
            if (servos_[i].attached()) servos_[i].detach();
            // Detaching frees the pin back to plain GPIO — it does NOT
            // guarantee the line ends up idle. On a pin with an internal
            // pull-up the line then sits HIGH, and a servo staring at a
            // permanently high signal holds its position instead of going
            // limp. That is exactly what SHRUG did while the other nine
            // relaxed: it is on GPIO 15, a strapping pin (MTDO) that the
            // ESP32 pulls up at reset.
            //
            // So say what we mean: no pulses. Driving the line low is the
            // real "relaxed" state and it is correct on every pin, not just
            // the ones that happened to float low by luck.
            pinMode(pins_[i], OUTPUT);
            digitalWrite(pins_[i], LOW);
        }
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
                servos_[i].setPeriodHertz(frameHz_[i]);
                servos_[i].attach(pins_[i], pulseMin_[i], pulseMax_[i]);
            }
        }
        attached_ = true;
        writeServos(); // hold the current pose
        forward("ATTACH");
        reply = "OK attached";
        return true;
    }
    // JCFG <j> <pinion> <gear> <pmin> <pmax> <dps> <range> <hz> <min> <max>
    // One joint's entire setup in ONE line. Nong Studio's "send rig" used to
    // push GEAR+PULSE+RANGE+RATE+LIMIT separately — 5 commands x 10 joints =
    // 50 round trips, about 1.6 s. This makes it 10, and re-attaches the servo
    // once instead of up to twice per joint.
    // The individual commands still work; this is a faster way to say the same
    // thing, and it validates exactly as they do.
    if (cmd == "JCFG") {
        if (argc < 11) {
            reply = "ERR usage: JCFG <1-10|name> <pinion> <gear> <pmin> <pmax> "
                    "<dps> <range> <hz> <min> <max>";
            return true;
        }
        int j = jointIndex(argv[1]);
        if (j < 0) { reply = "ERR joint 1-10 or name"; return true; }
        const int pinion = argv[2].toInt(), gear = argv[3].toInt();
        const int pmin = argv[4].toInt(), pmax = argv[5].toInt();
        const float dps = argv[6].toFloat(), rng = argv[7].toFloat();
        const int hz = argv[8].toInt();
        const float lo = argv[9].toFloat(), hi = argv[10].toFloat();
        // same limits the individual commands enforce — a batch must never be
        // a way to smuggle in a value they would have refused
        if (pinion < 1 || gear < 1) { reply = "ERR pinion/gear must be >=1"; return true; }
        if (pmin < 100 || pmax <= pmin + 100 || pmax > 5000) {
            reply = "ERR need 100<=pmin, pmax>pmin+100, pmax<=5000"; return true;
        }
        if (dps < 30) { reply = "ERR max_dps must be >= 30"; return true; }
        if (rng < NONG_RANGE_MIN_DEG || rng > NONG_RANGE_MAX_DEG) {
            reply = "ERR servo travel must be " + String(NONG_RANGE_MIN_DEG) + ".." +
                    String(NONG_RANGE_MAX_DEG) + " deg";
            return true;
        }
        if (hz < NONG_FRAME_HZ_MIN || hz > NONG_FRAME_HZ_MAX) {
            reply = "ERR frame rate must be " + String(NONG_FRAME_HZ_MIN) + ".." +
                    String(NONG_FRAME_HZ_MAX) + " Hz";
            return true;
        }
        if (hi <= lo) { reply = "ERR joint max must exceed min"; return true; }

        const bool reattachNeeded = (pulseMin_[j] != pmin) || (pulseMax_[j] != pmax) ||
                                    (frameHz_[j] != hz);
        gearPinion_[j] = pinion; gearGear_[j] = gear;
        pulseMin_[j] = pmin;     pulseMax_[j] = pmax;
        maxDps_[j] = dps;        servoRange_[j] = rng;
        frameHz_[j] = hz;
        minDeg_[j] = lo;         maxDeg_[j] = hi;
        reclamp();
        if (reattachNeeded) reattach(j);   // only this joint, never all ten
        else writeServos();                // the new gear/travel applies at once
        saveCalSoon();
        forward("JCFG " + Util::joinFrom(argv, argc, 1));
        reply = "OK " + String(JOINT_NAMES[j]) + " " + String(pinion) + ":" +
                String(gear) + " " + String(pmin) + "-" + String(pmax) + "us " +
                String(dps, 0) + "dps " + String(rng, 0) + "deg " + String(hz) +
                "Hz limit " + String(lo, 0) + ".." + String(hi, 0);
        return true;
    }

    // CAL [CLEAR] — where the calibration is kept, and how to forget it.
    // Without this a bad calibration on a card-less board would be stuck: the
    // usual fix is to delete /data/nong_cal.yaml, and there is no card.
    if (cmd == "CAL") {
        if (argc >= 2 && argv[1].equalsIgnoreCase("CLEAR")) {
            clearCal();
            reply = "OK calibration cleared from chip";
            if (sd_ && sd_->available()) reply += " + SD";
            reply += " — reboot to load the defaults";
            return true;
        }
        Preferences p;
        bool nvs = false;
        if (p.begin("nongcal", true)) { nvs = p.isKey("cal"); p.end(); }
        reply = String("CAL chip=") + (nvs ? "saved" : "none") +
                " sd=" + ((sd_ && sd_->available()) ? "yes" : "no card") +
                " (chip copy needs no SD; CAL CLEAR forgets both)";
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
            reply += "],\"frame_hz\":[";
            for (int i = 0; i < N; i++) { if (i) reply += ","; reply += String(frameHz_[i]); }
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
        saveCalSoon();
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
        saveCalSoon();
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
        bool changed = false;    // only re-attach when the pulse REALLY moved
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) {
                if (pulseMin_[i] != lo || pulseMax_[i] != hi) changed = true;
                pulseMin_[i] = lo; pulseMax_[i] = hi;
                if (dps >= 30) maxDps_[i] = dps;
            }
        if (changed) reattach(j); // the pulse range is set when the servo attaches
        saveCalSoon();
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
        saveCalSoon();
        forward("RANGE " + argv[1] + " " + argv[2]);
        reply = "OK servo travel " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) +
                " = " + String(r, 0) + " deg (home unchanged; check the travel "
                "away from home, then SETZERO if it needs re-trimming)";
        return true;
    }
    // SERVO [<1-10|name|ALL> <type>] — apply a known servo's pulse + speed + travel
    if (cmd == "SERVO") {
        if (argc < 3) {
            // the list comes from the generated table, so it can never name a
            // preset that does not exist (config/servos.json is the source)
            reply = "SERVO types: " + servoPresetNames() +
                    " | usage: SERVO <1-10|name|ALL> <type>";
            return true;
        }
        String t = argv[2];
        const ServoPreset* ps = findServoPreset(t);
        if (!ps) {
            reply = "ERR unknown servo (" + servoPresetNames() + ") — "
                    "or set a custom one with PULSE + RANGE + RATE";
            return true;
        }
        const int lo = ps->pulseMin, hi = ps->pulseMax, hz = ps->frameHz;
        const float dps = ps->maxDps, rng = ps->travelDeg;
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        bool changed = false;    // only re-attach when pulse/rate REALLY changed
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) {
                if (pulseMin_[i] != lo || pulseMax_[i] != hi || frameHz_[i] != hz)
                    changed = true;
                pulseMin_[i] = lo; pulseMax_[i] = hi; maxDps_[i] = dps;
                servoRange_[i] = rng; frameHz_[i] = hz; // trim unchanged — see RANGE
            }
        if (changed) reattach(j); // applies the new pulse range AND frame rate
        else writeServos();       // travel/speed changed: re-apply the pose
        saveCalSoon();
        forward("SERVO " + argv[1] + " " + argv[2]);
        reply = "OK " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) + " = " + t +
                " (" + String(lo) + "-" + String(hi) + "us, " + String(dps, 0) +
                " deg/s, " + String(rng, 0) + " deg travel, " + String(hz) + " Hz)";
        return true;
    }
    // RATE [<1-10|name|ALL> <hz>] — per-joint servo FRAME RATE. 50 = normal
    // hobby servo; the PDI-1181MG is a 330 Hz digital servo. A wrong rate can
    // make a digital servo chatter or cut torque ("disable itself").
    if (cmd == "RATE") {
        if (argc < 3) {
            reply = "RATE";
            for (int i = 0; i < N; i++)
                reply += " " + String(JOINT_NAMES[i]) + "=" + String(frameHz_[i]) + "Hz";
            return true;
        }
        int hz = argv[2].toInt();
        if (hz < NONG_FRAME_HZ_MIN || hz > NONG_FRAME_HZ_MAX) {
            reply = "ERR frame rate " + String(NONG_FRAME_HZ_MIN) + ".." +
                    String(NONG_FRAME_HZ_MAX) + " Hz (50 normal, 330 for PDI-1181MG)";
            return true;
        }
        String w = argv[1]; w.toUpperCase();
        int j = (w == "ALL") ? -1 : jointIndex(argv[1]);
        if (j < 0 && w != "ALL") { reply = "ERR joint 1-10, name, or ALL"; return true; }
        bool changed = false;    // only re-attach when the rate REALLY changed
        for (int i = 0; i < N; i++)
            if (j < 0 || i == j) {
                if (frameHz_[i] != hz) changed = true;
                frameHz_[i] = hz;
            }
        if (changed) reattach(j); // the frame rate is set when the servo attaches
        saveCalSoon();
        forward("RATE " + argv[1] + " " + argv[2]);
        reply = "OK frame rate " + (j < 0 ? String("all") : String(JOINT_NAMES[j])) +
                " = " + String(hz) + " Hz";
        return true;
    }
    // no RGB / PLAY / VOL here: nong hardware is 8 servos + the SD card only
    return false;
}

// Re-attach so a changed pulse range / frame rate takes effect immediately.
// j < 0 re-attaches every joint; otherwise ONLY joint j. Touching just the
// joint that changed matters: every attach() claims an ESP32 LEDC channel (the
// chip has 16, in 4 timer groups), and re-attaching all 10 servos for a
// one-joint change ran the board out of them and crashed it.
void NongModule::reattach(int j) {
    if (!attached_) return;
    for (int i = 0; i < N; i++) {
        if (j >= 0 && i != j) continue;
        if (pins_[i] < 0) continue;
        if (servos_[i].attached()) servos_[i].detach();
        servos_[i].setPeriodHertz(frameHz_[i]);   // re-apply the per-joint rate
        servos_[i].attach(pins_[i], pulseMin_[i], pulseMax_[i]);
    }
    writeServos();
}

void NongModule::addCapabilities(JsonArray caps) {
    caps.add("joints");       // the arm/pose card
    caps.add("servos");       // per-joint servo type, gear, pulse, travel, rate
    caps.add("calibration");  // SETZERO / CAL
    if (link_) caps.add("link");
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
    JsonArray fhz = o["frame_hz"].to<JsonArray>();
    for (int i = 0; i < N; i++) {
        gp.add(gearPinion_[i]); gg.add(gearGear_[i]);
        pmin.add(pulseMin_[i]); pmax.add(pulseMax_[i]);
        mdps.add(maxDps_[i]); srng.add(servoRange_[i]); fhz.add(frameHz_[i]);
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
