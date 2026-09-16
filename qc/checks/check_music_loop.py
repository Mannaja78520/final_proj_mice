"""A move's music can be told to repeat, and the repeat lives in the FILE.

Asked 2026-09-10: *make can loop the music of that sequence when select that
sequence to run*. Chosen shape: a `repeat` tickbox on the move's music row
writes `play: song.mp3 LOOP` into the sequence, so the repeat holds however the
show is started — the hub, the module's own page, or Run on robot — because none
of them do anything but hand the file to the player.

Three separate traps, one assertion each:

* **The greedy join.** `AudioPlayer::playCmd` ends with
  `Util::joinFrom(argv, argc, 1)`, which swallows EVERY remaining token, because
  a track name may contain spaces. Left alone, `PLAY song.mp3 LOOP` asks for the
  file `/music/song.mp3 LOOP` and simply fails. So LOOP has to come off the END
  before the join — and a name with a space in it must still survive.
* **The path is gone by the time the track ends.** `cleanup()` deletes the
  generator and clears `current_`, so a lap cannot be started from it. The path
  is remembered separately in `loopPath_`.
* **The lock.** `AudioPlayer::loop()` deliberately only `tryLock`s: it runs with
  the router mutex held, and blocking there would stall motion behind a web
  upload. So the lap must restart via `openTrack_()` INSIDE the lock it already
  holds — never by calling `play()`, which reaches a blocking `sd_->lock()`.
  SDStore's mutex is recursive, which is what makes that safe.

And one behaviour worth pinning: a show that reaches its own end silences a
REPEATING track but leaves a one-shot to finish. That asymmetry is deliberate —
a long track outliving a short show is a feature — so `stop()` must NOT be the
place the silencing happens.

The wire is the witness for the parsing: `fake_serial.NONG.audio_file` is set by
the fake's own splitting of the line, so it proves the module side did it, not
the page.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "a move's music can repeat, and the repeat is in the file"
SLOW = True

TRACK = "wave.mp3"
SPACED = "/music/two words.mp3"

DRIVER = """
function step(){
  try{
    if (typeof addKey !== "function" || typeof cueLoop !== "function")
      return setTimeout(step, 200);
    if (!haveUsb()) return setTimeout(step, 300);

    keys = [];
    pose = pose.map(function(){ return 60; });  addKey();
    pose = pose.map(function(){ return 120; }); addKey();
    $("seqName").value = "looptest";

    // ---- A: a track with repeat ticked reaches the YAML as one cue line
    setCueTrack(keys[1], "%s", true);
    qcMark("A=" + (buildYaml(0).yaml.indexOf("- play: %s LOOP") >= 0));
    qcMark("Aloop=" + cueLoop(keys[1]));
    qcMark("Atrack=" + cueTrack(keys[1]));

    // ---- B: it survives a round trip through the file and back
    var text = buildYaml(0).yaml;
    var back = parseSeqYaml(text);
    var k = back.keys[1] || {};
    qcMark("Bloop=" + /\\sLOOP$/i.test((k.cues || []).join("|")));
    qcMark("Btrack=" + JSON.stringify((k.cues || [])));

    // ---- C: untick, and the LOOP is gone but the track stays
    setCueTrack(keys[1], "%s", false);
    qcMark("C=" + (buildYaml(0).yaml.indexOf("- play: %s LOOP") >= 0));
    qcMark("Ctrack=" + cueTrack(keys[1]));

    // ---- D: changing the TRACK keeps the repeat — driven through the REAL
    // dropdown, not the helper behind it. Calling setCueTrack() directly passed
    // while the select's own handler threw the repeat away, which is the bug.
    musicList = ["%s", "other.mp3"];
    setCueTrack(keys[1], "%s", true);
    musOpen.add(1);
    renderTimeline();
    var row = document.querySelectorAll("#keys .key")[1];
    var pick = row ? row.querySelector("select.kmustrack") : null;
    var box = row ? row.querySelector(".kmusloop input") : null;
    qcMark("Dfound=" + (!!pick) + "," + (!!box));
    qcMark("Dchecked=" + (box ? box.checked : "none"));
    if (pick) {
      pick.value = "other.mp3";
      pick.onchange();                       // exactly what a click does
    }
    qcMark("Dloop=" + cueLoop(keys[1]));
    qcMark("Dtrack=" + cueTrack(keys[1]));

    // ---- E: what the MODULE is told, including a name with a space in it
    rawCmd("PLAY %s LOOP").then(function(r){
      qcMark("Ereply=" + String(r).replace(/[^A-Za-z0-9 ./_-]/g, ""));
      qcMark("done");
    });
  }catch(e){ qcFail(e); }
}
window.addEventListener("load", function(){ setTimeout(step, 1200); });
""" % (TRACK, TRACK, TRACK, TRACK, TRACK, TRACK, SPACED)


def _mark(marks, tag):
    for m in marks:
        if m.startswith(tag + "="):
            return m[len(tag) + 1:]
    return None


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")

    # ---- the firmware side, read from source ----------------------------
    src = (F.FIRMWARE / "src" / "core" / "AudioPlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    hdr = (F.FIRMWARE / "src" / "core" / "AudioPlayer.h").read_text(
        encoding="utf-8", errors="replace")

    # LOOP comes off before the join, or the flag becomes part of the path
    m = re.search(r"Util::joinFrom\(argv,\s*(\w+),\s*1\)", src)
    if t.ok(m, "playCmd still joins the remaining tokens into a path"):
        t.ok(m.group(1) != "argc",
             "and it joins up to a trimmed end, not argc",
             "joining to argc puts LOOP inside the file name, so the file is "
             "never found — the whole bug this guards")
    t.ok(re.search(r'last\s*==\s*"LOOP"', src),
         "a trailing LOOP is recognised", src[:0])
    t.ok("argc > 2" in src,
         "and a file actually NAMED loop still plays",
         "argc >= 2 would treat `PLAY LOOP` as a flag with no file")

    # the path is remembered where cleanup() cannot clear it
    t.ok("loopPath_" in hdr and "loopPath_" in src,
         "the repeat remembers its own path",
         "current_ is cleared by cleanup() before anyone knows the track ended")

    # openTrack_ calls cleanup() with gen_ still null, so cleanup must free what
    # HAS been allocated rather than bailing out on the generator alone. Found by
    # the model panel 2026-09-10: a file that would not open leaked its source
    # object and left the SD handle open, once per failed PLAY.
    cl = src[src.index("void AudioPlayer::cleanup()"):]
    cl = cl[:cl.index("\n}") + 2]
    t.ok("!gen_ && !id3_ && !file_" in cl.replace("  ", " "),
         "cleanup() frees a half-built track, not only a running one",
         "`if (!gen_) return;` leaks file_ on every failed open")

    # the lap restarts under the lock loop() already holds
    lp = src[src.index("void AudioPlayer::loop()"):]
    lp = lp[:lp.index("void AudioPlayer::stop()")]
    # Comments stripped: the comment on this very line names play() as the thing
    # NOT to do, and a plain substring test read that as the code doing it.
    lp = re.sub(r"//[^\n]*", "", lp)
    t.ok("openTrack_" in lp,
         "a lap restarts through openTrack_, which takes no new lock")
    t.ok("play(" not in lp,
         "and never by calling play(), which would block on the SD lock",
         "loop() only try-locks on purpose: it runs with the router mutex held, "
         "so blocking there stalls motion behind a web upload")
    t.ok("if (loopOn_)" in lp, "the lap only happens when repeat was asked for")
    t.ok(re.search(r"loopOn_\s*=\s*false", lp),
         "and one failed reopen ends it, instead of retrying every tick")

    # STOP means stop
    sp = src[src.index("void AudioPlayer::stop()"):]
    sp = sp[:sp.index("void AudioPlayer::cleanup()")]
    t.ok(re.search(r"loopOn_\s*=\s*false", sp),
         "STOP clears the repeat",
         "otherwise PLAY STOP silences this lap and the next one starts anyway")

    # ---- who silences a track that repeats ------------------------------
    seq = (F.FIRMWARE / "src" / "core" / "SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    body = seq[seq.index("void SequencePlayer::stop()"):]
    body = body[:body.index("void SequencePlayer::endOfShow()")]
    t.ok("silenceLoop" not in body,
         "stop() itself does NOT silence audio",
         "stop() is also the failure and unload path; a long one-shot outliving "
         "a short show is deliberate")
    t.ok("silenceLoop" in seq,
         "but the show's own end does",
         "a repeating track with nothing left to stop it plays forever")
    t.ok(seq.count("endOfShow()") >= 3,
         "and both natural-end paths go through it",
         "one of the two ends still calls stop() directly")

    # ---- the page and the wire ------------------------------------------
    fake_serial.reset()
    base, main = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s"
                 % (base, fake_serial.PORT), seconds=24)

    marks = fake_serial.qc_marks
    t.ok(not any(m.startswith("ERROR") for m in marks),
         "the page ran without throwing", marks)

    t.eq(_mark(marks, "A"), "true",
         "ticking repeat writes `play: %s LOOP` into the sequence" % TRACK)
    t.eq(_mark(marks, "Aloop"), "true", "and the page reads it back as repeating")
    t.eq(_mark(marks, "Atrack"), TRACK,
         "while the track name itself stays clean of the flag")

    t.eq(_mark(marks, "Bloop"), "true",
         "the repeat survives export and re-import")
    t.eq(_mark(marks, "C"), "false", "unticking removes the LOOP")
    t.eq(_mark(marks, "Ctrack"), TRACK, "and leaves the track")

    t.eq(_mark(marks, "Dfound"), "true,true",
         "the music row really shows a track picker and a repeat tickbox")
    t.eq(_mark(marks, "Dchecked"), "true",
         "the tickbox shows the repeat that is set, rather than starting blank")
    t.eq(_mark(marks, "Dloop"), "true",
         "picking a different song in the dropdown KEEPS the repeat")
    t.eq(_mark(marks, "Dtrack"), "other.mp3", "and really changes the track")

    # ---- the module split it, not the page ------------------------------
    wire = [c for _, c in fake_serial.wire]
    sent = [c for c in wire if c.upper().startswith("PLAY ")]
    t.ok(any(c.endswith("LOOP") for c in sent),
         "the LOOP reached the module as part of the command", sent[-3:])
    t.eq(fake_serial.NONG.audio_file, SPACED,
         "the module took LOOP off the end and kept the spaces in the name")
    t.ok(fake_serial.NONG.audio_loop,
         "and recorded that this track repeats",
         "the flag was parsed away without being acted on")
    t.contains(_mark(marks, "Ereply") or "", "looping",
         "the reply says it is looping, not merely playing")
