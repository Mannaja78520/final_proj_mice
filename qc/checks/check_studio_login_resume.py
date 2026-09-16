"""A module link waits for Studio login, then connects and starts its monitor."""
import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = 'Studio login resumes the requested connection without bypassing login'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => document.getElementById('usbPort').dataset.loaded, 4000);
    await qcMark('before-' + haveUsb());
    document.getElementById('loginUser').value = 'super_admin';
    document.getElementById('loginPass').value = 'wrong-password';
    appLogin();
    await qcMark('wrong-' + (currentUser === null && !haveUsb()));
    document.getElementById('loginPass').value = 'admin123';
    appLogin();
    const connected = await qcWaitFor(() => haveUsb() && document.getElementById('monChk').checked, 4000);
    await qcMark('after-' + connected);
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    base, _ = F.start_hub()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html?dev=usb:COM99&monitor=1',
                 studio_login=False, seconds=15)
    marks = fake_serial.qc_marks
    t.contains(marks, 'before-false', 'connection waits for login')
    t.contains(marks, 'wrong-true', 'wrong password never connects')
    t.contains(marks, 'after-true', 'valid login resumes connection and requested monitor')
    t.contains(marks, 'done', 'login journey completes')
