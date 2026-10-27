"""Prize machines over every route a module has: USB, RS485 and WiFi (A47-19).

User 2026-10-23, in the lab with one dispenser and a second bare ESP32 on USB:
the gachapon must be commanded and updated over WiFi, RS485 and USB "like the
other modules". The board side is the shared core (main.cpp USB reader and
RS485 bus feed one CommandRouter; FWBEGIN/FWDATA/FWEND ride any of them), so
what can break is the HUB: a machine row's `dev` must reach the right wire.

Three fake dispensers, one per route, asserted on what each board was told:
  * usb:COM96      a dispenser on its own cable (fake_serial.USB_GACHA, id 72)
  * usb:COM99:70   a dispenser behind a cable on the RS485 bus
  * wifi:<ip>      a dispenser over WiFi; GDISPENSE changes, so the hub must
                   log in to the board first (fake_wifi gate, 401 otherwise)
Then the stand-in: a bare ESP32 has no hall, so `GCFG fallback <ms>` turns by
time and the board reports `timed`; config/gacha.json given_results counts it
as given (the board already took it off its stock), a jam still is not.
Firmware update: hub_flash offers the mice_gacha image like every type in
modules.json, for the cable (esptool), WiFi (/api/ota) and bus (FW* commands).
"""
import json
import os
import tempfile
from pathlib import Path

import fake_serial
import fake_wifi
import qc as F

AREA = "hub"
TITLE = "prize machines answer over USB, RS485 and WiFi; a timed stand-in counts"


def _post(base, path, body):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    if F._cookie[0]:
        req.add_header("Cookie", F._cookie[0])
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_gacha_routes_"))
    wifi = fake_wifi.start()
    fake_wifi.reset()
    air = fake_serial._Gacha(73)
    fake_wifi.MODULE.gacha = air
    fake_serial.gacha_port_listed[0] = True
    cfg = {
        "machines": [
            {"id": "usb", "dev": "usb:%s" % fake_serial.GACHA_PORT, "label": "USB", "item": "pen"},
            {"id": "bus", "dev": "usb:%s:70" % fake_serial.PORT, "label": "RS485", "item": "cap"},
            {"id": "air", "dev": "wifi:%s" % wifi, "label": "WiFi", "item": "cup"},
        ],
        "items": {"pen": {}, "cap": {}, "cup": {}},
        "event": {"name": "routes", "open": True},
        "wait_s": 5,
    }
    (tmp / "gacha.json").write_text(json.dumps(cfg), encoding="utf-8")
    os.environ["MICE_GACHA_CONFIG"] = str(tmp / "gacha.json")
    os.environ["MICE_GACHA_DATA"] = str(tmp / "data")
    base, main = F.start_hub()
    fake_serial.reset()
    usb, bus = fake_serial.USB_GACHA, fake_serial.GACHAS[70]
    try:
        for mid, board, item in (("usb", usb, "pen"), ("bus", bus, "cap"), ("air", air, "cup")):
            code, got = _post(base, "/api/gacha/machine", {"machine": mid, "cmd": "GSTOCK 3"})
            t.ok(board.stock == 3, "%s: the stock command reached that board" % mid, (code, got))
            code, got = _post(base, "/api/gacha/dispense", {"item": item, "person": "P" + mid,
                                                            "app": "qc", "wait": True})
            t.ok(got.get("ok") and got.get("machine") == mid and got.get("result") == "done",
                 "%s: a prize is given and the hub waited until it fell" % mid, got)
            t.ok(board.seq == 1 and board.who == "P" + mid and board.stock == 2,
                 "%s: the board itself turned once for that person" % mid,
                 (board.seq, board.who, board.stock))
        others = [c for b, c in fake_serial.gacha_wire if b == 71]
        t.ok(not others, "no other board was told anything", others)
        t.ok(any(c.startswith("GDISPENSE") for c in fake_wifi.MODULE.cmds),
             "over WiFi the hub logged in and the board took GDISPENSE", fake_wifi.MODULE.cmds[-5:])

        # the stand-in ESP32: no hall, GCFG fallback -> "timed"
        usb.finish_as = "timed"
        code, got = _post(base, "/api/gacha/dispense", {"item": "pen", "person": "Q",
                                                        "app": "qc", "wait": True})
        t.ok(got.get("ok") and got.get("result") == "timed",
             "a timed turn (bare stand-in board) is reported as timed", got)
        g = main.hub_api_gacha.gacha()
        rows = g.log_rows(20)
        last = [r for r in rows if r.get("seq") in (2, "2") and r.get("machine") == "usb"]
        t.ok(last and last[-1].get("kind") == "done",
             "and counted as given, as given_results says", rows[-3:])
        usb.finish_as, usb.jam = "done", True
        _post(base, "/api/gacha/dispense", {"item": "pen", "person": "R", "app": "qc", "wait": True})
        rows = g.log_rows(20)
        jam = [r for r in rows if r.get("seq") in (3, "3") and r.get("machine") == "usb"]
        t.ok(jam and jam[-1].get("kind") == "jam", "a jam is still a jam", rows[-3:])

        # firmware: the gacha image is offered like every other type
        hf = main.hub_flash
        t.ok(hf.flash_env("gacha") == "mice_gacha", "the gacha build is env mice_gacha")
        t.ok(any(im["type"] == "gacha" for im in hf.flash_images()),
             "the firmware page lists the dispenser (from modules.json)",
             [im["type"] for im in hf.flash_images()])
        for name in ("start", "start_ota", "start_bus"):
            t.ok(callable(getattr(hf.Flasher, name, None)),
                 "a gacha can be flashed by %s, the shared path" % name)
    finally:
        fake_wifi.MODULE.gacha = None
        fake_serial.gacha_port_listed[0] = False
        usb.jam = False
        os.environ.pop("MICE_GACHA_CONFIG", None)
        os.environ.pop("MICE_GACHA_DATA", None)
