"""A local import inside the request router poisons EVERY endpoint.

2026-08-25: /api/report opened its handler with ``import json`` — two lines
inside the one giant function that routes every POST. Python decides local vs
global per FUNCTION at compile time, so those two lines made ``json`` local to
the whole router, and every branch that read it EARLIER — pairing, atomic
saves, OTA image transfer, play — died with ``UnboundLocalError`` and answered
500. Thirty-three red checks across four unrelated areas, from two innocent
looking lines. The browser checks stayed green: the pages were fine; the
SERVER was answering errors.

The guard is mechanical: the module already imports the stdlib names it uses
at the top, so ANY deeply-indented ``import <name>`` of one of them is this
bug waiting for its branch order to change. Re-importing at function scope is
never needed here.
"""
import re

import qc as F

AREA = "hub"
TITLE = "no local re-import of a module-level name inside a handler"

NAMES = ("json", "uuid", "re", "os", "time", "base64", "socket", "hashlib",
         "itertools", "shutil", "threading")


def run(t):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    lines = src.splitlines()
    bad = []
    for i, line in enumerate(lines):
        # `import json as _json` binds _json and leaves the global alone -
        # only the BOUND name can shadow anything, so judge that one.
        m = re.match(r"(\s{4,})import (\w+)(?:\s+as\s+(\w+))?", line)
        if not m or m.group(2) not in NAMES:
            continue
        name, indent = m.group(3) or m.group(2), m.group(1)
        if name != m.group(2):
            continue        # aliased to a different binding - nothing shadowed
        # Walk back to a def indented LESS than the import - a nested def at
        # the same depth is not the container, it would shrink the window to
        # nothing and hide exactly this bug.
        d = i
        while d > 0:
            dm = re.match(r"(\s*)def \w+", lines[d])
            if dm and len(dm.group(1)) < len(indent):
                break
            d -= 1
        if d == 0:
            continue
        dident = len(lines[d]) - len(lines[d].lstrip())
        j = d + 1
        while j < len(lines) and (not lines[j].strip()
                                  or len(lines[j]) - len(lines[j].lstrip()) > dident):
            j += 1
        body = [re.sub(r"#.*", "", l) for l in lines[d:j]]
        # In a DISPATCHER (the request router's many `if path ==` branches)
        # any local import of an owned name is unsafe full stop: sibling
        # branches read the global on paths that never pass the import line -
        # that is exactly how /api/report killed pairing, saves, OTA and play
        # while sitting textually BELOW their code. In a straight-line helper
        # (import, then use) the order protects it, so those stay legal.
        if len(re.findall(r"\bif path ==", "\n".join(body))) >= 2:
            bad.append("line %d: %s" % (i + 1, line.strip()))
            continue
        earlier = "\n".join(body[:i - d])
        if re.search(r"\b%s\b" % name, earlier):
            bad.append("line %d: %s" % (i + 1, line.strip()))
    t.ok(not bad,
         "no handler re-imports a name the same function also reads",
         "a local import makes the name local to the WHOLE function - every "
         "branch reading it earlier dies with UnboundLocalError "
         "(33 red checks, 2026-08-25): %r" % bad[:4])
