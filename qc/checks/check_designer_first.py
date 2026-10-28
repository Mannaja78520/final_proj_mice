"""Every screen is for a designer, not a programmer - and the rule is held.

A21-1 wrote the rule into CLAUDE.md; this check is what stops it rotting:

  * the designer rule really sits in CLAUDE.md;
  * the banned-word list lives in qc/data/designer_words.json as DATA - a new
    word costs an edit to JSON, never to this file. Its `core` names the
    founding words that may not quietly leave, and `allow_files` carries a
    reason next to every exemption so the next reader can judge it;
  * no banned word reaches a visitor of any page the hub serves.

Rendered, not source: hub.html carries `undefined` inside JS comments where
nobody visiting the page can read it, and a source scan would red-flag that
forever until somebody weakened the list. Script and style blocks come out,
elements classed .tech come out WITH their children (A21-3 moves exception
text there on purpose - behind one click is allowed), tags come out; what is
left is what a person sees. Word matching is whole-word: `nan` must not trip
inside `maintenance`.

JS is scanned at its STRING LITERALS only - identifiers never render, but
template text like `No robot named X answered` does. nong's app.js is exempt
today for its devtools-facing NaN warnings.

Out of scope, held elsewhere: backend error wording (A21-3) and the module
site inside firmware/src/web/WebUI.h, which is C++ holding HTML (A22-1).
"""
import io
import json
import re
from html.parser import HTMLParser

import qc as F

AREA = "hub"
TITLE = "the designer-first rule exists and no page talks like a programmer"

WORDS_PATH = F.CODE / "qc" / "data" / "designer_words.json"

PAGE_GLOBS = ["main_python/web/*.html",
              "main_python/web_ox/*.html",
              "main_python/web_gemini/*.html",
              "apps/*/index.html",
              "nong/main_python_set_nong/web/*.html"]
JS_GLOBS = ["main_python/web/*.js",
            "main_python/web_ox/*.js",
            "main_python/web_gemini/*.js",
            "apps/*/*.js",
            "nong/main_python_set_nong/web/*.js"]

RULE_1 = "## Every screen is for a designer, not a programmer"


class VisibleText(HTMLParser):
    """The words a visitor reads: script/style gone, .tech subtrees gone."""

    SKIP_TAGS = {"script", "style"}

    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                 "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        hidden = bool(self.stack and self.stack[-1][1])
        hidden = hidden or tag in self.SKIP_TAGS or "tech" in dict(attrs).get("class", "").split()
        if tag not in self.VOID_TAGS:
            self.stack.append((tag, hidden))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(data)


def visible_text(path):
    p = VisibleText()
    p.feed(io.open(path, encoding="utf-8", newline="").read())
    return " ".join(p.parts).lower()


def literal_text(src):
    # A typeof operand names a JS type, never visitor-facing copy. Keep all
    # other string literals (including notices that say "undefined").
    found = re.finditer(r'"([^"\n]*)"|\'([^\'\n]*)\'|`([^`\n]*)`', src)
    parts = []
    for match in found:
        value = next(v for v in match.groups() if v is not None)
        prefix = src[max(0, match.start() - 160):match.start()]
        if value == "undefined" and re.search(
                r"\btypeof\s+[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*(?:===?|!==?)\s*$", prefix):
            continue
        parts.append(value)
    return " ".join(parts).lower()


def js_strings(path):
    return literal_text(io.open(path, encoding="utf-8", newline="").read())


def run(t):
    parser = VisibleText()
    parser.feed('<div class="tech">hidden <b>undefined</b><input><br></div>'
                '<p>visible undefined <span>after</span></p>'
                '<script>hidden script</script><p>last</p>')
    t.eq(" ".join(parser.parts).split(), ["visible", "undefined", "after", "last"],
         "technical subtrees and void tags cannot hide later visitor text")
    t.eq(literal_text("typeof Mice !== 'undefined' && typeof window.Mice == \"undefined\""), "",
         "JS type operands are not visitor messages")
    t.eq(literal_text("notice('undefined'); const hint = 'undefined';"), "undefined undefined",
         "actual message literals remain subject to the banned-word check")
    store = json.loads(WORDS_PATH.read_text(encoding="utf-8"))
    banned = [w.lower() for w in store.get("banned", [])]
    t.ok(len(banned) >= 5, "the word list has real words in it")
    t.ok(all(re.fullmatch(r"[a-z0-9 ]+", w) for w in banned),
         "every entry is plain text a scanner can use")
    # The founding words cannot quietly leave - the list may grow in DATA,
    # but shrinking past its core is a check-visible decision.
    lost = [w for w in store.get("core", []) if w.lower() not in banned]
    t.ok(not lost, "the core words are still banned", ", ".join(lost))

    claude_md = (F.CODE / "CLAUDE.md").read_text(encoding="utf-8")
    t.contains(claude_md, RULE_1, "CLAUDE.md still carries the designer rule")

    allow = {k.replace("\\", "/"): v
             for k, v in (store.get("allow_files") or {}).items()}

    pages, jss = [], []
    for g in PAGE_GLOBS:
        pages.extend(sorted(F.CODE.glob(g)))
    for g in JS_GLOBS:
        jss.extend(sorted(F.CODE.glob(g)))
    t.ok(len(pages) >= 6, "the scan found the served pages", str(len(pages)))

    bad, scanned = [], []
    for path, text in [(p, visible_text(p)) for p in pages] \
            + [(p, js_strings(p)) for p in jss]:
        rel = path.relative_to(F.CODE).as_posix()
        scanned.append(rel)
        if rel in allow:
            continue
        for w in banned:
            if re.search(r"\b%s\b" % re.escape(w), text):
                bad.append("%s: %s" % (rel, w))
    t.ok(not bad, "nothing served shows a banned word to a visitor",
         "; ".join(bad[:5]) or "(clean)")

    # The exemption names real files - a renamed page must not silently keep
    # its pass.
    gone = sorted(a for a in allow if a not in scanned)
    t.ok(not gone, "every allowed file is a page that exists",
         ", ".join(gone))
