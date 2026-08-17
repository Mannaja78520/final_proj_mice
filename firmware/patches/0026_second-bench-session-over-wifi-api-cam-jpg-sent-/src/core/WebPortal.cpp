#include "core/WebPortal.h"
#include "core/CommandRouter.h"
#include "core/Identity.h"
#include "core/RS485Bus.h"
#include "modules/Module.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include "core/WifiLink.h"
#include "core/SequencePlayer.h"
#include "core/BuildTypes.h"
#if MICE_HAS_CAM
#include "modules/cam/CamModule.h"
#endif
#include <Update.h>
// The page for THIS build's module type, generated from the master
// src/web/WebUI.h by tools/gen_tables.py into $BUILD_DIR/generated/.
#include "web/ModuleUI.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPmDNS.h>
#include <SD.h>
#include <config.h>
#include <memory>

WebPortal* WebPortal::self_ = nullptr;

void WebPortal::begin(Identity* id, CommandRouter* router, SDStore* sd, RS485Bus* rs485) {
    self_ = this;
    id_ = id;
    router_ = router;
    sd_ = sd;
    rs485_ = rs485;
    wifiModeCfg_ = id_->wifiMode();
    appliedHost_ = id_->hostname();

    // log why every disconnect happens — makes "wrong password" vs
    // "network invisible (5GHz-only hotspot)" obvious on the serial monitor
    WiFi.onEvent([](WiFiEvent_t, WiFiEventInfo_t info) {
        uint8_t r = info.wifi_sta_disconnected.reason;
        const char* hint = "";
        if (r == 201) hint = " (AP not found: wrong SSID, or 5GHz-only network — ESP32 is 2.4GHz only)";
        else if (r == 202 || r == 15) hint = " (auth failed: wrong password, or WPA3-only network)";
        Serial.printf("[wifi] disconnected, reason=%u%s\n", r, hint);
    }, WiFiEvent_t::ARDUINO_EVENT_WIFI_STA_DISCONNECTED);

    WiFi.persistent(false);
    applyMode(wifiModeCfg_);
}

// Bring the radio to `mode` immediately. Called at boot and again by every
// WIFI / SET WIFI command, so there is exactly ONE piece of code that decides
// what the radio does — boot and a live change cannot drift apart.
void WebPortal::applyMode(const String& mode) {
    wifiModeCfg_ = mode;
    // the setup network is ALWAYS what gets tried: credentials entered on the
    // module win over the ones compiled into config.h, which are only a
    // factory fallback for a board nobody has set up yet.
    homeSsid_ = id_->wifiSsid().length() ? id_->wifiSsid() : String(WIFI_SSID);
    homePass_ = id_->wifiSsid().length() ? id_->wifiPass() : String(WIFI_PASS);
    staSsid_ = homeSsid_;          // any mode change goes back to the show
    staPass_ = homePass_;          // network; relaying is decided from there
    onRelay_ = false;
    relayName_ = "";

    if (mode == "off") { radioOff(); return; }

    // ORDER MATTERS: the radio first, the website second. AsyncWebServer::begin
    // binds a TCP socket, and lwip has no mailbox until an interface exists —
    // calling it first panics the chip with
    //   assert failed: tcpip_api_call ... (Invalid mbox)
    // in a boot loop. Found by flashing it.
    if (mode == "ap") {
        WiFi.mode(WIFI_AP);
        raiseAp();
        ensureServer();
        startAp();
        return;
    }

    // "on" — BOTH at once, for two different reasons that want the same thing:
    //   fallback: the show network may not be up yet, and the module's own AP
    //             is how you reach it to fix that;
    //   sharing:  a module parked out of router range can join THIS module's
    //             AP and still be reached from the hub.
    // The ESP32 does AP+STA on one radio natively. The AP starts on channel 1
    // and follows the STA to its channel once connected — an AP client is
    // dropped for a moment at that point, which is why the hub retries.
    WiFi.mode(WIFI_AP_STA);
    raiseAp();
    ensureServer();
    beginSta();
}

void WebPortal::radioOff() {
    WiFi.softAPdisconnect(true);
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    apMode_ = false;
    wstate_ = W_IDLE;
    Serial.println("[wifi] disabled — USB/RS485 only (WIFI ON to re-enable)");
}

void WebPortal::ensureServer() {
    if (serverStarted_) return;
    setupRoutes();
    server_.begin();
    serverStarted_ = true;
}

// Put our AP on air. No mode change and no state change — applyMode() owns
// both, so this can be called from either branch.
void WebPortal::raiseAp() {
    String apName = appliedHost_.length() > 30 ? appliedHost_.substring(0, 30) : appliedHost_;
    WiFi.setHostname(appliedHost_.c_str());
    // The password comes from the GROUP, so every module in one installation
    // shares it automatically and modules from anywhere else cannot get in.
    String apPass = id_->apPassword();
    WiFi.softAP(apName.c_str(), apPass.c_str());
    Serial.printf("[wifi] AP \"%s\" pass \"%s\" group \"%s\" ip=%s\n",
                  apName.c_str(), apPass.c_str(),
                  id_->group().length() ? id_->group().c_str() : "(none)",
                  WiFi.softAPIP().toString().c_str());
}

