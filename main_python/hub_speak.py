"""The rig's voice: which speakers there are, and ONE queue that decides who talks.

System A4-3..A4-5 (docs/system_integral.html). The face watcher greets, a
program on this PC celebrates, the Voice page answers through a robot - all of
them end here, so "is the rig already talking?" has one answer, decided under
one lock (A5-4). A caller says what to do when it is: `skip` drops the words,
`queue` waits its turn, and only an explicit `take` interrupts.

NOTHING HERE IS HELD ACROSS THE NETWORK. Making the sound (the voice helper)
and telling a board STREAM ON can each take seconds, and Stop All must never
wait behind either: silence() only flips flags and returns.

Speakers are DISCOVERED, never listed by hand: a board that reports the
`audio` capability is a speaker. config/speakers.json only says which one is
the default and which voice each uses. A board may report `audio` and still
have no amplifier wired (AMP none); its first STREAM ON says so, and the list
remembers it in plain words.
"""
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from collections import deque
from pathlib import Path

_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


# The board plays up to its ring (AudioStream.h BUF_MS = 200 ms) after the last
# datagram leaves; STREAM OFF sooner frees that buffer and clips the last word.
BOARD_TAIL_S = 0.35
WAIT_STEP_S = 0.25    # how often a queued job looks again at a busy room

# What a fresh PC has. config/speakers.json overrides any of it.
DEFAULTS = {"default": "pc", "rate": 22050, "queueMax": 8, "maxAgeSeconds": 30,
            "speakers": {"pc": {"name": "This PC's speakers", "kind": "pc",
                                "voice": ""}}}

# board name (lower case) -> why it cannot speak, learnt from STREAM ON
NO_SPEAKER = {}


