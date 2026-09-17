"""A module link waits for Studio login, then connects and starts its monitor.

Since 2026-09-17 the Studio login IS the hub login. Studio used to check a
local-only account list, so it looked logged in while the hub refused every
robot command with "log in before doing that" (user, in the lab). So:
a wrong password is refused BY THE HUB, the right one gives a hub session, and
a session made anywhere else (the hub page) logs Studio in by itself.
"""
import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = 'Studio login is the hub login, and resumes the requested connection'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    // Logged out, qcMark itself is refused by the hub: hold marks until login.
    const early = [];
    await qcWaitFor(() => document.getElementById('usbPort').dataset.loaded, 4000);
    await new Promise(r => setTimeout(r, 800));
    early.push('before-' + (haveUsb() || currentUser !== null));
    document.getElementById('loginUser').value = 'super_admin';
    document.getElementById('loginPass').value = 'wrong-password';
    await appLogin();
    const who1 = await fetch('/api/whoami').then(r => r.json());
    early.push('wrong-' + (currentUser === null && !haveUsb() && !who1.authed));
    document.getElementById('loginPass').value = '%s';
    await appLogin();
    const who2 = await fetch('/api/whoami').then(r => r.json());
    for (const m of early) await qcMark(m);
    await qcMark('hubsession-' + !!who2.authed);
    const connected = await qcWaitFor(() => haveUsb() && document.getElementById('monChk').checked, 4000);
    await qcMark('after-' + connected);
    // logged in elsewhere (the hub page): Studio follows without its own login
    currentUser = null;
    await syncHubLogin();
    await qcMark('adopt-' + (currentUser !== null));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
''' % F.HUB_PASSWORD


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    base, _ = F.start_hub()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html?dev=usb:COM99&monitor=1',
                 studio_login=False, hub_login=False, seconds=15)
    marks = fake_serial.qc_marks
    t.contains(marks, 'before-false', 'connection waits for login')
    t.contains(marks, 'wrong-true', 'wrong password never connects and the hub refuses it')
    t.contains(marks, 'hubsession-true', 'the Studio login logs in to the hub')
    t.contains(marks, 'after-true', 'valid login resumes connection and requested monitor')
    t.contains(marks, 'adopt-true', 'a hub session made elsewhere logs Studio in')
    t.contains(marks, 'done', 'login journey completes')
