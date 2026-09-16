"""One module is ONE row, whichever PC is holding it — and Home shows them.

Asked for on 2026-08-21, in the same breath as two other complaints about the
same screen: *the module make it list the module only once for me please... make
it list once show which module arviable on the top*, and *the home it look
noting show ... show only connected each module and connect from what it hard to
use*.

Both had the same cause. The hub merged the ways in that IT could see (cable,
WiFi, the RS485 bus behind a dongle) but a board plugged into the laptop next
door arrived from a different endpoint and was drawn in a card of its own
further down the page. So one robot was two rows, on two parts of the screen,
with different buttons — and which of them you happened to press decided which
machine carried the command. Home meanwhile counted them and printed a
sentence, which is a summary of a screen somebody then had to go and find.

What is held here:

  * a board reachable from HERE and from another PC is one entry, carrying both
    ways in as routes. The merge is done in `modules_everywhere` and not in the
    page, because `board_key` is the answer to *is this the same board* and it
    already lives in the hub;
  * every row says how it is reached, naming the far PC — the detail the
    separate card used to carry as a heading;
  * a board only the other PC can see is still openable from here, through that
    PC;
  * Home draws the rows themselves;
  * and Tools is the first tab, which is the third thing asked for in the same
    message.
"""
import json
import re

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "one module is one row, wherever it is plugged in, and Home shows them"
SLOW = True

FAR_HOST = "LAB-LAPTOP"
FAR_IP = "10.0.0.5"
# The SAME board this PC has on COM99, as the other PC sees it: same chip, so
# the merge has to recognise it. A different chip would prove nothing - two
# boards drawn as two rows is what should happen.
SHARED = {"id": 1, "name": "nong-test", "type": "nong", "chip": fake_serial.CHIP,
          "dev": "hub:%s/usb:COM7" % FAR_IP, "host": FAR_HOST, "hostIp": FAR_IP}
# ...and one that only the other PC can reach at all.
THEIRS = {"id": 42, "name": "lab-pair", "type": "nong", "chip": "BB11CC22DD33",
          "dev": "hub:%s/usb:COM8" % FAR_IP, "host": FAR_HOST, "hostIp": FAR_IP}

