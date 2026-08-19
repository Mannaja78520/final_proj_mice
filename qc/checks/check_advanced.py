"""Addresses and ports are hidden until someone asks for them - really hidden.

The job of the module screen is: show which modules are here, and open one. An
IP address serves none of that until something is wrong, and it sat on every
row in the same grey as the name.

Driven in a browser and asserted on VISIBILITY, not on text. That distinction
is the whole check: hiding something with a class it does not have, or leaving
it in the markup and colouring it darker, both leave the text in the DOM and
would pass any assertion made on innerHTML.

Three things have to hold, and the third is the one that gets broken by a
later change:

  * with the switch off, the address is not on screen;
  * with it on, it is - and the switch survives a reload, because a preference
    that resets is worse than no preference;
  * the name, the type and the module id are ALWAYS on screen. The id is not
    trivia: it is how a module is addressed on the bus, and how two identical
    arms on a shelf are told apart.
"""
import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "technical detail is hidden until it is asked for"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("AD " + s); qcMark("done"); }
// Is this element ACTUALLY on screen? getComputedStyle, not a class name: the
// question is what a person sees, and a rule that is written but overridden
// looks exactly like a rule that works if you only read the markup.
function shown(el){
  if (!el) return false;
  if (el.offsetParent === null) return false;
  var st = getComputedStyle(el);
  return st.display !== 'none' && st.visibility !== 'hidden' && el.offsetWidth > 0;
}
setTimeout(async function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (typeof w.setAdvanced !== 'function') return done("missing=setAdvanced");
    var reply = function(o){
      return Promise.resolve({ json: function(){ return Promise.resolve(o); } });
    };
    w.fetch = function(u){
      if (String(u).indexOf('/api/modules') >= 0)
        return reply({ok: true, lan: '10.0.0', modules: [{
          id: 7, name: 'armA', type: 'nong', chip: 'A0B1C2D3E4F5',
          routes: [{kind:'usb', dev:'usb:COM9', port:'COM9'},
                   {kind:'wifi', dev:'wifi:10.0.0.9', ip:'10.0.0.9'}]}]});
      return reply({ports: [], modules: [], ok: true});
    };

    // Open the screen first. Everything in a hidden panel reports itself as
    // not visible, and innerText on a panel that is display:none falls back to
    // the raw text - so measuring before opening the tab says the name is
    // hidden AND the address is readable, which is both answers wrong.
    var tab = d.querySelector('#tabs [data-go="modules"]');
    if (tab) tab.click();
    await new Promise(function(r){ setTimeout(r, 400); });
    w.setAdvanced(false);
    await w.scan(true);
    var row = d.querySelector('#mods .mod');
    if (!row) return done("row=none");
    var tech = row.querySelector('.tech');
    var out = [];
    out.push("off_tech=" + (shown(tech) ? "shown" : "hidden"));
    out.push("off_name=" + (shown(row.querySelector('.nm')) ? "shown" : "hidden"));
    out.push("off_type=" + (shown(row.querySelector('.ty')) ? "shown" : "hidden"));
    // The id is inside the same span as the address, so this proves the split
    // is real: hiding the address must not take the id with it.
    //
    // Measured on the ROW, which is on screen, not on the .ip span itself:
    // innerText of a display:none element falls back to its raw text, so
    // asking the hidden span reports the id as visible when it is not. That
    // is exactly how the lazy fix - hiding the whole span - passed the first
    // version of this assertion.
    out.push("off_id=" + (row.innerText.indexOf('#7') >= 0 ? "shown" : "hidden"));
    out.push("off_ip=" + (row.innerText.indexOf('10.0.0.9') >= 0 ? "shown" : "hidden"));

    w.setAdvanced(true);
    out.push("on_tech=" + (shown(row.querySelector('.tech')) ? "shown" : "hidden"));
    out.push("on_ip=" + (row.innerText.indexOf('10.0.0.9') >= 0 ? "shown" : "hidden"));
    out.push("saved=" + (w.localStorage.getItem('hub_adv') || "none"));
    out.push("box=" + (d.getElementById('advOn') ? "there" : "missing"));
    out.push("checked=" + (d.getElementById('advOn')
                           && d.getElementById('advOn').checked ? "yes" : "no"));
    done(out.join(" "));
  } catch (e) { done("ERR=" + String(e).replace(/[^A-Za-z0-9=]+/g, "_").slice(0,50)); }
}, 4000);
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=30)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("AD "):
            for part in m[3:].split(" "):
                k, _, v = part.partition("=")
                got[k] = v
    if not t.ok(got, "the page reported back", "%r" % (fake_serial.qc_marks[-3:],)):
        return

    t.eq(got.get("off_tech"), "hidden",
         "with the switch off, the technical detail is not on screen")
    t.eq(got.get("off_ip"), "hidden", "and the address is not readable")
    t.eq(got.get("off_name"), "shown", "the name is always there")
    t.eq(got.get("off_type"), "shown", "so is the type")
    t.eq(got.get("off_id"), "shown",
         "and so is the module id, which is how a board is addressed")

    t.eq(got.get("on_tech"), "shown", "turning it on shows the detail")
    t.eq(got.get("on_ip"), "shown", "including the address")
    t.eq(got.get("saved"), "1",
         "and the choice is remembered, because a preference that resets is "
         "worse than none")
    t.eq(got.get("box"), "there", "the switch is on the settings screen")
    t.eq(got.get("checked"), "yes", "and it shows the state it is in")

    # One rule, in the shared sheet, so a new page cannot invent its own.
    css = (F.CODE / "shared" / "web" / "mice.css").read_text(encoding="utf-8")
    t.contains(css, ".tech{display:none}", "the rule lives in the shared sheet")
    t.contains(css, "body.adv .tech", "with one switch that reveals it")
