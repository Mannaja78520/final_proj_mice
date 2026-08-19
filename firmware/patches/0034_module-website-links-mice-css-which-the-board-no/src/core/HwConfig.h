#pragma once
#include <Arduino.h>
#include <Preferences.h>

// Runtime hardware pin map, stored in the ESP32's own memory (NVS) so each
// board is WIRED-configured from its website — no recompiling before flash.
// Loaded at boot before any service touches a pin; changes need a reboot to
// take effect. The WS2812/RGB data pin is the one exception (kept compile
// time — FastLED fixes it at build time).
struct Pins {
    int motorA, motorB, motorPwm;    // lift motor driver
    int encA, encB;                  // lift encoder (-1 = none)
    int limitTop, limitDown;         // lift limit switches
    int rs485Rx, rs485Tx, rs485De;   // RS485 transceiver
    int sdCs, sdSck, sdMiso, sdMosi; // microSD (VSPI)
    int i2sBclk, i2sLrc, i2sDout;    // I2S audio amp
    int servo[10];                   // nong servos 1-8 arms, 9 WAIST, 10 SHRUG
                                     // (-1 = joint on another board)
};

class HwConfig {
public:
    Pins pins;                       // live map (defaults, then NVS overrides)

    void begin();                    // load overrides from NVS
    bool set(const String& key, int gpio);   // store + validate; reboot to apply
    bool clear(const String& key);
    void clearAll();
    int  get(const String& key) const;
    String listJson();               // current assignments {"motor_a":33,...}
    static String validPinsJson();   // which GPIOs are usable + why (for the web)
    static bool pinUsable(int gpio, bool output); // -1 ok = "disabled"

private:
    Preferences prefs_;
    int* memberFor(const String& key);
    const char* nvsFor(const String& key);
};

extern HwConfig hw;
