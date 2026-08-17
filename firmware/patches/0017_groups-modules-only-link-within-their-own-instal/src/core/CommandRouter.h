#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>

class Identity;
class Module;
class SDStore;
class SequencePlayer;
class ConfigStore;

// Single entry point for every command, no matter where it came from
// (RS485, web UI, WebSocket, USB serial, sequence file). Thread-safe via a
// recursive mutex: the async web server task and the main loop both call in.
//
// Core commands (module-independent):
//   PING                      -> PONG <id> <name> <type>
//   INFO                      -> one-line status JSON
//   SET ID <1-247>            -> stored in NVS immediately
//   SET NAME <name with spaces>
//   SET TYPE <lift|...>       -> stored, needs reboot
//   SET WIFI <ssid> <pass>    -> stored, needs reboot (no spaces in ssid)
//   CFG [<key> <value>|CLEAR] -> module settings in NVS (works without SD card)
//   MOVE <file>|MOVE STOP     -> run/stop a YAML sequence from /moves
//   REBOOT
// Everything else is forwarded to the active Module.
class CommandRouter {
public:
    void begin(Identity* id, Module* module, SDStore* sd, SequencePlayer* seq, ConfigStore* cfg);

    String handle(const String& line);
    void loop(); // drives module + sequence + deferred reboot

    Module* module() { return module_; }
    SequencePlayer* seq() { return seq_; }

    // Full status document (id/name/type/sd/seq/module). WiFi section is
    // added by WebPortal on top. Thread-safe.
    void buildStatus(JsonDocument& doc);

    void requestReboot(uint32_t delayMs = 800);

    // for callers that read identity/module state outside handle()/buildStatus()
    void lock();
    void unlock();

private:
    // In-memory sequence upload, used when no SD card is fitted. 8 KB is far
    // more than any real show sequence and leaves the heap alone.
    static const size_t RAM_SEQ_MAX = 8192;
    String ramUpload_, ramName_;
    bool   ramOpen_ = false;

    Identity* id_ = nullptr;
    Module* module_ = nullptr;
    SDStore* sd_ = nullptr;
    SequencePlayer* seq_ = nullptr;
    ConfigStore* cfg_ = nullptr;
    SemaphoreHandle_t mtx_ = nullptr;
    uint32_t rebootAt_ = 0;

    String handleLocked(const String& line);
};
