"""Conversation captures a full turn, stops cleanly, and starts one correct voice.

A45-18: the old eight-second recording cap clipped a visitor who waited
before speaking. Virtual time runs the real page through 30-second speech,
pauses, microphone loss and Stop/Start, then races slow synthesis against
an installed voice. These are browser/robot fakes, not microphone timings.
"""
import json
import shutil
import subprocess

import qc as F

AREA = "tools"
TITLE = "conversation preserves long speech and owns every microphone and voice"


def run(t):
    node = shutil.which("node")
    if not node:
        t.give_up("node is not installed")
    r = subprocess.run([node, str(F.CODE / "qc/data/voice_conversation.mjs"),
                        str(F.CODE / "apps/voice/app.js")], capture_output=True,
                       encoding="utf-8", errors="replace", timeout=45)
    lines = [line for line in r.stdout.splitlines() if line.startswith("[")]
    if not t.ok(lines, "the real page completes the conversation scenarios",
                (r.stdout + r.stderr)[-1400:]):
        return
    for result in json.loads(lines[-1]):
        t.ok(result["pass"], result["label"], repr(result.get("detail", "")))
    t.eq(r.returncode, 0, "all capture, cancellation and speech race scenarios pass")
