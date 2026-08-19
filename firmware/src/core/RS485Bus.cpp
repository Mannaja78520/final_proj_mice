#include "core/RS485Bus.h"
#include "core/Log.h"
#include "core/CommandRouter.h"
#include "core/Identity.h"
#include "core/HwConfig.h"
#include <config.h>

void RS485Bus::begin(Identity* id, CommandRouter* router) {
    id_ = id;
    router_ = router;
    sendMtx_ = xSemaphoreCreateMutex(); // web (async task) and loop both send
    pinMode(hw.pins.rs485De, OUTPUT);
    digitalWrite(hw.pins.rs485De, LOW); // listen
    Serial2.begin(RS485_BAUD, SERIAL_8N1, hw.pins.rs485Rx, hw.pins.rs485Tx);
    buf_.reserve(64);
}

void RS485Bus::loop() {
    while (Serial2.available()) {
        char c = (char)Serial2.read();
        if (c == '\n') {
            if (buf_.length()) handleLine(buf_);
            buf_ = "";
        } else if (c != '\r') {
            if (buf_.length() > 250) buf_ = ""; // garbage / missed terminator
            buf_ += c;
        }
    }
    // staggered broadcast reply due?
    if (pendingReply_.length() && (int32_t)(millis() - pendingAt_) >= 0) {
        send(pendingReply_);
        pendingReply_ = "";
    }
}

void RS485Bus::handleLine(String line) {
    line.trim();
    if (line.startsWith("@")) {
        // a reply from another module — someone (possibly the PC bridged
        // through us) asked for it; surface it on USB / the web console
        if (busLine_) busLine_(line);
        return;
    }
    if (!line.startsWith("#")) return;

    int sp = line.indexOf(' ');
    if (sp < 2) return;
    String addr = line.substring(1, sp);
    String payload = line.substring(sp + 1);
    payload.trim();
    if (!payload.length()) return;

    bool broadcast = (addr == "*" || addr == "0");
    if (!broadcast && addr.toInt() != id_->id()) return; // not for us

    String reply = router_->handle(payload);

    if (!broadcast) {
        send("@" + String(id_->id()) + " " + reply);
    } else if (payload.startsWith("PING") || payload.startsWith("ping")) {
        // Discovery: stagger replies so they do not collide on the bus. The
        // gap has to beat the time a line takes to travel - a PONG is about
        // 30 characters, which is 2.6 ms at 115200 - and 10 ms is comfortably
        // clear of that.
        //
        // The SLOT is what changed on 2026-08-19. It used to be id x 20 ms,
        // which is fine for id 3 and means 5.1 SECONDS for id 247. The hub
        // listened for 0.8 s, so every board above id 40 was invisible on a
        // real bus - measured with a nong on id 67 answering at 1344 ms, and
        // impossible to see against a fake that answers instantly.
        //
        // Now the delay is bounded: 24 slots of 10 ms, so every board has
        // answered within 240 ms whatever its id. Two boards can share a slot
        // (ids 24 apart); that is what the addressed follow-up is for, and a
        // collision that loses one answer is recoverable where a five second
        // wait is simply never made.
        pendingReply_ = "@" + String(id_->id()) + " " + reply;
        pendingAt_ = millis() + (uint32_t)(id_->id() % 24) * 10;
    }
}

// The ONLY place anything is written to Serial2. That matters: the line and its
// terminator are two calls, and on the USB port that exact shape was a real bug
// (a WiFi event landing between Serial.println's two writes — see core/Log.h).
// Here it is safe, for reasons that are worth stating rather than rediscovering:
//
//   * one writer, this function;
//   * serialised by sendMtx_, created in begin() because the async web task and
//     loop() both send;
//   * and the driver is held HIGH across both writes, dropped only after
//     flush(), so the whole frame is one transmission on the wire.
//
// The lock is the load-bearing part. Without it two tasks can interleave halves
// of two frames onto a bus every module is listening to, and the modules would
// act on the wreckage. So a missing mutex is reported instead of silently
// skipping the lock — it can only happen if begin() was never reached or the
// mutex could not be allocated, and both mean this board should not be trusted
// to talk on the bus.
void RS485Bus::send(const String& line) {
    if (sendMtx_) {
        xSemaphoreTake(sendMtx_, portMAX_DELAY);
    } else if (!warnedNoMtx_) {
        warnedNoMtx_ = true;                 // once, not once per frame
        LOGF(sys, "RS485 send has no lock — frames from two tasks can interleave");
    }
    digitalWrite(hw.pins.rs485De, HIGH);
    delayMicroseconds(20);
    Serial2.print(line);
    Serial2.print('\n');
    Serial2.flush(); // wait until the last byte left the UART before releasing the bus
    delayMicroseconds(20);
    digitalWrite(hw.pins.rs485De, LOW);
    if (sendMtx_) xSemaphoreGive(sendMtx_);
}

// A '#' line typed on USB serial or the website console: the PC uses this
// module as a gateway to the whole bus.
String RS485Bus::bridge(const String& raw, CommandRouter* router) {
    String line = raw;
    line.trim();
    int sp = line.indexOf(' ');
    if (sp < 2) return "ERR bad frame (use #<id> CMD or #* CMD)";
    String addr = line.substring(1, sp);
    String payload = line.substring(sp + 1);
    payload.trim();
    if (!payload.length()) return "ERR empty command";

    bool broadcast = (addr == "*" || addr == "0");
    if (!broadcast && addr.toInt() == id_->id()) {
        // addressed to the module the PC is plugged into: answer directly
        return "@" + String(id_->id()) + " " + router->handle(payload);
    }
    send(line); // put it on the bus for the others
    if (broadcast) {
        // we execute broadcasts too; other modules' PING replies stream in later
        return "@" + String(id_->id()) + " " + router->handle(payload);
    }
    return "-> sent, module " + addr + "'s reply appears when it answers";
}
