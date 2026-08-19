"""A network name with a space in it can actually be saved from the web page.

Found by a second model reading the same code, after the parser had been
"covered" for months. It is the clearest example in this project of a test
proving the wrong half of a feature.

`wifiargs::parse` handles quoting correctly and is well tested — see
firmware/test/test_logic/test_main.cpp, which asserts that
`"MSI 3058" mypass` splits into ssid "MSI 3058" and password "mypass". Those
tests passed, and always had.

The bug was in the CALLER. `saveSettings()` in the module website sent

    SET WIFI  + ssid + ' ' + pass

with no quotes at all. wifiargs::parse documents that an UNQUOTED first
argument is "the ssid up to the first space", so a real network called
"MSI 3058" was stored as ssid "MSI" with password "3058 <the real password>".
The board then never joined, and every read-back showed exactly what the user
had typed — the failure is invisible from the page. The SSID field even
carried a `placeholder="no spaces"`, which had quietly turned a defect into an
instruction to the user.

Network names contain spaces constantly, phone hotspots most of all. So this
check asserts the half that was missing: what the PAGE actually sends.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "wifi"
TITLE = "a WiFi name with a space in it can be saved"
SLOW = True

# Drives the real saveSettings() with a real spaced SSID, capturing the command
# instead of sending it. Asserting on the command that would reach the board —
# not on what the page says about itself.
PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="%s"></iframe>
<script>
function done(s){ qcMark("WS " + s); qcMark("done"); }
setTimeout(function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = w.document;
    if (typeof w.saveSettings !== 'function') return done("missing=saveSettings");

    var sent = [];
    w.cmd = function(c){ sent.push(c); return Promise.resolve("OK"); };
    w.alert = function(){};
    w.confirm = function(){ return true; };

    // a real network name, and a password that also has a space in it
    d.getElementById('setSsid').value = 'MSI 3058';
    d.getElementById('setPass').value = 'my pass word';
    var sid = d.getElementById('setId'); if (sid) sid.value = '';
    var snm = d.getElementById('setName'); if (snm) snm.value = '';
    var sty = d.getElementById('setType'); if (sty) sty.value = '';

    w.saveSettings();
    setTimeout(function(){
      var line = sent.filter(function(c){ return c.indexOf('SET WIFI') === 0; })[0] || 'none';
      var ph = (d.getElementById('setSsid').getAttribute('placeholder') || '');
      done("cmd=" + encodeURIComponent(line) + " ph=" + encodeURIComponent(ph));
    }, 1200);
  } catch (e) { done("ERR=" + String(e).slice(0,60)); }
}, 4500);
</script>
"""


def _split(rest):
    """The same rule wifiargs::parse applies, so the check reasons as the
    firmware does rather than guessing from the string."""
    rest = rest.strip()
    if rest.startswith('"'):
        end = rest.find('"', 1)
        if end < 0:
            return None, None
        return rest[1:end], rest[end + 1:].strip().strip('"')
    a, _, b = rest.partition(" ")
    return a, b.strip().strip('"')


def run(t):
    ui = (F.CODE / "firmware/src/web/WebUI.h").read_text(encoding="utf-8",
                                                         errors="replace")

    # ---- the field no longer teaches the user to work around the bug ----
    i = ui.find('id="setSsid"')
    j = ui.find(">", i)
    field = ui[i:j] if i >= 0 else ""
    t.ok(i >= 0, "the WiFi name field exists")
    t.ok("no spaces" not in field,
         "the WiFi name field does not tell the user to avoid spaces",
         "spaces are legal in a network name; the placeholder was covering "
         "for a bug in what the page sent")

    # ---- and what it SENDS is quoted ------------------------------------
    k = ui.find("async function saveSettings(")
    body = ui[k:ui.find("\n}", k)] if k >= 0 else ""
    t.ok(k >= 0, "saveSettings exists")
    t.contains(body, 'SET WIFI "',
               "the network name is sent quoted, so a space stays part of it")

    # ---- driven for real, in a browser ----------------------------------
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(PAGE % ("/mod?dev=usb%3A" + fake_serial.PORT), base, seconds=22)

    marks = [m for m in fake_serial.qc_marks if m.startswith("WS ")]
    if not t.ok(marks, "the module page reported back",
                "the page never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    last = marks[-1][3:]
    if "ERR=" in last or "missing=" in last:
        t.ok(False, "saving settings ran without throwing", last)
        return
    from urllib.parse import unquote
    got = dict(kv.split("=", 1) for kv in last.split(" ") if "=" in kv)
    line = unquote(got.get("cmd", ""))
    t.ok(line.startswith("SET WIFI "), "a SET WIFI command was sent", line)

    ssid, pw = _split(line[len("SET WIFI "):])
    # This is the whole point. Before the fix the firmware saw ssid "MSI",
    # password "3058 my pass word", and the board silently never connected.
    t.eq(ssid, "MSI 3058",
         "the board receives the WHOLE network name, space included")
    t.eq(pw, "my pass word",
         "and the password is its own argument, not the rest of the name")
