#include "modules/cam/CamModule.h"
#include "core/Log.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include <esp_camera.h>
#include <Wire.h>   // SCCB is I2C: the probe reads the sensor id directly
#include <SD.h>

// Sizes a person would ask for, smallest first. Anything above SVGA needs
// PSRAM; begin() lowers the starting size when there is none rather than
// letting the driver fail at capture time, which looks like a broken camera.
struct SizeName { const char* name; framesize_t size; };
static const SizeName SIZES[] = {
    {"qqvga", FRAMESIZE_QQVGA},   // 160x120
    {"qvga",  FRAMESIZE_QVGA},    // 320x240
    {"vga",   FRAMESIZE_VGA},     // 640x480
    {"svga",  FRAMESIZE_SVGA},    // 800x600
    {"xga",   FRAMESIZE_XGA},     // 1024x768
    {"sxga",  FRAMESIZE_SXGA},    // 1280x1024
    {"uxga",  FRAMESIZE_UXGA},    // 1600x1200
};
static const int NSIZES = sizeof(SIZES) / sizeof(SIZES[0]);

// The sensors this driver knows, by the id they report. A table, not a switch
// buried in a reply, so adding the next clone is one line.
//
// There is no one ESP32-CAM: the boards carry OV2640, OV3660, OV5640 or a
// GC-series part, and they do not behave the same at capture - frame sizes,
// clock and quality limits all differ. The driver has known the id all along
// and nothing ever asked it, so a board that initialised and then failed every
// capture gave no clue which part it was.
// Where a sensor should START, by the part it actually is.
//
// The SVGA figure above was measured on an OV2640 and was written in as one
// value for every board. It is not one board: a real ESP32-CAM here reports
// 0x5640 - an OV5640, a five megapixel part - and running it at SVGA while the
// frame buffer was allocated for the init size is exactly the shape of a
// capture that fails after a clean init.
//
// So the start size is a TABLE, and a sensor nobody has measured keeps the
// size its buffer was actually allocated for. Adding the next clone is one
// line, and the measurement that justifies it belongs beside it.
// EVERY CAMERA BOARD THIS FIRMWARE CAN FIND BY ITSELF.
//
// Asked for on 2026-08-19: the next board bought may be a different clone and
// nobody will know which. The sensor already reports what it is; the WIRING
// does not, and a wrong pin map looks exactly like a dead camera. So the maps
// are a table and the board tries them in order until the camera answers.
//
// Adding a board is one line here. Nothing else in the firmware needs to know
// it exists - the same promise the module, servo and command registries make.
// The board table is DATA: firmware/config/cam_boards.json, turned into
// CamBoards.h by gen_tables.py. It moved out of this file on 2026-08-20 so that
// adding a camera board is one entry with no C++ to read - and so the hub can
// draw the pin diagram for whichever board a module reports from the same
// source. Two copies of a pin map are two chances for the picture to lie about
// the wiring.
#include "modules/cam/CamBoards.h"

static framesize_t startSize(uint16_t pid, framesize_t initSize) {
    switch (pid) {
        case 0x2640: case 0x26:
            // Measured on this part: corrupted scanlines per frame at 10 MHz,
            // five frames each - qqvga 0.8, qvga 26.4, vga 12.8, svga 1.6.
            return FRAMESIZE_SVGA;
        default:
            // Not measured on this part. The buffer was allocated for this
            // size; asking the sensor for more is a guess with a brownout at
            // the end of it.
            return initSize;
    }
}

