"""Music on a move is CLICKABLE, not a line somebody types into the file.

A24-22 made a show's `play:` step survive load, playback and export. Nothing
could still ADD one: a designer had to open the YAML and type it, and the
project's rule is that anything settable is clickable - a value you edit in a
file is a bug on a screen made for designers, not a feature for experts.

So each keyframe carries a ♪, and pressing it opens a picker with the tracks
that are really on the robot's card (read from its /music folder) and a volume.
Driven in a real browser and asserted on the FILE and the WIRE, because a
picker that sets something the export and the robot never see is worse than
none:

  * the picker offers what the card actually holds, and nothing else;
  * choosing a track writes it into the show, so the exported file carries it;
  * the same choice reaches the module as PLAY when the hub runs the show;
  * choosing "no music" takes it off again, level and all.

The offline case is checked from the source, not the browser: the list cannot
be read with no robot, and what the file already says must still be shown and
still be exported - a show edited on a laptop with no robot on it must not
come back silent.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a move's music can be set by clicking, and it lands in the file"
SLOW = True

DRIVER = """
const wait = ms => new Promise(r => setTimeout(r, ms));
async function step(){
  try{
    while (!document.getElementById("liveChk") || !haveUsb()) await wait(200);
    document.getElementById("liveChk").checked = true;
    liveChanged();
    addKey(); addKey();                 // two keyframes: a show to export
    renderTimeline();
    const mus = document.querySelector(".key .kmus");
    if (!mus) { qcFail(new Error("no music button on a keyframe")); return; }
    mus.click();                        // opens the picker, reads /music
    await wait(1000);
    const sel = document.querySelector(".key .kmustrack");
    if (!sel) { qcFail(new Error("the picker did not open")); return; }
    qcMark("opts=" + Array.prototype.map.call(sel.options, o => o.value).join(","));
    sel.value = "song.mp3"; sel.onchange();
    const vol = document.querySelector(".key .kmusvol");
    vol.value = "65"; vol.onchange();
    qcMark(buildYaml(0).yaml.indexOf("- play: song.mp3") >= 0
           ? "yaml-has-track" : "yaml-missing-track");
    qcMark(buildYaml(0).yaml.indexOf("- vol: 65") >= 0
           ? "yaml-has-vol" : "yaml-missing-vol");

    // the hear-it button, between two markers so its PLAY cannot be mistaken
    // for the show's own cue later on
    await rawCmd("MOVE QCMARK HEAR");
    document.querySelector(".key .kmusbtn").click();
    await wait(500);
    await rawCmd("MOVE QCMARK HEARD");

    // adding a track from this PC. A file dialog cannot be opened by a script,
    // so the work it starts is called directly - the same code, no dialog.
    const f = new File([new Uint8Array([82,73,70,70,1,2,3,4])], "qc_added.wav",
                       {type: "audio/wav"});
    await uploadMusicFile(keys[0], f);
    qcMark((musicList || []).indexOf("qc_added.wav") >= 0
           ? "list-has-new-track" : "list-missed-new-track");
    qcMark(keyCue(keys[0], "play") === "qc_added.wav"
           ? "added-track-chosen" : "added-track-not-chosen");
    setKeyCue(keys[0], "play", "song.mp3");   // back to the track under test
    setKeyCue(keys[0], "vol", "65");
    renderTimeline();

    // and the show itself: the hub plays it, the cue reaches the module
    await rawCmd("MOVE QCMARK UI");
    togglePlay();
    await wait(2200);
    if (playing) togglePlay();
    const sel2 = document.querySelector(".key .kmustrack");
    sel2.value = ""; sel2.onchange();
    const y = buildYaml(0).yaml;
    qcMark(y.indexOf("play:") < 0 && y.indexOf("vol:") < 0
           ? "removed-clean" : "removal-left-something");
    qcMark("done");
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, _main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=16)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)

    opts = next((m[5:] for m in marks if m.startswith("opts=")), None)
    if t.ok(opts is not None, "the picker offered a list", marks):
        offered = [o for o in opts.split(",") if o]
        t.eq(sorted(offered), ["clap.wav", "song.mp3"],
             "it offers what is really in the robot's /music folder, and only that")

    t.contains(marks, "yaml-has-track", "the chosen track is written into the show")
    t.contains(marks, "yaml-has-vol", "and so is the level set beside it")
    t.contains(marks, "removed-clean",
               "choosing no music takes the track and its level back off")

    t.contains(marks, "list-has-new-track",
               "a track sent from the PC lands on the card and the picker "
               "offers it straight away, without a reload")
    t.contains(marks, "added-track-chosen",
               "and the move you added it from is set to it")

    wire = [c for _, c in fake_serial.wire]
    # ▶ must send its own PLAY, between the two markers - the show sends one
    # too, later, and an assertion that cannot tell them apart proves nothing.
    try:
        a = wire.index("MOVE QCMARK HEAR")
        b = wire.index("MOVE QCMARK UI")
        t.contains(wire[a + 1:b], "PLAY song.mp3",
                   "the hear-it button plays the track on the robot, without "
                   "running the show")
    except ValueError:
        t.ok(False, "both markers reached the module", wire[:8])

    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK UI")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    after = wire[i + 1:]
    t.contains(after, "PLAY song.mp3",
               "the track chosen by clicking reached the module")
    t.contains(after, "VOL 65", "at the level chosen beside it")

    # ---- offline: the list cannot be read, what is set is still kept ----
    js = (F.CODE / "nong/main_python_set_nong/web/app.js").read_text(
        encoding="utf-8", errors="replace")
    t.contains(js, "if (!liveLinked()) throw new Error",
               "no robot means no track list, rather than an empty one")
    fn = js[js.find("function musicRow("):]
    fn = fn[:fn.find("\nfunction ")]
    t.contains(fn, "names.indexOf(cur) < 0",
               "a track already in the file stays in the picker when the list "
               "cannot be read")
    t.ok(re.search(r"sel\.disabled\s*=\s*!musicList\s*&&\s*!cur", fn),
         "and the picker only locks when there is nothing to show at all",
         "locking it while a track IS set would hide the show's own music")