PAGE = """
<style>html,body{margin:0}iframe{width:1280px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function sleep(ms){ return new Promise(function(go){ setTimeout(go, ms); }); }
document.getElementById('f').addEventListener('load', async function(){
  var d = this.contentDocument;
  // The list arrives from several scans. Waiting for TWO ROWS is a bet on
  // how fast the machine is today - the far-PC answers can land seconds
  // after the local cable rows, and a read before them measures an early
  // frame: an unnamed row, a missing lab-pair, a via without its host.
  // Failed exactly so in both gates of 2026-08-25 with real boards on the
  // bench slowing the sweep, and passed alone twice - the signature.
  function hasFar(){
    return [].slice.call(d.querySelectorAll('#mods .mod .nm')).some(
      function(n){ return n.textContent.trim() === 'lab-pair'; });
  }
  var until = Date.now() + 30000;
  while ((d.querySelectorAll('#mods .mod').length < 2 || !hasFar())
         && Date.now() < until)
    await sleep(250);
  await sleep(500);                       // let the vias finish drawing too
  function rows(sel){
    return [].slice.call(d.querySelectorAll(sel)).map(function(r){
      var nm = r.querySelector('.nm'), via = r.querySelector('.via');
      return {name: (nm ? nm.textContent : '').trim(),
              via: (via ? via.textContent : '').trim()};
    });
  }
  var list = rows('#mods .mod');
  var home = rows('#homeMods .mod');
  var tabs = [].slice.call(d.querySelectorAll('#tabs [data-go]'))
               .map(function(b){ return b.getAttribute('data-go'); });
  qcMark('LIST rows=' + list.length
       + ' names=' + list.map(function(r){ return r.name; }).join('|')
       + ' home=' + home.length
       + ' homevia=' + d.querySelectorAll('#homeMods .via').length
       + ' listvia=' + d.querySelectorAll('#mods .via').length
       + ' hometools=' + d.querySelectorAll('#homeTools .mod').length
       + ' homeopen=' + d.querySelectorAll('#homeMods .mod button.primary').length
       + ' tabs=' + tabs.join(',')
       + ' firsttab=' + (tabs[0] || '-'));
  // The whole Modules tab, counted per NAME: a board must appear once on the
  // screen, not once per card that happens to know about it. The cable card
  // has to have finished probing first - counting before it draws anything
  // measures a page with nothing in it, and the duplicate this exists to catch
  // is drawn by that very card.
  await this.contentWindow.scanUsb();
  var deadline = Date.now() + 15000;
  while (!d.querySelector('#usbmods .via, #usbmods .mod')
         && Date.now() < deadline) await sleep(250);
  var seen = {};
  [].slice.call(d.querySelectorAll('[data-tab=modules] .mod .nm')).forEach(
    function(n){ var k = n.textContent.trim(); seen[k] = (seen[k] || 0) + 1; });
  qcMark('DUPES ' + Object.keys(seen).map(function(k){
    return k.replace(/ /g, '~') + '=' + seen[k]; }).join(' '));
  var sum = d.getElementById('homeSum');
  qcMark('SUM ' + (sum ? sum.textContent : 'missing').replace(/ /g, '~'));

  // ---- the count, with one board on each kind of way in ----------------
  // A rig with all four is not something a fake bench can produce, and the
  // sentence is the thing being tested, so the list is handed to the page.
  var w = this.contentWindow;
  var made = {ok: true, host: 'THISPC', lan: '10.0.0', errors: [], modules: [
    {id: 1, name: 'cabled', type: 'nong', chip: 'AA00',
     routes: [{kind: 'usb', dev: 'usb:COM9', port: 'COM9', mine: true}]},
    {id: 2, name: 'onbus', type: 'lift', chip: 'AA01',
     routes: [{kind: 'rs485', dev: 'usb:COM9:2', port: 'COM9', bus: 2, mine: true}]},
    {id: 3, name: 'onair', type: 'nong', chip: 'AA02', ip: '10.0.0.9',
     routes: [{kind: 'wifi', dev: 'wifi:10.0.0.9', ip: '10.0.0.9', mine: true}]},
    {id: 4, name: 'faraway', type: 'nong', chip: 'AA03',
     routes: [{kind: 'hub', dev: 'hub:10.0.0.5/usb:COM8', host: 'LAB-LAPTOP'}]}]};
  w.fetch = function(u){
    return Promise.resolve({json: function(){
      return Promise.resolve(String(u).indexOf('/api/modules') === 0
                             ? made : {ok: true, ports: [], modules: []}); }});
  };
  await w.scan(true);
  await sleep(400);
  qcMark('SUM2 ' + (sum ? sum.textContent : 'missing').replace(/ /g, '~'));

  // ---- and a board that renames itself stays ONE board ------------------
  made.modules[0].name = 'renamed-live';
  await w.scan(true);
  await sleep(400);
  var after = [].slice.call(d.querySelectorAll('#mods .mod .nm'))
                .map(function(n){ return n.textContent.trim(); });
  qcMark('RENAMED rows=' + after.length
       + ' names=' + after.join('|').replace(/ /g, '~'));
  list.forEach(function(r){
    qcMark('VIA ' + r.name.replace(/ /g, '~') + ' = '
           + (r.via || 'none').replace(/ /g, '~'));
  });
  qcMark('done');
});
</script>
"""


def _kv(marks, head):
    """The last `head k=v k=v` mark, as a dict."""
    got = [m for m in marks if m.startswith(head + " ")]
    if not got:
        return {}
    return dict(kv.split("=", 1)
                for kv in got[-1][len(head) + 1:].split(" ") if "=" in kv)


