"""The voice bench measures for real, and never fakes a number.

A20-6 asked for the bench BEFORE the accuracy work, so its own rule applies to
it too: a bench that silently reports nothing must not look like a result.
Four things must hold:

  1. cases.json is valid and carries >=25 questions with expected answers;
  2. against a REAL helper whose FAQ holds every case verbatim (one answer
     deliberately swapped), the typed run counts exactly 24/25 hits - the
     scoring compares what the rig SAID with what the case EXPECTS;
  3. the one swapped answer shows up as a MISS naming both strings;
  4. nothing listening -> exit non-zero with NOTHING was measured. Silence
     reading as success is the failure mode this whole task exists to kill.

Runs the real service subprocess in FAQ-only mode, like check_voice; no heavy
library needed because the bench falls back to typed text on this PC.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the voice bench scores a known run exactly and refuses fake numbers"

PORT = F._free_port()
DEAD = F.dead_port()           # held bound, so nothing CAN listen here
BENCH_PY = F.CODE / "apps" / "voice" / "bench" / "run_bench.py"


def bench(args, env_extra):
    p = subprocess.run(
        [sys.executable, str(BENCH_PY)] + args,
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", **env_extra))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def boot_helper(cfg, faq):
    svc_py = F.CODE / "apps" / "voice" / "service.py"
    log = open(Path(tempfile.mkdtemp(prefix="mice_vbench_")) / "svc.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, str(svc_py), "--config", str(cfg),
         "--faq", str(faq), "--port", str(PORT)],
        stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONUNBUFFERED="1"))
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/health" % PORT, timeout=2) as r:
                if json.loads(r.read()).get("ok"):
                    return proc
        except Exception:                           # noqa: BLE001
            time.sleep(0.3)
    proc.terminate()
    return None


def run(t):
    # ---- 1: the data file stands on its own ----------------------------
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry as R
    cases = R.load(F.CODE / "apps" / "voice" / "bench" / "cases.json")["cases"]

    rc, out = bench(["--selfcheck"], {})
    t.eq(rc, 0, "selfcheck passes with no dependencies installed")
    t.ok("%d cases ok" % len(cases) in out,
         "...and says how many cases it found (%d)" % len(cases), out[:150])

    # ---- build a temp config + FAQ from the bench's OWN cases ----------
    # Every question goes in verbatim (score 1.0, no fuzzy luck involved);
    # the LAST case gets a deliberately wrong answer, so the exact count is
    # len(cases) - 1 hits - a hand-checkable number.
    tmp = Path(tempfile.mkdtemp(prefix="mice_vbench_cfg_"))
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % PORT,
        "faqThreshold": 0.75,
        "stt": {"enabled": False}, "llm": {"enabled": False},
        "tts": {"enabled": False},
    }), encoding="utf-8")
    os.environ["MICE_VOICE_CONFIG"] = str(cfg)

    faqs = [{"questions": [c["text"]], "answer": c["expectAnswer"]}
            for c in cases]
    wrong_id = cases[-1]["id"]
    faqs[-1]["answer"] = "QC put this wrong answer here on purpose."
    faq = tmp / "qa_data.json"
    faq.write_text(json.dumps({"faqs": faqs}, ensure_ascii=False),
                   encoding="utf-8")

    proc = boot_helper(cfg, faq)
    try:
        if not t.ok(proc is not None, "the real helper came up (FAQ-only)"):
            return

        # ---- 2+3: the scored run --------------------------------------
        rc, out = bench(["--service", "http://127.0.0.1:%d" % PORT],
                        {"MICE_VOICE_CONFIG": str(cfg)})
        t.eq(rc, 0, "a measured run exits clean")
        want = "answer hits %d/%d" % (len(cases) - 1, len(cases))
        t.ok(want in out, "the hit count is EXACTLY right (%s)" % want, out[:400])
        t.ok("MISS " + wrong_id in out and "wrong answer here on purpose" in out,
             "the mismatched case is named with wanted vs got", out[:300])
        t.ok("not measured - speech-in is switched off" in out,
             "the error-rate half admits STT is off instead of inventing WER")
        t.ok("TYPED text" in out,
             "it says plainly that these runs were typed, not spoken")
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
        if proc:
            proc.terminate()

    # ---- 4: dead port -> no numbers, and it says so --------------------
    rc, out = bench(["--service", "http://127.0.0.1:%d" % DEAD],
                    {"MICE_VOICE_CONFIG": str(cfg)})
    t.ok(rc != 0, "measuring NOTHING exits non-zero, not 0")
    t.ok("NOTHING was measured" in out,
         "...and prints why the empty report is not evidence", out[:200])
