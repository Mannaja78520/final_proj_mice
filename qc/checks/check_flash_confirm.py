"""Overwriting a board's firmware asks first, and says WHICH board and WHICH PC.

Flashing is not undoable from this screen, it takes about a minute, and the
board is often in someone else's hands across the room. Several PCs at a venue
each run this same hub on the same network, so the operator can be looking at
the wrong browser tab and not know it — the old confirm named a COM port or an
IP address and nothing else.

Driven in a real browser, because the thing under test is what a person reads
before they commit. Two halves, and the second is the one that matters:

  * the panel NAMES things — the board, its id, what it runs now, what it will
    become, how it is reached, and the PC doing it;
  * and CANCEL really cancels. A confirm that flashes anyway, or that starts
    the write while the question is still on screen, is worse than no confirm:
    it teaches people the question is meaningless.
"""
import json

import browser
import fake_serial
import qc as F

AREA = "flash"
TITLE = "flashing asks first, and names the board and the PC"
SLOW = True

DRIVER = """
<style>html,body{margin:0}#f{width:1100px;height:1000px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function say(k, v){ return qcMark("FC " + k + "=" + String(v).replace(/[ |]/g, "~")); }
window.addEventListener("load", async function(){
  try{
    var d = document.getElementById('f').contentDocument;
    var w = document.getElementById('f').contentWindow;

    // Wait for the cable row and its Flash button to exist — the page probes
    // the port first, and how long that takes is not ours to predict.
    // Flashing lives on the Firmware screen since A2-2, so go there first.
    // The button says what it does now — "Write over the cable" — because a
    // button called Flash next to a board is the least undoable control in
    // the product wearing the mildest word in the language.
    var tab = d.querySelector('#tabs [data-go="firmware"]');
    if (tab) tab.click();
    var ready = await qcWaitFor(function(){
      return [].slice.call(d.querySelectorAll('button'))
               .some(function(b){ return /write over/i.test(b.textContent); });
    }, 40000);
    // 40s, not 20. The three waits below can run back to back, and the page
    // window has to cover all of them - see raw_page(seconds=) at the bottom.
    // Under a parallel gate this tab is slow to draw its first row because it
    // asks /api/ports, /api/mine and /api/scan before it has anything to show.
    if (!ready){ await say("ready", "no"); return qcMark("done"); }

    var flash = [].slice.call(d.querySelectorAll('button'))
                  .filter(function(b){ return /write over/i.test(b.textContent); })[0];
    flash.click();

    // TWO DIFFERENT QUESTIONS, measured separately. This used to wait for the
    // modal AND for its details in one 8s window, and report the whole thing as
    // "asked". Under a loaded machine the details arrived late, and the check
    // then said the page had flashed WITHOUT ASKING - which is not what
    // happened, and is the most alarming thing it could have said. Failed twice
    // in parallel gates on 2026-08-20 and passed alone every time.
    var shown = await qcWaitFor(function(){
      var m = d.getElementById('flashModal');
      var ask = d.getElementById('fcAsk');
      // The QUESTION has to be visible, not just the dialog it lives in. The
      // shell is also used for the progress and result states, so watching it
      // alone passed with the ask panel hidden - proved with tools/sabotage.py.
      return m && !m.hidden && ask && !ask.hidden;
    }, 20000);
    await say("asked", shown ? "yes" : "no");
    var detailed = shown && await qcWaitFor(function(){
      return d.getElementById('fcMeta').textContent.length > 10;
    }, 20000);
    await say("detailed", detailed ? "yes" : "no");
    if (!shown) return qcMark("done");


    await say("meta", d.getElementById('fcMeta').textContent);
    await say("danger", d.getElementById('fcGo').className);

    // Now the RACE. MY_PC is filled by a fetch when the page loads, and the
    // confirm used to print `MY_PC || 'this PC'` — so a quick click showed a
    // dialog that did not name the machine at all. Reproduce that state
    // exactly: forget the name, reopen the dialog, and it must STILL name the
    // PC.
    d.getElementById('fcCancel').click();
    await qcWaitFor(function(){
      return d.getElementById('flashModal').hidden; }, 4000);
    w.MY_PC = '';
    flash.click();
    await qcWaitFor(function(){
      return !d.getElementById('flashModal').hidden; }, 6000);
    await say("cold", d.getElementById('fcMeta').textContent);

    // CANCEL, and prove nothing was started by it.
    d.getElementById('fcCancel').click();
    await say("closed", d.getElementById('flashModal').hidden ? "yes" : "no");
    qcMark("done");
  }catch(e){ qcFail(e); }
});
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    # what the hub thinks before anyone touches anything
    before = json.loads(F.get(base + "/api/flash")[1])

    browser.raw_page(DRIVER, base, seconds=115)
    got = {}
    for m in fake_serial.qc_marks:
        if m.startswith("FC "):
            k, _, v = m[3:].partition("=")
            got[k] = v.replace("~", " ")

    if not t.ok(got, "the hub page reported back", fake_serial.qc_marks[-4:]):
        return

    # THE ROW NOT APPEARING IS NOT THE PAGE FLASHING WITHOUT ASKING.
    #
    # Told apart because conflating them is alarming and wrong, which this
    # check already learned once about its two later waits. In the parallel
    # gate on 2026-08-20 the Firmware row took longer than its window to
    # render - the tab asks /api/ports, /api/mine and /api/scan first, and a
    # loaded machine is slow at all three - so no Flash button existed to
    # click. The check reported "clicking Flash ASKS instead of flashing",
    # which reads as the safety gate being gone. It was not: nothing had been
    # clicked at all.
    if got.get("ready") == "no":
        t.ok(False,
             "the Firmware row appeared in time to be clicked",
             "no button matching 'write over' rendered before the window ran "
             "out, so nothing was clicked and this run says nothing about "
             "whether flashing asks first. That is a slow page, not a missing "
             "confirm.")
        return
    if not t.eq(got.get("asked"), "yes",
                "clicking Flash ASKS instead of flashing"):
        return
    # A separate question, so a slow machine cannot make the page look as if it
    # flashed without asking - see the driver.
    t.eq(got.get("detailed"), "yes",
         "and the confirm fills in which board, before anything is written")

    meta = got.get("meta", "")
    # The four facts a person needs to know they are about to overwrite the
    # right board from the right machine.
    t.contains(meta, fake_serial.PORT,
               "the confirm says how the board is reached")
    t.contains(meta.lower(), "becomes",
               "and what it will become")
    t.contains(meta, main.socket.gethostname(),
               "and NAMES THIS PC — the operator may be on the wrong tab")
    # ...and still names it when the page has NOT yet been told its own name.
    # Without this the check passed by luck: the load-time fetch usually wins
    # the race, so the fallback wording never appeared and a real fault sat
    # there being intermittently reported as a flaky test.
    t.contains(got.get("cold", ""), main.socket.gethostname(),
               "and names it even before the page has learned its own name")
    t.ok("runs" in meta or "#" in meta,
         "and identifies the board itself, not only the port", meta[:120])

    t.contains(got.get("danger", ""), "danger",
               "the overwrite button is styled as destructive")
    t.eq(got.get("closed"), "yes", "cancel closes the panel")

    # ---- and cancel really cancelled ----------------------------------
    # Asserted against the HUB, not against the page: a panel that closes while
    # the write has already begun is exactly the failure this guards.
    after = json.loads(F.get(base + "/api/flash")[1])
    t.ok(after.get("running") == before.get("running"),
         "cancelling starts no flash",
         "the hub began writing firmware while the question was still on "
         "screen: before=%r after=%r" % (before.get("running"), after.get("running")))
    t.ok(not after.get("port") or after.get("port") == before.get("port"),
         "and no port was taken", after)
