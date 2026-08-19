"""When something fails on the board's page, the page says so.

Four handlers on the module site caught an error and did nothing with it, and
each one ended with the page showing a state the board was not in:

  * a re-login after a password change, ignored - so Setup opened on a dead
    session: every card visible, every action behind it refused, nothing said;
  * `mustChange` read from a body that might not parse - swallowing it left the
    previous answer, false, so a board still carrying the shipped password
    stopped asking anyone to change it. The security prompt turning itself off;
  * logout, fired and forgotten, directly under a comment promising that a
    logout reaches the board so the cookie cannot serve whoever sits down next;
  * a file list, which left an empty dropdown - and an empty dropdown already
    means "nothing on this card", so a failed read looked like an empty SD.

Driven in a browser with the failures forced, because every one of these is
invisible from the inside: the code runs, nothing throws, and the page is
simply wrong about the board.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "the board page says when something failed"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="%s"></iframe>
<script>
function done(s){ qcMark("ER " + s); qcMark("done"); }
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    var out = [];

    // ---- the file list, when the card cannot be read ----------------
    if (typeof w.loadList === 'function') {
      var real = w.fetch;
      w.fetch = function(u){
        if (String(u).indexOf('/api/files') >= 0) return Promise.reject(new Error('no card'));
        return real.apply(w, arguments);
      };
      var sel = d.getElementById('moveSel') || d.querySelector('select');
      if (sel) {
        await w.loadList('/moves', 'moveSel');
        var txt = (sel.textContent || '').toLowerCase();
        out.push("files=" + (txt.indexOf('could not read') >= 0 ? "said" :
                             (txt.trim() ? "other" : "empty")));
      } else {
        out.push("files=noselect");
      }
      w.fetch = real;
    } else {
      out.push("files=nofn");
    }

    // ---- logout that the board never confirms -----------------------
    if (typeof w.doLogout === 'function') {
      var real2 = w.fetch;
      w.fetch = function(u){
        if (String(u).indexOf('/api/logout') >= 0) return Promise.reject(new Error('gone'));
        return real2.apply(w, arguments);
      };
      w.viaHub = function(){ return false; };   // the direct case is the one that matters
      w.doLogout();
      await new Promise(function(r){ setTimeout(r, 800); });
      var st = (d.getElementById('liStat') || {}).textContent || '';
      out.push("logout=" + (/did not confirm/i.test(st) ? "said" : "silent"));
      w.fetch = real2;
    } else {
      out.push("logout=nofn");
    }

    done(out.join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,50)); }
}, 6000);
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, _main = F.start_hub()
    url = "/mod?dev=usb%3A" + urllib.parse.quote(fake_serial.PORT)
    browser.raw_page(DRIVER % url, base, seconds=35)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("ER "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                got[k] = v
    if not t.ok(got, "the board page reported back",
                "%r" % (fake_serial.qc_marks[-3:],)):
        return

    t.eq(got.get("files"), "said",
         "a file list that could not be read says so, instead of looking empty")
    t.eq(got.get("logout"), "said",
         "a logout the board never confirmed is admitted, not assumed")

    # The other two are in the login flow, which needs a password the fake does
    # not have, so they are held to the SOURCE: an empty catch is the fault.
    ui = (F.FIRMWARE / "src" / "web" / "WebUI.h").read_text(encoding="utf-8")
    i = ui.find("mustChange = (await s.json()).mustChange === true")
    tail = ui[i:i + 260] if i >= 0 else ""
    t.ok(i >= 0, "the page still reads mustChange from the board")
    t.ok("catch(e){ mustChange = true; }" in tail.replace("\n", " ").replace("  ", " ")
         or "mustChange = true" in tail,
         "and an unreadable answer ASKS for a password rather than skipping it",
         "swallowing it turns the prompt off on a board that never had one set")

    j = ui.find("body:'user='+encodeURIComponent(auth.user)")
    after = ui[j:j + 700] if j >= 0 else ""
    t.ok(j >= 0, "the page signs back in after a password change")
    t.ok("if(!s.ok)" in after,
         "and it checks that the new session was granted",
         "ignoring it opened Setup on a dead session - cards visible, every "
         "action behind them refused, nothing on screen saying why")

    # No handler anywhere may be empty again: this is the pattern that produced
    # all four, and it is cheap to keep out.
    empty = ui.count("catch(e){}")
    t.eq(empty, 0, "no error on this page is caught and thrown away")
