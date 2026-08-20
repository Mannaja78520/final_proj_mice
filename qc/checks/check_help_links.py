"""Help lands on the part about what you were looking at, and never nowhere.

The help page has had a section anchor per area from the start - `#firmware`,
`#hub`, `#studio` - and until 2026-08-20 nothing in the project linked to one.
Every Help link went to the top of a page of over thirteen hundred lines, so
finding the paragraph about the screen in front of you meant scrolling past
everything else. That is the same fault as no help at all, dressed up.

Two halves, and the second is the one with teeth:

  * each screen links to ITS section - the hub's Help link follows the tab, a
    tool row carries the section its app.json declares, Studio and the board's
    own page point at their own;
  * every anchor anywhere in the project resolves. A link to `/help#flashing`
    when the section is called `#firmware` fails silently: the browser shows
    the top of the page and nobody can tell it from a link that was never
    contextual. That is exactly how this would rot back.

The by-task index at the top exists because the page is grouped by where each
feature RUNS, which is right once you know the system and useless on the first
day. Somebody arriving has a task, not a component - so every section must be
reachable that way too, or it is a section nobody new will ever find.
"""
import re

import qc as F

AREA = "hub"
TITLE = "help links land on the right section, and no anchor is dead"

HELP = "main_python/web/help.html"


def run(t):
    help_html = (F.CODE / HELP).read_text(encoding="utf-8")
    sections = set(re.findall(r'<section id="([a-z0-9-]+)"', help_html))
    t.ok(len(sections) >= 8, "the help page has a section per area (%d)"
         % len(sections), "found %s" % sorted(sections))

    # ---- every anchor in the whole project resolves -----------------
    # The silent failure this exists for: a wrong anchor shows the top of the
    # page, which looks exactly like a link that was never contextual.
    dead = []
    for rel in (HELP, "main_python/web/hub.html",
                "nong/main_python_set_nong/web/index.html",
                "firmware/src/web/WebUI.h"):
        f = F.CODE / rel
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for a in re.findall(r'/help#([a-z0-9-]+)', text):
            if a not in sections:
                dead.append("%s -> #%s" % (rel, a))
        if rel == HELP:
            for a in re.findall(r'href="#([a-z0-9-]+)"', text):
                if a not in sections:
                    dead.append("%s -> #%s" % (rel, a))
    t.eq(dead, [],
         "every help anchor in the project points at a section that exists")

    # ---- the hub's Help link follows the tab ------------------------
    hub = (F.CODE / "main_python" / "web" / "hub.html").read_text(encoding="utf-8")
    t.contains(hub, "function helpFor",
               "the hub page aims its Help link")
    m = re.search(r"var HELP_SECTION = \{(.*?)\};", hub, re.S)
    if t.ok(m, "and has a section per tab"):
        mapped = dict(re.findall(r"(\w+):\s*'([a-z0-9-]*)'", m.group(1)))
        tabs = set(re.findall(r"data-go=\"(\w+)\"", hub))
        missing = sorted(tabs - set(mapped))
        t.eq(missing, [],
             "every tab in the strip has a help section chosen for it")
        for tab, sec in mapped.items():
            t.ok(sec in sections,
                 "the %s tab points at a real section (#%s)" % (tab, sec),
                 "a wrong anchor silently shows the top of the page")
    t.contains(hub, "helpFor(name)",
               "and it is re-aimed whenever the tab changes",
               )

    # ---- a tool brings its own help link ----------------------------
    reg = (F.CODE / "tools" / "registry.py").read_text(encoding="utf-8")
    t.contains(reg, '"help": ""',
               "an app can declare which section is about it")
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry  # noqa: PLC0415
    for a in registry.apps():
        if a.get("help"):
            t.ok(a["help"] in sections,
                 "%s names a real help section (#%s)" % (a["id"], a["help"]),
                 "app.json can point anywhere; a wrong name is a dead link "
                 "that looks like a working one")
    t.contains(hub, "if(a.help){",
               "and the tool row only offers a link when there is one to offer",
               )

    # ---- and the by-task way in reaches everything ------------------
    idx = help_html[help_html.find('<section id="bytask"'):]
    idx = idx[:idx.find("</section>")]
    if not t.ok(idx, "there is a by-task index at the top"):
        return
    linked = set(re.findall(r'href="#([a-z0-9-]+)"', idx))
    orphans = sorted(sections - linked - {"bytask"})
    t.eq(orphans, [],
         "every section is reachable from a task, not only from the order "
         "they happen to appear in")
    heads = re.findall(r"<h3>([^<]+)</h3>", idx)
    t.ok(3 <= len(heads) <= 8,
         "the index is short enough to read at a glance (%d groups)" % len(heads),
         "a list as long as the page is a second table of contents, not a way in")
