"""Execute production page methods with isolated API/DOM fixtures for refusal and failure paths."""
import shutil
import subprocess
import qc as F

AREA = "hub"
TITLE = "all-page failures retain working controls, identity, results and drafts"


def run(t):
    node = shutil.which("node")
    if not t.ok(bool(node), "Node is available for production UI state regressions"):
        return
    for name in ("usability_hub.js", "usability_apps.js"):
        result = subprocess.run([node, str(F.CODE / "qc/data" / name)], cwd=F.CODE,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        for line in result.stdout.splitlines():
            if line.startswith(("PASS ", "FAIL ")):
                t.ok(line.startswith("PASS "), line[5:])
        t.eq(result.returncode, 0, name + " finishes all actual-method fixtures")
        if result.stderr:
            t.ok(result.returncode == 0, name + " has no unhandled fixture failure", result.stderr[-1200:])
