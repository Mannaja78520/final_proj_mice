"""Start an outside program (a partner) on this PC, hidden, and find where it is.

Asked 2026-09-16: *make Reconize open the app when click Open Reconize ...
run only main not dummy*, and: *reconize can change everytime because it the
outsource app ... we need to check and auto route everytime*. So:

* HOW to start it is read from THEIR start file (`start` in partners.json)
  on every press. Our `launch` list is only the fallback when that file
  cannot be read, so a new port or command on their side needs no edit here;
* WHERE it answers is read from what each part prints (uvicorn and vite both
  print their URL) and remembered in the temp folder. `live()` hands those
  addresses to the hub and the watcher, over the ones written in our config;
* a folder whose path holds a `refuseFolders` word (Dummy) is refused;
* a part still loading is never started twice (a face model takes ~15 s);
* logs go to the temp folder, never their folder - they update with
  `git checkout --detach` and a stray file there blocks it.
Measured 2026-09-16: vite answers on localhost (::1) only, so checks use the
URL exactly as printed - 127.0.0.1:5173 never answers.
"""
import json
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

_lock = threading.Lock()
_procs = {}          # (partner id, command) -> Popen
TMP = Path(tempfile.gettempdir())
ANSI = re.compile(r"\x1b\[[0-9;]*m")
URL = re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::\d+)?")
# start "title" cmd /k "cd backend && python -m uvicorn ..."
BAT_LINE = re.compile(r'^\s*start\s+"[^"]*"\s+cmd\s+/[kc]\s+"(.+)"\s*$', re.I)


def answers(url, timeout=1.0, below=500, json_only=False):
    """Somebody is listening: any status under `below` (300 = really healthy)."""
    if not url:
        return False
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if json_only and "json" not in (r.headers.get("Content-Type") or ""):
                return False
            return r.status < below
    except urllib.error.HTTPError as e:
        return e.code < below
    except Exception:                                        # noqa: BLE001
        return False


def refused(folder, words):
    low = str(folder).replace("\\", "/").lower()
    return next((w for w in words or [] if str(w).lower() in low), "")


def parts_of(entry):
    """[(cwd, command-line)] read from their start file, else our launch list."""
    folder = Path(entry.get("folder") or "")
    bat = folder / (entry.get("start") or "")
    out = []
    if entry.get("start") and bat.is_file():
        for line in bat.read_text(encoding="utf-8", errors="replace").splitlines():
            m = BAT_LINE.match(line)
            if not m:
                continue                     # echo, timeout, start chrome ...
            steps = [s.strip() for s in m.group(1).split("&&")]
            cwd = ""
            if steps and steps[0].lower().startswith("cd "):
                cwd = steps.pop(0)[3:].strip().strip('"')
            if steps:
                out.append((cwd, " && ".join(steps)))
    source = "their " + bat.name
    if not out:
        out = [(p.get("cwd") or "", " ".join(p.get("run") or []))
               for p in entry.get("launch") or []]
        source = "config/partners.json"
    # PHONES TOO (user 2026-09-17: the QR links on a phone did not open).
    # `addArgs` maps a piece of a command to flags added after it, so their
    # dev server listens on the network without editing their files.
    extra = entry.get("addArgs") or {}
    out = [(cwd, cmd + "".join(" " + flags for piece, flags in extra.items()
                               if piece in cmd and flags not in cmd))
           for cwd, cmd in out]
    return out, source


def _memo_path(pid):
    return TMP / ("mice_partner_%s.json" % pid)


def _memo(pid):
    try:
        return json.loads(_memo_path(pid).read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return {}


def _printed_url(log):
    try:
        text = ANSI.sub("", log.read_text(encoding="utf-8", errors="replace"))
    except Exception:                                        # noqa: BLE001
        return ""
    m = URL.search(text)
    return m.group(0).replace("0.0.0.0", "127.0.0.1") if m else ""


def live(pid, entry):
    """The entry with `open`/`api` replaced by where it really answered last."""
    got = dict(entry)
    urls = _memo(pid).get("urls") or {}
    health = entry.get("health") or "/api/health"
    for url in urls.values():
        # Vite answers ANY path with its page (200, html), so only JSON on the
        # health path means API - measured 2026-09-16.
        key = ("api" if answers(url.rstrip("/") + health, 0.5, 300, True)
               else "open")
        got[key] = url.rstrip("/")
    return got


def start(pid, entry):
    """Start whatever part is silent. Returns {ok, up, starting, ready, open, ...}."""
    name = entry.get("name") or pid
    folder = Path(entry.get("folder") or "")
    bad = refused(folder, entry.get("refuseFolders"))
    if bad:
        return {"ok": False, "error": "%s points at a %s copy - only the main "
                "one may be started. Fix folder in config/partners.json." % (name, bad)}
    if not folder.is_dir():
        return {"ok": False, "error": "the folder %s is not on this PC" % folder}
    parts, source = parts_of(entry)
    if not parts:
        return {"ok": False, "error": "no way to start %s: %s has no start "
                "lines and config/partners.json has no launch list" % (name, entry.get("start"))}

    hints = [p.get("check") or "" for p in entry.get("launch") or []]
    up, starting, logs = [], [], []
    with _lock:
        memo = _memo(pid)
        urls = memo.get("urls") or {}
        for i, (cwd, cmd) in enumerate(parts):
            label = cwd or "part %d" % (i + 1)
            log = TMP / ("mice_%s_%d.log" % (pid, i))
            key = (pid, cmd)
            proc = _procs.get(key)
            if proc is not None:
                found = _printed_url(log)
                if found:
                    urls[cmd] = found
            check = urls.get(cmd) or (hints[i] if i < len(hints) else "")
            if answers(check):
                up.append(label)
                continue
            if proc is not None and proc.poll() is None:
                starting.append(label)       # still loading - do not start twice
                continue
            if proc is not None:
                _procs.pop(key, None)
                return {"ok": False, "up": up, "log": str(log),
                        "error": "the %s part of %s stopped on its own (exit %s) "
                                 "- see the log" % (label, name, proc.returncode)}
            flags = 0
            if sys.platform == "win32":
                flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                out = open(log, "wb")
                _procs[key] = subprocess.Popen(
                    "cmd /c " + cmd if sys.platform == "win32" else cmd,
                    shell=sys.platform != "win32", cwd=str(folder / cwd),
                    stdout=out, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, creationflags=flags)
            except Exception as e:                           # noqa: BLE001
                return {"ok": False, "up": up,
                        "error": "could not start the %s part of %s (%s)" % (label, name, e)}
            starting.append(label)
            logs.append(str(log))
        memo["urls"] = urls
        try:
            _memo_path(pid).write_text(json.dumps(memo), encoding="utf-8")
        except Exception:                                    # noqa: BLE001
            pass
    ready = not starting
    return {"ok": True, "up": up, "starting": starting, "log": logs,
            "ready": ready, "from": source,
            "open": live(pid, entry).get("open") if ready else ""}
