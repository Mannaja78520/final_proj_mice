#include "core/CommandRouter.h"
#include "core/CommandHelp.h"
#include "core/ConfigStore.h"
#include "core/Identity.h"
#include "core/SDStore.h"
#include "core/SequencePlayer.h"
#include "core/Util.h"
#include "modules/Module.h"
#include "modules/ModuleFactory.h"
#include "core/HwConfig.h"
#include "core/UserStore.h"
#include <WiFi.h>
#include <config.h>
#include <mbedtls/base64.h>

// default folder for a bare filename in the file-transfer commands
static String fullPath(const String& p) {
    return p.startsWith("/") ? p : "/moves/" + p;
}

void CommandRouter::begin(Identity* id, Module* module, SDStore* sd, SequencePlayer* seq, ConfigStore* cfg) {
    id_ = id;
    module_ = module;
    sd_ = sd;
    seq_ = seq;
    cfg_ = cfg;
    mtx_ = xSemaphoreCreateRecursiveMutex();
}

void CommandRouter::lock()   { xSemaphoreTakeRecursive(mtx_, portMAX_DELAY); }
void CommandRouter::unlock() { xSemaphoreGiveRecursive(mtx_); }

String CommandRouter::handle(const String& line) {
    lock();
    String reply = handleLocked(line);
    unlock();
    return reply;
}

