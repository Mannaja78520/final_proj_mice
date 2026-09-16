"""A nong with an unset servo pin is NAMED, not missed.

A24-7. The old leader board shipped as a nong with every arm pin at -1: PING
answered, POSE ran, and not one servo moved, because a pin nobody set means
a joint nobody drives. Nothing asserted the map, so it took a person at the
bench to notice. tools/bench_nongpins.py now asks every reachable nong for
PIN? and gates on the law held here (qc/lib/nongpins.py): all eight arm
pins set; WAIST/SHRUG reported but allowed to wait for a linked partner.
"""
import qc as F
import nongpins

AREA = "firmware"
TITLE = "a nong whose arm pins are unset is named joint by joint"
SLOW = False


def run(t):
    full = {"servo%d" % i: {"gpio": g} for i, g in enumerate(
        [32, 33, 25, 26, 21, 22, 27, 14, 13, 15], start=1)}
    arm, body = nongpins.missing(full)
    t.eq(arm, [], "a fully-mapped nong passes")
    t.eq(body, [], "and so does one with waist and shrug wired")

    half = dict(full)
    half["servo3"] = {"gpio": -1}
    arm, body = nongpins.missing(half)
    t.eq([p for p, _ in arm], ["servo3"],
         "an unset elbow is named, with its pin")

    # A reply that never mentions the pin at all is the same silence.
    bare = {k: v for k, v in half.items() if k != "servo7"}
    arm, _ = nongpins.missing(bare)
    t.eq([p for p, _ in arm], ["servo3", "servo7"],
         "a missing entry counts as unset too")

    # WAIST/SHRUG unset is a report, not a fault — a linked partner owns them.
    bodyless = dict(full)
    bodyless["servo9"] = {"gpio": -1}
    bodyless["servo10"] = {"gpio": -1}
    arm, body = nongpins.missing(bodyless)
    t.eq(arm, [], "unset waist/shrug do not fail the arm audit")
    t.eq([p for p, _ in body], ["servo9", "servo10"],
         "but they are still reported for the operator to decide")

    # Garbage in the gpio field must read as unset, not crash the gate.
    junk = dict(full)
    junk["servo5"] = {"gpio": None}
    arm, _ = nongpins.missing(junk)
    t.eq([p for p, _ in arm], ["servo5"],
         "a pin of None is treated as unset, not as an exception")

    # And the bench tool really exists and reads this same law.
    tool = (F.CODE / "tools" / "bench_nongpins.py").read_text(
        encoding="utf-8")
    t.contains(tool, "import nongpins",
               "the bench tool audits through the shared law, not its own")
