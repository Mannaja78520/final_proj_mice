"""A complaint in any language keeps its words and gains an English twin.

A21-8. The chain: a report filed on any page is saved with the visitor's
words EXACTLY as written; a background call to the voice helper's /translate
adds text_en to that file once, when it can; the complaints screen and
tools/reports.py read the stored twin and never translate per refresh.

Two rules this check guards, both paid for in review:
  * the LIST endpoint must not translate live - each call is a GPU
    generation on the helper's local model, so a refresh would hang the page
    and re-translate the same words every time;
  * a failed translation is SILENCE, never a guess - "(translation
    unavailable)" standing where somebody's words were was a real finding.

Runs the REAL service subprocess with llm switched off (no torch needed):
English must come back byte-for-byte without a model, and Thai must be
refused honestly, naming config/voice.json - exactly the state of a PC
whose model is off.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "a complaint in any language keeps its words and gains an English twin"

# "the stop button does not work, the robot moves by itself" - a plausible
# complaint, and non-ASCII all the way through so the ASCII shortcut cannot
# fake a pass.
THAI = "ปุ่มหยุดไม่ทำงาน หุ่นยนต์ขยับเอง"
PORT = F._free_port()


def _svc_post(payload):
    req = urllib.request.Request(
        "http://127.0.0.1:%d/translate" % PORT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_translate_qc_"))
    cfg = tmp / "voice.json"
    faq = tmp / "qa_data.json"
    faq.write_text(json.dumps({"faqs": []}, ensure_ascii=False),
                   encoding="utf-8")
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % PORT,
        "stt": {"enabled": False}, "llm": {"enabled": False},
        "tts": {"enabled": False},
    }), encoding="utf-8")
    os.environ["MICE_VOICE_CONFIG"] = str(cfg)

    svc_log = open(tmp / "service.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--faq", str(faq), "--port", str(PORT)],
        stdout=svc_log, stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONUNBUFFERED="1"))
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
            except Exception:                   # noqa: BLE001
                time.sleep(0.3)
        if not t.ok(up, "the real voice helper came up (model off)",
                    Path(svc_log.name).read_text(errors="replace")[:300]):
            return

        # -- 1: English in, byte-for-byte back, no model involved --------
        st, ans = _svc_post({"text": "the arm will not home"})
        t.eq(st, 200, "ASCII text answers 200 straight from the service")
        t.ok(ans.get("ok") and ans.get("translated") is False
             and ans.get("text") == "the arm will not home",
             "English comes back IDENTICAL, marked as needing no translation",
             json.dumps(ans)[:150])

        # -- 2: Thai in with the model off: refused, naming the fix ------
        st, ans = _svc_post({"text": THAI})
        t.ok(not ans.get("ok"),
             "non-English with the model off is REFUSED, not faked",
             json.dumps(ans, ensure_ascii=False)[:150])
        t.ok("switched off" in (ans.get("error") or ""),
             "...and the refusal names config/voice.json, where the switch is",
             str(ans.get("error"))[:120])

        # -- 3: nothing in -> a plain refusal, not a crash ---------------
        st, ans = _svc_post({"text": "   "})
        t.eq(st, 400, "empty text is refused with a bad-request")

        # -- 4: through the hub - file a Thai complaint, then read it back -
        base, _m = F.start_hub()
        rep_dir = F.HUB / "reports"
        before = set(rep_dir.glob("*.json")) if rep_dir.is_dir() else set()
        st, body = F.post(base + "/api/report", json.dumps({
            "text": THAI, "page": "/hub.html?qc=1",
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }).encode())
        rid = (json.loads(body) or {}).get("id") if st == 200 else None
        if not t.ok(rid, "the hub accepted a report with no login",
                    "%s %s" % (st, body[:120])):
            return

        # The background translation gets an honest 'off' answer almost at
        # once; give it its moment, then demand the file be unchanged.
        stored = None
        deadline = time.time() + 6
        while time.time() < deadline and stored is None:
            new = [p for p in (rep_dir.glob("*.json") if rep_dir.is_dir()
                               else []) if p not in before]
            if new:
                stored = json.loads(new[0].read_text(encoding="utf-8"))
            else:
                time.sleep(0.2)
        t.ok(stored is not None and stored.get("text") == THAI,
             "the visitor's words are saved UNTOUCHED, not paraphrased",
             json.dumps(stored, ensure_ascii=False)[:200] if stored
             else "no report file appeared")
        t.ok(stored is not None and not stored.get("text_en"),
             "with the model off, NO translation is invented",
             json.dumps(stored, ensure_ascii=False)[:200] if stored
             else "no report file appeared")

        # -- 4b: the clock a visitor types becomes a FILENAME --------------
        # A time of ../../pwned used to carry the report out of reports/ and
        # write it wherever the string pointed on this PC.
        root_before = set(F.HUB.parent.rglob("*.json"))
        st, body = F.post(base + "/api/report", json.dumps({
            "text": "qc traversal", "time": "../../pwned"}).encode())
        t.eq(st, 200, "a report with a strange clock still files")
        stray = [p for p in F.HUB.parent.rglob("*.json")
                 if p not in root_before and p.parent != rep_dir]
        t.ok(not stray,
             "a crafted clock cannot move a report out of reports/",
             "wrote %s" % ([str(p) for p in stray[:3]],))

        # -- 4c: an open endpoint still caps what it will read -------------
        # /api/report takes complaints from anyone, so a Content-Length
        # claiming gigabytes must be refused, not read into RAM. The body is
        # VALID json - merely too big - so only the size check can refuse it;
        # junk would die in json.loads and prove nothing.
        big = json.dumps({"text": "qc oversize", "page": "/x",
                          "pad": "x" * (2 * 1048576)}).encode()
        req = urllib.request.Request(base + "/api/report", data=big,
                                     method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                st_big, ans_big = r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            st_big, ans_big = e.code, json.loads(e.read())
        except OSError as e:
            # Windows aborts the SENDER's socket when the hub hangs up before
            # reading the body - that is the refusal, seen from the far end.
            st_big, ans_big = 413, {"ok": False, "error": str(e)}
        t.ok(st_big in (400, 413, 500) or not ans_big.get("ok"),
             "a two-megabyte complaint is refused, not swallowed whole",
             "%s %s" % (st_big, str(ans_big)[:120]))

        # -- 5: the list serves what is stored - no model call anywhere ---
        st, body = F.get(base + "/api/reports")
        rows = (json.loads(body) or {}).get("reports", [])
        mine = [r for r in rows if r.get("id") == rid]
        t.ok(bool(mine), "the complaints list shows the new report")
        t.ok(mine and mine[0].get("text") == THAI
             and mine[0].get("text_en") == "",
             "...carrying the original and an EMPTY text_en for the pages "
             "to fall back from",
             json.dumps(mine, ensure_ascii=False)[:200])

        # -- both writers of one report file take the same lock ------------
        src = (F.HUB / "main.py").read_text(encoding="utf-8")
        t.ok(src.count("with _reports_lock:") >= 2,
             "the translator and the status screen share one file lock",
             "both read-modify-write the same json; unlocked, whichever "
             "wrote second put back a copy without the other's change - a "
             "closed report reopened itself, or a translation vanished")
        t.ok("could not save:" in src,
             "and a failed save is SAID, not swallowed",
             "the complaint used to vanish while the page reported ok")
        # The STATUS screen must read under that same lock, not only write
        # under it: a copy taken outside could put back a version without the
        # translation - the exact loss this lock exists for (2026-08-26).
        i_lock = src.find('with _reports_lock:', src.find('/api/reports'))
        i_read = src.find('_json.loads(f.read_text', i_lock)
        t.ok(i_lock >= 0 and i_read > i_lock,
             "the status screen reads its report inside the lock",
             "reading first and locking later leaves a window where a "
             "finished translation is overwritten by an older copy")
        # The LIST endpoint reads every file too - unlocked, its open read
        # handles made the writers' os.replace fail on Windows (panel,
        # 2026-08-26), eating a just-finished translation.
        i_get = src.find('/api/reports')
        i_post = src.find('/api/reports', i_get + 10)
        t.ok('_reports_lock' in src[i_get:i_post],
             "the complaints list reads inside the lock as well",
             "an unlocked reader holds files open while a writer replaces "
             "them, which fails on Windows")

        for p in (rep_dir.glob("*.json") if rep_dir.is_dir() else []):
            if p not in before:
                p.unlink(missing_ok=True)     # QC leaves no fake complaints
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
        proc.terminate()
        svc_log.close()
