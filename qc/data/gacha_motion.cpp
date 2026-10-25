// The check inserts actual GachaModule methods/command branches below.
// IO is fake; the motion state machine and centering clock are production C++.
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cctype>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include "esp32_hardware_gacha_module.h"
#include "modules/gacha/GachaMath.h"
struct String : std::string {
    using std::string::string;
    using std::string::operator=;
    String(long value) : std::string(std::to_string(value)) {}
    long toInt() const { return std::strtol(c_str(), nullptr, 10); }
    void toLowerCase() {
        for (char& c : *this) c = (char)std::tolower((unsigned char)c);
    }
    bool equalsIgnoreCase(const char* other) const {
        if (size() != std::strlen(other)) return false;
        for (size_t i = 0; i < size(); ++i)
            if (std::tolower((unsigned char)(*this)[i]) != std::tolower((unsigned char)other[i])) return false;
        return true;
    }
};
constexpr int PWM_Max = 1023;
uint32_t clockMs = 0;
int delayCalls = 0, removedCfg = 0;
uint32_t millis() { return clockMs; }
void delay(uint32_t ms) { ++delayCalls; clockMs += ms; }
struct Controller {
    int pwm = 0;
    std::vector<int> history;
    void spin(int value) { pwm = value; history.push_back(value); }
};
struct Preferences {
    bool begin(const char*, bool) { return true; }
    void remove(const char*) { ++removedCfg; }
    void end() {}
};
class GachaModule {
public:
    enum State { IDLE, TURNING, HOMING };
    enum Job { JOB_SPIN, JOB_HOME, JOB_DISPENSE, JOB_NUDGE, JOB_CALIB };
    enum SettlePhase { SETTLE_NONE, SETTLE_INTAKE, SETTLE_ROCK_FWD, SETTLE_ROCK_BACK,
                       SETTLE_CENTER, SETTLE_ADVANCE, SETTLE_VERIFY, SETTLE_PAUSE, SETTLE_NUDGE,
                       CALIB_REVERSE, CALIB_REST, CALIB_FIND, CALIB_SPAN, CALIB_BACK, CALIB_VERIFY };
    Controller io;
    Controller* motor_ = &io;
    gachamath::HallCounter hall_;
    gachamath::CenterMotion center_;
    bool sensor = false, activeLow_ = true;
    int magnets_ = GACHA_MAGNETS, slots_ = GACHA_SLOTS, drop_ = GACHA_DROP_SLOTS;
    int intakeDwellMs_ = GACHA_INTAKE_DWELL_MS;
    int speed_ = GACHA_SPEED, dir_ = 1, timeoutMs_ = GACHA_SLOT_TIMEOUT_MS;
    int debounceMs_ = GACHA_DEBOUNCE_MS, settleMs_ = GACHA_SETTLE_MS;
    int overshootMs_ = GACHA_OVERSHOOT_MS, overshootSpeed_ = GACHA_OVERSHOOT_SPEED;
    int returnMs_ = GACHA_RETURN_MS, returnSpeed_ = GACHA_RETURN_SPEED;
    int centerSpeed_ = GACHA_CENTER_SPEED, pauseMs_ = GACHA_PAUSE_MS;
    int advanceMs_ = GACHA_CENTER_ADVANCE_MS;
    int fallbackSlotMs_ = GACHA_FALLBACK_SLOT_MS;
    State state_ = IDLE;
    Job job_ = JOB_SPIN;
    SettlePhase settlePhase_ = SETTLE_NONE;
    int want_ = 0, got_ = 0, sign_ = 1, pos_ = 2, stock_ = 7, given_ = 4;
    bool posKnown_ = true, open_ = true, draining_ = false, lastForced_ = false;
    int drainMax_ = 0, drainCount_ = 0;
    bool testing_ = false;
    int testMax_ = 0, testCount_ = 0;
    uint32_t total_ = 0, seq_ = 0, spanOnMs_ = 0, spanTickMs_ = 0;
    bool spanWasOn_ = false;
    int learnedAdvanceMs_ = 0;
    String lastWho_;
    uint32_t hits_ = 0, lastPassMs_ = 0, settleUntil_ = 0, phaseUntil_ = 0;
    uint32_t startMs_ = 0, lastMs_ = 0;
    String lastResult_ = "turning";
    String motionResult_ = "idle";
    int saves = 0, countSaves = 0;
    bool hallActive() const { return sensor; }
    int perSlot() const { return gachamath::passesPerSlot(magnets_, slots_); }
    void motorOff() { if (motor_) motor_->spin(0); }
    void saveCfg() { ++saves; }
    void saveCounts() { ++countSaves; }
    void startTurn(Job job, int passes);
    void startNudge(int pwm, uint32_t duration);
    void startCenter(uint32_t now, uint32_t rest = GACHA_CENTER_WAIT_MS);
    void startCalibrate();
    void startSpan(uint32_t now);
    void invalidateReference(bool resetHall);
    void finish(const char* result);
    void resetDefaults();
    void loop();
    bool nudge(String argv[], int argc, String& reply);
    bool calibrate(String& reply);
    bool test(String argv[], int argc, String& reply);
    bool spin(String argv[], int argc, String& reply);
    bool home(String& reply);
    bool drain(String argv[], int argc, String& reply);
    bool stop(String& reply);
    bool config(String argv[], int argc, String& reply);
};

