"""The hub only ever moves the arm along legs Studio checked (A46-1).

main_python/gestures.py never decides a pose; it strings Studio's fitted
legs together: home -> resting hands, resting hands -> a gesture and back, the
moves inside a gesture, and straight from one gesture into the next ONLY when
Studio listed that pair as clear (`direct`). A shortcut anywhere else would be
a move nobody checked for the arm hitting the body.

So this throws hundreds of random plans at it (words, lengths, manners, seeds,
half the pairs listed as clear) and asserts every move in every plan is one of
those legs. Proven by breaking it: taking every pair as clear fails here.
The poses are far apart on purpose, so maxDps stretches moves, the arm runs
late and gestures get skipped (lateMs) - the plans where a careless shortcut
from one gesture to a later one would show.
"""
import random

import qc as F

AREA = "studio"
TITLE = "talk gestures move only along legs Studio checked"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    sys.path.insert(0, str(F.CODE / "tools"))
    import gestures as G
    import registry
    lib = registry.load(F.CODE / "config" / "gestures.json")
    P = lambda v: [float(v)] * 10                                  # noqa: E731
    fit = {"rig": {"min": [0] * 10, "max": [180] * 10, "home": P(90)},
           "restDef": lib["rest"]["keys"],
           "rest": {"keys": [{"pose": P(91), "t": 600}], "in": [{"pose": P(90.5), "t": 300, "via": True}],
                    "out": [{"pose": P(90.7), "t": 300, "via": True}]},
           "defs": {}, "gestures": {}, "direct": []}
    ids, legs = [], set()
    leg = lambda a, b: legs.add((tuple(a), tuple(b)))             # noqa: E731
    for i, (gid, g) in enumerate(lib["gestures"].items()):
        fit["defs"][gid] = g["keys"]
        for m in ("", "~m"):
            # far apart, so maxDps (not the gesture's own t) times most moves and
            # the arm runs late - the case where a gesture gets skipped
            base = 30 + i + (0.5 if m else 0)
            ks = [{"pose": P(base + 100 * ((k + i) % 2) + k / 10), "t": x.get("t", 400), "hold": x.get("hold", 0)}
                  for k, x in enumerate(g["keys"])]
            fit["gestures"][gid + m] = {"keys": ks, "in": [{"pose": P(base - 0.25), "t": 300, "via": True}],
                                        "out": [{"pose": P(base - 0.3), "t": 300, "via": True}]}
            ids.append(gid + m)
            chain = [P(91), P(base - 0.25)] + [k["pose"] for k in ks] + [P(base - 0.3), P(91)]
            for a, b in zip(chain, chain[1:]):
                leg(a, b)
    rnd = random.Random(1)
    fit["direct"] = [a + ">" + b for a in ids for b in ids if a != b and rnd.random() < 0.5]
    for d in fit["direct"]:
        a, b = d.split(">")
        leg(fit["gestures"][a]["keys"][-1]["pose"], fit["gestures"][b]["keys"][0]["pose"])
    for a, b in ((P(90), P(90.5)), (P(90.5), P(91)), (P(91), P(90.7)), (P(90.7), P(90))):
        leg(a, b)
    texts = ["สวัสดีค่ะ ยินดีต้อนรับทุกคน มีอะไรให้ช่วยไหม ขอบคุณค่ะ",
             "hello everyone, thank you, what do you want? great!", "คุณ " * 30, "ok"]
    bad, plans = [], 0
    for n in range(200):
        for tx in texts:
            r = G.plan(lib, fit, tx, ms=rnd.choice([0, 1500, 3000, 6000]),
                       manner=rnd.choice(["playful", "polite", "sassy", ""]), seed=n)
            if not r.get("ok"):
                bad.append(("no plan", tx, r))
                continue
            plans += 1
            st = r["steps"]
            for a, b in zip(st, st[1:]):
                if a["pose"] != b["pose"] and (tuple(a["pose"]), tuple(b["pose"])) not in legs:
                    bad.append((n, tx[:20], a["pose"][0], b["pose"][0]))
    t.ok(plans == 800, "every random plan was made", bad[:2])
    t.ok(not bad, "every move of %d random plans is a leg Studio checked" % plans,
         "unchecked straight moves (seed, text, from, to): %s" % bad[:4])
