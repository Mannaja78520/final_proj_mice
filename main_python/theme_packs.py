"""Theme packs: a colour set plus its pictures, installed like an extension.

User 2026-11-23: themes should work like VS Code extensions - install one, then
press Use. A pack is a folder (or a .zip of it) with ONE file, theme.json:

    {"id": "cloudy", "name": {"en": "Cloudy", "th": "..."}, "note": "...",
     "mode": "light" | "dark",
     "colors": {"bg": "#rrggbb", "card": ..., "txt": ..., ...},
     "images": {"apps/tv": "tv.svg"},     # optional: swap a picture by name
     "art": "clouds.svg",                  # optional: a soft page background
     "shape": {"r-md": "18px"}}            # optional: rounder corners

`mode` is how the page picks the matching picture set: a dark theme gets
`name.dark.webp` when it exists, a light one the plain file.
Built-in packs live in shared/web/themes/, installed ones beside hub_auth.json
(never in git). Both are read by this one class. The pack becomes one CSS block
(`:root[data-theme=<id>]`), so the picker on every page finds it with no list.
A pack that fails the contrast floors is refused at install, with the number.
"""
import io
import json
import re
import shutil
import zipfile
from pathlib import Path

REQUIRED = ("bg", "card", "sunk", "line", "txt", "mut", "acc", "on-acc", "btn",
            "ok", "warn", "err")
OPTIONAL = ("ty-nong", "ty-lift", "ty-cam", "ty-other")
# Same floors as qc/checks/check_themes.py; AA for text everywhere.
MIN_TEXT, MIN_MUTED, MIN_ACCENT, MIN_ON_ACC = 7.0, 4.5, 4.5, 4.5
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ID = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
FILE = re.compile(r"^[\w][\w.-]{0,63}$")
IMG_EXT = (".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif")
MAX_PACK = 4 * 1024 * 1024
RESERVED = {"indigo", "midnight", "daylight", "carnival"}


def _lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class ThemePackError(ValueError):
    pass


