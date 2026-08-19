#include "modules/cam/CamModule.h"
#include "core/Log.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include <esp_camera.h>
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

static const char* sizeName(framesize_t f) {
    for (int i = 0; i < NSIZES; i++)
        if (SIZES[i].size == f) return SIZES[i].name;
    return "?";
}

void CamModule::begin() {
    pinMode(CAM_FLASH_PIN, OUTPUT);
    digitalWrite(CAM_FLASH_PIN, LOW);

    camera_config_t c = {};
    c.ledc_channel = LEDC_CHANNEL_0;
    c.ledc_timer   = LEDC_TIMER_0;
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

    esp_err_t err = esp_camera_init(&c);
    if (err != ESP_OK) {
        ready_ = false;
        initErr_ = "camera init failed 0x" + String((int)err, HEX);
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
        s->set_framesize(s, FRAMESIZE_SVGA);
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
            reply = "CAM size=" + String(sizeName(s->status.framesize)) +
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
            digitalWrite(CAM_FLASH_PIN, flash_ ? HIGH : LOW);
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
