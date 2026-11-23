"""Shrink the generated pictures into shared/web/img/ (small WebP, TV-browser friendly).

  python tools/pack_images.py <folder with the big PNGs>

  mascot.png       -> img/mascot.webp          transparent image, 360 px high
  icon_<id>.png    -> img/apps/<id>.webp       128 px, rounded corners cut out
  help_<name>.png  -> img/help/<name>.webp     640 px wide

Why: the big PNGs are ~1.5 MB each; the hub is opened on a low-spec Android TV (Chrome 75).
Chrome 75 reads WebP with alpha. Generated with Codex image generation, 2026-11-22; they hold
no photo, no person and no private data. Re-run to rebuild; the big files are not kept in the repo.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "shared" / "web" / "img"


def mascot(src):
    im = Image.open(src).convert("RGBA")
    if im.getextrema()[3][0] == 255:
        ImageDraw.floodfill(im, (0, 0), (255, 255, 255, 0), thresh=28)
        ImageDraw.floodfill(im, (im.width - 1, 0), (255, 255, 255, 0), thresh=28)
    h = 360
    im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
    im.save(OUT / "mascot.webp", "WEBP", quality=82, method=6)


def icon(src, name):
    im = Image.open(src).convert("RGBA").resize((128, 128), Image.LANCZOS)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 511, 511), radius=112, fill=255)
    im.putalpha(mask.resize((128, 128), Image.LANCZOS))
    (OUT / "apps").mkdir(parents=True, exist_ok=True)
    im.save(OUT / "apps" / (name + ".webp"), "WEBP", quality=86, method=6)


def scene(src, name):
    im = Image.open(src).convert("RGB")
    im = im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS)
    (OUT / "help").mkdir(parents=True, exist_ok=True)
    im.save(OUT / "help" / (name + ".webp"), "WEBP", quality=80, method=6)


def main(folder):
    for f in sorted(Path(folder).glob("*.png")):
        if f.stem == "mascot":
            mascot(f)
        elif f.stem.startswith("icon_"):
            icon(f, f.stem[5:])
        elif f.stem.startswith("help_"):
            scene(f, f.stem[5:])
        else:
            continue
        print("packed", f.name)


if __name__ == "__main__":
    main(sys.argv[1])
