#include "core/SDStore.h"
#include "core/Log.h"
#include "core/HwConfig.h"
#include <SPI.h>
#include <YAMLDuino.h>
#include <config.h>

bool SDStore::begin() {
    mtx_ = xSemaphoreCreateRecursiveMutex();
    // A pin set to -1 means "this board has no SPI card", and it must be taken
    // literally: SPI.begin() with -1, or on pins that belong to something else,
    // still CLAIMS those pins. On an ESP32-CAM the default SD pins (5, 18, 19,
    // 23) are the camera's own data lines — the mount failed, the SPI bus kept
    // them, the camera initialised on top, and the first malloc after a capture
    // faulted with a valid frame in hand. Two hours of "the camera is broken"
    // that were never about the camera.
    if (hw.pins.sdCs < 0 || hw.pins.sdSck < 0 ||
        hw.pins.sdMiso < 0 || hw.pins.sdMosi < 0) {
        LOGF(sd, "no SPI card on this board (pins disabled)");
        ok_ = false;
        return false;
    }
    SPI.begin(hw.pins.sdSck, hw.pins.sdMiso, hw.pins.sdMosi, hw.pins.sdCs);
    ok_ = SD.begin(hw.pins.sdCs);
    if (!ok_) {
        LOGF(sd, "no card found, SD features disabled");
        return false;
    }
    const char* dirs[] = {"/music", "/moves", "/data"};
    for (auto d : dirs) {
        if (!SD.exists(d)) SD.mkdir(d);
    }
    LOGF(sd, "ok, %llu MB", (unsigned long long)(SD.cardSize() / (1024ULL * 1024ULL)));
    return true;
}

void SDStore::lock() {
    if (mtx_) xSemaphoreTakeRecursive(mtx_, portMAX_DELAY);
}

bool SDStore::tryLock(uint32_t ms) {
    return mtx_ && xSemaphoreTakeRecursive(mtx_, pdMS_TO_TICKS(ms)) == pdTRUE;
}

void SDStore::unlock() {
    if (mtx_) xSemaphoreGiveRecursive(mtx_);
}

bool SDStore::parseYaml(const String& text, JsonDocument& doc) {
    // No card, no lock, no file — just the text. Nothing here touches SD, so
    // it works on a board that has none.
    DeserializationError err = deserializeYml(doc, text.c_str());
    if (err) {
        LOGF(seq, "yaml parse (memory): %s", err.c_str());
        return false;
    }
    return true;
}

bool SDStore::loadYaml(const char* path, JsonDocument& doc) {
    if (!ok_) return false;
    lock();
    File f = SD.open(path, FILE_READ);
    if (!f) {
        unlock();
        return false;
    }
    DeserializationError err = deserializeYml(doc, f);
    f.close();
    unlock();
    if (err) {
        LOGF(sd, "yaml parse %s: %s", path, err.c_str());
        return false;
    }
    return true;
}

bool SDStore::saveText(const char* path, const String& text) {
    if (!ok_) return false;
    lock();
    File f = SD.open(path, FILE_WRITE);
    bool ok = false;
    if (f) {
        ok = f.print(text) == text.length();
        f.close();
    }
    unlock();
    return ok;
}

String SDStore::listJson(const char* dirPath) {
    String out = "[";
    if (!ok_) return out + "]";
    lock();
    File dir = SD.open(dirPath);
    if (dir && dir.isDirectory()) {
        bool first = true;
        File f;
        while ((f = dir.openNextFile())) {
            if (!f.isDirectory()) {
                if (!first) out += ",";
                first = false;
                // escape the filename so one odd name can't break the whole listing
                String esc;
                for (const char* p = f.name(); *p; p++) {
                    if (*p == '"' || *p == '\\') esc += '\\';
                    if ((uint8_t)*p >= 0x20) esc += *p;
                }
                out += "{\"n\":\"" + esc + "\",\"s\":" + String((unsigned long)f.size()) + "}";
            }
            f.close();
        }
    }
    if (dir) dir.close();
    unlock();
    return out + "]";
}

bool SDStore::remove(const char* path) {
    if (!ok_) return false;
    lock();
    bool ok = SD.remove(path);
    unlock();
    return ok;
}

// Write BESIDE the target, then swap on success.
//
// FILE_WRITE is "w": SD.open truncates the destination the moment it opens,
// before a single byte of the new file has arrived. An upload that then stops
// part way — RS485 frame lost, USB pulled, the board browning out mid-move, a
// WiFi POST timing out — destroyed the sequence that was already on the card
// AND failed to deliver the new one. Uploading over an existing name is the
// normal "Send to robot" flow, and the card is often the only copy at a venue.
//
// With a .part file, an interrupted upload leaves the old sequence untouched
// and only a stray temporary behind.
bool SDStore::openWrite(const char* path) {
    if (!ok_) return false;
    lock();
    if (wtx_) { wtx_.close(); SD.remove(wtxTmp_.c_str()); }   // abort previous
    wtxPath_ = path;
    wtxTmp_ = wtxPath_ + ".part";
    SD.remove(wtxTmp_.c_str());          // a leftover from a dead upload
    wtx_ = SD.open(wtxTmp_.c_str(), FILE_WRITE);
    if (!wtx_) { wtxPath_ = ""; wtxTmp_ = ""; }
    unlock();
    return (bool)wtx_;
}

bool SDStore::writeChunk(const uint8_t* data, size_t len) {
    if (!wtx_) return false;
    lock();
    bool ok = wtx_.write(data, len) == len;
    unlock();
    return ok;
}

bool SDStore::closeWrite(bool keep) {
    if (!wtx_) return false;
    lock();
    wtx_.close();
    bool ok = true;
    if (!keep) {
        // aborted: the old file was never touched, so only the temp goes
        SD.remove(wtxTmp_.c_str());
    } else {
        // the whole file arrived — NOW replace the old one
        SD.remove(wtxPath_.c_str());
        ok = SD.rename(wtxTmp_.c_str(), wtxPath_.c_str());
        if (!ok) SD.remove(wtxTmp_.c_str());   // do not leave a half-named file
    }
    wtxPath_ = "";
    wtxTmp_ = "";
    unlock();
    return ok;
}

int SDStore::readChunk(const char* path, uint32_t offset, uint8_t* buf, size_t len) {
    if (!ok_) return -1;
    lock();
    File f = SD.open(path, FILE_READ);
    if (!f) { unlock(); return -1; }
    int n = 0;
    if (f.seek(offset)) n = f.read(buf, len);
    f.close();
    unlock();
    return n < 0 ? -1 : n;
}
