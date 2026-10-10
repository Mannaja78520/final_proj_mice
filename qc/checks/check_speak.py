"""The rig's voice: one queue decides who talks, and silence always wins (A4-3..A4-5).

The face watcher greets, a program on this PC celebrates, the Voice page
answers through a robot - all of them end in ONE queue (main_python/
hub_speak.py). Before it there were two starters and no owner: a greeting
would stream over a person's live sound, a slow feeder put its audio into
the next stream's queue (measured 2026-09-29: 8 orphan senders from 20
racing starts), and Stop All sent MOVE STOP, which silences a song on the
SD card but not a live stream.

Asserted on what reached the fake board - the commands on its wire and the
datagrams at its UDP port, each sentence carrying its own sample value - not
on what the hub says about itself:

  * a sentence is STREAM ON, the sound, then STREAM OFF only after the
    board's 200 ms buffer has played out (BOARD_TAIL_S), or the last word
    is clipped;
  * `queue` waits its turn and never interleaves, `skip` is dropped with the
    reason and never even made, only `take` interrupts - and its STREAM OFF
    lands before the new STREAM ON;
  * a greeting that waited past its age is not said and not made;
  * the queue has a ceiling, said in plain words;
  * Stop All, with no login, silences speech in flight and empties the queue;
  * live sound from a page takes the speaker; the page that was taken over
    is told 409 instead of feeding someone else's stream, and its stop does
    not silence what took over; a greeting waits for live sound to go quiet;
  * speakers are FOUND by the board's `audio` capability; "no speaker wired"
    and "cable only" are said in plain words, and a board that refused is
    asked again rather than written off;
  * choosing a speaker, reading the queue and speaking all need a login from
    the network (a program at this PC: check_local_program).
"""
import io
import json
import os
import socket
import tempfile
import threading
import time
import wave
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "one queue decides who talks, and silence always wins"

RATE = 22050
# the value every sample of one sentence carries, so a datagram names its sentence
VALUES = {}


def _wav(seconds, value):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(int(value).to_bytes(2, "little", signed=True) * int(seconds * RATE))
    return buf.getvalue()


def _say(text, secs):
    """Text for the fake voice: '<tag>|<seconds>'. Its samples carry a value."""
    VALUES.setdefault(text.split("|")[0], 1000 + 37 * len(VALUES))
    return "%s|%s" % (text, secs)


