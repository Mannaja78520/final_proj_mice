"""A saved answer can move the robot - and only the PAGE can start it.

A20-10: an entry in qa_data.json may name a `move` (saved sequence file)
and a `module` (which robot plays it). The division is deliberate:

  * apps/voice/service.py only NAMES the move in its reply. It never holds
    the password and never touches the show clock;
  * the hub's new GET /api/seqsteps parses the same yaml /api/loadseq
    serves into ready steps - read-only, ungated like loadseq, because
    starting the show still goes through GATED /api/play;
  * the voice page fetches those steps and POSTs /api/play itself - the
    page is what holds the login.

The parser is checked through the real route, not by importing anything,
and the end-to-end phase asserts on the WIRE: steps that came out of a
qa_data-named sequence must reach the module as POSE commands.
"""
import json
import time

import fake_serial
import qc as F

AREA = "tools"
TITLE = ("an answer names its move, the parser serves steps, "
         "and the page alone starts them")

SEQ_DIR = F.CODE / "nong" / "main_python_set_nong" / "sequences"

FIX_COMPUTED = """# written by QC - timing computed from speed
name: qc_wave
loop: true
next: qc_old.yaml
steps:
  - speed: 45
  - pose: "90 90 90 90 90 90 90 90 90 90"
  - wait: 250
  - pose: "90 130 90 90 90 90 90 90 90 90"
"""

FIX_OLD = """name: qc_old
steps:
  - pose: "10 160 90 90 90 90 90 90 T 700"
  - play: some_song.mp3
  - pose: "20 150 90 90 90 90 90 90"
"""

FIX_BAD = """name: qc_bad
steps:
  - pose: "1 2 3 4 5 6 7 8 9"
"""

FIX_SHORT = """name: qc_short
steps:
  - pose: "90 90 90 90 90 90 90 90 T 500"
"""


def _write(name, text):
    p = SEQ_DIR / name
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _get(base, path):
    return json.loads(F.get(base + path)[1])


