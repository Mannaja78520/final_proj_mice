"""One brain, many mics - A20-11.

The helper LISTENS on whatever address `service` names in voice.json, so
one PC can be the brain for every hub at the venue: point the other hubs'
configs at it. Opting in is an edit, never a default - and because the
helper has no password, the wider bind must be a decision someone made on
purpose. This check proves the address in the URL is really the address
used: a helper pointed at this PC's LAN IP answers THERE and refuses
loopback, and says in its own log that it is shared.

Two guards come with the wider reach:
  * /ask now caps its body like /say already did - an unbounded
    Content-Length would let any WiFi peer make the helper allocate memory;
  * a saved answer's `module` is a robot NAME, matched case-insensitively
    against GET /api/modules/all at play time, so the robot can move
    between PCs. The matching lives in the page (which holds the login),
    so here it is checked as page glue plus the /api/modules/all contract
    the page matches against.
STOP stays ungated - someone watching an arm about to hit something must
never need to find a password first.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import fake_serial
import qc as F

AREA = "tools"
TITLE = "the brain shares by explicit address, and moves go to robots BY NAME"


def _cfg(tmp, url):
    c = tmp / "voice.json"
    c.write_text(json.dumps({
        "service": url, "faqThreshold": 0.75, "faqAskAgain": 0,
        "stt": {"enabled": False},
        "llm": {"enabled": False}, "tts": {"enabled": False},
    }), encoding="utf-8")
    return c


def _faq(tmp):
    f = tmp / "qa.json"
    f.write_text(json.dumps({"faqs": [
        {"questions": ["what is this"], "answer": "The Mice rig."},
    ]}, ensure_ascii=False), encoding="utf-8")
    return f


def _helper(cfg, faq, url):
    port = str(urlparse(url).port)
    log_path = cfg.parent / ("svc_%s.log" % port)   # two helpers, not one log
    log = open(log_path, "wb")
    proc = subprocess.Popen(
        # -u: a terminated process never flushes, and phase 3 asserts on
        # what the helper PRINTED - the log must land as it is printed.
        [sys.executable, "-u", str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--faq", str(faq), "--port", port],
        stdout=log, stderr=subprocess.STDOUT)
    return proc, port, log_path


def _wait_health(port, host="127.0.0.1", secs=15):
    deadline = time.time() + secs
    while time.time() < deadline:
        try:
            if json.loads(F.get(
                    "http://%s:%s/health" % (host, port))[1]).get("ok"):
                return True
        except Exception:                       # noqa: BLE001
            time.sleep(0.3)
    return False


def _lan_ip():
    """This PC's own LAN address, learned without sending a packet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return ""


def run(t):
    fake_serial.reset()
    base, _main = F.start_hub()
    tmp = Path(tempfile.mkdtemp(prefix="mice_multi_qc_"))
    try:
        # ---- 1: the contracts the page matches against -------------------
        mods = json.loads(F.get(base + "/api/modules/all")[1])
        t.ok(mods.get("ok") and isinstance(mods.get("modules"), list),
             "/api/modules/all answers with a module list",
             json.dumps(mods)[:120])
        t.ok(any("name" in m
                 and (m.get("routes") or [{}])[0].get("dev")
                 for m in mods["modules"]),
             "...and its rows carry name plus a route dev - what a NAME "
             "match needs")

        st, _ = F.post(base + "/api/play/stop", b"")
        t.ok(st != 401, "STOP stays ungated - stopping never needs a login")

        # ---- 2: /ask is capped, small questions are not -------------------
        url1 = "http://127.0.0.1:%d" % F._free_port()
        cfg = _cfg(tmp, url1)
        proc, port, logp = _helper(cfg, _faq(tmp), url1)
        try:
            t.ok(_wait_health(port), "a plain 127.0.0.1 helper comes up")
            big = b'{"text": "' + b"x" * (1024 * 1024 + 100) + b'"}'
            r = F.post("http://127.0.0.1:%s/ask" % port, big)
            got = json.loads(r[1])
            t.ok(not got.get("ok") and "too long" in got.get("error", ""),
                 "an oversized question is refused in words",
                 r[1][:140])
            small = json.loads(F.post(
                "http://127.0.0.1:%s/ask" % port,
                json.dumps({"text": "what is this"}).encode())[1])
            t.ok(small.get("ok") and small.get("source") == "faq",
                 "a normal question still asks normally",
                 json.dumps(small)[:120])

            # ---- 3: the URL's address IS the listen address ---------------
            ip = _lan_ip()
            if not t.ok(ip, "this PC has a LAN address to share on"):
                return
            url2 = "http://%s:%d" % (ip, F._free_port())
            cfg2 = _cfg(tmp, url2)
            proc2, port2, logp2 = _helper(cfg2, _faq(tmp), url2)
            try:
                t.ok(_wait_health(port2, host=ip),
                     "pointed at the LAN address, it answers THERE")
                refused = True
                try:
                    F.get("http://127.0.0.1:%s/health" % port2, timeout=4)
                    refused = False
                except Exception:               # noqa: BLE001
                    pass
                t.ok(refused, "...and NOT on 127.0.0.1 - the URL decides, "
                              "nothing wider")
                t.contains(logp2.read_text(errors="replace"),
                           "no password",
                           "sharing prints its cost where the sharer reads")
                t.ok("no password" not in logp.read_text(errors="replace"),
                     "a loopback helper stays quiet about sharing")
            finally:
                proc2.terminate()
                os.environ.pop("MICE_VOICE_CONFIG", None)
        finally:
            proc.terminate()

        # ---- 4: the page glue exists -------------------------------------
        page = (F.CODE / "apps" / "voice" / "index.html").read_text(
            encoding="utf-8", errors="replace")
        t.contains(page, "/api/modules/all",
                   "the page looks robots up by list, not by hardcoded dev")
        t.contains(page,
                   'm.name || "").trim().toLowerCase() === want',
                   "the name match compares the saved NAME with each robot, "
                   "ignoring case")
        t.contains(page,
                   "(bot.routes || []).find(rt => !rt.stale)",
                   "a robot is reached by a LIVE route only - a stale-only "
                   "row counts as not found")
        t.contains(page, "No robot named",
                   "an unknown name is answered in words that name it")
        t.contains(page, "already moving",
                   "a busy robot is answered in words, never queued")
        t.ok("bot.dev" in page,
             "the play request uses the dev the lookup found")
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