void WebPortal::beginSta() {
    // core 2.x: the hostname must be stored BEFORE the STA interface is
    // created — the core applies it on the STA_START event, ahead of the
    // DHCP request. Set any later and the router sees "esp32-XXXXXX".
    WiFi.setHostname(appliedHost_.c_str());
    WiFi.config(IPAddress(0, 0, 0, 0), IPAddress(0, 0, 0, 0), IPAddress(0, 0, 0, 0)); // re-arm DHCP
    WiFi.begin(staSsid_.c_str(), staPass_.length() ? staPass_.c_str() : nullptr); // nullptr = open network
    wstate_ = W_CONNECTING;
    wstateAt_ = millis();
    Serial.printf("[wifi] connecting to \"%s\" as \"%s\" in the background — USB/RS485 already live\n",
                  staSsid_.c_str(), appliedHost_.c_str());
}

// Fall back to being reachable over our own AP only. The AP itself is already
// on air (raiseAp at mode time); this is the STATE change that says clients
// should use 192.168.4.1, plus the retry clock.
void WebPortal::startAp() {
    apMode_ = true;
    wstate_ = W_AP;
    wstateAt_ = millis();
    lastStaRetry_ = millis();
    networkUp();
}

// SET WIFI <ssid> <pass> — store and JOIN NOW. Without this the only way to
// correct a typo'd SSID was a power cycle.
void WebPortal::applyCreds(const String& ssid, const String& pass) {
    id_->setWifi(ssid, pass);
    id_->setWifiMode("on");
    applyMode("on");
}


// Scan finished: pick the link we should be on.
//
// A neighbour is identified by its AP SSID being the NAME of a module we know
// (every module's hotspot is named after the module, and peers_ is how we
// learned those names). A board that has never seen another module therefore
// has nothing to lean on — which is correct: there is nothing to prove is a
// module rather than someone's phone.
void WebPortal::checkLink(int n) {
    int mainRssi = 0, bestRssi = 0;
    String bestName;
    bool bestKnown = false;
    for (int i = 0; i < n; i++) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        if (ssid == homeSsid_) {
            if (!mainRssi || rssi > mainRssi) mainRssi = rssi;
            continue;
        }
        if (ssid == appliedHost_) continue;       // our own AP
        if (!ssid.length()) continue;

        PeerDiscovery::Peer p;
        bool known = peers_.find(ssid, p);

        // A module we have met is always a candidate. One we have NOT met is
        // a candidate too, but only when this module belongs to a group —
        // because then the access-point password is derived from the group,
        // so the only network we can actually get into is a group-mate's.
        // That is what makes hunting for a neighbour safe: another company's
        // modules in the same room will simply refuse us, and ours refuse
        // them. Ungrouped boards never hunt; they would be using the shared
        // fallback password, which proves nothing about who owns the module.
        //
        // Without this, a cold start with no venue WiFi left every module
        // sitting on its own access point unable to find any of the others:
        // a neighbour was only recognised by a name we had already seen, and
        // a module that just booted has seen nobody.
        if (!known) {
            if (!id_->group().length()) continue;
            if (ssid == homeSsid_) continue;
            if (triedAp_ == ssid) continue;   // did not work last time; rotate
        }
        if (!bestRssi || rssi > bestRssi) {
            bestRssi = rssi;
            bestName = ssid;
            bestKnown = known;
        }
        // a module we already know beats a guess of the same strength
        if (known && !bestKnown) { bestRssi = rssi; bestName = ssid; bestKnown = true; }
    }

    switch (wifilink::decide(onRelay_, mainRssi, bestRssi)) {
        case wifilink::RELAY:
            Serial.printf("[wifi] \"%s\" is weak (%d dBm) — going through \"%s\" (%d dBm)\n",
                          homeSsid_.c_str(), mainRssi, bestName.c_str(), bestRssi);
            staSsid_ = bestName;
            staPass_ = id_->apPassword();   // only a group-mate will let us in
            onRelay_ = true;
            relayName_ = bestName;
            // remember an UNKNOWN one we are about to try, so that if it does
            // not let us in we move on to a different candidate next time
            triedAp_ = bestKnown ? String("") : bestName;
            beginSta();
            break;
        case wifilink::RETURN:
            Serial.printf("[wifi] \"%s\" is strong again (%d dBm) — leaving \"%s\"\n",
                          homeSsid_.c_str(), mainRssi, relayName_.c_str());
            staSsid_ = homeSsid_;
            staPass_ = homePass_;
            onRelay_ = false;
            relayName_ = "";
            beginSta();
            break;
        default:
            // scanning stopped the connect attempt; put it back
            if (WiFi.status() != WL_CONNECTED)
                WiFi.begin(staSsid_.c_str(), staPass_.length() ? staPass_.c_str() : nullptr);
            break;
    }
}

