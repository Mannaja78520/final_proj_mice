"""Which servos would be SILENT on a nong, straight from its PIN? reply.

A24-7: the old leader shipped with every ARM pin at -1 and nobody could hear
a servo until the map was rewritten by hand on the bench (2026-08-26). The
assertion lives here, apart from any transport, so the bench tool
(tools/bench_nongpins.py) and the QC check read the same law.
"""

# Joints 1-8 are the arm; a nong that cannot drive them is not a nong.
ARM_JOINTS = ["servo%d" % i for i in range(1, 9)]
# WAIST and SHRUG may legitimately wait for a second linked board.
BODY_JOINTS = ["servo9", "servo10"]


def _gpio(reply: dict, pin: str) -> int:
    rec = reply.get(pin)
    try:
        return int(rec.get("gpio", -1)) if isinstance(rec, dict) else -1
    except (TypeError, ValueError):
        return -1


def missing(reply: dict):
    """-> (arm, body): unset joints as (name, gpio) pairs.

    An arm pin at -1 means a servo nobody drives — exactly the state that
    sat unnoticed on a real board once. Body joints are reported so the
    operator can decide, not treated as a fault.
    """
    arm = [(p, _gpio(reply, p)) for p in ARM_JOINTS if _gpio(reply, p) < 0]
    body = [(p, _gpio(reply, p)) for p in BODY_JOINTS if _gpio(reply, p) < 0]
    return arm, body
