"""Promotion builds the checked tree, rejects stale proof, and protects concurrent edits."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest import mock

AREA = "tooling"
TITLE = "promotion builds before QC and copies only verified inputs"


def _write(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source.encode("utf-8"))


def _load():
    spec = importlib.util.spec_from_file_location(
        "pipeline_promote", Path(__file__).resolve().parents[2] / "promote.py")
    module = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(module)
    return module


def _fixture(root, builder=""):
    main, stage = root / "main", root / "stage"
    main.mkdir(parents=True)
    stage.mkdir()
    _write(stage / "tools/build_web.py", builder or "from pathlib import Path\nPath('web.js').write_bytes(b'built')\n")
    _write(stage / "qc/run_qc.py", '''import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def tree_fingerprint():
    h = hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name != '.qc-receipt.json' and '__pycache__' not in p.parts:
            h.update(str(p.relative_to(ROOT)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()
if __name__ == '__main__':
    (ROOT / 'qc-ran').write_bytes(b'yes')
    (ROOT / '.qc-receipt.json').write_text(json.dumps(dict(
        full=True, passed=1, failed=0, tree=tree_fingerprint())), encoding='utf-8')
    print('QC PASS 1 passed, 0 failed', flush=True)
''')
    return main, stage


def run(t):
    p = _load()
    with tempfile.TemporaryDirectory(prefix="mice-promote-test-") as folder:
        root = Path(folder)
        p.MAIN, p.STAGING = _fixture(root / "failed", "raise SystemExit(9)\n")
        with mock.patch.object(p, "_plan"), contextlib.redirect_stdout(io.StringIO()):
            code = p.main(["--staging", str(p.STAGING)])
        t.eq(code, 1, "failed web build refuses promotion")
        t.ok(not (p.STAGING / "qc-ran").exists(), "failed build never starts QC")
        t.ok(not list(p.MAIN.iterdir()), "failed build copies nothing and releases lock")

        p.MAIN, p.STAGING = _fixture(root / "generated")
        with mock.patch.object(p, "_plan"), contextlib.redirect_stdout(io.StringIO()):
            code = p.main(["--staging", str(p.STAGING)])
        t.eq(code, 0, "synthetic exact-tree gate promotes successfully")
        t.ok((p.MAIN / "web.js").is_file(), "newly generated web output is promoted")
        t.eq((p.MAIN / "web.js").read_bytes() if (p.MAIN / "web.js").exists() else None,
             b"built", "promoted output contains builder result")

        receipt_path = p.STAGING / ".qc-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for field, value in (("full", False), ("full", 1), ("failed", 1),
                             ("failed", False), ("passed", 0), ("passed", True),
                             ("tree", "")):
            bad = dict(receipt, **{field: value})
            _write(receipt_path, json.dumps(bad))
            t.ok(not p.already_green(p.STAGING), "receipt rejects %s=%r" % (field, value))
        _write(receipt_path, json.dumps(receipt))
        with mock.patch.object(p.subprocess, "run", return_value=subprocess.CompletedProcess(
                [], 1, stdout=receipt["tree"] + "\n", stderr="failed")):
            t.ok(not p.already_green(p.STAGING), "matching stdout from failed fingerprint is rejected")
        with mock.patch.object(p.subprocess, "run", side_effect=subprocess.TimeoutExpired([], 300)):
            t.ok(not p.already_green(p.STAGING), "fingerprint timeout rejects receipt")

        lock = p.MAIN / ".staging-promotion.lock"
        lock.mkdir()
        _write(lock / "owner.txt", "another-session")
        for flags in ([], ["--check"]):
            with mock.patch.object(p, "build_web") as build, contextlib.redirect_stdout(io.StringIO()):
                code = p.main(flags + ["--staging", str(p.STAGING)])
            t.eq(code, 1, "existing mutex rejects %s" % (flags or "promotion"))
            t.ok(not build.called, "mutex conflict starts no builder")
        t.eq((lock / "owner.txt").read_text(), "another-session", "foreign lock ownership stays intact")

        p.MAIN, p.STAGING = _fixture(root / "main-edit")
        _write(p.MAIN / "web.js", "old")
        def concurrent_gate(*args, **kwargs):
            _write(p.MAIN / "web.js", "concurrent edit")
            return True
        with mock.patch.object(p, "_plan"), mock.patch.object(p, "already_green", side_effect=[False, True]), \
                mock.patch.object(p, "run_qc", side_effect=concurrent_gate), \
                contextlib.redirect_stdout(io.StringIO()):
            code = p.main(["--staging", str(p.STAGING)])
        t.eq(code, 1, "main target edited during gate refuses promotion")
        t.eq((p.MAIN / "web.js").read_bytes(), b"concurrent edit", "main concurrent edit survives")

        p.MAIN, p.STAGING = _fixture(root / "stale-proof")
        with mock.patch.object(p, "_plan"), mock.patch.object(p, "already_green", side_effect=[False, False]), \
                mock.patch.object(p, "run_qc", return_value=True), contextlib.redirect_stdout(io.StringIO()):
            code = p.main(["--staging", str(p.STAGING)])
        t.eq(code, 1, "QC exit zero without exact receipt refuses promotion")
        t.ok(not list(p.MAIN.iterdir()), "stale receipt copies nothing")

        tree = root / "pruning"
        for name in ("keep.py", ".staging-other/nested/hidden.py", "node_modules/nested/hidden.js"):
            _write(tree / name, "source")
        visited = []
        real_walk = os.walk
        def traced_walk(*args, **kwargs):
            for row in real_walk(*args, **kwargs):
                visited.append(Path(row[0]).relative_to(tree).as_posix())
                yield row
        with mock.patch.object(p.os, "walk", side_effect=traced_walk):
            found = list(p.walk(tree))
        t.eq(found, [Path("keep.py")], "walk excludes skipped files")
        t.eq(visited, ["."], "walk prunes skipped subtrees before traversal")
