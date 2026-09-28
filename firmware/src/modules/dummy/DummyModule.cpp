#include "modules/dummy/DummyModule.h"
#include "modules/dummy/DummyMath.h"
#include "core/HwConfig.h"
#include <Preferences.h>

static const char* JOINT_NAMES[DummyModule::N] = NONG_JOINT_NAMES;

// ADC1 only: ADC2 is taken by the WiFi radio and reads garbage while it is on.
static bool adc1Pin(int g) { return g >= 32 && g <= 39; }

void DummyModule::defaults() {
    const int ch[N] = DUMMY_CH_DEF;
    const float lo[N] = NONG_MIN_DEF, hi[N] = NONG_MAX_DEF;
    const int sel[4] = DUMMY_MUX_SEL;
    for (int i = 0; i < N; i++) {
        ch_[i] = ch[i];
        zero_[i] = DUMMY_ZERO_DEF;
        span_[i] = DUMMY_SPAN_DEF;
        dir_[i] = 1;
        lo_[i] = lo[i];
        hi_[i] = hi[i];
    }
    muxSig_ = DUMMY_MUX_SIG;
    for (int k = 0; k < 4; k++) muxSel_[k] = sel[k];
}

void DummyModule::begin() {
    defaults();
    load();
    for (int i = 0; i < N; i++) raw_[i] = -1;
    setupPins();
}

void DummyModule::setupPins() {
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);   // the whole 0-3.3 V a pot swings over
    if (muxSig_ >= 0)
        for (int k = 0; k < 4; k++)
            if (muxSel_[k] >= 0) pinMode(muxSel_[k], OUTPUT);
    primed_ = false;                  // new wiring: do not blend old readings in
}

bool DummyModule::wired(int i) const {
    if (ch_[i] < 0) return false;
    return muxSig_ >= 0 ? ch_[i] < 16 : adc1Pin(ch_[i]);
}

int DummyModule::readChannel(int i) {
    int pin = ch_[i];
    if (muxSig_ >= 0) {
        for (int k = 0; k < 4; k++)
            if (muxSel_[k] >= 0) digitalWrite(muxSel_[k], (ch_[i] >> k) & 1);
        // The mux output and the ADC's sample capacitor need a moment after
        // the switch; the first read after it still carries the last channel.
        delayMicroseconds(20);
        analogRead(muxSig_);
        pin = muxSig_;
    }
    long sum = 0;
    for (int s = 0; s < DUMMY_OVERSAMPLE; s++) sum += analogRead(pin);
    return (int)(sum / DUMMY_OVERSAMPLE);
}

void DummyModule::loop() {
    const uint32_t now = millis();
    if (now - lastTick_ < DUMMY_TICK_MS) return;
    lastTick_ = now;
    for (int i = 0; i < N; i++) {
        if (!wired(i)) { raw_[i] = -1; continue; }
        const float r = (float)readChannel(i);
        raw_[i] = (primed_ && raw_[i] >= 0) ? dummymath::smooth(raw_[i], r, DUMMY_SMOOTH) : r;
    }
    primed_ = true;
}

float DummyModule::degOf(int i) const {
    return dummymath::potToDeg(raw_[i], zero_[i], span_[i], dir_[i],
                               lo_[i], hi_[i], (float)DUMMY_ADC_MAX);
}

int DummyModule::jointIndex(const String& token) const {
    for (int i = 0; i < N; i++)
        if (token.equalsIgnoreCase(JOINT_NAMES[i])) return i;
    int v = token.toInt();
    if (v >= 1 && v <= N && token[0] >= '0' && token[0] <= '9') return v - 1;
    return -1;
}

String DummyModule::calJson() const {
    JsonDocument d;
    JsonArray ch = d["ch"].to<JsonArray>(), z = d["zero"].to<JsonArray>(),
              sp = d["span"].to<JsonArray>(), dr = d["dir"].to<JsonArray>(),
              lo = d["min"].to<JsonArray>(), hi = d["max"].to<JsonArray>();
    for (int i = 0; i < N; i++) {
        ch.add(ch_[i]); z.add(roundf(zero_[i])); sp.add(span_[i]);
        dr.add(dir_[i]); lo.add(lo_[i]); hi.add(hi_[i]);
    }
    JsonObject m = d["mux"].to<JsonObject>();
    m["sig"] = muxSig_;
    JsonArray s = m["sel"].to<JsonArray>();
    for (int k = 0; k < 4; k++) s.add(muxSel_[k]);
    String out;
    serializeJson(d, out);
    return out;
}

