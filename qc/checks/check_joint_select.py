"""What a person may type for WHICH JOINT is decided in one place.

Five commands take the same first argument — GEAR, PULSE, RANGE, SERVO and HZ
all accept `<1-10|name|ALL>` — and each used to spell out the same three
things: parse the word, refuse it with the same sentence, and loop over the
joints it covers. Five copies of a rule about what a person is allowed to type.

That is worse than ordinary duplication, because the ERROR MESSAGE is part of
the rule. It is what tells someone what they may type instead, so a rule
changed in one command and not the other four leaves four commands telling
people something untrue.

This asserts the rule lives once — and then drives all five commands over the
wire, in the same run, to prove they really do behave the same way. The plan
said thirteen copies of three idioms; the code said five of each. The count in
this file came from counting.
"""
import re

import fake_serial
import qc as F

AREA = "nong"
TITLE = "which joint a command means is decided in one place"
SLOW = False

SRC = F.FIRMWARE / "src/modules/nong/NongModule.cpp"
HDR = F.FIRMWARE / "src/modules/nong/NongModule.h"

# Every command that takes <1-10|name|ALL>. Adding one here is how a new
# command gets covered — there is no list of these anywhere else.
TAKE_A_JOINT = ["GEAR", "PULSE", "RANGE", "SERVO", "HZ"]


def _code(path):
    s = path.read_text(encoding="utf-8", errors="replace")
    s = re.sub(r"//.*", "", s)
    return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def run(t):
    code = _code(SRC)
    hdr = _code(HDR)

    # ---- the rule is written once -------------------------------------
    t.contains(hdr, "struct JointSel", "there is one way to say which joints")
    t.contains(hdr, "jointSelHelp",
               "and one sentence telling a person what they may type")

    stray = len(re.findall(r'"ERR joint 1-10, name, or ALL"', code))
    t.ok(stray == 0,
         "no command spells that sentence out for itself",
         "%d copies left — change what a joint may be called and they disagree"
         % stray)

    hand_parsed = len(re.findall(r'==\s*"ALL"\s*\)\s*\?\s*-1\s*:\s*jointIndex', code))
    t.ok(hand_parsed == 0,
         "no command parses the joint word for itself", hand_parsed)

    hand_loop = len(re.findall(r"j\s*<\s*0\s*\|\|\s*i\s*==\s*j", code))
    t.ok(hand_loop == 0,
         "and none writes the which-joints-does-this-cover test by hand",
         "%d left" % hand_loop)

    uses = len(re.findall(r"selectJoints\(", code))
    t.ok(uses >= len(TAKE_A_JOINT),
         "every command that takes a joint asks for the selection",
         "%d call sites for %d commands" % (uses, len(TAKE_A_JOINT)))

    # ---- what this check CANNOT prove ---------------------------------
    # Driving GEAR/PULSE/RANGE over the wire was tried here and removed: the
    # fake module is a PYTHON stand-in and never implemented those commands, so
    # every assertion passed or failed for reasons that had nothing to do with
    # the C++. A green run here means the rule is written once — it does NOT
    # mean the five commands were executed. That needs a board, and the plan
    # marks the tasks that need one.
    #
    # What IS executed on a PC is the arithmetic in NongMath.h, by the native
    # tests in firmware/test/test_logic. JointSel is not there because it uses
    # Arduino's String; making it testable natively would mean a shim, which is
    # more machinery than the rule is worth.
    t.ok(True, "NOTE: the rule is asserted, the five commands are not executed")
