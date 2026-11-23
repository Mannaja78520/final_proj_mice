"""Browser dialogs (confirm / alert / prompt) follow the chosen language.

2026-11-23 case review: the page's own text is translated by watching the page, but a confirm()
box is not in the page, so "x.yaml is already saved. Replace it?" stayed English (or Thai) for
everyone. mice-lang.js now translates the text before it opens a dialog: whole text, else line by
line, and an entry with {} matches a line that names a file. The line breaks are kept.
"""
import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "confirm() dialogs are translated, with file names and line breaks kept"
SLOW = False

DRIVER = """
function ready(f){ return qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && f.contentWindow.MiceLang && d.body && d.body.innerText.length > 20; } catch (e) { return false; } }, 25000); }
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function one(lang){
  localStorage.setItem("mice.lang", lang);
  var f = document.createElement("iframe");
  f.style.cssText = "width:800px;height:600px";
  document.body.appendChild(f);
  f.src = "/";
  await ready(f); await sleep(1500);
  var w = f.contentWindow, say = w.MiceLang.say;
  qcMark("D~" + lang + "~wrapped~" + (String(w.confirm).indexOf("say(") >= 0 ? 1 : 0));
  qcMark("D~" + lang + "~document~" + f.contentDocument.documentElement.lang);
  qcMark("D~" + lang + "~file~" + JSON.stringify(say("my_move.yaml is already saved. Replace it?\\n\\nCancel, then type a new name to keep both.")));
  qcMark("D~" + lang + "~two~" + JSON.stringify(say("a.yaml has 3 step(s) this editor cannot read. Saving over it removes them.")));
  qcMark("D~" + lang + "~plain~" + JSON.stringify(say("nothing to translate here 123")));
}
async function run(){
  await one("zh"); await one("th");
  localStorage.setItem("mice.lang", "en");
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=70)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("D~"):
            _, lang, key, val = m.split("~", 3)
            got[(lang, key)] = val
    t.ok(len(got) == 10, "both languages answered", sorted(got))
    if len(got) == 10:
        for lang in ("zh", "th"):
            t.eq(got[(lang, "document")], lang, "screen readers get the selected language (%s)" % lang)
            t.ok(got[(lang, "wrapped")] == "1", "confirm() goes through the language layer (%s)" % lang)
            f = got[(lang, "file")]
            t.ok("my_move.yaml" in f and "\\n\\n" in f and "Replace" not in f, "the file name and the blank line survive (%s)" % lang, f)
            t.ok("a.yaml" in got[(lang, "two")] and "3" in got[(lang, "two")] and "editor" not in got[(lang, "two")],
                 "two names in one line are both carried over (%s)" % lang, got[(lang, "two")])
            t.ok(got[(lang, "plain")] == '"nothing to translate here 123"', "a text with no entry is left alone (%s)" % lang)
