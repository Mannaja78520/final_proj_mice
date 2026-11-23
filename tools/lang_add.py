"""Add translations to the language packs in one step.

    python tools/lang_add.py batch.json

batch.json = [{"src": "<text as the page carries it>", "th": "...", "en": "...", "zh": "...", "ja": "..."}, ...]
A Thai source text is a key of en/zh/ja; an English source text is a key of th/zh/ja
(see docs/LANGUAGES.md). Existing non-empty entries are kept unless --force.
--help writes to shared/web/lang/help/<code>.json (Help page strings) instead of the main packs;
a missing pack file is created.
"""
import json
import sys
from pathlib import Path

LANG = Path(__file__).resolve().parent.parent / "shared" / "web" / "lang"


def is_thai(t):
    return any("฀" <= c <= "๿" for c in t)


def main(argv):
    force = "--force" in argv
    lang_dir = LANG / "help" if "--help" in argv else LANG
    lang_dir.mkdir(parents=True, exist_ok=True)
    items = json.loads(Path([a for a in argv[1:] if not a.startswith("--")][0]).read_text(encoding="utf-8"))
    packs = {}
    for c in ("th", "en", "zh", "ja"):
        f = lang_dir / (c + ".json")
        packs[c] = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"name": c, "strings": {}}
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
        # write_bytes: write_text would turn LF into CRLF on Windows
        (lang_dir / (code + ".json")).write_bytes((json.dumps(p, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("added/updated %d entries" % added)


if __name__ == "__main__":
    main(sys.argv)
