"""Which checks a change needs - so a small change gets a small gate.

Asked 2026-09-16: *if we change some thing we can gate and qc about that ...
full check when edit the whole system or more than 1 system*.

The rules are DATA in qc/data/scope.json. decide() answers one of:
  ("full",   why)            core file, or more than maxSystems systems
  ("checks", [stems], why)   checks whose source names a changed file
  ("quick",  why)            a change no check names: run --quick as the floor

A scoped gate is a trade the user chose: faster, and it can miss a break in a
system the change did not name. `promote.py --full` is always there.
"""
import filecmp
import os
import re
from pathlib import Path

SKIP_DIRS = {".git", ".pio", "__pycache__", "node_modules", ".vscode", ".claude",
             "dist", "build", "patches", "patches_code", "generated", "tts_cache",
             "reports", "scratch"}
SKIP_EXT = {".pyc", ".pyo", ".tmp", ".exe", ".bin", ".elf", ".log", ".bak"}


CODE_EXT = {".py", ".js", ".html", ".css", ".cpp", ".h", ".ino"}


def _system_checks(code, paths, checks_dir=None):
    """Checks that docs/systems.json ties to the systems these paths belong to."""
    import sys
    if not (Path(code) / "docs" / "systems.json").is_file():
        return []                         # a tree with no map (check_scope's fakes)
    tools = str(Path(code) / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import systems
    reg = systems.load(code)
    out = []
    for sid in sorted({systems.owner(p, reg) for p in paths} - {None}):
        spec = next(s for s in reg["systems"] if s["id"] == sid)
        if spec.get("names") or spec.get("checks"):
            out += systems.checks_for(sid, code, reg)
    if checks_dir:                        # a test pointing at its own checks
        have = {f.stem for f in Path(checks_dir).glob("check_*.py")}
        out = [c for c in out if c in have]
    return out


def rules(code):
    import json
    raw = (Path(code) / "qc" / "data" / "scope.json").read_text(encoding="utf-8")
    # JSONC: drop // comments that are not inside a string
    raw = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*', lambda m: m.group(1) or "", raw)
    return json.loads(raw)


def _files(root):
    for parent, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".staging")]
        for n in names:
            f = Path(parent) / n
            if f.suffix not in SKIP_EXT:
                yield f.relative_to(root).as_posix()


def changed(work, main):
    """Paths that differ between a working tree and the tree it lands in."""
    work, main = Path(work), Path(main)
    out = []
    for rel in _files(work):
        dst = main / rel
        if not dst.is_file() or not filecmp.cmp(work / rel, dst, shallow=False):
            out.append(rel)
    return sorted(out)


def _under(rel, pats):
    return any(rel == p or (p.endswith("/") and rel.startswith(p)) for p in pats)


def system_of(rel, depth):
    parts = rel.split("/")
    n = depth.get(parts[0], 1)
    return "/".join(parts[:min(n, len(parts) - 1)] or parts[:1])


def decide(code, paths, checks_dir=None):
    r = rules(code)
    paths = [p for p in paths if not _under(p, r.get("ignore") or [])]
    if not paths:
        return ("quick", "only notes and the plan changed")
    core = [p for p in paths if _under(p, r.get("fullWhen") or [])]
    if core:
        return ("full", "a shared core file changed: %s" % ", ".join(core[:3]))
    # A check belongs to what it tests, so it is not a system of its own.
    systems = sorted({system_of(p, r.get("systemDepth") or {}) for p in paths
                      if not p.startswith("qc/checks/")}) or ["qc/checks"]
    if len(systems) > int(r.get("maxSystems") or 1):
        return ("full", "%d systems changed: %s" % (len(systems), ", ".join(systems)))

    generic = {g.lower() for g in r.get("genericNames") or []}
    needles = set()
    for p in paths:
        path = Path(p)
        stem = path.stem.lower()
        if stem.startswith("check_"):
            needles.add("#self:" + stem)
        elif stem in generic or len(stem) < 4:
            # its folder: apps/faces, not every index.html in the product
            needles.add(path.parent.as_posix().lower())
        else:
            needles.add(stem)

    picked = []
    for f in sorted(Path(checks_dir or Path(code) / "qc" / "checks").glob("check_*.py")):
        if "#self:" + f.stem in needles:
            picked.append(f.stem)
            continue
        if f.stem == "check_scope":
            continue                 # names every example path; not about them
        text = f.read_text(encoding="utf-8", errors="replace").lower()
        if any(n in text for n in needles if not n.startswith("#self:")):
            picked.append(f.stem)
    # ...plus the checks the file's system names in docs/systems.json (A26-93):
    # a check that drives /api/flash over HTTP never names hub_flash.py.
    for stem in _system_checks(code, paths, checks_dir):
        if stem not in picked:
            picked.append(stem)
    if not picked:
        code_files = [p for p in paths if Path(p).suffix.lower() in CODE_EXT]
        if code_files:
            # Code that no check names is code nothing here would test: the
            # quick floor would land it unread (Codex review 2026-09-22).
            return ("full", "no check names %s" % ", ".join(code_files[:3]))
        return ("quick", "no check names %s" % ", ".join(sorted(paths)[:3]))
    # checks every scoped gate runs whatever changed: the system map must not
    # drift just because the change did not name it (Codex review 2026-09-21)
    for stem in r.get("alwaysRun") or []:
        if stem not in picked and (Path(checks_dir or Path(code) / "qc" / "checks")
                                   / (stem + ".py")).is_file():
            picked.append(stem)
    return ("checks", picked, "%s changed" % systems[0])
