#pragma once
// Multi-hop command forwarding with NO router and NO hotspot, as pure logic.
// No Arduino and no radio in this file, so it is unit-tested on a PC
// (`pio test -e native`) and driven by tools/bench/mesh_model.py with hundreds
// of nodes. MeshLink.cpp is the thin part that puts these frames on ESP-NOW.
//
// WHY (user 2026-11-21): without a router, boards of one company only formed
// small WiFi clusters of about 5 (hotspot join is one hop). ESP-NOW frames are
// not tied to a network at all, so a frame can be repeated by any board that
// hears it: a robot far from the PC is reached through the boards in between.
//
// THE FRAME (all multi-byte fields big-endian), at most 219 of ESP-NOW's 250 bytes:
//   0 magic 0xA7   1 type (0 command, 1 reply)   2 src id   3 dst id (0 = everyone)
//   4 ttl          5 hops                         6..9 seq   10 len   11.. payload   then tag[8]
// The ids are the module ids the RS485 bus already uses, so `#17 PING` and
// `MESH 17 PING` name the same board. ttl and hops change on every repeat, so the
// tag (HMAC of the group key, cut to 8 bytes) covers every byte EXCEPT those two.
//
// REPEATING without a storm: a board repeats a new frame once, after a random
// wait of 0..jitterMs, and not at all if it heard that same frame from
// `suppressK` other boards in the meantime (counter-based suppression; in a
// crowded room most boards stay quiet). A frame already seen (src+seq in a ring
// of 64) is dropped. A frame for this board is delivered and, unless it was
// addressed to everyone, not repeated.
//
// NOT covered, said plainly: a captured frame can be replayed by someone with a
// radio until it leaves the 64-entry ring (the seq starts from a random boot
// value, so a rebooted board is not confused with its old self). The group key is
// what keeps strangers out; there is no clock to expire frames with.
#include <stdint.h>
#include <string.h>

namespace mesh {

const uint8_t MAGIC = 0xA7;
const uint8_t TYPE_CMD = 0, TYPE_REPLY = 1;
const size_t HEADER = 11, TAG = 8, MAX_PAYLOAD = 200, MAX_FRAME = HEADER + MAX_PAYLOAD + TAG;

// keyed tag: out[0..7]. Firmware: HMAC-SHA256 (mbedtls). Tests: a stand-in.
typedef void (*TagFn)(const uint8_t* key, size_t klen, const uint8_t* data, size_t n, uint8_t out[8]);

enum RxResult { RX_DELIVERED, RX_FORWARDING, RX_DROPPED_DUP, RX_BAD, RX_OWN, RX_DONE };

struct Delivery {
    uint8_t type, src, hops, len;
    char payload[MAX_PAYLOAD + 1];
};

struct Config {
    uint8_t id = 0;
    uint8_t ttl = 20;              // how many repeats a frame may travel (model: 255 boards need ~19 hops)
    uint16_t jitterMs = 40;        // random wait before repeating
    uint8_t suppressK = 3;         // stay quiet after hearing the frame this many times (model: 2 loses too many)
    const uint8_t* key = nullptr;  // group key
    size_t keyLen = 0;
    TagFn tag = nullptr;
    uint32_t (*rng)() = nullptr;
};

class MeshNode {
public:
    explicit MeshNode(const Config& c) : c_(c) { seq_ = (c.rng ? (c.rng() & 0xFFFF) : 1) << 16; }

    // Queue a frame this board originates. Sent by poll() within a few ms.
    bool send(uint8_t dst, uint8_t type, const char* payload, size_t len, uint32_t now) {
        if (len > MAX_PAYLOAD) len = MAX_PAYLOAD;
        Pending* p = freeSlot();
        if (!p) return false;
        uint8_t* f = p->bytes;
        f[0] = MAGIC; f[1] = type; f[2] = c_.id; f[3] = dst; f[4] = c_.ttl; f[5] = 0;
        ++seq_;
        f[6] = seq_ >> 24; f[7] = seq_ >> 16; f[8] = seq_ >> 8; f[9] = seq_;
        f[10] = (uint8_t)len;
        memcpy(f + HEADER, payload, len);
        seal(f, HEADER + len);
        p->len = HEADER + len + TAG;
        p->active = true; p->own = true; p->dups = 0;
        p->dueAt = now + (c_.rng ? c_.rng() % 5 : 0);
        remember(c_.id, seq_);
        return true;
    }