static String sensorName(uint16_t pid) {
    // The driver reports the FULL 16-bit product id, not the short form some
    // headers use - a real board answered 0x5640 and this table said unknown
    // because it only knew 0x56. Both are listed: different sensors report it
    // differently, and being wrong here is worse than being long.
    switch (pid) {
        case 0x2640: return "OV2640";
        case 0x3660: return "OV3660";
        case 0x5640: return "OV5640";
        case 0x7725: return "OV7725";
        case 0x7670: return "OV7670";
        case 0x1410: return "NT99141";
        case 0x2145: return "GC2145";
        case 0x032a: return "GC032A";
        case 0x0308: return "GC0308";
        case 0x3005: return "BF3005";
        case 0x26: return "OV2640";
        case 0x36: return "OV3660";
        case 0x56: return "OV5640";
        case 0x77: return "OV7725";
        case 0x76: return "OV7670";
        case 0x30: return "NT99141";
        case 0x9b: return "GC2145";
        case 0x5a: return "GC032A";
        case 0x9a: return "GC0308";
        case 0x20: return "BF3005";
        default:   return "unknown";
    }
}

static const char* sizeName(framesize_t f) {
    for (int i = 0; i < NSIZES; i++)
        if (SIZES[i].size == f) return SIZES[i].name;
    return "?";
}


// Read the sensor's identity over SCCB, which is I2C with a different name.
// Every camera the driver knows answers on 0x30, and the two id registers are
// at 0x0A (product, high) and 0x0B (low) on the OV family; the GC family
// answers 0xF0/0xF1. Both are read, because which one is right is exactly
// what we do not know yet.
String CamModule::probeSensor() {
    // EVERY SCCB BUS, not just the compiled-in one. This runs when init failed
    // on every layout, to tell a dead camera apart from wrong pins - and it
    // used to ask only the pins this firmware was built for, so on any other
    // board it reported *nothing answered* and blamed the ribbon. The boards
    // share pin pairs, so each distinct pair is tried once.
    String out;
    bool any = false;
    for (int b = -1; b < CAM_BOARD_COUNT; b++) {
        int sda = (b < 0) ? CAM_SIOD_PIN : CAM_BOARDS[b].siod;
        int scl = (b < 0) ? CAM_SIOC_PIN : CAM_BOARDS[b].sioc;
        if (sda < 0 || scl < 0) continue;
        bool seen = false;
        for (int k = -1; k < b; k++) {          // already tried this pair?
            int s2 = (k < 0) ? CAM_SIOD_PIN : CAM_BOARDS[k].siod;
            int c2 = (k < 0) ? CAM_SIOC_PIN : CAM_BOARDS[k].sioc;
            if (s2 == sda && c2 == scl) { seen = true; break; }
        }
        if (seen) continue;
        String found = probeBus(sda, scl);
        if (found.length()) {
            any = true;
            out += "on SDA " + String(sda) + "/SCL " + String(scl) + ": " + found;
        }
    }
    if (!any) return "nothing answered on SCCB, on any pin pair this firmware "
                     "knows - check the ribbon, the 5V supply and that XCLK is "
                     "running";
    return out;
}

// One bus, scanned. Split out so the caller can walk every board's pins.
String CamModule::probeBus(int sda, int scl) {
    Wire.begin(sda, scl, 100000);
    auto rd = [](uint8_t addr, uint8_t reg) -> int {
        Wire.beginTransmission(addr);
        Wire.write(reg);
        if (Wire.endTransmission(false) != 0) return -1;
        if (Wire.requestFrom((int)addr, 1) != 1) return -1;
        return Wire.read();
    };
    String out;
    for (uint8_t addr = 8; addr < 0x78; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            int a = rd(addr, 0x0A), b = rd(addr, 0x0B);
            int c1 = rd(addr, 0xF0), c2 = rd(addr, 0xF1);
            out += "SCCB 0x" + String(addr, HEX) +
                   " ov=" + String(a, HEX) + String(b, HEX) +
                   " gc=" + String(c1, HEX) + String(c2, HEX) + " ";
        }
    }
    return out;
}

// Take the LED pins belonging to the board that actually answered. Anything
// the board does not have stays -1, and -1 is never driven: an output pulled
// low on a pin that turns out to be a data line breaks the camera it was meant
// to light.
void CamModule::adoptLeds(const String& name) {
    flashPin_ = -1;
    ledPin_ = -1;
    for (int b = 0; b < CAM_BOARD_COUNT; b++) {
        if (name == CAM_BOARDS[b].name) {
            flashPin_ = CAM_BOARDS[b].flash;
            ledPin_ = CAM_BOARDS[b].led;
            break;
        }
    }
    if (name == "compiled-in") flashPin_ = CAM_FLASH_PIN;
    if (flashPin_ >= 0) {
        pinMode(flashPin_, OUTPUT);
        digitalWrite(flashPin_, LOW);
    }
}

