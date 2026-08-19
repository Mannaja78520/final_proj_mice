"""One board is one row, however many ways the hub can reach it.

The fault: a module plugged in AND on the WiFi appeared twice on the module
screen, as two robots. The two rows were not even equivalent - one sent
commands down the cable, the other over the air - so which copy someone
happened to click decided how the robot was driven.

Merging on the wrong thing is the trap, and this check is mostly about that:

  * the ID is a byte someone sets, and two blank boards out of one box share a
    default. Merging on it turns two robots into one, which is far worse than
    showing one robot twice: a command meant for one arm goes to the other.
  * the NAME is typed and changes.
  * the CHIP MAC cannot be changed by anyone, so that is the key - and a board
    running older firmware that reports no chip still has to work.

All three cases are driven here against the hub, with the WiFi probe standing
in for a network, because none of them can be told apart by looking at one
board.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "one board is one row, however it is reached"
SLOW = True



# The fault was VISIBLE - two rows for one robot - so the screen is driven too.
# A merged endpoint that the page ignores fixes nothing.
PAGE_ROWS = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("ID " + s); qcMark("done"); }
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (typeof w.scan !== 'function') return done("missing=scan");
    var reply = function(o){
      return Promise.resolve({ json: function(){ return Promise.resolve(o); } });
    };
    // One board, two ways to reach it - exactly what the hub now returns.
    w.fetch = function(u){
      u = String(u);
      if (u.indexOf('/api/modules') >= 0)
        return reply({ok: true, lan: '10.0.0', modules: [{
          id: 1, name: 'armA', type: 'nong', chip: 'A0B1C2D3E4F5',
          key: 'chip/A0B1C2D3E4F5',
          routes: [{kind: 'usb', dev: 'usb:COM9', port: 'COM9'},
                   {kind: 'wifi', dev: 'wifi:10.0.0.9', ip: '10.0.0.9'}]}]});
      return reply({ports: [], modules: [], ok: true});
    };
    await w.scan(true);
    var rows = [].slice.call(d.querySelectorAll('#mods .mod'));
    var names = rows.map(function(r){
      var n = r.querySelector('.nm'); return n ? n.textContent : '?'; });
    var text = rows.length ? rows[0].textContent.replace(/[^A-Za-z0-9]+/g, "_") : "";
    done(["rows=" + rows.length,
          "names=" + names.join(",").replace(/[^A-Za-z0-9,]+/g, "_"),
          "says=" + text.slice(0, 90)].join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,50)); }
}, 4000);
</script>
"""

def _mods(base, force=False):
    r = json.loads(F.get(base + "/api/modules" + ("?force=1" if force else ""))[1])
    return r.get("modules", [])


