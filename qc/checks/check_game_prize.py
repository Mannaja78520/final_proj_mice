"""A win in the friend's game, in a real browser, turns a prize machine (A47-6).

check_gacha proves the hub side (/play/ serving, /api/gacha/game, keys). This
proves apps/all-jao/link.js itself, the part the friend's page runs: a fake game
folder is served at /play/games/ inside an iframe of a hub page, and it does
what the real All-Jao games do (read from their code 2026-10-22):

  * writes a win record into its localStorage list (wheel/claw `logs`): ONE
    GDISPENSE for the new record; the record that was there before the page
    opened and a result no rule names turn nothing;
  * fires the event asked of the friend (`alljao:win`, quiz score 5 by Kim):
    the prize goes to the person the game names;
  * changes a status text to the memory game's "won" words.

Asserted on the fake boards' wire (fake_serial.gacha_wire), never on the page.
"""
import json
import os
import tempfile
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "a win in the friend's game (served by the hub, watched by link.js) turns a prize machine"

GAME = """<!doctype html><meta charset="utf-8"><title>fake game</title>
<script>localStorage.setItem("w", JSON.stringify({logs: [{id: "old", label: "ตุ๊กตาหมี"}]}));</script>
<body><p id="status">play</p>
<script>
setTimeout(function () {
  localStorage.setItem("w", JSON.stringify({logs: [{id: "a1", label: "ตุ๊กตาหมี"}, {id: "old", label: "ตุ๊กตาหมี"}]}));
  localStorage.setItem("w", JSON.stringify({logs: [{id: "a2", label: "ลองใหม่"}, {id: "a1", label: "ตุ๊กตาหมี"},
                                                    {id: "old", label: "ตุ๊กตาหมี"}]}));
  window.dispatchEvent(new CustomEvent("alljao:win", {detail: {game: "quiz", result: "5", player: "Kim", id: "q1"}}));
  document.getElementById("status").textContent = "เก่งมาก! จับคู่ครบทุกคู่แล้ว";
  window.gameDone = true;
}, 600);
</script>
</body>"""


def run(t):
    if not browser.available():
        t.ok(False, "a browser to run the game page", "no Edge/Chromium found")
        return
    tmp = Path(tempfile.mkdtemp(prefix="mice_game_"))
    (tmp / "games").mkdir()
    (tmp / "games" / "index.html").write_text(GAME, encoding="utf-8")
    (tmp / "partners.json").write_text(json.dumps({"games": {
        "name": "Games", "folder": str(tmp / "games"), "play": {
            "inject": "/app/all-jao/link.js",
            "watch": [{"game": "wheel", "key": "w", "list": "logs", "id": "id", "result": "label"},
                      {"game": "memory", "text": "status", "match": "ครบทุกคู่", "result": "won"},
                      {"event": "alljao:win", "result": "result", "person": "player", "id": "id"}]}}}),
        encoding="utf-8")
    (tmp / "gacha.json").write_text(json.dumps({
        "machines": [{"id": "g2", "dev": "usb:COM99:71", "label": "ตู้ข้างประตู", "item": "keychain"}],
        "items": {"keychain": {"label": "พวงกุญแจ"}},
        "event": {"name": "qc game", "open": True}, "wait_s": 5,
        "games": [{"game": "wheel", "result": "ตุ๊กตา", "item": "keychain", "person": "W"},
                  {"game": "quiz", "result": "^5$", "item": "keychain"},
                  {"game": "memory", "result": "won", "item": "keychain", "person": "M"}]},
        ensure_ascii=False), encoding="utf-8")
    os.environ["MICE_GACHA_CONFIG"] = str(tmp / "gacha.json")
    os.environ["MICE_GACHA_DATA"] = str(tmp / "data")
    os.environ["MICE_PARTNERS"] = str(tmp / "partners.json")
    try:
        base, main = F.start_hub()
        fake_serial.reset()
        g = main.hub_api_gacha.gacha()
        g.save_rules({"items": [], "people": []})
        fake_serial.GACHAS[71].stock = 10
        browser.raw_page("""
<iframe id="f" src="/play/games/" style="width:600px;height:300px"></iframe>
<script>
(async function () {
  const f = document.getElementById("f");
  await qcWaitFor(() => f.contentWindow && f.contentWindow.gameDone, 15000);
  await new Promise(go => setTimeout(go, 4000));      // three prizes, each waits for the turn before
  qcMark("done");
})().catch(qcFail);
</script>""", base, seconds=40)
        got = [c for b, c in fake_serial.gacha_wire if c.upper().startswith("GDISPENSE")]
        t.ok("GDISPENSE W" in got and got.count("GDISPENSE W") == 1,
             "a new wheel record gives one prize; the old record and a losing result give none", got)
        t.ok("GDISPENSE Kim" in got, "the game's own win event gives the prize to the player it names", got)
        t.ok("GDISPENSE M" in got, "the memory game's 'won' text gives a prize", got)
        t.ok(len(got) == 3, "and nothing else turned", got)
    finally:
        for k in ("MICE_GACHA_CONFIG", "MICE_GACHA_DATA", "MICE_PARTNERS"):
            os.environ.pop(k, None)
