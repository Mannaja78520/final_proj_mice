"""A show runs straight through, repeats an item, and draws itself on the bar.

Three things the user asked for on 2026-09-23:

  * *make every sequence in show run continute no stop before go to other
    sequence if not insert pause number*. Every sequence's FIRST step is its
    start pose, timed for travel from wherever the robot happened to be -
    yakyai.yaml carries T 3273. Chained, the arm is already standing on the
    previous sequence's last pose, so that 3.3 s was the arm holding nearly
    still between sequences: a stop, in everything but name. shows.py now
    re-times that one step from the REAL previous pose at the sequence's own
    speed, so identical poses hand over in 80 ms and only a `hold` the operator
    typed makes the robot wait.

  * *make can loop the sequence for how many time like 60S or 30S or make it
    loop for 4 time 3 time - have this 2 mode too*. Per item: repeat_mode
    "times" or "seconds", with one number. Seconds never cuts a pass in half -
    a pass stopped mid-move would leave the arm at a pose nobody chose - so it
    starts another whole pass while the elapsed time is still under target.

  * *when click in show and we have the all sequence show all of it in nong
    studio too in series*. /api/show/steps hands Studio THE SAME list the robot
    will run, with a mark per pass, so the editor cannot drift from the player.

The wire is the witness for the first one: the poses that actually reached the
module, with the T the hub asked for.
"""
import json
import time

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a show runs with no gap, repeats an item, and loads onto the time bar"
SLOW = True

# Two sequences that END and START on the same pose, each with a long authored
# entry time - the exact shape that produced the three-second stare.
ONE = ("name: qc_cont_one\nsteps:\n"
       "  - speed: 60\n"
       '  - pose: "20 90 90 90 90 90 90 90 90 90 T 3000"\n'
       '  - pose: "21 90 90 90 90 90 90 90 90 90 T 200"\n')
TWO = ("name: qc_cont_two\nsteps:\n"
       "  - speed: 60\n"
       '  - pose: "21 90 90 90 90 90 90 90 90 90 T 3000"\n'
       '  - pose: "22 90 90 90 90 90 90 90 90 90 T 200"\n')

