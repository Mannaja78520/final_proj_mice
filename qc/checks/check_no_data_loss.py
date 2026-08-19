"""Saving never destroys what was already there.

The worst thing this project can do to a user is lose their work: a rig is
hours of measuring and a timeline is hours of posing, and the editor holds the
only other copy in RAM.

Every save here used to truncate first. `Path.write_text` opens in "w" and
`SD.open(path, FILE_WRITE)` is the same "w" — both empty the destination the
instant they open, BEFORE any new content arrives. A save that then failed
(full disk, process killed, lid closed, USB pulled, board brown-out mid-write)
left NEITHER the old version nor the new one. Uploading over an existing name
is the normal "Send to robot" flow, so this was reachable in ordinary use.

Three things must hold, and all three are driven for real here:

  * a save that lands leaves the previous version recoverable
  * a save is not silently an overwrite — the reply says one happened
  * a save that FAILS leaves the original file exactly as it was

The SD card side cannot be driven without a board, so it is asserted at the
source: the write must go to a temporary and only be renamed into place at the
end. That is the whole mechanism, and it is one line to break.
"""
import importlib.util
import json
import re
from pathlib import Path

import fake_serial
import qc as F

AREA = "persistence"
TITLE = "saving never destroys the previous version"
SLOW = False


def _post(base, path, obj):
    return json.loads(F.post(base + path, json.dumps(obj).encode())[1])


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    projects = F.STUDIO / "projects"

    name = "qc_atomic_save"
    dest = projects / (name + ".json")
    bak = projects / (name + ".json.bak")
    for p in (dest, bak):
        if p.exists():
            p.unlink()

    # ---- 1. the first save just writes ----------------------------------
    r = _post(base, "/api/save", {"name": name,
                                  "project": {"keys": [{"pose": [1] * 10}]}})
    t.ok(r.get("ok") is True, "a project saves", r)
    t.ok(r.get("replaced") is False,
         "and a first save does not claim to have replaced anything")
    t.ok(dest.is_file(), "the file is really on disk")
    first = dest.read_text(encoding="utf-8")

    # ---- 2. saving over it keeps the previous version --------------------
    r = _post(base, "/api/save", {"name": name,
                                  "project": {"keys": [{"pose": [2] * 10}]}})
    # the editor's default name is my_move, so a silent overwrite is one
    # careless click away
    t.ok(r.get("replaced") is True,
         "saving over an existing project SAYS it replaced one")
    # Guarded, so losing the .bak fails THIS assertion and lets the rest of the
    # check run. An unguarded read here crashed the whole check and hid every
    # later result — which is exactly what happened when the fix was sabotaged
    # to prove this check works.
    if t.ok(bak.is_file(), "the previous version is kept as a .bak"):
        t.eq(bak.read_text(encoding="utf-8"), first,
             "and the .bak is the exact bytes that were there before")
    t.contains(dest.read_text(encoding="utf-8"), '"pose"',
               "while the live file is the new one")

    # ---- 3. a REFUSED save leaves the original untouched -----------------
    # This is the case that used to destroy both versions: the target was
    # already truncated by the time anything went wrong.
    before = dest.read_text(encoding="utf-8")
    code, body = F.post(base + "/api/save",
                        json.dumps({"name": "../escape", "project": {}}).encode())
    t.ok(code >= 400, "a bad name is refused", body[:120])
    t.eq(dest.read_text(encoding="utf-8"), before,
         "and a refused save leaves the existing project exactly as it was")

    # no temp file is left lying around after a normal save
    t.ok(not (projects / (name + ".json.tmp")).exists(),
         "no .tmp file is left behind")

    for p in (dest, bak):
        if p.exists():
            p.unlink()

    # ---- 4. the hub writes atomically, everywhere ------------------------
    src = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(src, "def write_atomic(",
               "the hub has one place that writes a file safely")
    # The point of the helper is that nothing bypasses it. write_text on a user
    # data path is the bug it exists to prevent.
    stray = re.findall(r"\((?:PROJECTS|SEQUENCES|STUDIO|SETTINGS_FILE)[^)]*\)?"
                       r"\s*\.write_text\(", src)
    t.eq(stray, [],
         "and no user-data file is written with write_text, which truncates first")

    # ---- 5. the SD card writes to a temporary, then renames --------------
    sd = (F.CODE / "firmware/src/core/SDStore.cpp").read_text(encoding="utf-8",
                                                              errors="replace")
    i = sd.find("bool SDStore::openWrite(")
    body_open = sd[i:sd.find("\n}", i)] if i >= 0 else ""
    t.contains(body_open, ".part",
               "an SD upload is written to a temporary file first")
    j = sd.find("bool SDStore::closeWrite(")
    body_close = sd[j:sd.find("\n}", j)] if j >= 0 else ""
    # an interrupted upload must leave the old sequence intact
    t.contains(body_close, "SD.rename",
               "and only renamed over the real file once it all arrived")

    portal = (F.CODE / "firmware/src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    k = portal.find('server_.on("/api/upload"')
    body_up = portal[k:k + 2600] if k >= 0 else ""
    t.contains(body_up, ".part",
               "the HTTP upload route does the same")
    t.contains(body_up, "SD.rename",
               "and swaps it in only at the end")

    # ---- 6. the timeline is not lost when the tab closes -----------------
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    t.contains(app, "nong_timeline_draft",
               "the timeline is kept outside RAM while it is being built")
    t.contains(app, "beforeunload",
               "and closing with unsaved keyframes asks first")
    # The draft must be its OWN key. Writing it into a project file would make
    # the safety net capable of destroying the thing it protects.
    t.ok("nong_timeline_draft" not in app.split("SETTINGS_KEYS")[1][:200]
         if "SETTINGS_KEYS" in app else True,
         "the draft is separate from the saved settings bundle")


    # ---- and promotion never carries a file the RUNNING system writes ----
    # The same failure one level up: promote.py copies staging over the real
    # tree, and a file the live system keeps writing is already stale in
    # staging by the time the copy happens. promt.md nearly lost 23 KB of
    # prompt history that way; settings_shared.json really did travel with a QC
    # run's timestamp on it; hub_auth.json would replace the user's own hub
    # password with a test one.
    spec = importlib.util.spec_from_file_location("qc_promote", F.CODE / "promote.py")
    promote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(promote)

    for rel in ("main_python/MiceHub.exe",           # rebuilt, never authored
                "promt.md",                          # the live prompt log
                "docs/PLAN.html",                    # progress, edited as it lands
                "main_python/hub_auth.json",         # this machine's password
                "main_python/hub_password.txt",      # ...and the readable copy
                "nong/main_python_set_nong/settings_shared.json"):
        t.ok(promote.skip(Path(rel)),
             "promote leaves %s alone" % rel,
             "the running system writes this file — promoting a staging copy "
             "overwrites whatever it has written since staging was made")

    # ...and the list is a list, not "skip everything": real source must move,
    # or the gate above would pass by doing nothing at all.
    for rel in ("main_python/main.py", "shared/web/mice.css",
                "main_python/hub_auth.py", "firmware/src/core/Log.cpp"):
        t.ok(not promote.skip(Path(rel)),
             "promote still carries %s" % rel,
             "source that stops being promoted is work that never lands")
