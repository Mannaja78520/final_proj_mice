"""Actual ShowPlayer thread transitions and API epochs: Stop wins stale starts."""
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import qc as F

AREA = "unattended"
TITLE = "Stop rejects pending starts and requires independent board acknowledgement"
STEPS = [{"pose": [90] * 10, "t": 2000}, {"pose": [100] * 10, "t": 2000}]


def run(t):
    sys.path.insert(0, str(F.HUB))
    import hub_show
    import hub_api_play

    def player(command=None, parse=None):
        return hub_show.ShowPlayer(cmd_fn=command or (lambda dev, cmd: "OK stopped"),
                                   parse_fn=parse or (lambda dev: None), cues_fn=lambda cues: cues or [])

    # Request is already entering start(), but has not passed validation yet.
    entered, release = threading.Event(), threading.Event()
    wire, result = [], []
    def delayed_parse(dev):
        entered.set()
        if not release.wait(5):
            raise RuntimeError("fixture validation release missing")
    p = player(lambda dev, cmd: wire.append(cmd) or "OK stopped", delayed_parse)
    request = threading.Thread(target=lambda: result.append(p.start("usb:COM99", STEPS)))
    request.start()
    try:
        t.ok(entered.wait(3), "start is paused before validation completes")
        stopped = p.stop()
    finally:
        release.set()
        request.join(5)
    t.ok(not request.is_alive() and result and result[0].get("ok") is False,
         "Stop invalidates a request already entering validation", result)
    t.ok(not wire and stopped.get("stop_ok") is True,
         "cancelled validation request sends no motion", wire)

    # A complete HTTP request arrives only AFTER Stop: its old epoch is refused.
    p = player(lambda dev, cmd: wire.append(cmd) or "OK stopped")
    epoch = p.status()["epoch"]
    p.stop()
    old_hub = hub_api_play._hub
    class Handler(hub_api_play.PlayRoutes):
        def body(self):
            return json.dumps({"dev": "usb:COM99", "steps": STEPS, "expected_epoch": epoch}).encode()
        def send_json(self, value, code=200):
            return value
        def send_err(self, error, code=400):
            return {"ok": False, "error": str(error)}
    hub_api_play.bind(SimpleNamespace(show=p))
    try:
        t.ok(Handler().api_play("POST", "/api/play", {}).get("ok") is False,
             "API forwards old expected_epoch and refuses transport-delayed start")
        t.ok(not p.running(), "stale HTTP start never creates a clock")
    finally:
        hub_api_play.bind(old_hub)
        p.stop()

    # Pause inside Thread.start(), while start owns its transition lock.
    RealThread = threading.Thread
    gate, spawn, stop_entered, stop_done = (threading.Event() for _ in range(4))
    order, requests = [], []
    class Worker:
        def __init__(self, *args, **kwargs):
            self.alive = False
        def start(self):
            spawn.set()
            if not gate.wait(5):
                raise RuntimeError("fixture spawn release missing")
            self.alive = True
            order.append("START")
        def is_alive(self):
            return self.alive
        def join(self, timeout=None):
            self.alive = False
    p = player(lambda dev, cmd: order.append(cmd) or "OK stopped")
    starter = RealThread(target=lambda: requests.append(p.start("usb:COM99", STEPS)))
    def stop_request():
        stop_entered.set()
        requests.append(p.stop())
        stop_done.set()
    stopper = RealThread(target=stop_request)
    with patch.object(hub_show.threading, "Thread", Worker):
        starter.start()
        try:
            t.ok(spawn.wait(3), "start is paused at worker spawn under transition lock")
            stopper.start()
            t.ok(stop_entered.wait(3), "concurrent Stop is dispatched")
            t.ok(not stop_done.wait(0.05), "Stop does not report success while spawn is unresolved")
        finally:
            gate.set()
            starter.join(5)
            stopper.join(5)
    t.ok(stop_done.is_set() and order == ["START", "STOP"] and not p.running(),
         "serialized Stop runs after pending spawn and leaves no clock", order)

    # Stopping a dead worker still retries an unresolved physical STOP.
    for reply in ("ERR locked", ""):
        p = player(lambda dev, cmd, reply=reply: reply)
        p.dev = "usb:COM99"
        result = p.stop()
        t.ok(result["stop_ok"] is False and result["error"],
             "raw STOP %r cannot be mistaken for acknowledgement" % reply, result)
        t.ok(p.start("usb:COM99", STEPS).get("ok") is False,
             "unconfirmed prior stop blocks a replacement show")
    def broken(dev, cmd):
        raise OSError("serial port disconnected")
    p = player(broken)
    p.dev = "usb:COM99"
    t.ok(p.stop()["stop_ok"] is False, "STOP exception is an explicit failed acknowledgement")

    class BusyWorker:
        alive = True
        def is_alive(self):
            return self.alive
        def join(self, timeout=None):
            pass
    p = player()
    old_worker = BusyWorker()
    p.thread, p.dev = old_worker, "usb:COM99"
    result = p.stop()
    t.ok(not result["stop_ok"] and p.thread is old_worker,
         "join timeout preserves unresolved worker ownership", result)
    t.ok(p.start("usb:OTHER", STEPS).get("ok") is False and p.dev == "usb:COM99",
         "replacement cannot overwrite unresolved worker device or event")
    old_worker.alive = False
    p._cmd_fn = lambda dev, cmd: "ERR still locked"
    t.ok(not p.stop()["stop_ok"], "worker exit cannot erase an unresolved board STOP refusal")
    p._cmd_fn = lambda dev, cmd: "OK stopped"
    result = p.stop()
    t.ok(result["stop_ok"] and not result["error"] and p.thread is None,
         "retry confirms stopped state independently of historical error", result)

    p = player(lambda dev, cmd: "OK stopped" if cmd == "STOP" else "OK audio stopped")
    p.dev = "usb:COM99"
    p.steps = [{"cues": ["PLAY /music/demo.mp3"]}]
    result = p.stop()
    t.eq(result["stop_reply"], "OK stopped", "STOP proof is separate from later audio reply")
    t.eq(result["last"], "OK audio stopped", "later audio command cannot overwrite STOP acknowledgement field")
