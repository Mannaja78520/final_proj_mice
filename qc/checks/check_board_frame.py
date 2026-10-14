"""The board's own site and the light-strip page wear the hub pages' head.

Web stage 4 (A41-5), from the audit of 2026-10-14 (A41-1: *each web page goes
its own way, hard to use - make it the same everywhere*):

  * the module page had a head of its own: name and badges, then "← back to
    the hub" on the RIGHT, and the technical switch alone on a line under it.
    Every hub page now starts with "← Hub" and ends with the switch. The board
    serves this page from flash, where mice-ui.js does not fit (mice_nong is
    near its OTA slot), so the same markup is written out by hand there;
  * the light-strip page (rgb.html) had a "← hub" link in a caption and its
    own address spelling, ?ip= or ?port=&id=, where every other page says
    ?dev=usb:COM5. It now takes ?dev= (old links still work) and talks to
    /api/dev/cmd like the module page;
  * logged out, the module page asked LIMIT? and CAM LIST, got 401 and left
    the start pose and the camera settings empty with no reason. A query is
    now free through the hub, as on the board itself (check_hub_auth holds the
    gate); CAM also changes settings, so its panel says who to log in to.

Asserted on what reached the module (fake_serial.wire), not on the page's words.
"""
import re
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "design"
TITLE = "the board site and the light-strip page wear the shared head"
SLOW = True


def _src():
    page = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    rgb = (F.HUB / "web" / "rgb.html").read_text(encoding="utf-8", errors="replace")
    mods = (F.HUB / "web" / "home" / "parts" / "modules.js").read_text(encoding="utf-8")
    return page, rgb, mods


