#pragma once
#include <Arduino.h>
#include <Update.h>

// FIRMWARE OVER ANY TRANSPORT, INCLUDING ONE WITH NO RESET LINES.
// ===============================================================
// esptool cannot flash a board over RS485 and never will: the ROM bootloader is
// entered by pulling EN and IO0 with DTR and RTS, and a two-wire differential
// bus has no such lines. Over WiFi the board updates itself through its own web
// server, which is fine until the part cannot do WiFi at all.
//
// Asked for on 2026-08-20: *make it can flash through all this 3 method too if
// i need to shieft to stm 32 it cannot use wifi it can use only rs485*. That
// settles the shape. The update has to be something the board does to ITSELF,
// driven by ordinary commands, so the same three commands ride a USB cable, the
// RS485 bus or WiFi and none of them needs a reset line:
//
//     FWBEGIN <bytes> <md5hex>   make room, start writing
//     FWDATA  <seq> <len> <b64>  one chunk; the reply names the seq it took
//     FWEND                      check the whole image, then reboot into it
//     FWABORT                    forget it and keep running what we have
//
// The names carry FW on purpose: FBEGIN/FDATA/FEND already exist and write an
// SD FILE. Reusing them would have meant one command that either stores a
// sequence or overwrites the firmware depending on state, which is the kind of
// thing that eventually flashes a robot with a YAML file.
//
// WHY A SEQUENCE NUMBER. The bus loses a line now and then, and an update that
// silently skips one produces a board that boots into rubbish. Each chunk says
// which one it is; a chunk out of order is REFUSED rather than written, so the
// sender can send it again. The board never has to guess.
//
// WHY A CHUNK IS SMALL. RS485Bus drops any line longer than 250 characters, so
// a chunk plus its `#<id> FWDATA <seq> ` prefix has to fit inside that. 150 raw
// bytes become 200 base64 characters, which leaves room for the prefix on any
// id. Slow, and slow is fine: an update is rare and a broken board is not.
//
// WHY MD5 OF THE WHOLE IMAGE. Every chunk arriving is not the same as the image
// being right, and the one moment to find that out is BEFORE rebooting into it.
class BusUpdate {
public:
    // FWBEGIN: make room. Returns a reply line either way.
    String begin(size_t total, const String& md5);
    // FWDATA: one chunk, base64. `seq` must be the next one expected, and
    // `want` is how many bytes it should decode to - a truncated line is still
    // legal base64, so without it a short chunk is accepted silently. See the
    // note in the .cpp: that cost a whole 1.29 MB transfer once.
    String data(uint32_t seq, size_t want, const String& b64);
    // FWEND: verify and reboot, or refuse and say why.
    String end();
    // FWABORT: stop, keep running what is already there.
    String abort();
    // FWSTAT: how far it has got - so a sender that lost its place can ask.
    String stat() const;

    bool running() const { return running_; }

private:
    bool running_ = false;
    uint32_t next_ = 0;          // the chunk number expected now
    size_t total_ = 0;           // what FWBEGIN promised
    size_t written_ = 0;         // what has really been written
    String md5_;                 // expected, lower-case hex
};
