"""The voice SETTINGS screens - a designer teaches the rig by clicking.

A20-12: apps/voice/index.html gains an Answers / Voice and language /
Words it gets wrong / Advanced surface over two stores that live on the
brain PC:

  * GET /api/voice/{config,faq} reads them - open, like every read;
  * POST writes them - GATED like /api/settings, because saving rewrites
    what the rig answers and how it listens;
  * and NO RESTART: the helper stats voice.json on every request
    (Brain.maybe_reload), drops a cached STT/LLM model whose id changed,
    and qa_data.json was already re-read per call.

Everything is driven through the real hub proxy against a real helper
subprocess, so what passes here is what a browser does.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "settings a designer can click, gated like everything that saves"


def _helper(tmp):
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % F._free_port(),
        "faqThreshold": 0.75, "faqAskAgain": 0,
        "stt": {"enabled": False},
        "llm": {"enabled": False}, "tts": {"enabled": False},
    }), encoding="utf-8")
    faq = tmp / "qa.json"
    faq.write_text('{"faqs": []}', encoding="utf-8")
    port = json.loads(cfg.read_text(encoding="utf-8"))["service"].rsplit(":", 1)[1]
    log = open(tmp / "svc.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--faq", str(faq), "--port", port],
        stdout=log, stderr=subprocess.STDOUT)
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            if json.loads(F.get("http://127.0.0.1:%s/health" % port)[1]).get("ok"):
                break
        except Exception:                       # noqa: BLE001
            time.sleep(0.3)
    return proc, cfg, faq


def _page():
    return (F.CODE / "apps" / "voice" / "index.html").read_text(
        encoding="utf-8", errors="replace")


def _raw_post(url, body):
    """POST with NO session - start_hub logs itself in, and its cookie rides
    on every F.post, which would make every gate look open."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def run(t):
    base, _main = F.start_hub()
    tmp = Path(tempfile.mkdtemp(prefix="mice_set_qc_"))
    os.environ["MICE_VOICE_CONFIG"] = str(tmp / "voice.json")
    proc, cfg, faq = _helper(tmp)
    try:
        # ---- 1: reading open, saving gated -------------------------------
        st, body = F.get(base + "/api/voice/config")
        t.ok(st == 200 and json.loads(body).get("ok"),
             "reading the voice store needs no login")
        st, _ = F.get(base + "/api/voice/faq")
        t.eq(st, 200, "...and neither does reading the answers")
        t.eq(_raw_post(base + "/api/voice/config", b'{"config": {}}'), 401,
             "saving the voice store IS gated, like /api/settings")
        t.eq(_raw_post(base + "/api/voice/faq", b'{"faqs": []}'), 401,
             "...and so is saving the answers")

        # ---- 2: a save lands on disk and reaches the RUNNING helper ------
        F.login(base)
        new_cfg = json.loads(cfg.read_text(encoding="utf-8"))
        new_cfg["faqThreshold"] = 0.6
        new_cfg["stt"] = {"enabled": True, "model": "base",
                          "language": "", "languages": {}}
        r = F.post(base + "/api/voice/config",
                   json.dumps({"config": new_cfg}).encode())
        t.ok(json.loads(r[1]).get("ok"), "a logged-in save goes through",
             r[1][:120])
        on_disk = json.loads(cfg.read_text(encoding="utf-8"))
        t.eq(on_disk.get("faqThreshold"), 0.6,
             "the save really rewrote the brain PC's file")
        st, body = F.get(base + "/api/voice/config")
        got = json.loads(body)["config"]
        t.eq(got.get("faqThreshold"), 0.6,
             "the running helper serves the NEW value - no restart")

        # ---- 3: answers round-trip, wrapped right on disk -----------------
        r = F.post(base + "/api/voice/faq", json.dumps({"faqs": [
            {"questions": ["where is the toilet"], "answer": "Left, then right."},
        ]}).encode())
        t.ok(json.loads(r[1]).get("ok"), "an answer saves through the proxy")
        wrapped = json.loads(faq.read_text(encoding="utf-8"))
        t.ok(isinstance(wrapped.get("faqs"), list)
             and wrapped["faqs"][0]["answer"].startswith("Left"),
             "...and lands as {faqs: [...]} - the shape every reader expects",
             faq.read_text(encoding="utf-8")[:100])
        got = json.loads(F.get(base + "/api/voice/faq")[1])
        t.eq(len(got["faqs"]), 1, "the saved answer comes back to the page")

        # ---- 4: the page carries the designer's controls ------------------
        p = _page()
        t.contains(p, "/api/voice/config", "the page loads and saves the store")
        t.contains(p, "/api/voice/faq", "...and the answers")
        t.contains(p, "/api/list?kind=sequences",
                   "moves come from a dropdown of sequences that exist")
        t.contains(p, "Most accurate",
                   "the listening model speaks designer words, not ids")
        t.contains(p, "Show technical details",
                   "advanced hides behind the same switch as the hub's")
        t.ok("No answers yet" in p,
             "the answers section says what its empty state is")

        # ---- 5: a broken saved address ANSWERS, it does not hang ----------
        # urllib raises ValueError on an address with no scheme (the real
        # shape: somebody typed the brain PC's bare IP) while building the
        # request; built outside the try, that killed the request thread and
        # the page waited for ever with no word.
        broken = json.loads(cfg.read_text(encoding="utf-8"))
        broken["service"] = "192.168.137.1"          # an IP, no scheme
        cfg.write_text(json.dumps(broken), encoding="utf-8")
        st, body = F.get(base + "/api/voice/config")
        t.eq(st, 500, "a helper address with no scheme is refused, not hung")
        t.ok("not usable" in body and "Voice tab" in body,
             "...and it names the setting and where to fix it", body[:120])
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
        proc.terminate()
