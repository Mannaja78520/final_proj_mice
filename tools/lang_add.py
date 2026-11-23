"""Add translations to the language packs in one step.

    python tools/lang_add.py batch.json

batch.json = [{"src": "<text as the page carries it>", "th": "...", "en": "...", "zh": "...", "ja": "..."}, ...]
A Thai source text is a key of en/zh/ja; an English source text is a key of th/zh/ja
(see docs/LANGUAGES.md). Existing non-empty entries are kept unless --force.
"""
import json
import sys
from pathlib import Path

LANG = Path(__file__).resolve().parent.parent / "shared" / "web" / "lang"


def is_thai(t):
    return any("฀" <= c <= "๿" for c in t)


def main(argv):
    force = "--force" in argv
    items = json.loads(Path([a for a in argv[1:] if not a.startswith("--")][0]).read_text(encoding="utf-8"))
    packs = {c: json.loads((LANG / (c + ".json")).read_text(encoding="utf-8")) for c in ("th", "en", "zh", "ja")}
    added = 0
    for it in items:
        src = it["src"]
        for code in ("th", "en", "zh", "ja"):
            if code == "th" and is_thai(src):
                continue
            if code == "en" and not is_thai(src):
                continue
            val = it.get(code)
            if not val:
                continue
            s = packs[code]["strings"]
            if force or not s.get(src):
                s[src] = val
                added += 1
    for code, p in packs.items():
        (LANG / (code + ".json")).write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added/updated %d entries" % added)


if __name__ == "__main__":
    main(sys.argv)
