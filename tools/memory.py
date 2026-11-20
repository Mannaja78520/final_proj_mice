"""Shared memory for every AI (Claude, Codex/GPT, Gemini): handoff/memory/.

    python tools/memory.py list                       the index (read this first)
    python tools/memory.py add <slug> "<one line>" <type> "<body>"   write or replace one fact
    python tools/memory.py index                      rebuild MEMORY.md from the files
    python tools/memory.py check                      validate (QC runs this)
    python tools/memory.py stale                      paths a memory names that no longer exist

WHY (user 2026-11-20): each AI had its own memory (Claude's lives in the cloud,
GPT and Gemini had none), so a fact told to one was lost to the others. The
post the user shared (Thai Type Coding, 2026) says the same: turn the tool's
auto memory off, write the memory yourself as plain files and keep it tidy.
Plain Markdown in the repo is the one format all three read.
The repo is PUBLIC: no keys, passwords, personal data, friend code (check refuses
the obvious ones). One fact per file, under 4 KB, so a recall never truncates.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEM = ROOT / "handoff" / "memory"
INDEX = MEM / "MEMORY.md"
TYPES = ("user", "feedback", "project", "reference")
MAX_BYTES = 4096
HEAD = re.compile(r"\A---\nname: (.+)\ndescription: (.+)\nmetadata:\n  type: (\w+)\n---\n", re.M)
# Shapes of secrets that must never reach a public repo (the list is data: add a line).
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|"
                    r"-----BEGIN [A-Z ]*PRIVATE KEY|[\w.+-]+@[\w-]+\.(com|net|org)\b)")


def files():
    return sorted(p for p in MEM.glob("*.md") if p.name != "MEMORY.md")


def parse(path):
    m = HEAD.match(path.read_text(encoding="utf-8"))
    return (m.group(1), m.group(2), m.group(3)) if m else None


def write(path, text):
    path.write_bytes(text.encode("utf-8"))   # LF on Windows too (CLAUDE.md)


def build_index():
    rows = ["# Shared memory (Claude, GPT, Gemini)", "",
            "Read this index, open only the files that match your task. Add a fact with",
            "`python tools/memory.py add ...`. Public repo: no secrets or personal data.", ""]
    for kind in TYPES:
        items = [(p, parse(p)) for p in files()]
        items = [(p, h) for p, h in items if h and h[2] == kind]
        if items:
            rows += ["## " + kind, ""]
            rows += ["- [%s](%s): %s" % (h[0], p.name, h[1]) for p, h in items]
            rows.append("")
    return "\n".join(rows)


def cmd_index():
    write(INDEX, build_index())
    print("wrote", INDEX.name)


def cmd_add(slug, desc, kind, body):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or kind not in TYPES:
        sys.exit("slug: kebab-case; type: " + "|".join(TYPES))
    text = "---\nname: %s\ndescription: %s\nmetadata:\n  type: %s\n---\n\n%s\n" % (slug, desc, kind, body)
    MEM.mkdir(parents=True, exist_ok=True)
    write(MEM / (slug + ".md"), text)
    cmd_index()


def problems():
    out = []
    for p in files():
        raw = p.read_bytes()
        h = parse(p)
        if not h:
            out.append("%s: missing name/description/type header" % p.name)
            continue
        if h[0] != p.stem:
            out.append("%s: name '%s' must equal the file name" % (p.name, h[0]))
        if h[2] not in TYPES:
            out.append("%s: type '%s' not in %s" % (p.name, h[2], TYPES))
        if len(raw) > MAX_BYTES:
            out.append("%s: %d bytes, split it (max %d)" % (p.name, len(raw), MAX_BYTES))
        if SECRET.search(raw.decode("utf-8", "replace")):
            out.append("%s: looks like a key or an e-mail; the repo is public" % p.name)
    if not INDEX.is_file() or INDEX.read_text(encoding="utf-8") != build_index():
        out.append("MEMORY.md is stale: run python tools/memory.py index")
    return out


PATHISH = re.compile(r"`((?:[\w.-]+/)*[\w.-]+(?:\.[a-z]{1,5}|/))`")


def stale():
    """Repo paths named in backticks that are gone: the memory is probably out of date.
    Report only (user 2026-11-20: a person or the AI decides what to prune)."""
    out = []
    for p in files():
        for ref in sorted(set(PATHISH.findall(p.read_text(encoding="utf-8")))):
            if "*" in ref or ref.startswith(("python", "http")):
                continue
            if not (ROOT / ref).exists():
                out.append("%s names %s, which does not exist" % (p.name, ref))
    return out


def main(argv):
    if argv[:1] == ["list"]:
        print(INDEX.read_text(encoding="utf-8") if INDEX.is_file() else "no memory yet")
    elif argv[:1] == ["index"]:
        cmd_index()
    elif argv[:1] == ["add"] and len(argv) == 5:
        cmd_add(*argv[1:])
    elif argv[:1] == ["check"]:
        bad = problems()
        print("\n".join(bad) or "memory ok")
        sys.exit(1 if bad else 0)
    elif argv[:1] == ["stale"]:
        gone = stale()
        print("\n".join(gone) or "no stale paths")
        sys.exit(1 if gone else 0)
    else:
        sys.exit(__doc__.split("\n\n", 2)[1])


if __name__ == "__main__":
    main(sys.argv[1:])
