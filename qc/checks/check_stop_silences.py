"""STOP means quiet as well as still.

A20-4 asked for this when the nong got a speaker: *the STOP that reaches every
board must silence it too*. Measured in the promoted tree on 2026-08-27, none
of the three STOP paths touched the speaker — the nong froze its pose, the lift
cut its motor, `MOVE STOP` ended the sequence, and the music kept playing over
a robot that had stopped moving. On a stage that reads as a machine that has
failed rather than one that was stopped on purpose.

STOP is the panic button, so all three now go through `Module::silence()`:

* it is a virtual on the base class, not an `audio_` reach-in, because
  `MOVE STOP` lives in core and core has no speaker to know about;
* the default does nothing, so a module type with no speaker (cam, blank)
  costs nothing and needs no branch;
* the nong forwards STOP to its partner board, so a linked pair goes quiet
  together.

`AudioPlayer::stop()` is public for exactly this. If it goes back to private,
this stops compiling rather than silently doing nothing — which is the reason
the assertion below names it.
"""
import qc as F

AREA = "firmware"
TITLE = "STOP silences the speaker, on every path that stops the show"


def run(t):
    fw = F.FIRMWARE

    base = (fw / "src/modules/Module.h").read_text(encoding="utf-8", errors="replace")
    t.contains(base, "virtual void silence()",
               "the base class carries silence(), so core can call it")

    player = (fw / "src/core/AudioPlayer.h").read_text(encoding="utf-8", errors="replace")
    pub = player.split("private:")[0]
    t.contains(pub, "void stop();",
               "AudioPlayer::stop() is public, so a module can call it")

    # every type that wires a speaker turns silence() into a real stop
    for name in ("nong", "lift"):
        hdr = (fw / ("src/modules/%s/%sModule.h" % (name, name))
               ).read_text(encoding="utf-8", errors="replace")
        t.contains(hdr, "void silence() override { audio_.stop(); }",
                   "%s's silence() really stops its player" % name)

        src = (fw / ("src/modules/%s/%sModule.cpp" % (name, name))
               ).read_text(encoding="utf-8", errors="replace")
        stop = src.split('cmd == "STOP"')
        t.ok(len(stop) > 1, "%s handles STOP" % name)
        if len(stop) > 1:
            # only the STOP branch, not the whole file: a silence() somewhere
            # else would not stop the show.
            body = stop[1][:400]
            t.contains(body, "silence()", "%s's STOP goes quiet as well as still" % name)

    router = (fw / "src/core/CommandRouter.cpp").read_text(encoding="utf-8", errors="replace")
    move = router.split('if (a == "STOP")')
    t.ok(len(move) > 1, "MOVE STOP is handled in core")
    if len(move) > 1:
        t.contains(move[1][:300], "module_->silence()",
                   "ending a show ends its sound with it")

    # a module type with no speaker must not be forced to grow one
    for name in ("cam",):
        hdr = (fw / ("src/modules/%s/%sModule.h" % (name, name.capitalize()))
               ).read_text(encoding="utf-8", errors="replace")
        t.ok("silence()" not in hdr,
             "%s does not override silence()" % name,
             "the base class default is the right answer for a board with no amp")

    docs = (fw / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.eq(docs.count("silences the speaker"), 2,
         "COMMANDS.md says so on both the lift's STOP and MOVE STOP")
    t.contains(docs, "silence the speaker", "and on the nong's STOP")
