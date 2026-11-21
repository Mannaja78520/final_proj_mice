#include "core/MeshLink.h"
#include "core/CommandRouter.h"
#include "core/Identity.h"
#include "core/Log.h"
#include "core/MeshLogic.h"
#include <WiFi.h>
#include <Preferences.h>
#include <esp_now.h>
#include <esp_random.h>
#include <mbedtls/md.h>

namespace {
Identity* g_id = nullptr;
CommandRouter* g_router = nullptr;
mesh::MeshNode* g_node = nullptr;
String g_key;
bool g_up = false;
std::function<void(const String&)> g_reply;
// A command is sent again, up to 3 times in all, until its answer comes back
// (model: 100 boards answered 16/20 with one try and 20/20 with three).
struct Wait { uint8_t dst = 0; char cmd[mesh::MAX_PAYLOAD + 1]; uint8_t tries = 0; uint32_t at = 0; bool used = false; };
Wait g_wait[4];
const uint32_t RETRY_MS = 900;
const uint8_t MAX_TRIES = 3;
uint32_t g_tx = 0, g_rx = 0, g_bad = 0, g_dup = 0, g_fwd = 0, g_cmds = 0;
const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// The radio callback only copies: everything else happens in loop(), on the
// same task as the RS485 and USB commands (the router is not re-entrant).
struct Slot { uint8_t b[mesh::MAX_FRAME]; uint8_t n = 0; };
Slot g_q[8];
volatile uint8_t g_qh = 0, g_qt = 0;

void IRAM_ATTR onRecv(const uint8_t*, const uint8_t* data, int len) {
    if (len <= 0 || len > (int)mesh::MAX_FRAME) return;
    uint8_t next = (g_qt + 1) & 7;
    if (next == g_qh) return;                       // queue full: drop (the sender will not know, as on any radio)
    memcpy(g_q[g_qt].b, data, len);
    g_q[g_qt].n = (uint8_t)len;
    g_qt = next;
}

void hmacTag(const uint8_t* key, size_t kl, const uint8_t* d, size_t n, uint8_t out[8]) {
    uint8_t full[32];
    mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), key, kl, d, n, full);
    memcpy(out, full, 8);
}
uint32_t rng() { return esp_random(); }

bool startRadio() {
    if (esp_now_init() != ESP_OK) return false;
    esp_now_peer_info_t p = {};
    memcpy(p.peer_addr, BROADCAST, 6);
    p.channel = 0;                                  // whatever channel the radio is on now
    p.encrypt = false;                              // broadcast cannot be encrypted: the frame tag signs it instead
    if (esp_now_add_peer(&p) != ESP_OK) return false;
    esp_now_register_recv_cb(onRecv);
    return true;
}
}  // namespace

bool MeshLink::enabled() { return g_id && g_id->meshMode() == "on"; }

void MeshLink::begin(Identity* id, CommandRouter* router) {
    g_id = id;
    g_router = router;
}

void MeshLink::onReply(std::function<void(const String&)> cb) { g_reply = cb; }

void MeshLink::loop() {
    if (!enabled()) return;
    if (!g_id->group().length()) return;            // no group, no key: never mesh with strangers
    if (!g_up) {
        static uint32_t lastTry = 0;
        if (millis() - lastTry < 2000) return;      // the radio may not be started yet
        lastTry = millis();
        if (WiFi.getMode() == WIFI_OFF) return;
        g_key = g_id->apPassword();
        mesh::Config c;
        c.id = g_id->id();
        c.key = (const uint8_t*)g_key.c_str();
        c.keyLen = g_key.length();
        c.tag = hmacTag;
        c.rng = rng;
        {   // seq must rise on every boot: keep a base in flash, step it by 65536 per start
            Preferences pr; pr.begin("mesh", false);
            uint32_t base = pr.getUInt("seq", 0) + 65536;
            pr.putUInt("seq", base); pr.end();
            c.seqStart = base ? base : 65536;
        }
        delete g_node;
        g_node = new mesh::MeshNode(c);
        g_up = startRadio();
        LOGF(wifi, "mesh %s on channel %d", g_up ? "up" : "could not start", (int)WiFi.channel());
        return;
    }
    while (g_qh != g_qt) {                          // frames heard
        Slot& s = g_q[g_qh];
        mesh::RxResult r = g_node->rx(s.b, s.n, millis());
        g_qh = (g_qh + 1) & 7;
        g_rx++;
        if (r == mesh::RX_BAD) g_bad++;
        else if (r == mesh::RX_DROPPED_DUP) g_dup++;
        else if (r == mesh::RX_FORWARDING) g_fwd++;
    }
    mesh::Delivery d;
    while (g_node->nextDelivery(d)) {               // frames for this board
        if (d.type == mesh::TYPE_CMD) {
            g_cmds++;
            String reply = g_router->handle(String(d.payload));
            if (reply.length() > mesh::MAX_PAYLOAD) reply = reply.substring(0, mesh::MAX_PAYLOAD - 3) + "...";
            g_node->send(d.src, mesh::TYPE_REPLY, reply.c_str(), reply.length(), millis());
        } else {
            for (auto& w : g_wait) if (w.used && w.dst == d.src) w.used = false;   // answered
            if (g_reply) g_reply("@" + String(d.src) + " " + String(d.payload));
        }
    }
    for (auto& w : g_wait) {                        // unanswered commands go out again
        if (!w.used || millis() - w.at < RETRY_MS) continue;
        if (w.tries >= MAX_TRIES) { w.used = false; continue; }
        if (g_node->send(w.dst, mesh::TYPE_CMD, w.cmd, strlen(w.cmd), millis())) { w.tries++; w.at = millis(); }
    }
    uint8_t out[mesh::MAX_FRAME];                   // frames due on air
    size_t n = g_node->poll(millis(), out, sizeof out);
    if (n && esp_now_send(BROADCAST, out, n) == ESP_OK) g_tx++;
}

String MeshLink::command(const String& dst, const String& cmd) {
    if (!enabled()) return "ERR mesh is off (SET MESH ON, needs a group)";
    if (!g_up || !g_node) return "ERR mesh is not up yet (radio starting, or no group)";
    int to = dst == "*" ? 0 : dst.toInt();
    if (dst != "*" && (to < 1 || to > 247)) return "ERR usage: MESH <id 1-247|*> <command>";
    if (!g_node->send((uint8_t)to, mesh::TYPE_CMD, cmd.c_str(), cmd.length(), millis()))
        return "ERR mesh is busy, try again";
    if (to != 0) {                                  // remember it so it can be sent again if no answer comes
        for (auto& w : g_wait) if (!w.used || w.dst == to) {
            w.used = true; w.dst = (uint8_t)to; w.tries = 1; w.at = millis();
            strncpy(w.cmd, cmd.c_str(), mesh::MAX_PAYLOAD); w.cmd[mesh::MAX_PAYLOAD] = 0;
            break;
        }
    }
    return "OK sent through the mesh to " + dst + " (the answer arrives as @" + dst + " ...)";
}

String MeshLink::status() {
    String s = "MESH mode=" + (g_id ? g_id->meshMode() : String("off")) + " up=" + String(g_up ? 1 : 0);
    if (g_up) s += " channel=" + String((int)WiFi.channel());
    s += " tx=" + String(g_tx) + " rx=" + String(g_rx) + " repeated=" + String(g_fwd) +
         " dup=" + String(g_dup) + " refused=" + String(g_bad) + " commands=" + String(g_cmds);
    return s;
}