def _post_json(url, obj, headers=None):
    import urllib.error
    import urllib.request
    req = F._with_cookie(urllib.request.Request(
        url, data=json.dumps(obj).encode("utf-8"), method="POST"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(body)
        except ValueError:
            return e.code, {"raw": body}


class FakeShow:
    def __init__(self):
        self.on = False
        self.started = []
        self.stops = []

    def running(self):
        return self.on

    def start(self, dev, steps, loop=None, name=""):
        self.started.append((dev, name))

    def stop(self, freeze=False, why=""):
        self.stops.append(why)
        self.on = False

    def status(self):
        return {"running": self.on}


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_qc_speak_"))
    spk = tmp / "speakers.json"
    spk.write_text(json.dumps({"default": "nong", "queueMax": 3,
                               "maxAgeSeconds": 30}), encoding="utf-8")
    os.environ["MICE_SPEAKERS"] = str(spk)
    base, main = F.start_hub()
    speak = main.hub_speak

    # ---- "audio" travels from the board to the speaker list ----------------
    import fake_wifi
    addr = fake_wifi.start()
    wifi = main.probe_module(addr) or {}
    t.ok("audio" in (wifi.get("caps") or []),
         "a board's WiFi answer carries its capabilities to the hub", json.dumps(wifi)[:200])
    usb = [u["module"] for u in main.probe_usb_all(True) if u.get("module")]
    t.ok(usb and "audio" in (usb[0].get("caps") or []),
         "and so does its answer down a cable", json.dumps(usb)[:200])
    real_usb, real_wifi = main.probe_usb_all, main.scan_modules
    try:
        # one board, both ways in; the cable row is first and knows no caps
        # (a bus board past the six the census asks INFO), the WiFi one does
        main.probe_usb_all = lambda force=False: [
            {"port": "COM9", "rs485": [],
             "module": dict(usb[0] if usb else {}, chip="QCSPK", caps=[])}]
        main.scan_modules = lambda force=False: [dict(wifi, chip="QCSPK")]
        merged = [m for m in main.modules_here(True) if m.get("chip") == "QCSPK"]
    finally:
        main.probe_usb_all, main.scan_modules = real_usb, real_wifi
    sp = [x for x in speak.speaker_list(mods=merged) if x["kind"] == "module"]
    t.ok(len(sp) == 1 and sp[0]["ready"] and sp[0]["ip"] == "127.0.0.1"
         and sp[0]["dev"] == "wifi:" + addr,
         "merged into one row, it is one speaker: sound to its IP, commands to its route",
         json.dumps(sp))

    # ---- the fake board: a UDP ear and a wire that records every command --
    ear = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ear.bind(("127.0.0.1", 0))
    ear.settimeout(0.1)
    heard = []                                   # (time, first sample value)
    done = threading.Event()

    def listen():
        while not done.is_set():
            try:
                data, _ = ear.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            heard.append((time.time(), int.from_bytes(data[:2], "little", signed=True)))
    threading.Thread(target=listen, daemon=True).start()

    wire = []                                    # (time, dev, command)
    stream_on = ["OK stream on"]

    def dev_cmd(dev, c, *a, **k):
        wire.append((time.time(), dev, c))
        return stream_on[0] if c.startswith("STREAM ON") else "OK"

    made = []

    def tts(text, voice, lang, rate):
        made.append(text)
        tag, secs = text.split("|")
        return _wav(float(secs), VALUES[tag]), ""

    nong = {"name": "nong", "type": "nong", "caps": ["pins", "joints", "audio"],
            "routes": [{"kind": "wifi", "ip": "127.0.0.1", "dev": "wifi:127.0.0.1"}],
            "best": "wifi:127.0.0.1"}
    lift = {"name": "lift", "type": "lift", "caps": ["motion", "audio"],
            "routes": [{"kind": "usb", "dev": "usb:COM98", "port": "COM98"}]}
    cam = {"name": "cam", "type": "cam", "caps": ["camera"],
           "routes": [{"kind": "wifi", "ip": "127.0.0.9", "dev": "wifi:127.0.0.9"}]}
    show = FakeShow()
    seqs = tmp / "sequences"
    seqs.mkdir()
    (seqs / "wave.yaml").write_text("name: wave\n", encoding="utf-8")   # parsed by the fake below
    saved = {k: getattr(main, k) for k in ("dev_cmd", "modules_here", "show",
                                           "SEQUENCES", "seq_steps")}
    saved_port = main.stream_audio.DEF_PORT
    main.dev_cmd = dev_cmd
    main.modules_here = lambda force=False: [nong, lift, cam]
    main.show = show
    main.SEQUENCES = seqs
    main.seq_steps = lambda text: {"steps": [{"pose": "a"}, {"pose": "b"}], "loop": False}
    main.stream_audio.DEF_PORT = ear.getsockname()[1]
    speak.SPEECH.tts = tts

    def state(jid):
        st = speak.SPEECH.status()
        for j in ([st["now"]] if st["now"] else []) + st["queue"] + st["recent"]:
            if j and j["id"] == jid:
                return j
        return {}

    def wait_end(jid, timeout=15.0):
        end = time.time() + timeout
        while time.time() < end:
            j = state(jid)
            if j.get("state") in ("done", "skipped", "expired", "cancelled", "failed"):
                return j
            time.sleep(0.05)
        return state(jid)

    def wait_heard(tag, timeout=10.0):
        end = time.time() + timeout
        while time.time() < end:
            if any(v == VALUES[tag] for _, v in heard):
                return True
            time.sleep(0.02)
        return False

    def times(tag):
        return [ts for ts, v in heard if v == VALUES[tag]]

    def cmds(since=0.0):
        return [(ts, c) for ts, d, c in wire if ts >= since]

    def speak_now(obj):
        code, got = _post_json(base + "/api/speak", obj)
        return got.get("id") or "", got

    try:
        F.login(base)

        # ---- speakers are found, not listed --------------------------------
        code, body = F.get(base + "/api/speakers")
        got = json.loads(body)
        by = {s["id"]: s for s in got.get("speakers", [])}
        t.ok("nong" in by and by["nong"]["ready"] and by["nong"]["dev"] == "wifi:127.0.0.1",
             "a board that reports the audio capability is a speaker, reached over WiFi",
             json.dumps(got)[:300])
        t.ok("cam" not in by, "a board without a speaker is not listed as one")
        t.ok("lift" in by and not by["lift"]["ready"]
             and "cable" in by["lift"]["why"],
             "a speaker reached only by cable says so in plain words",
             json.dumps(by.get("lift")))
        t.ok("pc" in by and (by["pc"]["ready"] or by["pc"]["why"]),
             "this PC's own speakers are always listed, with a reason when they cannot play")
        F.logout_qc()
        code, got = _post_json(base + "/api/speakers", {"default": "lift"})
        t.ok(code == 401 and got.get("need_login"),
             "choosing the default speaker needs a login", (code, got))
        F.login(base)
        code, got = _post_json(base + "/api/speakers", {"default": "nobody"})
        t.ok(code == 400 and "nobody" in (got.get("error") or ""),
             "an unknown speaker is refused by name", (code, got))
        code, got = _post_json(base + "/api/speakers",
                               {"default": "nong", "voices": {"nong": "qc-voice"}})
        disk = json.loads(spk.read_text(encoding="utf-8"))
        t.ok(code == 200 and disk.get("default") == "nong"
             and disk["speakers"]["nong"]["voice"] == "qc-voice"
             and disk.get("queueMax") == 3,
             "logged in, the choice is written to the file and the rest of it kept",
             json.dumps(disk))

        # ---- one sentence, whole, with the board's tail ----------------------
        t0 = time.time()
        jid, got = speak_now({"text": _say("A", 0.6), "to": "nong"})
        end = wait_end(jid)
        on = [ts for ts, c in cmds(t0) if c.startswith("STREAM ON")]
        off = [ts for ts, c in cmds(t0) if c == "STREAM OFF"]
        a = times("A")
        t.ok(end.get("state") == "done", "a sentence to a robot is said", json.dumps(end))
        t.ok(on and a and on[0] <= a[0],
             "the board is told STREAM ON before the first datagram",
             "otherwise the start of the word is gone")
        t.ok(len(a) >= 27, "the whole sentence reached the board (%d of 30 chunks)" % len(a))
        # 0.3: without the tail the sender's own stop takes up to 0.2 s
        t.ok(off and a and off[-1] - a[-1] >= 0.3,
             "STREAM OFF waits for the board to play out its buffer (%.2fs after the last datagram)"
             % ((off[-1] - a[-1]) if off and a else -1),
             "STREAM OFF frees the board's 200 ms ring at once: sooner clips the last word")

        # ---- queue waits, skip is dropped, neither interleaves ----------------
        t0 = time.time()
        q1, _ = speak_now({"text": _say("Q", 1.2), "to": "nong"})
        t.ok(wait_heard("Q"), "a long sentence starts")
        q2, _ = speak_now({"text": _say("R", 0.4), "to": "nong", "whenBusy": "queue"})
        _, sk = speak_now({"text": _say("S", 0.4), "to": "nong", "whenBusy": "skip"})
        t.ok(sk.get("state") == "skipped" and "already saying" in (sk.get("why") or ""),
             "`skip` while the rig talks is dropped, and says why", json.dumps(sk))
        e1, e2 = wait_end(q1), wait_end(q2)
        q, r = times("Q"), times("R")
        t.ok(e1.get("state") == "done" and e2.get("state") == "done" and q and r
             and max(q) < min(r),
             "`queue` waits its turn: every datagram of the first before any of the second",
             "%s %s" % (e1.get("state"), e2.get("state")))
        t.ok(_say("S", 0.4) not in made, "a skipped greeting is never even made")

        # ---- take interrupts, and its STREAM OFF lands first ------------------
        t0 = time.time()
        u, _ = speak_now({"text": _say("U", 3.0), "to": "nong"})
        t.ok(wait_heard("U"), "a three-second sentence starts")
        time.sleep(0.3)
        v, _ = speak_now({"text": _say("V", 0.4), "to": "nong", "take": True})
        eu, ev = wait_end(u), wait_end(v)
        seq = [c for _, c in cmds(t0)]
        t.ok(eu.get("state") == "cancelled" and ev.get("state") == "done",
             "`take` stops what was being said and says its own",
             "%s / %s" % (eu.get("state"), ev.get("state")))
        t.ok(len(times("U")) < 120, "the interrupted sentence was cut short (%d of 150 chunks)"
             % len(times("U")))
        t.ok(len(seq) >= 3 and seq[0].startswith("STREAM ON") and seq[1] == "STREAM OFF"
             and seq[2].startswith("STREAM ON"),
             "the board is told STREAM OFF before the new STREAM ON, never after it",
             " | ".join(seq))

        # ---- too late is not said, nor made ----------------------------------
        w, _ = speak_now({"text": _say("W", 1.2), "to": "nong"})
        t.ok(wait_heard("W"), "a sentence starts")
        y, _ = speak_now({"text": _say("Y", 0.3), "to": "nong", "maxAgeSeconds": 0.5})
        ew, ey = wait_end(w), wait_end(y)
        t.ok(ey.get("state") == "expired" and "too late" in (ey.get("why") or ""),
             "a greeting that waited past its age is dropped, in plain words", json.dumps(ey))
        t.ok(_say("Y", 0.3) not in made and not times("Y"),
             "and it was never made or sent")

        # ---- the ceiling, then Stop All with speech in flight -----------------
        z, _ = speak_now({"text": _say("Z", 3.0), "to": "nong"})
        t.ok(wait_heard("Z"), "a long sentence starts")
        waiting = [speak_now({"text": _say("Z%d" % i, 0.3), "to": "nong"})[0]
                   for i in range(3)]
        _, full = speak_now({"text": _say("Zx", 0.3), "to": "nong"})
        t.ok(full.get("state") == "skipped" and "too many" in (full.get("why") or ""),
             "past the queue's ceiling the newest is skipped, in plain words", json.dumps(full))
        F.logout_qc()
        t0 = time.time()
        code, body = F.post(base + "/api/stopall")
        after = time.time()
        got = json.loads(body)
        t.ok(code == 200 and "127.0.0.1" in (got.get("silenced") or []),
             "Stop All needs no login and names the board it silenced", body[:300])
        t.ok(any(c == "STREAM OFF" for _, c in cmds(t0)),
             "Stop All sends STREAM OFF - MOVE STOP does not end a live stream")
        time.sleep(0.8)
        late = [ts for ts in times("Z") if ts > after + 0.5]
        t.eq(late, [], "and the sound stops on the board")
        ends = [wait_end(j).get("state") for j in [z] + waiting]
        t.eq(ends, ["cancelled"] * 4, "the sentence in flight and everything waiting are cancelled")
        t.ok(not any(m.startswith("Z0") or m.startswith("Z1") or m.startswith("Z2")
                     for m in made), "nothing that waited was made after Stop All")
        F.login(base)

        # ---- live sound takes over; the old page is told, not fed -------------
        l, _ = speak_now({"text": _say("L", 3.0), "to": "nong"})
        t.ok(wait_heard("L"), "a long sentence starts")
        code, st = _post_json(base + "/api/stream/start",
                              {"dev": "wifi:127.0.0.1", "rate": RATE, "name": "qc live"})
        s1 = st.get("session") or ""
        el = wait_end(l)
        t.ok(code == 200 and s1 and el.get("state") == "cancelled"
             and "live sound" in (el.get("why") or ""),
             "a person's live sound takes the speaker, and the sentence says why it stopped",
             "%s %s %s" % (code, s1, json.dumps(el)))
        VALUES.setdefault("live", 1777)
        chunk = (1777).to_bytes(2, "little", signed=True) * 882

        def feed(session):
            import urllib.error
            import urllib.request
            req = F._with_cookie(urllib.request.Request(
                base + "/api/stream/feed?session=" + session, data=chunk * 5, method="POST"))
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read().decode() or "{}")
        code, fed = feed(s1)
        t.ok(code == 200 and fed.get("took", 0) > 0, "the live sound is fed", json.dumps(fed))
        _, sk = speak_now({"text": _say("G", 0.3), "to": "nong", "whenBusy": "skip"})
        t.ok(sk.get("state") == "skipped" and "live sound" in (sk.get("why") or ""),
             "a greeting with `skip` does not talk over live sound", json.dumps(sk))
        h, _ = speak_now({"text": _say("H", 1.5), "to": "nong", "whenBusy": "queue"})
        for _ in range(8):                     # a person still talking
            feed(s1)
            time.sleep(0.12)
        t.ok(not times("H"), "a greeting with `queue` waits while live sound is fed")
        t.ok(wait_heard("H", timeout=12), "and speaks once the live sound has gone quiet")
        code, stale = feed(s1)
        t.ok(code == 409 and stale.get("stale"),
             "the page that was taken over is told so (409), not fed into the next stream",
             "%s %s" % (code, json.dumps(stale)))
        n_off = len([1 for _, c in cmds(0) if c == "STREAM OFF"])
        code, body = F.post(base + "/api/stream/stop?session=" + s1)
        eh = wait_end(h)
        t.ok(code == 200 and json.loads(body).get("stopped") is False
             and eh.get("state") == "done" and len(times("H")) >= 70,
             "and its stop does not silence the greeting that took over",
             "%s %s %d chunks" % (body[:120], eh.get("state"), len(times("H"))))
        t.ok(len([1 for _, c in cmds(0) if c == "STREAM OFF"]) == n_off + 1,
             "only the greeting's own STREAM OFF followed")

        # ---- a board with no speaker wired, said and retried -------------------
        stream_on[0] = "ERR no speaker wired on this board (AMP none)"
        n, _ = speak_now({"text": _say("N", 0.3), "to": "nong"})
        en = wait_end(n)
        t.ok(en.get("state") == "failed" and "no speaker" in (en.get("why") or ""),
             "a board that has no speaker wired fails in plain words", json.dumps(en))
        by = {s["id"]: s for s in json.loads(F.get(base + "/api/speakers")[1])["speakers"]}
        t.ok(not by["nong"]["ready"] and "no speaker" in by["nong"]["why"],
             "and the speaker list remembers why", json.dumps(by["nong"]))
        stream_on[0] = "OK stream on"
        n2, _ = speak_now({"text": _say("N2", 0.3), "to": "nong"})
        t.ok(wait_end(n2).get("state") == "done",
             "once it answers again, it is asked again - not written off")

        # ---- a move with the words ------------------------------------------
        m, _ = speak_now({"text": _say("M", 0.3), "to": "nong", "move": "wave.yaml",
                          "module": "nong"})
        t.ok(wait_end(m).get("state") == "done" and ("wifi:127.0.0.1", "wave.yaml") in show.started,
             "a sentence with a move starts it on its robot through the one show clock",
             json.dumps(show.started))
        g, _ = speak_now({"text": _say("M2", 0.3), "to": "nong", "move": "wave.yaml",
                          "module": "ghost"})
        eg = wait_end(g)
        t.ok(eg.get("state") == "failed" and "ghost" in (eg.get("why") or ""),
             "a move for a robot that is not there fails by name", json.dumps(eg))

        # ---- the real voice helper is asked for plain WAV -----------------------
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        asked = []

        class Helper(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                asked.append(d)
                if d["text"].startswith("ERR"):
                    body, ctype = json.dumps({"ok": False, "error": "qc voice says no"}).encode(), \
                        "application/json"
                else:
                    body, ctype = _wav(0.3, VALUES["K"]), "audio/wav"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        VALUES.setdefault("K", 1999)
        helper = ThreadingHTTPServer(("127.0.0.1", 0), Helper)
        threading.Thread(target=helper.serve_forever, daemon=True).start()
        vcfg = tmp / "voice.json"
        vcfg.write_text(json.dumps({"service": "http://127.0.0.1:%d" % helper.server_address[1]}),
                        encoding="utf-8")
        os.environ["MICE_VOICE_CONFIG"] = str(vcfg)
        speak.SPEECH.tts = None
        try:
            k, _ = speak_now({"text": "K words", "to": "nong"})
            ek = wait_end(k)
            got = asked[0] if asked else {}
            t.ok(got.get("format") == "wav" and got.get("rate") == RATE
                 and got.get("voice") == "qc-voice",
                 "the voice helper is asked for plain WAV at the robot's rate, in the "
                 "speaker's own voice", json.dumps(got))
            t.ok(ek.get("state") == "done" and times("K"),
                 "and what it made reached the board", json.dumps(ek))
            e, _ = speak_now({"text": "ERR words", "to": "nong"})
            ee = wait_end(e)
            t.ok(ee.get("state") == "failed" and ee.get("why") == "qc voice says no",
                 "a helper that cannot speak it is quoted, not guessed at", json.dumps(ee))
        finally:
            speak.SPEECH.tts = tts
            os.environ.pop("MICE_VOICE_CONFIG", None)
            helper.shutdown()
            helper.server_close()

        # ---- the gates ----------------------------------------------------------
        F.logout_qc()
        code, body = F.post(base + "/api/speak", json.dumps({"text": "hi"}).encode())
        t.ok(code == 401 and "need_login" in body,
             "speaking from the network needs a login", (code, body[:160]))
        code, body = F.get(base + "/api/speak")
        t.ok(code == 401, "reading the queue needs one too - it carries people's names",
             (code, body[:160]))
        code, body = F.post(base + "/api/stream/voice", json.dumps({"text": "hi"}).encode())
        t.ok(code == 401, "the Voice page's robot speech is gated like the rest",
             (code, body[:160]))
        code, body = F.post(base + "/api/speak/stop")
        t.ok(code == 200, "and quiet never is", (code, body[:160]))
    finally:
        done.set()
        ear.close()
        speak.SPEECH.silence()
        for k, val in saved.items():
            setattr(main, k, val)
        main.stream_audio.DEF_PORT = saved_port
        speak.SPEECH.tts = None
        os.environ.pop("MICE_SPEAKERS", None)