class ThemePacks:
    def __init__(self, builtin_dir, user_dir):
        self.builtin = Path(builtin_dir)
        self.user = Path(user_dir)

    # ---- reading ---------------------------------------------------------
    def _read(self, folder, source):
        try:
            cfg = json.loads((folder / "theme.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        try:
            self.validate(cfg, folder)
        except ThemePackError:
            return None
        cfg["source"] = source
        return cfg

    def all(self):
        out, seen = [], set()
        for root, source in ((self.builtin, "builtin"), (self.user, "installed")):
            if not root.is_dir():
                continue
            for folder in sorted(p for p in root.iterdir() if p.is_dir()):
                cfg = self._read(folder, source)
                if cfg and cfg["id"] not in seen and cfg["id"] == folder.name:
                    seen.add(cfg["id"])
                    out.append(cfg)
        return out

    def listing(self):
        return [{"id": c["id"], "name": c["name"], "note": c.get("note", ""),
                 "mode": c["mode"], "source": c["source"],
                 "colors": {k: c["colors"][k] for k in ("bg", "card", "txt", "acc", "ok", "warn", "err")}}
                for c in self.all()]

    # ---- checking --------------------------------------------------------
    def validate(self, cfg, folder=None):
        if not isinstance(cfg, dict):
            raise ThemePackError("theme.json must be an object")
        if not ID.match(str(cfg.get("id", ""))):
            raise ThemePackError("id must be lowercase letters, digits and dashes")
        if cfg["id"] in RESERVED and (folder is None or folder.parent != self.builtin):
            raise ThemePackError("this id is used by a built-in theme")
        name = cfg.get("name")
        if isinstance(name, str):
            cfg["name"] = name = {"en": name}
        if not isinstance(name, dict) or not str(name.get("en", "")).strip():
            raise ThemePackError("name needs at least an English name")
        if cfg.get("mode") not in ("light", "dark"):
            raise ThemePackError('mode must be "light" or "dark"')
        colors = cfg.get("colors")
        if not isinstance(colors, dict):
            raise ThemePackError("colors is missing")
        for k in REQUIRED:
            if not HEX.match(str(colors.get(k, ""))):
                raise ThemePackError("colour %s must look like #1a2b3c" % k)
        for k in OPTIONAL:
            colors.setdefault(k, colors["mut"] if k == "ty-other" else colors["acc"])
            if not HEX.match(str(colors[k])):
                raise ThemePackError("colour %s must look like #1a2b3c" % k)
        c = colors
        for ground in ("bg", "card"):
            for key, floor in (("txt", MIN_TEXT), ("mut", MIN_MUTED)):
                r = contrast(c[key], c[ground])
                if r < floor:
                    raise ThemePackError("text colour %s on %s is %.1f:1, needs %.1f:1 so it stays readable"
                                         % (key, ground, r, floor))
        r = contrast(c["acc"], c["bg"])
        if r < MIN_ACCENT:
            raise ThemePackError("accent on background is %.1f:1, needs %.1f:1" % (r, MIN_ACCENT))
        r = contrast(c["on-acc"], c["acc"])
        if r < MIN_ON_ACC:
            raise ThemePackError("button text on accent is %.1f:1, needs %.1f:1" % (r, MIN_ON_ACC))
        for st in ("ok", "warn", "err"):
            r = contrast(c[st], c["card"])
            if r < 3.0:
                raise ThemePackError("state colour %s on card is %.1f:1, needs 3:1" % (st, r))
        for k, v in (cfg.get("shape") or {}).items():
            if k not in ("r-sm", "r-md", "r-lg") or not re.match(r"^\d{1,2}px$", str(v)):
                raise ThemePackError("shape may only set r-sm, r-md, r-lg as 12px")
        for rel in self.files(cfg):
            if not FILE.match(rel) or not rel.lower().endswith(IMG_EXT):
                raise ThemePackError("picture file name not allowed: %s" % rel)
            if folder is not None and not (folder / rel).is_file():
                raise ThemePackError("picture file is missing: %s" % rel)

    @staticmethod
    def files(cfg):
        imgs = cfg.get("images") or {}
        if not isinstance(imgs, dict):
            raise ThemePackError("images must map a picture name to a file")
        names = [str(v) for v in imgs.values()]
        if cfg.get("art"):
            names.append(str(cfg["art"]))
        return names

    # ---- the CSS ---------------------------------------------------------
    def css(self):
        out = []
        for c in self.all():
            sel = ':root[data-theme="%s"]' % c["id"]
            en = c["name"]["en"].replace('"', "'")
            note = str(c.get("note", "")).replace('"', "'")
            body = ['--theme-name:"%s";' % en, '--theme-note:"%s";' % note,
                    '--theme-mode:"%s";' % c["mode"]]
            body += ["--%s:%s;" % (k, c["colors"][k]) for k in REQUIRED + OPTIONAL]
            for k, v in (c.get("shape") or {}).items():
                body.append("--%s:%s;" % (k, v))
            body.append("color-scheme:%s;" % c["mode"])
            out.append("%s{%s}" % (sel, "".join(body)))
            if c.get("art"):
                out.append('%s body{background-image:url("/themes/%s/%s");'
                           'background-attachment:fixed;background-size:cover}'
                           % (sel, c["id"], c["art"]))
        return "\n".join(out) + "\n"

    def images(self, theme_id):
        for c in self.all():
            if c["id"] == theme_id:
                return {k: "/themes/%s/%s" % (theme_id, v) for k, v in (c.get("images") or {}).items()}
        return {}

    def file(self, theme_id, rel):
        """(bytes, ext) of one picture of a pack, or None. Only files the pack names."""
        for c in self.all():
            if c["id"] == theme_id and rel in self.files(c):
                root = (self.builtin if c["source"] == "builtin" else self.user) / theme_id
                f = root / rel
                if f.is_file():
                    return f.read_bytes(), f.suffix.lower()
        return None

    # ---- installing ------------------------------------------------------
    def install(self, data):
        """Install a pack from the bytes of a .zip or a bare theme.json."""
        if len(data) > MAX_PACK:
            raise ThemePackError("the pack is bigger than 4 MB")
        files = {}
        if data[:2] == b"PK":
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
            except zipfile.BadZipFile:
                raise ThemePackError("this is not a theme pack")
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                base = name.rsplit("/", 1)[-1]
                if info.is_dir() or not base or name.startswith("/") or ".." in name.split("/"):
                    continue
                if info.file_size > MAX_PACK:
                    raise ThemePackError("a file in the pack is too big")
                files[base] = zf.read(info)
        else:
            files["theme.json"] = data
        if "theme.json" not in files:
            raise ThemePackError("theme.json not found in the pack")
        try:
            cfg = json.loads(files["theme.json"].decode("utf-8-sig"))
        except ValueError:
            raise ThemePackError("theme.json is not valid JSON")
        self.validate(cfg)
        for rel in self.files(cfg):
            if rel not in files:
                raise ThemePackError("picture file is missing: %s" % rel)
            if rel.lower().endswith(".svg") and re.search(rb"<script|on\w+\s*=|javascript:", files[rel], re.I):
                raise ThemePackError("the SVG picture %s has active content" % rel)
        if any(b.get("id") == cfg["id"] for b in self._builtin_ids()):
            raise ThemePackError("this id is used by a built-in theme")
        dest = self.user / cfg["id"]
        self.user.mkdir(parents=True, exist_ok=True)
        tmp = self.user / (".tmp-" + cfg["id"])
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        (tmp / "theme.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        for rel in self.files(cfg):
            (tmp / rel).write_bytes(files[rel])
        shutil.rmtree(dest, ignore_errors=True)
        tmp.rename(dest)
        return cfg["id"]

    def _builtin_ids(self):
        return [c for c in self.all() if c["source"] == "builtin"]

    def remove(self, theme_id):
        if not ID.match(theme_id or ""):
            raise ThemePackError("no such theme")
        dest = self.user / theme_id
        if not dest.is_dir():
            raise ThemePackError("only installed themes can be removed")
        shutil.rmtree(dest)
