#include "core/AudioPlayer.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include "core/HwConfig.h"
#include "core/AmpTable.h"
#include <config.h>

#if MICE_HAS_AUDIO

#include <AudioFileSourceSD.h>
#include <AudioFileSourceID3.h>
#include <AudioGeneratorMP3.h>
#include <AudioGeneratorWAV.h>
#include <AudioOutputI2S.h>
#include <AudioOutputI2SNoDAC.h>
#include <driver/i2s.h>   // applyPins() below talks to the driver directly

void AudioPlayer::begin(SDStore* sd) {
    sd_ = sd;

    // Select output class based on the board's stored amp kind
    const AmpKind* ak = findAmp(hw.amp);
    if (!ak || strcmp(ak->mode, "none") == 0) {
        out_ = nullptr;  // no speaker
        return;
    }

    // Held as AudioOutputI2S*, not AudioOutput*: SetPinout and
    // SetOutputModeMono are declared on the I2S class only.
    AudioOutputI2S* i2s;
    if (strcmp(ak->mode, "analog") == 0) {
        // TPA3118/TPA3110/PAM8403: one wire, delta-sigma on DOUT. NoDAC still
        // runs the I2S peripheral, so it still claims pins — and its DEFAULTS
        // are bclk 26 / lrc 25 / dout 22, which on a nong are servos 4, 3
        // and 6. Naming them is what keeps a 44 kHz wave off servo lines.
        // BCLK/LRC are still driven; the amp simply has nothing on them.
        i2s = new AudioOutputI2SNoDAC(0);  // port 0
        i2s->SetPinout(hw.pins.i2sBclk, hw.pins.i2sLrc, hw.pins.i2sDout);
    } else if (strcmp(ak->mode, "dac") == 0) {
        // ESP32 built-in 8-bit DAC on GPIO25/26 (stereo)
        i2s = new AudioOutputI2S(0, AudioOutputI2S::INTERNAL_DAC);
        // SetPinout returns false for INTERNAL_DAC — pins are fixed in silicon
    } else {
        // "i2s" mode: MAX98357A, PCM5102A — 3-wire digital I2S
        i2s = new AudioOutputI2S();
        i2s->SetPinout(hw.pins.i2sBclk, hw.pins.i2sLrc, hw.pins.i2sDout);
    }
    dacMode_ = strcmp(ak->mode, "dac") == 0;

    // Force mono if the amp is mono (single speaker / mono amp board)
    if (ak->mono) i2s->SetOutputModeMono(true);

    out_ = i2s;
    setVolume(vol_);
    stream_.begin(out_);
}

// The library CANNOT say "leave this pin alone": AudioOutputI2S keeps its pin
// numbers in uint8_t (AudioOutputI2S.h:73-76), so a -1 arrives as 255. Its
// mclkPin therefore stays at its default 0, and on IDF 4.4 that routes a
// master clock onto GPIO0 — which on a nong carries LRC. So once the library
// has installed the driver, set the pins once more with a real
// I2S_PIN_NO_CHANGE for MCLK. Last writer wins, and this one is last.
void AudioPlayer::applyPins() {
    if (dacMode_) return;   // the built-in DAC's pins are fixed in silicon
    i2s_pin_config_t p = {};
    p.mck_io_num   = I2S_PIN_NO_CHANGE;
    p.bck_io_num   = hw.pins.i2sBclk;
    p.ws_io_num    = hw.pins.i2sLrc;
    p.data_out_num = hw.pins.i2sDout;
    p.data_in_num  = I2S_PIN_NO_CHANGE;
    i2s_set_pin(I2S_NUM_0, &p);
}

// Open the file and start the decoder. The caller owns the SD lock, so this can
// serve both a fresh PLAY and a repeat lap without either taking it twice.
bool AudioPlayer::openTrack_(const String& path) {
    file_ = new AudioFileSourceSD(path.c_str());
    if (!file_->isOpen()) {
        cleanup(); // under the lock: destructor may still touch the SPI bus
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
        return false;
    }
    return true;
}

bool AudioPlayer::play(const String& path, bool loop) {
    stream_.stop();      // one owner of I2S: the newest explicit order wins
    stop();              // also clears loopOn_, so a failed open arms no lap
    if (!sd_ || !sd_->available()) return false;

    sd_->lock();
    const bool ok = openTrack_(path);
    sd_->unlock();
    if (!ok) return false;
    applyPins();   // the decoder's begin() installed the driver — fix MCLK now
    current_ = path;
    loopOn_ = loop;
    loopPath_ = loop ? path : "";
    return true;
}

void AudioPlayer::loop() {
    if (stream_.running()) { stream_.loop(); return; }
    if (!gen_) return;
    // try-lock: this runs while the caller holds the router mutex, so blocking
    // here on a long web file transfer would stall motion/limit updates too.
    // Missing a few decode passes just pauses the audio briefly.
    if (!sd_->tryLock(5)) return;
    bool running = gen_->loop();
    bool relap = false;
    if (!running) {
        gen_->stop();
        cleanup();                            // SDStore's mutex is recursive
        if (loopOn_) {
            // The next lap starts HERE, under the lock already held. Calling
            // play() instead would reach a blocking sd_->lock() inside the one
            // function that must never wait on a web upload.
            relap = openTrack_(loopPath_);
            // One attempt per lap: a deleted file must not spin a failed open
            // on every tick for the rest of the show.
            if (!relap) { loopOn_ = false; loopPath_ = ""; }
        }
    }
    sd_->unlock();
    // ~5-30 ms of silence at the join: the decoder is destroyed and the file
    // reopened. Seamless would need a second source opened in advance.
    if (relap) { applyPins(); current_ = loopPath_; }
}

