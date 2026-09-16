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
if ROOT.name.startswith(".staging"):
    REAL = ROOT.parent
else:
    REAL = ROOT
BRIEF = ROOT / "tools" / "ai_brief.txt"

# The panel. Different FAMILIES, deliberately: two models from one family tend
# to be wrong in the same way, which is the thing a panel is supposed to fix.
# Three FAMILIES, five voices, asked for by the user 2026-08-19. Sonnet and
# Flash were added when GPT-OSS turned out to be contributing nothing at all
# (see ask()): a panel of two is not a panel. Flash is here for breadth rather
# than depth - it is fast and cheap, and a fifth reader costs little because
# every one of them is given tools/ai_brief.txt and a hard line budget.
# THE GEMINI VOICES ONLY, since 2026-08-20. Not a downgrade - a split, decided
# with the user after measuring where each voice actually earned its place:
#
#   * GEMINI PRO stays and is the reason this tool exists. It is the only way
#     to reach Gemini at all, and it is the best designer of anything a person
#     looks at. It earned it again the same day, on the flash control: keep ONE
#     button, let the hub pick the transport, and name the transport in the
#     status line so a four-minute wait explains itself. Better than what would
#     have been built without asking.
#   * CLAUDE OPUS AND SONNET LEFT THIS LIST, and did NOT leave the review. They
#     are now asked as Claude Code subagents instead, on the user's own
#     Anthropic plan. Same models, one less layer, and not sharing the pooled
#     Antigravity quota that ran dry on 2026-08-20 with nothing available until
#     about the 25th. Measured the same day: two subagents cost 51k and 64k
#     tokens and found two real defects - an optional md5 that would let a
#     corrupted image boot, and a stale-row colour regression - while one agy
#     panel run cost 676k tokens and returned nothing at all, because every
#     model read files for ten minutes and only then hit the error.
#   * GPT-OSS LEFT because it has never demonstrably found anything here. It
#     spent days failing silently behind a `(nothing)` that read as approval,
#     and after that was fixed it still has no finding to its name.
#
# So: this file is the GEMINI half of the panel, and the Claude half is the
# Agent tool. Both halves still run - see the plan and CLAUDE.md - and the rule
# that matters is unchanged: every finding is a shortlist to check against the
# code, never a fact.
PANEL = ["gemini-3.1-pro-high", "gemini-3.7-flash-high"]
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


# WHEN THE TOOL FAILS, THAT IS NOT AN OPINION.
#
# agy prints its own troubles on stdout like any other text: an expired login,
# a used-up quota, a timeout. The prose fallback below then parses those lines
# into "findings" and, because there were findings, the run counts as a success.
# Measured 2026-08-20: a panel of five came back with all five models broken -
# two needing a re-login and three out of quota for five days - and the report
# listed the login URL as a finding of severity "unchecked". 603,425 tokens
# spent, no review done, and nothing in the report saying so.
#
# The rule this file already carries is that a failure prints FAILED and never
# an empty list. This is the same rule one step earlier: a failure must not be
# able to disguise itself as content.
_TOOL_FAILURE = re.compile(
    r"quota reached|Authentication required|authentication (failed|timed out)"
    r"|Please upgrade your subscription|rate.?limit|Error: ",
    re.I)


