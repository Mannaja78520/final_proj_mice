#include "core/BusUpdate.h"
#include "core/Log.h"
#include <mbedtls/base64.h>

// The largest raw chunk a line can carry. See the note in BusUpdate.h: the bus
// drops lines over 250 characters, and 150 raw bytes is 200 base64 characters,
// which still leaves room for `#<id> FWDATA <seq> ` in front of it.
static const size_t MAX_CHUNK = 150;

String BusUpdate::begin(size_t total, const String& md5) {
    if (running_) Update.abort();
    running_ = false;
    next_ = 0;
    written_ = 0;
    total_ = total;
    md5_ = md5;
    md5_.toLowerCase();

    if (total == 0) return "ERR FWBEGIN needs the size in bytes";
    // Ask for the exact size, not UPDATE_SIZE_UNKNOWN: the driver can then
    // refuse an image that will not fit BEFORE a single byte is written,
    // rather than half way through when the running firmware is already gone.
    if (!Update.begin(total)) {
        return "ERR no room for " + String((unsigned)total) + " bytes: " +
               String(Update.errorString());
    }
    // THE MD5 IS NOT OPTIONAL. This used to read `if (md5_.length() == 32 &&
    // ...)`, so an FWBEGIN with no md5 started an update with no integrity
    // check at all and said nothing about it. Update.end(true) only verifies
    // CONTENT when an md5 was registered; with none it checks that the write
    // finished and no more. Everything else here guards a different failure:
    // the per-chunk length catches a TRUNCATED line, and the byte total
    // catches a SHORT image. Neither catches a corrupted one. So a flipped bit
    // in a chunk that still decoded to the declared length passed every guard,
    // and FWEND answered OK and rebooted the board into it.
    //
    // Found by a model review on 2026-08-20 and confirmed against the code.
    // The hub always sent an md5, which is exactly why this could sit here
    // unnoticed: the only caller happened to do the right thing.
    if (md5_.length() != 32) {
        Update.abort();
        return "ERR FWBEGIN needs the image md5 (32 hex characters). Without "
               "it nothing can tell a good image from a damaged one, and this "
               "board would boot whatever arrived";
    }
    if (!Update.setMD5(md5_.c_str())) {
        Update.abort();
        return "ERR that md5 is not 32 hex characters";
    }
    running_ = true;
    LOGF(sys, "update over the bus: %u bytes expected", (unsigned)total);
    return "OK FWBEGIN " + String((unsigned)total);
}

String BusUpdate::data(uint32_t seq, size_t want, const String& b64) {
    if (!running_) return "ERR no update started - send FWBEGIN first";
    // OUT OF ORDER IS REFUSED, NOT WRITTEN. A bus loses a line now and then,
    // and an update that quietly skips one produces a board that boots into
    // rubbish. Saying which one is expected lets the sender simply send it.
    if (seq != next_) {
        return "ERR out of order: expected " + String((unsigned)next_) +
               ", got " + String((unsigned)seq);
    }

    size_t cap = (b64.length() * 3) / 4 + 4;
    if (cap > MAX_CHUNK + 8) {
        return "ERR chunk too big: at most " + String((unsigned)MAX_CHUNK) +
               " bytes per FWDATA";
    }
    uint8_t raw[MAX_CHUNK + 8];
    size_t got = 0;
    int rc = mbedtls_base64_decode(raw, sizeof(raw), &got,
                                   (const unsigned char*)b64.c_str(),
                                   b64.length());
    if (rc != 0) return "ERR chunk is not valid base64";

    // A TRUNCATED LINE IS STILL VALID BASE64, and that is the whole reason this
    // length is on the wire. Measured 2026-08-20 flashing a real 1.29 MB image
    // over a cable: one chunk in nine thousand arrived 64 characters short, and
    // 136 characters is a legal base64 length, so it decoded cleanly into 102
    // bytes instead of 150. Nothing complained until FWEND counted the image
    // and found it 48 bytes light — four minutes of transfer wasted, with no
    // clue which chunk did it.
    //
    // Refusing here, WITHOUT advancing next_, means the sender simply sends the
    // same chunk again. A dropped run of bytes costs one round trip instead of
    // the whole update.
    // `want` is REQUIRED, not optional. Written as `if (want && ...)` the guard
    // switched itself off whenever the declared length was 0 - and toInt()
    // returns 0 for any token that is not a number, so `FWDATA 7 0 <b64>` and
    // `FWDATA 7 x <b64>` both wrote a short chunk in silence. Found 2026-08-21,
    // the same "present but not armed" shape as the md5 hole.
    if (want == 0 || want > MAX_CHUNK) {
        return "ERR FWDATA needs the chunk length: 1 to " +
               String((unsigned)MAX_CHUNK) + " bytes";
    }
    if (got != want) {
        return "ERR chunk short: got " + String((unsigned)got) + " of " +
               String((unsigned)want) + " bytes - send it again";
    }
    if (written_ + got > total_) {
        return "ERR that is more than FWBEGIN promised (" +
               String((unsigned)total_) + " bytes)";
    }
    if (Update.write(raw, got) != got) {
        String why = Update.errorString();
        Update.abort();
        running_ = false;
        return "ERR write failed: " + why;
    }
    written_ += got;
    next_++;
    return "OK " + String((unsigned)seq) + " " + String((unsigned)written_);
}

String BusUpdate::end() {
    if (!running_) return "ERR no update started";
    if (written_ != total_) {
        String why = "ERR only " + String((unsigned)written_) + " of " +
                     String((unsigned)total_) + " bytes arrived";
        Update.abort();
        running_ = false;
        return why;
    }
    // end(true) checks the md5 that FWBEGIN set. A wrong image is refused HERE,
    // while the board is still running firmware that works.
    if (!Update.end(true)) {
        String why = Update.errorString();
        running_ = false;
        return "ERR the image did not check out: " + why;
    }
    running_ = false;
    LOGF(sys, "update over the bus: image accepted, restarting");
    // The reply has to leave before the board goes. The caller sends it, then
    // this happens on the next loop - see CommandRouter.
    return "OK FWEND restarting";
}

String BusUpdate::abort() {
    if (!running_) return "OK nothing to abort";
    Update.abort();
    running_ = false;
    next_ = 0;
    written_ = 0;
    return "OK update abandoned - still running the firmware you had";
}

String BusUpdate::stat() const {
    if (!running_) return "FWSTAT idle";
    return "FWSTAT " + String((unsigned)written_) + "/" +
           String((unsigned)total_) + " next=" + String((unsigned)next_);
}
