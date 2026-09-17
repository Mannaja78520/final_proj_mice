"""A frozen Studio page reports itself to the hub.

User 2026-09-17: the whole page freezes during play, drag, live mode and even
idle. Headless it did not happen (0 long tasks), so the page must record it on
the machine where it does. This blocks the page for 2.5 s on purpose and
asserts a STUDIO FREEZE report reached the hub's reports folder, with the
state that says what was running.
"""
import json

import browser
import fake_serial
import qc as F

AREA = 'studio'
TITLE = 'a frozen Studio page sends a freeze report to the hub'
SLOW = True

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => typeof freezeCheck === 'function', 4000);
    await new Promise(r => setTimeout(r, 1500));
    const t0 = performance.now();
    while (performance.now() - t0 < 2500) {}          // the freeze
    await new Promise(r => setTimeout(r, 2000));      // next frame sees the gap
    await qcMark('sent-' + (_fw.sentAt >= 0) + '-hidden-' + document.hidden);
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    if not browser.available():
        t.give_up('headless Edge unavailable')
    fake_serial.reset()
    base, main = F.start_hub()
    rep = main.HERE / "reports"
    before = set(rep.glob("*.json")) if rep.is_dir() else set()
    browser.page(DRIVER, query=base + '/studio/_qcdriver.html?dev=usb%3A' + fake_serial.PORT,
                 seconds=20)
    t.contains(fake_serial.qc_marks, 'done', 'the page ran to the end')
    new = [p for p in (set(rep.glob("*.json")) if rep.is_dir() else set()) - before]
    texts = []
    for p in new:
        try:
            texts.append(json.loads(p.read_text(encoding="utf-8")).get("text", ""))
        except (OSError, ValueError):
            pass
        finally:
            try:
                p.unlink()                              # QC leaves no reports behind
            except OSError:
                pass
    hit = [x for x in texts if x.startswith("STUDIO FREEZE ")]
    if t.ok(hit, "the freeze reached the hub as a report",
            "reports %r, marks %r" % (texts, fake_serial.qc_marks)):
        state = json.loads(hit[0][len("STUDIO FREEZE "):])
        t.ok(state.get("gapMs", 0) >= 1500, "it says how long the page was stuck", repr(state))
        t.ok("slowCalls" in state and "playing" in state and "gpu" in state,
             "and what was running", repr(state))