# ---------------------------------------------------------------- speakers
def speakers_path(writing=False):
    if os.environ.get("MICE_SPEAKERS"):
        return Path(os.environ["MICE_SPEAKERS"])
    p = Path(_hub.asset("config", "speakers.json"))
    bundled = getattr(sys, "_MEIPASS", "")
    if writing and bundled and Path(bundled) in p.parents:
        # A venue exe's bundled copy is deleted when it exits: keep the change
        # beside the exe, which asset() reads first.
        p = Path(_hub.HERE) / "config" / "speakers.json"
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_speakers():
    """(config, why-not). A broken file falls back to the defaults, said out loud."""
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        raw = _hub.registry.load(speakers_path()) if _hub.registry else \
            json.loads(speakers_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return cfg, ""
    except Exception as e:                                   # noqa: BLE001
        return cfg, "config/speakers.json could not be read (%s)" % e
    for k, v in (raw or {}).items():
        if k == "speakers" and isinstance(v, dict):
            cfg["speakers"].update(v)
        else:
            cfg[k] = v
    return cfg, ""


def save_speakers(change):
    """Apply {default, voices: {id: voice}} from the screen. -> (ok, why)."""
    try:
        now = speakers_path()
        raw = json.loads(now.read_text(encoding="utf-8")) if now.is_file() else {}
    except Exception as e:                                   # noqa: BLE001
        return False, "config/speakers.json could not be read (%s)" % e
    known = {s["id"] for s in speaker_list()}
    if "default" in change:
        want = str(change.get("default") or "")
        if want not in known:
            return False, "there is no speaker called %r" % want
        raw["default"] = want
    for sid, voice in (change.get("voices") or {}).items():
        if sid not in known:
            return False, "there is no speaker called %r" % sid
        raw.setdefault("speakers", {}).setdefault(str(sid), {})["voice"] = str(voice or "")
    path = speakers_path(writing=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes((json.dumps(raw, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(tmp, path)
    return True, ""


def _wifi_route(m):
    """(dev, ip) of a live WiFi route. The ip loses any :port - the sound goes
    to the board's UDP port, the commands to the route's own address."""
    for r in m.get("routes") or []:
        if r.get("kind") == "wifi" and not r.get("stale") and r.get("ip"):
            return r.get("dev") or "wifi:" + r["ip"], r["ip"].split(":")[0]
    return "", ""


def speaker_list(cfg=None, mods=None):
    """Every speaker, ready or not, with the reason in plain words."""
    if cfg is None:
        cfg, _ = read_speakers()
    if mods is None:
        try:
            mods = _hub.modules_here()
        except Exception:                                    # noqa: BLE001
            mods = []
    named = cfg.get("speakers") or {}
    out, seen = [], set()
    pc = named.get("pc") or DEFAULTS["speakers"]["pc"]
    ok, why = SPEECH.pc.available()
    out.append({"id": "pc", "name": pc.get("name") or "This PC's speakers",
                "kind": "pc", "voice": pc.get("voice") or "", "ready": ok, "why": why})
    seen.add("pc")
    for m in mods:
        name = str(m.get("name") or "").strip()
        if not name or "audio" not in (m.get("caps") or []) or name.lower() in seen:
            continue
        seen.add(name.lower())
        dev, ip = _wifi_route(m)
        why = (NO_SPEAKER.get(name.lower()) or "") if ip else \
            "reached by cable only - speech goes to a robot over WiFi"
        out.append({"id": name, "name": name, "kind": "module",
                    "voice": (named.get(name) or {}).get("voice") or "",
                    "ready": not why, "why": why, "ip": ip, "dev": dev})
    # Named in the file but not found: listed, so a setting never vanishes.
    for sid, entry in named.items():
        if str(sid).lower() in seen:
            continue
        out.append({"id": sid, "name": entry.get("name") or sid, "kind": "module",
                    "voice": entry.get("voice") or "", "ready": False,
                    "why": "not found on the network right now"})
    return out


def resolve(to, cfg=None, mods=None):
    """The speaker called `to` ('' = the default). -> (speaker, why-not)."""
    if cfg is None:
        cfg, _ = read_speakers()
    want = str(to or cfg.get("default") or "pc").strip()
    for s in speaker_list(cfg, mods):
        if s["id"].lower() == want.lower():
            # A board that said "no speaker wired" is asked again: it costs one
            # command, and the amplifier may have been wired since.
            if s["ready"] or (s.get("ip") and s["why"] == NO_SPEAKER.get(s["id"].lower())):
                return s, ""
            return None, "%s cannot speak: %s" % (s["name"], s["why"])
    return None, "there is no speaker called %r" % want


def module_dev(name):
    """A live way to reach the board called `name`, for its move."""
    for m in _hub.modules_here():
        if str(m.get("name") or "").strip().lower() == str(name).strip().lower():
            return m.get("best") or next((r["dev"] for r in m.get("routes") or []
                                          if not r.get("stale")), "")
    return ""


# ---------------------------------------------------------------- the PC's own
class PcPlayer:
    """This PC's speakers. Windows only: the hub carries no audio library."""

    def available(self):
        if os.name == "nt":
            return True, ""
        return False, "only a hub on Windows can play through its own speakers"

    def play(self, wav, cancelled):
        ok, why = self.available()
        if not ok:
            return False, why
        import winsound
        with wave.open(io.BytesIO(wav)) as w:
            seconds = w.getnframes() / float(w.getframerate() or 1)
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="mice_say_")
        try:
            os.write(fd, wav)
            os.close(fd)
            winsound.PlaySound(name, winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
            end = time.time() + seconds + 0.2
            while time.time() < end:
                if cancelled():
                    self.stop()
                    return False, "stopped"
                time.sleep(0.05)
            return True, ""
        finally:
            try:
                os.unlink(name)
            except OSError:
                pass

    def stop(self):
        if os.name == "nt":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:                                # noqa: BLE001
                pass


# ---------------------------------------------------------------- the queue
class Speech:
    """One queue, one worker. States: queued -> making -> playing -> done |
    skipped | expired | cancelled | failed, each with a plain-words why."""

    def __init__(self):
        self.lock = threading.Lock()
        self.jobs = deque()
        self.now = None
        self.recent = deque(maxlen=30)
        self.gen = 0                  # bumped by silence(): older jobs never play
        self.wake = threading.Event()
        self.thread = None
        self.pc = PcPlayer()
        self.tts = None               # QC: fn(text, voice, lang, rate) -> (wav, why)
        self.last_end = 0.0

    # ---- what a screen sees ----
    def status(self):
        with self.lock:
            now = dict(self.now) if self.now else None
            speaking = bool(now and now.get("state") in ("making", "playing"))
            return {"ok": True, "speaking": speaking,
                    "quietFor": 0.0 if speaking else round(time.time() - self.last_end, 1)
                    if self.last_end else None,
                    "now": _public(now) if now else None,
                    "queue": [_public(j) for j in self.jobs],
                    "recent": [_public(j) for j in self.recent]}

    # ---- asking ----
    def submit(self, d, who=""):
        d = d if isinstance(d, dict) else {}
        text = str(d.get("text") or "").strip()
        move = str(d.get("move") or "").strip()
        if not text and not move:
            return {"ok": False, "error": "there is nothing to say"}
        when = str(d.get("whenBusy") or "queue")
        if when not in ("queue", "skip"):
            return {"ok": False, "error": "whenBusy is queue or skip, not %r" % when}
        cfg, _ = read_speakers()
        try:
            max_age = float(d.get("maxAgeSeconds") or cfg.get("maxAgeSeconds") or 30)
        except (TypeError, ValueError):
            return {"ok": False, "error": "maxAgeSeconds must be a number"}
        job = {"id": uuid.uuid4().hex[:10], "text": text, "to": str(d.get("to") or ""),
               "voice": str(d.get("voice") or ""), "lang": str(d.get("lang") or ""),
               "move": move, "module": str(d.get("module") or ""),
               "whenBusy": when, "take": bool(d.get("take")),
               "from": str(who or d.get("from") or ""), "at": time.time(),
               "maxAge": max_age, "state": "queued", "why": ""}
        if job["take"]:
            # Explicit only: a greeting never sends it (A5-4). The STREAM OFFs
            # are waited for, or one could land after this job's STREAM ON.
            off_all(self.silence(), wait=3.0)
            if move:
                try:
                    _hub.show.stop(why="taken over by speech")
                except Exception:                            # noqa: BLE001
                    pass
        with self.lock:
            busy, why = self._busy_locked(job)
            if busy and when == "skip" and not job["take"]:
                return self._finish_locked(job, "skipped", why)
            if len(self.jobs) >= int(cfg.get("queueMax") or 8):
                return self._finish_locked(job, "skipped", "too many things are waiting to be said")
            job["gen"] = self.gen
            self.jobs.append(job)
            self.wake.set()
        self._ensure_thread()
        return {"ok": True, "id": job["id"], "state": "queued"}

    def _finish_locked(self, job, state, why):
        job["state"], job["why"], job["ended"] = state, why, time.time()
        self.recent.appendleft(job)
        return {"ok": True, "id": job["id"], "state": state, "why": why}

    def _busy_locked(self, job):
        if self.now is not None:
            return True, "the rig is already saying something"
        if self.jobs:
            return True, "something is already waiting to be said"
        return self._room_busy(job)

    def _room_busy(self, job):
        if _hub.streamer.busy():
            return True, "live sound is playing through a robot"
        if _hub.show.running():
            return True, "a show is playing"
        return False, ""

    # ---- quiet ----
    def silence(self):
        """Stop All's half for speech: nothing queued, nothing playing.
        Never waits on the network; returns {ip: board_off} to turn off."""
        with self.lock:
            self.gen += 1
            for j in list(self.jobs):
                self._finish_locked(j, "cancelled", "stopped")
            self.jobs.clear()
            if self.now:
                self.now["cancel"] = True
        self.pc.stop()
        return _hub.streamer.halt()

    # ---- the worker ----
    def _ensure_thread(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                return
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def _loop(self):
        while True:
            self.wake.wait(1.0)
            with self.lock:
                if not self.jobs:
                    self.wake.clear()
                    continue
                job = self.jobs.popleft()
                job["state"] = "making"
                self.now = job
            try:
                state, why = self._do(job)
            except Exception as e:                           # noqa: BLE001
                state, why = "failed", "%s: %s" % (e.__class__.__name__, e)
            with self.lock:
                self.now = None
                self.last_end = time.time()
                self._finish_locked(job, state, why)

    def _cancelled(self, job):
        if job.get("cancel") or job["gen"] != self.gen:
            return "cancelled", "stopped"
        return None

    def _gone(self, job):
        """(state, why) when this job must not START any more, else None.
        Age counts only until it starts: a long answer is not cut mid-word."""
        if self._cancelled(job):
            return self._cancelled(job)
        if time.time() - job["at"] > job["maxAge"]:
            return "expired", "too late to say it - the moment had passed"
        return None

    def _do(self, job):
        gone = self._gone(job)            # waited too long in the queue: no voice made
        if gone:
            return gone
        cfg, _ = read_speakers()
        rate = int(cfg.get("rate") or 22050)
        wav = None
        speaker = None
        if job["text"]:
            speaker, why = resolve(job["to"], cfg)
            if not speaker:
                return "failed", why
            wav, why = self._make(job["text"], job["voice"] or speaker.get("voice") or "",
                                  job["lang"], rate)
            if why:
                return "failed", why
        # Wait for the room (someone's live sound, a show), then play.
        while True:
            gone = self._gone(job)
            if gone:
                return gone
            busy, _why = (False, "") if job["take"] else self._room_busy(job)
            if not busy:
                break
            time.sleep(WAIT_STEP_S)
        job["state"] = "playing"
        if job["move"]:
            why = self._move(job)
            if why:
                return "failed", why
        if wav is None:
            return "done", ""
        if speaker["kind"] == "pc":
            ok, why = self.pc.play(wav, lambda: bool(self._cancelled(job)))
            return ("done", "") if ok else (self._cancelled(job) or ("failed", why))
        return self._to_board(job, speaker, wav, rate)

    def _make(self, text, voice, lang, rate):
        """Text -> 16-bit WAV bytes, from the voice helper. -> (wav, why)."""
        if self.tts:
            return self.tts(text, voice, lang, rate)
        base, why = _hub.voice_service_url()
        if not base:
            return None, "the voice helper has no address - %s" % why
        body = json.dumps({"text": text, "voice": voice, "lang": lang,
                           "format": "wav", "rate": rate}).encode("utf-8")
        req = urllib.request.Request(base + "/say", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                got = r.read()
        except urllib.error.HTTPError as e:
            try:
                return None, json.loads(e.read().decode("utf-8")).get("error") or str(e)
            except Exception:                                # noqa: BLE001
                return None, "the voice helper refused (%s)" % e.code
        except OSError as e:
            return None, "the voice helper is not running on this PC (%s)" % e
        if not got.startswith(b"RIFF"):
            try:
                return None, json.loads(got.decode("utf-8")).get("error") or "no sound came back"
            except Exception:                                # noqa: BLE001
                return None, "the voice helper sent something that is not a sound"
        return got, ""

    def _move(self, job):
        """The job's move, on its module, through the one show clock."""
        dev = module_dev(job["module"]) if job["module"] else ""
        if not dev:
            return "no robot called %r answered just now" % job["module"]
        f = _hub.SEQUENCES / _hub.safe_name(job["move"])
        if not f.is_file():
            return "there is no saved move called %r" % job["move"]
        try:
            got = _hub.seq_steps(f.read_text(encoding="utf-8"))
            if len(got["steps"]) < 2:          # the rule /api/seqsteps keeps
                return "%s has fewer than two poses - nothing to play" % job["move"]
            _hub.show.start(dev, got["steps"], got.get("loop"), job["move"])
        except (ValueError, KeyError) as e:
            return "the move %r could not start (%s)" % (job["move"], e)
        return ""

    def _to_board(self, job, speaker, wav, rate):
        import stream_audio
        pcm = stream_audio.wav_pcm(wav, rate)
        dev, name = speaker["dev"], speaker["name"]

        def on():
            return _hub.dev_cmd(dev, "STREAM ON %d %d" % (stream_audio.DEF_PORT, rate))

        def off():
            return _hub.dev_cmd(dev, "STREAM OFF")

        while True:
            gone = self._gone(job)
            if gone:
                return gone
            st, why = _hub.streamer.claim(speaker["ip"], stream_audio.DEF_PORT, rate,
                                          "speech", on, off, take=job["take"])
            if st:
                break
            if why == "busy":
                time.sleep(WAIT_STEP_S)
                continue
            if why == "stopped":
                return "cancelled", "stopped"
            if "no speaker" in why.lower():
                NO_SPEAKER[name.lower()] = "no speaker is wired on this board"
                return "failed", "%s has no speaker wired" % name
            return "failed", "%s would not play it (%s)" % (name, why)
        NO_SPEAKER.pop(name.lower(), None)
        session = st["session"]
        _hub.streamer.feed_all(pcm, timeout=len(pcm) / (2.0 * rate) + 10, session=session)
        while _hub.streamer.session == session and _hub.streamer.q.qsize():
            if self._cancelled(job):
                return self._cancelled(job)
            time.sleep(0.05)
        if _hub.streamer.session != session:
            return self._cancelled(job) or ("cancelled", "live sound took over")
        time.sleep(BOARD_TAIL_S)
        if not _hub.streamer.release(session):
            return self._cancelled(job) or ("cancelled", "live sound took over")
        return "done", ""


def off_all(boards, wait=0.0):
    """STREAM OFF to every board in {ip: board_off}, in parallel. `wait` = how
    long to wait for the answers; 0 = do not wait at all."""
    threads = [threading.Thread(target=_quiet_call, args=(off,), daemon=True)
               for off in (boards or {}).values()]
    for th in threads:
        th.start()
    end = time.time() + wait
    for th in threads:
        th.join(max(0.0, end - time.time()))
    return list(boards or {})


def _quiet_call(fn):
    try:
        fn()
    except Exception:                                        # noqa: BLE001
        pass


def _public(job):
    """What a screen may see of a job: no internals."""
    keys = ("id", "text", "to", "from", "state", "why", "move", "module", "whenBusy")
    out = {k: job.get(k) for k in keys}
    out["age"] = round(time.time() - job.get("at", time.time()), 1)
    return out


SPEECH = Speech()
