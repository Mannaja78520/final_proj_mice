#include "core/AudioPlayer.h"
#include "core/SDStore.h"
#include "core/HwConfig.h"
#include <config.h>

#include <AudioFileSourceSD.h>
#include <AudioFileSourceID3.h>
#include <AudioGeneratorMP3.h>
#include <AudioGeneratorWAV.h>
#include <AudioOutputI2S.h>

void AudioPlayer::begin(SDStore* sd) {
    sd_ = sd;
    out_ = new AudioOutputI2S();
    out_->SetPinout(hw.pins.i2sBclk, hw.pins.i2sLrc, hw.pins.i2sDout);
    setVolume(vol_);
}

void AudioPlayer::setVolume(uint8_t v) {
    if (v > 100) v = 100;
    vol_ = v;
    if (out_) out_->SetGain(vol_ / 100.0f);
}

bool AudioPlayer::play(const String& path) {
    stop();
    if (!sd_ || !sd_->available()) return false;

    sd_->lock();
    file_ = new AudioFileSourceSD(path.c_str());
    if (!file_->isOpen()) {
        cleanup(); // under the lock: destructor may still touch the SPI bus
        sd_->unlock();
        return false;
    }
    String lower = path;
    lower.toLowerCase();
    bool ok;
    if (lower.endsWith(".wav")) {
        gen_ = new AudioGeneratorWAV();
        ok = gen_->begin(file_, out_);
    } else {
        id3_ = new AudioFileSourceID3(file_); // skips ID3 tags at file start
        gen_ = new AudioGeneratorMP3();
        ok = gen_->begin(id3_, out_);
    }
    if (!ok) {
        cleanup(); // under the lock: closes the still-open SD file
        sd_->unlock();
        return false;
    }
    sd_->unlock();
    current_ = path;
    return true;
}

void AudioPlayer::loop() {
    if (!gen_) return;
    // try-lock: this runs while the caller holds the router mutex, so blocking
    // here on a long web file transfer would stall motion/limit updates too.
    // Missing a few decode passes just pauses the audio briefly.
    if (!sd_->tryLock(5)) return;
    bool running = gen_->loop();
    if (!running) gen_->stop();
    sd_->unlock();
    if (!running) cleanup();
}

void AudioPlayer::stop() {
    if (gen_) {
        sd_->lock();
        gen_->stop();
        sd_->unlock();
    }
    cleanup();
}

void AudioPlayer::cleanup() {
    delete gen_;  gen_ = nullptr;
    delete id3_;  id3_ = nullptr;
    delete file_; file_ = nullptr;
    current_ = "";
}