String CommandRouter::handleLocked(const String& line) {
    String argv[16]; // roomy: file names with spaces come through as tokens
    int argc = Util::tokenize(line, argv, 16);
    if (argc == 0) return "ERR empty";
    String cmd = argv[0];
    cmd.toUpperCase();

    if (cmd == "PING") {
        return "PONG " + String(id_->id()) + " " + id_->name() + " " + id_->type();
    }

    if (cmd == "HELP" || cmd == "?") {
        // Straight from config/commands.json (compiled in), so the board can
        // never advertise a command it does not have, or hide one it does.
        return commandHelp(id_->type(), argc >= 2 ? argv[1] : String(""));
    }

    if (cmd == "INFO") {
        JsonDocument doc;
        buildStatus(doc);
        String out;
        serializeJson(doc, out);
        return out;
    }

    if (cmd == "SET") {
        if (argc < 3) return "ERR usage: SET ID|NAME|TYPE|WIFI ...";
        String what = argv[1];
        what.toUpperCase();
        if (what == "ID") {
            int v = argv[2].toInt();
            if (v < 1 || v > 247) return "ERR id must be 1-247";
            id_->setId((uint8_t)v);
            return "OK id=" + String(id_->id());
        }
        if (what == "NAME") {
            id_->setName(Util::joinFrom(argv, argc, 2));
            return "OK name=" + id_->name();
        }
        if (what == "TYPE") {
            String t = argv[2];
            t.toLowerCase();
            if (!ModuleFactory::isKnown(t)) return "ERR unknown type (" + ModuleFactory::knownTypesCsv() + ")";
            id_->setType(t);
            return "OK type=" + t + " (reboot to apply)";
        }
        if (what == "WIFI") {
            String a = argv[2];
            a.toUpperCase();
            // radio mode: OFF = USB/RS485 only, AP = own hotspot only, ON = normal
            if (argc == 3 && (a == "OFF" || a == "ON" || a == "AP")) {
                a.toLowerCase();
                id_->setWifiMode(a);
                return "OK wifi mode=" + a + " (reboot to apply)";
            }
            // otherwise: credentials. empty pass = open network
            id_->setWifi(argv[2], argc >= 4 ? Util::joinFrom(argv, argc, 3) : "");
            id_->setWifiMode("on"); // setting credentials implies the radio is wanted
            return "OK wifi stored (reboot to apply)";
        }
        return "ERR unknown SET target";
    }

    if (cmd == "CFG") {
        if (argc == 1) return "CFG " + cfg_->list();
        String k = argv[1];
        k.toLowerCase();
        if (k == "clear") {
            if (argc >= 3) {
                String k2 = argv[2];
                k2.toLowerCase();
                return cfg_->clear(k2) ? "OK cleared " + k2 : "ERR unknown key";
            }
            cfg_->clearAll();
            return "OK cleared all";
        }
        if (argc < 3) return "ERR usage: CFG [<key> <value>|CLEAR [key]]";
        if (!cfg_->set(k, argv[2].toFloat()))
            return "ERR keys: encoder leds speed speed_mms stages stage_mm mm_per_rev counts_per_rev max_rpm counts_per_stage volume speed_dps max_dps link peer";
        return "OK " + k + "=" + argv[2] + " (reboot to apply)";
    }

    // ---- login accounts for the Setup page (stored in NVS) ----
    //   AUTH <user> <pass>                 -> OK <user> | ERR bad login
    //   USER LIST <user> <pass>            -> ["manny",...]
    //   USER ADD  <user> <pass> <new> <newpass>
    //   USER DEL  <user> <pass> <target>
    //   USER PASS <user> <pass> <newpass>  -> change your own password
    if (cmd == "AUTH") {
        if (argc < 3) return "ERR usage: AUTH <user> <pass>";
        return users.verify(argv[1], argv[2]) ? "OK " + argv[1] : "ERR bad login";
    }
    if (cmd == "USER") {
        if (argc < 2) return "ERR usage: USER LIST|ADD|DEL|PASS <user> <pass> ...";
        String sub = argv[1];
        sub.toUpperCase();
        // every USER op requires a valid caller (argv[2]=user, argv[3]=pass)
        if (argc < 4 || !users.verify(argv[2], argv[3])) return "ERR auth";
        if (sub == "LIST") return users.listJson();
        if (sub == "ADD") {
            if (argc < 6) return "ERR usage: USER ADD <user> <pass> <new> <newpass>";
            return users.add(argv[4], argv[5]) ? "OK added " + argv[4]
                                               : "ERR exists or bad name/pass (no spaces)";
        }
        if (sub == "DEL") {
            if (argc < 5) return "ERR usage: USER DEL <user> <pass> <target>";
            return users.remove(argv[4]) ? "OK removed " + argv[4]
                                         : "ERR not found or last user";
        }
        if (sub == "PASS") {
            if (argc < 5) return "ERR usage: USER PASS <user> <pass> <newpass>";
            return users.setPass(argv[2], argv[4]) ? "OK password changed" : "ERR bad password";
        }
        return "ERR USER LIST|ADD|DEL|PASS";
    }

    // ---- hardware pin map (stored in NVS, set from the web; reboot to apply)
    //   PIN?                 -> current assignments (JSON)
    //   PIN VALID            -> which GPIOs are usable + why (JSON)
    //   PIN <name> <gpio>    -> set a pin (-1 = disable), reboot to apply
    //   PIN CLEAR [name]     -> reset one / all to compile defaults
    if (cmd == "PIN" || cmd == "PIN?" || cmd == "PINS" || cmd == "PINS?") {
        if (cmd == "PIN?" || cmd == "PINS" || cmd == "PINS?" || argc == 1)
            return hw.listJson();
        String k = argv[1];
        k.toLowerCase();
        if (k == "valid") return HwConfig::validPinsJson();
        if (k == "clear") {
            if (argc >= 3) {
                String k2 = argv[2]; k2.toLowerCase();
                return hw.clear(k2) ? "OK cleared " + k2 + " (reboot to apply)" : "ERR unknown pin";
            }
            hw.clearAll();
            return "OK cleared all pins (reboot to apply)";
        }
        if (argc < 3) return "ERR usage: PIN <name> <gpio> | PIN? | PIN VALID | PIN CLEAR [name]";
        int gpio = argv[2].toInt();
        if (!hw.set(k, gpio))
            return "ERR bad pin/gpio (gpio -1..39, not 6-11 flash; name from PIN?)";
        return "OK " + k + "=" + String(gpio) + " (reboot to apply)";
    }

    if (cmd == "FILES") {
        // same JSON as GET /api/files — so USB/RS485 apps can browse the SD
        String dir = argc >= 2 ? argv[1] : "/data";
        if (!Util::safePath(dir)) return "ERR bad dir";
        return sd_->listJson(dir.c_str());
    }

    // ---- SD file transfer as plain text commands ----
    // So the editor (and any script) can write/read/delete SD files over USB
    // serial and RS485 too, not only via the WiFi HTTP API. Data is base64
    // in small chunks (RS485 frames are limited to ~250 chars).
    //   FBEGIN <file>          start writing (bare name goes to /moves)
    //   FDATA <base64>         append a chunk
    //   FEND                   finish -> OK wrote /moves/x.yaml 812
    //   FREAD <file> <off> <n> read n bytes (<=120) -> base64, "EOF" at end
    //   FDEL <file>            delete
    if (cmd == "FBEGIN") {
        if (argc < 2) return "ERR usage: FBEGIN <file>";
        String path = fullPath(Util::joinFrom(argv, argc, 1));
        if (!Util::safePath(path)) return "ERR bad path";
        if (!sd_->openWrite(path.c_str())) return "ERR cannot open (sd?)";
        return "OK writing " + path;
    }
    if (cmd == "FDATA") {
        if (argc < 2) return "ERR usage: FDATA <base64>";
        if (!sd_->writing()) return "ERR no FBEGIN";
        uint8_t buf[192];
        size_t n = 0;
        if (mbedtls_base64_decode(buf, sizeof(buf), &n,
                                  (const uint8_t*)argv[1].c_str(), argv[1].length()) != 0)
            return "ERR bad base64";
        if (!sd_->writeChunk(buf, n)) return "ERR write failed";
        return "OK " + String(n);
    }
    if (cmd == "FEND") {
        if (!sd_->writing()) return "ERR no FBEGIN";
        String path = sd_->writePath();
        sd_->closeWrite(true);
        return "OK wrote " + path;
    }
    if (cmd == "FREAD") {
        if (argc < 4) return "ERR usage: FREAD <file> <offset> <len>";
        String path = fullPath(argv[1]);
        if (!Util::safePath(path)) return "ERR bad path";
        uint32_t off = (uint32_t)argv[2].toInt();
        int len = argv[3].toInt();
        if (len < 1 || len > 120) len = 120; // keeps the reply inside one RS485 frame
        uint8_t buf[120];
        int n = sd_->readChunk(path.c_str(), off, buf, len);
        if (n < 0) return "ERR cannot read " + path;
        if (n == 0) return "EOF";
        unsigned char b64[168];
        size_t olen = 0;
        mbedtls_base64_encode(b64, sizeof(b64), &olen, buf, n);
        return String((const char*)b64);
    }
    if (cmd == "FDEL") {
        if (argc < 2) return "ERR usage: FDEL <file>";
        String path = fullPath(Util::joinFrom(argv, argc, 1));
        if (!Util::safePath(path)) return "ERR bad path";
        return sd_->remove(path.c_str()) ? "OK deleted " + path : "ERR delete failed";
    }

    if (cmd == "MOVE") {
        if (argc < 2) return "ERR usage: MOVE <file>|STOP";
        String a = argv[1];
        a.toUpperCase();
        if (a == "STOP") {
            seq_->stop();
            return "OK move stopped";
        }
        String path = Util::joinFrom(argv, argc, 1);
        if (!path.startsWith("/")) path = "/moves/" + path;
        String err;
        if (!seq_->start(path, err)) return "ERR " + err;
        return "OK playing " + path;
    }

    if (cmd == "REBOOT") {
        requestReboot();
        return "OK rebooting";
    }

    String reply;
    if (module_->handleCommand(argv, argc, reply)) return reply;
    return "ERR unknown cmd: " + cmd;
}

