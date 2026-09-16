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
    // What this module CAN do, as short tags ("rgb", "audio", "joints"…).
    // The websites render their cards from these instead of from a hardcoded
    // list of module types, so a NEW type shows the right controls without the
    // site being taught about it. Core adds its own (sd, rs485, pins…).
    virtual void addCapabilities(JsonArray caps) { (void)caps; }

    virtual void status(JsonObject o) {}

    // true while a motion is in progress (sequence player waits on this)
    virtual bool busy() { return false; }

    // Stop any sound this module is making. STOP is the panic button, and a
    // show stopped in a hurry must not leave music playing over a robot that
    // has frozen — so every STOP path calls this, including MOVE STOP, which
    // lives in core and cannot know whether a speaker is wired.
    virtual void silence() {}

    // Silence ONLY a track that was told to repeat. A show that runs off its
    // last step leaves a one-shot playing on purpose — a long track may outlive
    // a short show — but a repeating one would never end by itself.
    virtual void silenceLoop() {}

    // Settings loaded from /data/module.yaml on the SD card, called before begin().
    virtual void applySettings(JsonVariant s) {}
};