String WebPortal::peersJson() {
    String selfIp = apMode_ ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
    return peers_.peersJson(selfIp);   // caller already holds the router mutex
}

// Run one command on ANOTHER module and hand back its reply.
//
// This is the last step of "a module is always reachable". A board parked out
// of router range joins a nearby module's AP (see applyMode) — but then the
// PC cannot see it, because it is on the other module's private subnet. So
// the module it joined forwards for it:
//
//     PC --USB--> lift  --its own AP-->  nong
//     REACH nong POSE 90 90 ...      -> "OK POSE"
//
// It is deliberately the SAME shape as the RS485 bridge (`#3 GOTO 2`): one
// command in, one reply line out, so nothing upstream has to learn a new
// protocol — the hub's dev= routing and the module website's console both
// work unchanged.
//
// It BLOCKS for up to REACH_TIMEOUT_MS, which is why it refuses while the
// module is moving: this loop also interpolates the servos, and a joint that
// stops mid-move is worse than a command that says "busy". Reaching through
// is for finding and configuring a module, not for driving one in a show —
// in a show you address it directly, or over RS485.
//
String WebPortal::reach(const String& target, const String& command) {
    if (wifiModeCfg_ == "off") return "ERR wifi is off (WIFI ON first)";
    if (wstate_ != W_ONLINE && wstate_ != W_AP) return "ERR no network yet";
    if (router_->module() && router_->module()->busy())
        return "ERR busy — the module is moving (reaching through would stall it)";

    PeerDiscovery::Peer p;
    if (!peers_.find(target, p))
        return "ERR no module \"" + target + "\" — try its ip, or PEERS to list them";

    String url = "http://" + p.ip + "/api/cmd?c=";
    for (unsigned i = 0; i < command.length(); i++) {   // percent-encode
        char c = command[i];
        if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') url += c;
        else if (c == ' ') url += '+';
        else {
            char buf[4];
            snprintf(buf, sizeof(buf), "%%%02X", (uint8_t)c);
            url += buf;
        }
    }

    // Retry, because a single attempt is not reliable and the reason is
    // structural: a module in AP_STA has ONE radio serving both the show
    // network and its own AP, so it time-slices and drops the odd packet.
    // Measured on the bench over a phone hotspot — one attempt at 800 ms
    // scored 1 of 6, while the far module answered the PC 6 of 6 the whole
    // time, so the far module was never the problem. Over a direct module AP
    // (one hop, no sharing) one attempt was already 7 of 7.
    //
    // The budget stays bounded and the busy() guard above still means this
    // can never happen while a joint is moving.
    int code = 0;
    String body;
    for (int attempt = 0; attempt < REACH_TRIES && code <= 0; attempt++) {
        HTTPClient http;
        http.setConnectTimeout(REACH_TIMEOUT_MS);
        http.setTimeout(REACH_TIMEOUT_MS);
        http.setReuse(false);   // a fresh connection each time; never a half-open one
        if (!http.begin(url)) return "ERR cannot reach " + p.ip;
        code = http.GET();
        if (code > 0) body = http.getString();
        http.end();
        // no pause between attempts: the failed one already spent its own
        // timeout, and a delay() here would be exactly the kind of blocking
        // wait the radio path is not allowed to contain
    }
    if (code <= 0) return "ERR " + p.name + " did not answer (" + p.ip + ")";
    body.trim();
    // never let a multi-line body break "one command, one reply line"
    int nl = body.indexOf('\n');
    if (nl >= 0) body = body.substring(0, nl);
    return body.length() ? body : ("ERR " + p.name + " sent an empty reply");
}

