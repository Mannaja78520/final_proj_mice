"""Published worktree snapshots are stale; source probes must restore exact bytes."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import qc as F
from checks import check_packing_list as packing
from checks import check_themes as themes
from checks import check_tools_list as tools_list

AREA = "tools"
TITLE = "QC uses the live plan and restores LF/CRLF sources even after exceptions"


class ProbeAbort(RuntimeError):
    pass


def run(t):
    with tempfile.TemporaryDirectory(prefix="mice_qc_integrity_") as folder:
        root = Path(folder)
        stage = root / ".staging-published"
        for base in (root, stage):
            (base / "docs").mkdir(parents=True)
            (base / "tools").mkdir()
            (base / "tools/plan.py").write_bytes((F.CODE / "tools/plan.py").read_bytes())
            (base / "docs/PLAN.html").write_text('<script src="plan_state.js"></script>', encoding="utf-8")
            state = "doing" if base == stage else "done"
            raw = "STATE\nA47-19: %s 2026-10-25 hw=robot — fixture\nEND" % state
            (base / "docs/plan_state.js").write_text("window.PLAN_STATE=" + json.dumps({"raw": raw}) + ";", encoding="utf-8")
        with patch.object(F, "CODE", stage), patch.dict(os.environ, {"MICE_PLAN": ""}):
            t.eq(packing.docs_dir(), root / "docs", "a complete published worktree copy cannot shadow the live plan")
            t.eq(packing.state_lines()["A47-19"]["status"], "done", "packing reads canonical state, not stale published JS")
            (stage / "docs/PLAN.html").write_text("The plan is not here", encoding="utf-8")
            t.eq(packing.docs_dir(), root / "docs", "a redirect signpost also resolves to the canonical plan")
        with patch.object(F, "CODE", root), patch.dict(os.environ, {"MICE_PLAN": ""}):
            t.eq(packing.docs_dir(), root / "docs", "the real checkout resolves its own plan")
        override = root / "explicit/PLAN.html"
        with patch.object(F, "CODE", stage), patch.dict(os.environ, {"MICE_PLAN": str(override)}):
            t.eq(packing.docs_dir(), override.parent, "explicit test-plan override uses the writer's resolver")

        for ending in ("\n", "\r\n"):
            for abort in (False, True):
                for kind in ("manifest", "theme"):
                    target = root / (kind + ".txt")
                    text = '{\n"name":"ทดสอบ"\n}\n' if kind == "manifest" else ':root{\n--name:"ทดสอบ";\n}\n'
                    original = text.replace("\n", ending).encode("utf-8")
                    target.write_bytes(original)
                    context = tools_list.broken_manifest(target) if kind == "manifest" else themes.temporary_theme(target, ":root{--probe:1}\n")
                    raised = False
                    try:
                        with context:
                            t.ok(target.read_bytes() != original, "%s probe actually changes its fixture" % kind)
                            if abort:
                                raise ProbeAbort()
                    except ProbeAbort:
                        raised = True
                    t.eq(raised, abort, "%s probe exercised the requested exit path" % kind)
                    t.eq(target.read_bytes(), original, "%s restores exact UTF-8/%s bytes after %s" %
                         (kind, "CRLF" if ending == "\r\n" else "LF", "exception" if abort else "success"))

        spec = importlib.util.spec_from_file_location("_sabotage_bytes", F.CODE / "tools/sabotage.py")
        sabotage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sabotage)
        target, specs = root / "source.py", root / "patch.json"
        specs.write_text(json.dumps([{"file": "source.py", "find": "ORIGINAL", "replace": "BROKEN"}]), encoding="utf-8")
        for ending in ("\n", "\r\n"):
            for abort in (False, True):
                original = ('ORIGINAL = "ทดสอบ"' + ending).encode("utf-8")
                target.write_bytes(original)

                def fake_check(_name):
                    broken = b"BROKEN" in target.read_bytes()
                    if broken and abort:
                        raise ProbeAbort()
                    return not broken, ["intentional fixture failure"] if broken else [], ""

                raised, result = False, None
                try:
                    with patch.object(sabotage, "ROOT", root), patch.object(sabotage, "run_check", fake_check), redirect_stdout(io.StringIO()):
                        result = sabotage.main(["--check", "fixture", "--spec", str(specs)])
                except ProbeAbort:
                    raised = True
                t.ok(raised if abort else result == 0, "real sabotage main exercises caught-fault or exception path")
                t.eq(target.read_bytes(), original, "real sabotage main restores exact original LF/CRLF bytes")
