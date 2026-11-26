"""A saved project can be named in Thai; nothing can climb out of its folder.

User 2026-11-21: staff are Thai, and "bad name" for a Thai show name was a dead
end. Files that stay on this PC (projects, sequences, shows) take any language
(main.py pc_name); what a board's SD card or command line receives stays ASCII
(safe_name), so that route still refuses and says so in plain words.
"""
import json
import urllib.parse

import qc as F

AREA = "persistence"
TITLE = "Thai names work for saved files on the PC, path tricks never do"
SLOW = False


def run(t):
    base, main = F.start_hub()
    F.login(base)
    name = "การแสดงงานวัด ๑"
    body = json.dumps({"name": name, "project": {"x": 1}}).encode()
    code, text = F.post(base + "/api/save", body)
    t.ok(code == 200, "saving a Thai-named project works", "%s %s" % (code, text[:100]))
    try:
        code, text = F.get(base + "/api/load?name=" + urllib.parse.quote(name + ".json"))
        t.ok(code == 200, "and it loads back by that name", "%s %s" % (code, text[:100]))
    finally:
        f = main.PROJECTS / (name + ".json")
        if f.exists():
            f.unlink()
    for bad in ("../x", "a/b", "a\\b", "..", ".hidden", "x" * 90, "a:b", ""):
        code, _ = F.post(base + "/api/save", json.dumps({"name": bad}).encode())
        t.ok(code == 400, "name %r is refused" % bad[:20], str(code))
    # Windows device names (found by the 2026-11-22 sweep). A full body is
    # sent: without "project" the save fails for another reason and the
    # name check is never reached, so a body of just a name proves nothing.
    for dev in ("con", "NUL.json", "com1", "lpt9.txt", "name."):
        body = json.dumps({"name": dev, "project": {"x": 1}}).encode()
        code, text = F.post(base + "/api/save", body)
        t.ok(code == 400, "device name %r is refused" % dev, "%s %s" % (code, text[:80]))
    # a save has its own 20 MB ceiling (2026-11-22 sweep: 60 MB was accepted)
    big = json.dumps({"name": "toobig", "project": "A" * (21 * 1048576)}).encode()
    try:
        code, text = F.post(base + "/api/save", big)
    except OSError as e:     # the hub may close the line on an oversize body
        code, text = 400, str(e)
    # 413 "payload too large" is the exact refusal; 400 is what the line closing used to look like
    t.ok(code in (400, 413), "a 21 MB save is refused", "%s %s" % (code, text[:80]))
    t.ok(not (main.PROJECTS / "toobig.json").exists(), "and nothing was written")
    t.ok(main.safe_name("track one.yaml") == "track one.yaml", "robot names still pass when plain")
    try:
        main.safe_name(name)
        t.ok(False, "a Thai name still cannot go to the robot's SD card")
    except ValueError:
        t.ok(True, "a Thai name still cannot go to the robot's SD card")
