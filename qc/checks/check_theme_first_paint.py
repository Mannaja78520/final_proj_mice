"""The saved theme is on the page before anything is drawn: no flash of the default colours.

2026-11-23 case review (GPT: "theme switch or reload during slow startup"): recording one frame at a
time while Studio loaded showed a frame with content and no data-theme, because mice.js (which sets
it) sits at the end of that page. A person on the daylight theme saw a dark flash on every open.
Every page of the hub is loaded here with a theme saved and watched frame by frame.
"""
import browser
import fake_serial
import qc as F

AREA = "web"
TITLE = "pages draw in the saved theme from the first frame"
SLOW = False

PAGES = ["/", "/help", "/studio/", "/app/tv/", "/app/camera/", "/app/gacha/", "/app/voice/",
         "/mod?dev=usb:COM99:67&name=nong-far"]

DRIVER = """
var PAGES = %s;
function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
async function one(url){
  var f = document.createElement("iframe");
  f.style.cssText = "width:900px;height:600px";
  document.body.appendChild(f);
  var bad = 0, seen = 0, stop = false;
  function tick(){
    try {
      var d = f.contentDocument;
      if (d && d.location.pathname !== "blank" && d.location.href !== "about:blank" && d.body && d.body.childElementCount > 0) {
        seen++;
        if (d.documentElement.getAttribute("data-theme") !== "daylight") bad++;
      }
    } catch (e) {}
    if (!stop) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
  f.src = url;
  await qcWaitFor(function(){ try { var d = f.contentDocument; return d.readyState === "complete" && d.location.pathname === url.split("?")[0]; } catch (e) { return false; } }, 20000);
  await sleep(300);
  stop = true;
  qcMark("TH~" + url + "~" + seen + "~" + bad);
  f.remove();
}
async function run(){
  localStorage.setItem("mice_theme", "daylight");
  localStorage.setItem("mice.lang", "en");
  for (var i = 0; i < PAGES.length; i++) await one(PAGES[i]);
  localStorage.removeItem("mice_theme");
  qcMark("done");
}
window.addEventListener("load", function(){ run(); });
""" % repr(PAGES)


def run(t):
    if not browser.available():
        t.give_up("headless browser not found")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.raw_page("<h1>wrapper</h1><script>" + DRIVER + "</script>", base, seconds=90)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("TH~"):
            _, url, seen, bad = m.split("~")
            got[url] = (int(seen), int(bad))
    t.ok(len(got) == len(PAGES), "every page was loaded", sorted(got))
    for url, (seen, bad) in sorted(got.items()):
        t.ok(seen > 0, "frames with content were seen on " + url, seen)
        t.ok(bad == 0, "no frame in the default colours on " + url, "%d of %d frames" % (bad, seen))
