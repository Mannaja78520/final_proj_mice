#!/usr/bin/env python3
"""Build a day-by-day diary of the project from what was actually recorded.

    python tools/make_diary.py            # writes docs/DIARY.md
    python tools/make_diary.py --print    # to the screen instead

The source is the patch logs, not memory. Every change to the web app, the hub
pages and the firmware is snapshotted with a date and a description at the time
it happens, so those three files together ARE the history — nothing has to be
reconstructed afterwards, and nothing that was landed can be quietly left out.

Kept deliberately plain: one heading per day, one line per change, tagged with
where it landed. It is a diary, not a specification.
"""
import re
import sys
from collections import OrderedDict
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent

SOURCES = [
    ("studio", CODE / "nong" / "main_python_set_nong" / "PATCHES.md"),
    ("hub", CODE / "main_python" / "PATCHES.md"),
    ("firmware", CODE / "firmware" / "PATCHES.md"),
]

# | 0031 | 2026-08-09 04:03 | what it did |
ROW = re.compile(r"^\|\s*(\d{3,4})\s*\|\s*(\d{4}-\d{2}-\d{2})[^|]*\|\s*(.+?)\s*\|?\s*$")


def rows():
    for where, path in SOURCES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = ROW.match(line.strip())
            if m:
                yield m.group(2), where, m.group(1), m.group(3).strip()


def tidy(text, limit=300):
    """One readable sentence or two — the full note lives in the patch."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:stop + 1] if stop > 120 else cut.rstrip() + "…")


def build():
    days = OrderedDict()
    for day, where, num, what in sorted(rows()):
        days.setdefault(day, []).append((where, num, what))

    out = ["# Mice — diary", "",
           "One entry per day, built from the patch logs by "
           "`python tools/make_diary.py`. Every change is snapshotted with its "
           "date when it lands, so this is the record rather than a "
           "recollection. Re-run it any time to bring the diary up to date.",
           ""]
    if not days:
        out.append("_No patches recorded yet._")
        return "\n".join(out)

    first, last = min(days), max(days)
    total = sum(len(v) for v in days.values())
    out += ["**%s → %s · %d changes over %d days**" % (first, last, total, len(days)),
            "", "---", ""]

    for day in sorted(days, reverse=True):        # newest first, like a diary
        items = days[day]
        out.append("## %s" % day)
        out.append("")
        for where, num, what in items:
            out.append("- **%s %s** — %s" % (where, num, tidy(what)))
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    text = build()
    if "--print" in sys.argv:
        # The diary contains characters the Windows console codepage (cp1252)
        # cannot encode — "→" in the summary line above all. Printing them to a
        # cp1252 stdout raises UnicodeEncodeError and the whole generator dies,
        # so ask for UTF-8 out before writing a single line.
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):     # pre-3.7, or a stream that cannot
            pass                              # be reconfigured — try anyway
        print(text)
    else:
        dest = CODE / "docs" / "DIARY.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", newline="\n")
        print("wrote %s (%d lines)" % (dest, text.count("\n") + 1))
