"""Parse the shipped Gacha/TV scripts, including the separate motion helper."""
import re
import shutil
import subprocess

import qc as F

AREA = "design"
TITLE = "Gacha and TV ship syntactically valid browser scripts"


def run(t):
    node = shutil.which("node")
    if not t.ok(bool(node), "Node is available for JavaScript parsing"):
        return
    for page in ("apps/gacha/index.html", "apps/tv/index.html"):
        html = (F.CODE / page).read_text(encoding="utf-8")
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I)
        for i, script in enumerate(scripts):
            if not script.strip():
                continue
            r = subprocess.run([node, "--check", "-"], input=script, text=True,
                               capture_output=True, encoding="utf-8", timeout=10)
            t.ok(r.returncode == 0, "%s inline script %d parses" % (page, i), r.stderr[-800:])
    p = F.CODE / "apps/gacha/motion.js"
    r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True, timeout=10)
    t.ok(r.returncode == 0, "Gacha motion helper parses", r.stderr[-800:])