def _kv_line(marks, head):
    """The last `head <one string>` mark, with the spaces put back."""
    got = [m for m in marks if m.startswith(head + " ")]
    return got[-1][len(head) + 1:].replace("~", " ") if got else ""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()

    # This check counts EXACT rows, so nothing real may answer it: on
    # 2026-08-26 a full gate ran while the bench was powered for the first
    # time, the genuine lab-pair answered the live WiFi sweep at its own
    # address, and the fabricated far-PC lab-pair below made that two rows.
    # The cable side stays live - fake_serial IS the cabled world - only the
    # network sweep reaches real boards.
    real_remote = main.remote_modules
    real_scan = main.scan_modules
    main.scan_modules = lambda force=False: []
    main.MODULES.forget()
    main.remote_modules = lambda force=False: ([dict(SHARED), dict(THEIRS)], [])
    try:
        # ---- the merge itself -------------------------------------------
        code, body = F.get(base + "/api/modules/all")
        t.eq(code, 200, "the one-list endpoint answers")
        d = json.loads(body)
        mods = d.get("modules") or []
        names = [m.get("name") for m in mods]
        t.eq(len([n for n in names if n == "nong-test"]), 1,
             "a board this PC and another PC can both reach is ONE entry")
        shared = [m for m in mods if m.get("name") == "nong-test"][0]
        kinds = sorted(set(r.get("kind") for r in shared.get("routes") or []))
        t.ok("hub" in kinds and any(k in kinds for k in ("usb", "rs485", "wifi")),
             "carrying both ways in, not just the one that was found first",
             "routes: %r" % (shared.get("routes"),))
        far = [r for r in shared["routes"] if r.get("kind") == "hub"][0]
        t.eq(far.get("host"), FAR_HOST,
             "and the far route names the PC that holds it")
        mine = [r for r in shared["routes"] if r.get("kind") != "hub"][0]
        t.eq(mine.get("mine"), True, "while this PC's own route says so")

        theirs = [m for m in mods if m.get("name") == "lab-pair"]
        t.eq(len(theirs), 1, "a board only the other PC can see is listed too")
        t.ok(theirs and theirs[0]["routes"][0]["dev"].startswith("hub:"),
             "openable through that PC",
             "the row needs a dev the hub can forward: %r" % (theirs,))

        # ---- a rename, and the answer that arrives too late --------------
        # The row flipped between the old name and the new one every few
        # seconds: renaming a board is answered at once on the cable, while the
        # WiFi sweep keeps handing back the record it last heard for the whole
        # grace period - and that late record was allowed to write the name
        # back. The person who has just renamed a board then cannot tell which
        # one they are looking at, which is the complaint this whole task
        # started from.
        real_usb, real_wifi = main.probe_usb_all, main.scan_modules
        try:
            main.probe_usb_all = lambda force=False: [
                {"port": "COM9", "rs485": [],
                 "module": {"id": 1, "chip": "AA", "name": "new-name",
                            "type": "nong"}}]
            main.scan_modules = lambda force=False: [
                {"id": 1, "chip": "AA", "name": "old-name", "type": "nong",
                 "ip": "10.0.0.9", "stale": True, "lastSeen": 12}]
            one = main.modules_here(True)
            t.eq(len(one), 1, "a renamed board is one board on both routes")
            t.eq(one[0].get("name"), "new-name",
                 "and a route that has gone quiet cannot rename it back")
            t.eq(one[0].get("ip"), "10.0.0.9",
                 "though a late answer may still add what nothing else knows")
        finally:
            main.probe_usb_all, main.scan_modules = real_usb, real_wifi
            main.MODULES.forget() if hasattr(main, "MODULES") else None

        # ---- and the page draws it that way ------------------------------
        fake_serial.reset()
        browser.raw_page(PAGE, base, seconds=45)
        marks = fake_serial.qc_marks
        head = [m for m in marks if m.startswith("LIST ")]
        if not t.ok(head, "the page reported back",
                    "nothing ran: %r" % (marks[-3:],)):
            return
        got = dict(kv.split("=", 1) for kv in head[-1][5:].split(" ") if "=" in kv)
        drawn = [n for n in got.get("names", "").split("|") if n]
        t.eq(len([n for n in drawn if n == "nong-test"]), 1,
             "the page draws that board once, not once per PC that can see it")
        t.contains(drawn, "lab-pair",
                   "and lists the one only the other PC can reach")
        t.ok(int(got.get("home", "0")) == int(got.get("rows", "-1")),
             "Home shows the same modules, not a count of them",
             "Home drew %s rows against the list's %s — Home used to carry one "
             "sentence and a button, which is a summary of a screen you then "
             "had to go and find" % (got.get("home"), got.get("rows")))
        t.ok(int(got.get("hometools", "0")) > 0,
             "and the tools are on Home too",
             "opening Studio took a tab, a scroll and a click")

        # ---- short on Home, long on the Modules tab ----------------------
        # Asked for 2026-08-22: *make the home show the each module once easy
        # to use but in module you show like before which from what*.
        t.eq(got.get("homevia"), "0",
             "Home says which modules are here, and no more than that")
        t.ok(int(got.get("listvia", "0")) >= 2,
             "while the Modules tab still says how each one is reached",
             "the ways in - which cable, which PC, which bus - were asked for "
             "on that tab specifically: %s" % got.get("listvia"))
        t.ok(int(got.get("homeopen", "0")) >= 2,
             "and every Home row can still be opened",
             "a shorter row is not a row with nothing to press: %s"
             % got.get("homeopen"))

        # ---- the tab bar -------------------------------------------------
        # Tools went first on 2026-08-21 to make it reachable, which put the
        # tab the page OPENS on in second place. Corrected the next morning:
        # the leftmost tab and the landing tab are the same one again, and
        # Tools keeps the place beside it.
        tabs = got.get("tabs", "").split(",")
        t.eq(got.get("firsttab"), "home",
             "Home is the first tab, and the one the page opens on")
        t.ok(tabs[1:2] == ["tools"],
             "with Tools right beside it",
             "it was the fifth tab and nobody found it; the bar reads %r" % tabs)

        # ---- once on the SCREEN, not once per card ------------------------
        # Reported 2026-08-22: *i found the problem it show more than 1 time
        # that why i consern this user don't know which module*. The board on
        # this PC's cable was drawn in the one list AND again as a full row
        # inside the cable card below it.
        dupes = _kv(marks, "DUPES")
        twice = {k: v for k, v in dupes.items() if v.isdigit() and int(v) > 1}
        t.ok(not twice, "no module is drawn twice on the Modules tab",
             "%r — a robot listed twice is a robot somebody has to guess about, "
             "and the two rows were not even the same: one drove it down the "
             "cable and the other through the PC that holds it" % twice)

        # ---- and Home counts them per way in ------------------------------
        # Asked for 2026-08-22: *show which module connect now from wifi how
        # many from rs485 from usb*. USB and RS485 were one number ("on a
        # cable"), which hides the difference that matters when a board is
        # missing: one is in your hand, the other is behind another board.
        said = _kv_line(marks, "SUM")
        t.contains(said, "module", "Home still says how many modules there are")
        four = _kv_line(marks, "SUM2")
        for word in ("4 modules", "1 on a USB cable", "1 on the RS485 bus",
                     "1 over WiFi", "1 through another PC"):
            t.contains(four, word,
                       "Home counts them per way in: %r" % word)

        # ---- a board that renames itself ---------------------------------
        # Asked 2026-08-22: *if that module change it own name what happen?*
        # It is the same board - the merge is on the chip, which cannot be
        # renamed - so it must stay one row and take the new name.
        ren = _kv(marks, "RENAMED")
        t.eq(ren.get("rows"), "4",
             "a board that renames itself is still one row, not two")
        t.contains(ren.get("names", ""), "renamed-live",
                   "and the row shows the name it has now")
        t.ok("cabled" not in ren.get("names", ""),
             "with the old name gone",
             "both names on screen means two rows for one board: %s"
             % ren.get("names"))

        via = dict(m[4:].split(" = ", 1) for m in marks if m.startswith("VIA "))
        t.contains(via.get("lab-pair", ""), FAR_HOST,
                   "the row for a far board says which PC it goes through")
        t.contains(via.get("nong-test", ""), FAR_HOST,
                   "and a shared board names that PC as well as its own cable")
        t.contains(via.get("nong-test", ""), "COM99",
                   "without losing the cable in front of you")
    finally:
        main.remote_modules = real_remote
        main.scan_modules = real_scan
        main.MODULES.forget()
