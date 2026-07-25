#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <functional>

// Base class every module type implements (lift, nong, ... future modules).
// A module never talks to WiFi/RS485 directly — commands arrive through
// CommandRouter as tokenized text lines, identical on every channel.
class Module {
public:
    virtual ~Module() {}
    virtual const char* type() const = 0;

    // Optional outgoing path onto the RS485 bus, wired by main.cpp.
    // Used by a linked nong leader to re-broadcast pose commands ("#* POSE
    // ...") so several ESP32 boards drive one humanoid in sync.
    std::function<void(const String&)> busSend;

    virtual void begin() {}
    virtual void loop() {}

    // argv[0] is the command token in UPPERCASE. Set reply and return true
    // if the command belongs to this module.
    virtual bool handleCommand(String argv[], int argc, String& reply) { return false; }

    // Fill the "module" section of the status JSON.
    virtual void status(JsonObject o) {}

    // true while a motion is in progress (sequence player waits on this)
    virtual bool busy() { return false; }

    // Settings loaded from /data/module.yaml on the SD card, called before begin().
    virtual void applySettings(JsonVariant s) {}
};
