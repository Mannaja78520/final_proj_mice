"""All four ways the web apps reach a module — not just the one that gets used.

Only shared-USB has ever been exercised. The other three are genuinely
different code: RS485 frames and unwraps every line, direct Web Serial runs in
the browser and owns the port, and WiFi takes a *separate branch* for file
transfer (the module's HTTP API instead of FBEGIN/FDATA/FEND). A break in any of
them is silent until someone plugs that cable in at the show.

Each transport must answer the same command, transfer a file, and read and
write the pin map — the pin config in particular, because it worked over WiFi
and failed over USB once already.
"""
import json
import urllib.parse

import browser
import fake_serial
import fake_wifi
import qc as F

AREA = "transports"
TITLE = "USB, RS485, Web Serial and WiFi all work"
SLOW = True

# Direct Web Serial cannot be reached from python at all, so it is driven in a
# real browser with navigator.serial stubbed — the stub speaks the module's
# line protocol, including the log lines the reader must skip.
DRIVER = """
(function(){
  // A fake navigator.serial: enough for serialConnect / serialReadLoop /
  // serialCmd to run for real. Replies carry a bracket-tag LOG line first, so
  // the reader's filter is exercised — a filter that ate "[{" broke pin config
  // over USB once, and this is the browser-side twin of that bug.
  var enc = new TextEncoder();
  function reply(line){
    return enc.encode("[nong] tick\\n" + line + "\\n");
  }
  // navigator.serial is a read-only accessor on a secure context, so a plain
  // assignment is silently dropped — it has to be redefined.
  var stub = {
    requestPort: function(){
      return Promise.resolve({
        open: function(){ return Promise.resolve(); },
        setSignals: function(){ return Promise.resolve(); },
        get readable(){
          return new ReadableStream({
            start: function(c){
              window.__push = function(b){ c.enqueue(b); };
            }
          });
        },
        get writable(){
          return new WritableStream({
            write: function(chunk){
              var s = new TextDecoder().decode(chunk).trim();
              var head = s.split(" ")[0].toUpperCase();
              var out = "OK";
              if (head === "INFO") out = JSON.stringify({id:3,name:"ser",type:"nong",sd:true,module:{joints:[90,90,90,90,90,90,90,90,90,90]}});
              else if (head === "PIN" || head === "PIN?") {
                out = /VALID/i.test(s) ? '[{"g":13,"c":"ok"}]' : '{"servo1":32}';
              }
              else if (head === "POSE") out = "OK POSE";
              setTimeout(function(){ if (window.__push) window.__push(reply(out)); }, 5);
              return Promise.resolve();
            }
          });
        },
      });
    },
  };
  try {
    Object.defineProperty(window.navigator, "serial",
                          { value: stub, configurable: true, writable: true });
  } catch (e) { window.navigator.serial = stub; }

  function step(){
    try{
      if (typeof serialConnect !== "function") return setTimeout(step, 200);
      qcMark2("stub-" + (navigator.serial === stub ? "installed" : "REJECTED"));
      document.getElementById("connSel").value = "serial";
      connModeChanged();
      serialConnect().then(function(){
        qcMark2("connected-" + (usbDirect() ? "yes" : "no"));
        return serialCmd("INFO");
      }).then(function(r){
        qcMark2("info-" + (/"type"/.test(r) ? "json" : "BAD:" + String(r).slice(0,20)));
        return serialCmd("PIN VALID");
      }).then(function(r){
        // the reply is a JSON ARRAY: the log filter must not have eaten it
        qcMark2("pinvalid-" + (/^\\[\\{/.test(String(r).trim()) ? "array" : "BAD:" + String(r).slice(0,20)));
        return serialCmd("PIN?");
      }).then(function(r){
        qcMark2("pinmap-" + (/servo1/.test(String(r)) ? "ok" : "BAD"));
        qcMark2("done");
      }).catch(function(e){ qcMark2("ERROR-" + (e.message||e)); });
    }catch(e){ qcMark2("ERROR-" + (e.message||e)); }
  }
  // report over the HUB, not the stubbed cable
  window.qcMark2 = function(m){
    return fetch("/api/usb/cmd?port=COM99&id=0&c=" +
                 encodeURIComponent("MOVE QCMARK " + m)).catch(function(){});
  };
  window.addEventListener("load", function(){ setTimeout(step, 1200); });
})();
"""


