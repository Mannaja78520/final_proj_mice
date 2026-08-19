#pragma once
#include <Arduino.h>
#include <vector>

class Identity;

// Finds the other modules on the WiFi network via mDNS so every module's
// website can act as the "main" site: it lists the whole fleet and links to
// each module's own page.
//
// Each module advertises the service _module._tcp on port 80 with TXT records
// id/name/type. A low-priority background task rescans every ~20 s
// (MDNS.queryService blocks ~3 s, which is why it cannot run on loopTask).
class PeerDiscovery {
public:
    struct Peer {
        int id = 0;
        String name, type, ip;
    };

    void begin(Identity* id);
    // (re)publish the _module._tcp service + id/name/type TXT records;
    // must be called again after MDNS.end()/begin() (e.g. rename)
    void announce();

    // JSON array, self first: [{"id":1,"name":"...","type":"...","ip":"...","self":true}, ...]
    // Caller must hold the router mutex (identity strings are read here).
    String peersJson(const String& selfIp);

    // Look a peer up by ip, name or bus id — how REACH turns "the nong" into
    // an address without the caller having to know where it ended up.
    bool find(const String& key, Peer& out);

    // How many other modules this one has seen. Zero means there is nothing
    // to lean on, so the weak-link check has no reason to scan at all.
    size_t count();

private:
    Identity* id_ = nullptr;
    std::vector<Peer> peers_;
    SemaphoreHandle_t mtx_ = nullptr;

    static void taskEntry(void* arg);
    void taskLoop();
    void scanAp(std::vector<Peer>& found);   // modules on OUR access point
    bool probe(const String& ip, Peer& out); // is there a module at this ip?
};