bool DummyModule::handleCommand(String argv[], int argc, String& reply) {
    String& cmd = argv[0];   // already uppercased by the router

    // The same answer, in the same format, as the robot's POSE?. A joint with
    // no pot answers '-', which POSE on the robot already reads as "leave this
    // joint where it is" - so a half-wired dummy can still drive the robot.
    if (cmd == "POSE?") {
        reply = "";
        for (int i = 0; i < N; i++) {
            if (i) reply += ' ';
            reply += (wired(i) && raw_[i] >= 0) ? String(degOf(i), 1) : String("-");
        }
        return true;
    }
    if (cmd == "POT?") {
        reply = "";
        for (int i = 0; i < N; i++) {
            if (i) reply += ' ';
            reply += String(raw_[i] < 0 ? -1 : (int)roundf(raw_[i]));
        }
        return true;
    }
    if (cmd == "DCAL?") { reply = calJson(); return true; }
    if (cmd == "DCAL") {
        if (argc == 2 && argv[1].equalsIgnoreCase("CLEAR")) {
            defaults(); save(); setupPins();
            reply = "OK dummy calibration back to defaults";
            return true;
        }
        if (argc < 4) { reply = "ERR DCAL <1-10|name|ALL> <CH|ZERO|SPAN|DIR|MIN|MAX> <value>"; return true; }
        const bool all = argv[1].equalsIgnoreCase("ALL");
        const int j = all ? -1 : jointIndex(argv[1]);
        if (!all && j < 0) { reply = "ERR joint 1-10, name, or ALL"; return true; }
        String f = argv[2]; f.toUpperCase();
        const float v = argv[3].toFloat();
        const int iv = argv[3].toInt();
        // Check once, before touching anything: ALL must not half-apply.
        if (f == "CH") {
            const bool ok = iv == -1 || (muxSig_ >= 0 ? (iv >= 0 && iv < 16) : adc1Pin(iv));
            if (!ok) { reply = muxSig_ >= 0 ? "ERR mux channel 0-15, or -1 = no pot"
                                            : "ERR ADC pin 32-39, or -1 = no pot"; return true; }
        } else if (f == "ZERO") {
            if (v < -2 * DUMMY_ADC_MAX || v > 3 * DUMMY_ADC_MAX) { reply = "ERR zero out of range"; return true; }
        } else if (f == "SPAN") {
            if (v < 10 || v > 3600) { reply = "ERR span 10-3600 deg"; return true; }
        } else if (f == "DIR") {
            if (iv != 1 && iv != -1) { reply = "ERR dir 1 or -1"; return true; }
        } else if (f == "MIN" || f == "MAX") {
            if (v < 0 || v > 270) { reply = "ERR limit 0-270 deg"; return true; }
            for (int i = 0; i < N; i++) {
                if (!all && i != j) continue;
                const float lo = f == "MIN" ? v : lo_[i], hi = f == "MAX" ? v : hi_[i];
                if (lo >= hi) { reply = "ERR min must be below max"; return true; }
            }
        } else { reply = "ERR field CH ZERO SPAN DIR MIN MAX"; return true; }
        for (int i = 0; i < N; i++) {
            if (!all && i != j) continue;
            if (f == "CH") ch_[i] = iv;
            else if (f == "ZERO") zero_[i] = v;
            else if (f == "SPAN") span_[i] = v;
            else if (f == "DIR") dir_[i] = iv;
            else if (f == "MIN") lo_[i] = v;
            else hi_[i] = v;
        }
        save();
        reply = "OK " + String(all ? "all" : JOINT_NAMES[j]) + " " + f + "=" + argv[3];
        return true;
    }
    // Hold the dummy in a known pose and tell it so: each joint works out its
    // own zero from where it is now. No ADC numbers for a person to read off.
    if (cmd == "DZERO") {
        if (argc < 2) { reply = "ERR DZERO <1-10|name|ALL> [deg]"; return true; }
        const bool all = argv[1].equalsIgnoreCase("ALL");
        const int j = all ? -1 : jointIndex(argv[1]);
        if (!all && j < 0) { reply = "ERR joint 1-10, name, or ALL"; return true; }
        const float deg = argc >= 3 ? argv[2].toFloat() : 90.0f;
        int done = 0;
        for (int i = 0; i < N; i++) {
            if ((!all && i != j) || !wired(i) || raw_[i] < 0) continue;
            zero_[i] = dummymath::zeroFor(raw_[i], deg, span_[i], dir_[i], (float)DUMMY_ADC_MAX);
            done++;
        }
        if (!done) { reply = "ERR no pot wired on that joint"; return true; }
        save();
        reply = "OK zeroed " + String(done) + " joint(s) at " + String(deg, 1);
        return true;
    }
    if (cmd == "DMUX?") {
        reply = "{\"sig\":" + String(muxSig_) + ",\"sel\":[" + String(muxSel_[0]) + "," +
                String(muxSel_[1]) + "," + String(muxSel_[2]) + "," + String(muxSel_[3]) + "]}";
        return true;
    }
    if (cmd == "DMUX") {
        if (argc == 2 && argv[1].equalsIgnoreCase("OFF")) {
            muxSig_ = -1;
            save(); setupPins();
            reply = "OK no mux: each joint's CH is its own ADC pin (32-39)";
            return true;
        }
        if (argc < 6) { reply = "ERR DMUX <sig> <s0> <s1> <s2> <s3> | OFF"; return true; }
        const int sig = argv[1].toInt();
        if (!adc1Pin(sig)) { reply = "ERR sig must be an ADC1 pin 32-39"; return true; }
        int sel[4];
        for (int k = 0; k < 4; k++) {
            sel[k] = argv[2 + k].toInt();
            if (sel[k] < 0 || !HwConfig::pinUsable(sel[k], true) || sel[k] == sig) {
                reply = "ERR select pin " + argv[2 + k] + " cannot be an output";
                return true;
            }
        }
        muxSig_ = sig;
        for (int k = 0; k < 4; k++) muxSel_[k] = sel[k];
        save(); setupPins();
        reply = "OK mux on " + String(sig);
        return true;
    }
    return false;
}

