#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "core/SeqScan.h"
#include "core/SDStore.h"

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
//
// A sequence can also CHAIN into another when it ends:
//
//   name: intro
//   next: wave.yaml     # when intro finishes, wave.yaml starts by itself
//
// so a show is built from short files that can each be run and edited on their
// own, instead of one long one. `loop: true` wins over `next` (an endlessly
// looping sequence never reaches its end). Chains are depth-limited, so a file
// that points back at itself stops instead of running forever.
class SequencePlayer {
public:
    static const int MAX_CHAIN = 16;   // a -> b -> c ...; guards a chain loop

    void begin(SDStore* sd, CommandRouter* router);
    bool start(const String& path, String& err);

    // Play a sequence held in MEMORY, with no SD card involved.
    //
    // Why this exists: a browser stops requestAnimationFrame in a hidden tab,
    // so a show driven live from Nong Studio freezes the moment you switch
    // away. The robot has to own its own playback. That was already true of
    // MOVE <file> — but only with a card fitted, and a board without one had
    // no way to run a sequence unattended at all.
    bool startText(const String& yaml, String& err);
    bool hasText() const { return ramYaml_.length() > 0; }
    const String& text() const { return ramYaml_; }
    // The name the text arrived under (FEND's FBEGIN name), so MOVE can
    // refuse when asked for a different file than the one held.
    void setText(const String& yaml, const String& name = "") {
        ramYaml_ = yaml;
        ramName_ = name;
    }
    const String& textName() const { return ramName_; }
    void stop();
    void loop(); // called from CommandRouter::loop() under the router mutex

    bool running() const { return running_; }
    const String& file() const { return file_; }

private:
    SDStore* sd_ = nullptr;
    CommandRouter* router_ = nullptr;
    // A card file through SDStore::readChunk: one short locked read per refill,
    // so an upload or a FILES listing never waits behind a whole show.
    struct SdSource : SeqSource {
        SDStore* sd = nullptr;
        String path;
        int read(uint32_t off, uint8_t* buf, size_t len) override {
            return sd->readChunk(path.c_str(), off, buf, len);
        }
    };
    SdSource sdSrc_;
    SeqTextSource textSrc_;
    String playText_;            // the RAM show being played (startText)
    SeqSource* src_ = nullptr;   // which one is playing
    SeqScan scan_;
    JsonDocument* head_ = nullptr;   // name/loop/next: the header only
    JsonDocument step_;              // the step being played
    bool running_ = false;
    bool loopSeq_ = false;
    String file_;
    uint32_t waitUntil_ = 0;
    uint32_t due_ = 0;   // when the last timed step ENDS on the file's clock
    bool waitBusy_ = false;
    static const uint32_t CATCH_UP_MS = 250;
    void catchUp();
    int chain_ = 0;      // how many files deep this run already is
    String ramYaml_;     // the in-memory sequence, when there is no card
    String ramName_;     // the name it arrived under, for MOVE to check

    bool startAt(const String& path, String& err, int depth);
    bool begin_(const String& name, int depth, String& err);
    void execStep(JsonVariant step);
    void endOfShow();   // the show ended by itself: end a REPEATING track too
};
