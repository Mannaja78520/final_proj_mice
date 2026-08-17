#include "core/PeerDiscovery.h"
#include "core/Identity.h"
#include "core/Util.h"
#include <WiFi.h>
#include <ESPmDNS.h>

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

void PeerDiscovery::taskLoop() {
    for (;;) {
        if (WiFi.status() == WL_CONNECTED) {
            int n = MDNS.queryService(SVC, PROTO); // blocks a few seconds
            std::vector<Peer> found;
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
            xSemaphoreTake(mtx_, portMAX_DELAY);
            peers_ = found;
            xSemaphoreGive(mtx_);
        }
        vTaskDelay(pdMS_TO_TICKS(20000));
    }
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
