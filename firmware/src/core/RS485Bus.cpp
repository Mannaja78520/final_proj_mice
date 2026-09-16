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
            // 250 ate every FILES listing that crossed a bridge - the head
            // was wiped and only a tail arrived. 2048 still bounds runaway
            // noise with no terminator, but leaves room for real replies.
            if (buf_.length() > 2048) buf_ = "";
            buf_ += c;
        }
    }
    // staggered broadcast replies due? Every queued slot is checked, not just
    // the newest — the newest used to be the ONLY slot and ate older PONGs.
    for (uint8_t i = 0; i < PENDING_N; i++) {
        if (pending_[i].length() && (int32_t)(millis() - pendingAt_[i]) >= 0) {
            send(pending_[i]);
            pending_[i] = "";
        }
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
        // Queue it: first free slot. Full queue? Give up the place of the entry
        // scheduled LAST (it has waited least and nothing is about to fire);
        // signed delta, so a millis() rollover cannot flip the comparison.
        uint8_t slot = PENDING_N;
        for (uint8_t i = 0; i < PENDING_N; i++)
            if (!pending_[i].length()) { slot = i; break; }
        if (slot == PENDING_N) {
            slot = 0;
            for (uint8_t i = 1; i < PENDING_N; i++)
                if ((int32_t)(pendingAt_[i] - pendingAt_[slot]) > 0) slot = i;
        }
        pending_[slot] = "@" + String(id_->id()) + " " + reply;
        pendingAt_[slot] = millis() + (uint32_t)(id_->id() % 24) * 10;
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
// Driver-enable timing, in microseconds, DERIVED from the baud rate rather
// than typed. One byte is 10 bits at 8N1, so at 115200 a byte is 86.8us.
static const uint32_t RS485_BYTE_US = (10UL * 1000000UL) / RS485_BAUD;
static const uint32_t RS485_SETUP_US = RS485_BYTE_US / 2 + 5;
static const uint32_t RS485_HOLD_US = RS485_BYTE_US * 2;

void RS485Bus::send(const String& line) {
    if (sendMtx_) {
        xSemaphoreTake(sendMtx_, portMAX_DELAY);
    } else if (!warnedNoMtx_) {
        warnedNoMtx_ = true;                 // once, not once per frame
        LOGF(sys, "RS485 send has no lock — frames from two tasks can interleave");
    }
    digitalWrite(hw.pins.rs485De, HIGH);
    delayMicroseconds(RS485_SETUP_US);
    Serial2.print(line);
    Serial2.print('\n');
    Serial2.flush(); // the FIFO is empty here - the shift register is not
    // AND THEN WAIT FOR THE SHIFT REGISTER. flush() empties the FIFO; the
    // byte already being clocked out lives beyond it, and dropping the
    // driver enable while it is still going cuts that character in half.
    // The receiver sees a framing error, which arrives as 0x00 - a NUL
    // where a letter should be, which is exactly the corruption measured
    // at the bench on 2026-08-20.
    //
    // 20us was less than a quarter of one byte at 115200 (86.8us), so the
    // margin was not small, it was absent. Derived from the baud rate now,
    // so changing RS485_BAUD cannot leave this behind. Found by the
    // five-model panel, looking at real corrupted replies.
    delayMicroseconds(RS485_HOLD_US);
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
