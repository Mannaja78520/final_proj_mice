#pragma once
#include <Arduino.h>
#include "core/AudioStream.h"

// MP3 / WAV playback from the SD card through an amp.
// The amp kind is chosen per board from config/amps.json (stored in NVS):
//   i2s     -> AudioOutputI2S (3-wire digital I2S, e.g. MAX98357A)
//   analog  -> AudioOutputI2SNoDAC (1-wire delta-sigma, e.g. TPA3110/PAM8403)
//   dac     -> AudioOutputI2S with INTERNAL_DAC (ESP32 built-in DAC on GPIO25/26)
//   none    -> no speaker; PLAY answers "no speaker wired"
// Shared by every module type that wires a speaker (lift, and nong since
// A7-9). The decoder library is a per-env dependency: when an env does not
// carry ESP8266Audio the class still compiles as a stub that answers
// "cannot play" — so adding a speaker to a type is ONE lib_deps line in
// platformio.ini, never a code edit.
#if __has_include(<AudioOutputI2S.h>)
#define MICE_HAS_AUDIO 1
#else
#define MICE_HAS_AUDIO 0
#endif

class AudioGenerator;
class AudioFileSourceSD;
class AudioFileSourceID3;
class AudioOutput;
class AudioOutputI2S;
class AudioOutputI2SNoDAC;
class SDStore;

class AudioPlayer {
public:
    void begin(SDStore* sd);
    void loop();

    void playCmd(String argv[], int argc, String& reply); // PLAY <file>|STOP
    void volCmd(String argv[], int argc, String& reply);  // VOL <0-100>
    void ampCmd(String argv[], int argc, String& reply);  // AMP <id>|VALID / AMP?
    // STREAM ON|OFF|? - live audio from the PC over UDP (A24-32). It plays
    // through THIS object's output, so the two sources cannot both hold I2S:
    // starting one stops the other, and each says which it did.
    void streamCmd(String argv[], int argc, String& reply);
    const AudioStream& stream() const { return stream_; }
    void setVolume(uint8_t vol0to100);   // also used to apply the saved level

    // Public because STOP means quiet, not only still: a module's own STOP
    // and MOVE STOP both call it through Module::silence().
    void stop();

    bool playing() const;
    bool looping() const;
    // End a track that was told to repeat, and leave a one-shot alone. A show
    // that runs off its last step does NOT silence audio (that is deliberate:
    // a long track may outlive a short show), but a repeating one would then
    // play forever with nothing left to stop it.
    void stopIfLooping();
    const String& current() const { return current_; }
    uint8_t volume() const { return vol_; }

private:
    bool play(const String& path, bool loop = false);  // "/music/track.mp3" or .wav

    String current_;
    uint8_t vol_ = 70;
    AudioStream stream_;

#if MICE_HAS_AUDIO
    // Decoding happens in loop(); every SD read is guarded by the SDStore
    // mutex so web uploads/downloads on the async task can't corrupt SPI.
    SDStore* sd_ = nullptr;
    AudioGenerator* gen_ = nullptr;
    AudioFileSourceSD* file_ = nullptr;
    AudioFileSourceID3* id3_ = nullptr;
    AudioOutput* out_ = nullptr;  // base class; actual type chosen in begin()
    bool dacMode_ = false;        // built-in DAC: its pins cannot be moved
    // The repeat is remembered HERE and not in current_, which cleanup() clears
    // the moment a track ends — by the time anyone knows it finished, the path
    // would already be gone.
    bool loopOn_ = false;
    String loopPath_;
    void cleanup();
    void applyPins();             // re-pin after the driver is installed
    // Opens and starts a track. The SD lock must ALREADY be held: a lap restart
    // happens inside the lock loop() took, and taking it again there would mean
    // a blocking lock in the one function that deliberately only try-locks.
    bool openTrack_(const String& path);
#endif
};