    RxResult rx(const uint8_t* b, size_t n, uint32_t now) {
        if (n < HEADER + TAG || b[0] != MAGIC) return RX_BAD;
        size_t len = b[10];
        if (len > MAX_PAYLOAD || n != HEADER + len + TAG) return RX_BAD;
        if (!verify(b, HEADER + len)) return RX_BAD;
        uint8_t src = b[2], dst = b[3];
        uint32_t seq = ((uint32_t)b[6] << 24) | ((uint32_t)b[7] << 16) | ((uint32_t)b[8] << 8) | b[9];
        if (src == c_.id) return RX_OWN;
        if (seen(src, seq)) {                       // heard again: counts towards suppression
            for (auto& p : pend_)
                if (p.active && !p.own && p.src == src && p.seq == seq) p.dups++;
            return RX_DROPPED_DUP;
        }
        remember(src, seq);
        bool forMe = dst == c_.id || dst == 0;
        RxResult r = RX_DONE;
        if (forMe && (b[1] == TYPE_CMD || b[1] == TYPE_REPLY)) {
            if (dq_ < DQ) {
                Delivery& d = dlv_[(dh_ + dq_) % DQ];
                d.type = b[1]; d.src = src; d.hops = b[5] + 1; d.len = (uint8_t)len;
                memcpy(d.payload, b + HEADER, len); d.payload[len] = 0;
                dq_++;
                r = RX_DELIVERED;
            }
        }
        bool repeat = (dst != c_.id) && b[4] > 1;   // not only for us, and ttl left
        if (repeat) {
            Pending* p = freeSlot();
            if (p) {
                memcpy(p->bytes, b, n);
                p->bytes[4] = b[4] - 1; p->bytes[5] = b[5] + 1;
                p->len = n; p->active = true; p->own = false; p->dups = 0;
                p->src = src; p->seq = seq;
                p->dueAt = now + (c_.rng && c_.jitterMs ? c_.rng() % c_.jitterMs : 0);
                if (r == RX_DONE) r = RX_FORWARDING;
            }
        }
        return r;
    }

    // The next frame that is due to go on air, copied to `out`; 0 when none.
    size_t poll(uint32_t now, uint8_t* out, size_t cap) {
        for (auto& p : pend_) {
            if (!p.active || (int32_t)(now - p.dueAt) < 0) continue;
            p.active = false;
            if (!p.own && p.dups >= c_.suppressK) continue;   // enough neighbours already repeated it
            if (p.len > cap) continue;
            memcpy(out, p.bytes, p.len);
            return p.len;
        }
        return 0;
    }

    bool nextDelivery(Delivery& d) {
        if (!dq_) return false;
        d = dlv_[dh_]; dh_ = (dh_ + 1) % DQ; dq_--;
        return true;
    }
    const Config& config() const { return c_; }

private:
    struct Pending { uint8_t bytes[MAX_FRAME]; size_t len = 0; uint32_t dueAt = 0; uint8_t dups = 0, src = 0;
                     uint32_t seq = 0; bool active = false, own = false; };
    static const int PEND = 8, RING = 64, DQ = 4;
    Config c_;
    Pending pend_[PEND];
    uint32_t seq_ = 0;
    struct Seen { uint8_t src = 0; uint32_t seq = 0; bool used = false; } ring_[RING];
    int ringAt_ = 0;
    Delivery dlv_[DQ];
    int dh_ = 0, dq_ = 0;

    Pending* freeSlot() { for (auto& p : pend_) if (!p.active) return &p; return nullptr; }
    bool seen(uint8_t s, uint32_t q) const { for (auto& r : ring_) if (r.used && r.src == s && r.seq == q) return true; return false; }
    void remember(uint8_t s, uint32_t q) {
        ring_[ringAt_].src = s; ring_[ringAt_].seq = q; ring_[ringAt_].used = true;
        ringAt_ = (ringAt_ + 1) % RING;
    }
    void maskedCopy(const uint8_t* f, size_t n, uint8_t* tmp) const { memcpy(tmp, f, n); tmp[4] = 0; tmp[5] = 0; }
    void seal(uint8_t* f, size_t n) const {
        uint8_t tmp[MAX_FRAME]; maskedCopy(f, n, tmp);
        c_.tag(c_.key, c_.keyLen, tmp, n, f + n);
    }
    bool verify(const uint8_t* f, size_t n) const {
        if (!c_.tag) return false;
        uint8_t tmp[MAX_FRAME], t[8]; maskedCopy(f, n, tmp);
        c_.tag(c_.key, c_.keyLen, tmp, n, t);
        uint8_t diff = 0; for (int i = 0; i < 8; i++) diff |= t[i] ^ f[n + i];   // no early exit
        return diff == 0;
    }
};

}  // namespace mesh
