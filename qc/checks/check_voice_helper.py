"""The hub starts the voice helper itself, once, and says why when it cannot.

User 2026-10-29: *แก้ ... แอพ voice ที่ค้าง*. On the PC nothing listened on
8767: the Voice page's Start waited 10 s and then showed "connecting…"
forever, and every line the rig had to say failed with it. The old start
sent the helper's output to nowhere, could pick the Microsoft Store stub as
Python under MiceHub.exe, and a second press started a second copy.

A fake helper (a tiny HTTP server named apps/voice/service.py in a temp
folder) stands in for the real one, so no model ever loads here:

1. start() twice -> ONE process; the second answer is "starting";
2. ensure() waits until /health answers;
3. a helper that exits at once -> state() says it stopped, with its last
   printed lines from the log (no more silent DEVNULL);
4. MiceHub.exe never takes WindowsApps\\python.exe; `["py", "-3"]` keeps
   its argument;
5. call() after "connection refused" starts the helper and tries again;
6. through the hub: a GET look answers 503 "starting" at once, a POST /say
   waits for the helper and goes through; a rig line gets its sound too;
7. inside the helper: the boot preload and a first question never load the
   same model twice at once (both ran, one without the GPU lock).
"""
import importlib.util
import json
import os
import threading
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import qc as F

AREA = "voice"
TITLE = "the hub starts the voice helper once, waits for it, and logs why it stopped"

FAKE = r'''
import os, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer
print("fake helper up", flush=True)
if os.environ.get("FAKE_MODE") == "die":
    print("Traceback: ModuleNotFoundError: No module named faster_whisper", flush=True)
    sys.exit(3)
time.sleep(float(os.environ.get("FAKE_DELAY") or 0))
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, body, kind="application/json"):
        self.send_response(200); self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_GET(self): self._send(b'{"ok": true, "parts": {}}')
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._send(b"RIFF....WAVEfake", "audio/wav")
HTTPServer(("127.0.0.1", int(os.environ["FAKE_PORT"])), H).serve_forever()
'''


def _root():
    root = Path(tempfile.mkdtemp(prefix="mice_qc_vhelper_"))
    (root / "apps" / "voice").mkdir(parents=True)
    (root / "apps" / "voice" / "service.py").write_text(FAKE, encoding="utf-8")
    return root