DRIVER = '''
window.addEventListener('load', async function(){
  try {
    await qcWaitFor(() => typeof showOnTimeline === 'function', 8000);
    showTab('shows');
    await refreshShows();
    newShow();
    const add = document.getElementById('showAddSeq');
    add.value = 'qc_cont_one.yaml'; addShowItem();
    add.value = 'qc_cont_two.yaml'; addShowItem();
    showDraft.items[0].repeat_mode = 'times';
    showDraft.items[0].repeat = 3;
    renderShow();
    // what the tab SAYS goes on the wire too: when this fails it is almost
    // always the hub refusing, and the refusal is the one line worth reading.
    await showOnTimeline();
    await qcMark('stat-' + document.getElementById('showStat').textContent.slice(0, 60).replace(/[^A-Za-z0-9]+/g, '_'));
    await qcMark('bar-keys-' + keys.length);
    await qcMark('bar-named-' + keys.filter(k => k.seqStart).length);
    await qcMark('bar-first-' + Math.round(keys[0].pose[0]));
    // the hand-over keyframe: pass 2 of qc_cont_one starts on pose 20 again,
    // travelling from 21 - one degree, so it must be the 80 ms floor.
    await qcMark('bar-handover-' + keys[2].t);
    await qcMark('bar-label-' + (keys[2].name || ''));
  } catch (e) { await qcFail(e); }
  await qcMark('done');
});
'''


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    F.login(base)
    seq = main.SEQUENCES
    seq.mkdir(exist_ok=True)
    made = [seq / "qc_cont_one.yaml", seq / "qc_cont_two.yaml"]
    made[0].write_text(ONE, encoding="utf-8")
    made[1].write_text(TWO, encoding="utf-8")
    folder = main.SHOWS.folder
    try:
        # ---- the chain has no gap in it -------------------------------------
        show = {"name": "qc_cont", "loop": False,
                "items": [{"seq": "qc_cont_one.yaml"}, {"seq": "qc_cont_two.yaml"}]}
        steps = main.SHOWS.steps(main.SHOWS.clean(show), main.seq_steps)
        t.eq([int(x["pose"][0]) for x in steps], [20, 21, 21, 22],
             "the chain is sequence one then sequence two")
        t.ok(steps[2]["t"] <= 80,
             "the move into the second sequence takes the floor, not its authored 3000 ms",
             "it asked for %d ms to travel from a pose it is already standing "
             "on - that is the stop the operator saw between sequences"
             % steps[2]["t"])
        t.eq(steps[0]["t"], 3000,
             "the FIRST sequence keeps its own entry time (the robot really is elsewhere)")
        t.eq(sum(s.get("hold", 0) for s in steps), 0,
             "and nothing waits anywhere, because no pause was asked for")

        # ---- a pause the operator typed is still obeyed ----------------------
        paused = dict(show, items=[{"seq": "qc_cont_one.yaml", "hold": 700},
                                   {"seq": "qc_cont_two.yaml"}])
        psteps = main.SHOWS.steps(main.SHOWS.clean(paused), main.seq_steps)
        t.eq(psteps[1]["hold"], 700,
             "a pause number makes the robot stand still after that sequence")

        # ---- repeat: N times -------------------------------------------------
        times = dict(show, items=[{"seq": "qc_cont_one.yaml",
                                   "repeat_mode": "times", "repeat": 3}])
        tsteps = main.SHOWS.steps(main.SHOWS.clean(times), main.seq_steps)
        t.eq([int(x["pose"][0]) for x in tsteps], [20, 21, 20, 21, 20, 21],
             "repeat 3 times plays the sequence three times in a row")
        t.ok(tsteps[2]["t"] <= 80 and tsteps[4]["t"] <= 80,
             "each repeat hands over at the floor too, so a loop has no gap in it",
             [s["t"] for s in tsteps])

        # ---- repeat: for N seconds ------------------------------------------
        # One pass is 3000 + 200 = 3200 ms, so 10 s needs four passes: three
        # would be 9.6 s, still under target. Passes after the first are
        # 80 + 200 = 280 ms, which is what makes this worth asserting - the
        # count must come from the REAL times, not the authored ones.
        secs = dict(show, items=[{"seq": "qc_cont_one.yaml",
                                  "repeat_mode": "seconds", "repeat": 10}])
        ssteps = main.SHOWS.steps(main.SHOWS.clean(secs), main.seq_steps)
        total = sum(s["t"] + s.get("hold", 0) for s in ssteps)
        t.ok(len(ssteps) % 2 == 0 and total >= 10000,
             "repeat for 10 s plays whole passes until 10 s have gone by",
             "%d passes, %d ms" % (len(ssteps) // 2, total))
        t.ok(total - (ssteps[-2]["t"] + ssteps[-1]["t"]) < 10000,
             "and stops at the first pass that crosses the target, not later",
             "%d ms over %d passes" % (total, len(ssteps) // 2))

        # A sequence too short to fill the target refuses instead of building a
        # list of tens of thousands of steps that nothing can stop.
        try:
            main.SHOWS.steps(main.SHOWS.clean(
                dict(show, items=[{"seq": "qc_cont_one.yaml",
                                   "repeat_mode": "seconds", "repeat": 100000}])),
                main.seq_steps)
            t.ok(False, "an impossible seconds target is refused", "it was accepted")
        except ValueError as e:
            t.ok("too short" in str(e) and "qc_cont_one.yaml" in str(e),
                 "an impossible seconds target is refused, naming the sequence", str(e))

        # ---- half a setting is no setting ------------------------------------
        t.eq(main.SHOWS.clean({"items": [{"seq": "a.yaml", "repeat": 5}]})["items"][0],
             {"seq": "a.yaml", "hold": 0, "repeat_mode": "", "repeat": 0},
             "a repeat number with no mode plays once, rather than half-repeating")
        t.eq(main.SHOWS.clean({"items": [{"seq": "a.yaml", "repeat_mode": "times",
                                          "repeat": 1}]})["items"][0]["repeat_mode"], "",
             "repeat 1 time is the same as playing once")

        # ---- what actually reached the robot ---------------------------------
        s, b = F.post(base + "/api/show/play",
                      json.dumps({"dev": "usb:COM99", "show": show}).encode())
        t.eq(s, 200, "the hub starts the chained show")
        deadline = time.time() + 12
        time.sleep(0.3)
        while time.time() < deadline and main.show.status().get("running"):
            time.sleep(0.2)
        time.sleep(0.3)
        sent = [c for _, c in fake_serial.wire if c.upper().startswith("POSE ")]
        lead = [(int(float(c.split()[1])), int(c.split()[-1])) for c in sent]
        chain = [p for p in lead if p[0] in (20, 21, 22)]
        t.eq([p[0] for p in chain], [20, 21, 21, 22],
             "the robot got both sequences, in order")
        handover = next((tt for v, tt in chain[2:3]), None)
        t.ok(handover is not None and handover <= 80,
             "and the move between them went out at the floor, not 3000 ms",
             "the wire asked for %s ms" % handover)

        # ---- Studio gets the same list ---------------------------------------
        s, b = F.get(base + "/api/show/steps?name=qc_cont")
        t.eq(s, 404, "steps for a show that was never saved is a plain 404")
        main.SHOWS.save(show)
        s, b = F.get(base + "/api/show/steps?name=qc_cont")
        got = json.loads(b)
        t.eq([int(x["pose"][0]) for x in got["steps"]], [20, 21, 21, 22],
             "the hub hands Studio the same steps the robot ran")
        t.eq([m["seq"] for m in got["marks"]], ["qc_cont_one.yaml", "qc_cont_two.yaml"],
             "with a mark saying where each sequence starts")

        if not browser.available():
            t.give_up("headless Edge unavailable - the hub half above still ran")
        fake_serial.reset()
        browser.page(DRIVER, query=base + "/studio/_qcdriver.html", seconds=25)
        m = fake_serial.qc_marks
        t.contains(m, "done", "the Shows tab ran to the end")
        t.contains(m, "bar-keys-8",
                   "three passes of one sequence and one of the other land on the "
                   "time bar as eight keyframes")
        t.contains(m, "bar-named-4",
                   "each pass is marked where it begins, so a long show can be read")
        t.contains(m, "bar-handover-80",
                   "the hand-over keyframe on the bar shows the floor, the same as "
                   "the robot gets - the editor must not draw a run the robot will "
                   "not perform")
        t.contains(m, "bar-label-qc_cont_one ×2",
                   "and a repeated pass says which pass it is")
    finally:
        for p in made + [folder / "qc_cont.json"]:
            try:
                p.unlink()
            except OSError:
                pass
