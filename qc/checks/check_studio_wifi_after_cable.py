"""WiFi picked after the cable is gone: Studio connects over WiFi, not the dead port.

User 2026-09-28: nong ran on the CH340 adapter (COM21), then was unplugged and
carried to another room. Studio's Find modules showed it on WiFi at
10.139.24.70 and the link said "+ WiFi", but every Connect failed with
`could not open port 'COM21'`. The page still held the old cable (hubPort),
and the cable always wins over WiFi - so a Connect over WiFi never tried WiFi.

Now, with WiFi picked, a cable that does not answer is dropped and the status
is asked over WiFi. Asserted on the fake WiFi module: the JOINT sent after the
connect must reach it (robot_link.js, connectLink).
"""
import browser
import fake_serial
import fake_wifi
import qc as F

AREA = 'studio'
TITLE = 'Studio falls back to WiFi when the remembered cable is gone'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    hubPort = 'COM_QC_GONE';                 // the unplugged adapter
    document.getElementById('connSel').value = 'wifi';
    connModeChanged();
    document.getElementById('robotIp').value = '%s';
    await connectRobot();
    await qcMark('cable-' + (hubPort || 'dropped'));
    await qcMark('wifi-' + haveWifi());
    await qcMark('stat-' + document.getElementById('robotStat').textContent
      .replace(/[^A-Za-z0-9]/g, '_').slice(0, 80));
    await robotCmd('JOINT WAIST 91');
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    wifi = fake_wifi.start()
    base, _ = F.start_hub()
    browser.page(DRIVER % wifi, query=base + '/studio/_qcdriver.html', seconds=40)
    marks = fake_serial.qc_marks
    t.contains(marks, 'done', 'the connect journey finished')
    t.contains(marks, 'cable-dropped', 'the dead cable was let go')
    t.ok(not any(m.startswith('stat-Could_not') for m in marks),
         'Connect says it reached the robot', repr(marks))
    t.ok(any('JOINT' in c for c in fake_wifi.MODULE.cmds),
         'the next command went over WiFi to the robot',
         'wifi got: %r' % (fake_wifi.MODULE.cmds[-6:],))
