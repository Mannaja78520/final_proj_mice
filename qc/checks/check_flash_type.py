"""Flashing a board also MAKES it that type — over the cable and over WiFi.

The bug this exists for, reported from the bench: "I flash the ESP32-CAM as cam
and it comes back blank", and "over WiFi I pick cam and it flashes blank".

Writing firmware is only half of it. The type a board IS lives in its own NVS,
and a binary only contains the module types it was BUILT with. When the stored
type is not one of them `ModuleFactory::create` falls back to BlankModule, so
the board boots blank, reports blank, and the camera is simply not there. The
flash itself looked perfect every time.

Two separate faults produced that one symptom:

  * over the cable, nothing set the type at all. `flashBox` wrote the image,
    said "flashed as cam", and left the stored type alone.
  * over WiFi the type WAS set, but too early. Right after an update the OLD
    firmware still answers for a moment; it does not know "cam", so
    `SET TYPE cam` came back "ERR unknown type (...)" — and that was treated as
    a hard failure and never retried. The board then rebooted into the cam
    firmware still storing "blank".

The board already reports which types its binary knows (`types` in
/api/dev/status, from CommandRouter::buildStatus). So the rule that fixes both
is: only ask the binary that is answering RIGHT NOW, only once it says it can
be this type, and keep watching until the board confirms it.

This is driven for real in a browser: a fake board answers as the OLD firmware
first and only later as the new one, exactly as a board does while it restarts.
Asserting on what reached the board — not on what the page says about itself.
"""

