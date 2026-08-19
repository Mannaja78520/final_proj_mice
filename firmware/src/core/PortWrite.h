#pragma once
// One line reaches the USB port in ONE call. The whole reason, in one place.
//
// Two different things go out of this port and both must arrive whole:
//
//   a REPLY   OK / ERR / PONG / @<id> ...  — main.cpp:emitLine
//   a LOG     [wifi] disconnected, ...     — core/Log.h
//
// They are written by different tasks. loop() answers commands; the WiFi event
// task and the async web server raise logs whenever they feel like it. If a
// line reaches the UART as two calls, the other task's line can land in the
// gap, and the two arrive spliced together:
//
//     OK joining lift-test now (WIFI for progress)[wifi] disconnected, reason=8
//
// The PC then reads that whole thing as the reply. Seen on the bench; it is why
// Serial.println is banned here — println is print(text) followed by a separate
// print of the terminator, and the gap between them is the bug.
//
// Serial.write(buf, len) hands the whole line to the UART queue under one lock,
// so no other task can get inside it. That is not folklore — it is in the core
// this firmware compiles against:
//
//   HardwareSerial::write(buf, size)  ->  uartWriteBuf(_uart, buffer, size)
//        cores/esp32/HardwareSerial.cpp:470
//   uartWriteBuf()  ->  UART_MUTEX_LOCK(); uart_write_bytes(...); UART_MUTEX_UNLOCK();
//        cores/esp32/esp32-hal-uart.c:679
//
// One call, one lock, whole buffer. println() is TWO of those calls with the
// lock released in between, which is the gap the bug lived in.
//
// Both paths used to implement this rule separately, each with its own comment
// explaining it. Two copies of a rule is one copy that can be lost: someone
// fixes a warning in one and the other keeps the hazard. So there is one
// function, and check_logging asserts nothing else writes to the port.
#include <Arduino.h>
#include <stddef.h>

namespace mice {

inline void writeOnce(const char* buf, size_t len) {
    if (buf && len) Serial.write(reinterpret_cast<const uint8_t*>(buf), len);
}

}  // namespace mice
