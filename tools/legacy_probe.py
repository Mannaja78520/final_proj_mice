"""Chrome 75 (Android TV) user agent against the hub pages: which file is served, does it start.

    python tools/legacy_probe.py

Not a real Chrome 75: modern Edge with the old UA string. It proves the SERVING
rule (legacy bundles) and that nothing throws on load; syntax Chrome 75 cannot
parse needs the E:\tv-sim VM (hung 2026-11-22, see results file).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "qc" / "lib"))
import qc as F  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

UA = "Mozilla/5.0 (Linux; Android 9; AFTMM Build/PS7233) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36"
OUT = []
base, _ = F.start_hub()
with sync_playwright() as pw:
    br = pw.chromium.launch(channel="msedge", headless=True)
    ctx = br.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
    for path in ("/", "/studio/", "/app/voice/", "/app/gacha/", "/app/tv/", "/app/camera/", "/help"):
        pg = ctx.new_page()
        errs, scripts = [], []
        pg.on("pageerror", lambda e: errs.append(str(e)[:100]))
        pg.on("response", lambda r: scripts.append(r.url.rsplit("/", 1)[-1]) if r.url.endswith((".js", ".html")) else None)
        pg.goto(base + path, wait_until="load")
        pg.wait_for_timeout(1500)
        legacy = [s for s in scripts if "legacy" in s]
        modern = [s for s in scripts if s in ("app.js", "app-voice.js")]
        OUT.append({"path": path, "errors": errs, "legacy_files": legacy, "modern_app_js": modern})
        print(("%s errs=%s legacy=%s modern=%s" % (path, errs[:2], legacy, modern)).encode("ascii", "replace").decode(), flush=True)
        pg.close()
    import re
    for path in ("/studio/app.js", "/studio/", "/app/voice/app.js", "/app/voice/", "/app/tv/", "/app/gacha/", "/app/camera/"):
        old = ctx.request.get(base + path, headers={"User-Agent": UA}).text()
        new = ctx.request.get(base + path, headers={"User-Agent": "Mozilla/5.0 Chrome/120.0 Safari/537.36"}).text()
        bad = len(re.findall(r"\?\.(?![0-9])|\?\?(?!=)", old))
        bad_new = len(re.findall(r"\?\.(?![0-9])|\?\?(?!=)", new))
        row = {"path": path, "differs_from_modern": old != new, "optional_chaining_or_nullish_old_ua": bad, "same_in_modern": bad_new}
        OUT.append(row)
        print("/".join(["LEG", path]), row, flush=True)
    br.close()
(ROOT / "docs" / "test_cases" / "legacy_probe.json").write_text(json.dumps(OUT, indent=1))
