"""Three copies of things that already existed, and the lists that generate.

A7-6, and all three are the same shape of fault - a second copy of something
the code already had:

  * the move loop wrote out the cosine ease again instead of calling
    `nongmath::ease`. Not just duplication: the copy had no clamp, so a `t`
    below zero - which a show clock can produce when a move's start time is in
    the future - would have driven the joint backwards past where it started;
  * `NongModule::maxDelta` was declared, defined, and called by nothing. It
    forwarded to `nongmath::maxDelta`. Dead code in a file this size is not
    harmless: it is a second name for the real function, and the next person
    calls whichever they find first;
  * the CFG command printed a hand-typed list of setting keys while
    `ConfigStore::MAP` held the real one. That list happened to be correct on
    2026-08-20 - fifteen keys, no drift - which is the only reason it is worth
    saying: it was RIGHT and still wrong to keep, because the drift is silent
    and only shows up to somebody already lost enough to have asked for help.

The check compares the generated list against the table, so a key added to
ConfigStore reaches the operator without anybody remembering the message.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "no second copy of the ease, the delta, or the settings key list"


def run(t):
    nong = (F.FIRMWARE / "src/modules/nong/NongModule.cpp").read_text(encoding="utf-8")
    hdr = (F.FIRMWARE / "src/modules/nong/NongModule.h").read_text(encoding="utf-8")
    math_h = (F.FIRMWARE / "src/modules/nong/NongMath.h").read_text(encoding="utf-8")

    # ---- one ease, and it clamps ------------------------------------
    t.contains(math_h, "inline float ease(",
               "the easing curve is defined once, in NongMath.h")
    ease = math_h[math_h.find("inline float ease("):]
    ease = ease[:ease.find("\n}") + 2]
    t.ok("t <= 0.0f" in ease and "t >= 1.0f" in ease,
         "and it clamps at both ends",
         "a t below zero drives the joint backwards past where it started; a "
         "show clock can produce one when a move starts in the future")

    code = re.sub(r"//[^\n]*", "", nong)
    t.contains(code, "nongmath::ease(",
               "the move loop calls it")
    t.ok("0.5f - 0.5f * cosf" not in code,
         "and does not write the same cosine out again",
         "the copy had no clamp, which is what made it worse than duplication")

    # ---- no dead forwarder ------------------------------------------
    t.ok("float NongModule::maxDelta" not in nong,
         "there is no second name for nongmath::maxDelta",
         "it forwarded, and nothing called it - so the next person calls "
         "whichever of the two they happen to find")
    t.ok("float maxDelta(const float" not in hdr,
         "and it is not declared either",
         "a declaration with no definition is the next compile error")

    # ---- the settings key list is generated -------------------------
    store_h = (F.FIRMWARE / "src/core/ConfigStore.h").read_text(encoding="utf-8")
    store_c = (F.FIRMWARE / "src/core/ConfigStore.cpp").read_text(encoding="utf-8")
    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(encoding="utf-8")

    t.contains(store_h, "String keys() const",
               "the store can say which keys it accepts")
    t.contains(router, "cfg_->keys()",
               "and the CFG command asks it")

    # The message must not spell any key out. This is the assertion with teeth:
    # a helpful person adding "and also try X" puts the drift straight back.
    cfg = router[router.find('if (cmd == "CFG")'):]
    cfg = cfg[:cfg.find("return \"OK \" + k")]
    table = re.findall(r'\{"(\w+)",\s*"\w+"', store_c)
    t.ok(len(table) >= 10, "the settings table has the keys (%d)" % len(table))
    spelled = [k for k in table if '"%s' % k in cfg or ' %s ' % k in cfg]
    t.eq(spelled, [],
         "the CFG error message names no key itself")

    # keys() really walks the table, rather than being a second literal.
    fn = store_c[store_c.find("String ConfigStore::keys()"):]
    fn = fn[:fn.find("\n}") + 2]
    t.contains(fn, "for (auto& m : MAP)",
               "keys() is built from the table it documents")
    t.ok('"' not in fn.replace('" "', "").replace('out += " "', ""),
         "and holds no key of its own",
         "found literals in keys(): %s" % re.findall(r'"([^"]*)"', fn))
