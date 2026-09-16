"""Any markdown file becomes a page that keeps itself current.

The generalisation of docs/PLAN.html, asked for 2026-08-19: *make it like this
for another plan too*.

Three properties, each guarding a specific way this rots:

  * **the markdown is the only source.** The HTML is generated. If it is ever
    edited by hand there are two copies of one document, and the copies drift
    silently - so the page says so on its own face;
  * **the page updates with nothing to press.** It is opened from
    `file:///E:/...`, and a file:// page may not fetch() a sibling: null
    origin, blocked. It MAY load a script. So the content is published as a
    script and re-loaded on a timer. Use fetch here and the page is frozen from
    the moment it opens, with nothing saying so;
  * **nothing from the document can inject into the page.** The content becomes
    innerHTML, so a `<script>` in a markdown file would run. Escaping happens
    before any markup is added, never after.

And the renderer says what it did not understand rather than dropping it. A
renderer that quietly loses a line is worse than one that admits it.
"""
import json

import qc as F


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import livedoc  # noqa: PLC0415

    src = (F.CODE / "tools" / "livedoc.py").read_text(encoding="utf-8")

    # ---- the renderer handles what these documents actually contain ---
    md = "\n".join([
        "# Title", "", "Some **bold** and `code` and [a link](http://x/).", "",
        "## Section", "- plain item", "- [x] finished", "- [ ] not finished", "",
        "| a | b |", "|---|---|", "| 1 | 2 |", "",
        "> a quote", "", "```", "raw <not> markup", "```", "", "---",
    ])
    out, done, total, odd = livedoc.render(md)
    t.eq((done, total), (1, 2), "task boxes are counted, ticked and not")
    for want, why in (("<h1>", "headings"), ("<strong>", "bold"),
                      ("<code>", "inline code"), ("<a href=", "links"),
                      ("<ul>", "lists"), ("<table>", "tables"),
                      ("<th>", "table headers"), ("<blockquote>", "quotes"),
                      ("<pre><code>", "code blocks"), ("<hr>", "rules")):
        t.contains(out, want, "it renders %s" % why)
    t.eq(out.count("<table>"), 1, "a table is ONE table, not a row each")
    # COUNT THE ROWS. Looking for "|---|" in the output passed with the
    # separator rendered, because by then it is <td>---</td> and the pipes are
    # long gone - the test was searching for something that could never appear
    # either way. Caught by tools/sabotage.py.
    t.eq(out.count("<tr>"), 2,
         "the table has a header and one data row, not the |---| line as well")
    t.ok("<td>---</td>" not in out,
         "and no cell is markdown punctuation",
         "a row of dashes through the middle of every table reads as a broken "
         "table, and it would be in every document with one")

    # ---- nothing in a document can inject -----------------------------
    bad, _d, _n, _o = livedoc.render("<script>alert(1)</script>\n\n[x](javascript:1)")
    t.ok("<script>" not in bad,
         "a <script> in the markdown is escaped, never emitted",
         "the content becomes innerHTML in the page, so this would RUN - and "
         "these documents are pasted into from panels and logs")
    t.contains(bad, "&lt;script&gt;", "it appears as text instead")
    i_esc = src.find("s = html.escape(s)")
    i_tag = src.find('re.sub(r"`([^`]+)`"')
    t.ok(0 < i_esc < i_tag,
         "escaping happens BEFORE any markup is added",
         "escape afterwards and every tag the renderer just built is turned "
         "into visible text - or worse, half of them are")

    # ---- a real document, end to end ---------------------------------
    doc = F.CODE / "qc" / "_qc_livedoc_sample.md"
    doc.write_bytes(("# Sample\n\n- [x] one\n- [ ] two\n\n| h |\n|---|\n| v |\n")
                    .encode("utf-8"))
    try:
        page, done, total, _odd = livedoc.build(doc)
        state = page.with_name(page.stem + ".doc.js")
        t.ok(page.is_file(), "it writes the page")
        t.ok(state.is_file(), "and the state script beside it")
        text = page.read_text(encoding="utf-8")
        js = state.read_text(encoding="utf-8")

        # THE FILE:// RULE. fetch() is blocked for a file:// page and a script
        # is not, which is the whole mechanism.
        t.contains(text, '<script src="' + state.name,
                   "the page loads the state as a SCRIPT")
        t.ok("fetch(" not in text,
             "and never fetches it",
             "a file:// page is given a null origin and the read is blocked, "
             "so the page would freeze at whatever it opened with and say "
             "nothing about it")
        t.contains(text, "setInterval",
                   "it re-reads on a timer, so it updates with nothing pressed")
        t.contains(text, "Date.now()",
                   "with a changing url, or the browser serves its cache "
                   "forever")

        d = json.loads(js[js.index("=") + 1:].rstrip().rstrip(";"))
        for k in ("stamp", "html", "done", "total"):
            t.ok(k in d, "the state carries %s" % k)
        t.eq((d["done"], d["total"]), (1, 2),
             "including the checklist counts the page shows")

        # THE ONE SOURCE RULE, stated where somebody about to edit will see it.
        t.contains(text, "never this page",
                   "the page says the markdown is the source")
        t.contains(text, doc.name,
                   "and names the file to edit instead")
    finally:
        for f in (doc, doc.with_suffix(".html"),
                  doc.with_name(doc.stem + ".doc.js")):
            f.unlink(missing_ok=True)

    # ---- it says what it could not render -----------------------------
    _o, _d, _n, odd = livedoc.render("```\nunclosed fence\n")
    t.ok(odd, "an unclosed code fence is reported, not silently swallowed",
         "the rest of the document would be inside it and invisible")


AREA = "tools"
TITLE = "any markdown file renders to a page that keeps itself current"
