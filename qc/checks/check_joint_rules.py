"""A joint field is allowed the same values whichever command sets it.

Six numbers describe a joint - the gear ratio, the pulse window, the maximum
speed, the servo's travel, the frame rate, the joint's limits - and each can be
set one at a time (GEAR, PULSE, SERVO, RANGE, HZ, LIMIT) or all at once (JCFG).
Until 2026-08-20 every rule was written out twice, once in each place.

The copies had ALREADY drifted, in wording: `need 100<=pmin, pmax>pmin+100` in
one and `need 100<=min, max>min+100, max<=5000 (us)` in the other, and JCFG's
travel message had lost the `(180 normal, 270 wide)` hint the single command
gives. Drifting wording is harmless on its own. It is the warning that the
NUMBERS drift next, and JCFG's own comment said what that would cost: a batch
must never be a way to smuggle in a value the single command would refuse.

So the rules live in `modules/nong/JointRules.h`, one function each, message
included - and this checks that neither caller has quietly grown its own copy
again. The limits themselves are NOT restated here: this asserts that there is
one definition, not what the numbers are, because a check that repeats the
numbers is a third copy of exactly the thing being removed.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "one rule per joint field, shared by the single commands and JCFG"

RULES = "src/modules/nong/JointRules.h"
NONG = "src/modules/nong/NongModule.cpp"


def run(t):
    rules = (F.FIRMWARE / RULES).read_text(encoding="utf-8")
    src = (F.FIRMWARE / NONG).read_text(encoding="utf-8")

    # ---- there is one rule per field --------------------------------
    named = set(re.findall(r"inline bool (\w+)\(", rules))
    for want in ("gear", "pulse", "dps", "travel", "hz", "limits"):
        t.ok(want in named, "there is one rule for %s" % want,
             "found %s" % sorted(named))

    # Each rule carries its own message. A rule that returns false without
    # saying why forces the caller to invent the wording, which is how the two
    # copies came to disagree in the first place.
    for name in named:
        body = rules[rules.find("inline bool %s(" % name):]
        body = body[:body.find("\n}")]
        t.contains(body, 'err = "ERR',
                   "%s says why it refused" % name)

    # ---- and both callers use them ----------------------------------
    t.contains(src, 'JointRules.h', "the nong module includes the rules")
    calls = re.findall(r"jointrule::(\w+)\(", src)
    t.ok(len(calls) >= 10,
         "both the single commands and JCFG go through them (%d calls)"
         % len(calls),
         "six rules used by two callers is at least ten calls; found %s"
         % sorted(set(calls)))

    jcfg = src[src.find('if (cmd == "JCFG")'):]
    jcfg = jcfg[:jcfg.find("forward(")]
    for want in ("gear", "pulse", "dps", "travel", "hz", "limits"):
        t.contains(jcfg, "jointrule::%s(" % want,
                   "JCFG checks %s with the shared rule" % want)

    # ---- nobody has written the checks out again --------------------
    # The real regression: a new command, or a tidy-up, restating a limit in
    # NongModule.cpp. Comments are stripped first - this file explains what the
    # old checks were, and an assertion that matched its own explanation would
    # be the fourth check in this suite to fall for that.
    code = re.sub(r"//[^\n]*", "", src)
    # CLAMPING IS NOT VALIDATING, and both are right in their place. A value
    # loaded from saved settings cannot be refused - there is nobody to refuse
    # it to - so it is constrained into range at load time. What must not come
    # back is a COMMAND deciding for itself what a legal value is, so the
    # limits may appear here only inside a constrain() call.
    strays = []
    src_lines = code.splitlines()
    for n, line in enumerate(src_lines):
        if not re.search(r"NONG_(?:FRAME_HZ|RANGE)_(?:MIN|MAX)", line):
            continue
        near = " ".join(src_lines[max(0, n - 1):n + 2])
        if "constrain(" not in near:
            strays.append(line.strip()[:70])
    t.eq(strays, [],
         "a command never restates a hardware limit - only clamping may")

    for phrase in ("pinion/gear must be", "max_dps must be",
                   "joint max must exceed"):
        t.eq(code.count(phrase), 0,
             "the %r message is not written out in the module" % phrase)
        t.eq(rules.count(phrase), 1,
             "and exists exactly once, in the rules")
