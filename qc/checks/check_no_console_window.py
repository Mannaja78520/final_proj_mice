"""Nothing the hub or the helper runs may open a black window.

User 2026-09-18: *why it have terminal popup every time / make it in
background*. Speaking a sentence that is not already in the cache runs
`edge_tts`, and may fall back to `tts.ps1` through PowerShell. Both are
console programs, and a console program started from a windowed parent gets a
console of its OWN on Windows - so a black box flashed over whatever the
person was doing, once per new phrase. The same hole was in the flasher
(esptool), in the stop-the-voice-helper PowerShell call, and in the old
Reconize starter, which ran their `start.bat` - a file whose whole job is to
open two `cmd /k` windows and a Chrome tab.

The fix is one flag, CREATE_NO_WINDOW, on every child. It is easy to leave off
the NEXT child that gets added, and nothing else would notice: the feature
works, it just flashes. So this reads the shipped code and fails when any
subprocess call in it has no `creationflags`.

Only code that SHIPS is read (main_python/, apps/). qc/ and tools/ are run
from a terminal by a person who is looking at it, and a window there is where
the output is supposed to go.
"""
import ast

import qc as F

AREA = "tools"
TITLE = "no child process opens a console window"

WHERE = ("main_python", "apps")


def _calls(path):
    """Every subprocess.run/Popen call in one file, as (line, has_flag)."""
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and f.attr in ("run", "Popen", "call",
                                                            "check_output")):
            continue
        if not (isinstance(f.value, ast.Name) and f.value.id == "subprocess"):
            continue
        out.append((node.lineno, any(k.arg == "creationflags" for k in node.keywords)))
    return out


def run(t):
    bare, seen = [], 0
    for folder in WHERE:
        for path in sorted((F.CODE / folder).rglob("*.py")):
            if "__pycache__" in path.parts or "bench" in path.parts:
                continue
            try:
                found = _calls(path)
            except SyntaxError as e:                     # noqa: PERF203
                return t.ok(False, "the shipped Python parses", "%s: %s" % (path, e))
            seen += len(found)
            bare += ["%s:%d" % (path.relative_to(F.CODE), line)
                     for line, ok in found if not ok]
    t.ok(seen >= 5, "the shipped code really does start child processes",
         "only %d subprocess calls found - this check would pass on nothing" % seen)
    t.ok(not bare, "every child process is started with creationflags",
         "no window flag at: " + ", ".join(bare))

    # The flag has to be the RIGHT one, and only on Windows: CREATE_NO_WINDOW
    # does not exist on Linux, where reading it would crash the hub at import.
    for name in ("main_python/main.py", "apps/voice/service.py"):
        src = (F.CODE / name).read_text(encoding="utf-8", errors="replace")
        t.ok('getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0' in src,
             "%s asks for CREATE_NO_WINDOW, and only on Windows" % name,
             "its NO_WINDOW is not the guarded getattr")

    # The old Reconize starter ran their start.bat, which opens two `cmd /k`
    # windows on purpose. Starting it now goes through partner_launch, which
    # is the same hidden starter the Open Reconize button already used.
    main = (F.CODE / "main_python" / "main.py").read_text(encoding="utf-8",
                                                          errors="replace")
    # The names in STRINGS, not in comments: a comment saying which trap this
    # was is the point of the comment.
    texts = [n.value for n in ast.walk(ast.parse(main))
             if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    named = [s for s in texts if s in ("start.bat", "Start Reconize.vbs")]
    t.ok(not named, "the hub never runs the face app's own start.bat or .vbs",
         "main.py still names %r as something to launch" % (named,))
    at = main.find('"/api/reconize/start"')
    block = main[at:at + 1200] if at >= 0 else ""
    t.ok('partner_launch.start("reconize"' in block,
         "starting the face app goes through the hidden starter",
         "/api/reconize/start no longer calls partner_launch")
