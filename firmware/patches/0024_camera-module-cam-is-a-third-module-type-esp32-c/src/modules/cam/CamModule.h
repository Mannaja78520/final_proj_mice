#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <config.h>
#include "modules/Module.h"

class SDStore;

// Camera module: an ESP32-CAM that takes stills and shows a live view.
//
// It is a module like any other — same identity, same command language, same
// website, same RS485 address, same OTA. What it does NOT have is any way to
// move something: the camera and the SD card between them occupy every usable
// GPIO on that board (see config/esp32_hardware_cam_module.h), so a camera
// board can never also drive a servo. That is why it is its own type.
//
// Commands (via CommandRouter, so identical over RS485 / web / serial):
//   SNAP [<file>]     -> take a picture; with a name, save it to /photos on SD
//   CAM               -> what the sensor is set to right now
//   CAM SIZE <name>   -> qqvga qvga vga svga xga sxga uxga
//   CAM QUALITY <n>   -> 10 (best) .. 63 (smallest file)
//   CAM FLASH ON|OFF  -> the white flood LED
//   CAM VFLIP|HMIRROR 0|1
//
// The live view is HTTP, not a command: GET /api/cam.jpg is one frame, and the
// module website refreshes it. A frame is far too big for the RS485 bus or a
// one-line serial reply, so those channels get SNAP (which reports the size
// and where it went) rather than the picture itself.
//
// PSRAM matters: with it the driver keeps two full frame buffers and stills up
// to UXGA work; without it the module falls back to one buffer at SVGA. The
// AI-Thinker board has PSRAM, and status() reports what was actually found so
// a board with a broken PSRAM chip is visible rather than mysterious.
class CamModule : public Module {
public:
    explicit CamModule(SDStore* sd) : sd_(sd) {}

    const char* type() const override { return "cam"; }
    void begin() override;
    void loop() override;
    bool handleCommand(String* argv, int argc, String& reply) override;
    void status(JsonObject o) override;
    void addCapabilities(JsonArray caps) override;
    void applySettings(JsonVariant cfg) override;

    // A single JPEG for the website. Returns false when the camera is not
    // there — the page then says so instead of showing a broken image.
    // The caller must free() the buffer it is given.
    bool grab(uint8_t** out, size_t* len);

    bool ready() const { return ready_; }

private:
    SDStore* sd_ = nullptr;
    bool ready_ = false;         // the sensor answered at boot
    String initErr_;             // why it did not, in words
    bool flash_ = false;
    uint32_t shots_ = 0;         // pictures taken since boot
    String lastFile_;

    bool applySize(const String& name, String& reply);
    String saveTo(const String& name, String& err);
};
