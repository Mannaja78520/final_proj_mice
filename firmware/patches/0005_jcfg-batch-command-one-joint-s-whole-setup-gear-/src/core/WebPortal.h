#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESPAsyncWebServer.h>
#include "core/PeerDiscovery.h"

class Identity;
class CommandRouter;
class SDStore;
class RS485Bus;

// WiFi + the module's own control website.
//
// Fully non-blocking: begin() returns immediately, so USB serial and RS485
// respond ~1 s after power-on even when there is no WiFi anywhere. The WiFi
// radio is driven by a small state machine in loop().
//
// WiFi mode (stored in NVS, set with SET WIFI ON|OFF|AP):
//   on  (default) join the configured network; if unreachable open the
//                 fallback AP and keep retrying the network every 60 s
//   ap            always host our own AP, never try to join a network
//   off           radio off — module is controlled over USB/RS485 only
//
// HTTP API (all also usable from scripts / the show controller):
//   GET  /                     control page (embedded, no SD needed)
//   GET  /api/status           full status JSON (same as the INFO command)
//   GET  /api/peers            all modules found on the network (fleet page)
//   GET  /api/cmd?c=<line>     run any command line, returns the reply text
//   GET  /api/files?dir=/music list SD files
//   GET  /api/download?path=/music/a.mp3
//   POST /api/upload?dir=/music (multipart file upload to SD)
//   GET  /api/delete?path=/music/a.mp3
//   WS   /ws                   status JSON pushed every 500ms; any text sent
//                              in is executed as a command line
class WebPortal {
public:
    void begin(Identity* id, CommandRouter* router, SDStore* sd, RS485Bus* rs485);
    void loop();

    bool apMode() const { return apMode_; }

    // show a line in the website console (used for RS485 replies from other
    // modules when the browser is bridging through this one)
    void pushConsole(const String& line);

private:
    enum WifiState { W_IDLE, W_CONNECTING, W_DIAGNOSING, W_ONLINE, W_AP };

    Identity* id_ = nullptr;
    CommandRouter* router_ = nullptr;
    SDStore* sd_ = nullptr;
    RS485Bus* rs485_ = nullptr;
    AsyncWebServer server_{80};
    AsyncWebSocket ws_{"/ws"};
    PeerDiscovery peers_;

    WifiState wstate_ = W_IDLE;
    uint32_t wstateAt_ = 0;
    String wifiModeCfg_;          // "on" | "off" | "ap"
    bool apMode_ = false;
    bool serverStarted_ = false;
    bool peersStarted_ = false;
    String staSsid_, staPass_;
    String appliedHost_;
    uint32_t lastPush_ = 0;
    uint32_t lastWifiCheck_ = 0;
    uint32_t lastStaRetry_ = 0;
    uint32_t lastHostCheck_ = 0;

    void beginSta();
    void startAp();
    void networkUp();             // (re)start mDNS + fleet announcement
    void startDiagnostic();       // async scan: why did the connect fail?
    void finishDiagnostic(int n);
    void applyHostname(const String& host);
    void setupRoutes();
    String statusJson();
};
