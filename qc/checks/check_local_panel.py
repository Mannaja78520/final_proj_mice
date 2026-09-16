"""The models on this PC are a real panel, and a dead one cannot look clean.

Asked for on 2026-08-20: *we will use deepseek and llama in local to help
brainstrome and do our work*, and the reason: *more model from different
provider it have different idea*.

Two things make a local panel worth having, and both are easy to lose:

  * **it is free and it cannot be cut off.** The networked panel is the better
    reviewer, but an unreliable link is not free - one run on 2026-08-20 spent
    676,387 tokens and returned nothing, because every model read files for ten
    minutes and only then hit the error. The work is billed before the failure;
  * **the voices are genuinely different.** Two models from one maker share
    their training and their blind spots, so the second mostly agrees and
    teaches nothing.

And three ways it could quietly stop being worth having, each guarded below:

  * **a silently truncated file.** ollama's default context is 4096 tokens for
    many models, so a source file longer than that is cut with nothing saying
    so - and the model then answers confidently about code it never saw. That
    is the exact failure this project keeps designing against, so `num_ctx` is
    set explicitly and a trimmed file is reported;
  * **a failure printed as an empty answer.** `(nothing)` beside a model's name
    reads as *found no problems* and can mean *never ran*. ai_panel.py had this
    bug for days before anyone noticed, and it cost real reviews;
  * **a missing model skipped in silence.** A panel that ran three of five
    voices and did not say so is a panel you would over-trust.
"""
import re

import qc as F

AREA = "tools"
TITLE = "the local model panel really is several makers, and says when one failed"

# A DeepSeek-R1 *distill* is not an independent model: `deepseek-r1:8b` comes
# from Llama and `deepseek-r1:14b` from Qwen, so it carries that base's blind
# spots under another name - which is the one thing a panel exists to avoid.
DISTILL_TRAP = "deepseek-r1"


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import local_panel  # noqa: PLC0415 - the module under test

    src = (F.CODE / "tools" / "local_panel.py").read_text(encoding="utf-8")

    # ---- several makers, not several models --------------------------
    t.ok(len(local_panel.PANEL) >= 4,
         "the panel asks at least four local models",
         "it asks %d: %s" % (len(local_panel.PANEL), local_panel.PANEL))
    # A FLOOR ON MAKERS, NOT A BAN ON REPEATS - and the difference was a real
    # mistake of mine, caught by the user on 2026-08-20.
    #
    # This asserted that no family may appear twice, on the theory that two
    # models from one maker share their blind spots so the second teaches
    # nothing. This project's own evidence contradicts that. The same day, a
    # SONNET subagent and an OPUS subagent - both Anthropic - reviewed this
    # firmware and returned findings with NO overlap at all: sonnet found the
    # md5 was optional so a corrupted image could boot; opus found NUL boot
    # lines being returned as replies and forwarded WiFi commands never getting
    # PEER_WAIT. Same maker, entirely different bugs.
    #
    # The honest caveat is that those two were also handed DIFFERENT FILES, so
    # it never was a clean test of maker against maker. What it does suggest is
    # that SCOPE is the stronger lever: two models reading the same 200 lines
    # converge, two models reading different files cannot. Worth building into
    # the panel later - give each model its own slice rather than one prompt.
    #
    # So what is guarded here is the thing that IS defensible: a panel that is
    # all one maker is one training pipeline wearing several names.
    families = [m.split(":")[0].split("-")[0] for m in local_panel.PANEL]
    t.ok(len(set(families)) >= 3,
         "the panel spans at least three makers (%d of %d models)"
         % (len(set(families)), len(local_panel.PANEL)),
         "a panel that is all one maker is one training pipeline under "
         "several names. A REPEATED maker is fine - opus and sonnet found "
         "completely different bugs here - but a single one is not. Got %s"
         % sorted(families))
    t.ok(not any(m.startswith(DISTILL_TRAP) for m in local_panel.PANEL),
         "and no R1 distill is counted as its own voice",
         "deepseek-r1:8b is distilled from Llama and :14b from Qwen, so it "
         "brings that base's blind spots wearing another name - the exact "
         "thing a panel of several makers is for")

    # ---- a file is never silently cut short ---------------------------
    t.ok(local_panel.NUM_CTX >= 8192,
         "the context length is set explicitly and is large (%d)"
         % local_panel.NUM_CTX,
         "many ollama models default to 4096, so a source file is truncated "
         "with nothing saying so and the model answers about code it never saw")
    t.contains(src, '"num_ctx": NUM_CTX',
               "and it is really passed to the model")
    t.contains(src, "/api/generate",
               "which is why the HTTP API is used rather than `ollama run`")

    got, notes = local_panel.gather(["tools/local_panel.py"])
    t.ok("local_panel.py" in got, "a real file is read and shown to the models")
    long_file = "x" * (local_panel.FILE_CHARS + 500)
    tmp = F.CODE / "tools" / "_qc_long_sample.txt"
    tmp.write_text(long_file, encoding="utf-8")
    try:
        _text, notes = local_panel.gather(["tools/_qc_long_sample.txt"])
        t.ok(any("cut" in n for n in notes),
             "a file too long to show is REPORTED as cut, not quietly trimmed",
             "a model answering about half a file, with nothing marking the "
             "cut, is how a review becomes confident nonsense")
    finally:
        tmp.unlink(missing_ok=True)
    _text, notes = local_panel.gather(["tools/does_not_exist_qc.py"])
    t.ok(any("does not exist" in n for n in notes),
         "and a file that is not there is named too")

    # ---- a failure is a failure, never an empty answer ----------------
    fn = src[src.find("def ask("):]
    fn = fn[:fn.find("\ndef ", 1)]
    t.contains(fn, '"error": str(e)',
               "a model that errors returns the reason")
    t.ok('"text": ""' in fn,
         "and an empty answer is not dressed up as content")
    rep = src[src.find('for r in answers:'):]
    t.contains(rep, "FAILED",
               "the report prints FAILED beside a model that did not run")
    t.contains(rep, "the model returned nothing",
               "and says so even when there was no error to quote",
               )

    # ---- a missing model is named, and a dead panel exits non-zero ----
    t.contains(src, "Not installed, so they did not speak",
               "models that are not installed are named in the report")
    t.contains(src, "NO REVIEW HAPPENED",
               "and a panel where every model failed says so plainly")
    t.ok("return 0 if spoke else 3" in src,
         "with a non-zero exit, so no script reads an outage as a pass",
         "this is the bug ai_panel.py had: an outage that looked like a clean "
         "review")

    # ---- the verdict is still a shortlist -----------------------------
    t.ok("SHORTLIST" in src or "shortlist" in src.lower(),
         "the report says its findings must be checked against the code",
         "these are small models; a confident wrong answer costs more than a "
         "quiet one, and this project has had that happen twice in a day")

    # ---- and the token brief goes to them too -------------------------
    j = src.find("prompt = ")
    t.contains(src[j:j + 400], "brief",
               "the prompt starts with the shared brief")
    t.ok(re.search(r"at most %d lines", src),
         "with a line budget, like every other model call here")
