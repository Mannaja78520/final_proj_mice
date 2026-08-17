"""Every page loads and runs without throwing.

This is the bug class that hid in plain sight. `isNong` was used twice in the
module website and defined nowhere — a ReferenceError thrown in the middle of
the status handler, which silently killed the joint sliders AND everything
rendered after that line. The data was perfect the whole time; three checks
covered the area and every one of them passed, because they all tested *around*
the page instead of looking at it.

The first attempt at guarding this parsed the JavaScript looking for names with
no definition. That was the wrong instinct: a hand-rolled parser mis-handled
template literals, reported a dozen functions that plainly exist, and would
have trained everyone to ignore it. Do not reimplement a language.

Load each page in a real browser and fail on what it actually throws. No false
positives, and it catches the whole family — undefined names, null property
reads, bad JSON — at the moment they happen.
"""
import browser
import fake_serial
import qc as F

AREA = "ui"
TITLE = "every page loads and runs without throwing"
SLOW = True

# Each page, and how long to let it settle. The module site is served for a
# CABLE, which is where the slider bug lived.
PAGES = [
    ("hub", "/"),
    ("module site over USB", "/mod?dev=usb%3ACOM99"),
    ("nong studio", "/studio/"),
    ("help", "/help"),
]

PAGE = """
<style>html,body{margin:0}iframe{width:1200px;height:820px;border:0;display:block}</style>
<div id="frames"></div>
<script>
// Errors are collected per page. window.onerror inside a same-origin iframe
// reports the iframe's own throws, which is exactly what we want: a page that
// looks fine but threw halfway through building itself.
var PAGES = __PAGES__;
var errs = {}, done_ = 0;
PAGES.forEach(function(p, i){
  errs[i] = [];
  var f = document.createElement('iframe');
  f.src = p[1];
  document.getElementById('frames').appendChild(f);
  f.addEventListener('load', function(){
    try{
      f.contentWindow.addEventListener('error', function(e){
        errs[i].push(String((e && e.message) || 'error').slice(0, 70));
      });
      f.contentWindow.addEventListener('unhandledrejection', function(e){
        var r = e && e.reason;
        errs[i].push('reject:' + String((r && r.message) || r).slice(0, 60));
      });
    }catch(e){ errs[i].push('cross-origin'); }
  });
});
setTimeout(function(){
  var out = [];
  PAGES.forEach(function(p, i){
    out.push(p[0].replace(/ /g, '~') + '=' + (errs[i].length
      ? errs[i][0].replace(/[^A-Za-z0-9:._-]/g, '~') : 'clean'));
  });
  qcMark("PAGES " + out.join(" "));
  qcMark("done");
}, 14000);
</script>
"""


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    js_pages = "[" + ",".join('["%s","%s"]' % (n, u) for n, u in PAGES) + "]"
    browser.raw_page(PAGE.replace("__PAGES__", js_pages), base, seconds=26)

    marks = [m for m in fake_serial.qc_marks if m.startswith("PAGES ")]
    if not t.ok(marks, "the pages reported back",
                "nothing ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][6:].split(" ") if "=" in kv)

    for name, _ in PAGES:
        key = name.replace(" ", "~")
        res = got.get(key)
        if res is None:
            t.ok(False, "%s reported" % name, "no result for this page")
            continue
        t.ok(res == "clean",
             "%s runs without throwing" % name,
             "it threw: %s — a throw stops everything after it, which is how "
             "the joint sliders went missing with every other check green" % res)
