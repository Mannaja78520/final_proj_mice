"""The hub says when its own exe is older than the source beside it.

Measured 2026-08-21: the hub answering on 8642 was yesterday's MiceHub.exe. It
was missing pairing, the chatty-board fix, the bus group carry and the OTA
login, it answered every request happily, and the only reason anyone noticed
was that its password did not match. Half an hour went into a bug that had been
fixed in source the running program had never seen.

So the build carries a receipt - a sha for every source file that went into it
- and a running hub compares that against the tree beside it. What this check
holds is the FOUR ways that can go wrong:

  * **mtime is not the signal.** A git checkout rewrites every mtime, so a
    tree that is byte-identical to the build would cry stale every time
    somebody switched branch. Only the bytes count;
  * **runtime files are not source.** The password hash, the known hubs and
    Studio's saved projects all live beside the code and change while the hub
    runs. Counting them would make every build stale within a minute of
    starting, which is a warning nobody would read twice;
  * **no source tree, no claim.** At a venue the exe travels alone. There is
    nothing to compare against, so it says nothing rather than guessing;
  * **and the stamp must cover what the build actually contains.** A folder
    bundled by MiceHub.spec but missing from AREAS is a folder that can change
    without anyone being told - the silent half of the original bug.
"""
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import fake_serial
import qc as F

AREA = "hub"
TITLE = "the hub says when its exe is older than the source"


def _tree(root):
    """A miniature of the real layout: source, scratch and runtime files."""
    (root / "main_python" / "web").mkdir(parents=True)
    (root / "shared" / "web").mkdir(parents=True)
    (root / "MiceHub.spec").write_bytes(b"# marker\n")
    (root / "main_python" / "main.py").write_bytes(b"print(1)\n")
    (root / "main_python" / "web" / "hub.html").write_bytes(b"<p>hub</p>\n")
    (root / "shared" / "web" / "mice.css").write_bytes(b".a{}\n")
    # Written by the hub while it runs - never source.
    (root / "main_python" / "hub_auth.json").write_bytes(b'{"hash": "x"}')
    (root / "main_python" / "known_hubs.json").write_bytes(b"[]")
    # QC's own driver page, which appears inside a web folder mid-run.
    (root / "main_python" / "web" / "_qcraw_1.html").write_bytes(b"<p>qc</p>")


