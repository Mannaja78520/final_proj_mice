#include "core/AudioStream.h"
#include "core/AudioPlayer.h"        // for MICE_HAS_AUDIO, one definition
#include "core/Log.h"

AudioStream* AudioStream::inst_ = nullptr;

#if MICE_HAS_AUDIO

#include <AudioOutput.h>
#include <WiFiUdp.h>
#include "core/HwConfig.h"
#include <soc/gpio_sig_map.h>
#include <soc/gpio_struct.h>
#include <soc/io_mux_reg.h>

// What the LRC pin REALLY carries, read back from the chip: "lrc" when the
// I2S word clock reaches it, "mclk" when the library's MCLK took GPIO0 over
// (the cracking, 2026-09-28). The fix is proven on the board, not assumed.
static const char* lrcWire() {
    int pin = hw.pins.i2sLrc;
    if (pin < 0 || pin > 33) return "none";
    if (pin == 0 && ((READ_PERI_REG(PERIPHS_IO_MUX_GPIO0_U) >> MCU_SEL_S) & MCU_SEL_V)
                        == FUNC_GPIO0_CLK_OUT1) return "mclk";
    return GPIO.func_out_sel_cfg[pin].func_sel == I2S0O_WS_OUT_IDX ? "lrc" : "other";
}

// One UDP read at a time. 512 samples (1 KB) is under the 1460-byte payload a
// sender can put in one datagram without fragmenting, so a packet is never
// split across two WiFi frames on this side.
static const int READ_SAMPLES = 512;

void AudioStream::begin(AudioOutput* out, std::function<void()> repin) {
    out_ = out;
    repin_ = repin;
    if (out_) inst_ = this;
}

bool AudioStream::start(uint16_t port, uint32_t rate, String& why, bool ws) {
    if (!out_) { why = "no speaker wired on this board"; return false; }
    if (rate < 8000 || rate > 48000) { why = "rate must be 8000-48000"; return false; }
    stop();

    // The ring is allocated BEFORE on_ goes true and freed AFTER it goes
    // false: the WebSocket task only writes while on_ is set.
    cap_ = (rate * (ws ? WS_BUF_MS : BUF_MS)) / 1000;
    buf_ = (int16_t*)malloc(cap_ * sizeof(int16_t));
    if (!buf_) { cap_ = 0; why = "not enough memory for the buffer"; return false; }

    if (!ws) udp_ = new WiFiUDP();
    if (udp_ && !udp_->begin(port)) {
        delete udp_; udp_ = nullptr;
        free(buf_); buf_ = nullptr; cap_ = 0;
        why = "could not listen on port " + String(port);
        return false;
    }
    // The stream is 16-bit MONO, but the output is fed stereo pairs - the same
    // sample twice - so one path serves a mono amp and a stereo one.
    out_->SetRate((int)rate);
    out_->SetBitsPerSample(16);
    out_->SetChannels(2);
    out_->begin();
    if (repin_) repin_();   // begin() just put MCLK on GPIO0 - take it back

    port_ = port; rate_ = rate; ws_ = ws;
    head_ = tail_ = 0;
    oddHave_ = false;
    priming_ = true;
    maxGap_ = under_ = packets_ = dropped_ = trims_ = pads_ = fed_ = 0;
    lastFeed_ = millis();
    on_ = true;
    LOGF(audio, "stream on: %s %u, %u Hz, %u ms buffer", ws ? "websocket" : "udp",
         port, rate, ws ? WS_BUF_MS : BUF_MS);
    return true;
}

void AudioStream::stop() {
    const bool was = on_;
    on_ = false;
    if (was && ws_) delay(2);   // a push() already past its on_ check ends first
    if (udp_) { udp_->stop(); delete udp_; udp_ = nullptr; }
    if (buf_) { free(buf_); buf_ = nullptr; }
    if (was && out_) out_->stop();
    cap_ = head_ = tail_ = 0;
    ws_ = false;
    toneLeft_ = 0;
    toneRun_ = false;
}

