"""Sequences: several on one card, suspending keyframes, and chaining files.

The suspend feature is the risky one. It has to be left OUT of everything that
runs — preview, live playback, export, upload and the crash check — while
staying IN the timeline so you can switch it back on. Anywhere that reads the
raw keyframe list instead of the play list is a silent bug: the editor shows
one thing and the robot does another.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "sequences"
TITLE = "suspend keyframes, chain files, many on one card"
SLOW = True

DRIVER = """
function step(){
  try{
    if (typeof playKeys !== "function") return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    qcMark("connected");

    // four keyframes with distinct first-joint values
    keys = [];
    [40, 70, 100, 130].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    keys.forEach(function(k,i){ if(i){ k.t = 600; } });
    document.getElementById("seqName").value = "qc_seq";
    qcMark("A-" + playKeys().map(function(k){ return Math.round(k.pose[0]); }).join("_"));
    qcMark("AT-" + totalMs());

    // suspend the middle one (index 2 = the 100 pose)
    keys[2].off = true;
    renderTimeline();
    qcMark("B-" + playKeys().map(function(k){ return Math.round(k.pose[0]); }).join("_"));
    qcMark("BT-" + totalMs());
    // the timeline still HOLDS it — suspend is not delete
    qcMark("BK-" + keys.length);

    // the exported file must not contain the suspended pose either
    var y = buildYaml().yaml;
    qcMark("BY-" + (y.indexOf("100 100 100") >= 0 ? "leaked" : "clean"));
    // ...and the move that replaced it must be timed at the SPEED that
    // applies, not at the servos' physical floor. Those are very different
    // numbers: the floor is the fastest the arm can possibly move, so timing
    // the replacement move by it turns a suspend into a full-speed lunge.
    // The stored time must be TOO SHORT for the new jump, or max() rightly
    // keeps it and the test proves nothing — that short stored time is exactly
    // the case that lunged.
    var keep3 = keys[3].t;
    keys[3].t = 200;
    var floor = minTime(keys[1].pose, keys[3].pose);
    var want = autoTime(keys[1].pose, keys[3].pose, speedDps());
    var got = playKeys()[2].t;
    qcMark("BM-" + (got === want ? "at-speed" : (got <= floor ? "at-floor" : got + "vs" + want)));
    keys[3].t = keep3;

    // THE SHRINKING CASE. Suspend the middle of  home -> somewhere -> home
    // and what is left is home -> home: the arm has nowhere to go, so the move
    // must take the minimum. Re-timing used to max() with the stored time, so
    // it kept the 400 ms written for "go somewhere" and the arm sat still for
    // 400 ms doing nothing. Re-timing has to SHORTEN a move as well as
    // lengthen one.
    keys = [];
    [90, 30, 90].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    keys[1].t = 400; keys[2].t = 400;
    keys[1].off = true;                       // suspend "somewhere"
    var pk = playKeys();
    qcMark("SC-" + pk.length + "-" + Math.round(pk[1].t)
           + "-" + Math.round(autoTime(pk[0].pose, pk[1].pose, speedDps())));

    // put the four-keyframe state back: everything below this point was
    // written against it, and a check that quietly changes the fixture for
    // the checks after it is its own bug.
    keys = [];
    [40, 70, 100, 130].forEach(function(v){
      pose = pose.map(function(){ return v; });
      addKey();
    });
    keys.forEach(function(k,i){ if(i){ k.t = 600; } });
    keys[2].off = true;
    renderTimeline();
    qcMark("BF-" + (want > floor ? "differ" : "same"));   // the test must be able to tell

    // a per-move speed on the SURVIVING keyframe governs the replacement move
    keys[3].dps = 25;
    var slow = playKeys()[2].t;
    qcMark("BD-" + (slow === autoTime(keys[1].pose, keys[3].pose, 25) ? "own-speed" : slow));
    delete keys[3].dps;
    keys[3].t = keep3;

    // put it back BEFORE anything that reloads the timeline (loading a
    // sequence legitimately replaces `keys`, so this has to be checked first)
    keys[2].off = false;
    renderTimeline();
    qcMark("D-" + playKeys().length);

    // chaining
    document.getElementById("seqNext").value = "wave";
    var y2 = buildYaml().yaml;
    qcMark("C-" + (/^next: wave\\.yaml$/m.test(y2) ? "ok" : "missing"));

    // this sequence's OWN speed: written as the first step, so a chain sets it
    // again at every hand-over instead of inheriting the previous file's
    document.getElementById("speedDps").value = "155";
    speedChanged();
    var y3 = buildYaml().yaml;
    var sIdx = y3.indexOf("- speed:"), pIdx = y3.indexOf("- pose:");
    qcMark("S-" + (/- speed: 155/.test(y3) ? "written" : "missing"));
    qcMark("SO-" + (sIdx >= 0 && sIdx < pIdx ? "first" : "late"));
    // and it comes back when the file is re-edited
    document.getElementById("speedDps").value = "60";
    loadParsedSeq(parseSeqYaml(y3), "qc");
    qcMark("SR-" + Math.round(speedDps()));
    // re-editing must NOT count the speed step as an unsupported one
    qcMark("SS-" + parseSeqYaml(y3).skipped);

    // ---- ONE MOVE slower than the rest of the sequence ----------------
    keys.forEach(function(k){ delete k.dps; });
    document.getElementById("speedDps").value = "120";
    speedChanged();
    var fast = keys[2].t;
    keys[2].dps = 30;                       // a quarter of the show speed
    keys[2].t = autoTime(keys[1].pose, keys[2].pose, 30);
    qcMark("M-" + (keys[2].t > fast ? "slower" : keys[2].t + "vs" + fast));
    // its neighbours must be untouched
    qcMark("MN-" + (keys[1].t === autoTime(keys[0].pose, keys[1].pose, 120) ? "ok" : "changed"));

    // the file must set that speed before the move and put it back after
    var y4 = buildYaml().yaml;
    var seq4 = y4.split("\\n").filter(function(l){ return /- (speed|pose):/.test(l); })
                 .map(function(l){ return /- speed: (\\d+)/.test(l)
                    ? "s" + l.match(/- speed: (\\d+)/)[1] : "p"; }).join(",");
    qcMark("MY-" + seq4);

    // and a full round trip keeps it on the same move
    var back = parseSeqYaml(y4);
    qcMark("MR-" + back.keys.map(function(k){ return k.dps ? Math.round(k.dps) : "-"; }).join("_"));
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    # ---- firmware side: chaining is real, and cannot run away ----------
    src = (F.FIRMWARE / "src/core/SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    hdr = (F.FIRMWARE / "src/core/SequencePlayer.h").read_text(
        encoding="utf-8", errors="replace")
    t.contains(src, '"next"', "the player reads a next: file")
    t.contains(hdr, "MAX_CHAIN", "chain depth is bounded")
    t.ok(re.search(r"loopSeq_\s*\)\s*\{", src),
         "loop is handled before next (a looping file never ends)")
    cmds = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(cmds, "next:", "COMMANDS.md documents chaining")

    # ---- several sequences live on one card, each runnable --------------
    fake_serial.reset()
    base, main = F.start_hub()
    for name in ("intro.yaml", "wave.yaml", "bow.yaml"):
        s, b = F.cmd(base, "FBEGIN /moves/" + name)
        t.eq(s, 200, "the card accepts %s" % name)
    s, listing = F.cmd(base, "FILES /moves")
    t.contains(listing, "wave", "the card lists what is on it")
    s, b = F.cmd(base, "MOVE wave.yaml")
    t.contains(b, "OK", "any one of them can be picked and run")

    # ---- the editor side, in a real browser ---------------------------
    if not browser.available():
        t.give_up("headless Edge not found — the suspend checks need a browser")
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=20)
    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks), "the editor ran clean", marks)
    got = {m.split("-", 1)[0]: m.split("-", 1)[1] for m in marks if "-" in m}

    t.eq(got.get("A"), "40_70_100_130", "all four keyframes play by default")
    t.eq(got.get("B"), "40_70_130", "a suspended keyframe is left out of the run")
    t.eq(got.get("BK"), "4", "but it stays in the timeline — suspend is not delete")
    t.ok(got.get("BT") and got.get("AT") and int(got["BT"]) < int(got["AT"]),
         "the run gets shorter when a keyframe is suspended",
         "total was %s, now %s" % (got.get("AT"), got.get("BT")))
    t.eq(got.get("BY"), "clean", "the exported file does not contain the suspended pose")
    t.eq(got.get("BF"), "differ",
         "the test can tell speed-timing from floor-timing (else it proves nothing)")
    t.eq(got.get("BM"), "at-speed",
         "the replacement move is timed at the show speed, NOT at the servos' "
         "physical floor (which would make suspending a keyframe lunge)")
    # THE SHRINKING CASE: home -> somewhere -> home with the middle suspended
    # leaves home -> home. The arm has nowhere to go, so the move must take the
    # minimum. Re-timing used to max() with the stored time and kept the 400 ms
    # that belonged to "go somewhere", so the arm sat still for 400 ms.
    sc = (got.get("SC") or "").split("-")
    if t.ok(len(sc) == 3, "the shrinking case reported", got.get("SC")):
        t.eq(sc[0], "2", "only two keyframes are left to play")
        t.eq(sc[1], sc[2],
             "and the remaining move is re-timed for the poses it ACTUALLY "
             "runs between (%s ms), not left at the suspended move's time" % sc[2])
        t.ok(int(sc[1]) < 400,
             "which is shorter than the 400 ms it replaced (%s ms)" % sc[1],
             "re-timing can only lengthen a move — the arm waits, going nowhere")

    t.eq(got.get("BD"), "own-speed",
         "a per-move speed on the surviving keyframe governs the replacement move")
    t.eq(got.get("C"), "ok", "a chained 'then run' file is written as next:")

    t.eq(got.get("S"), "written", "the sequence carries its own speed")
    t.eq(got.get("SO"), "first",
         "the speed step comes before the first pose, so it applies to the whole file")
    t.eq(got.get("SR"), "155", "re-editing a sequence restores ITS speed, not the editor's")
    t.eq(got.get("SS"), "0",
         "the speed step is understood, not reported as an unsupported step")

    # the firmware really applies it — this is what makes a chain deterministic
    t.contains((F.FIRMWARE / "src/core/SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace"),
        'key == "speed"', "the player applies a speed step")
    t.contains((F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace"),
               "Speed per sequence", "COMMANDS.md documents per-sequence speed")

    # ---- per-move speed -------------------------------------------------
    t.eq(got.get("M"), "slower", "a per-move speed re-times just that move")
    t.eq(got.get("MN"), "ok", "and leaves its neighbours alone")
    # speed, pose, pose, speed(30), pose, speed(back), pose
    t.eq(got.get("MY"), "s120,p,p,s30,p,s120,p",
         "the file sets that speed before the move and restores it after")
    t.eq(got.get("MR"), "-_-_30_-",
         "a round trip through the file keeps the override on the same move")

    t.eq(got.get("D"), "4", "un-suspending puts it straight back in the run")
