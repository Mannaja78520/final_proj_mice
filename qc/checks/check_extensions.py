"""This PC's apps are extensions: added by folder, removed, updated (A51-2).

User 2026-10-27: the hub is the centre, and a venue PC may have no face app,
no photo booth or no prize machine - or one app more than ours. "Everything
may be missing or extra at any time, and adding must always work." So:

  * a folder says what app it is with mice-app.json (their file, wins), our
    app.json, or a partner's "detect" list in config/partners.json - we
    never write into a friend's folder to recognise it;
  * this PC's list is a file of the machine's (extensions.json), never git;
  * remove hides, never deletes; restore brings a shipped app back;
  * an app that "needs" a partner is not listed where that partner is not
    installed - a client without Reconize sees no Reconize tile;
  * a partner folder written {parent}/... follows the tree when it moves
    (code -> mice_system), and this PC's chosen folder wins;
  * update runs the app's own "update" command (else git pull --ff-only).

Driven against throwaway folders, then through the running hub's routes.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "apps are extensions of this PC: add by folder, remove, update, missing ones hidden"


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def run(t):
    sys.path.insert(0, str(F.HUB))
    import extensions as X

    box = Path(tempfile.mkdtemp(prefix="qc_ext_"))
    try:
        data = box / "mice_system"                 # the hub's own tree
        data.mkdir()
        friend = box / "Face_Regonize"             # a friend's app, no file of ours
        _write(friend / "Start Reconize.vbs", "x")
        (friend / "backend").mkdir()
        (friend / "frontend").mkdir()
        theirs = box / "LuckyDraw"                 # an app that ships mice-app.json
        _write(theirs / X.MANIFEST, json.dumps({
            "id": "lucky-draw", "name": "Lucky draw", "kind": "app", "icon": "🎲",
            "entry": "index.html",
            "update": [sys.executable, "-c", "print('updated lucky draw')"]}))
        _write(theirs / "index.html", "<h1>lucky</h1>")
        (box / "Holiday photos").mkdir()           # not an app at all
        templates = {"reconize": {"name": "Reconize", "folder": "{parent}/Face_Regonize",
                                  "detect": ["Start Reconize.vbs", "backend", "frontend"]},
                     "booth": {"name": "Booth", "folder": str(box / "nowhere"),
                               "detect": ["scripts/run-main.ps1"]}}
        shipped = [{"id": "faces", "needs": "reconize"}, {"id": "gacha"},
                   {"id": "booth-app", "needs": "booth"}]
        E = X.Extensions(box / "pc" / "extensions.json", data,
                         partners=lambda: templates, apps=lambda: shipped)

        # ---- folders follow the tree ------------------------------------
        t.eq(Path(E.expand("{parent}/Face_Regonize")).resolve(), friend.resolve(),
             "{parent} is the folder the hub's tree sits in")
        rec = E.partner("reconize", templates["reconize"])
        t.ok(rec["installed"] and Path(rec["folder"]).resolve() == friend.resolve(),
             "a partner beside the tree is found and installed", rec)
        booth = E.partner("booth", templates["booth"])
        t.ok(not booth["installed"], "a partner whose folder is missing is not installed", booth)

        # ---- missing partners hide their apps -----------------------------
        parts = {k: E.partner(k, v) for k, v in templates.items()}
        shown = [a["id"] for a in shipped if E.visible(a, parts)]
        t.eq(shown, ["faces", "gacha"],
             "an app whose partner is not on this PC is not listed")

        # ---- what a folder is ---------------------------------------------
        t.eq((E.detect(friend) or {}).get("id"), "reconize",
             "a friend's folder is known by our template, nothing written into it")
        t.ok(sorted(p.name for p in friend.rglob("*")) ==
             sorted(["Start Reconize.vbs", "backend", "frontend"]),
             "and the friend's folder is untouched", "")
        got = E.detect(theirs) or {}
        t.ok(got.get("id") == "lucky-draw" and got.get("source") == "their mice-app.json",
             "their own mice-app.json says what the app is", got)
        t.eq(E.detect(box / "Holiday photos"), None, "a folder with no app is not an app")
        found = sorted(c["id"] for c in E.candidates())
        t.ok("lucky-draw" in found and "reconize" in found,
             "apps beside the tree are offered before anyone types a folder", found)

        # ---- add / remove / restore -------------------------------------------
        E.add(str(theirs))
        extra = E.extra_apps()
        t.ok(len(extra) == 1 and extra[0]["path"] == "/app/lucky-draw/"
             and Path(extra[0]["dir"]) == theirs,
             "an added app is served from its own folder", extra)
        try:
            E.add(str(box / "Holiday photos"))
            t.ok(False, "adding a folder with no app is refused", "it was added")
        except ValueError:
            t.ok(True, "adding a folder with no app is refused", "")
        moved = box / "elsewhere" / "FR"
        shutil.copytree(friend, moved)
        E.add(str(moved))
        t.eq(E.partner("reconize", templates["reconize"])["folder"], str(moved),
             "this PC's chosen folder wins over the shipped one")
        E.remove("gacha")
        t.ok(not E.visible({"id": "gacha"}, parts), "removing a shipped app hides it here", "")
        E.restore("gacha")
        t.ok(E.visible({"id": "gacha"}, parts), "and restore brings it back", "")
        E.remove("lucky-draw")
        t.eq(E.extra_apps(), [], "removing an added app takes it off the list")
        t.ok((theirs / "index.html").is_file(), "and deletes nothing on disk", "")
        stored = json.loads((box / "pc" / "extensions.json").read_text(encoding="utf-8"))
        t.ok("lucky-draw" not in stored["added"] and "reconize" in stored["added"],
             "the list is one file of this PC's", stored)

        # ---- their own file makes a partner official ---------------------------
        _write(moved / X.MANIFEST, json.dumps({"id": "reconize", "kind": "partner",
                                               "open": "http://127.0.0.1:5999"}))
        here = E.partners_here(templates)
        t.ok(here["reconize"].get("open") == "http://127.0.0.1:5999"
             and here["reconize"].get("detect") == templates["reconize"]["detect"],
             "a friend's own mice-app.json overrides our template field by field",
             here["reconize"])

        # ---- update ---------------------------------------------------------------
        E.add(str(theirs))
        up = E.update("lucky-draw")
        t.ok(up.get("ok") and "updated lucky draw" in up.get("output", ""),
             "update runs the app's own update command in its folder", up)
        t.ok(not E.update("gacha").get("ok"), "an app with no known way to update says so", "")
    finally:
        shutil.rmtree(box, ignore_errors=True)

    # ---- one store per machine, never in git ---------------------------------------
    ignored = (F.CODE / ".gitignore").read_text(encoding="utf-8")
    t.contains(ignored, "main_python/extensions.json", "git never keeps this PC's list")
    t.contains((F.CODE / "promote.py").read_text(encoding="utf-8"), '"extensions.json"',
               "and a promote never copies one PC's list over another's")
    for app, pid in (("faces", "reconize"), ("photobooth", "photobooth"), ("all-jao", "all-jao")):
        cfg = json.loads("\n".join(l for l in (F.CODE / "apps" / app / "app.json")
                                   .read_text(encoding="utf-8").splitlines()
                                   if not l.strip().startswith("//")))
        t.eq(cfg.get("needs"), pid, "the %s tile needs %s installed" % (app, pid))

    # ---- through the hub --------------------------------------------------------------
    base, main = F.start_hub()
    code, body = F.get(base + "/api/extensions")
    d = json.loads(body) if code == 200 else {}
    t.ok(d.get("ok") and isinstance(d.get("apps"), list) and isinstance(d.get("found"), list),
         "GET /api/extensions lists apps, partners and what was found", body[:200])
    code, body = F.post(base + "/api/extensions/remove", json.dumps({"id": "gacha"}).encode())
    _, apps = F.get(base + "/api/apps")
    gone = "gacha" not in [a["id"] for a in json.loads(apps).get("apps", [])]
    F.post(base + "/api/extensions/restore", json.dumps({"id": "gacha"}).encode())
    _, apps = F.get(base + "/api/apps")
    back = "gacha" in [a["id"] for a in json.loads(apps).get("apps", [])]
    t.ok(code == 200 and gone and back,
         "removing through the hub hides the tile, restoring brings it back",
         "%s %s %s" % (code, gone, back))
    t.ok(str(main.EXT.store) != str(Path(main.HERE) / "extensions.json"),
         "QC never touches this PC's real list", str(main.EXT.store))
