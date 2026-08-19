"""Studio opens on a module reached through another module's hotspot.

One USB cable is meant to be enough for a whole installation with no venue
WiFi: plug into any board, let the others join that board's own access point,
and address them as

    usb:COM7@far-nong        far-nong, via the board on COM7

The hub has understood that for a long time — it turns the peer into
`REACH far-nong <command>` down the cable. Studio did not. It cut off `usb:`
and split the rest on `:`, so `COM7@far-nong` came out as the PORT NAME: it
offered a serial port with that name in its dropdown, tried to open it, and
failed to reach a module that was perfectly reachable.

Driven in a real browser, and asserted on WHAT REACHED THE MODULE. The page is
always confident it connected; the only proof is the command arriving at the
far module with the peer still attached to it.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "Studio can be opened on a module behind another module's hotspot"
SLOW = True

# fake_serial answers for a second module behind the plugged-in one's hotspot.
PEER = "far-nong"

DRIVER = """
window.addEventListener("load", function(){
  setTimeout(function(){
    try{
      // What Studio decided the cable and the peer are, after reading ?dev=
      qcMark("PEER port=" + ($("usbPort").value || "none") +
             " peer=" + (window.HUB_PEER || "none"));
      // and then talk to it, which is the part that has to reach the far board
      rawCmd("PING").then(function(r){
        qcMark("PEER reply=" + String(r).slice(0, 40).replace(/[\\s|]+/g, "~"));
        qcMark("done");
      }).catch(function(e){
        qcMark("PEER reply=ERROR-" + String(e.message || e).slice(0, 40)
               .replace(/[\\s|]+/g, "~"));
        qcMark("done");
      });
    }catch(e){ qcFail(e); }
  }, 2500);
});
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    # _qcdriver.html is the real Studio page plus this driver — pointing at
    # /studio/ instead loads Studio WITHOUT the driver, so nothing reports and
    # the check waits out its whole deadline saying nothing.
    dev = "usb:%s@%s" % (fake_serial.PORT, PEER)
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=%s"
                 % (base, urllib.parse.quote(dev, safe="")), seconds=40)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("PEER "):
            for kv in m[5:].split(" "):
                k, _, v = kv.partition("=")
                if k:
                    got[k] = v.replace("~", " ")
    if not t.ok(got, "Studio reported back", fake_serial.qc_marks[-4:]):
        return

    # ---- the peer is split off, not glued to the port ------------------
    t.eq(got.get("port"), fake_serial.PORT,
         "Studio opens the real cable, not a port named after the peer")
    t.eq(got.get("peer"), PEER, "and keeps the peer it was given")

    # ---- and it REACHED the far module --------------------------------
    # On the wire, not in the page. A page that says connected while the
    # command went nowhere is the failure this exists to catch.
    # wire is (when, command) pairs — the command is the second half.
    wire = " ".join(c for _, c in fake_serial.wire)
    t.contains(wire.upper(), "REACH",
               "the command was forwarded to the module behind the hotspot",
               )
    t.contains(wire, PEER,
               "naming the peer it was meant for")
    t.ok("ERROR" not in got.get("reply", ""),
         "and Studio got an answer back rather than an error",
         got.get("reply"))

    # ---- the peer does not outlive the page it came from ---------------
    # Found by the multi-model review: HUB_PEER was set once when the page
    # opened and never cleared, so changing the cable by hand kept aiming every
    # command at the module behind the OLD board's hotspot. A value that
    # describes one session, kept in a global that nothing resets.
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "function clearPeer",
               "there is a way to stop aiming at a peer")
    # On the EVENTS, not inside the functions: usbPortChanged and
    # connModeChanged are also called while the page sets itself up, so
    # clearing there threw the peer away the moment a page opened with one.
    # Setting a value from code fires no change event; a person choosing one
    # from the dropdown does.
    t.contains(app, 'port.addEventListener("change"',
               "picking another cable by hand drops the peer")
    t.contains(app, 'mode.addEventListener("change"',
               "and so does changing the connection by hand")

    # ---- and the link to the module website points at the SAME board ----
    # It built its address without the peer, so it opened the plugged-in board
    # while every command went somewhere else: two robots, one screen.
    i = app.find("function moduleDev(")
    t.ok(i >= 0, "moduleDev exists")
    if i >= 0:
        t.contains(app[i:i + 500], "HUB_PEER",
                   "the module website link carries the peer too")