/*__PRODUCTION_METHODS__*/

int failures = 0;
void check(bool condition, const char* label) {
    std::cout << (condition ? "CPP_PASS " : "CPP_FAIL ") << label << '\n';
    if (!condition) ++failures;
}
void tick(GachaModule& m, uint32_t now, bool sensor) {
    clockMs = now; m.sensor = sensor; m.loop();
}
void calibrationScenario(bool verify, uint32_t start) {
    GachaModule m; String reply; clockMs = start; m.timeoutMs_ = 1000;
    const int oldAdvance = m.advanceMs_;
    m.calibrate(reply);
    check(reply == "OK calibrating" && clockMs == start, "calibration starts asynchronously");
    m.calibrate(reply); check(reply == "ERR busy", "calibration cannot replace an active job");
    auto lastPhase = GachaModule::SETTLE_NONE;
    uint32_t phaseAt = start;
    for (uint32_t elapsed = 0; elapsed <= GACHA_CALIB_MAX_MS && m.state_ != GachaModule::IDLE; ++elapsed) {
        const uint32_t now = start + elapsed;
        if (lastPhase != m.settlePhase_) { lastPhase = m.settlePhase_; phaseAt = now; }
        bool sensor = false;
        if (lastPhase == GachaModule::CALIB_FIND) sensor = now - phaseAt >= 70;
        if (lastPhase == GachaModule::CALIB_SPAN) sensor = now - phaseAt < 130;
        if (lastPhase == GachaModule::CALIB_BACK) sensor = true;
        if (lastPhase == GachaModule::CALIB_VERIFY) sensor = verify;
        tick(m, now, sensor);
    }
    check(m.state_ == GachaModule::IDLE && m.io.pwm == 0, "calibration terminates with motor off");
    if (verify) {
        check(m.motionResult_ == "done" && m.saves == 1, "only verified Hall calibration is saved");
        check(m.advanceMs_ > 0 && m.advanceMs_ <= GACHA_ADVANCE_MAX_MS,
              "calibration learns a bounded advance for future cycles");
    } else {
        check(m.motionResult_ == "jam" && m.saves == 0 && m.advanceMs_ == oldAdvance,
              "failed calibration verification never reports or saves success");
    }
    check(m.stock_ == 7 && m.given_ == 4 && !m.posKnown_, "calibration does not dispense or claim pocket reference");
}
/*__CONFIG_REFERENCE_CHECKS__*/

