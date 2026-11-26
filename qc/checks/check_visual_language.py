"""No page shows Thai in English/Chinese/Japanese, and no popup sits pinned at the top-left.

2026-11-23: after "547 cases tested" the user found visible bugs in minutes. The tests
looked at APIs, not at screens. This is the part of the screen-look that a script can
decide: every page is opened in en, zh and ja (the language is kept in localStorage,
same origin, so the iframe obeys it) and the visible text is scanned for Thai
letters (and, in th/zh/ja, for English UI words that nobody translated: "for", "WAIST", Help group titles). Text composed at run time ("Thai label: " + value) is not covered by the
exact-string translation and used to slip through (Home > Settings, Help "ถัดไป").
Pages, languages and what to ignore are DATA in tools/visual/pages.json; the scan
is tools/visual/probe.js, the same function the screenshot tool uses.
"""
import json
import os
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "no Thai text leaks into en/zh/ja pages; no popup pinned at the top-left"
SLOW = True
# Alone: a full run on the PC failed it with words other checks leave in the pages at that moment
# (a Thai test name on Voice, dummy_<date> on TV) and a half-rebuilt hub page (showTab is not defined),
# and it passes 165/165 on its own. It reads every page, so nothing else may write while it does.
SOLO = False

HERE = Path(F.CODE) / "tools" / "visual"

