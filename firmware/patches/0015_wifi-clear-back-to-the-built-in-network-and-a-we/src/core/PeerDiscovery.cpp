#include "core/PeerDiscovery.h"
#include "core/Identity.h"
#include "core/Util.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

static const char* SVC = "module";
static const char* PROTO = "tcp";

void PeerDiscovery::begin(Identity* id) {
    id_ = id;
    mtx_ = xSemaphoreCreateMutex();
    announce();
    // the scan itself no-ops until STA is connected (may join late)
    xTaskCreate(taskEntry, "peerscan", 4096, this, 1, nullptr);
}

void PeerDiscovery::announce() {
    // advertise ourselves so the other modules' fleet pages can find us
    MDNS.addService(SVC, PROTO, 80);
    MDNS.addServiceTxt(SVC, PROTO, "id", String(id_->id()).c_str());
    MDNS.addServiceTxt(SVC, PROTO, "name", id_->name().c_str());
    MDNS.addServiceTxt(SVC, PROTO, "type", id_->type().c_str());
}

void PeerDiscovery::taskEntry(void* arg) {
    static_cast<PeerDiscovery*>(arg)->taskLoop();
}

// Ask one address whether a module lives there. Used for the boards sitting on
// our own AP, which mDNS does not find (see scanAp).
bool PeerDiscovery::probe(const String& ip, Peer& out) {
    HTTPClient http;
    http.setConnectTimeout(400);
    http.setTimeout(400);
    if (!http.begin("http://" + ip + "/api/status")) return false;
    int code = http.GET();
    String body = code == 200 ? http.getString() : String("");
    http.end();
    if (!body.length()) return false;

    JsonDocument doc;
    if (deserializeJson(doc, body)) return false;
    if (!doc["id"].is<int>() || !doc["type"].is<const char*>()) return false;
    out.ip = ip;
    out.id = doc["id"] | 0;
    out.name = doc["name"] | ip;
    out.type = doc["type"] | "?";
    return true;
}

// The modules that joined OUR access point.
//
// mDNS does not find these. A module out of router range connects to a nearby
// module's AP and lives on its private 192.168.4.x subnet; queryService only
// asks on the station interface, so the host module never saw the very boards
// depending on it. Found on the bench: REACH by ip worked, by name did not,
// because PEERS came back with only the module itself in it.
//
// The DHCP pool here starts at 192.168.4.2 and this only runs when clients are
// actually associated, so it is a handful of short probes, on a background
// task, and nothing at all in the normal case.
void PeerDiscovery::scanAp(std::vector<Peer>& found) {
    int clients = WiFi.softAPgetStationNum();
    if (clients <= 0) return;
    String base = WiFi.softAPIP().toString();
    int dot = base.lastIndexOf('.');
    if (dot < 0) return;
    base = base.substring(0, dot + 1);
    // a couple past the client count, so a lease that skipped an address
    // (a client that left and rejoined) is still found
    int last = clients + 3;
    if (last > 8) last = 8;
    for (int i = 2; i <= last + 1; i++) {
        Peer p;
        if (!probe(base + String(i), p)) continue;
        if (p.id == id_->id()) continue;                 // that is us
        bool dup = false;
        for (auto& e : found) if (e.id == p.id) { dup = true; break; }
        if (!dup) found.push_back(p);
    }
}

void PeerDiscovery::taskLoop() {
    for (;;) {
        std::vector<Peer> found;
        // mDNS across the show network — only meaningful once we are on it
        if (WiFi.status() == WL_CONNECTED) {
            int n = MDNS.queryService(SVC, PROTO); // blocks a few seconds
            for (int i = 0; i < n; i++) {
                Peer p;
                p.ip = MDNS.IP(i).toString();
                p.id = MDNS.hasTxt(i, "id") ? MDNS.txt(i, "id").toInt() : 0;
                p.name = MDNS.hasTxt(i, "name") ? MDNS.txt(i, "name") : MDNS.hostname(i);
                p.type = MDNS.txt(i, "type");
                if (p.id == id_->id()) continue; // self is added by peersJson
                if (p.ip == "0.0.0.0") continue;
                found.push_back(p);
            }
        }
        // ...and the modules leaning on us. This runs whatever the STA is
        // doing: in AP mode there is no station at all, and those are exactly
        // the modules that have nobody else to be found by.
        scanAp(found);

        xSemaphoreTake(mtx_, portMAX_DELAY);
        peers_ = found;
        xSemaphoreGive(mtx_);
        vTaskDelay(pdMS_TO_TICKS(20000));
    }
}

// An ip is used as-is; anything else is matched against the peers this module
// has discovered, by name or by bus id. Names are matched case-insensitively
// because "Nong" and "nong" are the same module to anyone typing it.
bool PeerDiscovery::find(const String& key, Peer& out) {
    String k = key;
    k.trim();
    if (!k.length()) return false;
    // an ip needs no lookup — it may be a module this one has not discovered
    bool looksIp = true;
    int dots = 0;
    for (unsigned i = 0; i < k.length(); i++) {
        if (k[i] == '.') dots++;
        else if (!isdigit(k[i])) { looksIp = false; break; }
    }
    if (looksIp && dots == 3) { out.ip = k; out.name = k; return true; }

    String lower = k;
    lower.toLowerCase();
    xSemaphoreTake(mtx_, portMAX_DELAY);
    bool got = false;
    for (auto& p : peers_) {
        String pn = p.name;
        pn.toLowerCase();
        if (pn == lower || (k.toInt() && p.id == k.toInt())) {
            out = p;
            got = true;
            break;
        }
    }
    xSemaphoreGive(mtx_);
    return got;
}

String PeerDiscovery::peersJson(const String& selfIp) {
    String out = "[{\"id\":" + String(id_->id()) +
                 ",\"name\":\"" + Util::jsonEscape(id_->name()) +
                 "\",\"type\":\"" + id_->type() +
                 "\",\"ip\":\"" + selfIp + "\",\"self\":true}";
    xSemaphoreTake(mtx_, portMAX_DELAY);
    for (auto& p : peers_) {
        out += ",{\"id\":" + String(p.id) +
               ",\"name\":\"" + Util::jsonEscape(p.name) +
               "\",\"type\":\"" + Util::jsonEscape(p.type) +
               "\",\"ip\":\"" + p.ip + "\",\"self\":false}";
    }
    xSemaphoreGive(mtx_);
    return out + "]";
}
