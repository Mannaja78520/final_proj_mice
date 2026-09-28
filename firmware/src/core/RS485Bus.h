#pragma once
#include <Arduino.h>
#include <functional>

class CommandRouter;
class Identity;

// Half-duplex RS485 on UART2, DE + /RE tied to RS485_DE_PIN.
//
// Wire protocol (ASCII lines, LF terminated):
//   request : #<addr> <command line>      addr = module id, or * for broadcast
//   reply   : @<id> <reply text>
//
// Examples:
//   #3 GOTO 2        -> @3 OK goto 2
//   #3 SET NAME LiftA
//   #* RGB 255 0 0     (broadcast: executed by everyone, nobody replies)
//   #* PING            (broadcast discovery: each module replies @<id> PONG,
//                       staggered into 24 slots of 10 ms to avoid collisions)
//
// Bridging: a PC connected to just ONE module (USB serial or the website
// console) can master the whole bus through it — any line starting with '#'
// is passed to bridge(), which executes locally when addressed to us and
// forwards to the bus otherwise. Replies from other modules ('@' lines) are
// delivered through the onBusLine callback (printed on USB + web console).
class RS485Bus {
public:
    void begin(Identity* id, CommandRouter* router);
    void loop();
    // Thread-safe, and it does NOT wait for the wire: the line is queued and a
    // task of its own clocks it out. Measured 2026-09-21: a 1.3 KB INFO reply
    // sent inline held loop() - and every servo frame - for 116 ms.
    void send(const String& line);
    void drain(uint32_t maxMs);   // wait for queued lines to leave (before a reboot)

    // "#<id> CMD" / "#* CMD" from USB or the web console. Returns the
    // immediate reply; remote replies arrive later via onBusLine.
    String bridge(const String& line, CommandRouter* router);

    // called (from the main loop) for every reply line seen on the bus
    void onBusLine(std::function<void(const String&)> cb) { busLine_ = cb; }

private:
    Identity* id_ = nullptr;
    CommandRouter* router_ = nullptr;
    String buf_;

    // Broadcast replies waiting for their staggered slot. A QUEUE, not one
    // slot: two overlapping scans used to overwrite each other's PONG and the
    // hub silently lost boards. Four is plenty — slots fire every 10 ms; when
    // full, the newest entry gives its place to the newcomer.
    static const uint8_t PENDING_N = 4;
    String pending_[PENDING_N];
    uint32_t pendingAt_[PENDING_N] = {0};
    std::function<void(const String&)> busLine_;
    SemaphoreHandle_t sendMtx_ = nullptr;
    bool warnedNoMtx_ = false;   // say it once if the lock is missing
    QueueHandle_t txq_ = nullptr;   // String* lines waiting for the wire
    bool warnedFull_ = false;
    volatile bool sending_ = false;   // a line was taken off the queue and is going out

    void handleLine(String line);
    void sendNow(const String& line);   // the wire itself; blocks until sent
    static void txTask(void* self);
};
