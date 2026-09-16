#!/usr/bin/env python3
"""Ask several models ON THIS PC the same question, and collect what they say.

    python tools/local_panel.py --ask "does FWEND refuse a short image?" \
        --file firmware/src/core/BusUpdate.cpp --out local_review.md

    python tools/local_panel.py --list          which models are installed
    python tools/local_panel.py --ask "..." --models deepseek-coder-v2:16b,llama3.1:8b

WHY THIS EXISTS ALONGSIDE ai_panel.py
------------------------------------
`tools/ai_panel.py` asks the big models through Antigravity. It is the better
reviewer and it stays. But it has two costs this one does not:

  * it needs the NETWORK, and an unreliable link is not free. Measured
    2026-08-20: one panel run spent 676,387 tokens and returned nothing at all,
    because every model read files for ten minutes and only THEN hit the error.
    The work is billed before the failure;
  * it spends the user's quota. Asked for 2026-08-20: *if the voice very less
    you can use llama in my pc as another voice*.

A model on this PC costs nothing per token and cannot be cut off.

WHAT IT IS NOT FOR, MEASURED RATHER THAN GUESSED
------------------------------------------------
Do NOT ask these models whether code is correct. Benchmarked 2026-08-20 against
a bug with a known answer - the pre-fix BusUpdate.cpp, where the md5 was
optional so a damaged image could boot, which a Sonnet subagent had found hours
earlier. Two models, two briefs, four runs, four misses. And they were not quiet
misses:

  * deepseek-coder-v2:16b quoted the `written_ != total_` guard and called it
    the line that ALLOWS corruption. That guard prevents it. Then it reported
    three missing checks - base64 validity, chunk length - that are all written
    in the file it was reading;
  * qwen2.5-coder:14b said a sender would have to fail the final md5 check,
    which ASSUMES the md5 was registered. That assumption is the bug.

Both pattern-matched `Update.end(true)` to "md5 verified" without tracing
whether `setMD5` had ever been called. Confidently wrong about code in front of
them is the most expensive way for a review to fail, and this project has been
burnt by it before.

So: use this for questions whose answer can be CHECKED in seconds - which file
defines this, does this string appear, what calls this - and for throwing up
alternatives when a wrong idea is cheap. Every line it returns is a shortlist to
read the code against, never a fact.

THE BRIEF: TERSE IS FINE, AND IT IS NOT WHY THEY ARE WRONG
----------------------------------------------------------
The same benchmark ran each model under the terse `ai_brief.txt` and under a
brief that invited step-by-step reasoning first. Correctness was identical -
wrong both times - while the terse answers were about 2.4x shorter (110-168
tokens against 244-417). Locally an output token costs seconds rather than
money, so brevity buys time and, on this evidence, costs no accuracy. Keep the
terse brief; do not expect it to be the difference between right and wrong.

WHY DIFFERENT FAMILIES, NOT JUST MORE MODELS
--------------------------------------------
The user's reason, 2026-08-20: *more model from different provider it have
different idea*. Two models from one maker share their training and their blind
spots, so the second one mostly agrees and teaches you nothing. The default set
is deliberately one model each from DeepSeek, Meta, Alibaba, Microsoft and
Google.

Worth knowing when adding more: a DeepSeek-R1 *distill* is not an independent
model. `deepseek-r1:8b` is distilled from Llama and `deepseek-r1:14b` from Qwen,
so they inherit that base's blind spots while wearing another name - which is
the one thing this file is trying to avoid.

WHY THE HTTP API AND NOT `ollama run`
-------------------------------------
`ollama run` uses whatever context length the model's Modelfile happens to set,
and for many that is 4096 tokens. A source file longer than that is then
silently truncated - the model answers confidently about code it never saw,
which is the exact failure this project keeps having to design against. The API
lets `num_ctx` be set explicitly, and this file says out loud when a file had to
be cut.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "tools" / "ai_brief.txt"
OLLAMA = "http://127.0.0.1:11434"

# One from each maker. See the note above on why that matters more than count.
PANEL = [
    "deepseek-coder-v2:16b",   # DeepSeek - real MoE, code-trained
    "llama3.1:8b",             # Meta
    "qwen2.5-coder:14b",       # Alibaba
    "phi4:14b",                # Microsoft
    "gemma3:12b",              # Google
]

# How much of a file to show. Big enough for any single source file in this
# project, small enough that a 7B model still answers in under a minute.
FILE_CHARS = 24000
NUM_CTX = 16384


def installed():
    """What ollama actually has, so a missing model is named and not guessed."""
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=10) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception as e:                                    # noqa: BLE001
        raise SystemExit(
            "ollama is not answering on %s (%s).\n"
            "Start it (the Ollama app, or `ollama serve`) and try again."
            % (OLLAMA, e))


def ask(model, prompt, seconds=600):
    """One model, one answer. A failure is returned AS a failure, never as ''.

    The same rule ai_panel.py had to learn: an empty answer printed beside a
    model's name reads as *found no problems* and can mean *never ran*.
    """
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            # Low, not zero: these are review answers, and a little variation
            # is what makes a second opinion worth having at all.
            "temperature": 0.3,
        },
    }).encode()
    t0 = time.time()
    try:
        req = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=seconds) as r:
            d = json.loads(r.read())
        return {"model": model, "text": (d.get("response") or "").strip(),
                "secs": time.time() - t0, "error": ""}
    except Exception as e:                                    # noqa: BLE001
        return {"model": model, "text": "", "secs": time.time() - t0,
                "error": str(e)[:160]}


def gather(paths):
    """The files, and an honest note when one had to be cut short."""
    out, notes = [], []
    for p in paths:
        f = Path(p)
        if not f.is_absolute():
            f = ROOT / p
        if not f.is_file():
            notes.append("%s does not exist" % p)
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if len(text) > FILE_CHARS:
            # SAY SO. A model answering about the half of a file it was shown,
            # with nothing marking the cut, is how a review becomes confident
            # nonsense.
            text = text[:FILE_CHARS] + "\n... [CUT - file continues]\n"
            notes.append("%s was cut to %d characters" % (p, FILE_CHARS))
        out.append("----- %s -----\n%s" % (p, text))
    return "\n\n".join(out), notes


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ask", help="the question")
    ap.add_argument("--file", action="append", default=[],
                    help="a file to show them; repeat for several")
    ap.add_argument("--models", help="comma-separated; default the whole panel")
    ap.add_argument("--out", help="write the report here as markdown")
    ap.add_argument("--lines", type=int, default=12,
                    help="line budget per model (default 12)")
    ap.add_argument("--list", action="store_true",
                    help="what is installed, and what the panel wants")
    a = ap.parse_args(argv)

    have = installed()
    if a.list:
        print("installed on this PC:")
        for m in have:
            print("   " + m)
        missing = [m for m in PANEL if m not in have]
        print("\npanel wants: " + ", ".join(PANEL))
        if missing:
            print("MISSING (ollama pull <name>): " + ", ".join(missing))
        else:
            print("every panel model is here.")
        return 0

    if not a.ask:
        ap.error("--ask is required (or --list)")

    want = [m.strip() for m in a.models.split(",")] if a.models else PANEL
    # A model that is not installed is NAMED, not quietly skipped: a panel that
    # ran three of five voices and said nothing about it is a panel you would
    # over-trust.
    missing = [m for m in want if m not in have]
    models = [m for m in want if m in have]
    if not models:
        raise SystemExit("none of those models are installed. Have: %s"
                         % ", ".join(have))

    files, notes = gather(a.file)
    brief = BRIEF.read_text(encoding="utf-8") if BRIEF.is_file() else ""
    prompt = "\n".join([
        brief,
        "You are reviewing real code. Answer in at most %d lines." % a.lines,
        "Name a file and a line for every claim. If the files do not show "
        "enough to judge, say exactly that instead of guessing.",
        "",
        "QUESTION: " + a.ask,
        "",
        files,
    ])

    print("asking %d local model(s), one at a time (12 GB of VRAM holds one)"
          % len(models))
    answers = []
    for m in models:
        print("   %-24s ..." % m, end="", flush=True)
        r = ask(m, prompt)
        print(" %s (%.0fs)" % ("FAILED" if r["error"] else "ok", r["secs"]))
        answers.append(r)

    spoke = [r for r in answers if r["text"] and not r["error"]]
    lines = ["# Local panel - %s" % time.strftime("%Y-%m-%d %H:%M"), "",
             "**Question.** " + a.ask, ""]
    if not spoke:
        lines += ["> **NO REVIEW HAPPENED.** Every local model failed, so "
                  "nothing below is a judgement about the code. Do not read "
                  "the absence of findings as approval.", ""]
    if missing:
        lines += ["> Not installed, so they did not speak: %s"
                  % ", ".join(missing), ""]
    if notes:
        lines += ["> Files trimmed or missing: %s" % "; ".join(notes), ""]
    lines += ["**Files.** " + (", ".join(a.file) or "(none)"),
              "**Cost.** nothing - these ran on this PC", ""]
    for r in answers:
        lines += ["## %s  _(%.0fs)_" % (r["model"], r["secs"]), ""]
        lines += ["**FAILED** " + r["error"]] if r["error"] else \
                 [r["text"] or "**FAILED** the model returned nothing"]
        lines += [""]
    lines += ["---", "",
              "Every finding above is a SHORTLIST, not a fact. Check each one "
              "against the code before changing anything: these are small "
              "models, and a confident wrong answer costs more than a quiet "
              "one."]
    report = "\n".join(lines)

    if a.out:
        Path(a.out).write_text(report, encoding="utf-8")
        print("\nwrote " + a.out)
    else:
        print("\n" + report)
    return 0 if spoke else 3


if __name__ == "__main__":
    raise SystemExit(main())
