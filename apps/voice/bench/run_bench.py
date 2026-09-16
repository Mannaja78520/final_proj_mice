#!/usr/bin/env python3
"""The voice bench - numbers before opinions (A20-6, asked 2026-08-22).

bench/cases.json holds ~25 fixed questions, each with its expected text and
the one saved answer a correct rig gives back. This script turns them into
three numbers:

    error rate   how badly speech-in mangles the question (needs STT, A20-7;
                 until then this half says plainly it cannot run here)
    answer hits  how often the rig replies with exactly the right saved answer
    latency      milliseconds per part: recognise / answer

Nothing after A20-6 may be called better without moving one of these.

Usage (from the code folder):
    python apps\\voice\\bench\\run_bench.py --prepare    # speak the questions
    python apps\\voice\\bench\\run_bench.py              # measure what is installed
    python apps\\voice\\bench\\run_bench.py --selfcheck  # validate cases only

--prepare needs edge-tts and internet; it writes bench/audio/<id>.mp3.
Thai has no spaces between words, so its error rate counts CHARACTERS (CER);
English counts WORDS (WER). Both come from the same edit-distance routine.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BENCH = Path(__file__).resolve().parent
CODE = BENCH.parents[2]                       # apps/voice/bench -> code
CASES = BENCH / "cases.json"
AUDIO = BENCH / "audio"

VOICE_DEFAULTS = {"th": "th-TH-PremwadeeNeural", "en": "en-US-AriaNeural"}

# Languages written WITHOUT spaces between words: their error rate counts
# characters (CER), everyone else's counts words (WER). A new unsegmented
# language means one code here; a normal one needs nothing anywhere.
CHAR_LANGS = {"th", "lo", "my", "km", "ja", "zh"}


def load_config():
    """config/voice.json - the same store the hub and helper read, with the
    same MICE_VOICE_CONFIG override the hub honours."""
    path = Path(os.environ.get("MICE_VOICE_CONFIG")
                or (CODE / "config" / "voice.json"))
    try:
        sys.path.insert(0, str(CODE / "tools"))
        import registry
        return registry.load(path) or {}
    except Exception as e:                          # noqa: BLE001
        print("%s unreadable (%s) - using defaults" % (path.name, e))
        return {}


def load_cases():
    """(cases, problems). The file is data; its shape is checked here."""
    try:
        sys.path.insert(0, str(CODE / "tools"))
        import registry
        raw = registry.load(CASES)
    except Exception as e:                          # noqa: BLE001
        return [], ["cases.json could not be read: %s" % e]
    cases = raw.get("cases") if isinstance(raw, dict) else None
    if not cases:
        return [], ["cases.json holds no `cases` list"]
    seen, bad = set(), []
    for c in cases:
        cid = c.get("id", "?")
        if not c.get("text"):
            bad.append("%s: no text" % cid)
        elif "expectAnswer" not in c:
            bad.append("%s: no expectAnswer" % cid)
        elif not (c.get("lang") or "").strip():
            bad.append("%s: no lang" % cid)     # any language code is allowed
        elif cid in seen:
            bad.append("%s: duplicate id" % cid)
        else:
            seen.add(cid)
    return cases, bad


def audio_path(cid):
    for ext in (".wav", ".mp3"):        # .wav wins: a human recording beats synth
        p = AUDIO / (cid + ext)
        if p.exists():
            return p
    return None


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def tokens(text, lang):
    # Unsegmented scripts count characters; spaced languages count words.
    if lang in CHAR_LANGS:
        return list(text.replace(" ", ""))
    return text.split()


def err_rate(ref, hyp, lang):
    # The recogniser adds capitals and punctuation the expected text lacks;
    # strip both before counting or a PERFECT transcript scores 100% wrong.
    def clean(s):
        return re.sub(r"[^\w\s]+", "", (s or "").lower(), flags=re.UNICODE)
    r = tokens(clean(ref), lang)
    if not r:
        return 0.0 if not clean(hyp) else 1.0
    return edit_distance(r, tokens(clean(hyp), lang)) / len(r)


def make_stt(cfgv):
    """fn(wav_path, lang) -> text, or (None, why-not). A20-7 fills this in."""
    scfg = cfgv.get("stt") or {}
    if not scfg.get("enabled"):
        # Off in the store is a decision, not a fault - same rule as the LLM.
        return None, "speech-in is switched off in config/voice.json"
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, ("faster_whisper is not installed on this PC - "
                      "the error-rate half cannot run yet")
    mdl = WhisperModel(scfg.get("model", "small"),
                       device="auto", compute_type="auto")

    def fn(path, lang):
        segs, _info = mdl.transcribe(str(path), language=lang,
                                     condition_on_previous_text=False)
        return "".join(s.text for s in segs).strip()
    return fn, None


def prepare(cases):
    """Speak every question that has no recording yet."""
    try:
        import edge_tts
    except ImportError:
        print("edge-tts is not installed:  pip install edge-tts")
        print("(it also needs internet when it speaks)")
        return 1
    AUDIO.mkdir(exist_ok=True)
    todo = [c for c in cases if not audio_path(c["id"])]
    if not todo:
        print("every case already has a recording in %s" % AUDIO.name)
        return 0

    async def run():
        done = skipped = 0
        for c in todo:                       # one at a time: kinder to the API
            voice = c.get("ttsVoice") or VOICE_DEFAULTS.get(c["lang"])
            if not voice:
                print("SKIP %s no known voice for %s - set ttsVoice in "
                      "cases.json" % (c["id"], c["lang"]))
                skipped += 1
                continue
            out = AUDIO / (c["id"] + ".mp3")
            await edge_tts.Communicate(c["text"], voice).save(str(out))
            print("spoke %s" % c["id"])
            done += 1
        return done, skipped

    n, skipped = asyncio.run(run())
    print("%d recording(s) written to %s%s"
          % (n, AUDIO,
             ", %d skipped (no voice)" % skipped if skipped else ""))
    return 0


def ask(base, text):
    """(response, ms, net_error). response is {'ok': False, 'error': ...} when
    the helper answered with an error, None when nothing answered at all; the
    third item names a connection failure and is None otherwise."""
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/ask", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=200) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            resp = json.loads(e.read().decode("utf-8"))
        except ValueError:
            resp = {"ok": False, "error": "HTTP %s" % e.code}
    except (urllib.error.URLError, OSError) as e:
        return None, round((time.perf_counter() - t0) * 1000), str(e)
    return resp, round((time.perf_counter() - t0) * 1000), None


def norm(s):
    return " ".join((s or "").split())


def measure(args):
    cfgv = load_config()
    base = args.service or (cfgv.get("service") or "").rstrip("/")
    cases, bad = load_cases()
    if bad:
        for b in bad:
            print("CASES BROKEN: " + b)
        return 2

    stt, why_not = make_stt(cfgv)           # None on this PC until A20-7 lands
    misses, errs = [], []                   # errs: (lang, rate) for spoken cases
    hit = typed_only = audio_n = dead = 0
    ask_ms, stt_ms = [], []

    for c in cases:
        path = audio_path(c["id"])
        text, how, e_ms = c["text"], "typed", None
        if path and stt:
            t0 = time.perf_counter()
            got = stt(path, c["lang"]) or ""    # an EMPTY transcript is a real
            e_ms = round((time.perf_counter() - t0) * 1000)   # result: 100% wrong
            text, how, audio_n = got, "spoken", audio_n + 1
            errs.append((c["lang"], err_rate(c["text"], got, c["lang"])))
        elif not path:
            print("SKIP %-11s no recording - run --prepare" % c["id"])
        if how == "typed":                  # no recording OR no recogniser:
            typed_only += 1                 # either way this run is typed text

        resp, ms, net_err = ask(base, text) if base else (None, 0, "no service address")
        if net_err or resp is None:
            dead += 1
            if dead == 1:                    # one full reason, not 25 copies
                why = net_err or "timed out"
                print("ERR  %-11s the rig did not answer: %s" % (c["id"], why))
            continue
        if e_ms is not None:
            stt_ms.append(e_ms)
        ask_ms.append(ms)
        if resp.get("ok") and norm(resp.get("answer")) == norm(c["expectAnswer"]):
            hit += 1
            print("ok   %-11s %-7s answer %4d ms  %s"
                  % (c["id"], how, ms, resp.get("source", "")))
        else:
            misses.append((c["id"], how, c["expectAnswer"], resp.get("answer"),
                           resp.get("error")))

    measured = hit + len(misses)
    for cid, how, want, got, err in misses:
        print("MISS %-11s %-7s" % (cid, how))
        print("       wanted: %s" % want)
        print("       got:    %s" % (got or err))

    # The headline numbers. Error rate prints ONLY when speech really ran -
    # a typed bench says nothing about a microphone rig.
    print("")
    if dead:
        print("ERR  %d case(s) got no answer at all from %s" % (dead, base or "(none)"))
    print("answer hits %d/%d%s" % (
        hit, measured, " (%d%%)" % round(100 * hit / measured) if measured else ""))
    for lang in sorted({l for l, _r in errs}):
        rs = [r for l, r in errs if l == lang]
        label = "CER" if lang in CHAR_LANGS else "WER"
        print("error rate  %s %s (%s) over %d spoken case(s)"
              % (lang, "%.1f%%" % (100 * sum(rs) / len(rs)), label, len(rs)))
    if not errs and stt is None and why_not:
        print("error rate  not measured - " + why_not)
    if ask_ms:
        ask_ms.sort()
        mid = ask_ms[len(ask_ms) // 2]
        rec = ("%d ms" % sorted(stt_ms)[len(stt_ms) // 2]) if stt_ms else "n/a"
        print("latency     recognise median %s · answer median %d ms" % (rec, mid))
    if typed_only:
        print("(%d case(s) ran as TYPED text - speech-in did not run for them)"
              % typed_only)
    if not measured:
        print("NOTHING was measured - the numbers above are not evidence.")
        return 1
    return 0


def selfcheck():
    cases, bad = load_cases()
    for b in bad:
        print("BROKEN: " + b)
    th = sum(1 for c in cases if c["lang"] == "th")
    en = sum(1 for c in cases if c["lang"] == "en")
    print("%d cases ok (%d th, %d en)" % (len(cases), th, en))
    return 2 if bad or len(cases) < 25 else 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                               # noqa: BLE001
        pass                                        # old console; printing may mangle Thai
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepare", action="store_true",
                    help="speak the questions that have no recording yet")
    ap.add_argument("--service", default=None,
                    help="helper address to measure (default: config/voice.json)")
    ap.add_argument("--selfcheck", action="store_true",
                    help="validate cases.json and exit - no deps needed")
    args = ap.parse_args()

    cases, _bad = load_cases()
    if args.selfcheck:
        return selfcheck()
    if args.prepare:
        return prepare(cases)
    return measure(args)


if __name__ == "__main__":
    sys.exit(main())
