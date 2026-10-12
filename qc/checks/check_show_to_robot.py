"""A show can go ONTO the robot, and the file runs what the hub's Run runs.

User 2026-10-12 (A40-2): *in shows is there upload to the robot? now only run
and save to the PC*. ▶ Run on robot made the HUB the clock, so the show stopped
when the PC did. ⇪ Send to robot writes the show as one sequence file on the
robot's card (shows.robot_yaml) and the board plays it alone.

Three things, so none rots back:

* the file is the SAME run: parsed back with the hub's own parser it gives the
  very poses, move times and pauses /api/show/steps gives - a second rule for
  the file would drift until the robot played a show the editor never drew;
* the show's music stops where the hub's timer would stop it - inside a pause
  the wait is split, after the show a wait is added - because a file has no
  timer of its own;
* the Shows tab really SENDS it: asserted on the FBEGIN/FDATA bytes that
  reached the module, not on what the status line says.
"""
import base64
import json

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a show can be sent to the robot and plays the same run"
SLOW = True

SEQ_A = ("name: qc_trip_a\nloop: false\nsteps:\n"
         "  - speed: 120\n"
         '  - pose: "31 90 90 90 90 90 90 90 90 90 T 700"\n'
         '  - pose: "32.5 90 90 90 90 90 90 90 90 90 T 400"\n'
         "  - wait: 900\n")
SEQ_B = ("name: qc_trip_b\nloop: false\nsteps:\n"
         "  - speed: 120\n"
         '  - pose: "41 90 90 90 90 90 90 90 90 90 T 300"\n'
         '  - pose: "42 90 90 90 90 90 90 90 90 90 T 300"\n')
SHOW = {"name": "qc trip", "loop": False,
        "items": [{"seq": "qc_trip_a.yaml", "hold": 500},
                  {"seq": "qc_trip_b.yaml", "repeat_mode": "times", "repeat": 2}]}

DRIVER = """
function step(){
  try{
    if (typeof sendShowToRobot !== "function" || !document.getElementById("showName"))
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");
    newShow();
    showDraft.items = %s;
    renderShow();
    document.getElementById("showName").value = "qc trip";
    sendShowToRobot().then(function(){
      qcMark("stat-" + document.getElementById("showStat").textContent.slice(0, 40));
      setTimeout(function(){ qcMark("done"); }, 300);
    }).catch(function(e){ qcFail(e); });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % json.dumps(SHOW["items"])


def uploads():
    """Every file the module was sent, as (name, text), in wire order."""
    out, name, buf = [], None, ""
    for _ms, c in fake_serial.wire:
        head = c.split(" ", 1)[0].upper()
        if head == "FBEGIN":
            if name is not None:
                out.append((name, buf))
            name, buf = (c.split(" ", 1)[1].strip() if " " in c else "?"), ""
        elif head == "FDATA" and name is not None:
            try:
                buf += base64.b64decode(c.split(" ", 1)[1]).decode(errors="replace")
            except Exception:                       # noqa: BLE001
                pass
    if name is not None:
        out.append((name, buf))
    return out


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    seq = main.SEQUENCES
    seq.mkdir(exist_ok=True)
    made = [seq / "qc_trip_a.yaml", seq / "qc_trip_b.yaml"]
    made[0].write_bytes(SEQ_A.encode())
    made[1].write_bytes(SEQ_B.encode())
    try:
        # ---- 1. the file is the same run as the hub's ------------------------
        s, b = F.post(base + "/api/show/steps", json.dumps({"show": SHOW}).encode())
        want = json.loads(b).get("steps") or []
        s, b = F.post(base + "/api/show/yaml", json.dumps({"show": SHOW}).encode())
        j = json.loads(b or "{}")
        if not t.ok(s == 200 and j.get("ok"), "the hub writes the show as a file", b[:300]):
            return
        t.eq(j["file"], "qc_trip.show.yaml", "named after the show, marked as a show")
        got = main.seq_steps(j["yaml"])["steps"]
        t.eq([(st["pose"], st["t"], st["hold"]) for st in got],
             [([float(v) for v in st["pose"]], st["t"], st["hold"]) for st in want],
             "parsed back, the file is every pose, move time and pause of the hub's run")

        # ---- 2. the show's music stops where the hub's timer would -----------
        music = dict(SHOW, music="song.mp3", music_end="total", music_secs=1.5)
        _, b = F.post(base + "/api/show/yaml", json.dumps({"show": music}).encode())
        lines = [ln.strip() for ln in json.loads(b)["yaml"].splitlines()]
        # clock 0 = the first pose; the 400 ms move ends at 400, then ONE wait
        # of 1400 (the file's 900 + the item's 500 pause). 1500 falls 1100 in.
        at = lines.index("- play: STOP") if "- play: STOP" in lines else -1
        t.ok(at > 0 and lines[at - 1] == "- wait: 1100" and lines[at + 1] == "- wait: 300",
             "a stop inside a pause splits the wait at the right ms", lines)
        t.ok(lines.count("- play: STOP") == 1, "and it is said once", lines)
        # The song starts when the arm STANDS on the first pose, as ShowPlayer
        # starts it - not before the walk there. Written first, it ran 3.3 s
        # ahead of every move on nong 67 (user 2026-10-12).
        poses = [i for i, ln in enumerate(lines) if ln.startswith("- pose:")]
        play = lines.index("- play: song.mp3") if "- play: song.mp3" in lines else -1
        t.ok(poses and poses[0] < play < poses[1],
             "the song starts after the walk onto the first pose, before the next move",
             lines[:12])
        after = dict(SHOW, music="song.mp3", music_end="after", music_secs=2)
        _, b = F.post(base + "/api/show/yaml", json.dumps({"show": after}).encode())
        tail = [ln.strip() for ln in json.loads(b)["yaml"].splitlines()][-2:]
        t.eq(tail, ["- wait: 2000", "- play: STOP"],
             "music that outlives the show: the file waits, then stops it")

        # ---- 3. the Shows tab sends it to the robot ---------------------------
        if not browser.available():
            t.give_up("headless Edge not found — install Edge or run --quick")
        fake_serial.reset()
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=20)
        marks = fake_serial.qc_marks
        t.ok(not any(m.startswith("ERROR") for m in marks),
             "the page ran without throwing", marks)
        t.contains(marks, "connected", "Studio connected over USB")
        files = uploads()
        sent = [x for n, x in files if n.endswith("qc_trip.show.yaml")]
        t.ok(bool(sent), "the module received the show file", [n for n, _ in files])
        if sent:
            back = main.seq_steps(sent[-1])["steps"]
            t.eq([st["pose"] for st in back],
                 [[float(v) for v in st["pose"]] for st in want],
                 "what reached the module is the hub's run, pose for pose")
            # Studio passes the board's speed limits (showLimits), so a join
            # may be LONGER than the limit-free run above (80 -> 223 ms on the
            # QC rig) - the same times ▶ Run asks for. Never shorter.
            t.ok(len(back) == len(want) and all(
                     a["t"] >= w["t"] for a, w in zip(back, want)),
                 "and no move is faster than the hub's run",
                 [(a["t"], w["t"]) for a, w in zip(back, want)])
    finally:
        for f in made:
            f.unlink(missing_ok=True)
