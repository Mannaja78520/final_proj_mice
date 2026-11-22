"""Texts of the Help parts that a language still lacks (parts are written in Thai or English).

    python tools/help_texts.py hub          numbered Thai texts of parts/hub.html with no English yet
    python tools/help_texts.py hub zh       ...with no Chinese yet
    python tools/help_texts.py --all        count missing per part and language
The packs are shared/web/lang/help/<code>.json, keyed by the page's own (whitespace-collapsed) text.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = ROOT / "main_python/web/help/parts"
PACKS = ROOT / "shared/web/lang/help"
LANGS = ("th", "en", "zh", "ja")
SKIPPED = re.compile(r"<(script|style|code|pre)\b[\s\S]*?</\1>", re.I)


def texts(part):
    src = SKIPPED.sub("", (PARTS / (part + ".html")).read_text(encoding="utf-8"))
    seen = []
    for raw in re.findall(r">([^<>]+)<", src):
        t = " ".join(html.unescape(raw).split())
        if (re.search("[\u0e00-\u0e7f]", t) or re.search("[A-Za-z]{3}", t)) and t not in seen:
            seen.append(t)
    return seen


def pack(code):
    """The Help file plus the shared pack (a label like "Save" is already translated there)."""
    out = {}
    for p in (PACKS.parent / (code + ".json"), PACKS / (code + ".json")):
        if p.is_file():
            out.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8"))["strings"].items() if v})
    return out


def missing(part, code):
    """Thai pages' own text needs no Thai; the English pages' own text needs no English."""
    have = pack(code)
    thai = lambda t: re.search("[\u0e00-\u0e7f]", t) is not None
    return [t for t in texts(part) if not have.get(t) and not (code == "th" and thai(t)) and not (code == "en" and not thai(t))]


if __name__ == "__main__":
    if "--merge" in sys.argv:
        # --merge <part> <file>: lines "index|th|en|zh|ja" numbered as printed for that part; blank = skip
        part, src = sys.argv[2], sys.argv[3]
        todo = [t for t in texts(part) if any(t in missing(part, c) for c in LANGS)]
        packs = {c: json.loads((PACKS / (c + ".json")).read_text(encoding="utf-8")) if (PACKS / (c + ".json")).is_file()
                 else {"name": c, "strings": {}} for c in LANGS}
        for line in open(src, encoding="utf-8"):
            if line.strip():
                cells = line.rstrip("\n").split("|")
                key = todo[int(cells[0])]
                for code, val in zip(LANGS, cells[1:5]):
                    if val.strip():
                        packs[code]["strings"][key] = val.strip()
        PACKS.mkdir(parents=True, exist_ok=True)
        for c in LANGS:
            (PACKS / (c + ".json")).write_text(json.dumps(packs[c], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    elif "--all" in sys.argv:
        for f in sorted(PARTS.glob("*.html")):
            print("%-12s %4d texts  missing %s" % (f.stem, len(texts(f.stem)),
                  " ".join("%s=%d" % (c, len(missing(f.stem, c))) for c in LANGS)))
    else:
        part = sys.argv[1]
        todo = [t for t in texts(part) if any(t in missing(part, c) for c in LANGS)]
        for i, t in enumerate(todo):
            print(i, "[" + "".join(c for c in LANGS if t in missing(part, c)) + "]", t)
