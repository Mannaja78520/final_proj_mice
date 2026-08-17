#include "core/SDStore.h"
#include "core/HwConfig.h"
#include <SPI.h>
#include <YAMLDuino.h>
#include <config.h>

bool SDStore::begin() {
    mtx_ = xSemaphoreCreateRecursiveMutex();
    SPI.begin(hw.pins.sdSck, hw.pins.sdMiso, hw.pins.sdMosi, hw.pins.sdCs);
    ok_ = SD.begin(hw.pins.sdCs);
    if (!ok_) {
        Serial.println("[sd] no card found, SD features disabled");
        return false;
    }
    const char* dirs[] = {"/music", "/moves", "/data"};
    for (auto d : dirs) {
        if (!SD.exists(d)) SD.mkdir(d);
    }
    Serial.printf("[sd] ok, %llu MB\n", SD.cardSize() / (1024ULL * 1024ULL));
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
        Serial.printf("[sd] yaml parse %s: %s\n", path, err.c_str());
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

bool SDStore::openWrite(const char* path) {
    if (!ok_) return false;
    lock();
    if (wtx_) { wtx_.close(); SD.remove(wtxPath_.c_str()); } // abort previous
    wtx_ = SD.open(path, FILE_WRITE);
    wtxPath_ = wtx_ ? path : "";
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
    if (!keep) SD.remove(wtxPath_.c_str());
    wtxPath_ = "";
    unlock();
    return true;
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
