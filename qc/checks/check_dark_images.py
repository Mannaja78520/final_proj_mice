"""Dark themes show dark pictures (user 2026-11-23: a bright cartoon on a black page looked pasted on).

tools/make_dark_images.py writes <n>-dark.webp for every drawn picture and shared/web/img-dark.css
(one rule per picture and dark theme). The hub serves both; a new picture without its dark version,
or a dark theme missing from the list, fails here.
"""
import re
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "dark themes have a dark picture for every drawn picture"
SLOW = False


def run(t):
    root = Path(F.CODE) / "shared" / "web"
    base, _main = F.start_hub()
    css_code, css = F.get(base + "/img-dark.css")
    t.ok(css_code == 200 and "-dark.webp" in css, "the hub serves /img-dark.css", str(css_code))
    pictures = [p for sub in ("apps", "help") for p in (root / "img" / sub).glob("*.webp")
                if not p.name.endswith("-dark.webp") and p.stem != "help"]
    t.ok(len(pictures) >= 8, "pictures were found", str(len(pictures)))
    for p in pictures:
        rel = "/img/%s/%s" % (p.parent.name, p.stem)
        t.ok(p.with_name(p.stem + "-dark.webp").is_file(), "%s has a dark version" % rel)
        t.ok(('img[src="%s.webp"]{content:url(%s-dark.webp)}' % (rel, rel)) in css, "%s is swapped by the CSS" % rel)
    themes = open(root / "themes.css", encoding="utf-8").read()
    dark = re.findall(r':root\[data-theme="(\w+)"\]\{[^}]*color-scheme:\s*dark', themes.replace("\n", ""))
    # The CSS keys on data-mode="dark" (mice.js sets it from --theme-mode), so every dark theme,
    # packs included, gets the dark pictures: each dark theme must DECLARE itself dark.
    t.ok('html[data-mode="dark"]' in css, "the CSS swaps for any dark mode", css[:120])
    declared = re.findall(r':root\[data-theme="(\w+)"\]\{[^}]*--theme-mode:\s*"dark"', themes.replace("\n", ""))
    t.ok(bool(dark) and sorted(dark) == sorted(declared),
         "every dark theme declares --theme-mode dark", "%s vs %s" % (dark, declared))
    code, _ = F.get(base + "/img/apps/studio-dark.webp")
    t.ok(code == 200, "a dark picture is served", str(code))
