#pragma once
#include <Arduino.h>

// A small HTTPS server with one job: let a PHONE send its microphone to the
// robot with no hub (user 2026-09-28).
//
// A phone browser only gives getUserMedia to a secure page, and the board's
// own page is plain http, so the microphone switch there could never work.
// This raises https://<board>/talk: the same sound engine (cast.js), a login
// on the socket itself, and a WebSocket at /ws/audio that feeds the very same
// AudioStream the http socket and the hub's UDP feed.
//
// ON DEMAND ONLY (TALK ON / TALK OFF). A TLS connection costs this chip tens
// of kilobytes of RAM, so the server is not up while nobody talks, and it
// shuts itself after IDLE_MS with no sound. The certificate is made ON the
// board the first time (a fresh P-256 key, kept in NVS), so no private key
// lives in the source; the phone warns once, because nobody vouches for a
// certificate a robot made for itself - that is expected, and the link is
// still encrypted.
class SecureTalk {
public:
    static const uint32_t IDLE_MS = 10UL * 60UL * 1000UL;
    static const uint32_t MIN_HEAP = 60000;   // below this, refuse rather than crash

    static bool start(String& why);   // TALK ON
    static void stop();               // TALK OFF
    static bool running();
    static void loop();               // the idle shut-off; from WebPortal::loop
    static String status();           // TALK / TALK?
};
