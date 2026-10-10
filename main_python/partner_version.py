"""Which version of an outside program is installed, and does it still look
like the one we built against (system A9).

    report(entry) -> {commit, branch, version, tested, same, spec, words}

IT TELLS, IT NEVER ACTS (A9-3). Reconize updates itself often; when it moves
past the commit in partners.json `testedWith`, the screen says so in plain
words and everything keeps working exactly as before. Nothing here turns a
feature off - a guess that their update broke something is not a reason to
stop greeting at an event.

WE NEVER RUN GIT IN THEIR FOLDER (A9-1). Their updater owns it, and a git
command takes locks and can rewrite the index under it. So the commit is READ
from .git as files: HEAD, then refs/heads/<branch>, then packed-refs - after
a `git gc` the loose ref is gone and the commit lives only in packed-refs.
"""
import json
import urllib.request
from pathlib import Path


def _gitdir(folder):
    g = Path(folder) / ".git"
    if g.is_file():                     # a worktree: ".git" names the real one
        line = g.read_text(encoding="utf-8", errors="replace").strip()
        if line.startswith("gitdir:"):
            p = Path(line[7:].strip())
            return p if p.is_absolute() else (Path(folder) / p)
    return g


def commit(folder):
    """(sha, branch, why). Read only; branch is "" for a detached HEAD, which
    is how their updater leaves it (`git checkout --detach`)."""
    g = _gitdir(folder)
    try:
        head = (g / "HEAD").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "", "", "no git information in %s" % folder
    if not head.startswith("ref:"):
        return head, "", ""
    ref = head[4:].strip()
    branch = ref.rsplit("/", 1)[-1]
    loose = g / ref
    if loose.is_file():
        return loose.read_text(encoding="utf-8", errors="replace").strip(), branch, ""
    try:
        for line in (g / "packed-refs").read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0], branch, ""
    except OSError:
        pass
    return "", branch, "the branch %s has no commit written down" % branch


def spec_missing(entry, timeout=2.0):
    """(checked, missing). The HTTP paths we call that their OpenAPI page
    does not list. Only paths: OpenAPI says nothing about a websocket, and the
    fields of a row are checked on real payloads by the watcher instead."""
    ours = [entry.get("health"), (entry.get("login") or {}).get("path"),
            (entry.get("count") or {}).get("path")]
    ours += [s.get("path") for s in (entry.get("events") or []) if s.get("kind") == "poll"]
    ours = sorted({p.split("?")[0] for p in ours if p})
    try:
        with urllib.request.urlopen((entry.get("api") or "").rstrip("/")
                                    + (entry.get("spec") or "/openapi.json"), timeout=timeout) as r:
            paths = (json.loads(r.read().decode("utf-8")) or {}).get("paths") or {}
    except Exception:                                        # noqa: BLE001
        return False, []
    return True, [p for p in ours if p not in paths]


def report(entry, timeout=2.0):
    folder = entry.get("folder") or ""
    sha, branch, why = commit(folder) if folder else ("", "", "no folder in partners.json")
    version = ""
    vf = Path(folder) / (entry.get("versionFile") or "VERSION") if folder else None
    if vf and vf.is_file():
        version = vf.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0][:40]
    tested = [str(t) for t in (entry.get("testedWith") or [])]
    same = bool(sha) and any(sha.startswith(t) or t.startswith(sha) for t in tested)
    checked, missing = spec_missing(entry, timeout)
    name = entry.get("name") or "It"
    if not sha:
        words = "Mice cannot tell which version of %s is installed." % name
    elif same:
        words = "%s is the version Mice was tested with." % name
    else:
        words = ("%s has been updated since Mice was tested with it. Everything keeps "
                 "working as before; if greetings or counts stop, this is the first "
                 "place to look." % name)
    if missing:
        words += " Some of the addresses Mice uses are no longer listed by it."
    return {"ok": True, "commit": sha, "branch": branch, "version": version,
            "tested": tested, "same": same, "why": why,
            "spec": {"checked": checked, "missing": missing}, "words": words}
