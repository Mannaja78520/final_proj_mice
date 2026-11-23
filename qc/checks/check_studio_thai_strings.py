"""Every Thai sentence Studio's code puts on screen has an English, Chinese and Japanese entry.

2026-11-23 case review: the screenshot probe sees only the states it clicks to. Notices such as
"the song file size is not valid" appear only when something goes wrong, so the page showed
Thai to an English, Chinese or Japanese user exactly when they needed to understand. Pieces that
are glued to a variable at run time (ending in ": " or a space) and confirm() texts (not in the
page, so the language layer cannot reach them) are left out.
"""
import json
import re

import qc as F

AREA = "web"
TITLE = "Studio: every Thai message in the code is translated in en, zh and ja"
SLOW = False

LIT = re.compile(r"""(['"`])((?:(?!\1).)*[฀-๿](?:(?!\1).)*)\1""")


def run(t):
    parts = F.CODE / "nong" / "main_python_set_nong" / "web" / "app_parts"
    packs = {l: json.loads((F.CODE / "shared" / "web" / "lang" / (l + ".json")).read_text(encoding="utf-8"))["strings"]
             for l in ("en", "zh", "ja")}
    lits = {}
    for f in sorted(parts.glob("*.js")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("//"):
                continue
            for m in LIT.finditer(line):
                s = m.group(2)
                if s.endswith((" ", ":")) or s.rstrip().endswith(":") or "\\n" in s:
                    continue          # glued to a variable, or a confirm() text
                lits.setdefault(s.strip(), "%s:%d" % (f.name, n))
    t.ok(len(lits) > 20, "found the Thai messages in the code", len(lits))
    for lang, pack in packs.items():
        missing = sorted(s for s in lits if not pack.get(s))
        t.ok(not missing, "every Thai message has a %s entry" % lang,
             "; ".join("%s (%s)" % (s[:40], lits[s]) for s in missing[:5]))
