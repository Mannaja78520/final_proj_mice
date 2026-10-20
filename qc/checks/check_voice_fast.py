"""Long Thai audio keeps its tail; fast hearing preserves every language.

A45-18: measured complete 30 s Thai WAVs lost 25% of their characters in
one decoder window. Ten-second batches kept the tail. Exercise real routing,
lazy generator failures, cache lifetime, and fallback without loading models.
"""
import importlib.util
import json
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import qc as F

AREA = "tools"
TITLE = "fast hearing batches safely, keeps every language, and recovers the actual model"


def run(t):
    spec = importlib.util.spec_from_file_location("voice_fast_check", F.CODE / "apps/voice/service.py")
    svc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = svc
    spec.loader.exec_module(svc)
    calls, built, loaded = [], [], []

    class Model:
        def __init__(self, name, text="heard", fail=False):
            self.name, self.text, self.fail = name, text, fail

        def transcribe(self, path, **kw):
            calls.append((self.name, kw))

            def segments():
                if self.fail:
                    raise RuntimeError("CUDA libraries not found")
                yield SimpleNamespace(text=self.text, no_speech_prob=0.1)
                yield SimpleNamespace(text="not speech", no_speech_prob=0.9)
            return segments(), SimpleNamespace(language=kw.get("language") or "en", language_probability=0.99)

    class Batch:
        def __init__(self, model):
            built.append(model)
            self.model = model

        def transcribe(self, path, **kw):
            if getattr(self.model, "batch_oom", False):
                def failed():
                    raise RuntimeError("CUDA out of memory")
                    yield
                return failed(), SimpleNamespace(language="en")
            return self.model.transcribe(path, **kw)

    def cpu(mid, **kw):
        loaded.append((mid, kw))
        return Model(mid + " cpu", "ไทย")

    def brain():
        b = svc.Brain.__new__(svc.Brain)
        b.cfg = {"stt": {"enabled": True, "model": "small", "beam": 1,
                         "languages": {"th": {"bias": "robot"}, "en": {"bias": "robot"}}},
                 "providers": {"local": {"hear": {"byLanguage": {"th": "thai-model"},
                    "batchSize": 8, "chunkSeconds": 10,
                    "contextByLanguage": {"th": "ตู้มหัศจรรย์ Mice"}}}}}
        b._stt = Model("general")
        b._stt_loaded_model = "small"
        b._stt_own = {"thai-model": Model("thai", "ไทย")}
        b._stt_err = None
        b._lock = threading.Lock()
        return b

    fake = SimpleNamespace(BatchedInferencePipeline=Batch, WhisperModel=cpu)
    with patch.dict(sys.modules, {"faster_whisper": fake}):
        b = brain()
        for lang in ("th", "en", "ja", "zh"):
            before = len(calls)
            text, _ = b._whisper("clip.wav", lang, b.cfg["stt"])
            name, kw = calls[-1]
            t.eq(len(calls), before + 1, lang + " is decoded once")
            t.eq(name, "thai" if lang == "th" else "general", lang + " keeps its own model route")
            t.eq(kw.get("language"), lang, lang + " reaches the recogniser unchanged")
            t.ok(kw.get("chunk_length") == 10 and kw.get("batch_size") == 8,
                 lang + " uses bounded ten-second batches", repr(kw))
            t.ok("not speech" not in text, lang + " still discards non-speech segments", text)
            t.eq("ตู้มหัศจรรย์" in str(kw.get("initial_prompt")), lang == "th",
                 lang + " gets only its own language context")
        b._whisper("again.wav", "th", b.cfg["stt"])
        t.eq(sum(m is b._stt_own["thai-model"] for m in built), 1,
             "a model's batch pipeline is reused, not rebuilt per utterance")

        # A failure thrown while iterating must replace the failed Thai model,
        # not merely load a CPU general model then select the broken Thai again.
        b = brain()
        general = b._stt
        b._stt_own["thai-model"] = Model("broken Thai GPU", fail=True)
        got, why = b._listen_local(b"test clip", "th", b.cfg["stt"])
        t.ok(got and got["text"] == "ไทย" and why is None,
             "a lazy CUDA failure recovers and actually hears the Thai clip", repr((got, why)))
        t.ok(loaded and loaded[-1][0] == "thai-model" and loaded[-1][1].get("device") == "cpu",
             "the failing byLanguage model is reloaded on CPU", repr(loaded))
        t.ok(b._stt is general and not b._stt_own["thai-model"].fail,
             "CPU recovery replaces the own model and preserves the general model")
        t.ok(all(not m.fail for m in (batch.model for batch in b._stt_batches.values())),
             "a failed specialist is not retained by an old batch pipeline")

        b = brain()
        b._stt.batch_oom = True
        got, _ = b._whisper("large.wav", "en", b.cfg["stt"])
        t.eq(got, "heard", "a lazy batch memory failure gets one smaller serial retry")
        t.ok("batch_size" not in calls[-1][1], "the memory retry actually leaves the batch API")
        t.ok(not b._stt_batches, "the failing batch pipeline is released")

        b = brain()
        b.cfg["stt"]["fallback"] = {"language": "th", "when_not_in": ["th"]}
        b._detect = lambda *_: None
        b._own_model = lambda _: (_ for _ in ()).throw(OSError("specialist unavailable"))
        got, info = b._whisper("detect.wav", None, b.cfg["stt"])
        t.ok(got == "heard" and info.language == "th",
             "an unavailable specialist preserves a general language fallback", repr((got, info)))

        b = brain()
        b._whisper("cached.wav", "th", b.cfg["stt"])
        with patch.dict(sys.modules, {"torch": SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))}):
            b.unload()
        t.ok(not b._stt_batches and not b._stt_own and b._stt_attempt_model is None,
             "unload releases batch wrappers and their model references")

    # Existing installs without the batched API retain their serial listener.
    with patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=cpu)}):
        b = brain()
        got, _ = b._whisper("old-library.wav", "en", b.cfg["stt"])
        t.eq(got, "heard", "an older listener without the batched API still works")

    _answers(t, svc)
    _synthesis(t, svc)


