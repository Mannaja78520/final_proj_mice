"""Every var(--token) any served style names must be defined somewhere.

A token nobody defines resolves to nothing: the declaration is dropped and the
control silently wears whatever it inherited. .pin asked for --muted and --fg
for weeks while every theme defines --mut and --txt, so pin buttons rendered
as ordinary text and their hover did nothing. A rename or a typo is invisible
exactly like that — no console error, nothing.

A use WITH a fallback (`var(--x, #fff)`) is exempt: the fallback is the point.
"""
import re

import qc as F

AREA = "design"
TITLE = "every token a style names is one a theme defines"

DEF_RE = re.compile(r"(--[a-z0-9-]+)\s*:")          # --name: value  = definition
USE_RE = re.compile(r"var\((--[a-z0-9-]+)\s*(,)?")


def _inline_styles(text):
    return "\n".join(m.group(1)
                     for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S))


# Shared stylesheets first — every page links them.
SHARED = ("themes.css", "mice.css")

# Pages carrying their own <style> blocks. WebUI.h is the module website as a
# C++ raw string; its CSS is served verbatim, so scanning the source text is
# scanning what ships.
PAGES = (
    F.HUB / "web" / "hub.html",
    F.HUB / "web" / "rgb.html",
    F.HUB / "web" / "help.html",
    F.FIRMWARE / "src" / "web" / "WebUI.h",
    F.STUDIO_WEB / "index.html",
    F.STUDIO_WEB / "style.css",
) + tuple((F.CODE / "apps").glob("*/index.html"))


def run(t):
    defined, used = set(), {}
    shared_dir = F.CODE / "shared" / "web"
    for name in SHARED:
        css = (shared_dir / name).read_text(encoding="utf-8")
        defined |= set(DEF_RE.findall(css))
        for tok, fallback in USE_RE.findall(css):
            if not fallback:                    # var(--x, fallback) is exempt
                used.setdefault(tok, "shared/web/" + name)

    for path in PAGES:
        block = _inline_styles(path.read_text(encoding="utf-8", errors="replace"))
        defined |= set(DEF_RE.findall(block))
        for tok, fallback in USE_RE.findall(block):
            if not fallback:
                used.setdefault(tok, path.name)

    missing = sorted(tok for tok in used if tok not in defined)
    t.ok(not missing,
         "every var(--token) used is defined somewhere",
         "%s resolve to nothing (first used in %s)"
         % (", ".join(missing[:10]), ", ".join(used[m] for m in missing[:10])))
