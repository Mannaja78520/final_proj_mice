#include "core/WebPortal.h"
#include "core/CommandRouter.h"
#include "core/Identity.h"
#include "core/RS485Bus.h"
#include "core/SDStore.h"
#include "core/Util.h"
#include "web/WebUI.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <SD.h>
#include <config.h>
#include <memory>

void WebPortal::begin(Identity* id, CommandRouter* router, SDStore* sd, RS485Bus* rs485) {
    id_ = id;
    router_ = router;
    sd_ = sd;
    rs485_ = rs485;
    wifiModeCfg_ = id_->wifiMode();
    staSsid_ = id_->wifiSsid().length() ? id_->wifiSsid() : String(WIFI_SSID);
    staPass_ = id_->wifiSsid().length() ? id_->wifiPass() : String(WIFI_PASS);
    appliedHost_ = id_->hostname();

    if (wifiModeCfg_ == "off") {
        WiFi.mode(WIFI_OFF);
        Serial.println("[wifi] disabled — USB/RS485 only (SET WIFI ON to re-enable)");
        return;
    }

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

    if (wifiModeCfg_ == "ap") startAp();
    else beginSta();

    setupRoutes();
    server_.begin();
    serverStarted_ = true;
}

void WebPortal::beginSta() {
    // core 2.x: the hostname must be stored BEFORE mode(WIFI_STA) creates the
    // interface — the core applies it on the STA_START event, ahead of the
    // DHCP request. Set any later and the router sees "esp32-XXXXXX".
    WiFi.setHostname(appliedHost_.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.config(IPAddress(0, 0, 0, 0), IPAddress(0, 0, 0, 0), IPAddress(0, 0, 0, 0)); // re-arm DHCP
    WiFi.begin(staSsid_.c_str(), staPass_.length() ? staPass_.c_str() : nullptr); // nullptr = open network
    wstate_ = W_CONNECTING;
    wstateAt_ = millis();
    Serial.printf("[wifi] connecting to \"%s\" as \"%s\" in the background — USB/RS485 already live\n",
                  staSsid_.c_str(), appliedHost_.c_str());
}

void WebPortal::startAp() {
    apMode_ = true;
    wstate_ = W_AP;
    wstateAt_ = millis();
    lastStaRetry_ = millis();
    String apName = appliedHost_.length() > 30 ? appliedHost_.substring(0, 30) : appliedHost_;
    WiFi.setHostname(appliedHost_.c_str());
    // AP_STA when the AP is only a fallback, so we can keep retrying STA
    WiFi.mode(wifiModeCfg_ == "ap" ? WIFI_AP : WIFI_AP_STA);
    WiFi.softAP(apName.c_str(), AP_FALLBACK_PASS);
    Serial.printf("[wifi] AP \"%s\" pass \"%s\" ip=%s\n",
                  apName.c_str(), AP_FALLBACK_PASS, WiFi.softAPIP().toString().c_str());
    networkUp();
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
        String apName = host.length() > 30 ? host.substring(0, 30) : host;
        WiFi.softAP(apName.c_str(), AP_FALLBACK_PASS); // rename the AP in place
        networkUp();
    } else {
        // a new hostname is only announced reliably when the STA interface is
        // recreated from scratch, exactly like at boot
        WiFi.disconnect(true); // also powers the STA off
        delay(150);
        beginSta(); // networkUp() runs again once connected
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
        String selfIp = apMode_ ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
        router_->lock(); // identity strings must not move while we copy them
        String out = peers_.peersJson(selfIp);
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

    switch (wstate_) {
        case W_CONNECTING:
            if (WiFi.status() == WL_CONNECTED) {
                apMode_ = false;
                wstate_ = W_ONLINE;
                Serial.printf("[wifi] connected, ip=%s\n", WiFi.localIP().toString().c_str());
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
            // STA dropped? try to get back on the network
            if (now - lastWifiCheck_ >= 10000) {
                lastWifiCheck_ = now;
                if (WiFi.status() != WL_CONNECTED) {
                    Serial.println("[wifi] reconnecting...");
                    WiFi.reconnect();
                }
            }
            break;

        default:
            break;
    }
}
