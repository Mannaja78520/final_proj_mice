#pragma once
#include <Arduino.h>

// LIVE audio from the PC, played as it arrives - the robot as a speaker the
// show can talk through (A24-32). The PC sends raw 16-bit mono PCM in UDP
// datagrams; this fills a ring buffer and feeds I2S from the module loop.
//
// WHY UDP, and why not the web server (Gemini Pro, 2026-09-07, weighed against
// this board's measured behaviour): a TCP retransmission stalls playback, and
// the async web server already stops answering for the length of a track while
// the SD decode holds the SPI mutex. A late packet must be dropped, not
// waited for.
//
// It plays through the output AudioPlayer already built, never its own: the
// pins, the mono flag and the volume are decided in one place, and a second
// owner of I2S_NUM_0 would fight the first.
class AudioOutput;
class WiFiUDP;

class AudioStream {
public:
    // Defaults, overridable per call. 22050 Hz 16-bit mono is 352 kbps, which
    // is what a board also running WiFi, RS485 and ten servos can carry.
    static const uint16_t DEF_PORT = 4210;
    static const uint32_t DEF_RATE = 22050;
    // 200 ms of buffer (8820 bytes at the default rate). Much below this and a
    // WiFi latency spike is audible; much above it, the delay is.
    static const uint16_t BUF_MS = 200;

    void begin(AudioOutput* out);
    void loop();                       // every module loop; cheap while off

    // STREAM ON [port] [rate] | STREAM OFF | STREAM?
    void streamCmd(String argv[], int argc, String& reply);
    bool running() const { return on_; }
    void stop();

    // What the acceptance test reads. Gemini Pro's warning was that servo
    // timers, RS485 and the web server starve the audio task, so the board
    // MEASURES that starvation rather than anyone guessing: the longest gap
    // between two feeds while playing, and how often the buffer ran dry.
    uint32_t maxGapMs() const { return maxGap_; }
    uint32_t underruns() const { return under_; }
    uint32_t packets() const { return packets_; }
    uint16_t port() const { return port_; }
    uint32_t rate() const { return rate_; }
    uint8_t fillPct() const;
    String statusJson() const;

private:
    bool start(uint16_t port, uint32_t rate, String& why);
    void fill();                       // UDP -> ring
    void feed();                       // ring -> I2S

    AudioOutput* out_ = nullptr;
    WiFiUDP* udp_ = nullptr;
    bool on_ = false;
    bool priming_ = true;              // hold until half a buffer has arrived
    uint16_t port_ = DEF_PORT;
    uint32_t rate_ = DEF_RATE;
    int16_t* buf_ = nullptr;           // ring of SAMPLES, not bytes
    uint32_t cap_ = 0;
    uint32_t head_ = 0, tail_ = 0;
    uint32_t lastFeed_ = 0, maxGap_ = 0, under_ = 0, packets_ = 0, dropped_ = 0;
};