// One command, one line back. Never blocks: SCAN is asynchronous and the
// answer is collected in loop().
String WebPortal::wifiCommand(const String& arg) {
    String a = arg;
    a.trim();
    a.toUpperCase();

    if (a == "ON" || a == "OFF" || a == "AP") {
        String m = a;
        m.toLowerCase();
        id_->setWifiMode(m);
        applyMode(m);
        return "OK wifi " + m + " — applied now, no reboot";
    }
    // Forget the credentials typed into this board and go back to the network
    // compiled into config.h. Without this a board could only ever be moved
    // from one network to ANOTHER named one — there was no way home. That
    // matters when a module has been pointed at a neighbouring module's
    // hotspot for a bench test and now has to rejoin the real show network.
    if (a == "CLEAR") {
        id_->setWifi("", "");
        applyMode("on");
        return "OK forgot the stored network, now using \"" + staSsid_ +
               "\" from the firmware";
    }
    if (a == "RETRY") {
        if (wifiModeCfg_ == "off") return "ERR wifi is off (WIFI ON first)";
        applyMode("on");
        return "OK retrying \"" + staSsid_ + "\" now";
    }
    if (a == "SCAN") {
        if (wifiModeCfg_ == "off") return "ERR wifi is off (WIFI ON first)";
        if (scanState_) return "OK scanning — ask again in a moment";
        if (scanText_.length()) { String r = scanText_; scanText_ = ""; return r; }
        if (wstate_ == W_DIAGNOSING) return "OK a scan is already running — ask again in a moment";
        // A connect attempt in flight makes esp_wifi_scan_start refuse
        // (ESP_ERR_WIFI_STATE), and in "on" mode the STA retries constantly —
        // so the scan failed EVERY time until the attempt is stopped first.
        // Found on the bench: "ERR scan failed", over and over. The
        // credentials are kept, and loop() re-joins once the scan lands.
        WiFi.scanDelete();
        // Only stand the radio down when it is CONNECTING. A connect in
        // flight makes esp_wifi_scan_start refuse — but a connection that is
        // already up does not, and disconnecting an established link to scan
        // it actively breaks the scan:
        //
        //   OK scanning - ask again in a moment
        //   [wifi] disconnected, reason=8        <- our own disconnect
        //   [wifi] connecting to "SIRILUK#CD"    <- re-join, killing the scan
        //
        // WiFi.disconnect() is asynchronous, so its event lands AFTER the
        // scan has started and aborts it. Every scan then came back
        // "ERR scan failed" while the module sat happily on the network it
        // could not see. Read off the board's own log.
        if (WiFi.status() != WL_CONNECTED) {
            WiFi.setAutoReconnect(false);   // or the core re-connects and blocks the scan
            WiFi.disconnect(false, false);
        }
        if (WiFi.scanNetworks(true) == WIFI_SCAN_FAILED) {  // async: never stall the servo loop
            WiFi.setAutoReconnect(true);
            return "ERR could not start a scan";
        }
        scanState_ = 1;
        scanAt_ = millis();
        return "OK scanning — ask again in a moment";
    }
    if (a.length()) return "ERR usage: WIFI [ON|OFF|AP|RETRY|SCAN|CLEAR]";

    // no argument: where are we?
    String s = "WIFI mode=" + wifiModeCfg_;
    s += " state=";
    switch (wstate_) {
        case W_CONNECTING: s += "connecting"; break;
        case W_DIAGNOSING: s += "scanning"; break;
        case W_ONLINE:     s += "online"; break;
        case W_AP:         s += "ap-only"; break;
        default:           s += "idle"; break;
    }
    s += " ssid=\"" + staSsid_ + "\"";
    if (onRelay_) s += " via=\"" + relayName_ + "\"";   // leaning on a neighbour
    if (wstate_ == W_ONLINE) {
        s += " ip=" + WiFi.localIP().toString() + " rssi=" + String(WiFi.RSSI());
    }
    if (wifiModeCfg_ != "off") {
        s += " ap=\"" + WiFi.softAPSSID() + "\" apip=" + WiFi.softAPIP().toString() +
             " apclients=" + String(WiFi.softAPgetStationNum());
    }
    return s;
}

void WebPortal::networkUp() {
    MDNS.end();
    if (MDNS.begin(appliedHost_.c_str())) {
        MDNS.addService("http", "tcp", 80);
        if (!peersStarted_) {
            peers_.begin(id_);
            peersStarted_ = true;
        } else {
            peers_.announce();
        }
        Serial.printf("[wifi] mdns http://%s.local/\n", appliedHost_.c_str());
    }
}

// Async scan after a failed connect: says whether the SSID is visible at all
// on 2.4GHz and what auth it uses. Answers "why won't it join?" directly.
void WebPortal::startDiagnostic() {
    Serial.printf("[wifi] could not join \"%s\" — scanning...\n", staSsid_.c_str());
    WiFi.scanNetworks(true); // async, result polled in loop()
    wstate_ = W_DIAGNOSING;
    wstateAt_ = millis();
}

void WebPortal::finishDiagnostic(int n) {
    bool seen = false;
    for (int i = 0; i < n; i++) {
        if (WiFi.SSID(i) == staSsid_) {
            seen = true;
            Serial.printf("[wifi] \"%s\" IS visible (ch%d, %ddBm, enc=%d) -> check the password"
                          " / disable WPA3-only on the router\n",
                          staSsid_.c_str(), WiFi.channel(i), WiFi.RSSI(i), (int)WiFi.encryptionType(i));
        }
    }
    if (!seen) {
        Serial.printf("[wifi] \"%s\" NOT visible on 2.4GHz. If it's a phone/laptop hotspot,"
                      " switch it to 2.4GHz (iPhone: Maximize Compatibility)\n", staSsid_.c_str());
        if (n > 0) {
            Serial.printf("[wifi] networks I can see:");
            for (int i = 0; i < n && i < 10; i++) Serial.printf(" \"%s\"", WiFi.SSID(i).c_str());
            Serial.println();
        }
    }
    WiFi.scanDelete();
}