uint8_t AudioStream::fillPct() const {
    if (!cap_) return 0;
    uint32_t have = (head_ + cap_ - tail_) % cap_;
    return (uint8_t)((have * 100) / cap_);
}

void AudioStream::put(int16_t v) {
    uint32_t next = (head_ + 1) % cap_;
    if (next == tail_) { dropped_++; return; }   // full: this one is lost
    buf_[head_] = v;
    head_ = next;
}

void AudioStream::wsOpen(uint32_t rate) {
    if (!out_) return;
    wsWant_ = rate ? rate : DEF_RATE;
}

void AudioStream::wsClose() { wsStop_ = true; }

void AudioStream::push(const uint8_t* data, size_t len) {
    if (!on_ || !ws_ || !buf_) return;
    packets_++;
    size_t i = 0;
    if (oddHave_ && len) {                       // finish a sample split by TCP
        put((int16_t)(oddByte_ | (data[0] << 8)));
        oddHave_ = false;
        i = 1;
    }
    for (; i + 1 < len; i += 2) put((int16_t)(data[i] | (data[i + 1] << 8)));
    if (i < len) { oddByte_ = data[i]; oddHave_ = true; }
}

void AudioStream::fill() {
    int16_t tmp[READ_SAMPLES];
    // Bounded per loop: draining an unbounded backlog here would hold the
    // module loop away from the servos for as long as the sender is ahead.
    for (int pass = 0; pass < 4; pass++) {
        int n = udp_->parsePacket();
        if (n <= 0) return;
        packets_++;
        while (n > 0) {
            int want = n > (int)sizeof(tmp) ? (int)sizeof(tmp) : n;
            int got = udp_->read((uint8_t*)tmp, want);
            if (got <= 0) break;
            n -= got;
            for (int i = 0; i < got / 2; i++) put(tmp[i]);
        }
    }
}

void AudioStream::feed() {
    uint32_t have = (head_ - tail_ + cap_) % cap_;
    // Priming, and the underrun rule: hold silence until the buffer is half
    // full again rather than restarting on every dropped packet, which would
    // stutter instead of pausing once.
    if (priming_) {
        if (have < cap_ / 2) return;
        priming_ = false;
        lastFeed_ = millis();
    }
    if (!have) {
        under_++;
        priming_ = true;
        return;
    }
    uint32_t now = millis();
    uint32_t gap = now - lastFeed_;
    if (gap > maxGap_) maxGap_ = gap;      // the number the design is judged on
    lastFeed_ = now;

    // CLOCK DRIFT. The sender clock (PC or phone) and this board's I2S
    // clock never agree exactly, so over minutes the ring creeps full (then
    // whole packets are dropped - a crack) or empty (an underrun - a gap).
    // One sample in 256 skipped or repeated is 0.4 %, far below hearing, and
    // holds the ring near half full for as long as the stream runs.
    const uint32_t hi = cap_ * 3 / 4, lo = cap_ / 4;
    while (have) {
        int16_t s[2] = { buf_[tail_], buf_[tail_] };   // mono into both channels
        if (!out_->ConsumeSample(s)) break;            // DMA full: next loop
        fed_++;
        if ((fed_ & 255) == 0 && have > hi && have > 1) {
            tail_ = (tail_ + 1) % cap_;                // skip one: catch up
            have--;
            trims_++;
        } else if ((fed_ & 255) == 0 && have < lo) {
            pads_++;                                   // play it twice: wait
            continue;
        }
        tail_ = (tail_ + 1) % cap_;
        have--;
    }
}

