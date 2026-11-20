"""The face app's factory login ships in git; a customer's changed one never does.

User 2026-11-20: the Reconize admin login is the app's own factory default, so it
is the tracked default (`main_python/faces_login.default.json`). A customer who
changes it writes `main_python/faces_login.json`, which .gitignore keeps off the
cloud and which wins. With neither, the watcher says what to write (QC override).
"""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import qc as F


def run(t):
    default = F.CODE / "main_python" / "faces_login.default.json"
    t.ok(default.is_file(), "the factory login file is in the repo", str(default))
    t.ok(json.loads(default.read_text(encoding="utf-8")).get("reconize", {}).get("username"),
         "and names the app's own admin", "")
    spec = importlib.util.spec_from_file_location("_fl_default", F.CODE / "apps" / "faces" / "service.py")
    svc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(svc)
    os.environ.pop("MICE_FACES_LOGIN", None)
    box = Path(tempfile.mkdtemp(prefix="qc_faces_default_"))
    (box / "main_python").mkdir()
    (box / "main_python" / "faces_login.default.json").write_text(
        json.dumps({"_qc": {"username": "factory", "password": "f"}}), encoding="utf-8")
    old = svc.CODE
    svc.CODE = box
    try:
        state = svc.State("_qc")
        who, why = state.credentials()
        t.ok(who and who["username"] == "factory", "no local file: the factory login is used", (who, why))
        (box / "main_python" / "faces_login.json").write_text(
            json.dumps({"_qc": {"username": "mine", "password": "m"}}), encoding="utf-8")
        who, why = state.credentials()
        t.ok(who and who["username"] == "mine", "a local changed login wins over the factory one", (who, why))
    finally:
        svc.CODE = old
