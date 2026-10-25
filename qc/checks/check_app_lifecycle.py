"""Exercise actual shared UI and app methods together, with no external devices."""
import shutil
import subprocess
import qc as F

AREA = "tools"
TITLE = "shared App, preset saves, loaded row removal, themes and hidden polling agree"


def run(t):
    node = shutil.which("node")
    if not t.ok(bool(node), "Node is available for app integration fixtures"):
        return
    result = subprocess.run([node, str(F.CODE / "qc/data/app_lifecycle.js")],
                            cwd=str(F.CODE), capture_output=True, text=True,
                            encoding="utf-8", timeout=40)
    for line in result.stdout.splitlines():
        if line.startswith("PASS "):
            t.ok(True, line[5:])
        elif line.startswith("FAIL "):
            t.ok(False, line[5:])
    t.ok(result.returncode == 0, "production app integration fixtures finish", result.stderr[-1500:])
