"""Every file belongs to exactly one subsystem, and each header page is current.

Asked 2026-09-21 (A26-76): *make everything to sub-system ... when we change we
have point file to that file in md ... like c or c++ header of each system*.
docs/systems.json is the map; docs/systems/<id>.md is each system's header,
generated below a marker from the map (files, depends, used by, checks).

A map that drifts is worse than none - an AI trusts the header and edits the
wrong place. So this fails when:
  * a file is owned by nobody (a new file must be given a system);
  * two systems claim a file equally (ownership must be one answer);
  * a system depends on one that does not exist;
  * a header page is missing or its generated part is stale.
Run `python tools/systems.py build` after editing the map.
"""
import importlib.util
import tempfile
from pathlib import Path
import shutil

import qc as F

AREA = "tooling"
TITLE = "every file has one subsystem, and every header is current"


def _systems(code):
    spec = importlib.util.spec_from_file_location("systems", code / "tools" / "systems.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    code = F.CODE
    s = _systems(code)
    bad = s.verify(code)
    t.ok(not bad, "the system map is sound", "; ".join(bad[:8]))

    # ---- and a scoped gate always runs this check ------------------------
    import scope                                   # qc/lib, on the path in QC
    got = scope.decide(code, ["main_python/" + "q" + "r.py"])
    t.ok(got[0] == "checks" and "check_systems" in got[1],
         "a one-system gate still checks the map",
         "decide() gave %s" % (got[:2],))

    # ---- the closer pattern wins, like a closer #include -----------------
    reg = {"systems": [{"id": "outer", "files": ["x/"]},
                       {"id": "inner", "files": ["x/y/"]},
                       {"id": "glob", "files": ["x/y/*.md"]}]}
    t.eq(s.owner("x/y/z.py", reg), "inner", "a deeper folder beats its parent")
    t.eq(s.owner("x/q.py", reg), "outer", "and the parent keeps the rest")
    t.eq(s.owner("x/y/a.md", reg), "glob", "a named pattern beats a folder")
    t.eq(s.owner("x/y/sub/a.md", reg), "inner", "and * never crosses a folder")

    # ---- the verifier really catches what it claims (a scratch copy) -----
    tmp = Path(tempfile.mkdtemp(prefix="mice_sys_qc_"))
    try:
        for rel in ("docs/systems.json", "tools/systems.py"):
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(code / rel, tmp / rel)
        (tmp / "qc" / "checks").mkdir(parents=True)
        # paths built in pieces, so this check is not itself listed as testing them
        demo = "main_python/" + "md" + "ns.py"
        (tmp / "qc" / "checks" / "check_demo.py").write_text("# names " + demo + "\n")
        (tmp / "main_python").mkdir()
        (tmp / demo).write_text("# owned by hub-net\n")
        s.build(tmp)
        t.ok(not [b for b in s.verify(tmp) if "nobody owns" in b],
             "a scratch tree built from the map starts sound")
        (tmp / "brand_new_thing").mkdir()
        (tmp / "brand_new_thing" / "x.py").write_text("")
        t.ok(any("nobody owns brand_new_thing/x.py" in b for b in s.verify(tmp)),
             "a new file with no system is reported")
        page = tmp / "docs" / "systems" / "hub-net.md"
        page.write_text(page.read_text(encoding="utf-8") + "\n- `stale.py`\n",
                        encoding="utf-8")
        t.ok(any("hub-net.md is out of date" in b for b in s.verify(tmp)),
             "a header edited below the marker is reported as stale")
        t.eq(s.owner(demo, s.load(tmp)), "hub-net",
             "a file goes to the system that names it most specifically")

        # files the running system writes (promote.py SKIP_FILES) are not in
        # the map: a staging tree never has them, so listing them made every
        # header differ between main and staging (2026-09-21, docs.md)
        (tmp / "promote.py").write_text('SKIP_FILES = {"LIVE.html"}\n')
        (tmp / "docs" / "LIVE.html").write_text("x")
        t.ok("docs/LIVE.html" not in s.files(tmp, s.load(tmp)),
             "live files named in promote.py SKIP_FILES are left out of the map")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
