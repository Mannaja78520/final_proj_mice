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
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "no Thai text leaks into en/zh/ja pages; no popup pinned at the top-left"
SLOW = True

HERE = Path(F.CODE) / "tools" / "visual"

DRIVER = """
__PROBE__
var ALLOW = __ALLOW__, LALLOW = __LALLOW__, PAGES = __PAGES__, LANGS = __LANGS__;
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function run(){
  for (var li = 0; li < LANGS.length; li++) {
    localStorage.setItem("mice.lang", LANGS[li]);
    for (var pi = 0; pi < PAGES.length; pi++) {
      var pg = PAGES[pi], f = document.createElement("iframe");
      f.style.cssText = "width:1200px;height:800px";
      document.body.appendChild(f);
      f.src = pg.url;
      await sleep(pg.wait || 2500);
      var tabs = pg.tabs || [null];
      for (var ti = 0; ti < tabs.length; ti++) {
        try {
          if (tabs[ti]) { f.contentWindow.eval(tabs[ti]); await sleep(700); }
          var r = visualProbe(f.contentDocument);
          var bad = r.thai.filter(function(s){ return !ALLOW.some(function(a){ return new RegExp(a).test(s); }); });
          qcMark("THAI~" + LANGS[li] + "~" + pg.id + (tabs[ti] ? "~" + ti : "") + "~" + bad.length + "~" + (bad[0] || "").replace(/[^\\u0E00-\\u0E7Fa-zA-Z0-9]/g, "_").slice(0, 24));
          var lat = pg.latin === false ? [] : r.latin.filter(function(s){ return !LALLOW.some(function(a){ return new RegExp(a).test(s); }); });
          qcMark("LATIN~" + LANGS[li] + "~" + pg.id + (tabs[ti] ? "~" + ti : "") + "~" + lat.length + "~" + (lat[0] || "").replace(/[^a-zA-Z0-9]/g, "_").slice(0, 30));
          qcMark("STUCK~" + LANGS[li] + "~" + pg.id + "~" + r.stuck.length);
        } catch (e) { qcMark("ERR~" + pg.id + "~" + String(e).slice(0, 40).replace(/[^a-zA-Z0-9]/g, "_")); }
      }
      f.remove();
    }
  }
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found — install Edge/Chromium or run --quick")
    fake_serial.reset()
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
                t.ok(int(m.split("~")[-2]) == 0, "no leftover English UI text on %s in %s" % (pid, lang), m)
    for m in marks:
        if m.startswith("STUCK~"):
            _, lang, pid, n = m.split("~")
            t.ok(int(n) == 0, "no popup pinned at the corner on %s (%s)" % (pid, lang), m)
