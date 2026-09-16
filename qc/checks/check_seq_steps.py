"""A sequence step key is DATA, not a branch in the player (A7-5).

SequencePlayer::execStep carried an if-else chain that named both module
types' verbs — goto/home/up/down for the lift, pose/joint/relax/attach for the
nong. Adding a step meant editing shared C++ that had to know about every
module type, which is the thing this project keeps removing: a module type, a
servo, a command and a web app are each ONE entry in a registry.

So a step is declared on the command it calls, in config/commands.json, and
tools/gen_tables.py writes core/SeqSteps.h. The test that matters is the
project's own: can someone add the next one without opening this file?

THREE THINGS THIS EXISTS TO CATCH
---------------------------------
1. A step key that reaches the player but no longer sends anything. The keys
   used to be greppable in the C++; now they are not, and check_contracts was
   scraping exactly that (`key == "..."`), so the day they moved it would have
   reported every step Studio writes as understood while none of them were.
2. `wait` derived from `motion`. It cannot be: STOP and RELAX are both motion
   and neither may wait — STOP has nothing to finish and RELAX unpowers the
   servos, so `busy` never clears and the sequence stops dead on that step.
3. One key meaning two things. `home`, `stop` and `speed` are declared for
   BOTH lift and nong, and a build carrying both sees each twice. The
   generator collapses identical declarations and refuses a real conflict
   rather than silently taking whichever came first in the file.
"""
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "contracts"
TITLE = "a sequence step key is one registry entry, not a branch in the player"
SLOW = False

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402

GEN = F.FIRMWARE / "tools" / "gen_tables.py"
HEADER = F.FIRMWARE / "generated" / "core" / "SeqSteps.h"
PLAYER = F.FIRMWARE / "src" / "core" / "SequencePlayer.cpp"


def _table(text):
    """key -> (command, waits) as the generated header declares it."""
    out = {}
    for key, cmd, wait in re.findall(
            r'\{\s*"(\w+)",\s*"([^"]*)",\s*(true|false)\s*\}', text):
        out[key] = (cmd, wait == "true")
    return out


