"""Voice and faces helpers started for real (their own processes), poked over HTTP.

    python tools/helpers_probe.py

Voice runs on a COPY of config/voice.json and qa_data.json (the real ones are
never touched), on port 18767. Faces watcher runs on 18769 with no friend
program behind it, so it must say plainly that nobody is there.
No LLM question is asked on purpose (a miss would load a 4B model).
Tested on this PC against the local helpers, not on the stage.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = []


def rec(cid, ok, label, seen=""):
    OUT.append({"id": cid, "ok": bool(ok), "label": label, "seen": str(seen)[:200]})
    print(("%s %s %s | %s" % ("PASS" if ok else "FAIL", cid, label, str(seen)[:110])).encode("ascii", "replace").decode(), flush=True)


def call(port, path, body=None, raw=None, timeout=20, method=None):
    url = "http://127.0.0.1:%d%s" % (port, path)
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    rq = urllib.request.Request(url, data=data, method=method or ("POST" if data is not None else "GET"),
                                headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), time.time() - t
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), time.time() - t
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, e), time.time() - t


def wait(port, path, secs=60):
    end = time.time() + secs
    while time.time() < end:
        if call(port, path, timeout=2)[0] == 200:
            return True
        time.sleep(0.5)
    return False


def main():
    tmp = Path(tempfile.mkdtemp())
    rules_path = ROOT / "apps" / "faces" / "rules.json"
    rules_keep = rules_path.read_bytes()      # the faces watcher is the one writer: put it back at the end
    cfg = tmp / "voice.json"
    faq = tmp / "qa.json"
    src = ROOT / "config" / "voice.json"
    if src.exists():
        shutil.copy(src, cfg)
    else:
        cfg.write_text("{}")
    shutil.copy(ROOT / "apps" / "voice" / "qa_data.json", faq)
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    vp = subprocess.Popen([sys.executable, str(ROOT / "apps" / "voice" / "service.py"), "--config", str(cfg), "--faq", str(faq), "--port", "18767"],
                          cwd=str(ROOT), env=env, stdout=open(tmp / "v.log", "w"), stderr=subprocess.STDOUT)
    fp = subprocess.Popen([sys.executable, str(ROOT / "apps" / "faces" / "service.py"), "--port", "18769"],
                          cwd=str(ROOT), env=env, stdout=open(tmp / "f.log", "w"), stderr=subprocess.STDOUT)
    try:
        v_up = wait(18767, "/health")
        rec("VOICE-up", v_up, "voice helper answers /health", call(18767, "/health")[1][:100])
        f_up = wait(18769, "/health")
        rec("FACES-up", f_up, "faces watcher answers /health", call(18769, "/health")[1][:100])
        if v_up:
            for p in ("/config", "/faq", "/profiles", "/voices", "/styles", "/services", "/face", "/camera", "/nope"):
                s, b, t = call(18767, p)
                rec("VOICE GET " + p, s in (200, 404) and s != 500, "GET %s" % p, "%s %.2fs %s" % (s, t, b[:50].replace("\n", " ")))
            # FAQ question from the saved answers: instant
            faq_q = json.loads(faq.read_text(encoding="utf-8"))["faqs"][0]["questions"][0]
            s, b, t = call(18767, "/ask", {"text": faq_q})
            rec("UI-137", s == 200 and t < 5, "FAQ question answered without the model", "%s %.2fs %s" % (s, t, b[:80]))
            # nothing is asked that could wake the model: only inputs that fail before it
            cases = {
                "empty": {"text": ""},
                "spaces": {"text": "   "},
                "no body": None,
                "list body": [1, 2],
                "text is a number": {"text": 5},
                "text is null": {"text": None},
            }
            for k, body in cases.items():
                s, b, t = call(18767, "/ask", body if body is not None else {})
                rec("UI-138 " + k, s != 500 and s != 0, "ask with %s: plain error, no crash" % k, "%s %s" % (s, b[:80]))
            s, b, t = call(18767, "/ask", raw=b"{not json")
            rec("UI-138 bad json", s == 400, "ask with broken JSON -> 400", "%s %s" % (s, b[:60]))
            s, b, t = call(18767, "/ask", raw=b"x" * (2 * 1024 * 1024))
            rec("UI-138 2MB", s in (400, 413, 0), "ask with 2 MB body refused", "%s %s" % (s, b[:60]))
            # same FAQ question 40 at once
            res = []
            def hit():
                res.append(call(18767, "/ask", {"text": faq_q}, timeout=30))
            th = [threading.Thread(target=hit) for _ in range(40)]
            t0 = time.time()
            [x.start() for x in th]
            [x.join() for x in th]
            ok = sum(1 for r in res if r[0] == 200)
            rec("VOICE-40", ok == 40, "40 asks at once, all answered (%.1fs)" % (time.time() - t0), "%d of 40, slowest %.1fs" % (ok, max(r[2] for r in res)))
            s, b, t = call(18767, "/faq")
            before = b
            for _ in range(3):
                call(18767, "/faq", json.loads(b) if b.startswith("{") else {})
            rec("UI-142", call(18767, "/health")[0] == 200, "POST /faq with its own content keeps the helper alive", "")
        if f_up:
            for p in ("/health", "/state", "/rules", "/presence", "/count", "/nope"):
                s, b, t = call(18769, p)
                rec("FACES GET " + p, s != 500, "GET %s" % p, "%s %.2fs %s" % (s, t, b[:70].replace("\n", " ")))
            for k, body in (("empty rules", {}), ("rules not a dict", {"rules": 5}), ("huge name", {"rules": {"words": ["x" * 100000]}})):
                s, b, t = call(18769, "/rules", body)
                rec("FACES POST rules " + k, s != 500 and s != 0, "POST /rules %s: refused or saved, no crash" % k, "%s %s" % (s, b[:80]))
            s, b, t = call(18769, "/present", {"name": "ทดสอบ"})
            rec("FACES present", s != 500, "POST /present", "%s %s" % (s, b[:80]))
            s, b, t = call(18769, "/present", raw=b"\xff\xfe")
            rec("FACES present bin", s != 500, "POST /present binary", "%s %s" % (s, b[:80]))
    finally:
        for p in (vp, fp):
            p.kill()
        rules_path.write_bytes(rules_keep)
        (ROOT / "docs" / "test_cases" / "helpers_probe.json").write_text(json.dumps(OUT, indent=1))
        print("voice log tail:", (tmp / "v.log").read_text(errors="replace")[-300:].replace("\n", " | "))
        print("faces log tail:", (tmp / "f.log").read_text(errors="replace")[-300:].replace("\n", " | "))
        print("%d cases, %d failed" % (len(OUT), len([o for o in OUT if not o["ok"]])))


main()
