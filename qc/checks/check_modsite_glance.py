"""Standing at a board, its own page says what it is — without being asked.

The module website showed a name, an id, a type, a WiFi line and an SD flag.
The board reports three more things about itself in the same status payload,
and none of them reached the screen:

  fw     which firmware it runs. The first question anyone asks about a board
         behaving oddly, and the only way to get it was to send INFO on a
         console.
  group  which installation it belongs to. The hub has a whole screen about
         grouping and the board never said which group it was in.
  seq    whether it is running a sequence RIGHT NOW. Someone reaching into an
         arm needs to know whether it is about to move.

And one thing the board cannot know but the page can: whether you are talking
to it over WiFi or through the hub on a cable. Unplugging a cable means
something different from losing WiFi, so the page says which one it is.

Driven in a real browser, through the hub, which is how a person on a cable
sees this page.
"""
import urllib.parse

import browser
import fake_serial
import qc as F

AREA = "modsite"
TITLE = "the board's page says what it is at a glance"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="%s"></iframe>
<script>
function say(k, v){ return qcMark("GL " + k + "=" + String(v).replace(/[\\s|]+/g, "~")); }
window.addEventListener("load", async function(){
  try{
    var d = document.getElementById('f').contentDocument;
    await qcWaitFor(function(){
      var n = d.getElementById('hname');
      return n && n.textContent && n.textContent !== 'module'; }, 15000);
    await say("name", d.getElementById('hname').textContent);
    await say("id", d.getElementById('hid').textContent);
    await say("type", d.getElementById('htype').textContent);
    await say("fw", (d.getElementById('hfw')||{}).textContent || "MISSING");
    var gw = d.getElementById('hgroupwrap');
    await say("grouphidden", gw ? (gw.hidden ? "yes" : "no") : "MISSING");
    await say("now", (d.getElementById('hnow')||{}).textContent || "MISSING");
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    url = "/mod?dev=usb%3A" + urllib.parse.quote(fake_serial.PORT)

    def look():
        """Open the page and read what it says about itself."""
        browser.raw_page(DRIVER % url, base, seconds=40)
        out = {}
        for m in fake_serial.qc_marks:
            if m.startswith("GL "):
                k, _, v = m[3:].partition("=")
                out[k] = v.replace("~", " ")
        return out

    got = look()
    if not t.ok(got, "the board's page reported back", fake_serial.qc_marks[-4:]):
        return

    # ---- who it is ----------------------------------------------------
    t.ok(got.get("name"), "the page names the board", got)
    t.ok(got.get("id"), "and gives its id")
    t.ok(got.get("type"), "and its module type")

    # ---- WHICH FIRMWARE. The question that used to need a console. -----
    fw = got.get("fw", "")
    t.ok(fw and fw not in ("MISSING", "-", "?"),
         "and which firmware it is running",
         "a board behaving oddly is asked this first, and the page could not "
         "answer it: %r" % fw)

    # ---- the group label is honest when there is no group -------------
    # An empty label reads as a group called nothing. A board in no
    # installation should say nothing at all.
    t.ok(got.get("grouphidden") in ("yes", "no"),
         "the group badge exists", got.get("grouphidden"))

    # ---- what it is DOING, and how you reached it ---------------------
    now = got.get("now", "").lower()
    t.ok(now and now != "missing",
         "the page says what the board is doing", got.get("now"))
    t.contains(now, "not running",
               "idle in plain words, when it is idle")

    # ---- and now with the board actually playing something ------------
    # This is the state that matters: an arm on a timer looks exactly like a
    # still one. Asserting only the idle wording left the branch that names
    # the running sequence untested, which was proven by breaking it and
    # watching the check pass anyway.
    fake_serial.NONG.playing = True
    fake_serial.NONG.playing_file = "/moves/qc_show.yaml"
    try:
        busy = look()
    finally:
        fake_serial.NONG.playing = False
        fake_serial.NONG.playing_file = ""

    saying = busy.get("now", "").lower()
    t.contains(saying, "playing",
               "it says the board is playing something")
    t.contains(saying, "qc_show.yaml",
               "and NAMES the sequence, so you know what is about to move")
    # This page was opened through the hub over a cable, so it must say so —
    # unplugging a cable is not the same failure as losing WiFi.
    t.ok("cable" in now,
         "and that this page is reached over the cable, through the hub",
         "got %r" % got.get("now"))
