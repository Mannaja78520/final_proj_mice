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
        p._motion_dev = p.dev
        result = p.stop()
        t.ok(result["stop_ok"] is False and result["error"],
             "raw STOP %r cannot be mistaken for acknowledgement" % reply, result)
        t.ok(p.start("usb:COM99", STEPS).get("ok") is False,
             "unconfirmed prior stop blocks a replacement show")
    def broken(dev, cmd):
        raise OSError("serial port disconnected")
    p = player(broken)
    p.dev = "usb:COM99"
    p._motion_dev = p.dev
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
    p._motion_dev = p.dev
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
    p._motion_dev = p.dev
    p.steps = [{"cues": ["PLAY /music/demo.mp3"]}]
    result = p.stop()
    t.eq(result["stop_reply"], "OK stopped", "STOP proof is separate from later audio reply")
    t.eq(result["last"], "OK audio stopped", "later audio command cannot overwrite STOP acknowledgement field")

    # Confirmed history is not unresolved ownership: disconnected A cannot block B.
    calls, disconnected = [], [False]
    def routed(dev, command):
        calls.append((dev, command))
        if dev == "usb:A" and disconnected[0]:
            raise OSError("A disconnected")
        return "OK accepted"
    p = player(routed)
    p.home("usb:A", p.status()["epoch"])
    t.ok(p.stop()["stop_ok"] and not p._motion_dev, "confirmed HOME Stop releases actual motion ownership")
    disconnected[0] = True
    old_count = len(calls)
    started = p.start("usb:B", STEPS)
    t.ok(started.get("running") is True and not any(dev == "usb:A" for dev, _ in calls[old_count:]),
         "confirmed/disconnected historical A does not block playing B", calls[old_count:])
    p.stop()

    # Transport-delayed HOME carries an epoch and never dispatches after Stop.
    wire = []
    p = player(lambda dev, command: wire.append((dev, command)) or "OK stopped")
    epoch = p.status()["epoch"]
    p.stop()
    t.ok(p.home("usb:B", epoch).get("ok") is False and not wire,
         "HOME delivered after newer Stop cannot dispatch")
    for bad in (None, True, 0.5, "1"):
        t.ok(p.home("usb:B", bad).get("ok") is False, "HOME refuses invalid epoch %r" % (bad,))

    # HOME dispatch owns its target through timeout, then Stop reaches that target.
    def lost_home(dev, command):
        wire.append((dev, command))
        if command == "HOME":
            raise TimeoutError("HOME sent; reply lost")
        return "OK stopped"
    p = player(lost_home)
    t.ok(not p.home("usb:B", p.status()["epoch"])["ok"] and p._motion_dev == "usb:B",
         "ambiguous HOME retains ownership for safety")
    result = p.stop()
    t.ok(result["stop_ok"] and result["stop_dev"] == "usb:B" and not p._motion_dev,
         "Stop after ambiguous HOME acknowledges and releases the actual target", result)

    # Stop arriving during HOME IO waits the transition and sends STOP afterward.
    entered, release, finished = (threading.Event() for _ in range(3))
    order = []
    def waiting_home(dev, command):
        order.append(command)
        if command == "HOME":
            entered.set()
            if not release.wait(5):
                raise TimeoutError("fixture HOME release missing")
        return "OK acknowledged"
    p = player(waiting_home)
    home_thread = threading.Thread(target=lambda: p.home("usb:B", p.status()["epoch"]))
    stop_results = []
    def concurrent_stop():
        stop_results.append(p.stop())
        finished.set()
    stop_thread = threading.Thread(target=concurrent_stop)
    home_thread.start()
    try:
        t.ok(entered.wait(3), "HOME is paused inside bounded dispatch")
        stop_thread.start()
        t.ok(not finished.wait(0.05), "Stop cannot report success while HOME IO owns transition")
    finally:
        release.set()
        home_thread.join(5)
        stop_thread.join(5)
    t.ok(order == ["HOME", "STOP"] and stop_results and stop_results[0]["stop_ok"] and not p._motion_dev,
         "Stop during HOME finishes with acknowledged STOP on the same target", order)

    # The new exact route is login gated before it can touch any fake board.
    import fake_serial
    base, main = F.start_hub()
    F.logout_qc()
    before = sum(command == "HOME" for _, command in fake_serial.wire)
    status, body = F.post(base + "/api/play/home", json.dumps({"dev": "usb:COM99", "expected_epoch": 0}).encode())
    t.eq(status, 401, "fenced HOME requires authentication")
    t.eq(sum(command == "HOME" for _, command in fake_serial.wire), before,
         "unauthorized fenced HOME never reaches the module")
    F.login(base)