# The SECOND half, and the one that bites hardest: does the Firmware SCREEN
# actually finish the job? applyTypeAfterFlash can be perfect and still never be
# reached. This drives fwWrite itself — the function the button calls — with the
# network stubbed, and asserts on what reached the board, not on what the page
# says about itself. It caught two real faults on its first run: a write path
# that threw on a function deleted with the old screen, and a type that was
# never applied.
PAGE_WRITE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("FW " + s); qcMark("done"); }
setTimeout(function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (typeof w.fwWrite !== 'function') return done("missing=fwWrite");
    if (typeof w.fwTarget !== 'function') return done("missing=fwTarget");

    // A row for a board that runs something ELSE right now. What it runs must
    // be on screen next to the button that would replace it.
    var row = w.fwTarget({type:'cam'}, {name:'armA', ip:'10.0.0.9', type:'blank'});
    // The template's own newlines are in textContent, and a newline ENDS the
    // serial line a mark travels on — the first attempt reported one empty
    // field and nothing else. Anything that is not text becomes an underscore.
    var rowText = (row.textContent || '').replace(/[^A-Za-z0-9.:]+/g, '_');

    var urls = [], stored = 'blank';
    var reply = function(o){
      return Promise.resolve({
        json: function(){ return Promise.resolve(o); },
        text: function(){ return Promise.resolve(typeof o === 'string' ? o : JSON.stringify(o)); }
      });
    };
    w.confirmFlash = function(){ return Promise.resolve(true); };
    var stub = function(u){
      u = String(u); urls.push(u);
      if (u.indexOf('/api/ota') >= 0) return reply({ok:true});
      // THE REAL SHAPE, not a convenient one. This used to answer
      // {done:true}, a key /api/flash has never sent — so the harness proved
      // the page worked against a document the hub does not produce, and the
      // watcher's never-finishing bug lived here undetected for exactly that
      // reason. A fake that is kinder than reality tests nothing.
      if (u.indexOf('/api/flash') >= 0)
        return reply({running:false, ok:true, percent:100, error:'',
                      stage:'restarting the board', how:'wifi', log:[]});
      if (u.indexOf('/api/dev/status') >= 0)
        return reply({id:1, type:stored, types:['blank','cam']});
      if (u.indexOf('/api/dev/cmd') >= 0){
        var c = decodeURIComponent((u.split('&c=')[1] || '').split('&')[0]);
        if (c.indexOf('SET TYPE') === 0){ stored = c.split(' ')[2]; return reply('OK'); }
        return reply('OK');
      }
      return reply({modules:[]});
    };
    w.fetch = stub;

    var go = d.createElement('button');
    var bar = d.createElement('div'); bar.appendChild(d.createElement('i'));
    var say = d.createElement('span');
    var threw = '';
    try{
      w.fwWrite({type:'cam', env:'mice_cam', ready:true},
                {name:'armA', ip:'10.0.0.9', type:'blank'}, false, go, bar, say);
    }catch(e){ threw = String(e).slice(0,40); }

    setTimeout(function(){
      var typed = urls.filter(function(u){ return u.indexOf('SET+TYPE') >= 0
                                               || u.indexOf('SET%20TYPE') >= 0; });
      done(["row=" + rowText,
            "threw=" + (threw || "no"),
            "stored=" + stored,
            "typed=" + typed.length,
            "urls=" + urls.length,
            "seen=" + urls.map(function(u){ return u.split('?')[0]; })
                          .join(",").replace(/[^A-Za-z0-9,/]+/g, ""),
            "said=" + (say.textContent || "").replace(/[^A-Za-z0-9]+/g, "_").slice(0, 40),
            "addr=" + (typed.length ? decodeURIComponent(
                 (typed[0].split('dev=')[1] || '').split('&')[0]) : "none")
           ].join(" "));
    }, 12000);
  } catch (e) { done("ERR=" + String(e).slice(0,60)); }
}, 5000);
</script>
"""

import re

import browser
import fake_serial
import qc as F

AREA = "firmware"
TITLE = "flashing a board also makes it that type"
SLOW = True

# The page is driven with fetch stubbed, so no board and no esptool are needed.
# Phase 1 = the old firmware is still answering (it does NOT know "cam").
# Phase 2 = the new firmware is up (it knows "cam", but still STORES "blank").
# Phase 3 = SET TYPE landed, so the board reports "cam" for real.
PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("FT " + s); qcMark("done"); }
setTimeout(function(){
  try{
    var w = document.getElementById('f').contentWindow;
    if (typeof w.applyTypeAfterFlash !== 'function')
      return done("missing=applyTypeAfterFlash");

    var polls = 0, sent = [], sentEarly = 0, storedType = 'blank';

    w.fetch = function(u){
      u = String(u);
      var reply = function(o){
        return Promise.resolve({
          json: function(){ return Promise.resolve(o); },
          text: function(){ return Promise.resolve(typeof o === 'string' ? o : JSON.stringify(o)); }
        });
      };
      if (u.indexOf('/api/dev/status') >= 0){
        polls++;
        // the first two answers come from the OLD firmware, which has no cam
        if (polls <= 2) return reply({id:1, type:'blank', types:['blank','nong']});
        return reply({id:1, type:storedType, types:['blank','cam']});
      }
      // A FINISHED, SUCCESSFUL flash job, in the shape /api/flash really
      // returns: running/percent/stage/ok/error/how/log, and NO `done` key.
      // That is the whole point - the watcher used to wait for `done`, so it
      // only ever ended on a FAILURE and a successful write left the button
      // disabled and the type never applied.
      if (u.indexOf('/api/flash') >= 0){
        return reply({running:false, ok:true, percent:100, error:'',
                      stage:'restarting the board', how:'usb', log:[]});
      }
      if (u.indexOf('/api/dev/cmd') >= 0){
        var c = decodeURIComponent((u.split('&c=')[1] || '').split('&')[0]);
        if (c.indexOf('SET TYPE') === 0){
          sent.push(c);
          // asking the OLD firmware is the bug: it can only answer with an error
          if (polls <= 2){ sentEarly++; return reply('ERR unknown type (blank,nong)'); }
          storedType = c.split(' ')[2];        // it took
          return reply('OK type=' + storedType + ' (reboot to apply)');
        }
        return reply('OK');
      }
      return reply({});
    };

    // ---- does the WATCHER ever finish on a success? ----------------
    // Everything below is downstream of this. A watcher that never completes
    // is a button stuck disabled, a bar stuck on screen, and a board left
    // running new firmware under its old type - with no error anywhere.
    var wbar = w.document.createElement('div');
    wbar.innerHTML = '<i></i>';
    wbar.hidden = false;
    var wsay = w.document.createElement('span');
    var wgo = w.document.createElement('button');
    wgo.disabled = true;
    var watched = 'no';
    try{
      w.fwWatch(wbar, wsay, wgo, {dev:'', type:'', was:''});
    }catch(e){ watched = 'threw'; }

    setTimeout(function(){
      if (watched !== 'threw')
        watched = (wgo.disabled === false && wbar.hidden === true) ? 'yes' : 'no';
      // fresh counters: the watcher's own poll must not colour the numbers
      // the type test below reports.
      polls = 0; sent = []; sentEarly = 0; storedType = 'blank';
      runTypeTest();
    }, 3500);

    function runTypeTest(){
    var stat = w.document.createElement('span');
    w.applyTypeAfterFlash('usb:COM99', 'cam', stat);

    setTimeout(function(){
      var out = [];
      out.push("early=" + sentEarly);                  // must be 0
      out.push("sent=" + sent.length);                 // must be >= 1
      out.push("cmd=" + (sent[0] || 'none').replace(/ /g, '_'));
      out.push("stored=" + storedType);                // must end up cam
      out.push("said=" + (/cam/i.test(stat.textContent) ? "cam" : "no"));
      out.push("gaveup=" + (/^\\u26a0/.test(stat.textContent.trim()) ? "yes" : "no"));
      out.push("watchdone=" + watched);                // must be yes
      done(out.join(" "));
    }, 14000);
    }
  } catch (e) { done("ERR=" + String(e).slice(0,60)); }
}, 5000);
</script>
"""