// Re-apply the module name everywhere it is visible on the network: DHCP
// hostname (what the router's client list shows), mDNS <name>.local, the
// fleet-discovery TXT records, and the AP's SSID. Called from loop()
// whenever SET NAME changed the identity.
void WebPortal::applyHostname(const String& host) {
    appliedHost_ = host;
    Serial.printf("[wifi] name changed, applying hostname \"%s\"\n", host.c_str());
    if (wstate_ == W_AP) {
        raiseAp();      // rename the AP in place
        networkUp();
    } else {
        // A new hostname is only announced reliably when the STA interface is
        // recreated from scratch, exactly like at boot. The radio needs a
        // moment between powering down and back up — but this runs in the SAME
        // loop as the servo interpolation, so it must not be a delay(): a
        // blocked loop is a joint that stops mid-move. Power it down now and
        // let loop() bring it back on the next pass.
        WiFi.disconnect(true); // also powers the STA off
        staRestartAt_ = millis() + 150;
    }
}

void WebPortal::pushConsole(const String& line) {
    if (serverStarted_ && ws_.count()) ws_.textAll("> " + line);
}

String WebPortal::statusJson() {
    // buildStatus includes the wifi section, so INFO over USB/RS485 and
    // /api/status over HTTP return identical JSON
    JsonDocument doc;
    router_->buildStatus(doc);
    String out;
    serializeJson(doc, out);
    return out;
}

void WebPortal::setupRoutes() {
    ws_.onEvent([this](AsyncWebSocket*, AsyncWebSocketClient* client, AwsEventType type,
                       void* arg, uint8_t* data, size_t len) {
        if (type == WS_EVT_CONNECT) {
            client->text(statusJson());
        } else if (type == WS_EVT_DATA) {
            AwsFrameInfo* info = (AwsFrameInfo*)arg;
            if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
                String line((const char*)data, len);
                String reply = router_->handle(line);
                client->text("> " + reply); // UI treats non-JSON frames as console output
            }
        }
    });
    server_.addHandler(&ws_);

    server_.on("/", HTTP_GET, [](AsyncWebServerRequest* req) {
        req->send_P(200, "text/html", WEB_UI_HTML);
    });

    server_.on("/api/status", HTTP_GET, [this](AsyncWebServerRequest* req) {
        req->send(200, "application/json", statusJson());
    });

    server_.on("/api/peers", HTTP_GET, [this](AsyncWebServerRequest* req) {
        router_->lock(); // identity strings must not move while we copy them
        String out = peersJson();
        router_->unlock();
        req->send(200, "application/json", out);
    });

    server_.on("/api/cmd", HTTP_GET, [this](AsyncWebServerRequest* req) {
        if (!req->hasParam("c")) { req->send(400, "text/plain", "ERR missing c"); return; }
        String c = req->getParam("c")->value();
        c.trim();
        // '#' lines bridge onto the RS485 bus: control other modules through
        // this one (their replies stream into the console via the WebSocket)
        if (c.startsWith("#") && rs485_) {
            req->send(200, "text/plain", rs485_->bridge(c, router_));
            return;
        }
        req->send(200, "text/plain", router_->handle(c));
    });

    server_.on("/api/files", HTTP_GET, [this](AsyncWebServerRequest* req) {
        String dir = req->hasParam("dir") ? req->getParam("dir")->value() : "/data";
        if (!Util::safePath(dir)) { req->send(400, "text/plain", "ERR bad dir"); return; }
        req->send(200, "application/json", sd_->listJson(dir.c_str()));
    });

    server_.on("/api/delete", HTTP_GET, [this](AsyncWebServerRequest* req) {
        if (!req->hasParam("path")) { req->send(400, "text/plain", "ERR missing path"); return; }
        String path = req->getParam("path")->value();
        if (!Util::safePath(path)) { req->send(400, "text/plain", "ERR bad path"); return; }
        req->send(200, "text/plain", sd_->remove(path.c_str()) ? "OK" : "ERR delete failed");
    });

    server_.on("/api/download", HTTP_GET, [this](AsyncWebServerRequest* req) {
        if (!req->hasParam("path")) { req->send(400, "text/plain", "ERR missing path"); return; }
        String path = req->getParam("path")->value();
        if (!Util::safePath(path)) { req->send(400, "text/plain", "ERR bad path"); return; }
        sd_->lock();
        bool exists = SD.exists(path);
        sd_->unlock();
        if (!exists) { req->send(404, "text/plain", "ERR not found"); return; }

        auto file = std::make_shared<File>();
        sd_->lock();
        *file = SD.open(path, FILE_READ);
        sd_->unlock();
        if (!*file) { req->send(500, "text/plain", "ERR open failed"); return; }

        // if the client aborts mid-download, ~File() would otherwise touch the
        // SPI bus without the SD mutex (racing audio decode on the main loop)
        req->onDisconnect([this, file]() {
            sd_->lock();
            if (*file) file->close();
            sd_->unlock();
        });

        AsyncWebServerResponse* res = req->beginChunkedResponse(
            "application/octet-stream",
            [this, file](uint8_t* buf, size_t maxLen, size_t) -> size_t {
                sd_->lock();
                size_t n = file->read(buf, maxLen);
                if (n == 0) file->close();
                sd_->unlock();
                return n;
            });
        String fname = path.substring(path.lastIndexOf('/') + 1);
        res->addHeader("Content-Disposition", "attachment; filename=\"" + fname + "\"");
        req->send(res);
    });

    server_.on("/api/upload", HTTP_POST,
        [](AsyncWebServerRequest* req) {
            // _tempObject is set only after the final chunk closed cleanly
            // (the request destructor free()s it for us)
            bool ok = req->_tempObject != nullptr;
            req->send(ok ? 200 : 500, "text/plain", ok ? "OK" : "ERR upload failed (sd?)");
        },
        [this](AsyncWebServerRequest* req, String filename, size_t index,
               uint8_t* data, size_t len, bool final) {
            if (index == 0) {
                String dir = req->hasParam("dir") ? req->getParam("dir")->value() : "/data";
                if (!Util::safePath(dir)) return;
                int slash = filename.lastIndexOf('/');
                if (slash >= 0) filename = filename.substring(slash + 1);
                sd_->lock();
                req->_tempFile = SD.open(dir + "/" + filename, FILE_WRITE);
                sd_->unlock();
                // client aborts mid-upload: close under the SD mutex, not in ~File()
                req->onDisconnect([this, req]() {
                    if (req->_tempFile) {
                        sd_->lock();
                        req->_tempFile.close();
                        sd_->unlock();
                    }
                });
            }
            if (req->_tempFile) {
                sd_->lock();
                if (len) req->_tempFile.write(data, len);
                if (final) {
                    req->_tempFile.close();
                    req->_tempObject = malloc(1); // mark success
                }
                sd_->unlock();
            }
        });

