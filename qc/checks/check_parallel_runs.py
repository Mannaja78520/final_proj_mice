"""Two QC runs can happen at once without ruining each other.

Every change queued behind one 12-minute suite, so the user asked for more than
one working copy. Two staging trees are two PROCESSES, so the shared-state
collision that bit us inside one process does not apply — but three things did,
and all three fail silently rather than loudly, which is the dangerous kind:

  * browser.TAG was a constant and kill() matches on it, so one run killed the
    other run's browser in the middle of a measurement. That looks exactly like
    a flaky check;
  * qc._hub_port started at 8700 in both runs, so two trees fought over ports —
    or worse, one tree's hub answered the other tree's request, which does not
    fail at all, it just tests the wrong tree;
  * promote.py hardcoded MAIN/.staging, so a second tree could not be promoted.

This asserts each run takes an identity from its own process, and that the
identity really differs between processes — checked by starting a second
Python and comparing, not by reading the source and hoping.
"""
import subprocess
import sys

import qc as F

AREA = "qc"
TITLE = "two working copies can be verified at the same time"
SLOW = False

# Ask another process what IT computed. Reading the source cannot tell you
# whether two processes actually differ.
PROBE = (
    "import sys, os; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s');"
    "import browser, qc;"
    "print(browser.TAG); print(qc._hub_port[0]); print(os.getpid())"
)


def _ask_another_process():
    r = subprocess.run(
        [sys.executable, "-c", PROBE % (F.QC / "lib", F.QC)],
        capture_output=True, text=True, timeout=120, cwd=str(F.CODE))
    if r.returncode != 0:
        return None
    parts = (r.stdout or "").strip().splitlines()
    return parts if len(parts) == 3 else None


def run(t):
    import browser

    # ---- this run has its own identity --------------------------------
    t.ok(browser.TAG.startswith("MICEQCBROWSER") and browser.TAG != "MICEQCBROWSER",
         "the browser tag is particular to this run",
         "kill() matches on the tag, so a shared one means one run kills the "
         "other run's browser: %r" % browser.TAG)
    t.ok(F._hub_port[0] != 8700,     # noqa: SLF001 - the value under test
         "and so is the port range it starts hubs on",
         "two runs both starting at 8700 can answer each other's requests, "
         "which does not fail — it tests the wrong tree")

    # ---- and another process really gets a different one --------------
    other = _ask_another_process()
    if not t.ok(other, "a second process could be asked what it computed"):
        return
    tag, port, pid = other[0], other[1], other[2]
    t.ok(tag != browser.TAG,
         "a second run gets a DIFFERENT browser tag",
         "same tag in both (%s) — one run's kill() would take the other's "
         "browser down mid-measurement" % tag)
    t.ok(port != str(F._hub_port[0]),   # noqa: SLF001
         "and a different port range",
         "both runs would start hubs at %s" % port)

    # ---- and no tag is INSIDE another tag -----------------------------
    # kill() matches with `-like '*TAG*'`. A bare pid made the tag of 123 a
    # substring of the tag of 1234, so one worker's kill() took another
    # worker's Edge down mid-page: the page never said "done", the check
    # waited out its ~200 s grace and failed with nothing reported. That is
    # the flake that hit a different browser check in every full gate on
    # 2026-09-22 (A26-94). A pool makes a fresh process per check, so a gate
    # holds hundreds of pids and a prefix pair is near certain.
    for short, long in ((123, 1234), (5, 50), (2468, 24684)):
        t.ok(browser.tag_for(short) not in browser.tag_for(long),
             "the tag of pid %d is not inside the tag of pid %d" % (short, long),
             "kill() would take that other worker's browser down: %r in %r"
             % (browser.tag_for(short), browser.tag_for(long)))

    # ---- an unanswered "are they gone?" is not a yes -------------------
    # _running() answered 0 when the query failed, which reads as "all gone"
    # and let the next page start into a machine still full of browsers.
    import subprocess as _sp
    real = _sp.run
    try:
        for code, out, why in ((1, "", "the query failed"),
                               (0, "", "it answered nothing"),
                               (0, "Access denied", "it answered something else")):
            _sp.run = lambda *a, _c=code, _o=out, **k: _sp.CompletedProcess(
                a[0] if a else [], _c, _o, "boom")
            t.eq(browser._running(), -1,   # noqa: SLF001 - the value under test
                 "'do not know', not 'none left', when %s" % why)
    finally:
        _sp.run = real

    # ---- promote can be pointed at another tree -----------------------
    import importlib.util
    spec = importlib.util.spec_from_file_location("qc_promote", F.CODE / "promote.py")
    pr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pr)
    t.ok(hasattr(pr, "_pick_staging"), "promote.py can be pointed at a tree")
    if hasattr(pr, "_pick_staging"):
        home = F.LAYOUT.staging_home
        flat = F.LAYOUT.flat_home          # an old flat .staging is still the default
        t.eq(pr._pick_staging(None), home if flat else home / "main",
             "the default is .staging/main (or an old flat .staging)")
        t.eq(pr._pick_staging(".staging-ui").name, ".staging-ui",
             "an old second tree can still be named")
        t.eq(pr._pick_staging("ui"), F.REAL / ".staging-ui" if flat else home / "ui",
             "and a new one lives INSIDE .staging, not beside the root (A51-1)")
        t.ok(pr._pick_staging(r"E:/somewhere/else").as_posix().endswith("somewhere/else"),
             "including one outside the repo")

    _promote_topologies(t)


