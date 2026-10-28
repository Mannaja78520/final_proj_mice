"""A late open cannot overtake its subsequent close or clobber a config save."""
import importlib.util
import json
import sys
import tempfile
import threading
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "an uncertain Gacha open finishes before close and concurrent config writes"


def run(t):
    source = F.CODE / "main_python"
    sys.path.insert(0, str(source))
    try:
        spec = importlib.util.spec_from_file_location("_qc_event_gacha", source / "gacha.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(source))
    with tempfile.TemporaryDirectory(prefix="mice_event_order_") as folder:
        root = Path(folder)
        cfg = root / "gacha.json"
        cfg.write_text(json.dumps({"machines": [{"id": "fixture", "dev": "fixture"}],
                                   "event": {"open": False}, "items": {}}), encoding="utf-8")
        entered, release = threading.Event(), threading.Event()
        closed, saved, close_started, save_started = (threading.Event() for _ in range(4))
        errors = []

        def send(_dev, command):
            if command == "GEVENT OPEN":
                entered.set()
                if not release.wait(4):
                    raise TimeoutError("fixture open was not released")
            if command == "GEVENT CLOSE":
                closed.set()
            return "OK event fixture"

        engine = module.Gacha(cfg, root / "data", send, lambda _name: "fixture")

        def guarded(fn, started=None, completed=None):
            if started:
                started.set()
            try:
                fn()
            except Exception as error:
                errors.append(str(error))
            finally:
                if completed:
                    completed.set()

        opening = threading.Thread(target=guarded, args=(lambda: engine.set_event(open_=True),))
        closing = threading.Thread(target=guarded, args=(lambda: engine.set_event(open_=False), close_started))
        writing = threading.Thread(target=guarded, args=(lambda: engine.save_cfg({"items": {"new": {"label": "Saved"}}}), save_started, saved))
        threads = [opening]
        try:
            opening.start()
            if not t.ok(entered.wait(2), "actual open reached the controlled board boundary"):
                return
            closing.start(); threads.append(closing)
            writing.start(); threads.append(writing)
            t.ok(close_started.wait(2) and save_started.wait(2), "close and config callers are dispatched while open is unfinished")
            t.ok(not closed.wait(0.2), "close cannot race ahead of an unfinished open")
            t.ok(not saved.wait(0.2), "config writes wait for the same event operation owner")
        finally:
            release.set()
            for thread in threads:
                thread.join(timeout=4)
        t.ok(all(not thread.is_alive() for thread in threads), "all event/config callers finish")
        t.eq(errors, [], "event/config ordering has no thread errors")
        t.ok(closed.is_set(), "the later close reached the controlled board boundary")
        current = engine.cfg()
        t.eq(current["event"]["open"], False, "the later close is the final persisted and board event state")
        t.eq(current["items"], {"new": {"label": "Saved"}}, "a late open does not overwrite a concurrent successful config save")
