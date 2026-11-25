"""Every change adds a short change-log entry (patch-notes style: kind + one plain line, optional problem/method/numbers).

Asked 2026-11-25: the project report needs, per version, what changed, how it
works, the problem and the method that fixed it. Entries are one file each
(docs/changelog/entries/) so parallel agents never clash; docs/CHANGELOG.md is
generated. This validates the entries and the page, proves the validator can
fail, and fails a branch that changes code without adding an entry.
"""
import importlib.util
import subprocess
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "every change has a change-log entry and the page is current"
SLOW = False
# Paths whose change needs no entry (records, generated pages, task notes). Data: add a prefix.
EXEMPT = ("docs/changelog/", "docs/CHANGELOG.md", "docs/systems/", "docs/PLAN.html", "docs/BRIDGE.md",
          "handoff/", "qc/last_run.log", "promt.md", "PATCHES.md")


def load():
    spec = importlib.util.spec_from_file_location("changelog_under_test", str(F.CODE / "tools" / "changelog.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    return M


def git(*args):
    r = subprocess.run(["git", *args], cwd=str(F.CODE), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def changed_vs_main():
    base = git("merge-base", "origin/main", "HEAD")
    if not base:
        return None            # no origin/main here (zip copy, promote staging): nothing to compare
    files = git("diff", "--name-only", base) or ""
    return [f for f in files.splitlines() if f]


def run(t):
    M = load()
    bad = M.problems()
    t.ok(not bad, "every entry is valid and docs/CHANGELOG.md is current", "; ".join(bad))

    # Proof it can fail: a template placeholder, a bad date and a stale page are refused.
    with tempfile.TemporaryDirectory() as tmp:
        M.ENTRIES = Path(tmp) / "entries"
        M.ENTRIES.mkdir()
        M.PAGE = Path(tmp) / "page.md"
        (M.ENTRIES / "2026-01-01-x.md").write_text(
            "---\ndate: 2026-01-01\nkind: fixed\nprs: 1\narea: qc\ntitle: t\n---\nMethod: real\n", encoding="utf-8")
        M.PAGE.write_text(M.render(), encoding="utf-8")
        t.ok(not M.problems(), "a clean entry passes", "; ".join(M.problems()))
        (M.ENTRIES / "2026-01-01-x.md").write_text(
            "---\ndate: 2026-01-01\nkind: fixed\nprs: 1\narea: qc\ntitle: t\n---\nMethod: (optional) how\n", encoding="utf-8")
        t.ok(any("placeholder" in p for p in M.problems()), "an unfilled placeholder is refused", "the log would show template text")
        (M.ENTRIES / "2026-01-01-x.md").write_text(
            "---\ndate: 2026-01-01\nkind: fixed\nprs: 1\narea: qc\ntitle: changed\n---\nMethod: real\n", encoding="utf-8")
        t.ok(any("stale" in p for p in M.problems()), "a page not rebuilt after an edit is refused", "page and entries disagree")

    files = changed_vs_main()
    if files is None:
        return
    code = [f for f in files if not f.startswith(EXEMPT)]
    added = [f for f in files if f.startswith("docs/changelog/entries/")]
    t.ok(not code or added, "a branch that changes code adds a change-log entry",
         "run python tools/changelog.py new <slug> \"<title>\" --kind fixed --area <area>; changed: " + ", ".join(code[:5]))
