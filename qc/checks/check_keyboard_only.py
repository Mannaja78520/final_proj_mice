"""Every control can be reached and used with the keyboard alone.

A9-3b, the half of A9-3 that needs no hardware. A TV is driven by a remote,
which sends arrow keys and Enter and nothing else - but this is not only about
televisions. Somebody with a trackpad that has stopped working, somebody
running the show from a laptop on a shelf, and anybody using a screen reader
all move by Tab and press by Enter.

Three failures are looked for, in a real browser, on every page a person
actually opens:

  * **pointer-only controls** - anything that answers a click while not being
    reachable by Tab. A `<div onclick=...>` looks identical to a button and is
    invisible to the keyboard;
  * **focus you cannot see** - a control that is focused but looks exactly like
    the one beside it. Tabbing then means guessing where you are, which is
    worse than no focus ring at all because it looks like nothing happened;
  * **a page that stopped being walked** - every tab is opened and counted, so
    a broken tab switcher cannot turn into a page that reports no problems
    because nothing was looked at.

Native elements are the fix, not extra JavaScript: a `<button>` is reachable,
pressable with Enter AND with Space, and announces itself, for free.
"""
import browser
import fake_serial
import qc as F

AREA = "ui"
TITLE = "every control can be reached and pressed with the keyboard alone"
SLOW = True

# The third number is how many focusable controls the page must still have.
# Measured 2026-08-21 (hub 77, module site 53, studio 72, rgb 17, counted over
# every tab), floored well below that: it is here to catch a page that has
# stopped being walked - a broken showTab, a card that no longer renders -
# rather than to pin an exact count that any new button would break.
PAGES = [
    ("hub", "/", 45),
    ("module site", "/mod?dev=usb%3ACOM99", 30),
    ("nong studio", "/studio/", 40),
    ("rgb", "/rgb.html", 10),
]