def run(t):
    sys.path.insert(0, str(F.HUB))
    import build_stamp as B

    tmp = Path(tempfile.mkdtemp(prefix="mice_stamp_"))
    was_meipass = getattr(sys, "_MEIPASS", None)
    real_root = B.source_root
    try:
        src = tmp / "code"
        src.mkdir()
        _tree(src)
        bundle = tmp / "bundle"
        bundle.mkdir()

        # ---- what counts as source --------------------------------------
        files = B.source_files(src)
        for want in ("main_python/main.py", "main_python/web/hub.html",
                     "shared/web/mice.css"):
            t.ok(want in files, "%s counts as source" % want,
                 "the stamp covers %r" % sorted(files))
        t.ok("main_python/hub_auth.json" not in files,
             "the password store is NOT counted as source",
             "it is written while the hub runs, so counting it would make "
             "every build report itself stale a minute after starting")
        t.ok("main_python/known_hubs.json" not in files,
             "and neither is the list of hubs it has seen")
        t.ok("main_python/web/_qcraw_1.html" not in files,
             "and neither is a QC driver page sitting in a web folder",
             "QC writes one into the studio and hub web folders while a "
             "browser check runs; counting it would flap the stamp several "
             "times a minute")

        # ---- the receipt, and a tree that matches it ---------------------
        stamp_path = B.write(src, bundle)
        t.ok(stamp_path.is_file(), "the build writes a receipt")
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
        t.ok(stamp.get("files") and stamp.get("signature") and stamp.get("when"),
             "which names every file, a signature and when it was built",
             "got keys %r" % sorted(stamp))

        sys._MEIPASS = str(bundle)
        B.source_root = lambda start=None: src
        st = B.state(ttl=0)
        t.eq(st["stale"], False, "a fresh build is not stale")
        t.eq(B.why(st), "", "and says nothing at all about itself")

        # ---- the same bytes, a new date ----------------------------------
        # A git checkout rewrites every mtime. If that counted, switching
        # branch would announce a stale build on a tree that is identical to
        # the one the exe was made from.
        main_py = src / "main_python" / "main.py"
        os.utime(main_py, (0, 0))
        st = B.state(ttl=0)
        t.eq(st["stale"], False,
             "an old date on identical bytes is NOT stale")

        # ---- one changed byte --------------------------------------------
        main_py.write_bytes(b"print(2)\n")
        st = B.state(ttl=0)
        t.eq(st["stale"], True, "one changed source file makes it stale")
        t.eq(st["changed"], ["main_python/main.py"],
             "and it names the file that changed")
        t.contains(B.why(st), "main_python/main.py",
                   "the sentence says which file, not just that something did")
        t.contains(B.why(st), stamp["when"][:10],
                   "and when the running build was made")

        # ---- a new file counts too -----------------------------------------
        (src / "main_python" / "hub_pair.py").write_bytes(b"x = 1\n")
        st = B.state(ttl=0)
        t.eq(st["count"], 2, "a file that did not exist at build time counts")

        # ---- the exe travelling alone --------------------------------------
        B.source_root = lambda start=None: None
        st = B.state(ttl=0)
        t.eq(st["stale"], False,
             "with no source beside it, the hub makes no claim")
        t.ok(st["built"], "though it still says when it was built",
             "the build date is the first question after any strange report, "
             "and it is knowable even with nothing to compare against")

        # ---- and running from source is never stale ------------------------
        del sys._MEIPASS
        B.source_root = real_root
        st = B.state(ttl=0)
        t.eq(st["stale"], False, "main.py run from source is never stale",
             )
    finally:
        B.source_root = real_root
        if was_meipass is None:
            if hasattr(sys, "_MEIPASS"):
                del sys._MEIPASS
        else:
            sys._MEIPASS = was_meipass
        B._cache[0], B._cache[1] = 0.0, None
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- the stamp covers what the build really bundles ------------------
    spec = (F.CODE / "MiceHub.spec").read_text(encoding="utf-8")
    t.contains(spec, "build_stamp.write(",
               "the spec writes the receipt at build time")
    covered = ["/".join([a] + ([p] if "*" not in p else []))
               for a, p in B.AREAS]
    for m in re.finditer(r'ROOT\s*/\s*((?:"[^"]+"\s*/\s*)*"[^"]+")', spec):
        rel = "/".join(re.findall(r'"([^"]+)"', m.group(1)))
        if rel.startswith("build"):
            continue                      # the receipt itself, written by us
        t.ok(any(rel.startswith(c) or c.startswith(rel) for c in covered),
             "the stamp covers %s, which the spec bundles" % rel,
             "a folder that is built in but not stamped can change without "
             "anyone being told, which is the silent half of the original bug")

    # ---- the hub reports it, on the endpoint every tab already polls -----
    fake_serial.reset()
    base, _m = F.start_hub()
    code, body = F.get(base + "/api/version")
    t.eq(code, 200, "the version endpoint answers")
    d = json.loads(body)
    for k in ("stale", "staleWhy", "rebuild", "built"):
        t.ok(k in d, "it reports %s" % k)
    t.eq(d["rebuild"], B.REBUILD, "and names the one way to rebuild")
    code, body = F.get(base + "/api/selfupdate")
    t.ok("stale" in json.loads(body),
         "the update card is told as well",
         "somebody looking for a newer build is exactly the person who needs "
         "to know the one they are running was never rebuilt")

    # ---- and the page says it plainly ------------------------------------
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    t.contains(hub, 'id="staleExe"', "the page has a banner for it")
    t.contains(hub, "banner warn", "coloured as a caution, not an error")
    # The CALL, not the definition: `function paintStale(r){` also contains the
    # name, and matching that made deleting the call pass this check.
    t.contains(hub, "function paintStale(", "the page knows how to paint it")
    i_paint = hub.find("paintStale(r);")
    i_base = hub.find("myVer = r.version; return;")
    t.ok(0 < i_paint < i_base,
         "painted before the version baseline returns",
         "a stale exe is true on the FIRST answer; painting it after the "
         "baseline `return` means the banner only appears if the web files "
         "change as well, which is the one case that already had a banner")
    banner = hub[hub.find('id="staleExe"'):]
    banner = banner[:banner.find("</div>")]
    t.ok("dismissVer" not in banner and "Not now" not in banner,
         "and it cannot be dismissed",
         "reloading fixes an old page; nothing the browser can do fixes an "
         "old program, so a dismiss button would only hide it until the next "
         "person is confused by it")

    # ---- one rebuild command, everywhere -------------------------------
    # promote.py and make_app_branch.py each printed a rebuild line of their
    # OWN, and both were the bare --onefile form: it builds a hub with no web
    # pages and no registries, and PyInstaller rewrites the curated
    # MiceHub.spec with a generated stub while doing it (2026-08-21, the spec
    # had to be restored from git). A command a person is TOLD to run is part
    # of the product, so it is held to the same one-source rule as the code.
    for rel in ("promote.py", "tools/make_app_branch.py"):
        src = (F.CODE / rel).read_text(encoding="utf-8", errors="replace")
        hint = [l.strip() for l in src.splitlines()
                if "PyInstaller" in l and "--onefile" in l]
        t.eq(hint, [], "%s does not hand out a second rebuild command" % rel)
        t.contains(src, "build_stamp", "%s reads the one there is" % rel)