def _promote_topologies(t):
    """Import actual promotion code from private root/copy layouts; never promote."""
    import builtins
    import importlib.util
    from pathlib import Path
    import tempfile
    from unittest import mock

    source = (F.CODE / "promote.py").read_bytes()
    layout = (F.CODE / "tools/layout.py").read_bytes()
    config = (F.CODE / "config/layout.json").read_bytes()
    staging = F.LAYOUT.data["staging"]

    def load(folder, unavailable=False):
        target = folder / "promote.py"
        target.write_bytes(source)
        spec = importlib.util.spec_from_file_location("topology_promote", target)
        module = importlib.util.module_from_spec(spec)
        old_path = sys.path[:]
        real_import = builtins.__import__

        def import_without_layout(name, *args, **kwargs):
            if name == "layout":
                raise ImportError("layout unavailable in this fixture")
            return real_import(name, *args, **kwargs)

        try:
            if unavailable:
                with mock.patch("builtins.__import__", side_effect=import_without_layout):
                    spec.loader.exec_module(module)
            else:
                spec.loader.exec_module(module)
        finally:
            sys.path[:] = old_path
        return module

    def install(folder):
        (folder / "tools").mkdir(parents=True)
        (folder / "config").mkdir()
        (folder / "tools/layout.py").write_bytes(layout)
        (folder / "config/layout.json").write_bytes(config)

    with tempfile.TemporaryDirectory(prefix="qc_promote_layout_") as box:
        cases = (("root", None), ("nested", Path(staging["home"]) / "task"),
                 ("legacy", Path(staging["prefix"] + "-task")),
                 ("flat", Path(staging["home"])))
        for label, relative in cases:
            root = Path(box) / label
            install(root)
            copy = root if relative is None else root / relative
            if copy != root:
                install(copy)
            module = load(copy)
            t.eq(module.MAIN, root, label + ": promotion destination is the real root")
            home = root / staging["home"]
            expected = home if module.LAYOUT.flat_home else home / staging["default"]
            t.eq(module._pick_staging(None), expected, label + ": default copy is rooted once")
            t.eq(module._book("landed", "legacy.json"), root / staging["books"]["landed"],
                 label + ": shared bookkeeping is rooted once")
            override = Path(box) / (label + "-override")
            module.MAIN = override
            t.eq(module._pick_staging("task"), override / staging["home"] / "task",
                 label + ": explicit MAIN override still chooses the test tree")
            t.eq(module._book("landed", "legacy.json"), override / staging["books"]["landed"],
                 label + ": explicit MAIN override also controls bookkeeping")
        bare = Path(box) / "bare"
        bare.mkdir()
        module = load(bare, unavailable=True)
        t.eq(module.LAYOUT, None, "missing layout retains the bare-tool fallback")
        t.eq(module.MAIN, bare, "fallback import keeps its original source directory")
        t.eq(module._pick_staging(None), bare / ".staging", "fallback default remains flat")
        t.eq(module._book("landed", "legacy.json"), bare / "legacy.json",
             "fallback bookkeeping retains its explicit legacy path")
