// Modular show-module firmware.
//
// One binary serves every module type: the stored identity (NVS) decides
// which Module implementation boots. Control is identical over three
// channels — RS485 bus, the module's own website (WiFi), and USB serial —
// all funneled through CommandRouter.
//
//   src/core/     shared services (identity, sd, rs485, web, audio, rgb, sequences)
//   src/modules/  one folder per module type ("lift" today, more later)
//   config/       pin map + defaults
#include <Arduino.h>
#include <config.h>

#include "core/Identity.h"
#include "core/ConfigStore.h"
#include "core/HwConfig.h"
#include "core/UserStore.h"
#include "core/SDStore.h"
#include "core/SequencePlayer.h"
#include "core/CommandRouter.h"
#include "core/RS485Bus.h"
#include "core/WebPortal.h"
#include "modules/Module.h"
#include "modules/ModuleFactory.h"

Identity identity;
ConfigStore cfgstore;
SDStore sdstore;
SequencePlayer sequence;
CommandRouter router;
RS485Bus rs485;
WebPortal portal;
Module* module = nullptr;

static String serialBuf;

// Write a reply as ONE call, newline included.
//
// The protocol is "one command in, exactly one reply line out", and
// Serial.println() breaks that: it is print(text) followed by a separate
// print("\r\n"), so a WiFi event — which runs on another task — can land
// between them and glue its log line onto the end of the reply. Seen on the
// bench:
//
//   OK joining "lift-test" now (WIFI for progress)[wifi] disconnected, reason=8
//
// A single write(buf, len) goes into the UART queue under one lock, so no
// other task can get inside it. The leading newline also terminates any log
// line that was still half-printed, so the reply always starts clean.
static void emitLine(const String& s) {
    Serial.print("\n" + s + "\n");
}

void setup() {
  // load the runtime pin map from NVS first (fast) so every service below
  // uses the web-configured pins, then park the RS485 transceiver in receive
  // mode — until DE is driven LOW a floating pin could jam the shared bus
  hw.begin();
  pinMode(hw.pins.rs485De, OUTPUT);
  digitalWrite(hw.pins.rs485De, LOW);

  Serial.begin(115200);
  delay(100);
  Serial.println("\n[boot] fw " FW_VERSION);

  identity.begin();
  cfgstore.begin();
  users.begin();   // login accounts for the Setup page (default manny/12345678)
  sdstore.begin(); // optional: everything below also works without a card

  module = ModuleFactory::create(identity.type(), &sdstore);

  // settings precedence: defaults < /data/module.yaml (if card) < CFG in NVS
  {
    JsonDocument doc;
    if (sdstore.loadYaml("/data/module.yaml", doc)) {
      module->applySettings(doc.as<JsonVariant>());
      Serial.println("[boot] applied /data/module.yaml");
    }
  }
  {
    JsonDocument doc;
    if (cfgstore.applyTo(doc)) {
      module->applySettings(doc.as<JsonVariant>());
      Serial.println("[boot] applied CFG overrides from NVS");
    }
  }

  sequence.begin(&sdstore, &router);
  router.begin(&identity, module, &sdstore, &sequence, &cfgstore);
  module->begin();
  rs485.begin(&identity, &router);
  portal.begin(&identity, &router, &sdstore, &rs485);

  // modules may put frames on the bus themselves (nong "link" mode
  // broadcasts POSE to follower boards so multiple ESP32s move in sync)
  module->busSend = [](const String& line) { rs485.send(line); };

  // replies from other modules on the bus surface on USB and the web console,
  // so a PC connected to just this module can master the whole RS485 fleet
  rs485.onBusLine([](const String& line) {
    emitLine(line);
    portal.pushConsole(line);
  });

  Serial.printf("[boot] id=%u name=\"%s\" type=%s\n",
                identity.id(), identity.name().c_str(), identity.type().c_str());
  Serial.println("[boot] ready — commands on USB serial, RS485 (#<id> CMD) and http://" +
                 identity.hostname() + ".local/");
}

void loop() {
  rs485.loop();
  router.loop();   // module motion/rgb/audio + sequences + deferred reboot
  portal.loop();

  // USB serial accepts the same command lines (handy for bring-up).
  // Lines starting with '#' are bridged onto the RS485 bus (address any
  // module through this one: "#3 GOTO 2", "#* PING").
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      serialBuf.trim();
      if (serialBuf.length()) {
        emitLine(serialBuf[0] == '#' ? rs485.bridge(serialBuf, &router)
                                     : router.handle(serialBuf));
      }
      serialBuf = "";
    } else if (c != '\r') {
      serialBuf += c;
    }
  }

  // Let the other tasks actually run.
  //
  // This loop takes the router mutex on every pass (router.loop() drives the
  // module and the sequence player under it) and then immediately comes back
  // for more. The web server runs in its own task and needs that same mutex to
  // answer a command — so it spent most of its time queued behind a loop that
  // was doing nothing. Measured on the bench: a POSE over WiFi took ~90 ms
  // while an ICMP ping to the same board took 17 ms; the missing 70 ms was
  // this.
  //
  // delay(1) yields to the scheduler for one tick. Nothing here needs to spin
  // faster: the servos are written at their frame rate (50 Hz by default) from
  // a millis() clock, not once per pass.
  delay(1);
}
