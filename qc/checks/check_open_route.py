"""Open module uses a way in the hub really has, not one a board claimed.

User 2026-09-10 (A26-7): *hub can see the module via rs485 but cannot control
the robot*. The cable was working the whole time. The hub page preferred
`wifi:<ip>` over the cable whenever the board's record carried an STA address -
and that address is the BOARD's own claim, learned from an INFO answer over the
cable. It is true about the board and says nothing about this PC: the venue
WiFi may be down, the board may be on a hotspot this machine is not joined to,
or the lease may have moved. Opening it sent every call to an address nobody
here could reach, which reads as "no reply" with the cable sitting right there.

`routes` is the honest answer. A wifi route exists only when the hub's own
sweep got an answer back from that address; a usb/rs485 route only when a probe
on this PC's cable did. So WiFi outranks the cable when, and only when, there
is a live wifi route.

Driven through the page's own repaintMods(), not hand-written markup, and the
assertion is the address the ⚙ Open module button really opens.
"""
import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "Open module uses a way in the hub really has"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:900px;height:700px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("ROUTE " + s); qcMark("done"); }
window.addEventListener("load", async function(){
  var out = [];
  var fr = document.getElementById("f");
    try {
      var w = fr.contentWindow, d = fr.contentDocument;
      var ready = await qcWaitFor(function(){
        d = fr.contentDocument; w = fr.contentWindow;
        return d && typeof w.repaintMods === "function"
               && d.getElementById("mods"); }, 25000);
      out.push("builder=" + (ready ? "yes" : "no"));
      if (!ready) return done(out.join(" "));
      // #mods lives in the MODULES tab, and every other tab is display:none.
      var tab = d.querySelector('#tabs .tab[data-go="modules"]');
      if (tab) tab.click();

      // THE SAME BOARD, three times over, differing only in which ways in the
      // hub actually has. Every one of them claims the same STA address.
      w.MODS = [
        {id: 11, name: "wifi-live", type: "nong", ip: "10.0.0.11", wifi_mode: "sta",
         routes: [{kind: "wifi", dev: "wifi:10.0.0.11", ip: "10.0.0.11"},
                  {kind: "usb", dev: "usb:COM29", port: "COM29"}]},
        {id: 12, name: "cable-only", type: "nong", ip: "10.0.0.12", wifi_mode: "sta",
         routes: [{kind: "usb", dev: "usb:COM29", port: "COM29"}]},
        {id: 13, name: "bus-only", type: "nong", ip: "10.0.0.13", wifi_mode: "sta",
         routes: [{kind: "rs485", dev: "usb:COM29:67", port: "COM29", bus: 67}]},
        {id: 14, name: "wifi-stale", type: "nong", ip: "10.0.0.14", wifi_mode: "sta",
         routes: [{kind: "wifi", dev: "wifi:10.0.0.14", ip: "10.0.0.14", stale: true},
                  {kind: "usb", dev: "usb:COM29", port: "COM29"}]}
      ];
      w.repaintMods();

      // Read the address the button REALLY opens, by taking the window.open it
      // asks for. A title or a class would pass on a page that still sends
      // every call to the wrong place.
      var got = {};
      w.open = function(url){ got.url = url; return {focus: function(){}}; };
      var rows = d.querySelectorAll("#mods .mod");
      out.push("rows=" + rows.length);
      for (var i = 0; i < rows.length; i++) {
        var name = (rows[i].textContent.match(/(wifi-live|cable-only|bus-only|wifi-stale)/) || [])[0];
        var btns = rows[i].querySelectorAll("button");
        var open = null;
        for (var j = 0; j < btns.length; j++)
          if (btns[j].textContent.indexOf("Open module") >= 0) open = btns[j];
        if (!name || !open) { out.push("miss=" + (name || "?")); continue; }
        got.url = "";
        open.onclick();
        var dev = decodeURIComponent((got.url.match(/dev=([^&]*)/) || ["", ""])[1]);
        out.push(name + "=" + (dev || "none"));
      }
      done(out.join(" "));
    } catch (e) { done(out.join(" ") + " ERR=" + String(e).replace(/[^A-Za-z0-9 :.]/g, "_").slice(0, 80)); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    real = main.scan_modules
    main.scan_modules = lambda force=False: []     # the page's own MODS only
    try:
        browser.raw_page(PAGE, base, seconds=40)
    finally:
        main.scan_modules = real

    marks = [m[6:] for m in fake_serial.qc_marks if m.startswith("ROUTE ")]
    if not t.ok(marks, "the hub page reported back",
                "never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1].split(" ") if "=" in kv)
    if "ERR" in got:
        return t.ok(False, "the page ran without throwing", str(got))
    t.eq(got.get("builder"), "yes", "the page's own row builder is what was driven")
    t.eq(got.get("rows"), "4", "all four boards were drawn")

    t.eq(got.get("wifi-live"), "wifi:10.0.0.11",
         "a board the hub really reached over WiFi still opens over WiFi")
    t.ok(got.get("cable-only") == "usb:COM29",
         "a board with only a cable opens over the CABLE, not its claimed address",
         "opened %r - the ip came from an INFO answer over that same cable and "
         "is no promise this PC shares that network (A26-7)" % got.get("cable-only"))
    t.ok(got.get("bus-only") == "usb:COM29:67",
         "a board behind RS485 opens over the bus, with its bus id",
         "opened %r" % got.get("bus-only"))
    t.ok(got.get("wifi-stale") == "usb:COM29",
         "a WiFi route that has gone quiet does not outrank a live cable",
         "opened %r - a stale route is the hub saying it stopped answering, "
         "which is exactly when the cable should win" % got.get("wifi-stale"))
