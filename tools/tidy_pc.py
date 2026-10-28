#!/usr/bin/env python3
"""Rename the repo folder and tidy the folder around it, on the PC (A51-3).

    python tools/tidy_pc.py plan              what would move, what waits for an OK
    python tools/tidy_pc.py apply             do the approved moves + the rename

User 2026-10-27/28: `code` becomes `mice_system`, the friend's Photobooth and
its run data go under photobooth/, and the thesis/hardware leftovers are
listed for an OK. What moves is DATA, config/layout.json "pc": an entry with
an empty "ok" is only listed. Nothing is ever deleted.

Why each step is here (each one broke something once, or would):
  * Windows will not rename a folder that a process has as its working
    folder (the Remote Control session, MiceHub, the RL and YOLO training).
    So apply refuses while one runs, and names it; it also copies itself out
    of the repo before renaming, because its own folder is in the way;
  * git worktrees under .claude/worktrees remember the old path:
    `git worktree repair` after the rename;
  * git-ignored files of this PC (voice settings, logs) and Windows
    shortcuts (Desktop, Start menu, Startup, dist/Apps) may hold the old
    path: rewritten (a .bak beside each file), shortcuts re-pointed;
  * the Remote Control start command names the folder: printed new.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _load(path):
    return json.loads(re.sub(r"(?m)^\s*//.*$", "", Path(path).read_text(encoding="utf-8")))


class PcTidy:
    """The repo's folder and its parent, as config/layout.json "pc" wants them."""

    def __init__(self, repo=HERE, cfg=None):
        self.repo = Path(repo).resolve()
        self.parent = self.repo.parent
        self.cfg = cfg if cfg is not None else _load(self.repo / "config" / "layout.json")["pc"]
        self.say = []

    # ---- what would happen ------------------------------------------------
    def target_root(self):
        r = self.cfg.get("rename") or {}
        if r.get("ok") and self.repo.name == r.get("from"):
            return self.parent / r["to"]
        return self.repo

    def matches(self, pattern):
        return sorted(p for p in self.parent.iterdir() if fnmatch.fnmatch(p.name, pattern)
                      and p.resolve() != self.repo)

    def plan(self):
        """[(entry, [(src, dst)], approved)] - pure, so QC can read it."""
        out = []
        for e in self.cfg.get("moves") or []:
            pairs = []
            for pat in e.get("from") or []:
                for src in self.matches(pat):
                    pairs.append((src, self.parent / e["to"] / src.name
                                  if self._is_bin(e) else self.parent / e["to"]))
            out.append((e, pairs, bool(e.get("ok"))))
        return out

    def _is_bin(self, e):
        # several things into one folder ("thesis_archive") vs one folder renamed
        # ("Photobooth" -> "photobooth/Photobooth")
        return len(e.get("from") or []) > 1 or any(c in "*?" for c in "".join(e.get("from") or []))

    def leftovers(self):
        """Parent entries no move and no keep names: the next tidy's list."""
        keep = set(self.cfg.get("keep") or [])
        named = {s.name for _, pairs, _ in self.plan() for s, _ in pairs}
        return sorted(p.name for p in self.parent.iterdir()
                      if p.name not in keep and p.name not in named and p.resolve() != self.repo)

    # ---- is anything running in here ---------------------------------------
    def busy(self, roots):
        """Processes whose working folder or command line is inside roots."""
        try:
            import psutil
        except ImportError:
            return None
        keys = [str(r).lower() for r in roots]
        me = os.getpid()
        out = []
        for p in psutil.process_iter(["pid", "name", "cwd", "cmdline"]):
            try:
                if p.info["pid"] in (me, os.getppid()):
                    continue
                cwd = (p.info.get("cwd") or "").lower()
                cmd = " ".join(p.info.get("cmdline") or []).lower()
            except Exception:                                      # noqa: BLE001
                continue
            if any(cwd.startswith(k) or k in cmd for k in keys):
                out.append("%s (pid %s): %s" % (p.info["name"], p.info["pid"], cmd[:140] or cwd))
        return out

    def locks(self):
        return sorted(p.name for p in self.repo.glob(".staging-*.lock"))

    # ---- doing it ---------------------------------------------------------------
    def move_all(self, dry=False):
        done = []
        for e, pairs, ok in self.plan():
            if not ok:
                continue
            for src, dst in pairs:
                if dst.exists():
                    self.say.append("skip %s: %s already exists" % (src.name, dst))
                    continue
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                done.append((src, dst))
        return done

    def rename(self, dry=False):
        new = self.target_root()
        if new == self.repo:
            return None
        if new.exists():
            raise SystemExit("%s already exists - nothing renamed" % new)
        if not dry:
            os.rename(self.repo, new)
        return new

    def fix_paths(self, root, old):
        """After the rename: worktrees, this PC's files, shortcuts."""
        new = str(root)
        subprocess.run(["git", "worktree", "repair"], cwd=root, capture_output=True)
        fixed = []
        for f in self._ignored_text(root):
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            hits = [v for v in self._spellings(old) if v in text]
            if not hits:
                continue
            shutil.copy2(f, str(f) + ".bak")
            for v in hits:
                text = text.replace(v, self._like(v, new))
            with open(f, "w", encoding="utf-8", newline="") as w:
                w.write(text)
            fixed.append(f)
        return fixed

    @staticmethod
    def _spellings(old):
        s = str(old)
        both = {s, s.replace("\\", "/"), s.replace("/", "\\"),
                s.replace("\\", "\\\\"), s.replace("/", "\\").replace("\\", "\\\\")}
        return sorted(both, key=len, reverse=True)

    @staticmethod
    def _like(found, new):
        # write the new path the way the old one was written in that file
        if "\\\\" in found:
            return new.replace("/", "\\").replace("\\", "\\\\")
        if "/" in found:
            return new.replace("\\", "/")
        return new.replace("/", "\\")

    def _ignored_text(self, root):
        exts = tuple(self.cfg.get("fix_text") or [])
        r = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
                           cwd=root, capture_output=True, text=True)
        skip = (".staging", "_out", ".git", "node_modules", "__pycache__")
        for line in (r.stdout or "").splitlines():
            if line.endswith(exts) and not line.startswith(skip) and "/.staging" not in line:
                yield Path(root) / line

    @staticmethod
    def shortcut_dirs():
        if os.name != "nt":
            return []
        app = Path(os.environ.get("APPDATA", ""))
        sm = app / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        return [Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop", sm, sm / "Startup"]

    def fix_shortcuts(self, old, new):
        """Re-point every .lnk under the usual folders whose target was in old."""
        if os.name != "nt":
            return []
        ps = ("$o=$args[0];$n=$args[1];$s=New-Object -ComObject WScript.Shell;"
              "foreach($d in $args[2..($args.Count-1)]){if(Test-Path $d){"
              "Get-ChildItem $d -Recurse -Filter *.lnk -ErrorAction SilentlyContinue|%{"
              "$l=$s.CreateShortcut($_.FullName);"
              "if($l.TargetPath -like ($o+'*') -or $l.WorkingDirectory -like ($o+'*')){"
              "$l.TargetPath=$l.TargetPath.Replace($o,$n);$l.WorkingDirectory=$l.WorkingDirectory.Replace($o,$n);"
              "$l.Arguments=$l.Arguments.Replace($o,$n);$l.Save();$_.FullName}}}}")
        dirs = [str(d) for d in self.shortcut_dirs()] + [str(Path(new) / "dist")]
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps, str(old), str(new), *dirs],
                           capture_output=True, text=True)
        return [l for l in (r.stdout or "").splitlines() if l.strip()]

    def rc_command(self, root):
        return (self.cfg.get("rc_start") or "").replace("{root}", str(root))


