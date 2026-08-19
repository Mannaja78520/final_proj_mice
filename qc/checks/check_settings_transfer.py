"""Your Studio setup can move to another PC.

Everything Studio remembers — the tuned rig, your saved default, the STL
assignments, the panel width — lives in localStorage, which is per browser AND
per machine. Tuning a rig on the workshop PC and finding the show laptop knows
nothing about it is the problem this solves.

Two routes, both checked:

  * a file you carry, and
  * straight over the network, hub to hub.

The network route deliberately goes THROUGH the local hub. A page served by one
hub is not allowed to read another hub's response — that is a cross-origin
request and the browser blocks it. The hub has no such rule, so it fetches and
hands the result back same-origin. A check that only tested the browser half
would pass while the real thing was blocked.

Sequences and projects are NOT in the bundle: those are files on the hub and
travel with it already.
"""
import json
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "settings"
TITLE = "a Studio setup moves to another PC, by file or over the network"
SLOW = True

BUNDLE = {
    "kind": "mice-studio-settings", "version": 1,
    "rig": {"min": [30] * 10, "max": [150] * 10},
    "keys": {"nong_rig": '{"min":[30]}', "nong_sidew": "412"},
}

DRIVER = """
function report(s){ rawCmd("MOVE QCMARK " + s); }
window.addEventListener("load", function(){ setTimeout(function(){
  try{
    var out = [];

    // ---- what gets collected -------------------------------------------
    localStorage.setItem("nong_sidew", "377");
    var b = collectSettings();
    out.push("kind=" + b.kind);
    out.push("hasrig=" + (b.rig && b.rig.min ? "yes" : "no"));
    out.push("sidew=" + (b.keys["nong_sidew"] === "377" ? "yes" : "no"));
    // a login is per machine, not a setting — carrying it would be a surprise
    localStorage.setItem("nongZeroCred", '{"user":"x","pass":"y"}');
    out.push("nocred=" + (collectSettings().keys["nongZeroCred"] ? "LEAKED" : "no"));

    // ---- applying one --------------------------------------------------
    var mine = collectSettings();                 // keep, to put back after
    applySettings({kind:"mice-studio-settings", version:1,
                   rig: RIG, keys:{ "nong_sidew":"421" }}, "qc");
    out.push("applied=" + (localStorage.getItem("nong_sidew") === "421" ? "yes" : "no"));

    // ---- rubbish is refused, not half-applied --------------------------
    try {
      applySettings({hello:"world"}, "qc");
      out.push("reject=no");
    } catch (e) { out.push("reject=yes"); }
    try {
      applySettings(null, "qc");
      out.push("rejectnull=no");
    } catch (e) { out.push("rejectnull=yes"); }

    applySettings(mine, "qc");                    // restore
    report(out.join("~"));
  }catch(e){ report("ERR~" + String(e).slice(0,70)); }
  setTimeout(function(){ report("done"); }, 300);
}, 1500); });
"""


def run(t):
    # ---- the hub side: store, serve, refuse rubbish ---------------------
    fake_serial.reset()
    base, main = F.start_hub()
    if main.SETTINGS_FILE.exists():
        main.SETTINGS_FILE.unlink()

    s, b = F.get(base + "/api/settings")
    t.contains(b, "no settings", "a hub with nothing shared says so, plainly",
               )

    import urllib.request
    req = F._with_cookie(urllib.request.Request(base + "/api/settings",
                                 data=json.dumps({"bundle": BUNDLE}).encode(),
                                 method="POST"))
    with urllib.request.urlopen(req, timeout=20) as r:
        posted = json.loads(r.read().decode())
    t.ok(posted.get("ok"), "a bundle can be shared from this PC", posted)
    t.ok(main.SETTINGS_FILE.is_file(), "and it lands on disk, so it survives a restart")

    s, b = F.get(base + "/api/settings")
    got = json.loads(b)
    t.eq(got.get("kind"), "mice-studio-settings", "the hub serves it back")
    t.ok(got.get("savedAt"), "stamped with when it was shared")
    t.ok(got.get("savedBy"), "and which PC shared it, so you can tell them apart")

    bad = F._with_cookie(urllib.request.Request(base + "/api/settings",
                                 data=json.dumps({"bundle": {"nope": 1}}).encode(),
                                 method="POST"))
    try:
        with urllib.request.urlopen(bad, timeout=20) as r:
            body = r.read().decode()
    except Exception as e:  # noqa: BLE001
        body = getattr(e, "read", lambda: b"")().decode() or str(e)
    t.ok("settings bundle" in body.lower(),
         "anything that is not a bundle is refused",
         "a bad POST would overwrite a good setup")

    # ---- the network route, through the hub -----------------------------
    # Point it at THIS hub: proves the proxy fetches and returns, without
    # needing a second PC.
    host = base.split("//", 1)[1]
    s, b = F.get(base + "/api/settings/peer?host=" + urllib.parse.quote(host))
    t.eq(s, 200, "the hub fetches another PC's settings on the page's behalf")
    t.contains(b, "mice-studio-settings", "and hands back what it found")

    s, b = F.get(base + "/api/settings/peer?host=")
    t.contains(b.lower(), "need host", "with a clear message when no PC is named")
    s, b = F.get(base + "/api/settings/peer?host=10.255.255.1:9")
    t.contains(b.lower(), "cannot reach",
               "and when the other PC is not there, it says so rather than hanging")

    s, b = F.get(base + "/api/hubs")
    t.eq(s, 200, "other hubs on the network can be listed")
    t.ok("hubs" in json.loads(b), "as a list to choose from")

    # the browser must not be asked to do the cross-origin fetch itself
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.ok("/api/settings/peer" in app,
         "the page pulls THROUGH its own hub, not straight from the other PC",
         "a direct cross-origin fetch is blocked by the browser")

    # ---- the browser side -----------------------------------------------
    if not browser.available():
        t.give_up("headless Edge not found — the rest needs a browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=22)

    marks = [m for m in fake_serial.qc_marks if "~" in m]
    if not t.ok(marks, "the settings driver reported",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    g = dict(kv.split("=", 1) for kv in marks[-1].split("~") if "=" in kv)
    if "ERR" in g:
        t.ok(False, "the driver ran without throwing", g["ERR"])
        return

    t.eq(g.get("kind"), "mice-studio-settings", "the export is stamped as ours")
    t.eq(g.get("hasrig"), "yes", "and carries the rig")
    t.eq(g.get("sidew"), "yes", "and the other remembered settings")
    t.eq(g.get("nocred"), "no",
         "but NOT the zero-calibration login — that is per machine")
    t.eq(g.get("applied"), "yes", "importing puts the settings into this browser")
    t.eq(g.get("reject"), "yes", "a file that is not an export is refused")
    t.eq(g.get("rejectnull"), "yes", "and so is nothing at all")

    idx = (F.STUDIO / "web/index.html").read_text(encoding="utf-8", errors="replace")
    for want in ("exportSettings()", "importSettingsFile(", "shareSettings()",
                 "findHubs()", "getSettingsFrom()"):
        t.contains(idx, want, "the UI offers %s" % want.rstrip("(）)"))
    t.contains(idx, 'data-stab="setup"',
               "and the card belongs to a tab, so it is not on every screen")
