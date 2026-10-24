// The check inserts actual GachaModule methods/command branches below.
// IO is fake; the motion state machine and centering clock are production C++.
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include "esp32_hardware_gacha_module.h"
#include "modules/gacha/GachaMath.h"
using String = std::string;
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
    enum Job { JOB_SPIN, JOB_HOME, JOB_DISPENSE, JOB_NUDGE };
    enum SettlePhase { SETTLE_NONE, SETTLE_ROCK_FWD, SETTLE_ROCK_BACK,
                       SETTLE_CENTER, SETTLE_PAUSE, SETTLE_NUDGE };
    Controller io;
    Controller* motor_ = &io;
    gachamath::HallCounter hall_;
    gachamath::CenterMotion center_;
    bool sensor = false, activeLow_ = true;
    int magnets_ = GACHA_MAGNETS, slots_ = GACHA_SLOTS, drop_ = GACHA_DROP_SLOTS;
    int speed_ = GACHA_SPEED, dir_ = 1, timeoutMs_ = GACHA_SLOT_TIMEOUT_MS;
    int debounceMs_ = GACHA_DEBOUNCE_MS, settleMs_ = GACHA_SETTLE_MS;
    int overshootMs_ = GACHA_OVERSHOOT_MS, overshootSpeed_ = GACHA_OVERSHOOT_SPEED;
    int returnMs_ = GACHA_RETURN_MS, returnSpeed_ = GACHA_RETURN_SPEED;
    int centerSpeed_ = GACHA_CENTER_SPEED, pauseMs_ = GACHA_PAUSE_MS;
    int fallbackSlotMs_ = GACHA_FALLBACK_SLOT_MS;
    State state_ = IDLE;
    Job job_ = JOB_SPIN;
    SettlePhase settlePhase_ = SETTLE_NONE;
    int want_ = 0, got_ = 0, sign_ = 1, pos_ = 2, stock_ = 7, given_ = 4;
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
    void startCenter(uint32_t now);
    void finish(const char* result);
    void resetDefaults();
    void loop();
    bool nudge(String argv[], int argc, String& reply);
    bool stop(String& reply);
    bool clear(String& reply);
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
int main() {
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
        tick(m, 60, false);
        check(m.io.pwm == 0, "center pulse ends without blocking loop");
        tick(m, 94, false);
        check(m.io.pwm == 0, "center motor rests for full configured interval");
        tick(m, 95, false);
        check(m.io.pwm == m.centerSpeed_, "next center pulse uses clock, not delay");
        tick(m, 96, true); tick(m, 97, false);
        check(m.settlePhase_ == GachaModule::SETTLE_CENTER, "one noisy raw Hall sample cannot finish");
        tick(m, 100, true); tick(m, 105, true);
        check(m.settlePhase_ == GachaModule::SETTLE_PAUSE && m.io.pwm == 0, "debounced Hall enters stationary pause");
        tick(m, 5104, true);
        check(m.state_ != GachaModule::IDLE && m.io.pwm == 0, "default five-second pause is not shortened");
        tick(m, 5105, true);
        check(m.state_ == GachaModule::IDLE && m.lastResult_ == "done", "only confirmed Hall completes after pause");
    }
    {
        GachaModule m; clockMs = 0; m.loop(); m.startTurn(GachaModule::JOB_DISPENSE, 1);
        tick(m, 10, true); tick(m, 15, true);
        check(m.settlePhase_ == GachaModule::SETTLE_ROCK_FWD && m.io.pwm > 0, "arrival starts forward rock");
        tick(m, 195, true);
        check(m.settlePhase_ == GachaModule::SETTLE_ROCK_BACK && m.io.pwm < 0, "forward deadline starts reverse rock");
        tick(m, 196, false); tick(m, 201, false); tick(m, 475, false);
        check(m.settlePhase_ == GachaModule::SETTLE_CENTER && m.io.pwm == 0, "reverse deadline starts bounded center");
        tick(m, 515, false); tick(m, 518, true); tick(m, 523, true);
        check(m.settlePhase_ == GachaModule::SETTLE_PAUSE && m.io.pwm == 0, "full phase chain confirms Hall");
        tick(m, 5523, true);
        check(m.state_ == GachaModule::IDLE && m.lastResult_ == "done", "full phase chain completes after five-second hold");
    }
    for (auto phase : {GachaModule::SETTLE_ROCK_FWD, GachaModule::SETTLE_ROCK_BACK,
                       GachaModule::SETTLE_CENTER, GachaModule::SETTLE_PAUSE,
                       GachaModule::SETTLE_NUDGE}) {
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
    }
    {
        GachaModule m; String reply, args[] = {"GNUDGE", "250", "20"}; m.motor_ = nullptr;
        m.nudge(args, 3, reply); check(reply.rfind("ERR no motor", 0) == 0, "nudge refuses missing motor");
    }
    {
        GachaModule m; String reply; removedCfg = 0;
        m.overshootMs_ = m.overshootSpeed_ = m.returnMs_ = m.returnSpeed_ = 1;
        m.centerSpeed_ = m.pauseMs_ = m.fallbackSlotMs_ = 1; m.clear(reply);
        check(m.overshootMs_ == GACHA_OVERSHOOT_MS && m.overshootSpeed_ == GACHA_OVERSHOOT_SPEED,
              "CLEAR restores forward phase defaults");
        check(m.returnMs_ == GACHA_RETURN_MS && m.returnSpeed_ == GACHA_RETURN_SPEED,
              "CLEAR restores reverse phase defaults");
        check(m.centerSpeed_ == GACHA_CENTER_SPEED && m.pauseMs_ == GACHA_PAUSE_MS &&
              m.fallbackSlotMs_ == GACHA_FALLBACK_SLOT_MS, "CLEAR restores center pause and fallback defaults");
        check(m.saves == 1 && m.stock_ == 7 && m.given_ == 4, "CLEAR persists settings without changing stock/counts");
        m.state_ = GachaModule::TURNING; m.clear(reply);
        check(reply == "ERR busy" && removedCfg == 1 && m.saves == 1, "busy CLEAR cannot erase persisted settings");
    }
    check(delayCalls == 0, "all tested command and loop paths are nonblocking");
    return failures ? 1 : 0;
}