void CamModule::begin() {
    // The flood LED is set up AFTER the board is known (see below): driving a
    // compiled-in GPIO 4 on a board that has no flood LED means driving one of
    // that board's camera data lines. On an ESP-EYE, GPIO 4 is XCLK.

    camera_config_t c = {};
    c.ledc_channel = LEDC_CHANNEL_0;
    c.ledc_timer   = LEDC_TIMER_0;
    // Filled from whichever board map turns out to be right - see the loop
    // below. The compiled-in pins are the first candidate, not the only one.
    c.pin_d0 = CAM_Y2_PIN;   c.pin_d1 = CAM_Y3_PIN;
    c.pin_d2 = CAM_Y4_PIN;   c.pin_d3 = CAM_Y5_PIN;
    c.pin_d4 = CAM_Y6_PIN;   c.pin_d5 = CAM_Y7_PIN;
    c.pin_d6 = CAM_Y8_PIN;   c.pin_d7 = CAM_Y9_PIN;
    c.pin_xclk = CAM_XCLK_PIN;
    c.pin_pclk = CAM_PCLK_PIN;
    c.pin_vsync = CAM_VSYNC_PIN;
    c.pin_href = CAM_HREF_PIN;
    c.pin_sccb_sda = CAM_SIOD_PIN;
    c.pin_sccb_scl = CAM_SIOC_PIN;
    c.pin_pwdn = CAM_PWDN_PIN;
    c.pin_reset = CAM_RESET_PIN;
    c.xclk_freq_hz = CAM_XCLK_HZ;
    c.pixel_format = PIXFORMAT_JPEG;

    // With PSRAM there is room for two full frames, so a capture can be
    // handed out while the next one is filling. Without it, one small frame is
    // all that fits in internal RAM — say so rather than failing later.
    bool psram = psramFound();
    // The frame buffer is allocated HERE, for THIS size. Without PSRAM it
    // lives in internal RAM, and asking for SVGA at init fails outright
    // (`camera init failed 0x105` — seen on the bench). So the init size is
    // what the board can actually hold, and applySize() never lets a running
    // board ask for more than it was built for.
    c.frame_size = psram ? FRAMESIZE_SVGA : FRAMESIZE_QVGA;
    c.jpeg_quality = psram ? 12 : 16;
    c.fb_count = psram ? 2 : 1;
    c.fb_location = psram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
    // LATEST, not WHEN_EMPTY. Tried on the board: with ONE frame buffer (no
    // PSRAM) the driver refuses WHEN_EMPTY outright — `camera init failed
    // 0x105`, the same error SVGA-at-init gives. Two buffers would need PSRAM,
    // and PSRAM is off here for a bigger reason (see platformio.ini).
    c.grab_mode = CAMERA_GRAB_LATEST;

    // TRY EVERY BOARD WE KNOW. The compiled-in pins first, because they are
    // right for the board this was built for and cost nothing when they work;
    // then each map in the table until the camera answers.
    //
    // A wrong pin map and a dead camera look identical from here - both are
    // "init failed" - so the only way to tell them apart is to try. Init is
    // cheap and happens once at boot; a person holding an unknown clone would
    // otherwise be reading pinout diagrams.
    esp_err_t err = esp_camera_init(&c);
    if (err == ESP_OK) {
        // IT STILL HAS TO SAY WHICH BOARD. The compiled-in pins are a board -
        // they are one of the rows in the table - and leaving board_ empty
        // because the first attempt happened to work meant the commonest board
        // of all reported nothing. The hub then showed its pin diagram marked
        // as a guess, about the one board the firmware is certain of. Found by
        // the model panel on 2026-08-20.
        for (int b = 0; b < CAM_BOARD_COUNT; b++) {
            const CamPins& m = CAM_BOARDS[b];
            if (m.xclk == CAM_XCLK_PIN && m.siod == CAM_SIOD_PIN &&
                m.sioc == CAM_SIOC_PIN && m.y2 == CAM_Y2_PIN &&
                m.pclk == CAM_PCLK_PIN) {
                board_ = m.name;
                break;
            }
        }
        if (board_.length() == 0) board_ = "compiled-in";
        adoptLeds(board_);
        LOGF(cam, "camera started on the compiled-in pins (%s)", board_.c_str());
    }
    for (int b = 0; err != ESP_OK && b < CAM_BOARD_COUNT; b++) {
        const CamPins& m = CAM_BOARDS[b];
        esp_camera_deinit();
        c.pin_pwdn = m.pwdn;   c.pin_reset = m.reset;
        c.pin_xclk = m.xclk;
        c.pin_sccb_sda = m.siod; c.pin_sccb_scl = m.sioc;
        c.pin_d7 = m.y9; c.pin_d6 = m.y8; c.pin_d5 = m.y7; c.pin_d4 = m.y6;
        c.pin_d3 = m.y5; c.pin_d2 = m.y4; c.pin_d1 = m.y3; c.pin_d0 = m.y2;
        c.pin_vsync = m.vsync; c.pin_href = m.href; c.pin_pclk = m.pclk;
        err = esp_camera_init(&c);
        if (err == ESP_OK) {
            board_ = m.name;
            adoptLeds(board_);
            LOGF(cam, "this is a %s board - found by trying, not by being told",
                 m.name);
        }
    }
    if (err != ESP_OK) {
        ready_ = false;
        initErr_ = "camera init failed 0x" + String((int)err, HEX) +
                   " on every board layout this firmware knows";
        // WHICH camera? The driver refuses without saying, and the two causes
        // need opposite fixes: an unsupported sensor is a build flag, a silent
        // one is a ribbon or a power supply. So ask the chip directly, on the
        // same two wires, and put the answer where a person will see it.
        initErr_ += " (" + probeSensor() + ")";
        // The three real causes, in the order they actually happen. A number
        // on its own sends people to the internet; this sends them to the
        // ribbon cable.
        LOGF(cam, "%s — check the ribbon is seated and the latch closed, "
                  "that the board has 5V with enough current, and that "
                  "nothing else is driving the camera pins", initErr_.c_str());
        return;
    }
    ready_ = true;
    // The OV2640's own corrections, all off by default in the driver.
    //
    // Measured on this board at 10 MHz, corrupted scanlines per frame:
    // qqvga 0.8, qvga 26.4, vga 12.8, svga 1.6 — the damage tracks the frame
    // SIZE, not the clock, which points at the sensor's downscaler rather than
    // at noise. bpc/wpc are the sensor's bad-pixel correction and lenc is its
    // lens shading correction; they are what the part provides for exactly
    // this, and they cost nothing at runtime.
    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_bpc(s, 1);        // black-pixel correction
        s->set_wpc(s, 1);        // white-pixel correction
        s->set_lenc(s, 1);       // lens shading correction
        s->set_raw_gma(s, 1);    // gamma on the raw data
        // Start on the size that measured CLEANEST on this sensor. Corrupted
        // scanlines per frame, 10 MHz, five frames each:
        //     qqvga 0.8   qvga 26.4   vga 12.8   svga 1.6
        // The frame BUFFER is still allocated for the init size above (SVGA
        // cannot be the init size without PSRAM — it fails outright), but the
        // sensor is free to run larger afterwards, and does.
        s->set_framesize(s, startSize(s->id.PID, c.frame_size));
    }
    size_t spiFree = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    LOGF(cam, "ready, %s, PSRAM %s (%u bytes of it reached the heap)",
         sizeName(c.frame_size), psram ? "yes" : "NO (small frames only)",
         (unsigned)spiFree);
    if (psram && spiFree == 0) {
        // Seen on a real AI-Thinker board: the chip is there, the camera uses
        // it, but none of it was handed to the allocator — and then a plain
        // malloc(16 KB) panics inside the heap. Captures are unaffected
        // (nothing here allocates), so this is a warning, not a failure.
        psramSick_ = true;
        LOGF(cam, "WARNING: PSRAM is present but 0 bytes reached the heap — this "
                  "board cannot serve large allocations. Pictures still work; "
                  "nothing in this module allocates.");
    }
}

