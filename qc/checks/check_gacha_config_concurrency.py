"""A status read and config save share one lock, including the open file handle."""
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

AREA = "gacha"
TITLE = "Concurrent prize config read/save"
SLOW = False


class ObservedLock:
    """Expose the writer's first lock attempt without relying on a timing sleep."""

    def __init__(self):
        self.lock = threading.RLock()
        self.probed = threading.Event()
        self.writer_acquired = None

    def __enter__(self):
        if threading.current_thread().name == "config-writer":
            acquired = self.lock.acquire(blocking=False)
            self.writer_acquired = acquired
            self.probed.set()
            if not acquired:
                self.lock.acquire()
        else:
            self.lock.acquire()
        return self

    def __exit__(self, *exc):
        self.lock.release()


def run(t):
    from main_python.gacha import Gacha

    with tempfile.TemporaryDirectory(prefix="qc_gacha_cfg_") as box:
        cfg = Path(box) / "config.json"
        cfg.write_text(json.dumps({"event": {"name": "before", "open": False}}), encoding="utf8")
        gacha = Gacha(cfg, Path(box) / "data", lambda *a: None, lambda *a: None)
        gacha.lock = ObservedLock()
        opened, release = threading.Event(), threading.Event()
        original_read = Path.read_text
        result, errors = {}, []

        def read_text(path, *args, **kwargs):
            if path == cfg and threading.current_thread().name == "config-reader":
                # Hold an actual file handle in cfg()->registry.load()->read_text.
                with path.open("r", *args, **kwargs) as stream:
                    data = stream.read()
                    opened.set()
                    if not release.wait(10):
                        raise TimeoutError("reader release watchdog")
                    return data
            return original_read(path, *args, **kwargs)

        def read():
            try:
                result["read"] = gacha.cfg()["event"]["name"]
            except Exception as exc:
                errors.append(repr(exc))

        def write():
            try:
                gacha.save_cfg({"event": {"name": "after"}})
            except Exception as exc:
                errors.append(repr(exc))

        reader = threading.Thread(target=read, name="config-reader", daemon=True)
        writer = threading.Thread(target=write, name="config-writer", daemon=True)
        with patch.object(Path, "read_text", read_text):
            reader.start()
            try:
                t.ok(opened.wait(10), "actual config read holds its file handle")
                writer.start()
                t.ok(gacha.lock.probed.wait(10), "save attempted the shared lock")
                t.eq(gacha.lock.writer_acquired, False,
                     "writer waits for the status reader before replacing config")
            finally:
                release.set()
                reader.join(10)
                if writer.ident is not None:
                    writer.join(10)
        t.ok(not reader.is_alive() and not writer.is_alive(), "both config threads finish")
        t.eq(errors, [], "read and save complete without file sharing errors")
        t.eq(result.get("read"), "before", "reader received a coherent previous config")
        t.eq(gacha.cfg()["event"]["name"], "after", "completed save is readable in full")
