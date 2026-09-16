"""The app is ONE file: nothing has to travel beside MiceHub.exe.

Asked on 2026-08-19 about the second PC at a venue: *if other pc don't have
python html css node or other thing what should we do*. It should need none of
them. The exe already carried the code, but every page, stylesheet and registry
still had to sit in the right folder next to it, so a copied exe started and
then served nothing.

The trap this check exists for is the opposite mistake. A one-file build unpacks
into a TEMPORARY folder that is deleted when the app exits, so bundling a
writable path there would silently throw away saved work - a Studio project, a
password, the list of known hubs - every time the hub closed. So the split is
the thing being tested:

  * read-only files are found through `asset()`, which prefers a real file next
    to the exe and falls back to the bundled copy;
  * everything written at runtime hangs off `HERE` or `DATA`, which are always
    real folders on disk.
"""
import tempfile
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "the app is one file, and nothing writable lives inside it"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    if not t.ok(hasattr(main, "asset"), "the hub can find its shipped files"):
        return

    # ---- next to the exe wins over the bundled copy -----------------
    box = Path(tempfile.mkdtemp(prefix="qc_onefile_"))
    beside, bundled = box / "beside", box / "bundled"
    for d in (beside / "shared" / "web", bundled / "shared" / "web"):
        d.mkdir(parents=True)
    (beside / "shared" / "web" / "mice.css").write_text("beside", encoding="utf-8")
    (bundled / "shared" / "web" / "mice.css").write_text("bundled", encoding="utf-8")
    (bundled / "shared" / "web" / "only.css").write_text("bundled", encoding="utf-8")

    was = main._ROOTS
    main._ROOTS = [beside, bundled]
    try:
        got = main.asset("shared", "web", "mice.css")
        t.eq(got.read_text(encoding="utf-8"), "beside",
             "a file placed next to the exe is used instead of the bundled one")
        got = main.asset("shared", "web", "only.css")
        t.eq(got.read_text(encoding="utf-8"), "bundled",
             "and the bundled copy is used when there is nothing beside it")
        missing = main.asset("shared", "web", "nope.css")
        t.ok(str(missing).endswith("nope.css"),
             "a file that is in neither still names a real path",
             "returning None here turns a missing page into a crash three "
             "frames away from the cause")
    finally:
        main._ROOTS = was
        import shutil
        shutil.rmtree(box, ignore_errors=True)

    # ---- writable things never come out of the bundle ---------------
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    for name in ("AUTH_STORE", "KNOWN_HUBS"):
        i = src.find(name + " = ")
        line = src[i:src.find("\n", i + 40)]
        t.ok("asset(" not in line,
             "%s is a real file on disk, not a bundled one" % name,
             "a one-file build unpacks to a temporary folder that is deleted "
             "on exit - a password or a hub list written there is lost every "
             "time the app closes")
    for name in ("STUDIO = ", "FIRMWARE_DIR = "):
        i = src.find(name)
        line = src[i:src.find("\n", i)]
        t.contains(line, "DATA",
                   "%sis a folder the hub can write to" % name)

    # ---- and the build really carries what the hub serves -----------
    spec = F.CODE / "MiceHub.spec"
    if not t.ok(spec.exists(), "there is a build recipe for the one-file app",
                "expected %s" % spec):
        return
    # The LIST, not the file: an early version of this check searched the
    # whole spec and failed on the word "projects" appearing in the comment
    # that explains why projects are not bundled.
    import ast  # noqa: PLC0415
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    listed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(x, "id", "") == "datas" for x in node.targets):
            listed = [n.value for n in ast.walk(node.value)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    if not t.ok(listed, "the build recipe lists files to carry",
                "no datas= assignment found; a one-file build with an empty "
                "datas is exactly the bug this task fixed"):
        return

    # ---- THE DOCUMENTED COMMAND MUST USE THE SPEC ---------------------
    # CLAUDE.md told a session to run PyInstaller against main.py directly.
    # That does two kinds of damage, both seen on 2026-08-21: the exe ships
    # with no web pages and no registries (it starts, says "registries
    # unavailable: No module named 'registry'" and answers 500 on every page),
    # and PyInstaller REWRITES MiceHub.spec with a generated stub, destroying
    # the curated one — so the next build from "the spec" is broken too. The
    # rule cost three builds and a `git checkout -- MiceHub.spec`.
    rules = (F.CODE / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    builds = [ln for ln in rules.splitlines() if "PyInstaller" in ln]
    t.ok(builds, "the project rules say how to build the app")
    bad = [ln for ln in builds if "main_python/main.py" in ln]
    t.ok(not bad,
         "and never by naming the script instead of the spec",
         "this line rebuilds a broken exe AND overwrites MiceHub.spec: %s"
         % (bad[0].strip()[:120] if bad else ""))
    t.ok(any("MiceHub.spec" in ln for ln in builds),
         "the documented command runs MiceHub.spec")
    joined = " ".join(listed).replace("\\", "/")
    for folder in ("main_python/web", "shared/web",
                   "nong/main_python_set_nong/web", "firmware/config"):
        t.contains(joined, folder, "the build bundles %s" % folder)

    # EVERY data file the registry reads, asked of the registry itself rather
    # than listed here. The first build shipped without apps/ and the exe ran
    # perfectly while serving an empty app list - nothing failed, the screen
    # was just blank. A list written out by hand would have made the same
    # mistake again the next time someone adds a registry.
    import registry  # noqa: PLC0415
    roots = [getattr(registry, n, None) for n in
             ("APPS_DIR", "SERVOS_FILE", "COMMANDS_FILE", "MODULES_FILE")]
    for r in [x for x in roots if x]:
        try:
            rel = Path(r).resolve().relative_to(F.CODE.resolve()).as_posix()
        except ValueError:
            continue                    # outside the tree; nothing to bundle
        t.ok(any(rel.startswith(x) or x.startswith(rel) for x in
                 [Path(y).as_posix() for y in listed]),
             "the build carries %s, which the registry reads" % rel,
             "the exe will start and quietly serve an empty list without it")
    # EVERY file main.py asks asset() for, read out of main.py itself. Frozen,
    # asset() looks beside the exe and inside the bundle - and nowhere else -
    # so a shipped file that is in neither makes the hub behave as though the
    # file said nothing. config/page_access.json was exactly that on
    # 2026-09-09: the packaged hub would have gated no card at all and printed
    # nothing about it. A hand-kept list would have missed the next one too.
    mainsrc = (F.CODE / "main_python" / "main.py").read_text(encoding="utf-8")
    wanted = set()
    for call in ast.walk(ast.parse(mainsrc)):
        if not (isinstance(call, ast.Call)
                and getattr(call.func, "id", "") == "asset"):
            continue
        parts = [a.value for a in call.args
                 if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if len(parts) == len(call.args) and parts:
            wanted.add("/".join(parts))

    # The DESTINATIONS, not every string in the block. Reading all of them was
    # this check's own first version and it passed while the bundle was wrong:
    # `str(ROOT / "firmware" / "config")` contributes the bare word `config`,
    # which happily "covered" config/page_access.json with nothing carrying it.
    dests = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(x, "id", "") == "datas" for x in node.targets):
            for tup in ast.walk(node.value):
                if (isinstance(tup, ast.Tuple) and len(tup.elts) == 2
                        and isinstance(tup.elts[1], ast.Constant)
                        and isinstance(tup.elts[1].value, str)):
                    dests.append(Path(tup.elts[1].value).as_posix())

    def carried(rel):
        """Covered only on whole path SEGMENTS.

        A string prefix would say main_python/web covers main_python/web_ox,
        which is a different folder entirely. `.` is one file at the bundle
        root, so it covers nothing.
        """
        parts = rel.split("/")
        for d in dests:
            if d == ".":
                continue
            dp = d.split("/")
            if parts[:len(dp)] == dp:
                return True
        return False

    # Two the code deliberately tolerates being absent, said so in main.py
    # itself: *both folders may be absent while the designs are built*
    # (main_python/main.py:100-101). They are the A23-1 comparison pages,
    # mounted additively; the pages people actually use are untouched.
    OPTIONAL = {"main_python/web_gemini", "main_python/web_ox"}
    for rel in sorted(wanted - OPTIONAL):
        t.ok(carried(rel),
             "the build carries %s, which main.py asks asset() for" % rel,
             "frozen, asset() searches beside the exe and inside the bundle "
             "only - a file in neither leaves the hub acting as if it were "
             "empty, with nothing on any screen saying so. Carried: %s"
             % dests)

    for never in ("projects", "sequences", "models", "hub_auth"):
        t.ok(never not in joined,
             "and never bundles %s, which the hub writes" % never,
             "bundling it would put saved work in a folder that is deleted "
             "when the app exits")

    # ---- an exe built inside the code tree serves pages LIVE ----------
    # User 2026-09-17: make every change fast. code/dist/MiceHub.exe reads
    # pages from code/ first, so a page edit needs a refresh, not a rebuild;
    # a venue install (no code tree beside it) keeps the bundled copies.
    main_src = (F.CODE / "main_python" / "main.py").read_text(encoding="utf-8")
    t.ok('_ROOTS.insert(1, HERE.parent)' in main_src
         and '(HERE.parent / "main_python" / "main.py").is_file()' in main_src,
         "an exe inside the code tree reads pages live from it",
         "without it every page change costs an exe rebuild and a hub restart")
