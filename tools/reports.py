#!/usr/bin/env python3
"""Print open reports in English for a work session.

A21-8: ANY LANGUAGE in, English for whoever fixes it. The hub translates
each report once, in the background, when it is filed; this tool shows that
stored translation, and only asks the voice helper live when a report has
none yet. A report it cannot translate prints as written, plus why - never
a guess at what somebody meant.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Overridable so a check can point it at a sandbox - same idea as MICE_VOICE_CONFIG.
REPORTS_DIR = Path(os.environ.get("MICE_REPORTS_DIR")
                   or (ROOT / "main_python" / "reports"))


def voice_base():
    """The helper's address from config/voice.json - the same file the hub reads."""
    path = os.environ.get("MICE_VOICE_CONFIG") or str(ROOT / "config" / "voice.json")
    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return ""
    return (cfg.get("service") or "").rstrip("/")


def translate_text(text):
    """English, or None - never a paraphrase of what we could not read."""
    if not text or all(ord(c) < 128 for c in text):
        return text
    base = voice_base()
    if not base:
        return None
    try:
        req = urllib.request.Request(
            base + "/translate",
            data=json.dumps({"text": text}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        # The model may load on this call; an explicit tool run can wait.
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = (data.get("text") or "").strip() if data.get("ok") else ""
        return out or None
    except Exception:
        return None


def main():
    if not REPORTS_DIR.is_dir():
        print("No reports directory found at", REPORTS_DIR)
        return 0

    open_reports = []
    for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status", "open") == "open":
                open_reports.append(data)
        except Exception:
            continue

    if not open_reports:
        print("No open reports.")
        return 0

    print(f"=== {len(open_reports)} open report(s) ===\n")
    for rep in open_reports:
        time_str = (rep.get("time") or "?").replace("T", " ")[:19]
        module = rep.get("module") or "no module"
        text = rep.get("text") or ""
        shown = rep.get("text_en")
        if not shown:
            shown = translate_text(text)
        print(f"[{time_str}] {module}")
        if shown:
            print(f"  {shown}")
        else:
            print(f"  {text}")
            print("  (not translated - start the voice helper, then run again)")
        print(f"  id: {rep.get('id', '?')}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