PAGE = """
<style>html,body{margin:0}iframe{width:1200px;height:820px;border:0;display:block}</style>
<div id="frames"></div>
<script>
var PAGES = __PAGES__;
var res = {}, ready = 0;

function visible(el){
  if (el.disabled || el.hidden) return false;
  var r = el.getBoundingClientRect();
  if (!r.width && !r.height) return false;
  var cs = el.ownerDocument.defaultView.getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden') return false;
  // Inside a CLOSED <details> is not on screen for anybody. The summary that
  // opens it is a native control - reachable by Tab and opened with Enter -
  // so the contents are one keypress away, not unreachable. Chrome still
  // reports a box for them, and el.focus() quietly does nothing, which read
  // as a control with no focus ring.
  for (var p = el.parentElement; p; p = p.parentElement){
    if (p.tagName === 'DETAILS' && !p.open
        && !(el.closest && el.closest('summary'))) return false;
  }
  return true;
}

// Reachable by Tab: the browser's own list, plus anything given a tabindex.
function focusable(el){
  var tag = el.tagName.toLowerCase();
  var ti = el.getAttribute('tabindex');
  if (ti !== null) return parseInt(ti, 10) >= 0;
  if (tag === 'a') return el.hasAttribute('href');
  return ['button', 'input', 'select', 'textarea', 'summary'].indexOf(tag) >= 0;
}

// Named the way a person would point at it: what it is, plus what it says.
// "button" alone sends the reader hunting through forty of them.
function name(el){
  var said = (el.textContent || el.getAttribute('placeholder') || '')
    .replace(/\s+/g, '~').slice(0, 16);
  return (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')
    + (el.className && typeof el.className === 'string'
       ? '.' + el.className.split(' ')[0] : '')
    + (said ? '~' + said : '')).slice(0, 44);
}

// A control that answers a click. Only INLINE handlers can be seen this way -
// a listener added in script is invisible to a page reading itself - which is
// why `cursor:pointer` is tested as well, below: it is what a person actually
// reads as "this is pressable", however the handler got there.
function clicky(el){
  return el.hasAttribute('onclick') || el.getAttribute('role') === 'button'
      || el.hasAttribute('onkeydown') && el.getAttribute('role');
}

function look(doc){
  var out = {pointer: [], blind: [], n: 0, first: ''};
  var all = doc.querySelectorAll('*');       // static: taken before priming
  // PRIMED, or the first control on every page looks broken. A browser only
  // draws the focus ring when it believes focus came from the keyboard, and
  // for focus moved by script it decides by looking at what was focused
  // before: a text field always counts, anything else inherits. So the first
  // element this loop touched reported no ring while a real Tab press shows
  // one - a false failure on exactly one control per page, measured
  // 2026-08-21. An off-screen text field starts the chain honestly.
  var prime = doc.createElement('input');
  prime.type = 'text';
  prime.style.cssText = 'position:fixed;left:-9999px;top:0';
  doc.body.appendChild(prime);
  try{ prime.focus(); }catch(e){}
  for (var i = 0; i < all.length; i++){
    var el = all[i];
    if (!visible(el)) continue;
    // Two ways to look like a control: answering a click, or being drawn as
    // something to click. A listener added in script is invisible to a page
    // reading itself - but `cursor:pointer` is not, and it is how a person
    // decides what is pressable in the first place.
    var cs0 = doc.defaultView.getComputedStyle(el);
    // The OUTERMOST element drawn as clickable, not its children: cursor is
    // inherited, so a card with four divs inside it would otherwise be
    // reported five times and the real control would be lost in the noise.
    var par = el.parentElement
      && doc.defaultView.getComputedStyle(el.parentElement).cursor;
    var looks = cs0.cursor === 'pointer' && par !== 'pointer'
      && el.tagName !== 'LABEL';
    // A clickable CONTAINER may keep its click, but it has to SAY where the
    // keyboard does the same job: data-keyboard is a selector for the control
    // inside it that does what clicking the container does. Accepting any
    // focusable descendant instead was too generous and was caught doing
    // nothing on 2026-08-21 - a timeline chip holds a name field, a suspend
    // button and two time boxes, so it passed while the one thing clicking it
    // did, selecting that move, was still mouse-only.
    var eq = el.getAttribute('data-keyboard');
    var alt = null;
    try{ alt = eq ? el.querySelector(eq) : null; }catch(e){ alt = null; }
    if ((clicky(el) || looks) && !focusable(el) && !(alt && focusable(alt)))
      out.pointer.push(name(el) + (eq ? '~says~' + eq + '~but~it~is~not~focusable' : ''));
    if (!focusable(el)) continue;
    out.n++;
    if (!out.first) out.first = name(el);
    // Focus you can SEE. Compared against the same element unfocused, so a
    // page that draws its own ring in any way still passes - what fails is a
    // control that looks identical whether or not it is focused.
    // Blurred FIRST: a page may open with something already focused (a search
    // box, the first field of a form), and measuring that element's "before"
    // while it is focused compares the focused look with itself.
    try{ if (doc.activeElement === el) el.blur(); }catch(e){}
    var cs = doc.defaultView.getComputedStyle(el);
    var before = cs.outlineStyle + cs.outlineWidth + cs.boxShadow + cs.borderColor;
    try{ el.focus(); }catch(e){ continue; }
    cs = doc.defaultView.getComputedStyle(el);
    var after = cs.outlineStyle + cs.outlineWidth + cs.boxShadow + cs.borderColor;
    // Spaces stripped: a computed colour is "rgba(0, 0, 0, 0)", and the marks
    // are read back as space-separated fields - one colour would split a
    // report into pieces and the reader would see half an answer.
    if (before === after) out.blind.push(name(el) + '='
      + after.replace(/\\s+/g, '').slice(0, 24)
      + (doc.activeElement === el ? '~took-focus' : '~NOT-focused'));
  }
  prime.remove();
  return out;
}

// EVERY TAB, not just the one that opens. Both the hub and the module site
// hide cards by data-tab, so a single look at the page misses most of the
// controls in it - the Network and Tools tabs together hold more buttons than
// Home does.
function sleep(ms){ return new Promise(function(go){ setTimeout(go, ms); }); }

async function lookAll(doc){
  var win = doc.defaultView, tabs = [];
  var cards = doc.querySelectorAll('[data-tab]');
  for (var i = 0; i < cards.length; i++){
    var n = cards[i].getAttribute('data-tab');
    if (tabs.indexOf(n) < 0) tabs.push(n);
  }
  var out = {pointer: [], blind: [], n: 0, first: '', tabs: tabs.length};
  var passes = (tabs.length && typeof win.showTab === 'function') ? tabs : [null];
  for (var k = 0; k < passes.length; k++){
    if (passes[k]){ try{ win.showTab(passes[k]); }catch(e){} }
    // A tab fetches its own contents when it opens - the module's file list,
    // the firmware images, the module rows. Scanning the instant it is shown
    // measures an empty tab, and that is not a page with no faults, it is a
    // page nobody looked at. It cost a whole gate on 2026-08-21: a delete
    // control that could not be reached by Tab was missed four times running
    // and then failed the suite, because the rows had arrived that time.
    await sleep(700);
    var o = look(doc);
    out.n += o.n;
    if (!out.first) out.first = o.first;
    o.pointer.forEach(function(x){ if (out.pointer.indexOf(x) < 0) out.pointer.push(x); });
    o.blind.forEach(function(x){ if (out.blind.indexOf(x) < 0) out.blind.push(x); });
  }
  return out;
}

PAGES.forEach(function(p, i){
  var f = document.createElement('iframe');
  f.src = p[1];
  document.getElementById('frames').appendChild(f);
  f.addEventListener('load', async function(){
    await sleep(2500);
    var o;
    try{ o = await lookAll(f.contentDocument); }
    catch(e){ o = {pointer: ['unreadable~' + (e && e.message)], blind: [],
                   n: 0, first: ''}; }
    res[i] = o;
    ready++;
  });
});

// ONE MARK PER PAGE. All four pages in a single mark reads back as one long
// line of space-separated fields, and a computed colour ("rgba(0, 0, 0, 0)")
// carries spaces of its own - so a report split into pieces and the reader
// saw half an answer. Measured 2026-08-21.
(async function(){
  // Report when every page has finished walking its tabs, not after a fixed
  // wait: a fixed wait is a bet on how fast the machine is today, and this
  // check is one of several browsers running at once.
  var until = Date.now() + 45000;
  while (ready < PAGES.length && Date.now() < until) await sleep(300);
  PAGES.forEach(function(p, i){
    var o = res[i] || {pointer: ['never~loaded'], blind: [], n: 0, first: ''};
    var line = p[0].replace(/ /g, '~') + ' ' + o.n + '/' + o.pointer.length
      + '/' + o.blind.length
      + ' pointer:' + (o.pointer.slice(0, 2).join('|') || '-')
      + ' blind:' + (o.blind.slice(0, 2).join('|') || '-');
    qcMark("KEYS " + line.replace(/[^A-Za-z0-9=~|#:._/ -]/g, '_').slice(0, 150));
  });
  qcMark("done");
})();
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, _m = F.start_hub()
    js = "[" + ",".join('["%s","%s"]' % (n, u) for n, u, _f in PAGES) + "]"
    browser.raw_page(PAGE.replace("__PAGES__", js), base, seconds=60)

    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("KEYS ")]
    if not t.ok(marks, "the pages reported back",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = {m.split(" ", 1)[0]: m.split(" ", 1)[1] for m in marks if " " in m}

    for name, _u, floor in PAGES:
        key = name.replace(" ", "~")
        row = got.get(key)
        if not t.ok(row, "%s reported" % name, "no result for this page"):
            continue
        counts, detail = row.split(" ", 1)
        n, pointer, blind = (int(x) for x in counts.split("/"))
        t.ok(n >= floor, "%s: its controls were really walked" % name,
             "only %d focusable controls across its tabs, expected at least "
             "%d — a page that stopped being walked reports no problems, "
             "which reads exactly like a page with none" % (n, floor))
        t.ok(pointer == 0,
             "%s: nothing answers a click but not Tab" % name,
             "%d pointer-only control(s): %s — a div that answers onclick "
             "looks like a button and is invisible to the keyboard"
             % (pointer, detail))
        t.ok(blind == 0,
             "%s: focus is visible on every control" % name,
             "%d control(s) look identical focused and unfocused: %s — "
             "tabbing then means guessing where you are" % (blind, detail))
