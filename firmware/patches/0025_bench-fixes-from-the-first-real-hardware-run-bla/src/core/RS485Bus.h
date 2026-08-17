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
//   #* PING            (broadcast discovery: each module replies @<id> PONG...
//                       staggered by id*20ms to avoid bus collisions)
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
    void send(const String& line); // thread-safe (send mutex)

    // "#<id> CMD" / "#* CMD" from USB or the web console. Returns the
    // immediate reply; remote replies arrive later via onBusLine.
    String bridge(const String& line, CommandRouter* router);

    // called (from the main loop) for every reply line seen on the bus
    void onBusLine(std::function<void(const String&)> cb) { busLine_ = cb; }

private:
    Identity* id_ = nullptr;
    CommandRouter* router_ = nullptr;
    String buf_;
    String pendingReply_;
    uint32_t pendingAt_ = 0;
    std::function<void(const String&)> busLine_;
    SemaphoreHandle_t sendMtx_ = nullptr;

    void handleLine(String line);
};
