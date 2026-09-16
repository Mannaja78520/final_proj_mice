"""What this build was made from, so a running exe can say it is out of date.

The trap this closes, measured 2026-08-21: the hub answering on 8642 was
yesterday's `MiceHub.exe`, missing pairing, the chatty-board fix, the bus group
carry and the OTA login. Nothing said so. It was noticed only because its
password did not match, and half an hour went into hunting a bug that had
already been fixed in source the exe had never seen.

The exe cannot ask git and cannot read its own future, but it can carry a
receipt: `MiceHub.spec` calls `write()` at build time, which records a sha for
every source file that went in, and the bundle carries that receipt. A running
exe re-reads those same files from the tree beside it and compares. Different
sha, and it says which files - so the answer is *main.py changed since this was
built*, not a vague *maybe rebuild*.

Two deliberate limits:

* **content, never mtime.** A `git checkout` rewrites every mtime, which would
  cry stale on a tree that is byte-identical to the build. A sha only moves
  when the bytes move;
* **no source, no claim.** On a venue PC the exe travels alone. There is
  nothing to compare against, so the hub says nothing at all rather than
  guessing - a warning that fires where it cannot be acted on is a warning
  people learn to close.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

# Where the hub's source lives, relative to `code/`. This list is what the
# stamp covers, and `check_stale_build` holds it against MiceHub.spec's own
# `datas` so the two cannot drift: a folder that is bundled but not stamped is
# a folder that can change without anyone being told.
AREAS = (
    ("main_python", "*.py"),
    ("main_python", "nong.ico"),      # baked into the exe, so a change needs a build
    ("main_python/web", "**/*"),
    ("shared/web", "**/*"),
    ("nong/main_python_set_nong/web", "**/*"),
    ("firmware/config", "**/*"),
    # The hub's own config: where the voice helper answers, and which pages
    # work with no login. Bundled into the exe, so editing one beside a stale
    # exe has to be something the hub can notice and say.
    ("config", "**/*"),
    ("apps", "**/*"),
    ("tools", "registry.py"),
    ("firmware/src/web", "WebUI.h"),
)
# Source, not the things the hub writes while it runs: a password hash, a list
# of known hubs and a saved project all change without the build changing.
KEEP = (".py", ".html", ".css", ".js", ".json", ".svg", ".png", ".ico",
        ".webp", ".h", ".yaml", ".yml")
STAMP = "build_stamp.json"


def _sha(f):
    return hashlib.sha1(f.read_bytes()).hexdigest()[:8]


def source_files(root):
    """{path relative to code/: sha} for everything a build is made from."""
    root = Path(root)
    out = {}
    for area, pattern in AREAS:
        d = root / area
        if not d.is_dir():
            continue
        for f in sorted(d.glob(pattern)):
            # Names starting with _ are scratch: QC writes its driver pages
            # into the web folders while a browser check runs, and counting
            # them would make every build look stale a moment later.
            rel = f.relative_to(root)
            if not f.is_file() or f.suffix.lower() not in KEEP:
                continue
            if any(p.startswith("_") or p == "__pycache__" for p in rel.parts):
                continue
            try:
                out[rel.as_posix()] = _sha(f)
            except OSError:
                continue      # deleted or locked between the listing and the read
    return out


def signature(files):
    """One short id for a whole source tree."""
    h = hashlib.sha1()
    for rel in sorted(files):
        h.update(("%s:%s\n" % (rel, files[rel])).encode())
    return h.hexdigest()[:12]


def write(root, out_dir):
    """Record what this build is made from. Called by MiceHub.spec."""
    files = source_files(root)
    stamp = {"when": time.strftime("%Y-%m-%d %H:%M"),
             "signature": signature(files), "files": files}
    p = Path(out_dir) / STAMP
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(stamp).encode("utf-8"))
    return p


def built_from():
    """The receipt this exe carries, or None when running from source."""
    base = getattr(sys, "_MEIPASS", "")
    if not base:
        return None
    p = Path(base) / STAMP
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def source_root(start=None):
    """The source tree beside this exe, or None if it travels alone.

    Only a few levels up: the exe sits in `code/dist/`, in `code/main_python/`
    or in `code/` itself, and walking further would eventually find somebody
    else's checkout.

    `MiceHub.spec` is the marker, not `main.py` alone. The panel's point,
    2026-08-21: the tree that this exe could have been BUILT from is the only
    one worth comparing against, and a folder with a stray main.py in it is
    not that.
    """
    here = Path(start or sys.executable).resolve().parent
    for d in (here, *list(here.parents)[:3]):
        if (d / "MiceHub.spec").is_file() and (d / "main_python" / "main.py").is_file():
            return d
    return None


_cache = [0.0, None]


def state(ttl=30.0, now=None):
    """Is the running build older than the source beside it?

    Cached: every open tab polls the version endpoint, and re-reading two
    hundred files to answer a question whose answer changes once a day is a
    poor trade.
    """
    now = now if now is not None else time.time()
    if _cache[1] is not None and now - _cache[0] < ttl:
        return _cache[1]
    out = {"stale": False, "built": "", "changed": [], "count": 0, "source": ""}
    # Never raises. This rides on /api/version, which every open tab polls and
    # the login screen needs: a hub that cannot answer it because a file moved
    # while it was being read is far worse than one that cannot tell whether
    # it is stale.
    try:
        stamp = built_from()
        if stamp:
            out["built"] = stamp.get("when", "")
            root = source_root()
            if root:
                out["source"] = str(root)
                was = stamp.get("files") or {}
                now_files = source_files(root)
                changed = sorted(set(k for k in set(was) | set(now_files)
                                     if was.get(k) != now_files.get(k)))
                out["changed"] = changed[:3]
                out["count"] = len(changed)
                out["stale"] = bool(changed)
    except Exception:                                         # noqa: BLE001
        return out                       # not cached: try again next time
    _cache[0], _cache[1] = now, out
    return out


# The one way to rebuild. Written here so the banner, the diagnostics bundle
# and CLAUDE.md cannot each carry a different command - a bare --onefile line
# built a hub with no web pages and overwrote the spec while doing it.
REBUILD = "python -m PyInstaller --clean MiceHub.spec"


def why(st):
    """One sentence a person can act on, or "" when there is nothing to say."""
    if not st.get("stale"):
        return ""
    more = st["count"] - len(st["changed"])
    return ("This hub is running an OLD build: MiceHub.exe was built %s, and "
            "%d source file%s changed since (%s%s)."
            % (st["built"] or "earlier", st["count"],
               "" if st["count"] == 1 else "s", ", ".join(st["changed"]),
               ", and %d more" % more if more > 0 else ""))