def _report(t, approved_only=False):
    print("repo:   %s" % t.repo)
    new = t.target_root()
    if new != t.repo:
        print("rename: %s -> %s   (ok: %s)" % (t.repo.name, new.name, t.cfg["rename"]["ok"]))
    for e, pairs, ok in t.plan():
        if approved_only and not ok:
            continue
        tag = "OK " if ok else "WAIT"
        print("\n[%s] -> %s   %s" % (tag, e["to"], e.get("why", "")))
        for src, dst in pairs:
            print("    %s  ->  %s" % (src.name, dst.relative_to(t.parent)))
        if not pairs:
            print("    (nothing here matches %s)" % ", ".join(e["from"]))
    rest = t.leftovers()
    if rest:
        print("\nnot in any list (stays): " + ", ".join(rest))


def _apply(t, args):
    roots = [t.repo] + [s for _, pairs, ok in t.plan() if ok for s, _ in pairs]
    if not args.yes:
        _report(t, approved_only=True)
        print("\nnothing changed: add --yes to do the OK'd moves above")
        return 0
    if t.locks():
        print("a QC/promote lock is held: %s - wait for it" % ", ".join(t.locks()))
        return 2
    running = t.busy(roots)
    if running is None and not args.closed_everything:
        print("psutil is missing, so running programs cannot be checked. Close MiceHub, "
              "Studio, the voice helper, every Claude/Remote Control session and any "
              "training in these folders, then add --closed-everything.")
        return 2
    if running:
        print("still running inside these folders - close them first:\n  " + "\n  ".join(running))
        return 2
    old = t.repo
    for src, dst in t.move_all():
        print("moved %s -> %s" % (src.name, dst.relative_to(t.parent)))
    new = t.rename()
    if new:
        print("renamed %s -> %s" % (old.name, new.name))
        for f in t.fix_paths(new, old):
            print("fixed path in %s (old copy: .bak)" % f.relative_to(new))
        if (new / "tools" / "make_app_shortcuts.py").is_file():
            subprocess.run([sys.executable, str(new / "tools" / "make_app_shortcuts.py")], cwd=new)
        for l in t.fix_shortcuts(old, new):
            print("re-pointed shortcut %s" % l)
        print("\nStart Remote Control again from the new folder:\n  " + t.rc_command(new))
    for s in t.say:
        print(s)
    return 0


def _inside(path, folder):
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except ValueError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["plan", "apply"])
    ap.add_argument("--yes", action="store_true", help="really move (apply)")
    ap.add_argument("--closed-everything", action="store_true",
                    help="no psutil: you closed every program in these folders yourself")
    ap.add_argument("--repo", default=str(HERE))
    args = ap.parse_args(argv)
    t = PcTidy(args.repo)
    if args.what == "plan":
        _report(t)
        return 0
    if args.yes and _inside(Path.cwd(), t.repo):
        print("run this from the folder above, so this shell is not inside the folder "
              "being renamed:\n  cd \"%s\"\n  python \"%s\" apply --yes"
              % (t.parent, Path(t.repo.name) / "tools" / "tidy_pc.py"))
        return 2
    if args.yes and _inside(Path(__file__).resolve(), t.repo) and not os.environ.get("TIDY_PC_COPY"):
        # Windows will not rename the folder this script runs from: run a copy
        tmp = Path(tempfile.mkdtemp(prefix="tidy_pc_")) / "tidy_pc.py"
        shutil.copy2(__file__, tmp)
        env = dict(os.environ, TIDY_PC_COPY="1")
        return subprocess.call([sys.executable, str(tmp), *sys.argv[1:], "--repo", str(t.repo)],
                               cwd=str(t.parent), env=env)
    return _apply(t, args)


if __name__ == "__main__":
    sys.exit(main())