int main() {
    GachaConfigChecks::run();
    {
        GachaModule m; String reply, args[] = {"GTEST"}; m.magnets_ = 8;
        m.test(args, 1, reply);
        check(reply == "OK testing" && m.testMax_ == 1 && m.want_ == m.perSlot(),
              "omitted GTEST count defaults to one pocket, not every configured slot");
        check(m.stock_ == 7 && m.given_ == 4, "default one-pocket GTEST does not dispense");
    }
    {
        GachaModule m; String reply; m.hall_.stable = true; m.motionResult_ = "jam";
        m.home(reply);
        check(reply == "OK already at a magnet" && m.motionResult_ == "done" && m.posKnown_ && m.pos_ == 0,
              "already-at-Hall HOME replaces the previous motion fault truthfully");
        m.state_ = GachaModule::TURNING; m.motionResult_ = "turning"; m.home(reply);
        check(reply == "ERR busy" && m.motionResult_ == "turning", "HOME cannot claim completion while another job runs");
    }
    {
        GachaModule m; clockMs = 0; m.timeoutMs_ = 200;
        m.startTurn(GachaModule::JOB_DISPENSE, 1); m.startCenter(0);
        for (uint32_t now = 0; now <= 200; ++now) tick(m, now, false);
        check(m.state_ == GachaModule::IDLE && m.io.pwm == 0, "missing Hall stops at deadline");
        check(m.lastResult_ == "jam", "missing Hall is a fault, never success");
        check(m.settlePhase_ == GachaModule::SETTLE_NONE, "fault does not enter success pause");
        check(m.stock_ == 7 && m.given_ == 4, "fault does not invent another dispense");
    }
    {
        GachaModule m; clockMs = 0; m.timeoutMs_ = 200;
        m.startTurn(GachaModule::JOB_HOME, 1); m.startCenter(0);
        for (uint32_t now = 0; now <= 200; ++now) tick(m, now, false);
        check(m.pos_ == 2 && m.state_ == GachaModule::IDLE, "failed HOME does not claim pocket zero");
        check(m.motionResult_ == "jam", "failed HOME exposes its own fault result");
    }
    {
        GachaModule m; clockMs = 0; m.loop();
        m.startTurn(GachaModule::JOB_DISPENSE, 1); m.startCenter(0);
        tick(m, 40, false);
        check(m.io.pwm == m.centerSpeed_, "center pulse starts after configured wait");
        tick(m, 55, false);
        check(m.io.pwm == 0, "center pulse ends without blocking loop");
        tick(m, 89, false);
        check(m.io.pwm == 0, "center motor rests for full configured interval");
        tick(m, 90, false);
        check(m.io.pwm == m.centerSpeed_, "next center pulse uses clock, not delay");
        tick(m, 91, true); tick(m, 92, false);
        check(m.settlePhase_ == GachaModule::SETTLE_CENTER, "one noisy raw Hall sample cannot finish");
        tick(m, 100, true); tick(m, 105, true);
        check(m.settlePhase_ == GachaModule::SETTLE_ADVANCE, "debounced Hall starts bounded advance");
        tick(m, 123, true); tick(m, 158, true);
        check(m.settlePhase_ == GachaModule::SETTLE_PAUSE && m.io.pwm == 0, "Hall verified at rest enters pause");
        tick(m, 5157, true);
        check(m.state_ != GachaModule::IDLE && m.io.pwm == 0, "default five-second pause is not shortened");
        tick(m, 5158, true);
        check(m.state_ == GachaModule::IDLE && m.lastResult_ == "done", "only confirmed Hall completes after pause");
    }
    {
        GachaModule m; clockMs = 0; m.intakeDwellMs_ = 0; m.loop(); m.startTurn(GachaModule::JOB_DISPENSE, 1);
        tick(m, 10, true); tick(m, 15, true);
        check(m.settlePhase_ == GachaModule::SETTLE_ROCK_FWD && m.io.pwm > 0, "arrival starts forward rock");
        tick(m, 195, true);
        check(m.settlePhase_ == GachaModule::SETTLE_ROCK_BACK && m.io.pwm < 0, "forward deadline starts reverse rock");
        tick(m, 196, false); tick(m, 201, false); tick(m, 475, false);
        check(m.settlePhase_ == GachaModule::SETTLE_CENTER && m.io.pwm == 0, "reverse deadline starts bounded center");
        tick(m, 575, false); tick(m, 578, true); tick(m, 583, true);
        tick(m, 601, true); tick(m, 636, true);
        check(m.settlePhase_ == GachaModule::SETTLE_PAUSE && m.io.pwm == 0, "full phase chain confirms Hall");
        tick(m, 5636, true);
        check(m.state_ == GachaModule::IDLE && m.lastResult_ == "done", "full phase chain completes after five-second hold");
    }
    for (auto phase : {GachaModule::SETTLE_INTAKE, GachaModule::SETTLE_ROCK_FWD, GachaModule::SETTLE_ROCK_BACK,
                       GachaModule::SETTLE_CENTER, GachaModule::SETTLE_ADVANCE, GachaModule::SETTLE_VERIFY,
                       GachaModule::SETTLE_PAUSE, GachaModule::SETTLE_NUDGE, GachaModule::CALIB_REVERSE,
                       GachaModule::CALIB_REST, GachaModule::CALIB_FIND, GachaModule::CALIB_SPAN,
                       GachaModule::CALIB_BACK, GachaModule::CALIB_VERIFY}) {
        GachaModule m; String reply; clockMs = 0;
        m.startTurn(GachaModule::JOB_DISPENSE, 1); m.settlePhase_ = phase;
        m.center_.begin(0, 200, 20, 35, 40); m.io.spin(250);
        m.stop(reply); tick(m, 10000, false);
        check(m.state_ == GachaModule::IDLE && m.settlePhase_ == GachaModule::SETTLE_NONE,
              "STOP cancels active phase and stale timers");
        check(m.io.pwm == 0 && !m.center_.active && m.lastResult_ == "stopped",
              "STOP cannot restart motor on later loop");
    }
    {
        GachaModule m; clockMs = UINT32_MAX - 30; m.timeoutMs_ = 200;
        const uint32_t start = clockMs; m.startTurn(GachaModule::JOB_DISPENSE, 1); m.startCenter(start);
        tick(m, start + 40, false); check(m.io.pwm > 0, "center clock handles millis wrap");
        tick(m, start + 200, false);
        check(m.io.pwm == 0 && m.lastResult_ == "jam", "center timeout handles millis wrap");
    }
    for (const auto& values : std::vector<std::pair<String, String>>{
             {"400", "-1"}, {"400", "0"}, {"400", "1001"}, {"400", "abc"},
             {"400", "999999999999999999999999"}, {"0", "20"}, {"1024", "20"},
             {"-1024", "20"}, {"x", "20"}, {"400x", "20"}, {"", "20"}, {"400", ""}}) {
        GachaModule m; String reply, args[] = {"GNUDGE", values.first, values.second};
        const uint32_t before = clockMs; m.nudge(args, 3, reply);
        check(reply.rfind("ERR", 0) == 0 && m.io.history.empty() && clockMs == before,
              "invalid nudge cannot move or block");
    }
    {
        GachaModule m; String reply, args[] = {"GNUDGE", "-250", "20"}; clockMs = UINT32_MAX - 10;
        const uint32_t start = clockMs; m.nudge(args, 3, reply);
        check(reply == "OK nudging" && m.io.pwm == -250 && clockMs == start, "valid nudge returns immediately");
        m.nudge(args, 3, reply);
        check(reply == "ERR busy" && m.io.pwm == -250, "busy nudge is refused without disturbing job");
        tick(m, start + 19, false); check(m.io.pwm == -250, "nudge respects requested duration");
        tick(m, start + 20, false);
        check(m.io.pwm == 0 && m.state_ == GachaModule::IDLE, "nudge deadline works across millis wrap");
        check(m.stock_ == 7 && m.given_ == 4 && m.pos_ == 2, "nudge does not count or claim pocket position");
        check(!m.posKnown_, "manual nudge invalidates pocket reference");
    }
    {
        GachaModule m; String reply, args[] = {"GNUDGE", "250", "20"}; m.motor_ = nullptr;
        m.nudge(args, 3, reply); check(reply.rfind("ERR no motor", 0) == 0, "nudge refuses missing motor");
    }
    {
        GachaModule m; String reply, args[] = {"GCFG", "CLEAR"}; removedCfg = 0;
        m.overshootMs_ = m.overshootSpeed_ = m.returnMs_ = m.returnSpeed_ = 1;
        m.centerSpeed_ = m.pauseMs_ = m.fallbackSlotMs_ = 1;
        m.intakeDwellMs_ = m.advanceMs_ = 1; m.config(args, 2, reply);
        check(m.overshootMs_ == GACHA_OVERSHOOT_MS && m.overshootSpeed_ == GACHA_OVERSHOOT_SPEED,
              "CLEAR restores forward phase defaults");
        check(m.returnMs_ == GACHA_RETURN_MS && m.returnSpeed_ == GACHA_RETURN_SPEED,
              "CLEAR restores reverse phase defaults");
        check(m.centerSpeed_ == GACHA_CENTER_SPEED && m.pauseMs_ == GACHA_PAUSE_MS &&
              m.fallbackSlotMs_ == GACHA_FALLBACK_SLOT_MS, "CLEAR restores center pause and fallback defaults");
        check(m.saves == 1 && m.stock_ == 7 && m.given_ == 4, "CLEAR persists settings without changing stock/counts");
        check(m.intakeDwellMs_ == GACHA_INTAKE_DWELL_MS && m.advanceMs_ == GACHA_CENTER_ADVANCE_MS,
              "CLEAR restores intake and learned advance defaults");
        m.state_ = GachaModule::TURNING; m.config(args, 2, reply);
        check(reply == "ERR busy" && removedCfg == 1 && m.saves == 1, "busy CLEAR cannot erase persisted settings");
    }
    {
        GachaModule m; clockMs = 0; m.timeoutMs_ = 200;
        m.startTurn(GachaModule::JOB_DISPENSE, 1);
        tick(m, GACHA_INTAKE_DWELL_MS - 1, false);
        check(m.io.pwm == 0 && m.state_ != GachaModule::IDLE, "intake dwell keeps motor off without premature jam");
        tick(m, GACHA_INTAKE_DWELL_MS, false);
        check(m.io.pwm == m.speed_ && m.lastPassMs_ == GACHA_INTAKE_DWELL_MS, "intake completion starts slot timeout from motor start");
    }
    {
        GachaModule m; String reply; clockMs = 0; m.loop();
        m.startTurn(GachaModule::JOB_SPIN, 1); m.startCenter(0);
        tick(m, 40, true); tick(m, 45, true); tick(m, 63, false); tick(m, 68, false); tick(m, 98, false);
        check(m.motionResult_ == "jam" && m.io.pwm == 0, "leaving Hall after advance fails final verification");
    }
    {
        GachaModule m; String reply, args[] = {"GTEST", "3"}; m.magnets_ = 8; m.slots_ = 4;
        m.test(args, 2, reply);
        check(reply == "OK testing" && m.want_ == 2 && m.testMax_ == 3,
              "GTEST starts one pocket and remembers total pockets");
        m.test(args, 2, reply); check(reply == "ERR busy", "GTEST refuses an active job");
    }
    for (const String value : {"-1", "0", "101", "bad", "999999999999999999999", ""}) {
        GachaModule m; String reply, args[] = {"GTEST", value}; m.test(args, 2, reply);
        check(reply.rfind("ERR", 0) == 0 && m.io.history.empty(), "invalid GTEST cannot become a default movement");
    }
    for (const String value : {"2147483647", "-2147483648", "999999999999999999999", "51", "-51", "2x", ""}) {
        GachaModule m; String reply, args[] = {"GSPIN", value}; m.magnets_ = 8;
        m.spin(args, 2, reply);
        check(reply.rfind("ERR", 0) == 0 && m.io.history.empty(), "GSPIN validates token and bounds before multiplication");
    }
    {
        GachaModule m; String reply, args[] = {"GSPIN", "-50"}; m.magnets_ = 8;
        m.spin(args, 2, reply); check(m.want_ == 100 && m.sign_ == -1, "negative GSPIN boundary remains supported");
    }
    {
        GachaModule m; String reply, args[] = {"GSPIN", "-100", "MAG"}; m.magnets_ = 8;
        m.spin(args, 3, reply); check(m.want_ == 100 && m.sign_ == -1, "GSPIN MAG uses arrivals rather than pockets");
    }
    {
        GachaModule m; String reply, args[] = {"GTEST", "3"}; clockMs = 0; m.loop();
        m.magnets_ = 8; m.overshootMs_ = m.returnMs_ = 0; m.pauseMs_ = 5;
        m.test(args, 2, reply); int changes = 0, previous = 0; bool pauseMotorOff = true;
        for (uint32_t now = 0; now <= 2500 && m.state_ != GachaModule::IDLE; ++now) {
            const bool sensor = m.settlePhase_ != GachaModule::SETTLE_NONE ||
                                (now >= 10 && ((now - 10) / 20) % 2 == 0);
            tick(m, now, sensor);
            if (m.settlePhase_ == GachaModule::SETTLE_PAUSE) pauseMotorOff &= m.io.pwm == 0;
            if (m.testCount_ != previous) { ++changes; previous = m.testCount_; }
        }
        check(m.testCount_ == 3 && changes == 3 && !m.testing_ && m.motionResult_ == "done",
              "actual loop verifies and completes each self-test pocket separately");
        check(pauseMotorOff && m.stock_ == 7 && m.given_ == 4, "per-pocket test pauses without dispensing");
    }
    {
        GachaModule m; clockMs = 0; m.startTurn(GachaModule::JOB_SPIN, 1);
        m.settlePhase_ = GachaModule::SETTLE_PAUSE; m.phaseUntil_ = 100;
        tick(m, 90, false); tick(m, 100, false);
        check(m.motionResult_ == "jam" && m.io.pwm == 0, "lost Hall during pause cannot finish successfully");
    }
    {
        GachaModule m; String reply, args[] = {"GDRAIN", "2"}; clockMs = 0; m.stock_ = 2;
        m.drain(args, 2, reply);
        check(reply == "OK drain started" && m.stock_ == 1 && m.given_ == 5, "drain reserves one prize at a time");
        m.finish("done"); check(m.draining_ && m.stock_ == 0 && m.given_ == 6, "drain starts exactly one next prize");
        m.finish("done"); check(!m.draining_ && m.state_ == GachaModule::IDLE && m.given_ == 6, "drain stops at stock and request limit");
    }
    {
        GachaModule m; String reply, args[] = {"GDRAIN", "2"}; m.open_ = false;
        m.drain(args, 2, reply);
        check(reply == "ERR event closed" && m.io.history.empty(), "drain cannot bypass closed event");
        m.open_ = true; m.stock_ = -1; m.drain(args, 1, reply);
        check(reply.rfind("ERR", 0) == 0 && m.io.history.empty(), "uncounted stock needs an explicit drain limit");
    }
    {
        GachaModule m; String reply, args[] = {"GDRAIN", "3"}; clockMs = 0; m.drain(args, 2, reply);
        m.stop(reply); tick(m, 10000, false);
        check(!m.draining_ && m.state_ == GachaModule::IDLE && m.given_ == 5, "STOP prevents drain restart");
    }
    for (const String value : {"-1", "0", "1000", "bad", "999999999999999999999", ""}) {
        GachaModule m; String reply, args[] = {"GDRAIN", value}; m.drain(args, 2, reply);
        check(reply.rfind("ERR", 0) == 0 && m.io.history.empty(), "invalid drain never defaults to hundreds of prizes");
    }
    {
        GachaModule m; String reply; clockMs = 0; m.timeoutMs_ = 200; m.calibrate(reply);
        for (uint32_t now = 0; now < 1000 && m.state_ != GachaModule::IDLE; ++now) tick(m, now, false);
        check(m.motionResult_ == "jam" && m.io.pwm == 0 && m.saves == 0, "calibration with missing Hall fails without saving");
    }
    {
        GachaModule m; String reply; clockMs = 0; m.calibrate(reply);
        m.settlePhase_ = GachaModule::CALIB_REST; m.phaseUntil_ = 10000;
        tick(m, GACHA_CALIB_MAX_MS, false);
        check(m.motionResult_ == "jam" && m.io.pwm == 0, "whole calibration has a hard deadline");
    }
    calibrationScenario(true, 0);
    calibrationScenario(false, 0);
    calibrationScenario(true, UINT32_MAX - 400);
    for (int settle : {0, 45}) for (int pause : {0, 60}) for (bool keepHall : {false, true}) {
        GachaModule m; clockMs = 0; m.loop();
        m.overshootMs_ = m.returnMs_ = 0; m.settleMs_ = settle; m.pauseMs_ = pause; m.timeoutMs_ = 150;
        m.startTurn(GachaModule::JOB_HOME, 1);
        tick(m, 10, true); tick(m, 15, true);
        check(m.state_ != GachaModule::IDLE, "no-rock arrival still requires verification, including pause=0");
        for (uint32_t now = 16; now < 500 && m.state_ != GachaModule::IDLE; ++now) tick(m, now, keepHall);
        check(m.motionResult_ == (keepHall ? "done" : "jam") && m.io.pwm == 0,
              "no-rock/settle/pause combinations cannot bypass resting Hall verification");
        check(m.posKnown_ == keepHall, "only verified no-rock HOME establishes pocket reference");
    }
    {
        GachaModule m; clockMs = 0; m.posKnown_ = true; m.fallbackSlotMs_ = 20;
        m.startTurn(GachaModule::JOB_SPIN, 1); tick(m, 20, false);
        check(m.state_ == GachaModule::IDLE && m.io.pwm == 0 && m.motionResult_ == "timed",
              "explicit timed fallback stops and reports estimated completion");
        check(!m.posKnown_, "timed fallback cannot retain a sensor-confirmed position");
    }
    check(delayCalls == 0, "all tested command and loop paths are nonblocking");
    return failures ? 1 : 0;
}