def _helper(vh, root, port, mode="ok", delay=0, **cfg):
    settings = dict({"autoStart": True, "startSeconds": 20, "waitSeconds": 15,
                     "log": "helper.log"}, **cfg)
    env = dict(os.environ, FAKE_PORT=str(port), FAKE_MODE=mode, FAKE_DELAY=str(delay))
    return vh.VoiceHelper(lambda: ("http://127.0.0.1:%d" % port, ""), lambda: settings,
                          root=root, data=root, env=lambda: env, frozen=False)


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    import voice_helper as vh
    procs = []
    try:
        # ---- 1 + 2: one start, then it answers ----------------------------
        root, port = _root(), F._free_port()
        h = _helper(vh, root, port, delay=1.5)
        first, second = h.start(), h.start()
        procs.append(h._proc)
        t.ok(first.get("started") and second.get("starting"),
             "a second start while the first is coming up does not start another",
             "first=%r second=%r" % (first, second))
        t.ok(h.state().get("starting"), "state() says starting, with seconds", h.state())
        ok, why = h.ensure()
        t.ok(ok, "ensure() waits until the helper answers /health", why)
        t.ok(h.start().get("already_running"), "a start while it runs is 'already running'")
        t.ok("fake helper up" in h.log_tail(), "what the helper prints lands in its log",
             h.log_tail())

        # ---- 3: it exits at once -> said, with its last lines --------------
        root3, port3 = _root(), F._free_port()
        d = _helper(vh, root3, port3, mode="die")
        d.start()
        procs.append(d._proc)
        ok, why = d.ensure(wait=10)
        st = d.state()
        t.ok(not ok and "stopped" in why, "a helper that dies is reported, not waited on forever", why)
        t.ok(st.get("exited") == 3 and "faster_whisper" in (st.get("tail") or ""),
             "state() gives the exit code and the helper's last printed lines", st)

        # ---- 4: which Python MiceHub.exe uses ------------------------------
        stub = r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\python.exe"
        found = {"python": stub, "py": r"C:\Windows\py.exe"}
        f = vh.VoiceHelper(lambda: ("", ""), lambda: {"python": ["python", ["py", "-3"]]},
                           root=root, data=root, frozen=True,
                           which=lambda n: found.get(n), exists=lambda p: True)
        t.eq(f.python(), [r"C:\Windows\py.exe", "-3"],
             "the Store stub is skipped and the launcher keeps its -3")
        none = vh.VoiceHelper(lambda: ("", ""), lambda: {"python": ["python"]},
                              root=root, data=root, frozen=True,
                              which=lambda n: stub, exists=lambda p: True)
        got = none.start() if none.python() is None else {}
        t.ok(not got.get("ok") and "voice_helper.json" in (got.get("error") or ""),
             "no usable Python: the answer names the file to fix", got)

        # ---- 5: call() starts it after "refused" ---------------------------
        root5, port5 = _root(), F._free_port()
        c = _helper(vh, root5, port5)
        url = "http://127.0.0.1:%d/health" % port5

        def look():
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.read()
        got = c.call(look)
        procs.append(c._proc)
        t.ok(b'"ok": true' in got, "call(): refused -> started -> answered", got)
        off = _helper(vh, _root(), F._free_port(), autoStart=False)
        try:
            off.call(lambda: urllib.request.urlopen(
                "http://127.0.0.1:%d/" % F.dead_port(), timeout=3))
            t.ok(False, "autoStart off: the refusal comes back")
        except OSError as e:
            t.ok("autoStart" in str(e) and off._proc is None,
                 "autoStart off: nothing starts and the reason names the switch", str(e))

        # ---- 6: through the hub -------------------------------------------
        import hub_speak
        cfg = _root() / "voice.json"
        old_cfg = os.environ.get("MICE_VOICE_CONFIG")
        os.environ["MICE_VOICE_CONFIG"] = str(cfg)
        base, main = F.start_hub()
        F.login(base)
        old_helper, old_tts = main.VOICE_HELPER, hub_speak.SPEECH.tts

        def down_helper(delay=1.0):
            """A fresh fake helper on a fresh port, not running yet."""
            port = F._free_port()
            cfg.write_text(json.dumps({"service": "http://127.0.0.1:%d" % port}), encoding="utf-8")
            helper = _helper(vh, _root(), port, delay=delay)
            helper.url = main.voice_service_url
            main.VOICE_HELPER = helper
            return helper
        try:
            look = down_helper()
            st, body = F.get(base + "/api/voice/health")
            procs.append(look._proc)
            got = json.loads(body or b"{}")
            t.ok(st == 503 and got.get("starting"),
                 "a look while it is down answers at once: 'starting'", (st, body[:200]))
            st, body = F.get(base + "/api/voice/helper")
            got = json.loads(body or b"{}")
            t.ok(got.get("ok") and (got.get("starting") or got.get("running")),
                 "/api/voice/helper tells the page it is starting", body[:200])

            say = down_helper()
            st, body = F.post(base + "/api/voice/say", json.dumps({"text": "hi"}).encode())
            procs.append(say._proc)
            t.ok(st == 200 and str(body).startswith("RIFF"),
                 "POST /say while the helper is down: started, waited, spoken", (st, body[:120]))

            rig = down_helper()
            hub_speak.SPEECH.tts = None              # the real road to the helper
            wav, why = hub_speak.SPEECH._make("hi", "", "th", 16000)
            procs.append(rig._proc)
            t.ok(wav and wav.startswith(b"RIFF"),
                 "a line the rig must say while the helper is down still gets its sound", why)
        finally:
            main.VOICE_HELPER, hub_speak.SPEECH.tts = old_helper, old_tts
            if old_cfg is None:
                os.environ.pop("MICE_VOICE_CONFIG", None)
            else:
                os.environ["MICE_VOICE_CONFIG"] = old_cfg
        # ---- 7: one load per model --------------------------------------
        spec = importlib.util.spec_from_file_location("voice_helper_check_svc",
                                                      F.CODE / "apps/voice/service.py")
        svc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(svc)
        b = svc.Brain.__new__(svc.Brain)
        b.cfg = {"llm": {"enabled": True}, "stt": {"enabled": True}}
        b._llm = b._llm_err = b._stt = b._stt_err = None
        loads = {"llm": 0, "stt": 0}

        def fake(kind):
            def now():
                if getattr(b, "_" + kind):
                    return                       # the real loaders start the same way
                time.sleep(0.3)                  # a model takes a while to load
                loads[kind] += 1
                setattr(b, "_" + kind, object())
            return now
        b._load_llm_now, b._load_stt_now = fake("llm"), fake("stt")
        both = [threading.Thread(target=f) for f in (b._load_llm, b._load_llm, b._load_stt, b._load_stt)]
        for x in both:
            x.start()
        for x in both:
            x.join(5)
        t.ok(loads == {"llm": 1, "stt": 1},
             "preload and a first question together load each model ONCE", loads)
    finally:
        for p in procs:
            if p is not None and p.poll() is None:
                p.kill()
                try:
                    p.wait(timeout=5)
                except Exception:                            # noqa: BLE001
                    pass
        time.sleep(0.1)
