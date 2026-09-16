"""Music survives the trip THROUGH the editor, not only through the hub.

check_show_music proves the hub plays a saved show's cues. Studio does not
hand the hub that file: it parses the yaml itself (parseSeqYaml), edits
keyframes, and posts its own steps to /api/play. So a show loaded into the
editor and played from there was still silent after the hub could play music
- the cues were counted as `skipped` and thrown away at load.

Driven in a real browser, asserted on the WIRE, because the whole point is
what reaches the module: load a saved sequence with a `play:` step in it,
press Play with the hub as the clock, and the track must go out with the
first move. The export half is checked here too - a file edited in Studio
and written back must still carry its music, or editing a show is how you
lose it.
"""
import os

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a show edited in Studio keeps its music"
SLOW = True

SEED = ("name: qcmus\nloop: false\nsteps:\n"
        "  - speed: 60\n"
        "  - vol: 70\n"
        "  - play: qc_song.mp3\n"
        "  - pose: \"40 40 140 140 40 40 140 140 90 90 T 900\"\n"
        "  - wait: 150\n"
        "  - pose: \"130 130 60 60 130 130 60 60 90 90 T 1100\"\n")

DRIVER = """
function step(){
  try{
    if (!document.getElementById("liveChk")) return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);
    document.getElementById("loopChk").checked = false;
    document.getElementById("liveChk").checked = true;
    liveChanged();
    var sel = document.getElementById("seqList");
    var opt = Array.prototype.find.call(sel.options, function(o){
      return o.value === "qc_music.yaml"; });
    if (!opt) { qcFail(new Error("seeded sequence not offered in the list")); return; }
    sel.value = "qc_music.yaml";
    editLocalSeq().then(function(){
      // the export half: the file Studio would write back must still say it
      var y = buildYaml(0).yaml;
      qcMark(y.indexOf("- play: qc_song.mp3") >= 0 ? "export-keeps-music"
                                                   : "export-lost-music");
      rawCmd("MOVE QCMARK MU");
      setTimeout(function(){
        togglePlay();                       // the hub is the clock: hubPlay()
        setTimeout(function(){
          qcMark("done");
          if (playing) togglePlay();
        }, 2500);
      }, 900);
    }).catch(qcFail);
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found - install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    seq_dir = main.SEQUENCES
    seq_dir.mkdir(exist_ok=True)
    seed = seq_dir / "qc_music.yaml"
    seed.write_text(SEED, encoding="utf-8", newline="\n")
    try:
        browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                     % (base, fake_serial.PORT), seconds=14)
    finally:
        os.remove(seed)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)
    t.contains(marks, "export-keeps-music",
               "a show edited in Studio still carries its music when written back")

    wire = [c for _, c in fake_serial.wire]
    try:
        i = len(wire) - 1 - wire[::-1].index("MOVE QCMARK MU")
    except ValueError:
        t.ok(False, "the marker reached the module", wire[-4:])
        return
    after = wire[i + 1:]
    poses = [j for j, c in enumerate(after) if c.upper().startswith("POSE ")]
    if not t.ok(poses, "playing from the editor drove the module", after[:6]):
        return
    played = [j for j, c in enumerate(after) if c == "PLAY qc_song.mp3"]
    t.ok(played, "the track the file names reached the module", after[:6])
    t.contains(after, "VOL 70", "and so did the volume it asked for")
    if played:
        t.ok(played[0] < poses[0],
             "the music started with the show, not after its first move",
             after[:6])
