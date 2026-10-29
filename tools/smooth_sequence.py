"""Smooth a sequence file: the shared smoother for makers outside Studio (A54-1).

User 2026-10-29: every move through one smoother, like a plugin. Studio
smooths what it writes itself; a sequence made anywhere else (the RL dances,
a hand-written file, an old export) goes through this: it adds a `pass:` step
before every pose that should be passed through instead of stopped on, and
reports the jerk before and after at the board's 50 Hz. Times never change.

    python tools/smooth_sequence.py dance.yaml                 -> dance.smooth.yaml
    python tools/smooth_sequence.py dance.yaml --out x.yaml --source rl --rig my_rig.json
    python tools/smooth_sequence.py dance.yaml --report        only the numbers

No collision check runs here, so the curve leaves the straight lines the
file's maker checked by at most uncheckedOffLineDeg (motion_smooth.json).
Old `pass:` steps in the file are replaced. A board without PASS skips them.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main_python"))
sys.path.insert(0, str(ROOT))
import motion_smooth  # noqa: E402
from tools.nong_sim.board_clock import STEP  # noqa: E402
from tools.nong_sim.studio import StudioFacts, load_rig  # noqa: E402


def read_keys(lines):
    """[(line index, key)] for every pose step; a wait becomes the hold of the
    pose before it, the pace in force gives the speed cap."""
    keys, pace, inside = [], None, False
    for n, line in enumerate(lines):
        if line.startswith("steps:"):
            inside = True
            continue
        m = STEP.match(line) if inside else None
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip().strip('"')
        if key == "pose":
            w = value.split()
            t = float(w[w.index("T") + 1]) if "T" in w else 0.0
            keys.append((n, {"pose": [float(v) for v in w[:10]], "t": t, "hold": 0}))
        elif key == "wait" and keys:
            keys[-1][1]["hold"] += max(0.0, float(value))
        elif key == "pace" and pace is None:
            pace = value
    return keys, pace


def smooth(text, rig, source="rl", cfg=None):
    """(new text, report before, report after)."""
    cfg = cfg if cfg is not None else motion_smooth.load_config()
    lines = [ln for ln in text.splitlines() if not re.match(r"^\s*-\s*pass\s*:", ln)]
    found, pace = read_keys(lines)
    K = [k for _, k in found]
    facts = StudioFacts()
    words = (pace or "").split()
    if words[:1] == ["music"]:
        cap = float(words[1]) if len(words) > 1 else facts.music_dps
    else:
        cap = facts.safe_dps
    before = motion_smooth.jerk_report(K) if len(K) > 1 else {}
    if not motion_smooth.enabled(cfg, source) or len(K) < 3:
        return "\n".join(lines) + "\n", before, before
    V = motion_smooth.Smoother(cfg, rig, cap).vias(K)
    out, at = [], {n: i for i, (n, _) in enumerate(found)}
    for n, line in enumerate(lines):
        i = at.get(n)
        p = motion_smooth.pass_values(V, i) if i else None
        if p:
            indent = line[:len(line) - len(line.lstrip())]
            out.append('%s- pass: "%s"' % (indent, motion_smooth.pass_line(p)))
        out.append(line)
    return "\n".join(out) + "\n", before, motion_smooth.jerk_report(K, V)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--out")
    ap.add_argument("--rig", help="a Studio rig or settings backup (default: rig_default.json)")
    ap.add_argument("--source", default="rl", help="motion_smooth.json source (rl, studio, ...)")
    ap.add_argument("--report", action="store_true", help="print the numbers, write nothing")
    a = ap.parse_args(argv)
    src = Path(a.file)
    text, before, after = smooth(src.read_text(encoding="utf-8"), load_rig(a.rig), a.source)
    print(json.dumps({"before": before, "after": after}))
    if not a.report:
        out = Path(a.out) if a.out else src.with_suffix(".smooth" + src.suffix)
        with open(out, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
