"""Studio's "Open module config" must point at the board Studio is talking to.

The failure mode worth guarding is a silent one: the button opens *a* module
page, but for the wrong transport or the wrong bus address, so you end up
configuring a different board than the one you are posing. So the check asserts
the exact URL for each way Studio can be connected.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "open-module-config targets the connected board"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof moduleDev !== "function") return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");

    // 1) shared USB, no bus id -> the cable's own board
    qcMark("D1-" + moduleDev());

    // 2) shared USB with an RS485 address -> a board BEHIND that cable
    document.getElementById("busId").value = "7";
    qcMark("D2-" + moduleDev());
    document.getElementById("busId").value = "";

    // 3) WiFi as well: commands prefer the cable, so the button must too --
    // opening the WiFi page while driving the cable would configure the
    // right board by luck only
    document.getElementById("robotIp").value = "10.0.0.5";
    qcMark("D3-" + moduleDev());

    // 4 and 5 need the link torn down — but qcMark reports THROUGH that link,
    // so take the readings first, restore, then send them.
    var keep = hubPort;
    hubPort = "";
    var d4 = moduleDev();                       // WiFi alone
    document.getElementById("robotIp").value = "";
    var d5 = moduleDev() || "none";             // nothing connected at all
    hubPort = keep;
    qcMark("D4-" + d4);
    qcMark("D5-" + d5);
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    port = fake_serial.PORT
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" % (base, port),
                 seconds=20)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the page ran clean", marks)
    got = {m.split("-", 1)[0]: m.split("-", 1)[1] for m in marks if "-" in m}

    t.eq(got.get("D1"), "usb:" + port, "shared USB targets that cable")
    t.eq(got.get("D2"), "usb:%s:7" % port,
         "an RS485 bus id is carried through, so the page opens the board behind the cable")
    t.eq(got.get("D3"), "usb:" + port,
         "with both links up it follows the cable, like every other command")
    t.eq(got.get("D4"), "wifi:10.0.0.5", "WiFi alone targets that address")
    t.eq(got.get("D5"), "none", "with nothing connected it opens nothing")

    # ---- and the hub really serves the page those strings point at ----
    for dev in ("usb:" + port, "usb:%s:7" % port, "wifi:10.0.0.5"):
        import urllib.parse
        s, b = F.get("%s/mod?dev=%s" % (base, urllib.parse.quote(dev)))
        t.eq(s, 200, "the hub serves the module site for %s" % dev)
        t.contains(b, "/api/dev/", "and it carries the transport shim for %s" % dev)

    # the button exists and is wired
    idx = (F.STUDIO_WEB / "index.html").read_text(encoding="utf-8", errors="replace")
    t.contains(idx, "openModule()", "the Robot link card has the button")
