"""A direct write to main is announced in BRIDGE within seconds; a promote is not.

Asked 2026-09-16 (A0-23): *in the realtime? like when you use the old file and
restore it, in realtime, so the problem already occur* - other agents must learn
of a shared-file change the moment it happens, not at their next promote.

Holds:
  * an edit made straight in main becomes one MAIN-WRITE entry naming the file;
  * a file a promote wrote (logged in .staging-landed.jsonl) is never reported;
  * a staging tree holding its own edit of that file is named as a COLLISION;
  * a touch that leaves the bytes alone says nothing;
  * a busy BRIDGE keeps the change pending instead of dropping it;
  * one watcher per machine: a live owner's lock is respected.
Driven in throwaway trees with a fake clock; the real BRIDGE is never touched.
"""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import qc as F


AREA = "tools"
TITLE = "watch_main announces direct writes to main, not promotes"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(t):
    W = _load("watch_main_under_test", F.CODE / "tools" / "watch_main.py")
    P = _load("watch_promote_under_test", F.CODE / "promote.py")

    main = Path(tempfile.mkdtemp(prefix="qc_watch_main_"))
    (main / "docs").mkdir()
    (main / "docs" / "BRIDGE.md").write_text("# bridge\n", encoding="utf-8")
    (main / "shared.js").write_text("v1", encoding="utf-8")
    (main / "other.js").write_text("v1", encoding="utf-8")
    P.MAIN = main
    stage = main / ".staging-qc"
    P.STAGING = stage
    P.init()
    t.ok((stage / P.BASE_NAME).is_file() and str(stage) in (main / P.TREES_LIST).read_text(encoding="utf-8"),
         "--init records the base and lists the tree", "")

    w = W.Watcher(P, main)
    bridge = lambda: (main / "docs" / "BRIDGE.md").read_text(encoding="utf-8")

    # staging edits shared.js; someone then writes it straight into main
    (stage / "shared.js").write_text("staging edit", encoding="utf-8")
    (main / "shared.js").write_text("direct edit", encoding="utf-8")
    os.utime(main / "shared.js", ns=(1, 1))
    t.ok(w.step(now=1000.0) is None, "nothing is said before the write settles", "")
    said = w.step(now=1010.0)
    log = bridge()
    t.ok(said is not None and "Event: MAIN-WRITE" in log and "shared.js" in log,
         "a direct write to main is announced in BRIDGE", log[-400:])
    t.ok("COLLISION" in log and ".staging-qc" in log,
         "and the staging tree holding its own edit is named", log[-400:])
    t.ok("other.js" not in log, "an untouched file is not named", log[-400:])

    # a touch with the same bytes is not news
    before = bridge()
    os.utime(main / "other.js", ns=(5, 5))
    w.step(now=1020.0)
    t.ok(w.step(now=1030.0) is None and bridge() == before,
         "a touch that leaves the bytes alone says nothing", "")

    # a promote's own write is matched by path and hash
    (main / "other.js").write_text("promoted", encoding="utf-8")
    with open(main / P.LANDED_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"files": {"other.js": P.file_hash(main / "other.js")}}) + "\n")
    w.step(now=1040.0)
    t.ok(w.step(now=1050.0) is None and bridge() == before,
         "a file a promote wrote is never reported as a direct write", bridge()[-300:])

    # busy BRIDGE: the change waits for the next poll
    (main / "other.js").write_text("direct again", encoding="utf-8")
    real_bridge = P.bridge
    P.bridge = lambda event, lines: False
    w.step(now=1060.0)
    t.ok(w.step(now=1070.0) is None and "other.js" in w.pending,
         "a busy BRIDGE keeps the change pending", w.pending)
    P.bridge = real_bridge
    t.ok(w.step(now=1080.0) is not None and "other.js" in bridge()[len(before):],
         "and it is announced once BRIDGE is free", bridge()[-300:])

    # a deletion is reported as one
    (main / "shared.js").unlink()
    w.step(now=1090.0)
    w.step(now=1100.0)
    t.ok("shared.js (deleted)" in bridge(), "a deletion is announced as a deletion", bridge()[-300:])

    # one watcher: a live owner (this process) keeps its lock
    held = W.single_instance(main)
    t.ok(held is not None, "the first watcher takes the lock", "")
    t.ok(W.single_instance(main) is None, "a second one leaves a live owner's lock alone", "")
    W.release(*held)
    t.ok(not (main / ".staging-watch.lock").exists(), "and the lock is released on exit", "")
