"""Monitor works over the RS485 adapter even when ticked before Connect (A26-42).

User 2026-09-17: *monitor: no reply (not connected) - but can connect and use
via rs485*. Monitor only ever polled: ticked with no open link - before Connect,
or after a first Connect that timed out while the hub opened the port - it said
"not connected" every 350 ms while the cable worked. It also let polls pile up
on one shared cable when a reply took longer than a tick.

Now ticking monitor connects first, and a poll never overlaps the previous one.
Asserted on the fake bus behind a USB-RS485 adapter: INFO reached the board and
the page shows the board's own state.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "monitor connects by itself over RS485, and polls one at a time"
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    document.getElementById('connSel').value = 'usb'; connModeChanged(); await loadPorts();
    document.getElementById('usbPort').value = '%s'; document.getElementById('busId').value = '';
    await qcMark('before-' + haveUsb());
    await qcMark('QCMON');
    document.getElementById('monChk').checked = true; monitorChanged();
    await qcWaitFor(() => /^MONITOR/.test(document.getElementById("robotStat").textContent), 15000);
    await qcMark('linked-' + haveUsb());
    await qcMark('stat-' + document.getElementById('robotStat').textContent
      .replace(/[^A-Za-z0-9]/g, '_').slice(0, 60));
    document.getElementById('monChk').checked = false; monitorChanged();
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
''' % fake_serial.DONGLE_PORT


def run(t):
    js = (F.CODE / "nong/main_python_set_nong/web/app_parts/robot_link.js").read_text(encoding="utf-8")
    tick = js[js.find("async function monitorTick"):]
    tick = tick[:tick.find(chr(10) + "function ", 10)]
    t.ok("if (monBusy) return;" in tick and "monBusy = false" in tick,
         "a monitor poll never starts while the last one is still waiting",
         "over RS485 a reply can outlast the 350 ms tick, and stacked polls failed")

    if not browser.available():
        t.give_up("headless Edge unavailable - the source half above still ran")
    fake_serial.reset()
    fake_serial.dongle_listed[0] = True
    base, _ = F.start_hub()
    browser.page(DRIVER, query=base + "/studio/_qcdriver.html", seconds=40)
    marks = fake_serial.qc_marks
    t.contains(marks, "done", "the page finished")
    t.contains(marks, "before-false", "monitor was ticked with no link open")
    t.contains(marks, "linked-true", "ticking monitor opened the link by itself")
    stat = next((m for m in marks if m.startswith("stat-")), "")
    t.ok(stat.startswith("stat-MONITOR"),
         "and the page shows what the board reports, not 'not connected'", stat)
    wire = [c for _, c in fake_serial.wire]
    try:
        i = wire.index("MOVE QCMARK QCMON")
    except ValueError:
        i = 0
    t.ok(sum(1 for c in wire[i:] if c.upper().startswith("INFO")) >= 2,
         "the board behind the adapter was asked for its state, again and again",
         wire[i:i + 10])
