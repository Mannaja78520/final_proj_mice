"""The user's own recorded voice: two switches, both OFF, and no personal data in Git.

User 2026-11-06: a 16-minute recording of their own speech should be usable
two ways - as the reference voice of the Thai feeling voice, and as fixed
clips played for named events - each switchable, the audio and transcripts
kept in .local (the repo is public). This check holds:

  * config/voice_clips.json ships OFF and empty: no clip names, no transcript,
    no speaker tokens, so the voice is exactly what it was before;
  * switched off, a recording in the character's voice/ folder changes nothing;
    switched on, speaker.json becomes the voice "person:user-voice" (32 tokens)
    and an event with a clip returns that file; an event with no clip, a
    missing file, or a name with path parts falls back (None) to the speak voice;
  * the service lists the voice and serves the clip only through UserVoice;
  * tools/voice_clips.py cuts a long speech run at its quietest point, keeps
    every clip within minSeconds..maxSeconds and puts no lead/tail on an inner cut;
  * no audio or speaker file is tracked under config/ (git ls-files).

Tested against fakes: whether the recorded voice SOUNDS right is a person's call.
"""
import importlib.util
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the user's recorded voice: reference + event clips, off by default, nothing personal in Git"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _wav(path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\0\0" * 2400)


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    cfg_path = F.CODE / "config" / "voice_clips.json"
    import registry
    cfg = registry.load(cfg_path)
    _defaults(t, cfg)
    uv = _load("mice_user_voice", "apps/voice/user_voice.py")
    tmp = Path(tempfile.mkdtemp(prefix="qc_uservoice_"))
    try:
        _switches(t, uv, cfg, tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    _service(t)
    _cut(t)
    _tracked(t)


def _defaults(t, cfg):
    ref, ev = cfg.get("reference") or {}, cfg.get("events") or {}
    t.ok(ref.get("enabled") is False and ev.get("enabled") is False,
         "both uses ship switched OFF", (ref.get("enabled"), ev.get("enabled")))
    t.ok(not ref.get("clips") and not ref.get("text") and not ev.get("clips"),
         "no clip name, transcript or event mapping ships in Git", (ref.get("clips"), ev.get("clips")))
    t.ok("speaker" not in ref and "speaker" not in json.dumps(cfg),
         "no speaker tokens ship in Git")


def _switches(t, uv, cfg, tmp):
    folder = tmp / "voice"
    folder.mkdir()
    _wav(folder / "hello.wav")
    _wav(tmp / "outside.wav")                           # a real file one level up: ../ must not reach it
    (folder / "speaker.json").write_text(json.dumps({"speaker": list(range(32))}), encoding="utf-8")

    def user(change):
        box = json.loads(json.dumps(cfg))
        for key, val in change.items():
            box[key].update(val)
        path = tmp / "voice_clips.json"
        path.write_text(json.dumps(box), encoding="utf-8")
        return uv.UserVoice(path)

    off = user({})
    t.ok(off.person(folder) is None and off.event_clip(folder, "welcome") is None,
         "switched off, a recording in the voice folder changes nothing")
    on_ref = user({"reference": {"enabled": True, "gender": "male", "backup": "th-TH-NiwatNeural"}})
    who = on_ref.person(folder)
    t.ok(who and who["speaker"] == list(range(32)) and who["gender"] == "male"
         and who["backup"] == "th-TH-NiwatNeural" and who["languages"] == ["th"],
         "reference on: speaker.json is a saved voice with its gender and backup", who)
    t.ok(on_ref.person(tmp / "nowhere") is None and on_ref.person(None) is None,
         "reference on but no speaker.json yet: no voice is offered")
    on_ev = user({"events": {"enabled": True, "clips": {"welcome": "hello.wav", "gone": "nope.wav",
                                                        "evil": "../outside.wav", "text": "hello.txt"}}})
    t.eq(on_ev.event_clip(folder, "welcome"), folder / "hello.wav", "events on: the event's clip is returned")
    t.ok(on_ev.event_clip(folder, "other") is None, "an event with no clip falls back to the speak voice")
    t.ok(on_ev.event_clip(folder, "gone") is None, "a clip file that is missing falls back to the speak voice")
    t.ok(on_ev.event_clip(folder, "evil") is None and on_ev.event_clip(folder, "text") is None,
         "a name with path parts, or not a wav, is never served")
    t.ok(user({"events": {"enabled": False, "clips": {"welcome": "hello.wav"}}}).event_clip(folder, "welcome") is None,
         "events off: a mapped clip is not used")


def _service(t):
    text = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    t.ok("{USER_PERSON: extra}" in text and 'req.get("event")' in text and ".event_clip(" in text,
         "the helper lists the recorded voice and plays an event clip through UserVoice")
    folder = (F.CODE / "config" / "voice_profiles.json").read_text(encoding="utf-8")
    t.ok('"voice"' in folder, "the character folder has a voice/ asset kind")


def _cut(t):
    vc = _load("mice_voice_clips", "tools/voice_clips.py")
    import numpy as np
    cut = {"minSeconds": 3, "maxSeconds": 15, "leadSeconds": 0.12, "tailSeconds": 0.2}
    env = np.ones(int(60 / vc.FRAME))
    env[int(24.0 / vc.FRAME)] = 0.0                     # the only quiet spot of a 40 s run
    clips = vc.plan([(5.0, 45.0)], env, cut)
    long = [c[1] - c[0] + 0.32 for c in clips]
    t.ok(all(3 <= d <= 15 for d in long) and len(clips) >= 3,
         "a 40 s run becomes clips of 3-15 s each", [round(d, 2) for d in long])
    t.ok(any(abs(c[1] - 24.0) < 0.1 for c in clips), "a long run is split at its quietest point",
         [(round(c[0], 1), round(c[1], 1)) for c in clips])
    t.ok(clips[0][3] and clips[1][2] and not clips[0][2] and not clips[-1][3],
         "an inner cut gets no lead/tail, a real edge does", [(c[2], c[3]) for c in clips])
    short = vc.plan([(0.0, 1.0), (10.0, 12.0)], np.ones(2000), cut)
    t.ok(short == [], "speech shorter than minSeconds is dropped", short)


def _tracked(t):
    out = subprocess.run(["git", "ls-files", "config"], cwd=str(F.CODE), capture_output=True, text=True).stdout
    bad = [p for p in out.split() if p.lower().endswith((".wav", ".m4a", ".mp3")) or p.endswith("speaker.json")]
    t.ok(not bad, "no audio or speaker file is tracked under config/", bad)
