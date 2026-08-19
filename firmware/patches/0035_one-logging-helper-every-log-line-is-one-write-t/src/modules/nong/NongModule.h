#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <config.h>
#include "modules/Module.h"
#include "core/HwConfig.h"

class SDStore;

// Nong humanoid module: upper body with two arms, no fingers.
// HARDWARE: 8 MG90S servos + the microSD card (for /moves sequences) — that
// is all. No encoder, no RGB strip, no speaker (those are lift hardware; a
// board is one type at a time, so nong reuses their pins for servos).
// Each arm has a universal joint in the shoulder and a universal joint in
// the elbow, every universal joint built from 2 MG90S servos -> 8 joints:
//
//   idx  name    axis                      idx  name    axis
//   1    L_SH_P  left shoulder pitch       5    R_SH_P  right shoulder pitch
//   2    L_SH_R  left shoulder roll        6    R_SH_R  right shoulder roll
//   3    L_EL_P  left elbow pitch          7    R_EL_P  right elbow pitch
//   4    L_EL_R  left elbow roll           8    R_EL_R  right elbow roll
//
// Angles (POSE/JOINT, neutral 90, the [min,max] limits) are JOINT degrees —
// the physical joint angle. Each servo drives its joint through a reduction
// gear (pinion on the servo, gear on the joint, default 12:13), so the joint
// turns pinion/gear of the servo; writeServos() converts joint->servo, and
// the servo uses its full 0..180 while the joint stays in its smaller safe
// range (a 2-servo universal joint can't reach 0..180 — default limit
// 30..150 JOINT deg). Moves are interpolated with a cosine ease over a
// duration T; without T the duration comes from the speed (deg/s) and the
// largest joint delta — the same formula the pose editor uses.
//
// ONE ESP32 drives all 8 joints by default (the default servo_pins fit one
// board with no strap pins). Only if one board is not enough (wiring/power)
// split the humanoid over two: give every board the SAME firmware,
// SET TYPE nong, wire them to the same RS485 bus, and set servo_pins[i] to
// -1 for joints wired to the other board. On the LEADER (the board with the
// SD card that plays the sequences) set link: 1 — every
// POSE/JOINT/HOME/RELAX/ATTACH/SPEED it executes is then repeated on the
// bus with the resolved duration, so both boards move in sync (seamless:
// one sequence, one command, the whole humanoid follows).
// SELECT the partner with peer: <id> — the leader then addresses exactly
// that module ("#<id> ..."), so other robots on the same bus are never
// disturbed. peer: 0 (default) = broadcast "#* ..." to everyone.
// Followers keep link: 0. Never set link on two boards (command storm).
//
// Move times are physically honest: any commanded T shorter than
// largest-joint-delta / max_dps (the servo's real speed limit) is raised to
// that minimum, so a pose is always actually reached before the next step.
// The reply reports the effective T.
//
// Commands (via CommandRouter — identical over RS485 / web / USB):
//   POSE <a1..a8> [T <ms>]      all 8 joints (deg 0-180, '-' keeps a joint)
//   POSE?                       -> "90.0 90.0 ..." current angles
//   JOINT <1-8|name> <deg> [T <ms>]
//   HOME [T <ms>] | ZERO        -> move to the zero/home pose
//   SETZERO                     -> calibrate: current pose becomes home (90 deg)
//   RELAX | ATTACH              servos limp (pose by hand) / powered again
//   SPEED <deg_per_s> | SPEED?
//   TIME? [a1..a8]              -> estimated ms for that move (editor helper)
//   LIMIT?                      -> per-joint min/max + gear + pulse (JSON)
//   LIMIT <1-8|name> <min> <max>-> set a joint's travel limits
//   GEAR [<1-8|name|ALL> <pinion> <gear>]   -> per-joint reduction
//   PULSE [<1-8|name|ALL> <minUs> <maxUs> [maxDps]] -> per-joint servo pulse
//   RANGE [<1-8|name|ALL> <deg>]            -> per-joint SERVO travel
//                                              (180 normal, 270 wide-angle)
//   RATE  [<1-8|name|ALL> <hz>]             -> per-joint SERVO frame rate
//                                              (50 normal, 330 for PDI-1181MG)
//   SERVO [<1-8|name|ALL> <type>]           -> apply a servo preset
//                 (mg90s | pdi1181mg | tiankong35 | generic180 | generic270)
// All of these apply immediately and are saved to /data/nong_cal.yaml on the
// SD card, so they survive a reboot. Every joint can use a DIFFERENT servo.
//
// SERVO TRAVEL vs JOINT LIMITS — two different things, never mix them up:
//   servo_range (RANGE) = how far the SERVO turns end to end, a property of
//     the servo you bought: 180 for an MG90S, 270 for a wide-angle one.
//   joint_min/joint_max (LIMIT) = how far the JOINT may turn, a property of
//     your mechanism.
// Poses, sequences and neutral 90 are always JOINT degrees, so fitting a 270
// servo is a one-number change (RANGE 1 270) — every saved move keeps working
// and the arm does not move at home, because joint 90 sits at the middle of
// the travel whatever the travel is.
class NongModule : public Module {
public:
    static const int N = 10; // logical joints: 8 arm (2 arms x universal
                             // shoulder+elbow) + WAIST (body yaw) + SHRUG

    // servo pins default to the web-configured NVS map (hw); module.yaml
    // servo_pins (applySettings, called after this) can still override them
    explicit NongModule(SDStore* sd) : sd_(sd) {
        for (int i = 0; i < N; i++) pins_[i] = hw.pins.servo[i];
    }
    const char* type() const override { return "nong"; }

