"""The friend's game contract (handoff 2026-11-05): score range rule + webhook out.

  * a "games" rule with min/max gives a prize only for a score inside the range
    (the quiz ends every round with a score; the hub decides what wins);
  * gacha.out goes to a webhook entry {url, format: "alljao"} as
    {event: "gacha.out", id: <unique>} with "Authorization: Bearer <token>", the
    token from the environment, never from the config file (public repo);
  * with no token nothing is sent and the failure is logged.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "friend's game: quiz score range gives a prize; gacha.out reaches their webhook with a bearer token"


def _engine(root, cfg, posts):
    source = F.CODE / "main_python"
    sys.path.insert(0, str(source))
    try:
        spec = importlib.util.spec_from_file_location("_qc_friend_gacha", source / "gacha.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(source))
    path = root / "gacha.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return module.Gacha(path, root / "data", lambda d, c: "OK", lambda n: "x",
                        post=lambda u, b, h=None: posts.append((u, b, h)) or 200)


def run(t):
    old = os.environ.pop("GACHA_WEBHOOK_TOKEN", None)
    try:
        with tempfile.TemporaryDirectory(prefix="mice_friend_") as folder:
            root, posts = Path(folder), []
            hook = {"url": "http://game.invalid/api/gacha/webhook", "format": "alljao"}
            g = _engine(root, {"machines": [], "items": {"k": {"label": "K"}}, "event": {"open": True},
                               "games": [{"game": "quiz", "min": 8, "item": "k"}, {"game": "big", "min": 8, "item": "k"}, {"game": "spin", "item": "k"},
                                         {"game": "wheel", "result": "x", "item": "k"}],
                               "webhooks": {"out": [hook]}}, posts)
            fits = lambda game, r: bool(g.game_item(game, r))          # noqa: E731
            t.ok(fits("big", "8") and fits("big", 10) and not fits("big", "7") and not fits("big", "abc"),
                 "a rule min 8 (no top known): 8 and 10 win, 7 and a non-number do not",
                 [fits("big", v) for v in ("8", 10, "7", "abc")])
            t.ok(fits("quiz", 5) and not fits("quiz", 4),
                 "a quiz rule min 8 is lowered to the top score 5, so a full score still wins", [fits("quiz", 5), fits("quiz", 4)])
            t.ok(fits("spin", "ส่วนลด 10%") and not fits("spin", "ลองใหม่") and not fits("spin", "Try again!"),
                 "a rule without a pattern pays a real slice, but a try-again slice never gives a prize")
            t.ok(fits("wheel", "xx") and not fits("wheel", "y"), "a rule without a range still matches by result")

            g.hook("out", {"item": "k", "machines": ["g1"]})
            time.sleep(0.5)
            t.ok(not posts, "no token: nothing is sent", posts)
            t.ok(any(h.get("ok") is False and "token" in h.get("error", "") for h in g.hook_log),
                 "and the missing token shows in the hook log", g.hook_log)

            os.environ["GACHA_WEBHOOK_TOKEN"] = "qc-secret"
            g.hook("out", {"item": "k", "machines": ["g1"]})
            g.hook("out", {"item": "k", "machines": ["g1"]})
            for _ in range(40):
                if len(posts) >= 2:
                    break
                time.sleep(0.1)
            t.ok(len(posts) == 2 and posts[0][0] == hook["url"], "gacha.out is posted to their webhook", posts)
            if len(posts) == 2:
                b0, b1 = posts[0][1], posts[1][1]
                t.ok(b0.get("event") == "gacha.out" and b0.get("id") and b0["id"] != b1["id"],
                     "body has event gacha.out and a unique id each time", (b0, b1))
                t.ok(posts[0][2] == {"Authorization": "Bearer qc-secret"}, "with the bearer token", posts[0][2])
    finally:
        os.environ.pop("GACHA_WEBHOOK_TOKEN", None)
        if old is not None:
            os.environ["GACHA_WEBHOOK_TOKEN"] = old
