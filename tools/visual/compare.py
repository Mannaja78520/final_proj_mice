"""Compare two screenshot folders from shoot.js (old known-good vs new): which screens changed, by how much.
  python tools/visual/compare.py <old dir> <new dir> <out dir> [--min 0.01]
Writes a side-by-side PNG (old | new | changed pixels) for every screen whose changed share is above --min,
and prints a table sorted by change. A screenshot that exists in only one folder is listed too.
"""
import sys
from pathlib import Path
from PIL import Image, ImageChops


def main():
    old, new, out = (Path(a) for a in sys.argv[1:4])
    lim = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 0.01
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    names = sorted({p.name for p in old.glob("*.png")} | {p.name for p in new.glob("*.png")})
    for n in names:
        a, b = old / n, new / n
        if not a.exists() or not b.exists():
            rows.append((1.0, n, "only in " + ("new" if b.exists() else "old")))
            continue
        A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        h = max(A.height, B.height)
        if A.size != B.size:
            A2 = Image.new("RGB", (A.width, h), "white"); A2.paste(A); A = A2
            B2 = Image.new("RGB", (B.width, h), "white"); B2.paste(B); B = B2
        D = ImageChops.difference(A, B).convert("L").point(lambda v: 255 if v > 24 else 0)
        share = sum(1 for v in D.getdata() if v) / (D.width * D.height)
        rows.append((share, n, "%.1f%% changed" % (share * 100)))
        if share >= lim:
            S = Image.new("RGB", (A.width * 3, h), "white")
            S.paste(A, (0, 0)); S.paste(B, (A.width, 0)); S.paste(D.convert("RGB"), (A.width * 2, 0))
            S.save(out / n)
    for share, n, note in sorted(rows, reverse=True):
        print("%-60s %s" % (n, note))


main()
