#include "core/SecureTalk.h"
#include "core/AudioPlayer.h"        // MICE_HAS_AUDIO, one definition
#include "core/AudioStream.h"
#include "core/Log.h"

#if MICE_HAS_AUDIO && defined(MICE_TALK)

#include "core/UserStore.h"
#include "web/CastJs.h"
#include "web/MiceCss.h"
#include "web/TalkUI.h"
#include <Preferences.h>
#include <WiFi.h>
#include <esp_https_server.h>
#include <lwip/sockets.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/pk.h>
#include <mbedtls/x509_crt.h>

static httpd_handle_t srv = nullptr;
static String certPem, keyPem;         // must outlive the server: it keeps pointers
static volatile int audioFd = -1;      // the signed-in socket that feeds the speaker
static volatile uint32_t lastUse = 0;

// ---- the certificate: made here once, kept in NVS -----------------------
static bool makeCert(String& why) {
    Preferences p;
    p.begin("talk", false);
    certPem = p.getString("crt", "");
    keyPem = p.getString("key", "");
    if (certPem.length() && keyPem.length()) { p.end(); return true; }

    mbedtls_pk_context key;
    mbedtls_entropy_context ent;
    mbedtls_ctr_drbg_context rng;
    mbedtls_x509write_cert crt;
    mbedtls_mpi serial;
    mbedtls_pk_init(&key);
    mbedtls_entropy_init(&ent);
    mbedtls_ctr_drbg_init(&rng);
    mbedtls_x509write_crt_init(&crt);
    mbedtls_mpi_init(&serial);
    const char* pers = "mice-talk";
    bool ok = false;
    unsigned char* buf = (unsigned char*)malloc(1600);
    do {
        if (!buf) { why = "no memory for the certificate"; break; }
        if (mbedtls_ctr_drbg_seed(&rng, mbedtls_entropy_func, &ent,
                                  (const unsigned char*)pers, strlen(pers))) { why = "rng"; break; }
        if (mbedtls_pk_setup(&key, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY)) ||
            mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(key),
                                mbedtls_ctr_drbg_random, &rng)) { why = "key"; break; }
        mbedtls_x509write_crt_set_version(&crt, MBEDTLS_X509_CRT_VERSION_3);
        mbedtls_x509write_crt_set_md_alg(&crt, MBEDTLS_MD_SHA256);
        mbedtls_x509write_crt_set_subject_key(&crt, &key);
        mbedtls_x509write_crt_set_issuer_key(&crt, &key);
        mbedtls_mpi_lset(&serial, (mbedtls_mpi_sint)(esp_random() & 0x7fffffff));
        if (mbedtls_x509write_crt_set_subject_name(&crt, "CN=mice robot") ||
            mbedtls_x509write_crt_set_issuer_name(&crt, "CN=mice robot") ||
            mbedtls_x509write_crt_set_serial(&crt, &serial) ||
            mbedtls_x509write_crt_set_validity(&crt, "20260101000000", "20460101000000")) {
            why = "certificate fields"; break;
        }
        memset(buf, 0, 1600);
        if (mbedtls_x509write_crt_pem(&crt, buf, 1600, mbedtls_ctr_drbg_random, &rng)) {
            why = "certificate"; break;
        }
        certPem = String((const char*)buf);
        memset(buf, 0, 1600);
        if (mbedtls_pk_write_key_pem(&key, buf, 1600)) { why = "key pem"; break; }
        keyPem = String((const char*)buf);
        ok = true;
    } while (false);
    if (buf) { memset(buf, 0, 1600); free(buf); }
    mbedtls_mpi_free(&serial);
    mbedtls_x509write_crt_free(&crt);
    mbedtls_ctr_drbg_free(&rng);
    mbedtls_entropy_free(&ent);
    mbedtls_pk_free(&key);
    if (ok) {
        p.putString("crt", certPem);
        p.putString("key", keyPem);
        LOGF(sys, "talk: made this board's own certificate");
    }
    p.end();
    return ok;
}