void CamModule::loop() {}

// Take a frame, and give it back. The module itself never copies one.
//
// Who copies, and when, was settled on real hardware: WebPortal makes a small
// private copy for an HTTP response (the driver reclaims and refills its own
// buffer the moment it is returned, which truncated the first pictures), while
// SNAP and a card write use the driver's buffer directly and hand it straight
// back. Either way the loan is short, and exactly one frame is ever out.
// Exactly one frame is ever out on loan (inflight_), which is what makes
// give() safe to call twice: the web response gives it back when its last
// chunk is written, and again if the client disconnected first. A frame the
// second path never reached is reclaimed here on the next take(), so a browser
// closed mid-picture cannot starve the driver of buffers.
camera_fb_t* CamModule::take() {
    if (!ready_) return nullptr;
    if (inflight_) {                       // a previous loan was never returned
        esp_camera_fb_return(inflight_);
        inflight_ = nullptr;
    }
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) return nullptr;
    if (!fb->buf || !fb->len) { esp_camera_fb_return(fb); return nullptr; }
    shots_++;
    inflight_ = fb;
    return fb;
}

void CamModule::give(camera_fb_t* fb) {
    if (!fb || inflight_ != fb) return;    // already handed back
    inflight_ = nullptr;
    esp_camera_fb_return(fb);
}

