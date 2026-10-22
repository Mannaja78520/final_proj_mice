#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <motor.h>
#include <config.h>
#include "modules/Module.h"
#include "modules/gacha/GachaMath.h"

class SDStore;

// Prize dispenser (gachapon). One motor turns a holder with pockets; one hall
// sensor at the RECEIVE position sees a magnet under every pocket. The item
// comes in from the back into the pocket at the sensor and does not fall
// until the holder turns `drop` pockets on (user 2026-10-22).
//
// Motion is counted in magnet ARRIVALS, never in time: turning N pockets is
// N * passesPerSlot arrivals. No arrival within `timeout` = jammed, motor off.
//
// Everything a person sets (pockets, magnets, drop, speed, event, stock, item
// type) is stored in NVS namespace "gacha", so a board keeps its event over a
// reboot. The hub's gacha app is the brain for several machines (types,
// fallback, rules per person); the board only counts, turns and refuses.
// Commands: GSPIN GHOME GDISPENSE STOP G? GSTOCK GEVENT GITEM GCFG GCFG? GCOUNT
// (config/commands.json, firmware/COMMANDS.md).
class GachaModule : public Module {
public:
    explicit GachaModule(SDStore* sd) : sd_(sd) {}
    const char* type() const override { return "gacha"; }

    void begin() override;
    void loop() override;
    bool handleCommand(String argv[], int argc, String& reply) override;
    void addCapabilities(JsonArray caps) override;
    void status(JsonObject o) override;
    bool busy() override { return state_ != IDLE; }

private:
    enum State { IDLE, TURNING, HOMING };
    enum Job { JOB_SPIN, JOB_HOME, JOB_DISPENSE };

    SDStore* sd_;
    Controller* motor_ = nullptr;
    gachamath::HallCounter hall_;

    // settings (GCFG, NVS)
    int magnets_ = GACHA_MAGNETS, slots_ = GACHA_SLOTS, drop_ = GACHA_DROP_SLOTS;
    int speed_ = GACHA_SPEED, dir_ = 1;
    int timeoutMs_ = GACHA_SLOT_TIMEOUT_MS, debounceMs_ = GACHA_DEBOUNCE_MS;
    int settleMs_ = GACHA_SETTLE_MS;
    bool activeLow_ = GACHA_HALL_ACTIVE_LOW;
    String item_;                  // item type this machine holds ("" = not set)

    // event + stock (NVS)
    String event_;
    bool open_ = true;             // a fresh board dispenses: bench tests need no setup
    int stock_ = -1;               // balls left, -1 = not counted
    int loaded_ = 0;               // put in this event (set + every add)
    int given_ = 0, forced_ = 0;   // dispensed this event; forced ones are in given_ too
    uint32_t total_ = 0, hits_ = 0;  // lifetime dispenses / magnet arrivals

    // motion
    State state_ = IDLE;
    Job job_ = JOB_SPIN;
    int want_ = 0, got_ = 0, sign_ = 1;
    int pos_ = 0;                  // pocket at the sensor, counted from boot / GHOME
    uint32_t lastPassMs_ = 0, settleUntil_ = 0, startMs_ = 0;

    // last dispense, for apps polling G?
    uint32_t seq_ = 0;
    String lastWho_, lastResult_ = "none";
    bool lastForced_ = false;
    uint32_t lastMs_ = 0;

    bool hallActive() const;
    int perSlot() const { return gachamath::passesPerSlot(magnets_, slots_); }
    void startTurn(Job job, int passes);
    void finish(const char* result);
    void motorOff();
    void makeMotor();
    void load();
    void saveCfg();
    void saveCounts();
    String cfgJson() const;
    String statusJson();
};
