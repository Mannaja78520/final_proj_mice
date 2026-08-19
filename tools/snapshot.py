#!/usr/bin/env python3
"""Numbered, append-only snapshots of a set of source files.

The engine behind `nong/main_python_set_nong/save_patch.py` (the web app) and
`firmware/save_fw_patch.py` (the firmware). Each snapshot is one change:
snapshots never overwrite each other, so any earlier version can be looked at
or restored.

Kept deliberately format-compatible with the original web-only save_patch.py —
same `patches/NNNN_<slug>/` layout, same `PATCHES.md` table, same numbering —
so existing patches and the project's habits keep working.
"""
import datetime
import shutil
from pathlib import Path


class Snapshots:
    def __init__(self, root: Path, patterns, patches: Path, index: Path,
                 what: str, restore_cmd: str, also=None):
        self.root = Path(root)
        self.patterns = list(patterns)   # globs relative to root
        self.patches = Path(patches)
        self.index = Path(index)
        self.what = what                 # "web app" / "firmware"
        self.restore_cmd = restore_cmd   # shown in each patch.md
        # Files that live OUTSIDE root but that the snapshot is worthless
        # without — the shared stylesheet is the case this exists for: a page
        # restored from 2026-06 with today's design system is not the page
        # anyone remembers. Each entry is (folder, globs, prefix); the prefix is
        # where they sit inside the patch, so an old patch that has no prefix
        # folder still restores exactly the way it always did.
        self.also = [(Path(r), list(pats), pre) for r, pats, pre in (also or [])]

    # ---- the files a snapshot covers -------------------------------
    def pairs(self):
        """[(source file, path inside the patch, folder it restores to)]"""
        out = []
        for pat in self.patterns:
            for p in sorted(self.root.glob(pat)):
                if p.is_file():
                    out.append((p, p.relative_to(self.root), self.root))
        for root, pats, pre in self.also:
            for pat in pats:
                for p in sorted(root.glob(pat)):
                    if p.is_file():
                        out.append((p, Path(pre) / p.relative_to(root), root))
        return out

    def sources(self):
        return [rel for _, rel, _ in self.pairs()]

    def _dest(self, rel):
        """Where a file inside a patch belongs back in the tree."""
        for root, _, pre in self.also:
            pre = Path(pre)
            if rel == pre or pre in rel.parents:
                return root / rel.relative_to(pre)
        return self.root / rel

    def existing(self):
        if not self.patches.is_dir():
            return []
        out = []
        for p in self.patches.iterdir():
            if p.is_dir() and p.name[:4].isdigit():
                out.append((int(p.name[:4]), p))
        return sorted(out)

    @staticmethod
    def slugify(text):
        keep = "".join(c if c.isalnum() or c in " -_" else " " for c in text.lower())
        return "-".join(keep.split())[:48] or "patch"

    # ---- save / list / restore -------------------------------------
    def save(self, desc, quiet=False):
        self.patches.mkdir(parents=True, exist_ok=True)
        got = self.existing()
        n = (got[-1][0] + 1) if got else 1
        folder = self.patches / ("%04d_%s" % (n, self.slugify(desc)))
        folder.mkdir()
        saved = []
        for src, rel, _ in self.pairs():
            dst = folder / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            saved.append(rel.as_posix())
        when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        (folder / "patch.md").write_text(
            "# Patch %04d\n\n- **when:** %s\n- **change:** %s\n- **files:** %s\n\n"
            "Restore this exact version with:  `%s %d`\n"
            % (n, when, desc, ", ".join(saved), self.restore_cmd, n), encoding="utf-8")
        if not self.index.exists():
            self.index.write_text(
                "# %s patches\n\nEvery change to the %s is saved here as a numbered "
                "patch. Old patches are never removed — each row is a snapshot you can "
                "restore with `%s <n>`.\n\n| # | when | change |\n|---|---|---|\n"
                % (self.what.capitalize(), self.what, self.restore_cmd), encoding="utf-8")
        with self.index.open("a", encoding="utf-8") as f:
            f.write("| %04d | %s | %s |\n" % (n, when, desc.replace("|", "/")))
        if not quiet:
            print("saved patch %04d -> %s (%d file(s))" % (n, folder.name, len(saved)))
        return n

    def show_list(self):
        got = self.existing()
        if not got:
            print("no patches yet")
            return
        for n, p in got:
            desc = ""
            md = p / "patch.md"
            if md.exists():
                for line in md.read_text(encoding="utf-8").splitlines():
                    if line.startswith("- **change:**"):
                        desc = line.split(":**", 1)[1].strip()
            print("%04d  %s" % (n, desc))

    def restore(self, n):
        match = [p for num, p in self.existing() if num == int(n)]
        if not match:
            print("no patch %s" % n)
            return
        folder = match[0]
        # never lose the current version: snapshot it before overwriting
        self.save("auto-backup before restoring patch %s" % n, quiet=True)
        count = 0
        for f in folder.rglob("*"):
            if f.is_file() and f.name != "patch.md":
                rel = f.relative_to(folder)
                dst = self._dest(rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                count += 1
        print("restored patch %04d (%d file(s)) — the previous version was auto-saved first"
              % (int(n), count))


def cli(snap, argv, doc):
    """Shared command line: <desc> | --list | --restore <n>."""
    # Patch descriptions carry UI text, which carries symbols like "⚙". The
    # Windows console defaults to cp1252 and raises UnicodeEncodeError on those,
    # which made --list unusable once any patch mentioned one.
    try:
        import sys as _s
        _s.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(argv) < 1 or argv[0] in ("-h", "--help"):
        print(doc)
    elif argv[0] == "--list":
        snap.show_list()
    elif argv[0] == "--restore":
        snap.restore(argv[1])
    else:
        snap.save(" ".join(argv))
