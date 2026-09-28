"""Studio drives a nong behind a plain USB-RS485 adapter without typing a bus id.

Bench 2026-09-17: nong #67 on the bus behind a CH340+MAX485 adapter on COM12.
The hub found it, WiFi worked, but Studio's "USB / RS485 (shared)" said
`no reply from COM12`: an adapter has no board of its own, so a command with
no `#<id>` reaches nobody, and the bus id box is hidden technical detail.

Now a silent cable makes Studio ask the hub who is behind it and use that id.
Asserted on the fake bus: the JOINT must reach the board, which the dongle only
delivers when it is framed with the board's id.
"""
import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = 'Studio finds the bus id behind a USB-RS485 adapter by itself'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    document.getElementById('connSel').value = 'usb';
    connModeChanged();
    await loadPorts();
    document.getElementById('usbPort').value = '%s';
    document.getElementById('busId').value = '';
    await connectRobot();
    await qcMark('linked-' + haveUsb());
    if (!haveUsb()) await qcMark('stat-' + document.getElementById('robotStat').textContent
      .replace(/[^A-Za-z0-9]/g, '_').slice(0, 90) + '-port-' + document.getElementById('usbPort').value);
    await qcMark('busid-' + document.getElementById('busId').value);
    await robotCmd('JOINT WAIST 91');
    // a fresh page knows no bus id: the last one that answered on this port
    // must be tried first, not two unaddressed INFOs and a bus census
    document.getElementById('busId').value = '';
    hubPort = '';
    const t0 = performance.now(), asked = [], realFetch = window.fetch;
    window.fetch = function (u, o) { asked.push(String(u)); return realFetch(u, o); };
    await connectRobot();
    window.fetch = realFetch;
    await qcMark('again-unaddressed-' + asked.filter(u => u.includes('usb/cmd') && /[?&]id=0&/.test(u)).length);
    await qcMark('again-' + haveUsb() + '-busid-' + document.getElementById('busId').value);
    await qcMark('again-ms-' + Math.round(performance.now() - t0));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
''' % fake_serial.DONGLE_PORT


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    fake_serial.dongle_listed[0] = True
    base, _ = F.start_hub()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html', seconds=40)
    marks = fake_serial.qc_marks
    t.contains(marks, 'done', 'the connect journey finished')
    t.contains(marks, 'linked-true', 'Studio connected through the adapter')
    t.ok(any(m.startswith('busid-') and m != 'busid-' for m in marks),
         'the bus id was filled in from the hub probe', repr(marks))
    t.ok(any(m.startswith('again-true-busid-') and m != 'again-true-busid-' for m in marks),
         'a second Connect recalls the bus id that answered last time', repr(marks))
    t.contains(marks, 'again-unaddressed-0',
               'the second Connect sends no command without the bus id')
    ms = [int(m[9:]) for m in marks if m.startswith('again-ms-')]
    t.ok(ms and ms[0] < 1500, 'and connects without a 2 s probe first',
         'took %r ms - COM21 took ~9 s per Connect (2026-09-27)' % ms)
    t.ok(any('JOINT' in c for _ms, c in fake_serial.wire),
         'the JOINT reached the board behind the adapter',
         'wire: %r' % (fake_serial.wire[-8:],))