def run(t):
    fake_serial.reset()
    made = [_write("_qc_move_computed.yaml", FIX_COMPUTED),
            _write("_qc_move_old.yaml", FIX_OLD),
            _write("_qc_move_bad.yaml", FIX_BAD),
            _write("_qc_move_short.yaml", FIX_SHORT)]
    base, _main = F.start_hub()
    try:
        # ---- 1: the parser, through its real route ----------------------
        s = _get(base, "/api/seqsteps?name=_qc_move_computed.yaml")
        t.ok(s.get("ok"), "the computed-timing sequence parses", str(s)[:120])
        st = s["steps"]
        t.eq(len(st), 2, "two pose steps came out")
        t.eq(st[0]["t"], 1000, "the first step gets the reach-the-start time")
        t.eq(st[0]["hold"], 250, "wait became the previous step's hold")
        # 40 deg at 45 deg/s = 888 ms - the firmware rule, not a guess
        t.eq(st[1]["t"], 888, "a missing T is computed as max delta over speed")
        t.ok(s.get("loop") is True and s.get("next") == "qc_old.yaml",
             "loop and chain come back - but chains are NOT followed here")

        s = _get(base, "/api/seqsteps?name=_qc_move_old.yaml")
        st = s["steps"]
        t.eq([len(p["pose"]) for p in st], [10, 10],
             "old arms-only poses are padded to 10 joints")
        t.ok(st[0]["pose"][8:] == [90.0, 90.0]
             and st[0]["pose"][:2] == [10.0, 160.0],
             "...padded with WAIST and SHRUG at neutral, arms kept",
             str(st[0]["pose"]))
        t.eq(st[0]["t"], 700, "an explicit T is kept exactly")
        t.eq(st[1]["t"], 166, "the next one computes from the padded poses "
                              "(10 deg at the 60 deg/s fallback)")
        t.ok(all("pose" in x for x in st), "the music step left no hole")

        body = F.get(base + "/api/seqsteps?name=_qc_move_bad.yaml")[1]
        got = json.loads(body)
        t.ok(not got.get("ok") and "8 or 10 joints" in got.get("error", ""),
             "a 9-joint pose is refused in words, not crashed",
             body[:140])
        got = _get(base, "/api/seqsteps?name=_qc_move_short.yaml")
        t.ok(not got.get("ok") and "fewer than two" in got.get("error", ""),
             "one pose alone is not a show")
        got = _get(base, "/api/seqsteps?name=_qc_missing.yaml")
        t.ok(not got.get("ok") and "_qc_missing" in got.get("error", ""),
             "a missing file names the file")

        # read-only by decision: reading steps changes nothing, so like
        # loadseq it stays open while starting the show stays gated.
        st, b = F.get(base + "/api/seqsteps?name=_qc_move_old.yaml")
        t.eq(st, 200, "reading steps needs no login")

        # ---- 2: the service passes the move through, nothing more -------
        import os
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp(prefix="mice_mv_qc_"))
        faq = tmp / "qa.json"
        faq.write_text(json.dumps({"faqs": [
            {"questions": ["do a wave"], "answer": "Watch this.",
             "move": "_qc_move_computed.yaml", "module": "usb:COM99"},
            {"questions": ["where is the toilet"], "answer": "Left."},
        ]}, ensure_ascii=False), encoding="utf-8")
        cfg = tmp / "voice.json"
        cfg.write_text(json.dumps({
            "service": "http://127.0.0.1:%d" % F._free_port(),
            "faqThreshold": 0.75, "faqAskAgain": 0,
            "stt": {"enabled": False},
            "llm": {"enabled": False}, "tts": {"enabled": False},
        }), encoding="utf-8")
        os.environ["MICE_VOICE_CONFIG"] = str(cfg)
        port = json.loads(cfg.read_text())["service"].rsplit(":", 1)[1]
        log = open(tmp / "svc.log", "wb")
        proc = subprocess.Popen(
            [sys.executable, str(F.CODE / "apps" / "voice" / "service.py"),
             "--config", str(cfg), "--faq", str(faq), "--port", port],
            stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.time() + 15
            while time.time() < deadline:
                try:
                    if json.loads(F.get(
                            "http://127.0.0.1:%s/health" % port)[1]).get("ok"):
                        break
                except Exception:                   # noqa: BLE001
                    time.sleep(0.3)
            cookie = F.login(base)

            def ask(q):
                r = F.post(base + "/api/voice/ask",
                           json.dumps({"text": q}).encode())
                return json.loads(r[1])

            hit = ask("do a wave")
            t.ok(hit.get("source") == "faq"
                 and hit.get("move") == "_qc_move_computed.yaml"
                 and hit.get("module") == "usb:COM99",
                 "a moving answer carries move AND module to the page",
                 json.dumps(hit)[:160])
            plain = ask("where is the toilet")
            t.ok(plain.get("ok") and "move" not in plain
                 and "module" not in plain,
                 "a still answer carries neither",
                 json.dumps(plain)[:120])
        finally:
            os.environ.pop("MICE_VOICE_CONFIG", None)
            proc.terminate()

        # ---- 3: end-to-end - the named move reaches THE WIRE -------------
        s = _get(base, "/api/seqsteps?name=_qc_move_computed.yaml")
        r = F.post(base + "/api/play", json.dumps({
            "dev": "usb:" + fake_serial.PORT, "steps": s["steps"],
            "loop": True, "name": "qc_wave"}).encode())
        t.ok(json.loads(r[1]).get("running") is True,
             "the page-shaped request plays the named sequence")
        end = time.time() + 3
        while time.time() < end and not any(
                c.startswith("POSE") for _, c in fake_serial.wire):
            time.sleep(0.05)
        poses = [c for _, c in fake_serial.wire if c.startswith("POSE")]
        if t.ok(poses, "the module received the moves"):
            t.contains(poses[0], "90 90 90",
                       "...and the first pose is the file's own")
        F.post(base + "/api/play/stop", b"")

        # ---- 4: the page glue exists ------------------------------------
        page = (F.CODE / "apps" / "voice" / "index.html").read_text(
            encoding="utf-8", errors="replace")
        t.contains(page, "/api/seqsteps", "the page loads the parsed steps")
        t.contains(page, "/api/play", "and posts the show itself")
        t.contains(page, "Stop the move", "with a Stop in sight while it runs")
        t.contains(page, "r.move && r.module",
                   "only an answer that carries both can start a move")
    finally:
        F.post(base + "/api/play/stop", b"")
        for p in made:
            p.unlink(missing_ok=True)
