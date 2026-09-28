"""Studio says when its joint limits differ from the robot's, and fixes it on a click.

Bench 2026-09-17: a show drawn at 25 and 155 deg ran on nong #67, whose limits
are 30..150, so the firmware clamped every such pose and the real arm did not
match the preview - silently. On connect Studio now compares LIMIT? with its rig
and shows both fixes; "Use the robot's limits" must make them agree.
"""
import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = "Studio warns when its joint limits differ from the robot's"
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => typeof haveUsb === 'function' && haveUsb(), 8000);
    const robot = JSON.parse(await rawCmd('LIMIT?'));
    RIG.min[0] = Math.round(+robot.min[0]) - 5;         // Studio allows more than the arm
    await checkLimitsMatch();
    const box = document.getElementById('limMismatch');
    await qcMark('shown-' + !box.hidden);
    await qcMark('names-' + /L shoulder pitch|L_SH_P/.test(document.getElementById('limMismatchText').textContent));
    await pullLimits(); await checkLimitsMatch();
    await qcMark('fixed-' + box.hidden + '-' + (Math.round(RIG.min[0]) === Math.round(+robot.min[0])));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    base, _ = F.start_hub()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html?dev=usb%3A' + fake_serial.PORT,
                 seconds=25)
    m = fake_serial.qc_marks
    t.contains(m, 'done', 'the page ran to the end')
    t.contains(m, 'shown-true', 'a limit that differs from the robot is shown')
    t.contains(m, 'names-true', 'naming the joint in words')
    t.contains(m, 'fixed-true-true', "Use the robot's limits makes them agree and the warning goes")
