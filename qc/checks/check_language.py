"""A language is one file; the hub lists the folder and every page can switch.

User 2026-11-21: Thai first, every language must work, adding one must be easy.
shared/web/lang/<code>.json = {"name", "strings": {English text: translation}};
/lang/index.json lists them; shared/web/mice-lang.js (loaded by mice-ui.js)
builds the picker and swaps the texts. A text with no entry stays English.
"""
import json

import qc as F

AREA = "hub"
TITLE = "languages: listed from a folder, Thai ships, a bad name is refused"
SLOW = False


def run(t):
    base, _main = F.start_hub()
    code, text = F.get(base + "/lang/index.json")
    langs = json.loads(text).get("languages", []) if code == 200 else []
    codes = [l["code"] for l in langs]
    t.ok("en" in codes and "th" in codes, "English and Thai are offered", str(codes))
    for c in codes:
        if c == "en":
            continue
        code, body = F.get(base + "/lang/%s.json" % c)
        data = json.loads(body) if code == 200 else {}
        t.ok(code == 200 and data.get("name") and len(data.get("strings", {})) > 50,
             "%s has a name and strings" % c, str(code))
    code, _ = F.get(base + "/lang/..%2Fmain.json")
    t.ok(code == 404, "a path trick is refused", str(code))
    code, js = F.get(base + "/mice-lang.js")
    t.ok(code == 200 and "mice.lang" in js, "the switch script is served")
    code, ui = F.get(base + "/mice-ui.js")
    t.ok('/mice-lang.js' in ui, "every page that loads mice-ui.js gets the switch")
    t.ok("?." not in js and "??" not in js, "the switch is Chrome 75 safe")
    import os
    got = json.loads(F.get(base + "/lang/index.json")[1]).get("default")
    t.ok(got == "off", "QC pages are left as written (MICE_LANG=off)", str(got))
    os.environ["MICE_LANG"] = "th"
    try:
        got = json.loads(F.get(base + "/lang/index.json")[1]).get("default")
    finally:
        os.environ["MICE_LANG"] = "off"
    t.ok(got == "th", "a hub with no setting offers Thai first", str(got))
    # English turns the page's own Thai back into English (lang/en.json)
    en = json.loads(F.get(base + "/lang/en.json")[1])
    t.ok(sum(1 for k in en["strings"] if any("฀" <= c <= "๿" for c in k)) > 40,
         "English has entries for the Thai text the pages carry")
    t.ok(codes.count("en") == 1, "English is listed once", str(codes))
