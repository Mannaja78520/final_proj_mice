"""Which labels on a page does its Help part never mention?  (user 2026-11-22: Help must match the app)

docs/help_map.json says which Help part describes which page. A label is the text of a
button, tab or heading. A page label that its Help part does not contain is "drift": a
feature was added without telling the person who reads Help. check_help_drift keeps a
baseline (qc/data/help_drift_baseline.json) so the list can only shrink: a NEW unmentioned
label fails QC until Help (each app's help/ folder, every language) is updated.

    python tools/help_drift.py            the unmentioned labels per page
    python tools/help_drift.py --baseline write the current list as the baseline
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "docs" / "help_map.json"
BASE = ROOT / "qc" / "data" / "help_drift_baseline.json"
TAG = re.compile(r"<(button|h2|h3|summary|label)\b[^>]*>([\s\S]*?)</\1>", re.I)


def labels(page):
    html = (ROOT / page).read_text(encoding="utf-8")
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", "", html)
    out = []
    for _, inner in TAG.findall(html):
        text = re.sub(r"<[^>]+>", "", inner)
        text = " ".join(text.replace("&amp;", "&").split())
        text = re.sub(r"^[^\w]+", "", text).strip()          # leading emoji / arrows
        if len(text) >= 4 and re.search("[A-Za-z]{3}", text) and text not in out:
            out.append(text)
    return out


def drift():
    result = {}
    for page, part in json.loads(MAP.read_text(encoding="utf-8")).items():
        if page.startswith("_"):
            continue
        path = ROOT / part
        fragments = [path / (code + ".html") for code in ("th", "en")] if path.is_dir() else [path]
        source = " ".join(f.read_text(encoding="utf-8") for f in fragments)
        help_text = " ".join(source.replace("&amp;", "&").split()).lower()
        result[page] = [x for x in labels(page) if x.lower() not in help_text]
    return result


if __name__ == "__main__":
    d = drift()
    if "--baseline" in sys.argv:
        BASE.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for page, miss in d.items():
        print(page, len(miss))
        for m in miss[:200]:
            print("   ", m)