def _kinds(mod):
    return sorted(r["kind"] for r in mod.get("routes", []))


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT

    # The same board, answering on WiFi as well as on its cable. probe_module
    # is looked up when it runs (discovery passes probes as wrappers), so this
    # stands in for a network without one.
    def on_wifi(ip, timeout=0.6):
        if ip.endswith(".77"):
            return {"id": 1, "name": "nong-test", "type": "nong",
                    "chip": fake_serial.CHIP, "ip": ip}
        return None

    real_probe = main.probe_module
    main.probe_module = on_wifi
    main.MODULES.forget()
    try:
        mods = _mods(base, force=True)
        cabled = [m for m in mods if "usb" in _kinds(m)]
        t.ok(cabled, "the board on the cable is listed", json.dumps(mods)[:300])

        one = cabled[0]
        t.contains(str(_kinds(one)), "wifi",
                   "and the SAME board carries its WiFi route, not a second row")
        t.eq(len([m for m in mods if m.get("chip") == fake_serial.CHIP]), 1,
             "one board, one entry")
        t.ok(any(r.get("port") == port for r in one["routes"]),
             "the cable route names the port", json.dumps(one["routes"]))
        t.ok(any(r.get("ip", "").endswith(".77") for r in one["routes"]),
             "and the WiFi route names the address")

        # ---- two boards that SHARE an id are still two boards ---------
        def two_boards(ip, timeout=0.6):
            if ip.endswith(".77"):
                return {"id": 1, "name": "other-arm", "type": "nong",
                        "chip": "FFEEDDCCBBAA", "ip": ip}
            return None

        main.probe_module = two_boards
        main.MODULES.forget()
        mods = _mods(base, force=True)
        # The fake bus carries a THIRD board of its own (the one that answers a
        # broadcast late, added when the fake stopped pretending a bus is
        # instant). So this asks about the two boards under test rather than
        # about the size of the list - which is the honest question anyway.
        want = {fake_serial.CHIP, "FFEEDDCCBBAA"}
        mine = [m for m in mods if (m.get("chip") or "") in want]
        t.eq(len(mine), 2,
             "two boards that share an id are two boards, not one")
        chips = sorted((m.get("chip") or "") for m in mine)
        t.eq(chips, sorted(want), "and each keeps its own chip")

        # ---- a thin answer must not erase a fuller one ---------------
        # A board answering a sweep while it is still booting reports its chip
        # and almost nothing else. Letting that win blanks the name and type
        # the cable already learned, and the row turns into an anonymous
        # question mark while the board is sitting right there.
        def half_awake(ip, timeout=0.6):
            if ip.endswith(".77"):
                return {"id": 1, "chip": fake_serial.CHIP, "name": "", "type": "",
                        "ip": ip}
            return None

        main.probe_module = half_awake
        main.MODULES.forget()
        mods = _mods(base, force=True)
        mine = [m for m in mods if m.get("chip") == fake_serial.CHIP]
        t.eq(len(mine), 1, "a half-awake answer is still the same board")
        t.eq(mine[0].get("name"), "nong-test",
             "and it does not blank the name the cable already knew")
        t.eq(mine[0].get("type"), "nong", "nor the type")

        # ---- older firmware, which reports no chip at all -------------
        def old_firmware(ip, timeout=0.6):
            if ip.endswith(".78"):
                return {"id": 9, "name": "old-arm", "type": "lift", "ip": ip}
            return None

        main.probe_module = old_firmware
        main.MODULES.forget()
        mods = _mods(base, force=True)
        old = [m for m in mods if m.get("name") == "old-arm"]
        t.eq(len(old), 1, "a board with no chip is still listed")
        t.ok(old and old[0].get("key", "").startswith("id/"),
             "identified by its id, because that is all it offers",
             old[0].get("key") if old else "missing")
    finally:
        main.probe_module = real_probe
        main.MODULES.forget()

    # ---- the key itself, at the edges -------------------------------
    t.eq(main.board_key({"chip": "a0b1c2"}), main.board_key({"chip": "A0B1C2"}),
         "the chip is matched whatever case it arrives in")
    t.ok(main.board_key({"id": 1, "type": "nong"})
         != main.board_key({"id": 1, "type": "lift"}),
         "without a chip, two ids match only when the type matches too",
         "two blank boards out of one box share a default id")
    t.ok(main.board_key({"chip": "A1"}) != main.board_key({"id": 1}),
         "and a board with a chip is never confused with one without")

    # ---- and the SCREEN shows one row --------------------------------
    if not browser.available():
        return
    fake_serial.reset()
    browser.raw_page(PAGE_ROWS, base, seconds=25)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("ID "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                got[k] = v
    if not t.ok(got, "the module screen reported back",
                "%r" % (fake_serial.qc_marks[-3:],)):
        return
    t.eq(got.get("rows"), "1",
         "a board on a cable AND on the WiFi is ONE row, not two")
    t.eq(got.get("names"), "armA", "and it is named once")
    t.contains(got.get("says", ""), "COM9",
               "the row says it can be reached on the cable")
    t.contains(got.get("says", ""), "WiFi",
               "and over WiFi, so nobody has to guess which row does what")

