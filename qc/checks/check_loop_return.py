"""A looping show travels back to its start in time with the robot.

Bench 2026-09-17: at the end of a looping show the preview jumped straight to
the first pose while the real arm still had to travel there (slowly, under the
safety cap), so from then on the web ran ahead of the robot. Now the travel back
is a timed segment in the preview, in the steps the hub plays, and in the live
sends. The hub also waits as long as the board says a move really takes.
"""
import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = 'a looping show travels back to the start in time with the robot'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => typeof loopReturnMs === 'function', 6000);
    const a = new Array(10).fill(90), b = a.slice(); b[0] = 150;
    keys = [{pose: a, t: 1000, hold: 0}, {pose: b, t: 2000, hold: 0}];
    bumpKeys();
    document.getElementById('loopChk').checked = false;
    const plain = totalMs();
    document.getElementById('loopChk').checked = true; bumpKeys();
    const ret = loopReturnMs(), total = totalMs();
    await qcMark('ret-' + ret + '-grew-' + (total - plain));
    const mid = poseAt(plain + ret / 2)[0];
    await qcMark('mid-' + (mid > 100 && mid < 140));
    await qcMark('seg-' + (segmentAt(plain + ret / 2) === 2));
    const st = hubShowSteps();
    await qcMark('steps-' + st.length + '-last-' + st[st.length - 1].pose[0] + '-t-' + (st[st.length - 1].t === ret));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    base, main = F.start_hub()
    took = main.ShowPlayer._took
    t.eq(took("OK pose T=2356ms", 500), 2356, "the hub waits the time the board reports")
    t.eq(took("OK pose T=300ms", 900), 900, "but never less than it asked for")
    t.eq(took("ERR busy", 700), 700, "and an answer without a time changes nothing")

    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html', seconds=20)
    m = fake_serial.qc_marks
    t.contains(m, 'done', 'the page ran to the end')
    ret = [x for x in m if x.startswith('ret-')]
    ok = False
    if ret:
        parts = ret[0].split('-')                 # ret-<ms>-grew-<ms>
        ok = int(parts[1]) >= 60 * 1570 // 60 and parts[1] == parts[3]
    # 60 deg back at <= 60 deg/s peak needs >= 60*pi/2/60 s = 1571 ms
    t.ok(ok, 'loop adds the travel back, at least as long as the safety cap needs', repr(ret))
    t.contains(m, 'mid-true', 'the preview is halfway back halfway through that travel')
    t.contains(m, 'seg-true', 'and it counts as a move the robot is sent')
    t.ok(any(x.startswith('steps-3-last-90-t-true') for x in m),
         'the hub is given the travel back as its own step', repr(m))
