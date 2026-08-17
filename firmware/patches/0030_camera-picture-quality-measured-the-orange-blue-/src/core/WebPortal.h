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

    // There is exactly one radio, so there is exactly one WebPortal. The
    // command router reaches it through this instead of being handed a
    // pointer through four constructors.
    static WebPortal* instance() { return self_; }

    // ---- live WiFi control: everything here applies NOW, no reboot ----
    // A show cannot be rebooted to change a network, and "reboot to apply"
    // meant the only way to fix a wrong SSID was to power-cycle the module
    // with the arm in whatever position it stopped in.
    // arg: "" | ON | OFF | AP | RETRY | SCAN | CLEAR. One line back, always.
    String wifiCommand(const String& arg);
    void applyCreds(const String& ssid, const String& pass);

    // Run one command on ANOTHER module and return its reply, so a module the
    // PC cannot see is still controllable through one it can. See the .cpp.
    String reach(const String& target, const String& command);

    // The fleet as JSON, self first — the same list /api/peers serves, so
    // the PEERS command and the website can never disagree.
    String peersJson();

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

    // why an OTA upload was refused or failed, so the reply says something
    // useful instead of a bare 500 (see the /api/ota handler)
    String otaErr_;
    bool camStreaming_ = false;   // one live view at a time
    uint32_t camStreamAt_ = 0;    // last chunk, so a dead viewer frees it

    WifiState wstate_ = W_IDLE;
    uint32_t staRestartAt_ = 0;   // deferred STA restart, so a rename never blocks
    uint32_t wstateAt_ = 0;
    String wifiModeCfg_;          // "on" | "off" | "ap"
    bool apMode_ = false;
    bool serverStarted_ = false;
    bool peersStarted_ = false;
    String staSsid_, staPass_;   // what we are actually joined to
    // The SHOW network, kept separate from staSsid_: while relaying through
    // another module we are joined to that module's hotspot, but this is
    // still where we want to be, and what we measure the signal of.
    String homeSsid_, homePass_;
    bool onRelay_ = false;        // joined via a neighbouring module's hotspot
    String relayName_;
    String triedAp_;             // last unknown AP we tried, so we rotate
    uint32_t lastLinkCheck_ = 0;
    String appliedHost_;
    uint32_t lastPush_ = 0;
    uint32_t lastWifiCheck_ = 0;
    uint32_t lastStaRetry_ = 0;
    uint32_t lastHostCheck_ = 0;

    // Per attempt, and how many attempts. A module sharing its WiFi runs
    // AP_STA on one radio, so it time-slices and loses the odd packet — one
    // attempt scored 1 of 6 over a hotspot. The product is the worst case,
    // and it only ever happens with the module idle (reach() checks busy()).
    static const uint16_t REACH_TIMEOUT_MS = 700;
    static const uint8_t  REACH_TRIES = 3;

    static WebPortal* self_;
    // 0 idle, 1 a WIFI SCAN the user asked for, 2 a link-quality scan
    int scanState_ = 0;
    static const uint32_t LINK_CHECK_MS = 60000;  // slow: switching costs a drop
    String scanText_ = "";        // its one-line result, ready for the next ask
    uint32_t scanAt_ = 0;         // when it started, so a stuck scan gives up
    static const uint32_t SCAN_TIMEOUT_MS = 15000;

    void applyMode(const String& mode);   // bring the radio to `mode` right now
    void radioOff();
    void ensureServer();          // start the website once, however we got here
    void raiseAp();               // put our own AP on air (no mode change)
    void beginSta();
    void checkLink(int n);   // scan results -> stay / relay / return
    void startAp();
    void networkUp();             // (re)start mDNS + fleet announcement
    void startDiagnostic();       // async scan: why did the connect fail?
    void finishDiagnostic(int n);
    void applyHostname(const String& host);
    void setupRoutes();
    String statusJson();
};
