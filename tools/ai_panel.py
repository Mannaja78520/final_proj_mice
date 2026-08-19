#!/usr/bin/env python3
"""Ask several models the same question, then have one judge the answers.

    python tools/ai_panel.py --dir shared/web --ask "what is wrong with themes.css"
    python tools/ai_panel.py --dir . --ask "..." --models gemini-3.1-pro-high,claude-opus-4-6-thinking
    python tools/ai_panel.py --list                       which models exist today

WHY
---
The user's standing instruction, 2026-08-18 and again 2026-08-19: do not trust
one model, have several check the same thing and let them disagree - and make
one of them the head that judges the rest. This is that, as a command, because
doing it by hand meant it happened when it was convenient rather than always.

WHAT IT DOES
------------
1. Sends the SAME question to every model in the panel, in parallel.
2. Collects the answers into one report.
3. Sends the answers to the HEAD model, which is asked to say which findings
   are real, which are wrong, and which cannot be told from the files.

WHAT IT COSTS, MEASURED
-----------------------
One call is never cheap: every model starts with about 24k tokens of its own
prompt and tools before it reads anything. Measured 2026-08-19 on one small
file:

    claude-opus-4-6-thinking    25k tokens   answered in one turn
    gemini-3.1-pro-high         16k tokens   as the head, reading findings only
    gemini-3.7-flash-high      163k tokens   explored for several turns

So a three-model panel on one question is roughly 60k-200k tokens. That is a
decision-point tool, not something to run per file: use it before building
something with a design in it, and before promoting work that a person will
look at. Routine questions go to one model, or to nobody.

Two things here keep the cost down. The SCHEMA stops a model writing an essay -
it turned a 2928 character answer into two lines. And the head reviewer is
given findings as data rather than three transcripts, which was previously the
most expensive part of a run.

WHAT IT DOES NOT DO
-------------------
It does not decide anything. The head's verdict is a shortlist, not a fact:
every finding is still checked against the code before anything is changed.
This project has already had a model be confidently wrong twice in one day -
once claiming a poll used the wrong endpoint, once inventing a shared variable
that was a per-call argument - and the check that caught both was reading the
code, not asking a fourth model.

THE TWO TRAPS THIS TOOL EXISTS TO AVOID
---------------------------------------
* `agy` picks the main tree as its workspace and skips dot-directories, so a
  question about unpromoted work in `.staging` gets answered about the last
  PROMOTED version - with nothing in the answer saying so. Two reviews came
  back "file not present" and one reviewed the wrong version confidently.
  It CAN read `.staging` when the directory is named: --add-dir reaches it,
  measured by asking for a value that had existed for four minutes and only
  there. So this names the real directories and reviews the real files. An
  earlier version copied them somewhere plain first, which worked and was
  worse: a copy is a second thing that can go stale, and the point is to
  review exactly what is about to be promoted.
* A prompt may not contain a double quote: `agy` truncates there silently and
  answers confidently about the half it saw. Quotes are replaced here rather
  than hoping the caller remembered.
"""
import argparse
import json
import shutil
import tempfile
import concurrent.futures as cf
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if ROOT.name == ".staging":
    REAL = ROOT.parent
else:
    REAL = ROOT
BRIEF = ROOT / "tools" / "ai_brief.txt"

# The panel. Different FAMILIES, deliberately: two models from one family tend
# to be wrong in the same way, which is the thing a panel is supposed to fix.
PANEL = ["gemini-3.1-pro-high", "claude-opus-4-6-thinking", "gpt-oss-120b-medium"]
HEAD = "gemini-3.1-pro-high"

# The SHAPE of an answer, enforced by agy rather than asked for in words.
# Measured 2026-08-19 on the same question with the same terse brief:
#     gemini-3.1-pro-high        344 chars    honoured the budget
#     claude-opus-4-6-thinking  2928 chars    ignored it
#     gpt-oss-120b-medium       2514 chars    ignored it
# A style rule in a prompt is a request. A schema is not: with this, the worst
# offender answered in two lines. Every model then reports in the same shape,
# which is also easier to read than three different essays - the findings line
# up and can be compared.
SCHEMA = {
    "type": "object",
    "required": ["findings"],
    "properties": {"findings": {
        "type": "array", "maxItems": 8,
        "items": {
            "type": "object",
            "required": ["file", "what", "severity"],
            "properties": {
                "file": {"type": "string"},
                "line": {"type": "integer"},
                "severity": {"type": "string", "enum": ["real", "maybe", "fine"]},
                "what": {"type": "string", "maxLength": 160},
            }}}}}


def clean(text):
    """A prompt agy will not truncate. Quotes are the whole problem."""
    return text.replace('"', "'").replace("“", "'").replace("”", "'")


def ask(model, prompt, add_dirs, timeout=600, schema=True):
    """One model, one answer. Never raises: a panel with a hole is still a panel.

    The answer comes back as data, not prose, because agy can ENFORCE a schema
    and cannot enforce a writing style. That is the whole difference between
    a 344 character answer and a 2900 character one.
    """
    cmd = ["agy"]
    for d in (add_dirs or []):
        cmd += ["--add-dir", str(d)]
    sf = None
    if schema:
        sf = Path(tempfile.mkdtemp(prefix="mice_schema_")) / "schema.json"
        sf.write_text(json.dumps(SCHEMA), encoding="utf-8")
        cmd += ["--output-format", "json", "--json-schema", str(sf)]
    cmd += ["-p", clean(prompt), "--mode", "plan", "--model", model]
    t0 = time.time()
    findings, raw, used = [], "", {}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        raw = (r.stdout or "").strip() or (r.stderr or "").strip()
        if schema:
            try:
                data = json.loads(raw)
                findings = (data.get("structured_output") or {}).get("findings") or []
                used = data.get("usage") or {}
                raw = json.dumps(findings)
            except ValueError:
                pass                    # not JSON: keep whatever came back
    except subprocess.TimeoutExpired:
        raw = "(no answer: timed out after %ds)" % timeout
    except OSError as e:
        raw = "(no answer: %s)" % e
    finally:
        if sf:
            shutil.rmtree(sf.parent, ignore_errors=True)
    return {"model": model, "secs": round(time.time() - t0, 1),
            "text": raw, "findings": findings, "used": used}


