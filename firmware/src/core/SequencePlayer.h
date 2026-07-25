#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

class CommandRouter;
class SDStore;

// Plays a YAML movement sequence from the SD card (/moves/*.yaml).
// Each step is translated into a normal command line and pushed through
// CommandRouter, so anything you can type over RS485/WiFi works in a file:
//
//   name: demo
//   loop: false
//   steps:
//     - home: 1
//     - goto: 2          # waits until the lift arrives
//     - wait: 1000       # ms
//     - rgb: 255 0 0
//     - effect: rainbow
//     - play: /music/intro.mp3
//     - vol: 80
//     - pose: "90 45 120 90 90 135 60 90 T 800"  # nong: 8 joints, waits
//     - joint: "L_EL_P 120 T 500"                # nong: one joint, waits
//     - speed: 150                               # deg/s (nong) / pwm (lift)
//     - relax: 1 / attach: 1                     # nong: servos limp / powered
//     - cmd: "RGB BRIGHT 200"   # raw escape hatch
class SequencePlayer {
public:
    void begin(SDStore* sd, CommandRouter* router);
    bool start(const String& path, String& err);
    void stop();
    void loop(); // called from CommandRouter::loop() under the router mutex

    bool running() const { return running_; }
    const String& file() const { return file_; }

private:
    SDStore* sd_ = nullptr;
    CommandRouter* router_ = nullptr;
    JsonDocument* doc_ = nullptr;
    bool running_ = false;
    bool loopSeq_ = false;
    size_t idx_ = 0;
    String file_;
    uint32_t waitUntil_ = 0;
    bool waitBusy_ = false;

    void execStep(JsonVariant step);
};