#if MICE_HAS_CAM
    // ---- one camera frame ---------------------------------------------
    // A JPEG is far too big for a one-line reply on RS485 or serial, so the
    // picture lives here and those channels get SNAP instead. One frame per
    // request on purpose: an MJPEG stream would hold one of this board's four
    // connections open for as long as someone watched it, and the rest of the
    // site would stop answering.
    server_.on("/api/cam.jpg", HTTP_GET, [this](AsyncWebServerRequest* req) {
        CamModule* cam = static_cast<CamModule*>(router_->module());
        camera_fb_t* fb = cam ? cam->take() : nullptr;
        if (!fb) {
            req->send(503, "text/plain", "no picture — the camera did not start");
            return;
        }
        // Copy the frame, hand the driver's buffer straight back, and send the
        // copy. Sending the driver's buffer directly was tried on the real
        // board and gave a 200 with 353 bytes of a 13,000-byte frame: the
        // frame was reclaimed and refilled while the send was still queued.
        // A private copy cannot be pulled out from under the response.
        //
        // ~3-5 KB per frame at QVGA, freed as soon as it is sent. If the copy
        // cannot be made, say so: a 503 is a picture you did not get, a crash
        // is a board that went away.
        size_t len = fb->len;
        uint8_t* copy = (uint8_t*)malloc(len);
        if (copy) memcpy(copy, fb->buf, len);
        cam->give(fb);                       // the driver may refill it now
        if (!copy) {
            req->send(503, "text/plain", "out of memory for a frame");
            return;
        }
        AsyncWebServerResponse* res =
            req->beginResponse_P(200, "image/jpeg", copy, len);
        res->addHeader("Cache-Control", "no-store");
        req->onDisconnect([copy]() { free(copy); });
        req->send(res);
    });