void CommandRouter::buildStatus(JsonDocument& doc) {
    lock();
    doc["id"] = id_->id();
    doc["name"] = id_->name();
    doc["type"] = id_->type();
    doc["fw"] = FW_VERSION;
    doc["sd"] = sd_->available();
    JsonArray types = doc["types"].to<JsonArray>();
    ModuleFactory::appendKnownTypes(types);
    JsonObject seq = doc["seq"].to<JsonObject>();
    seq["running"] = seq_->running();
    seq["file"] = seq_->file();
    // wifi info here (not only on the web) so INFO over USB/RS485 tells an
    // app where to find the module's website/HTTP API
    JsonObject wifi = doc["wifi"].to<JsonObject>();
    bool sta = WiFi.status() == WL_CONNECTED;
    bool ap = WiFi.getMode() & WIFI_MODE_AP;
    wifi["mode"] = sta ? "sta" : (ap ? "ap" : "off");
    wifi["wmode"] = id_->wifiMode();   // configured mode: on | ap | off (default on)
    wifi["ip"] = sta ? WiFi.localIP().toString() : (ap ? WiFi.softAPIP().toString() : "");
    wifi["ssid"] = sta ? WiFi.SSID() : "";
    wifi["rssi"] = sta ? WiFi.RSSI() : 0;
    wifi["host"] = id_->hostname();
    module_->status(doc["module"].to<JsonObject>());
    unlock();
}

void CommandRouter::requestReboot(uint32_t delayMs) {
    rebootAt_ = millis() + delayMs;
    if (rebootAt_ == 0) rebootAt_ = 1; // 0 means "not scheduled"
}

void CommandRouter::loop() {
    lock();
    module_->loop();
    seq_->loop();
    unlock();

    if (rebootAt_ && (int32_t)(millis() - rebootAt_) >= 0) {
        Serial.println("[sys] rebooting...");
        delay(50);
        ESP.restart();
    }
}
