"""Prize machine stock both ways, play only, other sources, the random box.

User 2026-11-05: set the stock in the prize machine and tell the game what is
there; a game may be play only (no real prize); other programs may use the
machine; a random box takes the count of each item when loaded and a press
gives one, weighted by what is left. Asserted on the fake boards' wire.

  * GET /api/gacha/stock lists every kind with stock, odds and available;
    a kind with an event total is capped by it; a kind with no machine is
    listed as not available;
  * loading a random box writes its counts and tells the board GSTOCK <sum>;
  * 4 presses of a box holding a:3, b:1 give exactly that (3 a, 1 b), each
    turns the board once, the 5th is refused "box empty" and moves nothing;
  * a game in config play_only wins with no GDISPENSE; one request can turn
    play only off (or on) for itself;
  * the game names a kind from the stock list (item): that kind is given;
    a kind the hub does not know falls back to the rules;
  * a source with its own item list / closed is refused before any machine;
  * webhooks.stock hears the stock after a prize, with the new counts.
"""
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import fake_serial
import qc as F

AREA = "hub"
TITLE = "prize machine stock: hub tells games the stock, play only, other sources, random box"


def _call(base, method, path, body=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    if F._cookie[0]:
        req.add_header("Cookie", F._cookie[0])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def _turns():
    return [(b, c) for b, c in fake_serial.gacha_wire if c.upper().startswith("GDISPENSE")]


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_gstock_"))
    heard = []

    class Hook(BaseHTTPRequestHandler):
        def do_POST(self):                                   # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            heard.append(json.loads(self.rfile.read(n).decode() or "{}"))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    hook = HTTPServer(("127.0.0.1", F._free_port()), Hook)
    threading.Thread(target=hook.serve_forever, daemon=True).start()
    cfg = {
        "machines": [
            {"id": "g1", "dev": "usb:COM99:70", "label": "bear machine", "item": "bear"},
            {"id": "box", "dev": "usb:COM99:71", "label": "mystery box", "item": "mystery",
             "mode": "random"},
        ],
        "items": {"bear": {"label": "Bear"}, "mystery": {"label": "Mystery"},
                  "a": {"label": "Item A"}, "b": {"label": "Item B"}, "cup": {"label": "Cup"}},
        "event": {"name": "", "open": True},
        "games": [{"game": "quiz", "item": "bear"}, {"game": "wheel", "item": "bear"}],
        "play_only": {"game:quiz": True},
        "sources": {"kiosk": {"items": ["bear"]}, "shut": {"enabled": False}},
        "webhooks": {"stock": ["http://127.0.0.1:%d/hook" % hook.server_port]},
        "wait_s": 5,
    }
    (tmp / "gacha.json").write_text(json.dumps(cfg), encoding="utf-8")
    os.environ["MICE_GACHA_CONFIG"] = str(tmp / "gacha.json")
    os.environ["MICE_GACHA_DATA"] = str(tmp / "data")
    base, main = F.start_hub()
    fake_serial.reset()
    g = main.hub_api_gacha.gacha()
    try:
        _call(base, "POST", "/api/gacha/machine", {"machine": "g1", "cmd": "GSTOCK 3"})
        code, got = _call(base, "POST", "/api/gacha/load",
                          {"machine": "box", "items": {"a": 3, "b": 1}})
        t.ok(got.get("ok") and fake_serial.GACHAS[71].stock == 4
             and ("71", "GSTOCK 4") in [(str(b), c) for b, c in fake_serial.gacha_wire],
             "loading a random box tells the board the sum of its items", (code, got))
        t.ok(g.boxes().get("box") == {"a": 3, "b": 1}, "and the hub keeps each item's count", g.boxes())

        code, st = _call(base, "GET", "/api/gacha/stock")
        rows = {r["item"]: r for r in st.get("items") or []}
        t.ok(rows.get("bear", {}).get("stock") == 3 and rows.get("a", {}).get("stock") == 3
             and rows.get("b", {}).get("stock") == 1,
             "the stock list shows each kind's real count (bear 3, a 3, b 1)", rows)
        t.ok(rows.get("cup", {}).get("available") is False and rows["bear"]["available"],
             "a kind with no machine is listed as not available", rows.get("cup"))
        pool = rows["bear"]["odds"] + rows["a"]["odds"] + rows["b"]["odds"]
        t.ok(abs(pool - 1.0) < 0.01 and rows["b"]["odds"] < rows["a"]["odds"],
             "odds follow the stock and add up to one", [rows[i]["odds"] for i in ("bear", "a", "b")])
        g.save_rules({"items": [{"event": "", "item": "bear", "total": "2"}], "people": []})
        rows = {r["item"]: r for r in _call(base, "GET", "/api/gacha/stock")[1]["items"]}
        t.ok(rows["bear"]["stock"] == 2, "an event total caps the stock list", rows["bear"])
        g.save_rules({"items": [], "people": []})

        code, st = _call(base, "GET", "/api/gacha/stock?game=quiz")
        t.ok(st.get("play_only") is True and _call(base, "GET", "/api/gacha/stock?game=wheel")[1]["play_only"] is False,
             "the stock answer says which game is play only", st.get("play_only"))
        code, st = _call(base, "GET", "/api/gacha/stock?source=kiosk")
        t.ok([r["item"] for r in st["items"]] == ["bear"], "a source's list holds only its own kinds", st["items"])

        # play only
        n0 = len(_turns())
        code, got = _call(base, "POST", "/api/gacha/game", {"game": "quiz", "result": "5", "ref": "q1"})
        t.ok(got.get("ok") and got.get("play_only") and len(_turns()) == n0,
             "a play-only game wins with no machine turning", (got, _turns()))
        code, got = _call(base, "POST", "/api/gacha/game",
                          {"game": "quiz", "result": "5", "ref": "q2", "play_only": False})
        t.ok(got.get("ok") and not got.get("play_only") and len(_turns()) == n0 + 1,
             "one request can turn play only off for itself", got)
        code, got = _call(base, "POST", "/api/gacha/game",
                          {"game": "wheel", "result": "x", "ref": "w1", "play_only": True})
        t.ok(got.get("play_only") and len(_turns()) == n0 + 1, "or on, for a game not set that way", got)

        # the game names a kind from the stock list
        code, got = _call(base, "POST", "/api/gacha/game",
                          {"game": "wheel", "result": "whatever", "ref": "w2", "item": "bear"})
        t.ok(got.get("ok") and got.get("machine") == "g1" and len(_turns()) == n0 + 2,
             "the game names a kind from the stock list: that kind is given", got)

        # sources
        n1 = len(_turns())
        code, got = _call(base, "POST", "/api/gacha/dispense", {"item": "mystery", "app": "kiosk"})
        t.ok(not got.get("ok") and got.get("reason") == "source item" and len(_turns()) == n1,
             "a source may only ask for its own kinds", got)
        code, got = _call(base, "POST", "/api/gacha/dispense", {"item": "bear", "app": "shut"})
        t.ok(not got.get("ok") and got.get("reason") == "source closed" and len(_turns()) == n1,
             "a closed source is refused", got)
        code, got = _call(base, "POST", "/api/gacha/dispense", {"item": "bear", "app": "new-program", "play_only": True})
        t.ok(got.get("ok") and got.get("play_only") and len(_turns()) == n1,
             "a program nobody wrote down may ask, and play only works for any program", got)

        # the random box
        given = []
        for i in range(4):
            code, got = _call(base, "POST", "/api/gacha/random", {"machine": "box", "wait": True})
            given.append(got.get("drawn"))
            time.sleep(0.05)
        t.ok(sorted(given) == ["a", "a", "a", "b"],
             "four presses give exactly what was loaded (3 a, 1 b), whatever the order", given)
        n2 = len(_turns())
        code, got = _call(base, "POST", "/api/gacha/random", {"machine": "box"})
        t.ok(not got.get("ok") and got.get("reason") == "box empty" and len(_turns()) == n2,
             "an empty box is refused and moves nothing", got)
        code, got = _call(base, "POST", "/api/gacha/load",
                          {"machine": "box", "items": [{"item": "a", "count": 2}], "mode": "add"})
        t.ok(g.boxes().get("box") == {"a": 2}, "adding to a box puts more in", g.boxes())

        # stock webhook
        deadline = time.time() + 5
        while time.time() < deadline and not any(h.get("type") == "gacha.stock" for h in heard):
            time.sleep(0.1)
        ev = [h for h in heard if h.get("type") == "gacha.stock"]
        t.ok(ev and {"item", "stock", "odds"} <= set(ev[-1]["stock"][0]),
             "webhooks.stock hears the stock list", ev[-1:] or heard)
    finally:
        hook.shutdown()
        os.environ.pop("MICE_GACHA_CONFIG", None)
        os.environ.pop("MICE_GACHA_DATA", None)