def _answers(t, svc):
    b = svc.Brain.__new__(svc.Brain)
    b.cfg = {"faqThreshold": 0.75}
    b.faq_path = F.CODE / "apps/voice/qa_data.json"
    for text, expected in (("สวัสดีครับ", "สวัสดี"), ("hello", "Hello"),
                           ("こんにちは", ""), ("你好", ""), ("你好！", ""),
                           ("你好。", ""), ("hi!", ""), ("bye!", "")):
        hit, score = b.match_faq(text)
        t.ok(hit is not None, "a standalone greeting still works: " + text, repr(score))
        if expected:
            t.ok(expected.lower() in (hit or {}).get("answer", "").lower(),
                 "the greeting keeps its saved meaning: " + text, repr(hit))
    for text in ("สวัสดีครับ อยากทราบว่าหุ่นยนต์ใช้มอเตอร์แบบไหนและควบคุมด้วยบอร์ดอะไรครับ",
                 "ผมเป็นนักศึกษาวิศวกรรม อยากทราบหลักการควบคุมมอเตอร์ ขอบคุณครับ",
                 "Hello, can you explain which motor and controller this robot uses?",
                 "こんにちは、このロボットのモーターと制御基板について教えてください",
                 "你好，请解释这个机器人的电机和控制器是如何工作的"):
        hit, score = b.match_faq(text)
        t.ok(not hit or not hit.get("wholeQuestion"),
             "an incidental greeting or thanks cannot replace a substantive question", repr((text, score, hit)))
        t.ok(not hit or not hit.get("move"),
             "a substantive question cannot accidentally launch a greeting move", repr(hit))
    hit, score = b.match_faq("วันนี้งานเปิดถึงกี่โมง", lang="th")
    t.ok(hit and "17:00" in hit.get("answer", ""),
         "the closing-hours paraphrase uses verified saved hours, not invented time", repr((score, hit)))
    hit, score = b.match_faq("ขอถ่ายรูปกับหุ่นยนต์ได้ไหม", lang="th")
    t.ok(hit and "ยืนข้าง" in hit.get("answer", ""),
         "the existing lower-score photo question still works", repr((score, hit)))


def _synthesis(t, svc):
    with tempfile.TemporaryDirectory() as folder:
        b = svc.Brain.__new__(svc.Brain)
        b._tts_lock = threading.Lock()
        b._cache_path = lambda ident, text, **_: Path(folder) / (ident + ".wav")
        audio = svc.providers.pcm_wav(b"\x01\x02" * 500)
        entered, release, foreground = threading.Event(), threading.Event(), threading.Event()
        made, errors = [], []

        def background():
            entered.set()
            release.wait(4)
            made.append("background")
            return audio, None

        def one(ident, make):
            try:
                return b._spoken(ident, "answer", "", "", make)
            except Exception as error:
                errors.append(repr(error))

        worker = threading.Thread(target=one, args=("background", background))
        worker.start()
        try:
            t.ok(entered.wait(2), "the prebuilder is synthesising a different line")
            visitor = threading.Thread(target=one, args=("visitor", lambda: (foreground.set() or audio, None)))
            visitor.start()
            t.ok(foreground.wait(2), "a visitor does not wait behind a slow background line")
        finally:
            release.set()
            worker.join(5)
            if "visitor" in locals():
                visitor.join(5)
        t.ok(not errors, "concurrent synthesis completes without errors", repr(errors))
        count = []
        jobs = [threading.Thread(target=one, args=("same", lambda: (count.append(1) or audio, None)))
                for _ in range(4)]
        for job in jobs:
            job.start()
        for job in jobs:
            job.join(5)
        t.eq(len(count), 1, "concurrent requests for one line build one sound")
        t.ok(not b._tts_keys and not errors, "completed synthesis releases every per-line lock", repr(errors))