bool CamModule::applySize(const String& name, String& reply) {
    sensor_t* s = esp_camera_sensor_get();
    if (!s) { reply = "ERR no sensor"; return true; }
    for (int i = 0; i < NSIZES; i++) {
        if (!name.equalsIgnoreCase(SIZES[i].name)) continue;
        if (!psramFound() && SIZES[i].size > FRAMESIZE_SVGA) {
            reply = "ERR " + name + " needs PSRAM — svga is the largest here";
            return true;
        }
        if (s->set_framesize(s, SIZES[i].size) != 0) {
            reply = "ERR the sensor refused " + name;
            return true;
        }
        reply = "OK size=" + name;
        return true;
    }
    String all;
    for (int i = 0; i < NSIZES; i++) { if (i) all += ' '; all += SIZES[i].name; }
    reply = "ERR sizes: " + all;
    return true;
}

// Write one frame to the card. Returns the path, or "" with err set.
String CamModule::saveTo(const String& name, String& err) {
    if (!sd_ || !sd_->available()) { err = "no sd card"; return ""; }
    camera_fb_t* fb = take();
    if (!fb) { err = ready_ ? "capture failed" : initErr_; return ""; }
    String path = name.startsWith("/") ? name : ("/photos/" + name);
    if (!path.endsWith(".jpg")) path += ".jpg";
    sd_->lock();
    SD.mkdir("/photos");
    File f = SD.open(path, FILE_WRITE);
    bool ok = f;
    if (ok) {
        ok = f.write(fb->buf, fb->len) == fb->len;
        f.close();
    }
    sd_->unlock();
    give(fb);
    if (!ok) { err = "cannot write " + path; return ""; }
    lastFile_ = path;
    return path;
}