DRIVER = """
__PROBE__
var ALLOW = __ALLOW__, LALLOW = __LALLOW__, PAGES = __PAGES__, LANGS = __LANGS__;
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 20000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  for (var li = 0; li < LANGS.length; li++) {
    localStorage.setItem("mice.lang", LANGS[li]);
    for (var pi = 0; pi < PAGES.length; pi++) {
      var pg = PAGES[pi], f = document.createElement("iframe");
      f.style.cssText = "width:1200px;height:800px";
      document.body.appendChild(f);
      f.src = pg.url;
      await ready(f); await sleep(pg.wait || 1500);
      var tabs = pg.tabs || [null];
      for (var ti = 0; ti < tabs.length; ti++) {
        try {
          if (tabs[ti]) { f.contentWindow.eval(tabs[ti]); await sleep(700); }
          // The Help topic view can hide guides until a reader selects them.
          if (pg.id === "help") f.contentDocument.querySelectorAll("main > section.pv-off")
            .forEach(function(section){ section.classList.remove("pv-off"); });
          var r = visualProbe(f.contentDocument);
          var bad = r.thai.filter(function(s){ return !ALLOW.some(function(a){ return new RegExp(a).test(s); }); });
          qcMark("THAI~" + LANGS[li] + "~" + pg.id + (tabs[ti] ? "~" + ti : "") + "~" + bad.length + "~" + (bad[0] || "").replace(/[^\\u0E00-\\u0E7Fa-zA-Z0-9]/g, "_").slice(0, 24));
          var lat = pg.latin === false ? [] : r.latin.filter(function(s){ return !LALLOW.some(function(a){ return new RegExp(a).test(s); }); });
          qcMark("LATIN~" + LANGS[li] + "~" + pg.id + (tabs[ti] ? "~" + ti : "") + "~" + lat.length + "~" + (lat[0] || "").replace(/[^a-zA-Z0-9]/g, "_").slice(0, 30));
          var at = r.attr.filter(function(s){ return !LALLOW.some(function(a){ return new RegExp(a).test(s.replace(/^[a-z-]+: /, "")); }); });
          qcMark("ATTR~" + LANGS[li] + "~" + pg.id + "~" + at.length);
          qcMark("STUCK~" + LANGS[li] + "~" + pg.id + "~" + r.stuck.length);
        } catch (e) { qcMark("ERR~" + pg.id + "~" + String(e).slice(0, 40).replace(/[^a-zA-Z0-9]/g, "_")); }
      }
      f.remove();
    }
  }
  // phone width: no page may scroll sideways (a hand cannot reach what sits past the edge)
  localStorage.setItem("mice.lang", "en");
  for (var qi = 0; qi < PAGES.length; qi++) {
    var f2 = document.createElement("iframe");
    f2.style.cssText = "width:390px;height:800px";
    document.body.appendChild(f2);
    f2.src = PAGES[qi].url;
    await ready(f2); await sleep(PAGES[qi].wait || 1500);
    try {
      var d2 = f2.contentDocument;
      qcMark("PHONEW~" + PAGES[qi].id + "~" + (d2.documentElement.scrollWidth - 390));
    } catch (e) { qcMark("ERR~phone~" + PAGES[qi].id); }
    f2.remove();
  }
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def _run(t):
    if not browser.available():
        t.give_up("headless browser not found — install Edge/Chromium or run --quick")
    fake_serial.reset()
    # The Voice page shows what the voice helper last said. Another check's helper (or the real one on
    # this PC) answers with its own test sentence, a Thai name, and the page then "leaks" it into en/zh/ja.
    # Point the hub at a dead helper: the page is read the way a hub with no helper shows it.
    import os
    import tempfile
    dead = os.path.join(tempfile.gettempdir(), "mice_qc_voice_dead_vl_%d.json" % os.getpid())
    with open(dead, "w", encoding="utf-8") as f:
        f.write('{"service": "http://127.0.0.1:9"}')
    os.environ["MICE_VOICE_CONFIG"] = dead
    base, _main = F.start_hub()
    cfg = json.loads((HERE / "pages.json").read_text(encoding="utf-8"))
    pages = [{"id": p["id"], "url": p["url"], "wait": p.get("wait"),
              "latin": p.get("latin", True), "tabs": [None] + [s["steps"][0]["eval"] for s in p.get("states", [])
                                if s.get("leak") and s["steps"] and "eval" in s["steps"][0]]}
             for p in cfg["pages"] if p.get("leak", True)]
    allow = cfg.get("thaiAllowed", [])
    langs = list(cfg["langs"])       # en too: its Thai is checked; th/zh/ja: their English is
    drv = (DRIVER.replace("__PROBE__", (HERE / "probe.js").read_text(encoding="utf-8"))
           .replace("__PAGES__", json.dumps(pages)).replace("__LANGS__", json.dumps(langs))
           .replace("__ALLOW__", json.dumps(allow)).replace("__LALLOW__", json.dumps(cfg.get("latinAllowed", []))))
    browser.raw_page("<h1>wrapper</h1><script>" + drv + "</script>", base, seconds=240)
    marks = list(fake_serial.qc_marks)
    t.ok(any(m == "done" for m in marks), "the scan finished", marks[-3:])
    t.ok(not any(m.startswith("ERR~") for m in marks), "no page threw", [m for m in marks if m.startswith("ERR~")])
    thai = [m for m in marks if m.startswith("THAI~")]
    t.ok(len(thai) >= len(pages) * len(langs), "every page was scanned in every language", len(thai))
    for m in thai:
        _, lang, pid = m.split("~")[:3]
        n = int(m.split("~")[-2])
        if lang != "th":
            t.ok(n == 0, "no Thai on %s in %s" % (pid, lang), m)
    for m in marks:
        if m.startswith("LATIN~"):
            _, lang, pid = m.split("~")[:3]
            if lang != "en":     # English pages are English; Thai/Chinese/Japanese pages must not keep English UI words
                n = int(m.split("~")[-2])
                t.ok(n == 0, "no leftover English UI text on %s in %s" % (pid, lang), m)
    # Tooltips / placeholders / labels still in English. Not zero yet (long tooltips): a RATCHET, so it can only go down.
    left = {}
    for m in marks:
        if m.startswith("ATTR~"):
            _, lang, pid, n = m.split("~")
            left[lang] = left.get(lang, 0) + int(n)
    base_n = cfg.get("attrLeakBaseline", {})
    for lang, n in sorted(left.items()):
        if lang != "en":
            t.ok(n <= base_n.get(lang, 0), "English tooltips/placeholders left in %s: %d (ceiling %d, lower it when you translate)" % (lang, n, base_n.get(lang, 0)), left)
    for m in marks:
        if m.startswith("PHONEW~"):
            _, pid, extra = m.split("~")
            t.ok(int(extra) <= 2, "%s does not scroll sideways on a 390 px phone" % pid, m)
    for m in marks:
        if m.startswith("STUCK~"):
            _, lang, pid, n = m.split("~")
            t.ok(int(n) == 0, "no popup pinned at the corner on %s (%s)" % (pid, lang), m)


def run(t):
    # The worker process runs more checks after this one: the dead voice helper must not leak into them.
    prev = os.environ.get("MICE_VOICE_CONFIG")
    try:
        return _run(t)
    finally:
        if prev is None:
            os.environ.pop("MICE_VOICE_CONFIG", None)
        else:
            os.environ["MICE_VOICE_CONFIG"] = prev
