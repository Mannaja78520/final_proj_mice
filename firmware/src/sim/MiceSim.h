// Test hooks for running the firmware on an emulator (QEMU) with nothing wired.
// Compiled ONLY into the `*_sim` envs (-D MICE_SIM); every other build sees an
// empty file, so no release binary carries a line of this.
//
// QEMU's ESP32 has no ADC, no LEDC/RMT and no way to drive a GPIO from outside,
// so the firmware's own reads and writes of them are redirected here at link
// time (-Wl,--wrap=...), and the test talks to this layer over USB serial:
//
//   ~PIN <gpio> <0|1>     force what digitalRead(gpio) returns (a hall magnet)
//   ~PIN <gpio> -         release it (back to the real pin)
//   ~ADC <gpio> <0-4095>  force what analogRead(gpio) returns (a potentiometer)
//   ~PWM?                 last duty written per LEDC channel / pin, one line
//   ~ENC <n>              what the encoder's pulse counter reads
//   ~PINS?                which pins are forced
//   ~RGB?                 how many times the LED strip was refreshed
//
// Replies start with "~" so they cannot be mistaken for a command reply.
#pragma once
#ifdef MICE_SIM
#include <Arduino.h>
namespace micesim {
// True when `line` was a sim command (reply filled in); false = not ours.
bool handle(const String& line, String& reply);
void rgbShown();   // called where the LED strip would have been refreshed
}
#endif
