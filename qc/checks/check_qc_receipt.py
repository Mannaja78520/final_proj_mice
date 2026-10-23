"""A receipt ignores generated PC output but still rejects changed source inputs."""
import importlib.util
from pathlib import Path
import tempfile

AREA = "tooling"
TITLE = "QC receipts distinguish runtime output from checked source"


def run(t):
    spec = importlib.util.spec_from_file_location(
        "receipt_runner", Path(__file__).resolve().parents[1] / "run_qc.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    with tempfile.TemporaryDirectory(prefix="mice-receipt-") as folder:
        runner.CODE = Path(folder)
        source = runner.CODE / "main.py"
        source.write_bytes(b"source = 1\n")
        baseline = runner.tree_fingerprint()
        for rel in (".local/voice/questions.csv", "qc/_urdf_real.json",
                    "scratch/continue-urdf-1023/full-exit.txt"):
            output = runner.CODE / rel
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"generated one\n")
            t.eq(runner.tree_fingerprint(), baseline, rel + " creation is runtime output")
            output.write_bytes(b"generated two\n")
            t.eq(runner.tree_fingerprint(), baseline, rel + " rewrite is runtime output")
            output.unlink()
            t.eq(runner.tree_fingerprint(), baseline, rel + " removal is runtime output")
        for rel in ("main.py", "config/voice.json", "qc/data/fixture.json",
                    "handoff/tasks/current.md", "qc/other.json"):
            checked = runner.CODE / rel
            checked.parent.mkdir(parents=True, exist_ok=True)
            before = runner.tree_fingerprint()
            checked.write_bytes(b"checked input one\n")
            first = runner.tree_fingerprint()
            t.ok(first != before, rel + " invalidates stale proof", "source/config/test inputs stay hashed")
            checked.write_bytes(b"checked input two\n")
            second = runner.tree_fingerprint()
            t.ok(second != first, rel + " edit invalidates stale proof", "source/config/test inputs stay hashed")
            checked.unlink()
            t.ok(runner.tree_fingerprint() != second, rel + " removal invalidates stale proof", "source/config/test inputs stay hashed")
