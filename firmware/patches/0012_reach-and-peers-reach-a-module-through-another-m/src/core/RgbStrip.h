#pragma once
#include <Arduino.h>
#include <config.h>
#define FASTLED_INTERNAL // silence FastLED version pragma
#include <FastLED.h>

// WS2812B strip with a small non-blocking effect engine.
// Effects: solid | rainbow | chase | breathe | off
class RgbStrip {
public:
    void begin(uint16_t count);
    void loop();

    void setColor(uint8_t r, uint8_t g, uint8_t b);
    void setBrightness(uint8_t b);
    bool setEffect(const String& name);
    void setCount(uint16_t c);

    uint8_t r() const { return r_; }
    uint8_t g() const { return g_; }
    uint8_t b() const { return b_; }
    uint8_t brightness() const { return bright_; }
    const String& effect() const { return effect_; }
    uint16_t count() const { return count_; }

private:
    CRGB leds_[RGB_MAX_LEDS];
    uint8_t r_ = 0, g_ = 0, b_ = 80;
    uint8_t bright_ = 128;
    String effect_ = "solid";
    uint16_t count_ = RGB_DEFAULT_LEDS;
    uint32_t lastFrame_ = 0;
    uint8_t phase_ = 0;

    void render();
};
