"""Pictures that travel with a problem report (screenshots, phone photos).

One file per picture under HERE/reports/img/, named <report id>_<n>.<ext>, next
to the report's JSON. The folder is machine-local and gitignored: a screenshot
can show a customer's screen, so it never goes to the public repo.

The reporting route is open (no login), so everything is checked here, not
trusted from the page: the picture must really be a JPEG/PNG/WebP by its first
bytes, small, and at most MAX_IMAGES per report. The page shrinks pictures
before sending (see report_images.js); this is the second wall.
"""
import base64
import re
from pathlib import Path

MAX_IMAGES = 3
MAX_BYTES = 450 * 1024          # per picture, after the page's shrinking (3 of them as base64 must fit MAX_BODY)
MAX_BODY = 2 * 1048576          # whole report request; check_translate sends 2 MB+ and expects a refusal
_ID = re.compile(r"^[0-9a-f]{12}$")
_URL = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$")
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_MIME = {v: k for k, v in _EXT.items()}


def _kind(raw):
    """What the bytes really are - the data: header is the sender's claim."""
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return ""


def decode(urls):
    """data: URLs from the page -> [(ext, bytes)]; a bad one is dropped, not fatal."""
    out = []
    for u in (urls if isinstance(urls, list) else [])[:MAX_IMAGES * 2]:
        if len(out) >= MAX_IMAGES:
            break
        m = _URL.match(u) if isinstance(u, str) and len(u) < MAX_BYTES * 2 else None
        if not m:
            continue
        try:
            raw = base64.b64decode(m.group(2), validate=True)
        except Exception:
            continue
        kind = _kind(raw)
        if kind and len(raw) <= MAX_BYTES:
            out.append((_EXT[kind], raw))
    return out


def save(img_dir, rid, urls):
    """Write the pictures; returns the file names to put in the report."""
    pics = decode(urls)
    if not pics or not _ID.match(rid):
        return []
    Path(img_dir).mkdir(parents=True, exist_ok=True)
    names = []
    for n, (ext, raw) in enumerate(pics):
        name = "%s_%d.%s" % (rid, n, ext)
        (Path(img_dir) / name).write_bytes(raw)
        names.append(name)
    return names


def read(img_dir, rid, n):
    """(mime, bytes) of picture n of report rid, or None."""
    if not _ID.match(str(rid)) or not str(n).isdigit() or int(n) >= MAX_IMAGES:
        return None
    for ext, mime in _MIME.items():
        p = Path(img_dir) / ("%s_%d.%s" % (rid, int(n), ext))
        if p.is_file():
            return mime, p.read_bytes()
    return None
