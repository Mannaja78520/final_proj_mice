"""Start the local AI (Ollama) when something needs it, not at Windows login.

Asked 2026-11-20: "why does it have to be started by hand after a reboot? open
it when it is used - like when you test". So a provider in
config/voice_providers.json may carry `"autoStart": {"command": [...],
"ready": <url that answers when it is up>, "waitSeconds": 40}`; the first call
that needs it (the Load-the-AI button, a question, a test) finds it down,
starts it hidden, waits until it answers, and carries on. Nothing is
registered with Windows and nothing stays installed: close the hub's helper
and, if you want, end the Ollama process, and it comes back next time it is used.

The command is DATA (the repo's own tools/ollama_serve.py, so KV cache and
the models folder come from config/local_ai.json, one source). One start at a
time; after a failed start it does not retry for COOLDOWN seconds so a broken
install cannot freeze every answer for 40 s.
"""
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COOLDOWN = 60
SHORT = 0.3                                  # probe timeout when we only re-check
_lock = threading.Lock()
_failed_at = {}


def is_up(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:                      # noqa: BLE001 - down, refused, slow: all "not up"
        return False


def _python():
    # The hub exe is not a Python; fall back to the one on PATH.
    return "python" if getattr(sys, "frozen", False) else sys.executable


def wake(prov):
    """(up, why). Cheap when it is already up (one tiny GET) or has no autoStart."""
    cfg = prov.get("autoStart")
    if not cfg:
        return True, ""
    url = cfg["ready"]
    cooling = time.time() - _failed_at.get(url, 0) < COOLDOWN
    # Windows does not refuse a closed local port at once: the probe waits out its
    # whole timeout (measured 2026-11-21: 1.5 s for 127.0.0.1, 3.0 s for localhost).
    # So while we are in the cooldown after a failed start, and for the re-check
    # inside the lock, probe briefly: a server that is up answers in milliseconds.
    if is_up(url, SHORT if cooling else 1.5):
        return True, ""
    if cooling:
        return False, "the local AI did not start a minute ago; press Load the AI to try again"
    with _lock:
        if is_up(url, SHORT):
            return True, ""
        cmd = [_python() if c == "{python}" else c for c in cfg["command"]]
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        try:
            subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, creationflags=flags)
        except OSError as e:
            _failed_at[url] = time.time()
            return False, "could not start the local AI (%s)" % e
        end = time.time() + float(cfg.get("waitSeconds", 40))
        while time.time() < end:
            if is_up(url):
                return True, ""
            time.sleep(0.5)
        _failed_at[url] = time.time()
        return False, "the local AI did not answer within %d s" % int(cfg.get("waitSeconds", 40))
