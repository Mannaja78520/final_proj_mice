#pragma once
#include <Arduino.h>
#include <FS.h>
#include <SD.h>
#include <ArduinoJson.h>

// microSD access. All SD/SPI traffic must go through lock()/unlock() because
// the async web server task (uploads/downloads) and the main loop (audio
// decode, YAML IO) share one SPI bus.
//
// Layout created on first boot:
//   /music  - mp3 / wav files for the speaker
//   /moves  - YAML movement sequences (see sd_card_example/)
//   /data   - module.yaml settings + any module data
class SDStore {
public:
    bool begin();
    bool available() const { return ok_; }

    void lock();
    // non-blocking variant for callers that can just skip a pass (audio decode)
    bool tryLock(uint32_t ms);
    void unlock();

    // Parse a YAML file on SD into an ArduinoJson document.
    bool loadYaml(const char* path, JsonDocument& doc);
    // Parse YAML already in memory. Static, and works with NO card fitted —
    // a sequence sent over the wire must be playable on a board without SD.
    static bool parseYaml(const String& text, JsonDocument& doc);
    bool saveText(const char* path, const String& text);
    // JSON array: [{"n":"file.mp3","s":1234}, ...]
    String listJson(const char* dir);
    bool remove(const char* path);

    // Chunked file transfer for the text command channels (FBEGIN/FDATA/
    // FEND/FREAD over USB serial and RS485 — see CommandRouter). One write
    // transfer at a time; FBEGIN aborts a previous unfinished one.
    bool openWrite(const char* path);
    bool writeChunk(const uint8_t* data, size_t len);
    bool closeWrite(bool keep);            // keep=false: abort + delete
    bool writing() const { return (bool)wtx_; }
    const String& writePath() const { return wtxPath_; }
    // bytes read, 0 = EOF, -1 = error
    int readChunk(const char* path, uint32_t offset, uint8_t* buf, size_t len);

private:
    bool ok_ = false;
    SemaphoreHandle_t mtx_ = nullptr;
    File wtx_;
    String wtxPath_;
};
