"""A frozen Studio page cannot leave the robot running a show (A26-46).

User 2026-09-17: *when web freeze it make not match with robot and when stop in
web after freeze the robot it still move not stop because i can't stop the web
is freeze*. The hub plays the show so it survives the page being hidden or
closed - on purpose - but that also meant a FROZEN page kept the arm moving
with no way to press Stop there.

So a Studio page that starts a show asks to be watched and beats every second
while on screen. Hidden or closed, it says so first and the show carries on as
before. Silent without saying so = frozen: the hub stops the show and the arm.

Asserted on the fake module's wire (STOP reached it) and on the hub's player.
"""
import json
import time
import urllib.request

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "a frozen Studio page stops the hub's show; a hidden or closed one does not"
SLOW = True

DRIVER = """
const wait = ms => new Promise(r => setTimeout(r, ms));
async function step(){
  try{
    while (typeof hubPlay !== "function" || !haveUsb()) await wait(200);
    document.getElementById("liveChk").checked = true; liveChanged();
    pose = pose.map(function(){ return 80; });  addKey();
    pose = pose.map(function(){ return 100; }); addKey();
    keys.forEach(function(k,i){ if(i){ k.t = 1000; k.hold = 20000; } });
    playT = 0; togglePlay();
    await wait(3500);
    qcMark("playing-" + playing);
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def _steps():
    return [{"pose": [90] * 10, "t": 80, "hold": 0},
            {"pose": [60] * 10, "t": 200, "hold": 60000}]


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    show, dev = main.show, "usb:%s" % fake_serial.PORT
    show.BEAT_TIMEOUT = 1.0                     # the rule, at test speed

    # ---- 1. watched and silent: stopped, and the arm told to STOP ------
    show.start(dev, _steps(), watch=True)
    t0 = time.time()
    while show.running() and time.time() - t0 < 6:
        time.sleep(0.05)
    t.ok(not show.running(), "a watched show whose page went silent is stopped",
         "still running after %.1f s" % (time.time() - t0))
    t.ok("froze" in show.status()["error"], "and says why, in plain words",
         show.status()["error"])
    t.ok("STOP" in [c for _, c in fake_serial.wire], "and the arm got STOP",
         [c for _, c in fake_serial.wire][-4:])

    # ---- 2. the page said it was leaving: the show carries on ----------
    show.start(dev, _steps(), watch=True)
    urllib.request.urlopen(urllib.request.Request(
        base + "/api/play/beat", data=json.dumps({"leaving": True}).encode(),
        method="POST"), timeout=5).read()
    time.sleep(2.5)
    t.ok(show.running(), "a page that was hidden or closed ON PURPOSE leaves the show running",
         "the show surviving a closed page is the reason the hub plays it")
    show.stop()

    # ---- 3. never watched (a hub-page play): unchanged -----------------
    show.start(dev, _steps())
    time.sleep(2.5)
    t.ok(show.running(), "a show nobody asked to watch is not stopped by silence")
    show.stop()

    # ---- 4. the real Studio page beats while it plays ------------------
    if not browser.available():
        t.give_up("headless Edge unavailable - the hub half above still ran")
    fake_serial.reset()
    show.BEAT_TIMEOUT = 2.5     # beats come every 1 s; 1.0 here would be a coin toss
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran without throwing", marks[-4:])
    t.contains(marks, "playing-true",
               "a Studio page on screen keeps its show alive past the timeout by beating")
    st = show.status()
    t.ok(show.watched and not st["error"],
         "and the hub knows it is being watched", st)
    show.stop()
    show.BEAT_TIMEOUT = 4.0
