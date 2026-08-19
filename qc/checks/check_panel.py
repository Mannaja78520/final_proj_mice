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

    t.ok(len(ai_panel.PANEL) >= 5,
         "the panel asks at least five models",
         "it asks %d: %s" % (len(ai_panel.PANEL), ai_panel.PANEL))
    families = {m.split("-")[0] for m in ai_panel.PANEL}
    t.ok(len(families) >= 3,
         "from at least three different makers",
         "models from one maker share their blind spots; got %s" % sorted(families))
    t.ok(ai_panel.HEAD in ai_panel.PANEL or ai_panel.HEAD,
         "and one of them reads the others' findings")

    # ---- a model that cannot answer as data still speaks -------------
    t.ok(hasattr(ai_panel, "prose_findings"),
         "there is a fallback for a model that cannot answer as data")
    got = ai_panel.prose_findings("- the retreat is a one way latch\n- fine")
    t.eq(len(got), 1, "a prose answer becomes findings")
    t.eq(got[0]["severity"], "unchecked",
         "marked unchecked, because it was not held to the shape")

    src = (F.CODE / "tools" / "ai_panel.py").read_text(encoding="utf-8")
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