void AudioPlayer::stop() {
    // STOP means stop, not "stop this lap".
    loopOn_ = false;
    loopPath_ = "";
    if (gen_) {
        sd_->lock();
        gen_->stop();
        sd_->unlock();
    }
    cleanup();
}

void AudioPlayer::cleanup() {
    // ANY of the three, not just the generator. openTrack_ calls this after
    // allocating file_ and before allocating gen_, so a file that will not open
    // used to leak its AudioFileSourceSD — and left the SD handle open with it.
    // One leak per failed PLAY on a board with 300 KB of heap. Found by the
    // model panel 2026-09-10; it predates the repeat feature, which reaches the
    // same branch on a failed lap.
    if (!gen_ && !id3_ && !file_) return;
    sd_->lock();   // deleting the source closes the SD file: SPI traffic
    delete gen_;  gen_ = nullptr;
    delete id3_;  id3_ = nullptr;
    delete file_; file_ = nullptr;
    current_ = "";
    sd_->unlock();
}

bool AudioPlayer::playing() const { return gen_ != nullptr; }
bool AudioPlayer::looping() const { return loopOn_; }
void AudioPlayer::stopIfLooping() { if (loopOn_) stop(); }

#else  // no decoder lib in this env: same API, honest answers

void AudioPlayer::begin(SDStore*) {}
void AudioPlayer::loop() {}
bool AudioPlayer::play(const String&, bool) { return false; }
void AudioPlayer::stop() {}
bool AudioPlayer::playing() const { return false; }
bool AudioPlayer::looping() const { return false; }
void AudioPlayer::stopIfLooping() {}

#endif // MICE_HAS_AUDIO

// ---- below here both builds share the same code ------------------------

void AudioPlayer::setVolume(uint8_t v) {
    if (v > 100) v = 100;
    vol_ = v;
#if MICE_HAS_AUDIO
    if (out_) out_->SetGain(vol_ / 100.0f);
#endif
}

// One parser for every module type that wires a speaker. The module keeps the
// literal `cmd == "PLAY"` (commands.json scope points at its file); the body
// lives here so two modules cannot drift.
void AudioPlayer::playCmd(String argv[], int argc, String& reply) {
#if MICE_HAS_AUDIO
    if (argc < 2) { reply = "ERR usage: PLAY <file> [LOOP]|STOP"; return; }
    String a = argv[1];
    a.toUpperCase();
    if (a == "STOP") {
        stop();
        reply = "OK audio stopped";
        return;
    }
    // Take LOOP off the END before joining. joinFrom swallows every remaining
    // token because a file name may contain spaces — so left alone, the path
    // becomes "/music/song.mp3 LOOP" and the file is simply not found.
    // argc > 2 so a file actually named LOOP still plays.
    bool loop = false;
    int end = argc;
    if (argc > 2) {
        String last = argv[argc - 1];
        last.toUpperCase();
        if (last == "LOOP") { loop = true; end = argc - 1; }
    }
    String path = Util::joinFrom(argv, end, 1);
    if (!path.startsWith("/")) path = "/music/" + path;
    if (!play(path, loop)) {
        reply = "ERR cannot play " + path;
        return;
    }
    reply = String(loop ? "OK looping " : "OK playing ") + path;
#else
    (void)argv; (void)argc;
    reply = "ERR this build has no speaker support";
#endif
}

void AudioPlayer::volCmd(String argv[], int argc, String& reply) {
    if (argc < 2) { reply = "ERR usage: VOL <0-100>"; return; }
    setVolume((uint8_t)constrain(argv[1].toInt(), 0, 100));
    reply = "OK vol=" + String(vol_);
}

// AMP <id>   choose the amplifier kind (stored in NVS, reboot to apply)
// AMP VALID  every amp the firmware knows, as JSON — the page's dropdown
// AMP?       the one this board is set to, as JSON — the page's wiring line
void AudioPlayer::ampCmd(String argv[], int argc, String& reply) {
#if MICE_HAS_AUDIO
    // Same shape as PIN? / PIN VALID: asking is never an error, so a bare AMP
    // answers what is set rather than scolding.
    if (argc < 2 || argv[0].endsWith("?")) {
        const AmpKind* cur = findAmp(hw.amp);
        reply = cur ? ampJson(*cur) : String("ERR no amp set");
        return;
    }
    String a = argv[1];
    a.toUpperCase();
    if (a == "VALID") {
        reply = ampListJson();  // JSON array from AmpTable
        return;
    }
    if (!hw.setAmp(argv[1])) {
        reply = "ERR unknown amp " + argv[1] + " (see AMP VALID)";
        return;
    }
    reply = "OK amp=" + hw.amp + " (reboot to apply)";
#else
    (void)argv; (void)argc;
    reply = "ERR this build has no speaker support";
#endif
}

// STREAM ON|OFF|? - the live source. Starting it stops a file that is playing,
// for the same reason PLAY stops the stream: one output, one owner.
void AudioPlayer::streamCmd(String argv[], int argc, String& reply) {
    String a = argc > 1 ? argv[1] : "";
    a.toUpperCase();
    if (a == "ON") stop();
    stream_.streamCmd(argv, argc, reply);
}