def _fn(src, name):
    """The body of one JS function, so an assertion cannot pass on another."""
    i = src.find("function " + name + "(")
    if i < 0:
        return ""
    j = src.find("\nfunction ", i + 10)
    body = src[i:j if j > 0 else len(src)]
    # a comment is not behaviour: strip them before asserting on code
    return re.sub(r"//[^\n]*", "", body)


def run(t):
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")

    # ---- 1. both flash paths set the type ------------------------------
    # The cable path used to write the firmware and stop there, which is the
    # whole of the "flashed as cam, came back blank" report.
    t.ok("function applyTypeAfterFlash(" in hub,
         "there is one place that makes a board the type it was flashed as")

    # Both paths are ONE path now: flashing moved to the Firmware screen
    # (A2-2), where a cable and a WiFi write end in the same watcher. The
    # property is unchanged and this check is what caught its loss — the
    # moved screen wrote the firmware and never told the board its new type.
    watch = _fn(hub, "fwWatch")
    t.contains(watch, "applyTypeAfterFlash",
               "a finished write sets the board's type")

    # ...AND THE WATCHER HAS TO GET THERE. Every field the completion test
    # reads must be a field the hub really sends, or the type step is perfect
    # code that never runs. Found 2026-08-20: the test was `if (s.done ||
    # s.error)` and /api/flash has never sent a `done` key — status() returns
    # running/percent/stage/ok/error/how/log and /api/flash/at only proxies the
    # same document. So a write that SUCCEEDED never finished in the UI: the
    # button stayed disabled, the bar stayed on screen, and the board kept
    # running new firmware under its old type. Only a FAILED write ended
    # cleanly, which is why nobody noticed.
    import re as _re                                          # noqa: PLC0415
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    # The FLASH job's status, not the show player's — main.py has more than one
    # `def status(self)`, and taking the first one made this assert against the
    # wrong document entirely.
    st = src[:src.find('"how": self.how')]
    st = st[st.rfind("    def status(self):"):]
    sends = set(_re.findall(r'"(\w+)":', st))
    t.ok(sends, "the hub's flash status names its fields", str(sorted(sends)))
    cond = watch[watch.find("const finished ="):]
    cond = cond[:cond.find(";")]
    reads = set(_re.findall(r"s\.(\w+)", cond))
    unknown = sorted(r for r in reads if r not in sends and r != "done")
    t.eq(unknown, [],
         "the completion test only reads fields /api/flash actually sends")
    t.ok(reads & sends,
         "and it reads at least one field that is really there",
         "a watcher waiting on a key nothing sends never finishes, so every "
         "step after it - including setting the board's type - silently never "
         "happens on the one path that matters, the successful one")
    write = _fn(hub, "fwWrite")
    t.contains(write, "usb:", "the cable path addresses the board by its port")
    t.contains(write, "wifi:", "and the WiFi path by its address")
    t.contains(write, "type: img.type",
               "and both carry the type that was just written")

    # ---- 2. it asks the RIGHT binary, and does not give up -------------
    apply_fn = _fn(hub, "applyTypeAfterFlash")
    t.contains(apply_fn, "types",
               "it reads which types the answering binary actually has")
    t.contains(apply_fn, "indexOf(type)<0",
               "and waits while the answering firmware does not have this type")
    t.ok("return;" not in apply_fn.split("startsWith('ERR')")[-1][:120]
         if "startsWith('ERR')" in apply_fn else True,
         "an ERR from the old firmware is a reason to wait, not to give up",
         "'ERR unknown type' is exactly what the OLD firmware says while the "
         "board is still restarting")

    # ---- 3. and it really behaves that way in a browser -----------------
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(PAGE, base, seconds=30)

    marks = [m for m in fake_serial.qc_marks if m.startswith("FT ")]
    if not t.ok(marks, "the hub page reported back",
                "the page never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    last = marks[-1][3:]
    if "ERR=" in last or "missing=" in last:
        t.ok(False, "the type-setting ran without throwing", last)
        return
    got = dict(kv.split("=", 1) for kv in last.split(" ") if "=" in kv)

    # sending SET TYPE on the first answer is what left the board blank: the
    # answer came from the old firmware, which can only reject the new type
    t.eq(got.get("early"), "0",
         "it never asks the OLD firmware to become a type it does not have")
    t.ok(int(got.get("sent", "0")) >= 1,
         "once the new firmware is up, it does set the type", str(got))
    t.eq(got.get("cmd"), "SET_TYPE_cam",
         "and it sends exactly the type that was flashed")
    # the bug itself: cam firmware + stored "blank" boots BlankModule
    t.eq(got.get("stored"), "cam",
         "so the board ends up stored as cam, not blank")
    t.eq(got.get("gaveup"), "no",
         "and it does not report failure while the board is still restarting")
    t.eq(got.get("said"), "cam",
         "the row says which type the board ended up as")

    # DRIVEN, in a real browser, against the real /api/flash document: a
    # SUCCESSFUL job has to finish. Asserting on the source alone was not
    # enough — proved with tools/sabotage.py, where restoring the old
    # `s.done || s.error` test passed a source-level check happily, because
    # `error` is a field the hub really sends. Only running it catches that
    # the condition can never become true on the path that succeeds.
    t.eq(got.get("watchdone"), "yes",
         "a flash that SUCCEEDED finishes: the bar hides and the button "
         "comes back")

    # ---- the SCREEN finishes the job -----------------------------------
    fake_serial.reset()
    browser.raw_page(PAGE_WRITE, base, seconds=40)
    w = {}
    for m in fake_serial.qc_marks:
        if m.startswith("FW "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                w[k] = v
    if not t.ok(w, "the Firmware screen reported back", fake_serial.qc_marks[-4:]):
        return
    t.eq(w.get("threw"), "no", "clicking Write does not throw")
    t.contains(w.get("row", ""), "blank",
               "the row says what the board runs NOW, beside the button that replaces it")
    t.ok(int(w.get("typed", "0")) >= 1,
         "a finished write tells the board what it now is",
         "the firmware landed but the board would still call itself blank; "
         "the page asked for: " + w.get("seen", ""))
    t.eq(w.get("stored"), "cam", "and the board ends up storing the new type")
    t.eq(w.get("addr"), "wifi:10.0.0.9",
         "addressed to the board that was written, not another one")