bool CamModule::handleCommand(String* argv, int argc, String& reply) {
    String cmd = argv[0];
    cmd.toUpperCase();

    if (cmd == "SNAP") {
        if (!ready_) { reply = "ERR " + initErr_; return true; }
        if (argc >= 2) {
            String err;
            String path = saveTo(Util::joinFrom(argv, argc, 1), err);
            reply = path.length() ? ("OK saved " + path) : ("ERR " + err);
            return true;
        }
        // no name: just prove the sensor works, and say how big a frame is
        camera_fb_t* fb = take();
        if (!fb) { reply = "ERR capture failed"; return true; }
        size_t len = fb->len;
        give(fb);
        reply = "OK captured " + String((unsigned)len) +
                " bytes (SNAP <name> saves it, /api/cam.jpg shows it)";
        return true;
    }

    if (cmd == "CAM") {
        sensor_t* s = esp_camera_sensor_get();
        if (argc == 1) {
            if (!ready_ || !s) { reply = "ERR " + initErr_; return true; }
            reply = "CAM board=" + board_ +
                    " sensor=" + sensorName(s->id.PID) +
                    " pid=0x" + String(s->id.PID, HEX) +
                    " ver=0x" + String(s->id.VER, HEX) +
                    " size=" + String(sizeName(s->status.framesize)) +
                    " quality=" + String(s->status.quality) +
                    " flash=" + String(flash_ ? "on" : "off") +
                    " vflip=" + String(s->status.vflip) +
                    " hmirror=" + String(s->status.hmirror) +
                    " psram=" + String(psramFound() ? 1 : 0) +
                    " shots=" + String(shots_);
            return true;
        }
        String what = argv[1];
        what.toUpperCase();
        if (what == "FLASH") {
            if (argc < 3) { reply = "ERR usage: CAM FLASH ON|OFF"; return true; }
            String v = argv[2];
            v.toUpperCase();
            flash_ = (v == "ON" || v == "1");
            if (flashPin_ >= 0) digitalWrite(flashPin_, flash_ ? HIGH : LOW);
            reply = "OK flash=" + String(flash_ ? "on" : "off");
            return true;
        }
        if (!ready_ || !s) { reply = "ERR " + initErr_; return true; }
        if (what == "SIZE") {
            if (argc < 3) { reply = "ERR usage: CAM SIZE <qqvga..uxga>"; return true; }
            return applySize(argv[2], reply);
        }
        if (what == "QUALITY") {
            int q = argc >= 3 ? argv[2].toInt() : 0;
            if (q < 10 || q > 63) { reply = "ERR quality 10 (best) - 63 (smallest)"; return true; }
            s->set_quality(s, q);
            reply = "OK quality=" + String(q);
            return true;
        }
        if (what == "VFLIP" || what == "HMIRROR") {
            int on = argc >= 3 ? argv[2].toInt() : 0;
            if (what == "VFLIP") s->set_vflip(s, on ? 1 : 0);
            else s->set_hmirror(s, on ? 1 : 0);
            reply = "OK " + what + "=" + String(on ? 1 : 0);
            return true;
        }
        reply = "ERR CAM [SIZE <name>|QUALITY <10-63>|FLASH ON|OFF|VFLIP 0|1|HMIRROR 0|1]";
        return true;
    }
    return false;
}

void CamModule::addCapabilities(JsonArray caps) {
    caps.add("camera");
}

void CamModule::status(JsonObject o) {
    sensor_t* s = ready_ ? esp_camera_sensor_get() : nullptr;
    o["ready"] = ready_;
    if (!ready_) o["error"] = initErr_;
    o["psram"] = psramFound();
    o["flash"] = flash_;
    o["shots"] = shots_;
    if (lastFile_.length()) o["last"] = lastFile_;
    if (s) {
        o["size"] = sizeName(s->status.framesize);
        o["quality"] = s->status.quality;
    }
}

void CamModule::applySettings(JsonVariant cfg) {
    // /data/module.yaml or CFG: size and quality, so a camera comes up the way
    // it was left rather than on the driver's default every boot.
    if (!cfg.is<JsonObject>()) return;
    JsonObject o = cfg.as<JsonObject>();
    if (o["cam_size"].is<const char*>()) {
        String reply;
        applySize(String((const char*)o["cam_size"]), reply);
    }
    if (o["cam_quality"].is<int>()) {
        sensor_t* s = esp_camera_sensor_get();
        int q = o["cam_quality"].as<int>();
        if (s && q >= 10 && q <= 63) s->set_quality(s, q);
    }
}
