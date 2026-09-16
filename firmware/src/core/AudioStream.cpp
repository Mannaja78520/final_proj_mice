#include "core/AudioStream.h"
#include "core/AudioPlayer.h"        // for MICE_HAS_AUDIO, one definition
#include "core/Log.h"

#if MICE_HAS_AUDIO

#include <AudioOutput.h>
#include <WiFiUdp.h>

// One UDP read at a time. 512 samples (1 KB) is under the 1460-byte payload a
// sender can put in one datagram without fragmenting, so a packet is never
// split across two WiFi frames on this side.
static const int READ_SAMPLES = 512;

void AudioStream::begin(AudioOutput* out) { out_ = out; }

bool AudioStream::start(uint16_t port, uint32_t rate, String& why) {
    if (!out_) { why = "no speaker wired on this board"; return false; }
    if (rate < 8000 || rate > 48000) { why = "rate must be 8000-48000"; return false; }
    stop();

    cap_ = (rate * BUF_MS) / 1000;
    buf_ = (int16_t*)malloc(cap_ * sizeof(int16_t));
    if (!buf_) { cap_ = 0; why = "not enough memory for the buffer"; return false; }

    udp_ = new WiFiUDP();
    if (!udp_->begin(port)) {
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

    port_ = port; rate_ = rate;
    head_ = tail_ = 0;
    on_ = true; priming_ = true;
    maxGap_ = under_ = packets_ = dropped_ = 0;
    lastFeed_ = millis();
    LOGF(audio, "stream on: udp %u, %u Hz, %u ms buffer", port, rate, BUF_MS);
    return true;
}

void AudioStream::stop() {
    if (udp_) { udp_->stop(); delete udp_; udp_ = nullptr; }
    if (buf_) { free(buf_); buf_ = nullptr; }
    if (on_ && out_) out_->stop();
    cap_ = head_ = tail_ = 0;
    on_ = false;
}

uint8_t AudioStream::fillPct() const {
    if (!cap_) return 0;
    uint32_t have = (head_ - tail_) % cap_;
    return (uint8_t)((have * 100) / cap_);
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
            for (int i = 0; i < got / 2; i++) {
                uint32_t next = (head_ + 1) % cap_;
                if (next == tail_) { dropped_++; return; }   // full: drop the rest
                buf_[head_] = tmp[i];
                head_ = next;
            }
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

    while (have) {
        int16_t s[2] = { buf_[tail_], buf_[tail_] };   // mono into both channels
        if (!out_->ConsumeSample(s)) break;            // DMA full: next loop
        tail_ = (tail_ + 1) % cap_;
        have--;
    }
}

void AudioStream::loop() {
    if (!on_) return;
    fill();
    feed();
}

String AudioStream::statusJson() const {
    return String("{\"on\":") + (on_ ? "true" : "false")
         + ",\"port\":" + String(port_)
         + ",\"rate\":" + String(rate_)
         + ",\"buf_ms\":" + String(BUF_MS)
         + ",\"fill\":" + String(fillPct())
         + ",\"packets\":" + String(packets_)
         + ",\"dropped\":" + String(dropped_)
         + ",\"underruns\":" + String(under_)
         + ",\"max_gap_ms\":" + String(maxGap_) + "}";
}

#else   // no decoder library in this build: same API, honest answers

void AudioStream::begin(AudioOutput*) {}
void AudioStream::loop() {}
void AudioStream::stop() {}
uint8_t AudioStream::fillPct() const { return 0; }
bool AudioStream::start(uint16_t, uint32_t, String& why) {
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
    if (a != "ON") { reply = "ERR usage: STREAM ON [port] [rate] | OFF | ?"; return; }
    uint16_t port = argc > 2 ? (uint16_t)argv[2].toInt() : DEF_PORT;
    uint32_t rate = argc > 3 ? (uint32_t)argv[3].toInt() : DEF_RATE;
    String why;
    if (!start(port, rate, why)) { reply = "ERR " + why; return; }
    reply = "OK stream on udp " + String(port) + " " + String(rate) + " Hz mono";
}
