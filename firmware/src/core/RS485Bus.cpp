#include "core/RS485Bus.h"
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
        // discovery: stagger replies by id so they don't collide on the bus
        pendingReply_ = "@" + String(id_->id()) + " " + reply;
        pendingAt_ = millis() + (uint32_t)id_->id() * 20;
    }
}

void RS485Bus::send(const String& line) {
    if (sendMtx_) xSemaphoreTake(sendMtx_, portMAX_DELAY);
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