void AudioStream::loop() {
    // WebSocket requests arrive on the network task; the driver is only ever
    // touched here, on the module loop.
    if (wsStop_) {
        wsStop_ = false;
        if (on_ && ws_) { stop(); LOGF(audio, "stream off: websocket closed"); }
    }
    if (wsWant_) {
        uint32_t r = wsWant_;
        wsWant_ = 0;
        String why;
        if (!start(0, r, why, true)) LOGF(audio, "websocket stream refused: %s", why.c_str());
    }
    if (!on_) return;
    if (udp_) fill();
    if (toneLeft_) {
        // keep the ring about half full, like a well-behaved sender
        while (toneLeft_ && fillPct() < 50) {
            put((int16_t)(8000.0f * sinf(tonePhase_)));
            tonePhase_ += 2.0f * (float)M_PI * 440.0f / (float)rate_;
            if (tonePhase_ > 2.0f * (float)M_PI) tonePhase_ -= 2.0f * (float)M_PI;
            toneLeft_--;
        }
        if (!toneLeft_) priming_ = false;   // play out the tail, no re-prime
    }
    if (toneRun_ && !toneLeft_ && head_ == tail_) {
        toneRun_ = false;
        LOGF(audio, "test tone done: %s", statusJson().c_str());
        stop();
        return;
    }
    feed();
}

String AudioStream::statusJson() const {
    return String("{\"on\":") + (on_ ? "true" : "false")
         + ",\"via\":\"" + (ws_ ? "ws" : "udp") + "\""
         + ",\"lrc\":\"" + (on_ ? lrcWire() : "off") + "\""
         + ",\"port\":" + String(port_)
         + ",\"rate\":" + String(rate_)
         + ",\"buf_ms\":" + String(BUF_MS)
         + ",\"fill\":" + String(fillPct())
         + ",\"packets\":" + String(packets_)
         + ",\"dropped\":" + String(dropped_)
         + ",\"underruns\":" + String(under_)
         + ",\"trims\":" + String(trims_)
         + ",\"pads\":" + String(pads_)
         + ",\"max_gap_ms\":" + String(maxGap_) + "}";
}

#else   // no decoder library in this build: same API, honest answers

void AudioStream::begin(AudioOutput*, std::function<void()>) {}
void AudioStream::loop() {}
void AudioStream::wsOpen(uint32_t) {}
void AudioStream::wsClose() {}
void AudioStream::push(const uint8_t*, size_t) {}
void AudioStream::put(int16_t) {}
void AudioStream::stop() {}
uint8_t AudioStream::fillPct() const { return 0; }
bool AudioStream::start(uint16_t, uint32_t, String& why, bool) {
    why = "this build has no speaker support";
    return false;
}
void AudioStream::fill() {}
void AudioStream::feed() {}
String AudioStream::statusJson() const { return "{\"on\":false}"; }

#endif  // MICE_HAS_AUDIO

// STREAM ON [port] [rate] | STREAM OFF | STREAM?
// Shared by every module type that wires a speaker, like PLAY and VOL.
void AudioStream::streamCmd(String argv[], int argc, String& reply) {
    String a = argc > 1 ? argv[1] : "";
    a.toUpperCase();
    if (argc < 2 || argv[0].endsWith("?") || a == "?") {
        reply = statusJson();
        return;
    }
    if (a == "OFF" || a == "STOP") {
        stop();
        reply = "OK stream off";
        return;
    }
    if (a == "TEST") {
        String why;
        if (!start(0, DEF_RATE, why, true)) { reply = "ERR " + why; return; }
        toneLeft_ = DEF_RATE * 3;
        toneRun_ = true;
        tonePhase_ = 0;
        reply = "OK test tone 440 Hz 3 s through the stream path";
        return;
    }
    if (a != "ON") { reply = "ERR usage: STREAM ON [port] [rate] | OFF | TEST | ?"; return; }
    uint16_t port = argc > 2 ? (uint16_t)argv[2].toInt() : DEF_PORT;
    uint32_t rate = argc > 3 ? (uint32_t)argv[3].toInt() : DEF_RATE;
    String why;
    if (!start(port, rate, why)) { reply = "ERR " + why; return; }
    reply = "OK stream on udp " + String(port) + " " + String(rate) + " Hz mono";
}