def run(t):
    page, rgb, mods = _src()

    # ---- the board site: the same head, written out ----------------------
    head = page[page.find('<header class="topbar">'):]
    head = head[:head.find("</header>")]
    t.ok(head, "the module page has the shared head (<header class=\"topbar\">)")
    back, name = head.find('id="hubBack"'), head.find('id="hname"')
    t.ok(0 <= back < name, "the way back to the hub comes first, before the name",
         "it used to sit on the right after the badges")
    t.ok('class="topbar-home"' in head[back - 40:back + 60],
         "and it is drawn as the shared '← Hub' button")
    t.ok(head.count('id="advOn"') == 1 and page.count('id="advOn"') == 1
         and 'class="topbar-adv' in head,
         "one technical switch, last in the head", head[-300:])
    t.ok("back to the hub" not in page and "module-options" not in page,
         "no hand-made way back or switch line is left")

    # ---- logged out: a camera panel says why it is empty ----------------
    cam = page[page.find("async function camLoad("):]
    cam = cam[:cam.find("\nasync function ", 10)]
    t.ok("refusal(txt)" in cam and "camLocked=true" in cam,
         "a refused CAM LIST says who to log in to, and waits for a login", cam[:300])
    t.ok("addEventListener('mice-login',camRetry)" in page,
         "and the panel asks again once somebody logs in")

    # ---- the light-strip page: shared parts, one address ----------------
    t.ok('src="/mice-ui.js"' in rgb and '<header class="topbar">' in rgb
         and '<body class="page">' in rgb,
         "rgb.html is built from the shared parts and head")
    t.ok("/api/usb/cmd" not in rgb and "/api/robot/cmd" not in rgb
         and "/api/dev/cmd?dev=" in rgb,
         "rgb.html talks to /api/dev/cmd, like the module page")
    t.ok("qp.get('dev')" in rgb, "and reads the module page's ?dev= address")
    t.ok(re.search(r"/rgb\.html\?dev=", mods),
         "Home opens it with ?dev=", "main_python/web/home/parts/modules.js")

    if not browser.available():
        t.ok(True, "browser part skipped: no headless browser here")
        return

    # ---- in a real browser, LOGGED OUT: head order and the start pose ----
    base, _main = F.start_hub()
    fake_serial.reset()
    dev = urllib.parse.quote("usb:" + fake_serial.PORT)
    browser.raw_page("""
<style>html,body{margin:0}#f{width:1280px;height:900px;border:0}</style>
<script>
(async function(){
  await fetch("/api/logout", {method: "POST"});
  var fr = document.createElement("iframe");
  fr.id = "f"; fr.src = "/mod?dev=%(dev)s";
  document.body.appendChild(fr);
  var d = function(){ return fr.contentDocument; };
  var filled = await qcWaitFor(function(){
    var v = d() && d().getElementById("hv1");
    return v && v.value !== "";
  }, 25000);
  var h = d().querySelector("header.topbar");
  var kids = h ? Array.prototype.map.call(h.children, function(e){
    return e.id || e.className.split(" ")[0]; }) : [];
  var back = d().getElementById("hubBack");
  var who = await (await fetch("/api/whoami")).json();
  var out = "BF filled=" + (filled ? "yes" : "no")
    + " first=" + (kids[0] || "none") + " last=" + (kids[kids.length - 2] || "none")
    + " back=" + (back && !back.hidden ? back.getAttribute("href") : "hidden")
    + " authed=" + (who.authed ? "yes" : "no")
    + " stat=" + (d().getElementById("homeStat").textContent || "-")
      .replace(/[^A-Za-z]+/g, "_").slice(0, 30);
  // Marks go over a gated route: log back in before reporting.
  var x = new XMLHttpRequest();
  x.open("POST", "/api/login", false);
  x.setRequestHeader("Content-Type", "application/json");
  x.send(JSON.stringify({password: "%(pw)s"}));
  await qcMark(out.replace(/ /g, "~"));
  qcMark("done");
})();
</script>""" % {"dev": dev, "pw": F.HUB_PASSWORD}, base, seconds=60)
    got = next((m.replace("~", " ") for m in fake_serial.qc_marks
                if m.startswith("BF")), "")
    t.ok(got, "the module page reported back", fake_serial.qc_marks[-3:])
    t.ok(" authed=no" in got, "it was measured logged out", got)
    t.ok(" first=hubBack " in got and " back=/ " in got,
         "logged out, the head opens with '← Hub' to the hub serving it", got)
    t.ok(" last=topbar-adv " in got,
         "and ends with the technical switch (the badges line under it)", got)
    t.ok("filled=yes" in got,
         "logged out, the start pose is read and shown, not left blank", got)
    sent = [c.upper() for _, c in fake_serial.wire]
    t.ok(any(c.startswith("LIMIT?") for c in sent),
         "because LIMIT? reached the module", sent[-8:])

    # ---- the light-strip page reaches the module on ?dev=, and old links
    fake_serial.reset()
    browser.raw_page("""
<script>
window.addEventListener("load", async function(){
  for (const q of ["dev=%(dev)s", "port=%(port)s"]) {
    var fr = document.createElement("iframe");
    fr.src = "/rgb.html?" + q + "&name=strip";
    document.body.appendChild(fr);
    await qcWaitFor(function(){
      var b = fr.contentDocument && fr.contentDocument.querySelector("button[onclick*='solid']");
      return b && fr.contentWindow.cmd;
    }, 15000);
    var top = fr.contentDocument.querySelector("header.topbar .topbar-home");
    await qcMark("RGB " + q.split("=")[0] + " home=" + (top ? top.getAttribute("href") : "none"));
    await fr.contentWindow.cmd("RGB EFFECT solid", 0, "effectStat");
    fr.remove();
  }
  qcMark("done");
});
</script>""" % {"dev": dev, "port": urllib.parse.quote(fake_serial.PORT)}, base, seconds=40)
    marks = fake_serial.qc_marks
    t.ok("RGB dev home=/" in marks and "RGB port home=/" in marks,
         "rgb.html wears the shared head ('← Hub' first)", marks[-4:])
    solid = [c for _, c in fake_serial.wire if c.upper().startswith("RGB EFFECT SOLID")]
    t.ok(len(solid) >= 2,
         "and its command reached the module on ?dev= and on an old ?port= link",
         [c for _, c in fake_serial.wire][-8:])