def run(t):
    head = HEADER.read_text(encoding="utf-8", errors="replace")
    player = PLAYER.read_text(encoding="utf-8", errors="replace")
    table = _table(head)

    # ---- the player reads the table, and names no module's verbs ------
    t.contains(player, "findSeqStep", "the player looks its steps up in the table")
    # ...and USES the wait flag it finds there. Reading the table but ignoring
    # this field leaves every assertion below true while no step ever waits,
    # so the next step lands mid-move and two commands fight over the same
    # servos. Caught by sabotage 2026-08-21, which is the only reason this
    # line exists — the rest of the check passed happily without it.
    t.contains(player, "s->wait", "and waits when the table says to")
    # A YAML boolean is a MARKER, not an argument. COMMANDS.md teaches
    # "- home: 1" and "- stop: 1" because YAML needs a value there, and
    # flattening one into the command sent "HOME true". The handlers ignore a
    # stray token (nong HOME only reads T when argc>=3; the lift verbs
    # dispatch on the command alone), so "- home: 1" is harmless either way —
    # but "true" appearing in a command line is not something to ship.
    t.contains(player, "v.is<bool>()",
               "and a bare yes/no marker is not passed on as an argument")
    # The two that are NOT commands stay in code, deliberately, and are the
    # only keys allowed to appear there.
    in_code = set(re.findall(r'key == "(\w+)"', player))
    t.eq(sorted(in_code), ["cmd", "wait"],
         "and the only keys still written in C++ are the two that are not commands")
    # A negative wait: used to wrap to ~49 days and stall the show forever.
    # t.contains takes no detail - the why lives in this comment.
    t.contains(player, "if (w < 0) w = 0;",
               "a negative wait clamps to zero instead of wrapping huge")
    # Unknown keys stay skippable (files from another module type must play
    # what they can) but never SILENTLY - a typo'd step vanished once.
    t.ok("is not known to this board" in player,
         "an unknown step key leaves one line in the log")

    # ---- MOVE from RAM names its show; long lines refuse ---------------
    cmd_src = (F.FIRMWARE / "src" / "core" / "CommandRouter.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.ok(re.search(r"bool match\s*=\s*held", cmd_src)
         and "in memory, not " in cmd_src,
         "with no card, MOVE only plays the show it actually holds",
         "it used to play whatever was uploaded last under ANY name asked "
         "for - showB.yaml silently ran showA. The refusal must be built "
         "from textName(), not waved through")
    util = (F.FIRMWARE / "src" / "core" / "Util.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.ok("-(argc + 1)" in util and "too many words" in cmd_src,
         "a line longer than 16 words is refused, never run truncated",
         "the dropped tail used to vanish and the shortened command still "
         "executed")

    # ---- every declared step really reached the table -----------------
    declared = {st["key"]: c for c in registry.commands()
                for st in (c.get("steps") or [])}
    missing = sorted(set(declared) - set(table))
    t.ok(not missing, "every step declared in commands.json is in the table",
         "declared and not generated: %r — the player would ignore it "
         "silently, which is how a step does nothing and says nothing"
         % (missing,))

    # ---- and nothing in the table was invented -------------------------
    t.ok(not sorted(set(table) - set(declared)),
         "and nothing is in the table that no command declared")

    # ---- the ones that must NOT wait ----------------------------------
    # Both are `motion` in the registry, so anything deriving `wait` from
    # `motion` fails here rather than at a show.
    for key in ("stop", "relax"):
        if key in table:
            t.ok(not table[key][1], "'%s:' does not wait for the move to finish" % key,
                 "STOP has nothing to finish and RELAX unpowers the servos, so "
                 "busy never clears and the sequence hangs on that step")
    for key in ("pose", "goto", "home"):
        if key in table:
            t.ok(table[key][1], "'%s:' does wait" % key,
                 "without it the next step lands mid-move and the two fight")

    # ---- the subcommands keep their word ------------------------------
    t.eq(table.get("effect", ("", False))[0], "RGB EFFECT",
         "'effect:' becomes RGB EFFECT")
    t.eq(table.get("bright", ("", False))[0], "RGB BRIGHT",
         "'bright:' becomes RGB BRIGHT")

    # ---- ADDING ONE COSTS ONE FILE ------------------------------------
    # The claim in the docstring, driven rather than asserted: a new step is
    # declared in the registry, the generator is run, and it appears — with no
    # C++ touched at all.
    # AGAINST A COPY, NEVER THE SHIPPED REGISTRY. Patching the real file and
    # restoring it is safe alone and wrong in the suite, which runs in
    # parallel: every other check that calls gen_tables reads whatever is on
    # disk at that instant. The camera version of this check did exactly that
    # and crashed check_design_system, which had touched nothing (2026-08-21).
    src = F.FIRMWARE / "config" / "commands.json"
    original = src.read_text(encoding="utf-8")
    patched = original.replace(
        '"steps": [{"key": "relax"}]',
        '"steps": [{"key": "relax"}, {"key": "qcnewstep", "wait": true}]', 1)
    if t.ok(patched != original,
            "the registry could be extended for this test",
            "the anchor moved; this check would prove nothing"):
        box = Path(tempfile.mkdtemp(prefix="qc_seqstep_"))
        cfg = box / "commands.json"
        cfg.write_bytes(patched.encode("utf-8"))     # write_bytes: never CRLF
        spec = importlib.util.spec_from_file_location("qc_gen_tables_seq", GEN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.COMMANDS_JSON = cfg
        out = box / "out"
        err = None
        try:
            mod.gen_seqsteps(out, ("nong", "lift"))
        except SystemExit as e:
            err = str(e)
        made = out / "core" / "SeqSteps.h"
        grown = _table(made.read_text(encoding="utf-8")) if made.is_file() else {}
        t.ok("qcnewstep" in grown,
             "a step added to the registry appears with NO C++ change",
             "generator said: %s" % err)
        if "qcnewstep" in grown:
            t.eq(grown["qcnewstep"], ("RELAX", True),
                 "carrying the command it was declared on, and its wait flag")
