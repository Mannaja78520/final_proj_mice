"""The face app is reachable from our hub, and its addresses are data.

First step of the system-integration plan (docs/system_integral.html): a tile
that opens Reconize, and nothing that can move a robot yet. Small on purpose -
the button exists before any greeting can.

WHAT THIS HOLDS, AND WHY EACH LINE EXISTS

  * the tool is listed and its page really serves. That is `check_registries`'s
    job for every app; here it is the proof that adding an outside program cost
    one folder and no hub code.
  * **the outside address is NOT in app.json.** `registry.py:107` lets `url`
    override the served path with no validation of the scheme, so
    `"url": "http://127.0.0.1:5173"` would render a tile that opens their app -
    and would break `check_registries`, which GETs `base + path` for every
    listed app. The addresses live in `config/partners.json`, served at
    `/api/partners`, and the page reads them from there. Changing where Reconize
    lives is one edit and no code.
  * **and the page keeps no second copy of them.** It carried its own
    `links.json` until A2-2; two lists of the same addresses disagree the first
    time one is edited, and the watcher would be reading the other one.
  * **no password is anywhere under `apps/`.** Every file in an app folder is
    served with NO login (`main.py:3702-3715`), so a credentials file there is a
    credentials file published to the venue WiFi. A plan review caught that
    placement before it shipped; this is what stops it coming back.
  * the camera app says what it really is: **ESP32 camera**. It only ever knew
    ESP32-CAM boards - the page builds its list from modules whose `type` is
    `cam` - so the old name promised a webcam it cannot show.
"""
import json
import sys

import qc as F


AREA = "hub"
TITLE = "the face app opens from our hub, with no secret in the served folder"

# Anything that looks like a login. A file under apps/ is public by design.
SECRET_HINTS = ("password", "passwd", "secret", "token", "jwt", "api_key",
                "apikey", "credential")


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                        # noqa: E402

    apps = {a["id"]: a for a in registry.apps()}
    t.ok("faces" in apps, "the Reconize tool is listed", sorted(apps))
    if "faces" not in apps:
        return
    faces = apps["faces"]
    t.eq(faces["name"], "Reconize", "under the name the owner chose")

    # ---- the outside address is NOT in the manifest --------------------
    # Checked BEFORE anything is fetched, on purpose. `url` replaces the tile's
    # path with whatever it says, so `base + path` becomes
    # "http://127.0.0.1:8770http://127.0.0.1:5173" and the check dies with a
    # traceback instead of naming the rule that was broken. A sabotage caught
    # by a crash is caught by luck.
    manifest = json.loads(registry.strip_jsonc(
        (F.CODE / "apps/faces/app.json").read_text(encoding="utf-8")))
    t.ok(not manifest.get("url"),
         "app.json carries no outside address",
         "registry.py:107 would turn `url` into the tile's path, and "
         "check_registries GETs base+path for every app - an absolute address "
         "there breaks the gate and hides the real one from links.json")
    if manifest.get("url"):
        return

    # ---- the page serves, like every other app ------------------------
    base, _main = F.start_hub()
    code, body = F.get(base + faces["path"])
    t.eq(code, 200, "and its page really serves at %s" % faces["path"])
    t.contains(body, "Open Reconize", "with the one button this step is about")
    # The same head as every other app page (user 2026-09-17: *why UI it not
    # the same as other? make it like other*).
    t.ok('<div class="head">' in body and "🏠 Hub</button>" in body,
         "and the same head as the other app pages: Hub button, title, switch",
         "the page had its own h1 and a text link back to the hub")

    # ---- ONE list of addresses, not one per page ----------------------
    # The tile used to carry its own links.json beside it. Two lists disagree
    # the first time one is edited, and the watcher reads the other one - so
    # the page now asks /api/partners like everything else.
    # The FETCH, not the words. Asserting on "/api/partners" alone passed with
    # the fetch replaced by a hardcoded object, because the phrase still sat in
    # this page's own comment - caught by sabotage, 2026-09-10.
    t.contains(body, 'fetch("/api/partners"',
               "the page asks the hub where Reconize lives")
    t.ok("127.0.0.1" not in body,
         "and no address is written into the page itself",
         "an address here is a second copy of config/partners.json: moving "
         "Reconize would need a code edit, and whichever list was not edited "
         "keeps sending the rig to the old port")
    t.ok(not (F.CODE / "apps/faces/links.json").exists(),
         "and keeps no address list of its own",
         "config/partners.json is the one list; a second copy beside the page "
         "is the copy that goes stale")

    code, raw = F.get(base + "/api/partners")
    t.eq(code, 200, "and that list serves with no login")
    entry = (json.loads(raw).get("partners") or {}).get("reconize") or {}
    for key in ("open", "api", "health", "folder"):
        t.ok(entry.get(key), "the entry names the %s" % key, entry)

    # ---- nothing secret under apps/, ever -----------------------------
    leaks = []
    for p in (F.CODE / "apps").rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".json", ".txt", ".env", ".ini"):
            continue
        name = p.name.lower()
        if any(h in name for h in SECRET_HINTS):
            leaks.append(p.relative_to(F.CODE).as_posix())
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for hint in SECRET_HINTS:
            if ('"%s"' % hint) in text and '"%s": ""' % hint not in text:
                leaks.append("%s (%s)" % (p.relative_to(F.CODE).as_posix(), hint))
                break
    t.ok(not leaks,
         "no file under apps/ holds a login",
         "every file in an app folder is served with no login at all, so a "
         "credentials file there is published to anyone on the venue WiFi: %s"
         % leaks)

    # ---- the camera app is honest about what it is --------------------
    t.ok(apps.get("camera", {}).get("name") == "ESP32 camera",
         "the camera app says which camera it can actually show",
         "it lists only modules whose type is cam, so the old name promised a "
         "webcam it has never been able to open; got %r"
         % apps.get("camera", {}).get("name"))
