"""Language packs for the hub pages: list, start a new one, see what is missing.

A pack is ONE file, shared/web/lang/<code>.json:
    {"name": "Français", "strings": {"<text on the page>": "<translation>", ...}}
The hub lists the folder by itself (/lang/index.json) and every page's picker
shows the new language - no code changes. An entry left "" (empty) or missing
keeps the page's own text, so a half-finished pack never breaks a page.
The keys are the texts the pages carry: English ones (th.json) and the Thai
ones (en.json). Full how-to: docs/LANGUAGES.md.

    python tools/lang.py list                 packs and how complete each is
    python tools/lang.py new fr "Français"    start a pack with every key, empty
    python tools/lang.py missing fr           keys still empty/missing (for a translator)
    python tools/lang.py check                every pack is valid JSON with name + strings
"""
import json
import sys
from pathlib import Path

LANG = Path(__file__).resolve().parent.parent / "shared" / "web" / "lang"


def read(code):
    return json.loads((LANG / (code + ".json")).read_text(encoding="utf-8"))


def all_keys():
    keys = {}
    for code in ("th", "en"):          # the two packs that name every text the pages carry
        if (LANG / (code + ".json")).is_file():
            for k in read(code)["strings"]:
                keys[k] = 1
    return list(keys)


def done(code):
    s = read(code)["strings"]
    return sum(1 for k in all_keys() if s.get(k))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "list":
        total = len(all_keys())
        for f in sorted(LANG.glob("*.json")):
            d = read(f.stem)
            print("%-6s %-14s %4d / %d texts" % (f.stem, d.get("name", "?"), done(f.stem), total))
    elif cmd == "new" and len(argv) >= 4:
        code, name = argv[2], argv[3]
        target = LANG / (code + ".json")
        if target.exists():
            sys.exit("%s already exists; edit it, or run: missing %s" % (target.name, code))
        pack = {"name": name, "strings": {k: "" for k in all_keys()}}
        target.write_text(json.dumps(pack, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("created %s with %d empty entries" % (target, len(pack["strings"])))
    elif cmd == "missing" and len(argv) >= 3:
        s = read(argv[2])["strings"]
        for k in all_keys():
            if not s.get(k):
                print(k)
    elif cmd == "check":
        bad = 0
        for f in sorted(LANG.glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                assert isinstance(d.get("name"), str) and isinstance(d.get("strings"), dict)
                assert all(isinstance(v, str) for v in d["strings"].values())
            except Exception as e:      # noqa: BLE001
                bad += 1
                print("BAD", f.name, e)
        sys.exit(1 if bad else 0)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
