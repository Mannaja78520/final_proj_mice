"""One shared memory for Claude, GPT and Gemini lives in handoff/memory/.

Asked 2026-11-20: each AI kept its own memory, so a fact told to one was lost
to the others. Now plain files in the repo, written by the AIs themselves
(tools/memory.py). This keeps the files valid, the index current, the repo
public-safe (no keys or e-mail) and every AI entry file pointing at it.
"""
import importlib.util
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "shared memory files are valid, indexed and public-safe"
ENTRY_FILES = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def load():
    spec = importlib.util.spec_from_file_location("memory_under_test", str(F.CODE / "tools" / "memory.py"))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    return M


def run(t):
    M = load()
    bad = M.problems()
    t.ok(not bad, "every memory file is valid and MEMORY.md is current", "; ".join(bad))
    t.ok((F.CODE / "handoff" / "memory" / "gpt-overflow-rule.md").is_file(),
         "the GPT overflow rule is in memory", "Claude has no rule for when to hand work to Codex")
    for name in ENTRY_FILES:
        top = "\n".join((F.CODE / name).read_text(encoding="utf-8").splitlines()[:25])
        t.ok("tools/memory.py" in top, "%s points to the shared memory" % name,
             "that AI never reads or writes the shared memory")

    # The validator must really refuse a leaked key and an oversized file (proof it can fail).
    with tempfile.TemporaryDirectory() as tmp:
        M.MEM = Path(tmp)
        M.INDEX = Path(tmp) / "MEMORY.md"
        M.cmd_add("ok-fact", "fine", "user", "plain text")
        t.ok(not M.problems(), "a clean fact passes", "; ".join(M.problems()))
        M.cmd_add("leak", "bad", "user", "key sk-" + "a" * 30)
        t.ok(any("leak.md" in p for p in M.problems()), "a key-shaped string is refused", "secrets would reach the public repo")
        M.cmd_add("leak", "bad", "user", "mail someone@example.com")
        t.ok(any("leak.md" in p for p in M.problems()), "an e-mail address is refused", "personal data would reach the public repo")
        M.cmd_add("leak", "bad", "user", "x" * 5000)
        t.ok(any("bytes" in p for p in M.problems()), "an oversized fact is refused", "recall would truncate it")

    # stale: a path that does not exist is reported, one that does is not.
    with tempfile.TemporaryDirectory() as tmp:
        M.MEM = Path(tmp)
        M.INDEX = Path(tmp) / "MEMORY.md"
        M.cmd_add("paths", "d", "project", "see `HANDOFF.md` and `no/such/file.py`")
        gone = M.stale()
        t.ok(len(gone) == 1 and "no/such/file.py" in gone[0], "stale names only the missing path",
             "; ".join(gone))
