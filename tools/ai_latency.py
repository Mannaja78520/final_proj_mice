#!/usr/bin/env python3
"""How long the local AI takes, in numbers (asked 2026-11-21: "make AI faster").

    python tools/ai_latency.py                 # 3 warm rounds + 1 cold, Thai + English
    python tools/ai_latency.py --rounds 5 --out docs/experiments/2026-11-21_ai_latency.json

Talks to the same Ollama the hub uses (config/local_ai.json host, model = the
`ollama` provider's think model). Stdlib only, so it runs on the PC as is.
Per question it records: time to first word (what a streamed answer would
feel like), time to the whole answer (what the hub waits for today, because
openai_think does not stream), words per second. COLD = the model unloaded first
(keep_alive 0), i.e. what the first question after a long quiet spell costs.
Budget: 4 rounds x 2 questions; stop rule: do not tune further under 10 % gain.
"""
import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from registry import strip_jsonc  # noqa: E402

QUESTIONS = [("th", "ห้องน้ำอยู่ที่ไหน"), ("en", "Where is the restroom?")]
SYSTEM = "You are a short, polite museum robot. Answer in one or two sentences in the language asked."


def jload(p):
    return json.loads(strip_jsonc(Path(p).read_text(encoding="utf-8")))


def post(host, path, body, stream=False):
    req = urllib.request.Request("http://%s%s" % (host, path), json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120)


def unload(host, model):
    post(host, "/api/generate", {"model": model, "keep_alive": 0}).read()


def ask(host, model, text, max_tokens):
    """-> (first_word_s, total_s, words). Streams so the first word can be timed."""
    t0, first, n = time.perf_counter(), None, 0
    r = post(host, "/v1/chat/completions", {
        "model": model, "stream": True, "temperature": 0, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]})
    for line in r:
        line = line.decode("utf-8", "replace").strip()
        if not line.startswith("data:") or line.endswith("[DONE]"):
            continue
        d = ((json.loads(line[5:]).get("choices") or [{}])[0].get("delta") or {}).get("content")
        if d:
            n += 1                                   # one chunk ~ one token
            first = first or time.perf_counter() - t0
    return first or 0.0, time.perf_counter() - t0, n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out")
    a = ap.parse_args()
    host = jload(ROOT / "config" / "local_ai.json")["host"]
    prov = jload(ROOT / "config" / "voice_providers.json")["providers"]["ollama"]["jobs"]["think"]
    model, mt = prov["model"], int(prov.get("maxTokens", 256))
    rows = []
    unload(host, model)
    for label, rounds in (("cold", 1), ("warm", a.rounds)):
        for _ in range(rounds):
            for lang, q in QUESTIONS:
                f, tot, n = ask(host, model, q, mt)
                rows.append({"state": label, "lang": lang, "first_s": round(f, 3),
                             "total_s": round(tot, 3), "tokens": n,
                             "tok_per_s": round(n / max(tot - f, 1e-6), 1)})
                print(rows[-1])
    for st in ("cold", "warm"):
        r = [x for x in rows if x["state"] == st]
        print("%s: first word median %.2fs, whole answer median %.2fs" % (
            st, statistics.median(x["first_s"] for x in r), statistics.median(x["total_s"] for x in r)))
    if a.out:
        Path(a.out).write_text(json.dumps({"model": model, "host": host, "rows": rows}, indent=1),
                               encoding="utf-8")


if __name__ == "__main__":
    main()