    void begin() override;
    void loop() override;
    bool handleCommand(String argv[], int argc, String& reply) override;
    void addCapabilities(JsonArray caps) override;
    void status(JsonObject o) override;
    bool busy() override;
    void applySettings(JsonVariant s) override;

    // Calibration is stored TWICE, on purpose:
    //   * NVS on the chip  — always, so a board with NO SD card still keeps
    //     its gear, limits, pulses, travel, rate and zero across a power cycle.
    //     This is the one that always exists, so it is applied last and wins.
    //   * /data/nong_cal.yaml on the card — when a card is fitted, as a
    //     readable copy you can inspect, back up or move to another board.
    // Both are written by every LIMIT/GEAR/PULSE/RANGE/RATE/SERVO/SETZERO.
    struct CalBlob {
        uint16_t magic;              // 'NC' — anything else is ignored
        uint16_t version;
        uint16_t joints;             // how many joints this blob holds
        float minDeg[N], maxDeg[N], trim[N], neutral[N];
        int16_t gearPinion[N], gearGear[N], pulseMin[N], pulseMax[N];
        float maxDps[N], servoRange[N];
        int16_t frameHz[N];
        uint8_t invert[N];
    };
    static const uint16_t CAL_MAGIC = 0x4E43;   // 'N','C'
    static const uint16_t CAL_VERSION = 1;

private:
    SDStore* sd_;
    Servo servos_[N];

    // settings (see /data/module.yaml and the CFG command).
    // NOTE: the arrays MUST have full defaults — without a module.yaml the
    // values are otherwise zero, which clamps every joint to 0 deg.
    int pins_[N] = NONG_SERVO_PINS;  // pin per logical joint, -1 = other board
    float minDeg_[N] = NONG_MIN_DEF;                         // per-joint JOINT limits
    float maxDeg_[N] = NONG_MAX_DEF;
    float trim_[N] = NONG_TRIM_DEF;                          // added at the servo
    bool invert_[N] = NONG_INVERT_DEF;
    float neutral_[N] = NONG_NEUTRAL_DEF;                    // HOME pose
    // PER-JOINT servo + gear: every joint can use a different servo and a
    // different reduction (as built: shoulders PDI-1181MG 15:18, elbows
    // MG90S 12:13). All settable at runtime (GEAR / PULSE / SERVO commands).
    int gearPinion_[N] = NONG_GEAR_PINION_DEF; // pinion teeth (on the servo)
    int gearGear_[N] = NONG_GEAR_GEAR_DEF;     // gear teeth (on the joint)
    int pulseMin_[N] = NONG_PULSE_MIN_DEF;     // servo pulse range (us)
    int pulseMax_[N] = NONG_PULSE_MAX_DEF;
    float maxDps_[N] = NONG_MAX_DPS_DEF;       // per-joint physical speed limit
    // servo TRAVEL in deg (180 normal, 270 wide-angle). The servo's own span
    // from pulseMin to pulseMax — not the joint's range.
    float servoRange_[N] = NONG_SERVO_RANGE_DEF;
    // servo FRAME RATE in Hz (50 normal, 330 for the PDI-1181MG digital servo).
    // Set at attach time; a wrong rate can make a digital servo cut torque.
    int frameHz_[N] = NONG_FRAME_HZ_DEF;
    float speedDps_ = NONG_DEFAULT_SPEED_DPS;  // show speed (all joints)
    bool link_ = false;              // leader: repeat pose cmds on RS485
    int peer_ = 0;                   // partner module id (0 = broadcast to all)

    // motion state (logical angles are tracked for all 8 joints, including
    // the ones on other boards, so the leader always knows the full pose)
    float cur_[N], from_[N], target_[N];
    uint32_t moveStart_ = 0, moveDur_ = 0, lastTick_ = 0;
    bool moving_ = false;
    bool attached_ = false;
    bool calDirty_ = false;          // settings changed, YAML not written yet
    uint32_t calDirtyAt_ = 0;        // when — the write happens once it goes quiet

    int jointIndex(const String& token) const;     // "3"|"L_EL_P" -> 0-based, -1 bad
    float clampJoint(int i, float deg) const;
    float maxDelta(const float tgt[N]) const;       // largest joint change (deg)
    float slowestMaxDps() const;                    // slowest joint's limit
    uint32_t durationFor(const float tgt[N]) const; // ms from speed setting
    uint32_t minDuration(const float tgt[N]) const; // physical floor from max_dps
    void startMove(const float tgt[N], uint32_t ms);
    void writeServos();
    // Re-attach after a pulse-range / frame-rate change. j < 0 = every joint,
    // otherwise ONLY that joint: each attach() claims an ESP32 LEDC channel,
    // so re-attaching all 10 servos for a change to one of them burns through
    // the chip's channels and crashes the board (Nong Studio's "update" sends
    // 10 x PULSE + 10 x RATE in a burst — that used to be 200 attach calls).
    void reattach(int j = -1);
    void forward(const String& cmdline); // link: 1 -> "#<peer> ..." or "#* ..."
    void loadCal();                      // /data/nong_cal.yaml -> settings
    void saveCal();                      // persist to NVS + SD (writes now)
    void saveCalNvs();                   // the copy that works with no SD card
    bool loadCalNvs();                   // true if a stored blob was applied
    void clearCal();                     // forget both copies (CAL CLEAR)
    // Ask for a save instead of doing one per command: Studio's "update" sends
    // ~50 commands back to back and each used to rewrite the whole YAML.
    void saveCalSoon();
    void reclamp();                      // keep neutral/current inside limits
};
