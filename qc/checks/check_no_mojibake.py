"""No label a visitor reads was saved through the wrong text encoding.

Found 2026-10-27: Studio's Video page offered "Group dance â€” keep ..." and
the hub's machine-budget choices read "à¸­à¸±à¸•..." instead of Thai. Both
files were written by a Windows tool that read UTF-8 as cp1252 and saved it
back as UTF-8, so every em-dash and every Thai letter turned into 2-3 Latin
characters. Nothing failed: the JSON still parsed, the page still loaded.

The scan looks for the byte patterns that cp1252-read UTF-8 leaves behind:
`â€` (curly quotes, dashes, ellipsis) and `à¸`/`à¹` (every Thai letter).
Neither pair appears in real English or Thai text. Scanned: what the hub
and Studio serve, and the config/data they read labels from.
"""
import qc as F

AREA = "tooling"
TITLE = "no visible text was saved in the wrong encoding"
SLOW = False

GLOBS = ["config/**/*.json", "qc/data/*.json", "shared/web/**/*",
         "main_python/web/**/*", "apps/**/*",
         "nong/main_python_set_nong/web/**/*"]
EXTS = {".json", ".html", ".js", ".css", ".md", ".txt"}
MARKERS = ["â€", "à¸", "à¹"]


def run(t):
    seen = 0
    bad = []
    for pattern in GLOBS:
        for path in F.CODE.glob(pattern):
            if path.suffix not in EXTS or "node_modules" in path.parts or not path.is_file():
                continue
            seen += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if any(m in line for m in MARKERS):
                    bad.append(f"{path.relative_to(F.CODE).as_posix()}:{n}")
                    break
    t.ok(seen > 50, "the scan reached the served pages and config", f"{seen} files")
    t.ok(not bad, "no file holds UTF-8 that was read as cp1252 and saved again",
         ", ".join(bad[:8]))