// ---- pages ---------------------------------------------------------------
static esp_err_t sendP(httpd_req_t* req, const char* type, const char* body, bool cache) {
    lastUse = millis();
    httpd_resp_set_type(req, type);
    if (cache) httpd_resp_set_hdr(req, "Cache-Control", "max-age=86400");
    return httpd_resp_send(req, body, HTTPD_RESP_USE_STRLEN);
}
static esp_err_t pageTalk(httpd_req_t* r) { return sendP(r, "text/html", TALK_UI_HTML, false); }
static esp_err_t pageCast(httpd_req_t* r) { return sendP(r, "text/javascript", CAST_JS, true); }
static esp_err_t pageCss(httpd_req_t* r) { return sendP(r, "text/css", MICE_CSS, true); }
static esp_err_t pageRoot(httpd_req_t* req) {
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "/talk");
    return httpd_resp_send(req, nullptr, 0);
}

static void wsSay(httpd_req_t* req, const char* text) {
    httpd_ws_frame_t f = {};
    f.type = HTTPD_WS_TYPE_TEXT;
    f.payload = (uint8_t*)text;
    f.len = strlen(text);
    httpd_ws_send_frame(req, &f);
}

// ---- the sound socket ----------------------------------------------------
// Text: LOGIN <user> <pass>, then START <rate>, STOP. Binary: 16-bit LE mono
// PCM, only from the signed-in socket. The newest login wins the speaker.
static esp_err_t wsAudio(httpd_req_t* req) {
    if (req->method == HTTP_GET) return ESP_OK;          // the handshake
    lastUse = millis();
    AudioStream* st = AudioStream::instance();
    httpd_ws_frame_t f = {};
    esp_err_t e = httpd_ws_recv_frame(req, &f, 0);       // length first
    if (e != ESP_OK) return e;
    const int fd = httpd_req_to_sockfd(req);
    if (f.type == HTTPD_WS_TYPE_CLOSE) {
        if (fd == audioFd) { if (st) st->wsClose(); audioFd = -1; }
        return ESP_OK;
    }
    if (!f.len || f.len > 16384) return ESP_OK;
    uint8_t* buf = (uint8_t*)malloc(f.len + 1);
    if (!buf) return ESP_ERR_NO_MEM;
    f.payload = buf;
    e = httpd_ws_recv_frame(req, &f, f.len);
    if (e != ESP_OK) { free(buf); return e; }
    if (f.type == HTTPD_WS_TYPE_TEXT) {
        buf[f.len] = 0;
        String t((const char*)buf);
        memset(buf, 0, f.len);                           // the password was in it
        if (t.startsWith("LOGIN ")) {
            int sp = t.indexOf(' ', 6);
            String u = sp > 0 ? t.substring(6, sp) : "";
            String pw = sp > 0 ? t.substring(sp + 1) : "";
            if (u.length() && users.verify(u, pw)) {
                audioFd = fd;
                wsSay(req, "OK");
            } else {
                wsSay(req, "ERR wrong user or password");
                LOGF(sys, "talk: login refused for \"%s\"", u.c_str());
            }
        } else if (t.startsWith("START")) {
            if (fd != audioFd) wsSay(req, "ERR log in first");
            else if (!st) wsSay(req, "ERR no speaker on this board");
            else { st->wsOpen((uint32_t)t.substring(5).toInt()); wsSay(req, "OK"); }
        } else if (t.startsWith("STOP") && fd == audioFd && st) {
            st->wsClose();
        }
    } else if (f.type == HTTPD_WS_TYPE_BINARY && fd == audioFd && st) {
        st->push(buf, f.len);
    }
    free(buf);
    return ESP_OK;
}

// A phone that walks out of range never sends CLOSE: the socket just goes.
// The server calls this for every socket it drops, so the speaker is freed.
static void onClose(httpd_handle_t, int fd) {
    if (fd == audioFd) {
        AudioStream* st = AudioStream::instance();
        if (st) st->wsClose();
        audioFd = -1;
    }
    close(fd);
}

// THE FIRST TALK ON REBOOTED THE BOARD (real nong, 2026-09-28): no reply on
// RS485 and more heap free afterwards. mbedtls_x509write_crt_pem alone puts a
// 4 KB buffer on the stack, plus the ECDSA signature, and the command ran on
// the 8 KB loop task - a stack overflow. So the heavy part (certificate and
// TLS server) runs in its own task with room, and TALK ON answers at once;
// TALK? then says "starting", "on" or why it failed.
static volatile bool starting = false;
static String failWhy;