#endif

    // ---- OTA: new firmware over WiFi, no cable ------------------------
    //
    // The partition table already has two app slots (min_spiffs.csv: app0 and
    // app1, 1.875 MB each), so this writes the one that is NOT running and
    // switches to it at reboot. A failed or half-sent update therefore cannot
    // brick the board: the old firmware is still in the other slot, untouched,
    // and it is what boots if the new image never validates.
    //
    // Refused while the module is MOVING. Writing flash blocks for milliseconds
    // at a time, which is exactly what makes a servo loop stutter, and a show
    // interrupted by a reboot is worse than an update that waited.
    server_.on("/api/ota", HTTP_POST,
        [this](AsyncWebServerRequest* req) {
            bool ok = req->_tempObject != nullptr;
            if (ok) {
                req->send(200, "text/plain",
                          "OK updated, rebooting into the new firmware");
                router_->requestReboot(600);
            } else {
                req->send(500, "text/plain",
                          otaErr_.length() ? otaErr_ : String("ERR update failed"));
            }
        },
        [this](AsyncWebServerRequest* req, String filename, size_t index,
               uint8_t* data, size_t len, bool final) {
            if (index == 0) {
                otaErr_ = "";
                bool force = req->hasParam("force") &&
                             req->getParam("force")->value() == "1";
                if (!force && router_->module() && router_->module()->busy()) {
                    otaErr_ = "ERR the module is moving — stop it first, or add force=1";
                    return;
                }
                if (!force && router_->seq() && router_->seq()->running()) {
                    otaErr_ = "ERR a sequence is playing — MOVE STOP first, or add force=1";
                    return;
                }
                Serial.println("[ota] receiving new firmware...");
                if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
                    otaErr_ = "ERR cannot start the update: " + String(Update.errorString());
                    return;
                }
            }
            if (otaErr_.length()) return;         // already refused this upload
            if (len && Update.write(data, len) != len) {
                otaErr_ = "ERR write failed: " + String(Update.errorString());
                Update.abort();
                return;
            }
            if (final) {
                if (Update.end(true)) {
                    Serial.printf("[ota] %u bytes written, rebooting\n",
                                  (unsigned)(index + len));
                    req->_tempObject = malloc(1);  // mark success
                } else {
                    otaErr_ = "ERR update did not finish: " + String(Update.errorString());
                }
            }
        });

    server_.onNotFound([](AsyncWebServerRequest* req) {
        req->send(404, "text/plain", "not found");
    });
}