def run(t):
    fake_serial.reset()
    fake_wifi.reset()
    wifi_ip = fake_wifi.start()
    base, main = F.start_hub()
    port = fake_serial.PORT

    def cmd_over(dev, c):
        return F.get("%s/api/dev/cmd?dev=%s&c=%s"
                     % (base, urllib.parse.quote(dev), urllib.parse.quote(c)))

    # ---- 1 & 2: USB/UART and RS485, through the hub -------------------
    for label, dev in (("USB / UART", "usb:%s" % port),
                       ("RS485 (bus id 2)", "usb:%s:2" % port),
                       ("WiFi", "wifi:%s" % wifi_ip)):
        s, b = cmd_over(dev, "INFO")
        t.eq(s, 200, "%s: a command round-trips" % label)
        t.contains(b, '"type"', "%s: and the reply is the module's" % label)
        t.ok(not b.startswith("@"), "%s: no frame left on the reply" % label)

        # status, files and the PIN map on every transport
        s, b = F.get("%s/api/dev/status?dev=%s" % (base, urllib.parse.quote(dev)))
        t.contains(b, '"type"', "%s: status works" % label)
        s, b = F.get("%s/api/dev/files?dev=%s&dir=/moves" % (base, urllib.parse.quote(dev)))
        t.eq(s, 200, "%s: the SD listing works" % label)

        # PIN CONFIG — the one that worked on WiFi and failed on USB once
        s, b = cmd_over(dev, "PIN VALID")
        t.eq(s, 200, "%s: PIN VALID answers" % label)
        t.ok(b.strip().startswith("["),
             "%s: PIN VALID returns its JSON array" % label,
             "a log-line filter probably ate it: %r" % b[:60])
        s, b = cmd_over(dev, "PIN?")
        t.contains(b, "servo", "%s: the pin map reads back" % label)
        s, b = cmd_over(dev, "PIN servo1 27")
        t.contains(b.lower(), "ok", "%s: a pin can be SET" % label)

    # ---- WiFi file transfer takes its own branch ----------------------
    # Studio uploads over WiFi with the module's HTTP API, not FBEGIN/FDATA.
    s, b = F.get("%s/api/robot/files?ip=%s&dir=/moves" % (base, wifi_ip))
    t.contains(b, "wave", "WiFi: the robot file list comes back")
    s, b = F.get("%s/api/robot/download?ip=%s&path=%s"
                 % (base, wifi_ip, urllib.parse.quote("/moves/wave.yaml")))
    t.contains(b, "pose:", "WiFi: a sequence downloads")
    s, b = F.get("%s/api/robot/delete?ip=%s&path=%s"
                 % (base, wifi_ip, urllib.parse.quote("/moves/wave.yaml")))
    t.ok("wave.yaml" not in fake_wifi.MODULE.files, "WiFi: and deletes")

    # ---- 4: direct Web Serial, in a real browser ----------------------
    if not browser.available():
        t.give_up("headless Edge not found — the Web Serial half needs a browser")
    before = len(fake_serial.qc_marks)
    browser.page(DRIVER, query="%s/studio/_qcdriver.html" % base, seconds=20)
    marks = fake_serial.qc_marks[before:]
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "direct Web Serial ran clean", marks)
    got = {m.split("-", 1)[0]: m.split("-", 1)[1] for m in marks if "-" in m}
    t.eq(got.get("connected"), "yes", "direct Web Serial connects")
    t.eq(got.get("info"), "json", "direct Web Serial: INFO round-trips")
    t.eq(got.get("pinvalid"), "array",
         "direct Web Serial: a JSON array reply survives the log-line filter")
    t.eq(got.get("pinmap"), "ok", "direct Web Serial: the pin map reads back")
