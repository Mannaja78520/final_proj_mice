"""What a handed-off worker must finish: the repo, its task files, and when it is done.

The handoff contract is the repo's own (HANDOFF.md + one file per task in
handoff/tasks/), so this only has to name WHICH task files. Order of guesses:
task files the stopped session mentioned, then files owned by that AI and
touched recently, then any task file touched recently.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import time

TASK_REF = re.compile(r"handoff[/\\]+tasks[/\\]+([\w.\-]+\.md)")
DONE = re.compile(r"(?im)^(?:Status|State):\s*done\b")
TAIL = 400_000  # bytes of a transcript read for task names / last words


def repo_of(cwd, fallback):
    if cwd and os.path.isdir(cwd):
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return os.path.normpath(r.stdout.strip())
    return str(fallback)


def _tail(path):
    try:
        with open(path, "rb") as f:
            f.seek(max(0, os.path.getsize(path) - TAIL))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def last_words(source):
    """The stopped AI's last real sentence, so the next one knows the context."""
    for line in reversed(_tail(source).splitlines()):
        if '"assistant"' not in line or "<synthetic>" in line:
            continue
        try:
            msg = json.loads(line).get("message") or {}
        except ValueError:
            continue
        for c in reversed(msg.get("content") or []):
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip():
                return " ".join(c["text"].split())[:600]
    return "(not found)"


def find_tasks(repo, task_glob, source, provider, scope_hours):
    files = sorted(glob.glob(os.path.join(repo, task_glob)))
    by_name = {os.path.basename(f): f for f in files}
    named = [by_name[n] for n in dict.fromkeys(TASK_REF.findall(_tail(source))) if n in by_name]
    if named:
        return named
    recent = [f for f in files if time.time() - os.path.getmtime(f) < scope_hours * 3600]
    owned = [f for f in recent if re.search(r"(?im)^Owner:.*%s" % re.escape(provider), _read(f))]
    return owned or recent


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def open_tasks(tasks):
    return [t for t in tasks if os.path.isfile(t) and not DONE.search(_read(t))]


def snapshot(repo, tasks):
    """Changes when the worker did anything: task files or the repo's HEAD."""
    h = hashlib.sha1()
    for t in tasks:
        h.update(_read(t).encode("utf-8", "replace"))
    for args in (["rev-parse", "HEAD"], ["status", "--porcelain"]):  # Codex cannot commit
        r = subprocess.run(["git", "-C", repo] + args, capture_output=True, text=True)
        h.update(r.stdout.encode())
    return h.hexdigest()
