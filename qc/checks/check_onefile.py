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
    for never in ("projects", "sequences", "models", "hub_auth"):
        t.ok(never not in joined,
             "and never bundles %s, which the hub writes" % never,
             "bundling it would put saved work in a folder that is deleted "
             "when the app exits")
