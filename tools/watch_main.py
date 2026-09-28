#!/usr/bin/env python3
"""Tell every agent, within seconds, that main changed outside promote.py (A0-23).

    set MICE_AGENT=claude:09171042-a7db
    python tools/watch_main.py            run in the background; one per machine

User 2026-09-16: *other agents must learn of a shared-file change the moment it
happens*. A direct write to main is not stopped - nothing here can stop another
process - it is announced in BRIDGE as MAIN-WRITE, naming any staging tree that
holds its own unpromoted edit of the same file (a collision).

A promote logs what it writes to .staging-landed.jsonl before copying, so a
land is matched by path AND hash and is never reported. Honest limits: a write
reverted between two scans is missed; a metadata-preserving edit waits for the
next full hash sweep (SWEEP seconds).
"""
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REAL = HERE.parent if HERE.name.startswith(".staging") else HERE

POLL, SETTLE, SWEEP = 2.0, 3.0, 300.0
MAX_NAMES = 20


def load_promote(main):
    spec = importlib.util.spec_from_file_location("watch_promote", str(HERE / "promote.py"))
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    P.MAIN = main
    return P


def scan(P, root, previous):
    """{path: (mtime_ns, size)}. A file that cannot be stat'ed keeps its old row."""
    out = {}
    for rel in P.walk(root):
        key = rel.as_posix()
        try:
            st = (root / rel).stat()
            out[key] = (st.st_mtime_ns, st.st_size)
        except OSError:
            if key in previous:
                out[key] = previous[key]
    return out


def read_hash(P, path):
    """sha256, None when absent, "?" when it exists but cannot be read yet."""
    for _ in range(3):
        try:
            return P.file_hash(path)
        except OSError:
            time.sleep(0.2)
    return "?"


def landed(P, main):
    """Every (path, hash) a promote wrote."""
    seen = set()
    try:
        lines = (main / P.LANDED_LOG).read_text(encoding="utf-8").splitlines()
    except OSError:
        return seen
    for line in lines:
        try:
            seen.update(json.loads(line).get("files", {}).items())
        except (ValueError, AttributeError):
            continue
    return seen


def trees(P, main):
    """Working copies with a base record: the listed ones and any .staging* folder."""
    found = set()
    listed = main / P.TREES_LIST
    if listed.is_file():
        found.update(Path(x) for x in listed.read_text(encoding="utf-8").split("\n") if x.strip())
    found.update(d for d in main.glob(".staging*") if d.is_dir())
    return sorted(t for t in found if (t / P.BASE_NAME).is_file())


def collisions(P, main, key, main_hash):
    """Trees whose own copy of `key` was edited AND differs from main's new one.
    A tree with no base entry for the file is unknown, never a collision."""
    hits = []
    for tree in trees(P, main):
        b = P.load_base(tree).get(key)
        if b is None:
            continue
        s = P.file_hash(tree / key)
        if s is not None and s != b and s != main_hash:
            hits.append(tree.name)
    return hits


class Watcher:
    def __init__(self, P, main):
        self.P, self.main = P, main
        self.rows = scan(P, main, {})
        self.hashes = {k: read_hash(P, main / k) for k in self.rows}
        self.pending = {}           # path -> new hash (None = deleted)
        self.last_change = 0.0
        self.last_sweep = time.time()

    def _note(self, key, now):
        h = read_hash(self.P, self.main / key)
        if h == "?":
            return                  # locked mid-write; the next scan retries
        if h != self.hashes.get(key):
            self.hashes[key] = h
            self.pending[key] = h
            self.last_change = now
        if h is None:
            self.hashes.pop(key, None)

    def step(self, now=None, sweep=False):
        """One poll. Returns the BRIDGE lines it announced, or None."""
        now = time.time() if now is None else now
        rows = scan(self.P, self.main, self.rows)
        moved = {k for k in rows.keys() | self.rows.keys() if rows.get(k) != self.rows.get(k)}
        if sweep or now - self.last_sweep >= SWEEP:
            moved |= set(rows)
            self.last_sweep = now
        self.rows = rows
        for key in sorted(moved):
            self._note(key, now)
        if self.pending and now - self.last_change >= SETTLE:
            return self.announce()
        return None

    def announce(self):
        promoted = landed(self.P, self.main)
        direct = {k: h for k, h in self.pending.items() if (k, h) not in promoted}
        if not direct:
            self.pending.clear()
            return None
        names = sorted(direct)
        shown = ", ".join(("%s (deleted)" % k) if direct[k] is None else k
                          for k in names[:MAX_NAMES])
        if len(names) > MAX_NAMES:
            shown += " (+%d more)" % (len(names) - MAX_NAMES)
        lines = ["Tree: %s (main, written directly - not through promote.py)" % self.main,
                 "Files: " + shown]
        clash = []
        for k in names:
            hit = collisions(self.P, self.main, k, direct[k])
            if hit:
                clash.append("%s in %s" % (k, ", ".join(hit)))
        if clash:
            lines.append("COLLISION - staging holds its own edit of: " + "; ".join(clash[:MAX_NAMES]))
        lines.append("Next: the writer says who in BRIDGE. A tree listed above merges "
                     "main's version, then promote.py --accept-main PATH.")
        if self.P.bridge("MAIN-WRITE", lines) is False:
            return None             # BRIDGE busy: pending stays, retried next poll
        self.pending.clear()
        return lines


def single_instance(main):
    """Lock dir holding pid + process start time. A dead or different process
    with that pid is proof of a stale lock; age alone never is."""
    import psutil
    lock = main / ".staging-watch.lock"
    me = psutil.Process()
    token = {"pid": me.pid, "created": me.create_time(), "token": uuid.uuid4().hex,
             "agent": os.environ.get("MICE_AGENT", "")}
    try:
        lock.mkdir()
    except FileExistsError:
        try:
            other = json.loads((lock / "owner.json").read_text(encoding="utf-8"))
            if psutil.Process(other["pid"]).create_time() == other["created"]:
                print("already watching: pid %s (%s)" % (other["pid"], other.get("agent")))
                return None
        except (psutil.NoSuchProcess, OSError, ValueError, KeyError, TypeError):
            pass
        print("previous watcher is gone - taking over its lock")
    (lock / "owner.json").write_text(json.dumps(token), encoding="utf-8")
    return lock, token


def release(lock, token):
    try:
        if json.loads((lock / "owner.json").read_text(encoding="utf-8")).get("token") == token["token"]:
            (lock / "owner.json").unlink()
            lock.rmdir()
    except (OSError, ValueError):
        pass


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    held = single_instance(REAL)
    if held is None:
        return 0
    try:
        P = load_promote(REAL)
        w = Watcher(P, REAL)
        print("watching %s (%d files)" % (REAL, len(w.rows)), flush=True)
        while True:
            said = w.step()
            if said:
                print(time.strftime("%H:%M:%S"), said[1], flush=True)
            time.sleep(POLL)
    except KeyboardInterrupt:
        return 0
    finally:
        release(*held)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
