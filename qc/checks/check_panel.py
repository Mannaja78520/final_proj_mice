"""The review panel really is several models, and a dead one cannot look clean.

The user's rule, and the reason this file exists: *use multiple AI to help
brainstorm before taking any action*, and *do not trust only 1 AI*. That is only
true while the panel actually SPEAKS. On 2026-08-19 it was found that
`gpt-oss-120b-medium` had been failing on every run - it errors when an answer
shape is enforced with a JSON schema - and the report printed `(nothing)` beside
its name. `(nothing)` reads as *this model found no problems*. It meant *this
model never ran*, which is the most dangerous way for a check to fail: it looks
like agreement.

So three properties are held here:

  * enough voices, from more than one family, because two models from the same
    maker share their blind spots;
  * a model that cannot answer as data is asked again in plain prose, so a
    schema quirk never costs a whole voice;
  * a failure is REPORTED as a failure, never as an empty finding list.

And the token brief goes to every one of them, the user's other standing rule:
they pay for the panel's output too.
"""
import qc as F

AREA = "tools"
TITLE = "the review panel has five voices, and says when one of them failed"


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import ai_panel  # noqa: PLC0415 - the module under test

    src = (F.CODE / "tools" / "ai_panel.py").read_text(encoding="utf-8")

    # THE PANEL IS SPLIT ACROSS TWO MECHANISMS since 2026-08-20, so this file
    # is no longer the whole of it and cannot be asked to prove it is.
    #
    #   this file          the GEMINI voices, through agy
    #   the Agent tool     the CLAUDE voices, as Claude Code subagents
    #
    # Opus and Sonnet moved to subagents on the user's own Anthropic plan: same
    # models, one less layer, and not sharing the pooled Antigravity quota that
    # ran dry on 2026-08-20. Measured the same day - two subagents cost 51k and
    # 64k tokens and found two real defects, while one agy panel run cost 676k
    # and returned nothing. GPT-OSS left because it has never demonstrably
    # found anything here.
    #
    # So what is asserted is what THIS file is now responsible for: more than
    # one Gemini voice, with Pro among them, and a written record of where the
    # other half went - or the split becomes folklore and the Claude half is
    # quietly forgotten by whoever reads this file next.
    t.ok(len(ai_panel.PANEL) >= 2,
         "the Gemini half of the panel is more than one voice",
         "it asks %d: %s" % (len(ai_panel.PANEL), ai_panel.PANEL))
    t.ok(any("pro" in m for m in ai_panel.PANEL),
         "and Pro is one of them",
         "Flash alone is for lookups; the judgement calls need Pro, which is "
         "also the only model that designs the visible surfaces well")
    t.ok("subagent" in src.lower(),
         "and the file says where the CLAUDE voices come from now",
         "a panel that silently shrank from five voices to two, with nothing "
         "explaining that the other three moved rather than died, is how a "
         "review quietly becomes one opinion")
    t.ok(ai_panel.HEAD in ai_panel.PANEL or ai_panel.HEAD,
         "and one of them reads the others' findings")

    # ---- a model that cannot answer as data still speaks -------------
    t.ok(hasattr(ai_panel, "prose_findings"),
         "there is a fallback for a model that cannot answer as data")
    got = ai_panel.prose_findings("- the retreat is a one way latch\n- fine")
    t.eq(len(got), 1, "a prose answer becomes findings")
    t.eq(got[0]["severity"], "unchecked",
         "marked unchecked, because it was not held to the shape")

    t.contains(src, 'data.get("status") == "ERROR"',
               "an errored model is noticed rather than read as empty")
    t.contains(src, "schema=None, retry=False",
               "and is asked again without the schema it failed on")

    # ---- and a failure is never shown as a clean answer --------------
    t.contains(src, "FAILED",
               "the report names a model that failed")
    i = src.find("def said(")
    body = src[i:i + 500]
    t.ok('a.get("error")' in body,
         "the report distinguishes 'found nothing' from 'never ran'",
         "printing the same text for both is what hid a dead model for days")

    # ---- an OUTAGE cannot dress itself up as content -----------------
    # Measured 2026-08-20 and it cost a whole review. Two models needed a
    # re-login and three were out of quota for five days. agy prints its own
    # troubles as ordinary text, the prose fallback parsed them into
    # "findings", and because there were findings the run counted as a success:
    # the report listed a Google OAuth URL as a finding of severity
    # "unchecked". 603,425 tokens, no review, and nothing saying so.
    for text, why in (
            ("Error: Individual quota reached. Please upgrade your subscription.",
             "a used-up quota"),
            ("Authentication required. Please visit the URL to log in:",
             "an expired login"),
            ("Error: authentication timed out.", "a login that timed out")):
        t.ok(ai_panel.tool_failed(text), "%s is recognised as a failure" % why,
             "parsed as findings instead, it becomes a confident-looking "
             "review of nothing")
    t.ok(not ai_panel.tool_failed(
            "main.py:812 the retry loop can spin forever on a dead port"),
         "while a real finding is NOT mistaken for one",
         "over-matching here would throw away genuine review comments, which "
         "is the opposite failure and just as silent")
    i = src.find("return {\"model\": model,")
    t.contains(src[max(0, i - 400):i], "tool_failed(raw)",
               "and every answer is checked before it is believed")

    # THE HEAD LINE ESPECIALLY. rows() falls back to "(nothing)", and on the
    # head's line that reads as "the reviewer found no problems" when it means
    # "the reviewer never ran" - the very sentence at the top of this file.
    i = src.find("## The head reviewer")
    t.contains(src[i:i + 200], "said(verdict)",
               "the head's verdict says FAILED when the head failed")

    # And when EVERY model is down, the report says so at the top and the
    # command exits non-zero, so no script can read an outage as an all-clear.
    t.contains(src, "NO REVIEW HAPPENED",
               "a panel where all models failed says so plainly")
    # ...and says something DIFFERENT when the head survived the panel. Seen
    # 2026-08-20: both panel models timed out, the head read the files itself
    # and produced six specific findings, and the banner still claimed
    # "nothing below is a judgement about the code" - untrue of the paragraph
    # immediately under it. A warning that is wrong about its own page is how
    # people learn to skip warnings.
    t.contains(src, "ONE model's unreviewed",
               "and names the case where the head answered but the panel did not")
    i = src.find("if verdict[\"findings\"]:")
    t.ok(0 < i and src.find("NO REVIEW HAPPENED", i) > i,
         "choosing between the two by whether there is a verdict to read",
         "one banner for both states is wrong in one of them, and it is the "
         "state where somebody is about to act on findings")
    t.ok("return 0 if got else 3" in src,
         "and the command exits non-zero when no review happened",
         "a caller that gates on this would otherwise treat a total outage as "
         "a pass")

    # ---- and one model running out never costs the whole review ------
    # The user's rule, 2026-08-19: *if run of token of each use the rest*. A
    # voice failing costs one opinion. The HEAD failing used to cost the
    # verdict itself, since nothing else read the findings.
    i = src.find("verdict = ask(head")
    body = src[i:i + 900]
    t.contains(body, "for spare in models",
               "another model judges when the head cannot")
    t.contains(body, "head = spare",
               "and the report names whoever actually judged")

    # ---- every voice is given the token brief ------------------------
    # The user pays for the panel's output: *make gemini use less token like
    # claude, we have caveman, maybe we use too much*.
    t.ok(ai_panel.BRIEF.is_file(),
         "the token brief exists", "expected %s" % ai_panel.BRIEF)
    j = src.find("prompt = ")
    t.contains(src[j:j + 400], "brief",
               "the panel prompt starts with the brief")
    k = src.find("judge = ")
    t.contains(src[k:k + 500], "brief",
               "and so does the head reviewer's")
    t.ok("At most" in src,
         "with a hard line budget",
         "without one the models answer at length and the user pays for it")
