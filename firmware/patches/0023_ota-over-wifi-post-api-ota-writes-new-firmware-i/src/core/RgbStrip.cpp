#include "core/RgbStrip.h"

void RgbStrip::begin(uint16_t count) {
    setCount(count);
    FastLED.addLeds<WS2812B, RGB_LED_PIN, GRB>(leds_, RGB_MAX_LEDS);
    FastLED.setBrightness(bright_);
    fill_solid(leds_, RGB_MAX_LEDS, CRGB::Black);
    FastLED.show();
}

void RgbStrip::setCount(uint16_t c) {
    if (c < 1) c = 1;
    if (c > RGB_MAX_LEDS) c = RGB_MAX_LEDS;
    count_ = c;
}

void RgbStrip::setColor(uint8_t r, uint8_t g, uint8_t b) {
    r_ = r; g_ = g; b_ = b;
    if (effect_ == "off") effect_ = "solid";
}

void RgbStrip::setBrightness(uint8_t b) {
    bright_ = b;
    FastLED.setBrightness(bright_);
}

bool RgbStrip::setEffect(const String& name) {
    String n = name;
    n.toLowerCase();
    if (n != "solid" && n != "rainbow" && n != "chase" && n != "breathe" && n != "off") return false;
    effect_ = n;
    return true;
}

void RgbStrip::loop() {
    uint32_t now = millis();
    if (now - lastFrame_ < 25) return; // ~40 fps
    lastFrame_ = now;
    phase_++;
    render();
}

void RgbStrip::render() {
    CRGB c(r_, g_, b_);
    if (effect_ == "solid") {
        fill_solid(leds_, count_, c);
    } else if (effect_ == "rainbow") {
        fill_rainbow(leds_, count_, phase_, max(1, 255 / (int)count_));
    } else if (effect_ == "chase") {
        fadeToBlackBy(leds_, count_, 60);
        leds_[phase_ % count_] = c;
    } else if (effect_ == "breathe") {
        CRGB scaled = c;
        scaled.nscale8_video(beatsin8(12, 8, 255));
        fill_solid(leds_, count_, scaled);
    } else { // off
        fill_solid(leds_, count_, CRGB::Black);
    }
    // keep unused tail of the compile-time buffer dark
    if (count_ < RGB_MAX_LEDS) fill_solid(leds_ + count_, RGB_MAX_LEDS - count_, CRGB::Black);
    FastLED.show();
}