void DummyModule::save() {
    CalBlob b{};
    b.magic = CAL_MAGIC;
    b.version = CAL_VERSION;
    for (int i = 0; i < N; i++) {
        b.ch[i] = ch_[i]; b.zero[i] = zero_[i]; b.span[i] = span_[i];
        b.lo[i] = lo_[i]; b.hi[i] = hi_[i]; b.dir[i] = dir_[i];
    }
    b.muxSig = muxSig_;
    for (int k = 0; k < 4; k++) b.muxSel[k] = muxSel_[k];
    Preferences p;
    if (!p.begin("dummycal", false)) return;
    p.putBytes("cal", &b, sizeof(b));
    p.end();
}

bool DummyModule::load() {
    Preferences p;
    if (!p.begin("dummycal", true)) return false;
    CalBlob b{};
    size_t n = p.getBytes("cal", &b, sizeof(b));
    p.end();
    // A blob from another layout is ignored whole - the defaults beat a mix.
    if (n != sizeof(b) || b.magic != CAL_MAGIC || b.version != CAL_VERSION) return false;
    for (int i = 0; i < N; i++) {
        ch_[i] = b.ch[i]; zero_[i] = b.zero[i];
        span_[i] = b.span[i] > 0 ? b.span[i] : DUMMY_SPAN_DEF;
        dir_[i] = b.dir[i] < 0 ? -1 : 1;
        if (b.lo[i] < b.hi[i]) { lo_[i] = b.lo[i]; hi_[i] = b.hi[i]; }
    }
    muxSig_ = b.muxSig;
    for (int k = 0; k < 4; k++) muxSel_[k] = b.muxSel[k];
    return true;
}

void DummyModule::addCapabilities(JsonArray caps) {
    caps.add("pots");   // the dummy card: live angles + calibration
}

void DummyModule::status(JsonObject o) {
    JsonArray joints = o["joints"].to<JsonArray>();
    JsonArray raw = o["raw"].to<JsonArray>();
    for (int i = 0; i < N; i++) {
        if (wired(i) && raw_[i] >= 0) joints.add(roundf(degOf(i) * 10) / 10);
        else joints.add(nullptr);
        raw.add(raw_[i] < 0 ? -1 : (int)roundf(raw_[i]));
    }
    JsonDocument cal;
    deserializeJson(cal, calJson());
    o["cal"] = cal.as<JsonObject>();
}
