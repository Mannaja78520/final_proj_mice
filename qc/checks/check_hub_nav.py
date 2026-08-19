"""The hub's destinations exist, go somewhere, and none of them is a blank panel.

The hub had three tabs — Modules, Network, Tools — and everything else was
somewhere inside one of them: the help page was two clicks deep inside Tools,
flashing lived on each module row, and there was no first screen at all.

Driven in a real browser, because the thing under test is what happens when a
person clicks. Three properties, and the third is the one that rots:

  * every destination in the bar leads to a panel, and to the RIGHT one;
  * a destination that LEAVES the page is a link, not a tab — a tab that
    navigates away loses your place with no warning;
  * no destination is blank. An empty panel that promises a feature is worse
    than a small one that works, so an empty destination has to say what it is,
    why it is empty, and what to do instead.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "every destination in the hub leads somewhere, and none is blank"
SLOW = True

WANT = ["home", "modules", "firmware", "network", "tools", "settings"]

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
// Collapse ALL whitespace, not just spaces. innerText puts a newline between
// elements, and a newline ends the command line at the fake module — so a
// multi-line report arrived as its first line only, which looked like the page
// having nothing but a heading on it.
function say(k, v){ return qcMark("NAV " + k + "=" + String(v).replace(/[\s|]+/g, "~")); }
window.addEventListener("load", async function(){
  try{
    var d = document.getElementById('f').contentDocument;
    await qcWaitFor(function(){ return d.querySelector('#tabs .tab'); }, 15000);

    var tabs = [].slice.call(d.querySelectorAll('#tabs [data-go]'));
    await say("gos", tabs.map(function(b){ return b.getAttribute('data-go'); }).join(","));

    // Help must be a real link that leaves the page.
    var help = [].slice.call(d.querySelectorAll('#tabs a')).filter(function(a){
      return /help/i.test(a.textContent); })[0];
    await say("helplink", help ? help.getAttribute('href') : "none");
    await say("helptag", help ? help.tagName : "none");

    // Each destination shows its own panel and only its own.
    for (var i = 0; i < %s.length; i++){
      var name = %s[i];
      var btn = d.querySelector('#tabs [data-go="' + name + '"]');
      if (!btn){ await say("open-" + name, "nobutton"); continue; }
      btn.click();
      await qcWaitFor(function(){
        var c = d.querySelector('[data-tab="' + name + '"]');
        return c && c.style.display !== 'none'; }, 4000);
      // Firmware paints from two fetches. Measuring the instant the tab
      // opens counts the words of a screen that is still loading, which is
      // not the same thing as an empty screen.
      if (name === 'firmware')
        await qcWaitFor(function(){
          var st = d.getElementById('fwStat');
          return st && !/checking/i.test(st.textContent); }, 15000);
      var mine = [].slice.call(d.querySelectorAll('[data-tab="' + name + '"]'));
      var shown = mine.filter(function(c){ return c.style.display !== 'none'; });
      var others = [].slice.call(d.querySelectorAll('[data-tab]')).filter(function(c){
        return c.getAttribute('data-tab') !== name && c.style.display !== 'none'; });
      // How much readable text the destination actually offers.
      var words = shown.map(function(c){ return c.innerText.trim(); }).join(" ");
      await say("open-" + name, (shown.length ? "yes" : "no") +
                "/others" + others.length + "/words" + words.split(/\\s+/).length);
      await say("text-" + name, words.toLowerCase().slice(0, 400));
    }
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
""" % (str(WANT).replace("'", '"'), str(WANT).replace("'", '"'))


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(DRIVER, base, seconds=45)

    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("NAV "):
            k, _, v = m[4:].partition("=")
            got[k] = v.replace("~", " ")
    if not t.ok(got, "the hub page reported back", fake_serial.qc_marks[-4:]):
        return

    # ---- every destination is there -----------------------------------
    gos = got.get("gos", "").split(",")
    for name in WANT:
        t.ok(name in gos, "the bar offers %s" % name, "found: %s" % gos)

    # ---- help LEAVES the page, and looks like it does ------------------
    t.ok(got.get("helptag") == "A",
         "Help is a link, not a tab",
         "a tab that navigates away loses the page you were on with no warning; "
         "got a <%s>" % got.get("helptag"))
    t.contains(got.get("helplink", ""), "/help", "and it points at the help page")

    # ---- each one opens its own panel, alone --------------------------
    for name in WANT:
        v = got.get("open-" + name, "")
        t.ok(v.startswith("yes"), "%s opens a panel" % name, v or "never reported")
        m = re.search(r"others(\d+)", v)
        if m:
            t.eq(int(m.group(1)), 0,
                 "and opening %s hides the others" % name)
        # ---- and it is not a blank panel ------------------------------
        # An empty destination must still say what it is, why it is empty and
        # what to do instead. Ten words is not a design standard, it is a floor:
        # below it there is nothing on screen but a heading.
        w = re.search(r"words(\d+)", v)
        if w:
            t.ok(int(w.group(1)) >= 10,
                 "%s says something, rather than being an empty panel" % name,
                 "only %s words on screen" % w.group(1))

    # ---- a destination with no feature yet must say where the feature IS ---
    # A word count alone is too weak, and that was proven by breaking it: the
    # Firmware explanation was deleted and the check still passed, because a
    # heading, a status line and a button clear any floor while saying nothing
    # useful. So assert the thing the destination actually promises.
    # Firmware is where flashing HAPPENS now (A2-2), so what it owes the
    # reader changed: either the boards it can write to and how each one is
    # reached, or the exact reason it cannot write anything from this PC.
    fw = got.get("text-firmware", "")
    t.ok("cable" in fw or "wifi" in fw or "esptool" in fw or "build it" in fw,
         "Firmware says what it can write, or exactly why it cannot",
         "a flashing screen that explains neither is a dead end: %r" % fw[:200])
    t.ok("undone" in fw or "esptool" in fw or "build it" in fw,
         "and it does not offer an irreversible write without saying so",
         fw[:200])
    st = got.get("text-settings", "")
    t.ok("password" in st,
         "Settings says how the hub password works", "got: %r" % st[:140])
