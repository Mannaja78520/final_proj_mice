#pragma once
#include <Arduino.h>

// Is the board keeping up? One cheap timer around loop() and the servo frame,
// read with PERF? (asked 2026-09-21: low loop time, realtime, no lag, no
// restarts). Every figure is a window since the last PERF?, except heap_min,
// boots and reset, which are since power-on / since the last reset.
namespace perf {
    void begin();                   // once, in setup(): counts the boot
    void passBegin();               // top of loop()
    void passEnd();                 // just before loop() yields
    void frame(uint32_t gapMs);     // one servo frame; gap from the previous one
    void held(uint32_t us, const char* what);   // router lock released
    void part(const char* name);    // loop() section boundary: names the slow one
    String report();                // the PERF? reply; starts a new window
}
