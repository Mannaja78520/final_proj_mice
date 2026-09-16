"""The Voice app answers through the hub proxy, and says plainly when off.

A20-5, the shell. The hub never imports torch: /api/voice/* is FORWARDED to
apps/voice/service.py, a separate process grown from the llm/test.py
prototype (FAQ-first, model only on a miss). Three things must hold:

  1. helper not running -> an honest 503 that names what to start;
  2. helper running     -> health and asks pass through unchanged, including
                           the FAQ answer itself (the part that makes it
                           useful with no GPU at all);
  3. asking is GATED    - A20-10 will let an answer move a robot, so the same
                           login gate as every other command applies now.

This runs the REAL service subprocess in FAQ-only mode (llm switched off in
its config), so no heavy library is needed and the whole chain — service,
proxy, gate — is exercised for real.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the voice helper answers through the hub, or says plainly it is off"

# Two saved questions with EXACT expected text — the fuzzy match must return
# the saved answer verbatim, not a paraphrase.
FAQS = {"faqs": [
    {"questions": ["what time do you open", "opening hours"],
     "answer": "We open at eight and close at five."},
    {"questions": ["where is the toilet"],
     "answer": "Down the hall, on the left."},
]}
Q_OPEN = "what time do you open"
A_OPEN = "We open at eight and close at five."
Q_MISS = "tell me a joke about a robot"
# A20-8: a GREY-ZONE match asks again instead of guessing. The thresholds are
# built AROUND this question's measured score, so the fixture stays in the
# band no matter what that score turns out to be.
Q_NEAR = "what time does it open"
SCORE_NEAR = max(SequenceMatcher(None, Q_NEAR.lower(), q.lower()).ratio()
                 for item in FAQS["faqs"] for q in item["questions"])

PORT = F._free_port()


def run(t):
    import subprocess

    # The hub reads WHERE its voice config lives at import time, but reads the
    # FILE fresh on every request. One temp file stands in for the real one:
    # it names the service address from the start, so phase 1 is the case a
    # person actually hits — configured, but not yet started.
    tmp = Path(tempfile.mkdtemp(prefix="mice_voice_qc_"))
    cfg = tmp / "voice.json"
    faq = tmp / "qa_data.json"
    faq.write_text(json.dumps(FAQS, ensure_ascii=False), encoding="utf-8")
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % PORT,
        # Q_NEAR must land BETWEEN the two: answered above, asked-again in
        # the band, model only below.
        "faqThreshold": SCORE_NEAR + 0.02,
        "faqAskAgain": SCORE_NEAR - 0.02,
        "stt": {"enabled": False}, "llm": {"enabled": False},
        "tts": {"enabled": False},
    }), encoding="utf-8")
    os.environ["MICE_VOICE_CONFIG"] = str(cfg)

    base, _main = F.start_hub()
    cookie = F.login(base)

    # ---- 1: nothing listening -> words that name the fix --------------
    st, body = F.get(base + "/api/voice/health")
    t.eq(st, 503, "helper off: the proxy says so, not an empty error")
    err = (json.loads(body) or {}).get("error", "")
    t.ok("service.py" in err and "voice" in err.lower(),
         "...and names what to start", err[:120])

    # ---- boot the REAL helper -----------------------------------------
    svc_py = F.CODE / "apps" / "voice" / "service.py"
    svc_log = open(tmp / "service.log", "wb")          # why-it-died evidence
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.Popen(
        [sys.executable, str(svc_py), "--config", str(cfg),
         "--faq", str(faq), "--port", str(PORT)],
        stdout=svc_log, stderr=subprocess.STDOUT, env=env)
    try:
        deadline = time.time() + 15
        up = False
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:%d/health" % PORT, timeout=2) as r:
                    if json.loads(r.read()).get("ok"):
                        up = True
                        break
            except Exception:                       # noqa: BLE001
                time.sleep(0.3)
        if not t.ok(up, "the real voice helper came up (FAQ-only mode)",
                    svc_log.name):
            return

        # ---- 2: through the hub, unchanged ----------------------------
        st, body = F.get(base + "/api/voice/health")
        svc_log.flush()
        h = json.loads(body)
        t.eq(st, 200, "health passes through the hub")
        t.ok(h.get("ok") and "saved answers" in h.get("parts", {}).get("faq", ""),
             "the helper's own report survives the hop",
             body[:150] + " || poll=%r log: %s"
             % (proc.poll(), Path(svc_log.name).read_text(errors="replace")[:400]))

        req = urllib.request.Request(
            base + "/api/voice/ask",
            data=json.dumps({"text": Q_OPEN}).encode(), method="POST")
        req.add_header("Cookie", cookie)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            ans = json.loads(r.read())
        t.eq(ans.get("answer"), A_OPEN,
             "a saved question returns its answer VERBATIM from the FAQ")
        t.eq(ans.get("source"), "faq", "...marked as coming from the FAQ")

        # ---- 3: asking is gated, like anything else that may move a rig -
        F.logout_qc()
        st, body = F.post(base + "/api/voice/ask",
                          json.dumps({"text": Q_OPEN}).encode())
        got = json.loads(body)
        t.eq(st, 401, "asking without logging in is refused")
        t.ok(got.get("need_login"), "...with the login request, not silence",
             body[:120])
        F.login(base)

        # ---- 4: a miss with the model off says so honestly -------------
        req = urllib.request.Request(
            base + "/api/voice/ask",
            data=json.dumps({"text": Q_MISS}).encode(), method="POST")
        req.add_header("Cookie", cookie)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            miss = json.loads(r.read())
        t.ok(not miss.get("ok") and "model" in (miss.get("error") or "").lower(),
             "no saved answer fits AND the model is off: it says so",
             json.dumps(miss)[:120])

        # ---- 5: the grey zone asks again instead of guessing (A20-8) ----
        req = urllib.request.Request(
            base + "/api/voice/ask",
            data=json.dumps({"text": Q_NEAR}).encode(), method="POST")
        req.add_header("Cookie", cookie)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as r:
            near = json.loads(r.read())
        t.ok(near.get("repeat") and not near.get("ok"),
             "a near match ASKS AGAIN, marked as a repeat - never answered",
             json.dumps(near, ensure_ascii=False)[:150])
        t.ok("say it again" in (near.get("error") or ""),
             "...in words a visitor can act on",
             json.dumps(near, ensure_ascii=False)[:150])
        t.ok(abs(near.get("score", 0) - SCORE_NEAR) < 0.02,
             "...and carries its real similarity score",
             "%s vs measured %.3f" % (near.get("score"), SCORE_NEAR))
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
        proc.terminate()