def where_of(paths):
    """The directories to hand to agy, and the file names to name in the prompt.

    The REAL files, in the tree they live in - including `.staging`, which is
    where all work happens. agy skips dot-directories when it picks a workspace
    on its own, which is why a review asked without --add-dir silently answers
    about the last PROMOTED version instead of the one being written. Naming
    the directory explicitly reaches it: measured 2026-08-19 by asking for a
    value that had existed for four minutes and only in staging.

    Reviewing a COPY works too, and was the first version of this. It is worse:
    a copy is a second thing that can be stale, and the whole point is to
    review exactly what is about to be promoted.
    """
    dirs, names = [], []
    for raw in paths:
        q = Path(raw).resolve()
        if q.is_dir():
            if q not in dirs:
                dirs.append(q)
            names += sorted(f.name for f in q.iterdir()
                            if f.is_file() and f.suffix in (
                                ".py", ".js", ".css", ".html", ".h", ".cpp",
                                ".json", ".md"))
        elif q.is_file():
            if q.parent not in dirs:
                dirs.append(q.parent)
            names.append(q.name)
    return dirs, names


def run(question, paths, models=None, head=None, out=None):
    models = models or PANEL
    head = head or HEAD
    brief = BRIEF.read_text(encoding="utf-8") if BRIEF.is_file() else ""
    where, files = where_of(paths) if paths else ([], [])

    prompt = "%s\nRead these files in the added directory: %s\n%s\nAnswer directly, no plan. At most 15 lines." % (
        brief, ", ".join(files) or "(none)", question)

    print("asking %d models about %s" % (len(models), ", ".join(files) or "nothing"))
    with cf.ThreadPoolExecutor(max_workers=len(models)) as pool:
        answers = list(pool.map(lambda m: ask(m, prompt, where), models))

    # What it cost, per model, in the units the bill is in. Printed because the
    # user pays for this and asked to see where it goes.
    spent = 0
    for a in answers:
        u = a.get("used") or {}
        spent += u.get("total_tokens") or 0
        print("   %-28s %5.1fs  %2d findings  %s tokens"
              % (a["model"], a["secs"], len(a["findings"]),
                 u.get("total_tokens", "?")))

    # ---- the head reads the panel ----------------------------------
    # Findings only, as data. Before the schema this carried up to 4000
    # characters of prose per model and was the most expensive part of a run.
    seen = []
    for a in answers:
        for f in a["findings"]:
            seen.append("%s | %s:%s | %s | %s" % (
                a["model"].split("-")[0], f.get("file", "?"), f.get("line", ""),
                f.get("severity", "?"), f.get("what", "")))
    judge = ("%s%sSeveral models reviewed: %s%sTheir findings, one per line:%s%s%s"
             "You are the head reviewer. Keep only what the files support. Mark "
             "each real, maybe or fine, worst first. Ignore anything not in the "
             "files."
             % (brief, chr(10), ", ".join(files), chr(10), chr(10),
                (chr(10)).join(seen) or "(none)", chr(10)))
    verdict = ask(head, judge, where)
    hu = (verdict.get("used") or {}).get("total_tokens") or 0
    spent += hu
    print("   %-28s %5.1fs  %2d findings  %s tokens  (head)"
          % (head, verdict["secs"], len(verdict["findings"]), hu or "?"))
    print("   %-28s %s tokens total" % ("", spent or "?"))

    stamp = time.strftime("%Y-%m-%d %H:%M")

    def rows(fs):
        return [" - **%s** `%s:%s` %s" % (f.get("severity", "?"), f.get("file", "?"),
                                          f.get("line", ""), f.get("what", ""))
                for f in fs] or [" - (nothing)"]

    report = ["# Panel review - %s" % stamp, "",
              "**Question.** %s" % question.strip(), "",
              "**Files.** %s" % (", ".join(files) or "none"),
              "**Cost.** %s tokens across %d models"
              % (spent or "?", len(models) + 1), "",
              "## The head reviewer (%s)" % head, ""] + rows(verdict["findings"])
    report += ["", "## What each model said", ""]
    for a in answers:
        report += ["### %s  _(%.1fs, %s tokens)_"
                   % (a["model"], a["secs"],
                      (a.get("used") or {}).get("total_tokens", "?")), ""]
        report += rows(a["findings"]) + [""]
    report += ["---", "",
               "_A verdict is a shortlist, not a fact. Every finding here is "
               "checked against the code before anything changes._"]

    text = "\n".join(report)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8", newline="")
        print("\nwrote", out)
    else:
        print("\n" + verdict["text"])
    return text


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ask", help="the question to put to the panel")
    ap.add_argument("--dir", action="append", default=[],
                    help="a file or folder under review (repeatable)")
    ap.add_argument("--models", help="comma separated, default the standard panel")
    ap.add_argument("--head", help="which model judges the answers")
    ap.add_argument("--out", help="write the report here (markdown)")
    ap.add_argument("--list", action="store_true", help="what models exist today")
    a = ap.parse_args(argv)

    if a.list:
        subprocess.run(["agy", "models"])
        return 0
    if not a.ask:
        ap.print_help()
        return 2
    run(a.ask, a.dir,
        models=[m.strip() for m in a.models.split(",")] if a.models else None,
        head=a.head, out=a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
