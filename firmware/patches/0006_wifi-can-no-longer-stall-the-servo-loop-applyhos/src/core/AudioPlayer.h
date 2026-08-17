#pragma once
#include <Arduino.h>

class AudioGenerator;
class AudioFileSourceSD;
class AudioFileSourceID3;
class AudioOutputI2S;
class SDStore;

// MP3 / WAV playback from the SD card through an I2S amp (MAX98357A).
// Decoding happens in loop(); every SD read is guarded by the SDStore mutex
// so web uploads/downloads on the async task can't corrupt the SPI bus.
class AudioPlayer {
public:
    void begin(SDStore* sd);
    void loop();

    bool play(const String& path); // "/music/track.mp3" or "/music/track.wav"
    void stop();
    void setVolume(uint8_t vol0to100);

    bool playing() const { return gen_ != nullptr; }
    const String& current() const { return current_; }
    uint8_t volume() const { return vol_; }

private:
    SDStore* sd_ = nullptr;
    AudioGenerator* gen_ = nullptr;
    AudioFileSourceSD* file_ = nullptr;
    AudioFileSourceID3* id3_ = nullptr;
    AudioOutputI2S* out_ = nullptr;
    String current_;
    uint8_t vol_ = 70;

    void cleanup();
};
