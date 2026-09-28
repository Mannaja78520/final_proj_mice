"""Studio opened from the hub follows the fastest route while it stays open.

The hub used to put the route that was fastest at open time in Studio's URL.
That froze the page on one cable or WiFi address.  This check keeps one Studio
page open, changes the hub's answer after the first JOINT, and proves the next
JOINT reaches the same fake board over WiFi.  No hardware is used.
"""
import browser
import fake_serial
import fake_wifi
import qc as F

AREA = "studio"
TITLE = "an open Studio page follows the hub's fastest route"
SLOW = True


DRIVER = r"""
async function report(mark) {
  await fetch('/api/usb/cmd?port=COM99&id=0&c=' +
    encodeURIComponent('MOVE QCMARK ' + mark));
}
window.addEventListener('load', async function () {
  try {
    const ready = await qcWaitFor(() => typeof rawCmd === 'function' &&
      typeof haveAuto === 'function' && haveAuto(), 15000);
    if (!ready) throw new Error('auto route did not become ready');
    await rawCmd('JOINT WAIST 91');
    await rawCmd('JOINT SHRUG 92');
    const yaml = 'name: auto-route\nsteps: []\n';
    await sdUpload('auto-route.yaml', yaml);
    const readBack = await sdDownload('auto-route.yaml');
    await sdDelete('auto-route.yaml');
    if (readBack !== yaml) throw new Error('auto route file round trip changed data');
    await report('auto-' + moduleDev());
    await report('files-ok');
  } catch (e) {
    await report('ERROR-' + String(e).replace(/[^A-Za-z0-9]/g, '_').slice(0, 80));
  }
  await report('done');
});
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - run --quick")
    fake_serial.reset()
    fake_wifi.reset()
    wifi = fake_wifi.start()
    base, main = F.start_hub()
    auto = "auto:chip/QC-STUDIO"
    usb = "usb:" + fake_serial.PORT
    wifi_dev = "wifi:" + wifi
    original = main.resolve_auto

    def fastest(dev):
        if dev != auto:
            return original(dev)
        first_joint_arrived = any(c == "JOINT WAIST 91" for _ms, c in fake_serial.wire)
        return wifi_dev if first_joint_arrived else usb

    main.resolve_auto = fastest
    try:
        browser.page(DRIVER,
                     query=base + "/studio/_qcdriver.html?dev=" + auto + "&monitor=1",
                     seconds=35)
    finally:
        main.resolve_auto = original

    marks = fake_serial.qc_marks
    t.contains(marks, "done", "the open Studio page finished")
    t.ok(not any(m.startswith("ERROR-") for m in marks),
         "Studio accepted auto:<board>", repr(marks))
    t.contains(marks, "auto-" + auto,
               "Studio keeps the board key instead of freezing one route")
    t.ok(any(c == "JOINT WAIST 91" for _ms, c in fake_serial.wire),
         "the first Studio command used the fastest cable route",
         repr(fake_serial.wire[-12:]))
    t.ok("JOINT SHRUG 92" in fake_wifi.MODULE.cmds,
         "the next command from the same page followed the new fastest WiFi route",
         repr(fake_wifi.MODULE.cmds[-12:]))
    t.contains(marks, "files-ok",
               "Studio file upload, download and delete use the auto device API")
    t.ok("auto-route.yaml" not in fake_wifi.MODULE.files,
         "the file round trip ended with the requested delete")