def tool_failed(text):
    """The reason this model said nothing usable, or "" if it really answered."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line and _TOOL_FAILURE.search(line):
            return line[:160]
    return ""


def ask(model, prompt, add_dirs, timeout=600, schema=True, retry=True):
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
    findings, raw, used, error = [], "", {}, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        raw = (r.stdout or "").strip() or (r.stderr or "").strip()
        if schema:
            try:
                data = json.loads(raw)
                used = data.get("usage") or {}
                out_obj = data.get("structured_output")
                if data.get("status") == "ERROR" or out_obj is None:
                    # The model could not answer in the enforced shape. This
                    # was SILENT until 2026-08-19: gpt-oss-120b failed this way
                    # on every panel run for days, and the report printed
                    # "(nothing)" beside its name - which reads as "found no
                    # problems" and is the most dangerous way to fail. It
                    # answers fine in plain prose, so ask again without the
                    # schema rather than losing the voice entirely.
                    error = str(data.get("error") or "no structured answer")
                    if retry:
                        again = ask(model, prompt, add_dirs, timeout,
                                    schema=None, retry=False)
                        findings = prose_findings(again["text"])
                        raw = again["text"]
                        used = again.get("used") or used
                        error = "" if findings else (
                            "%s; prose retry gave nothing either" % error)
                else:
                    findings = out_obj.get("findings") or []
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
    # LAST WORD: if what came back is the TOOL complaining, it is a failure
    # however many lines of it there are. Without this the prose fallback turns
    # an expired login into eight confident-looking findings and the run reports
    # a successful review — see tool_failed().
    broke = tool_failed(raw)
    if broke:
        findings, error = [], broke
    return {"model": model, "secs": round(time.time() - t0, 1),
            "text": raw, "findings": findings, "used": used, "error": error}


def prose_findings(text, limit=8):
    """A plain answer turned into findings, for a model that cannot do schema.

    Deliberately dumb: one line, one finding, no file attributed. A model that
    could not answer in the enforced shape has not earned a confident file:line,
    and the head reviewer is told to weigh these the same as any other claim -
    which is to say, not at all until the code is read.
    """
    out = []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-*# ").strip()
        if len(line) < 12 or line.startswith("```") or line.startswith("{"):
            continue
        out.append({"file": "", "line": "", "severity": "unchecked",
                    "what": line[:300]})
        if len(out) >= limit:
            break
    return out


SOURCE_SUFFIXES = (".py", ".js", ".css", ".html", ".h", ".cpp", ".json", ".md")
# Build output and dependency trees are not the work under review, and one of
# them (.pio) is larger than everything else here put together.
SKIP_DIRS = {".pio", "node_modules", "__pycache__", "build", "dist", "generated"}
NAME_CAP = 60


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
            # RECURSE. iterdir() reads the top level only, and naming a project
            # root then listed seven files that happened to sit beside the
            # source. Measured 2026-08-20: a question about
            # firmware/src/core/BusUpdate.cpp reported its files as
            # ".qc-receipt.json, CHANGELOG.md, CLAUDE.md, NEXT_SESSION.md,
            # README.md, promote.py, promt.md" — none of them the subject. The
            # models could still reach the real files through --add-dir, so the
            # answer looked plausible while the stated scope was fiction.
            found = []
            for f in q.rglob("*"):
                if not f.is_file() or f.suffix not in SOURCE_SUFFIXES:
                    continue
                # The RELATIVE parts, not the absolute ones. Testing f.parts
                # walks the whole path from the drive letter down — which
                # includes `.staging`, so the dot rule threw away every file in
                # the tree this tool exists to review. It reported zero files
                # for a folder holding eleven.
                rel = f.relative_to(q)
                if any(p in SKIP_DIRS or p.startswith(".") for p in rel.parts):
                    continue
                found.append(str(rel).replace("\\", "/"))
            found.sort()
            if len(found) > NAME_CAP:
                # Say it was trimmed. A truncated list presented as the whole
                # is the same lie in a smaller font.
                names += found[:NAME_CAP] + ["...and %d more under %s"
                                             % (len(found) - NAME_CAP, q.name)]
            else:
                names += found
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
    # IF ONE RUNS OUT, USE THE REST - the user's rule, 2026-08-19. A voice that
    # fails costs one opinion, which the other four cover. The HEAD failing used
    # to cost the whole verdict, because nothing else read the findings. So when
    # the head comes back empty AND broken, the next model on the panel reads
    # them instead, and the report says who ended up judging.
    verdict = ask(head, judge, where)
    if not verdict["findings"] and verdict.get("error"):
        for spare in models:
            if spare == head:
                continue
            print("   %s could not judge (%s) - asking %s"
                  % (head, verdict["error"], spare))
            verdict = ask(spare, judge, where)
            if verdict["findings"]:
                head = spare
                break
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

    def said(a):
        """What one model contributed - or why it contributed nothing."""
        if a["findings"]:
            return rows(a["findings"])
        if a.get("error"):
            return [" - **FAILED** %s" % a["error"]]
        return [" - (nothing to report)"]

    report = ["# Panel review - %s" % stamp, "",
              "**Question.** %s" % question.strip(), "",
              "**Files.** %s" % (", ".join(files) or "none"),
              "**Cost.** %s tokens across %d models"
              % (spent or "?", len(models) + 1), "",
              # said(), not rows(). rows() falls back to "(nothing)", and on
              # the HEAD line that reads as "the reviewer found no problems"
              # when it means "the reviewer never ran". That is the exact
              # failure this file was written to stop, and it was still live
              # here on 2026-08-20: five broken models, and a verdict that
              # said "(nothing)".
              "## The head reviewer (%s)" % head, ""] + said(verdict)
    report += ["", "## What each model said", ""]
    for a in answers:
        report += ["### %s  _(%.1fs, %s tokens)_"
                   % (a["model"], a["secs"],
                      (a.get("used") or {}).get("total_tokens", "?")), ""]
        report += said(a) + [""]
    # NO PANEL AT ALL IS NOT A CLEAN REVIEW.
    #
    # When every model is broken, the report is a page of FAILED lines, and a
    # page of FAILED lines still LOOKS like a review that found nothing. It has
    # to say, at the top and on the console, that no review happened - and the
    # exit code has to be non-zero so a script cannot treat it as a pass.
    # Measured 2026-08-20: two models needed a re-login and three were out of
    # quota for five days; the run cost 603,425 tokens and read as complete.
    alive = [a for a in answers if a["findings"] or not a.get("error")]
    dead = not alive
    if dead:
        why = sorted({a.get("error", "")[:60] for a in answers if a.get("error")})
        # THE HEAD CAN SURVIVE A DEAD PANEL, and then the banner has to say
        # something different. Seen 2026-08-20: both panel models timed out,
        # the head read the files itself and produced six specific findings,
        # and the page still said "nothing below is a judgement about the
        # code" - which was untrue of the very next paragraph. A warning that
        # is wrong about its own page teaches people to skip warnings.
        if verdict["findings"]:
            banner = ["> **THE PANEL FAILED — this is ONE model's unreviewed "
                      "opinion.** All %d panel models failed, so nothing "
                      "cross-checked the findings below and no second voice "
                      "disagreed with them. Treat them as a shortlist to read "
                      "the code against, which is the rule anyway, but with "
                      "none of the safety a panel is for." % len(answers), ""]
        else:
            banner = ["> **NO REVIEW HAPPENED.** All %d models failed, so "
                      "nothing below is a judgement about the code — it is a "
                      "list of outages. Do not read the absence of findings "
                      "as approval." % len(answers), ""]
        banner += ["> - %s" % w for w in why] + [""]
        report[4:4] = banner
        print("\n!! NO REVIEW HAPPENED - all %d models failed:" % len(answers))
        for w in why:
            print("     " + w)

    text = "\n".join(report)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8", newline="")
        print("\nwrote", out)
    else:
        print("\n" + verdict["text"])
    return "" if dead else text


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
    # Non-zero when the panel did not run, so a caller that gates on this
    # cannot mistake an outage for an all-clear.
    got = run(a.ask, a.dir,
              models=[m.strip() for m in a.models.split(",")] if a.models else None,
              head=a.head, out=a.out)
    return 0 if got else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