static bool startNow(String& why);

static void startTask(void*) {
    String why;
    if (!startNow(why)) {
        failWhy = why;
        LOGF(sys, "talk: %s", why.c_str());
    }
    starting = false;
    vTaskDelete(nullptr);
}

bool SecureTalk::start(String& why) {
    if (srv || starting) return true;
    if (!AudioStream::instance()) { why = "no speaker on this board"; return false; }
    if (ESP.getFreeHeap() < MIN_HEAP) {
        why = "not enough memory for the secure page (" + String(ESP.getFreeHeap()) + " bytes free)";
        return false;
    }
    failWhy = "";
    starting = true;
    if (xTaskCreate(startTask, "talk", TASK_STACK, nullptr, 1, nullptr) != pdPASS) {
        starting = false;
        why = "no memory to start it";
        return false;
    }
    return true;
}

static bool startNow(String& why) {
    if (!makeCert(why)) { why = "could not make the certificate: " + why; return false; }

    httpd_ssl_config_t cfg = HTTPD_SSL_CONFIG_DEFAULT();
    cfg.cacert_pem = (const uint8_t*)certPem.c_str();
    cfg.cacert_len = certPem.length() + 1;
    cfg.prvtkey_pem = (const uint8_t*)keyPem.c_str();
    cfg.prvtkey_len = keyPem.length() + 1;
    cfg.httpd.max_open_sockets = 3;    // the page, its files, and the sound socket
    cfg.httpd.ctrl_port = 32770;       // clear of any other esp_http_server
    cfg.httpd.close_fn = onClose;
    cfg.httpd.lru_purge_enable = true;
    esp_err_t e = httpd_ssl_start(&srv, &cfg);
    if (e != ESP_OK) {
        srv = nullptr;
        why = "the secure server did not start (" + String(esp_err_to_name(e)) + ")";
        return false;
    }
    static const httpd_uri_t uris[] = {
        {"/", HTTP_GET, pageRoot, nullptr, false, false, nullptr},
        {"/talk", HTTP_GET, pageTalk, nullptr, false, false, nullptr},
        {"/cast.js", HTTP_GET, pageCast, nullptr, false, false, nullptr},
        {"/mice.css", HTTP_GET, pageCss, nullptr, false, false, nullptr},
        {"/ws/audio", HTTP_GET, wsAudio, nullptr, true, false, nullptr},
    };
    for (const auto& u : uris) httpd_register_uri_handler(srv, &u);
    lastUse = millis();
    LOGF(sys, "talk: secure page up, %u bytes free", ESP.getFreeHeap());
    return true;
}

void SecureTalk::stop() {
    if (!srv) return;
    httpd_ssl_stop(srv);
    srv = nullptr;
    if (audioFd >= 0) {
        AudioStream* st = AudioStream::instance();
        if (st) st->wsClose();
        audioFd = -1;
    }
    LOGF(sys, "talk: secure page off");
}

bool SecureTalk::running() { return srv != nullptr; }

void SecureTalk::loop() {
    // off after a long quiet spell - but never while a phone is talking
    if (srv && audioFd < 0 && millis() - lastUse > IDLE_MS) stop();
}

String SecureTalk::status() {
    String ip = WiFi.getMode() & WIFI_MODE_STA && WiFi.status() == WL_CONNECTED
              ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
    String state = srv ? "on https://" + ip + "/talk"
                 : starting ? String("starting")
                 : failWhy.length() ? "off (failed: " + failWhy + ")" : String("off");
    return String("TALK ") + state
         + (audioFd >= 0 ? " talking" : "") + " heap=" + String(ESP.getFreeHeap());
}

#else   // not in this build (MICE_TALK, platformio.ini): same API, honest answers

bool SecureTalk::start(String& why) { why = "this board type has no secure talk page yet"; return false; }
void SecureTalk::stop() {}
bool SecureTalk::running() { return false; }
void SecureTalk::loop() {}
String SecureTalk::status() { return "TALK off (not in this build)"; }

#endif  // MICE_HAS_AUDIO && MICE_TALK