void WebPortal::loop() {
    if (wifiModeCfg_ == "off") return;
    uint32_t now = millis();

    if (serverStarted_ && now - lastPush_ >= 500) {
        lastPush_ = now;
        ws_.cleanupClients();
        if (ws_.count()) ws_.textAll(statusJson());
    }

    // pick up SET NAME without a reboot: rename hostname/AP/mDNS to match
    if (now - lastHostCheck_ >= 2000) {
        lastHostCheck_ = now;
        router_->lock(); // identity strings can move under SET NAME
        String host = id_->hostname();
        router_->unlock();
        if (host != appliedHost_) applyHostname(host);
    }

    // a hostname change asked for the STA to come back up — do it here, on a
    // later pass, instead of blocking inside applyHostname()
    if (staRestartAt_ && (int32_t)(now - staRestartAt_) >= 0) {
        staRestartAt_ = 0;
        beginSta();          // networkUp() runs again once connected
    }

    // a scan, collected without blocking the loop. Purpose decides what the
    // results are for: 1 = the user asked, 2 = are we on the best link?
    if (scanState_) {
        int n = WiFi.scanComplete();
        if (n >= 0 && scanState_ == 2) {
            // Record the results for a WIFI SCAN too. The two scans share one
            // radio, so a link check that happens to be running is exactly
            // when a user asks — and silently eating the answer left them
            // polling "ask again in a moment" for ever.
            scanText_ = "OK " + String(n) + " network(s):";
            for (int i = 0; i < n && i < 12; i++) {
                scanText_ += " \"" + WiFi.SSID(i) + "\"(" + String(WiFi.RSSI(i)) + "dBm)";
            }
            checkLink(n);
            WiFi.scanDelete();
            scanState_ = 0;
        } else if (n >= 0) {
            scanText_ = "OK " + String(n) + " network(s):";
            for (int i = 0; i < n && i < 12; i++) {
                scanText_ += " \"" + WiFi.SSID(i) + "\"(" + String(WiFi.RSSI(i)) + "dBm)";
            }
            if (!n) scanText_ += " none — 2.4GHz only, is the hotspot on?";
            WiFi.scanDelete();
            scanState_ = 0;
        } else if (n == WIFI_SCAN_FAILED) {
            scanText_ = "ERR scan failed";
            scanState_ = 0;
        } else if (now - scanAt_ >= SCAN_TIMEOUT_MS) {
            // A scan can simply never finish — most often when the radio is
            // still settling right after boot. Without this the module answers
            // "ask again in a moment" for ever and the state machine stays
            // parked, because the whole of it waits for scanState_ to clear.
            // Say so and let the caller try again.
            WiFi.scanDelete();
            scanText_ = "ERR the scan did not finish — try again in a moment";
            scanState_ = 0;
        }
        // Scanning REQUIRES dropping the connection (esp_wifi_scan_start
        // refuses while a connect is in flight), so a scan is a deliberate
        // interruption of the link and has to be undone properly.
        //
        // Bare WiFi.begin() was not enough: wstate_ stayed W_ONLINE the whole
        // time, so the module reported "online" while holding no address at
        // all — seen on the bench as
        //     state=online ssid="manny" ip=0.0.0.0
        // and the hub could not reach it. Go back through beginSta() so the
        // state machine re-establishes the link the same way it does at boot,
        // including the DHCP re-arm and the connect timeout.
        if (!scanState_) {
            WiFi.setAutoReconnect(true);     // the scan is over; normal service
            if (wifiModeCfg_ == "on" && WiFi.status() != WL_CONNECTED) beginSta();
        }
    }

    // Is there a better link than the one we are on?
    //
    // A weak WiFi does not fail, it just performs badly: commands arrive late
    // and a show stutters. So a module far from the router leans on a nearer
    // module's hotspot instead. Falling back only when the connect FAILS never
    // catches this case. wifilink::decide() holds the rule and is unit-tested
    // on a PC, because a real -80 dBm signal cannot be produced on a bench.
    if (wifiModeCfg_ == "on" && serverStarted_ && !scanState_ &&
        wstate_ != W_CONNECTING && wstate_ != W_DIAGNOSING &&
        now - lastLinkCheck_ >= LINK_CHECK_MS) {
        lastLinkCheck_ = now;
        int rssi = (wstate_ == W_ONLINE && !onRelay_) ? WiFi.RSSI() : 0;
        // No known peers means nothing to lean on, so scanning would only
        // ever answer "stay". That is not free: a scan drops the link for a
        // moment and fights any scan the user asked for. On a weak network
        // with no neighbours it fired every 60 s for nothing, and WIFI SCAN
        // kept coming back "ERR scan failed" because the two collided.
        bool worthLooking = onRelay_ || peers_.count() > 0;
        if (worthLooking && (onRelay_ || rssi == 0 || rssi < wifilink::WEAK_RSSI)) {
            WiFi.scanDelete();
            // Same rule as WIFI SCAN: only stand the radio down when it is
            // CONNECTING. Disconnecting a live link aborts the very scan we
            // just asked for, because the disconnect event arrives after it.
            if (WiFi.status() != WL_CONNECTED) {
                WiFi.setAutoReconnect(false);
                WiFi.disconnect(false, false);
            }
            if (WiFi.scanNetworks(true) != WIFI_SCAN_FAILED) { scanState_ = 2; scanAt_ = now; }
            else WiFi.setAutoReconnect(true);
        }
    }

    // While a scan is running the radio is DELIBERATELY disconnected — the
    // ESP32 refuses to scan with a connect in flight. None of the recovery
    // paths below may act on that, because WiFi.begin() aborts a scan that is
    // already running. That is what made every scan come back "0 networks":
    // the W_ONLINE watchdog saw "not connected", helpfully re-joined, and
    // killed the scan it knew nothing about.
    //
    // Everything above this line still runs: status pushes, the hostname
    // check, and collecting the scan itself.
    if (scanState_) return;

    switch (wstate_) {
        case W_CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                apMode_ = false;
                wstate_ = W_ONLINE;
                // the AP deliberately STAYS up: that is how a module out of
                // router range gets on the network through this one
                Serial.printf("[wifi] connected, ip=%s — still sharing AP \"%s\"\n",
                              WiFi.localIP().toString().c_str(), WiFi.softAPSSID().c_str());
                networkUp();
            } else if (now - wstateAt_ >= WIFI_CONNECT_TIMEOUT_MS) {
                startDiagnostic();
            }
            break;

        case W_DIAGNOSING: {
            int n = WiFi.scanComplete();
            if (n >= 0) {
                finishDiagnostic(n);
                startAp();
            } else if (n == WIFI_SCAN_FAILED || now - wstateAt_ >= 10000) {
                WiFi.scanDelete();
                startAp();
            }
            break;
        }

        case W_AP:
            // the AP is only a fallback in "on" mode: the real network may
            // appear later (hotspot turned on after boot), keep retrying
            if (wifiModeCfg_ == "on") {
                if (WiFi.status() == WL_CONNECTED) {
                    apMode_ = false;
                    wstate_ = W_ONLINE;
                    Serial.printf("[wifi] joined \"%s\" late, ip=%s (fallback AP stays up)\n",
                                  staSsid_.c_str(), WiFi.localIP().toString().c_str());
                    networkUp();
                } else if (now - lastStaRetry_ >= 60000) {
                    lastStaRetry_ = now;
                    WiFi.begin(staSsid_.c_str(), staPass_.length() ? staPass_.c_str() : nullptr);
                }
            }
            break;

        case W_ONLINE:
            // STA dropped? try to get back on the network.
            //
            // "connected" is not enough: after a scan the link can come back
            // associated but with NO address, and the module then reports
            // itself online while nothing can reach it — the bench showed
            // `state=online ... ip=0.0.0.0`. An address is what actually makes
            // it reachable, so that is what is checked.
            if (now - lastWifiCheck_ >= 10000) {
                lastWifiCheck_ = now;
                bool noIp = (uint32_t)WiFi.localIP() == 0;
                if (WiFi.status() != WL_CONNECTED || noIp) {
                    Serial.printf("[wifi] link lost (%s) — re-establishing\n",
                                  noIp ? "no address" : "disconnected");
                    beginSta();       // full re-join, not a bare reconnect
                }
            }
            break;

        default:
            break;
    }
}
