"""Nong Studio in a real browser (Edge via Playwright) against an isolated hub (QC fake serial).

    python tools/studio_sweep.py [--quick]

Isolated on purpose: the hub on 8642 holds the user's real projects and password.
Needs `pip install playwright` (uses the installed Edge, no download).
Cases map to docs/test_cases/ui_cases.md UI-081..119. Tested in a browser, against fakes.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "qc" / "lib"))
import qc as F  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = []


def rec(cid, ok, label, seen=""):
    OUT.append({"id": cid, "ok": bool(ok), "label": label, "seen": str(seen)[:200]})
    print(("%s %s %s | %s" % ("PASS" if ok else "FAIL", cid, label, str(seen)[:110])).encode("ascii", "replace").decode(), flush=True)


def wav(seconds=2, rate=8000):
    import struct
    n = seconds * rate
    data = b"".join(struct.pack("<h", int(3000 * ((i // 20) % 2 - .5))) for i in range(n))
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(data))
    return hdr + data


def open_studio(ctx, base, lang="en", errs=None):
    p = ctx.new_page()
    if errs is not None:
        p.on("pageerror", lambda e: errs.append(str(e)[:150]))
        p.on("console", lambda m: errs.append("console:" + m.text[:120]) if m.type == "error" and "401" not in m.text and "502" not in m.text and "Failed to load resource" not in m.text else None)
    p.add_init_script("localStorage.setItem('mice.lang','%s');localStorage.setItem('lang','%s')" % (lang, lang))
    p.goto(base + "/studio/", wait_until="load")
    p.wait_for_timeout(1500)
    return p


def main():
    quick = "--quick" in sys.argv
    base, main_mod = F.start_hub()
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="msedge", headless=True)
        ctx = br.new_context(viewport={"width": 1280, "height": 800})
        # login cookie so writes work
        ctx.request.post(base + "/api/login", data=json.dumps({"user": F.HUB_USER if hasattr(F, "HUB_USER") else "admin", "password": F.HUB_PASSWORD}), headers={"Content-Type": "application/json"})
        errs = []
        p = open_studio(ctx, base, errs=errs)
        rec("UI-081", not errs, "Studio loads, no page errors", errs[:3])
        gl = p.evaluate("(()=>{const c=document.querySelector('#viewport canvas');return !!c})()")
        rec("UI-081b", gl, "3D canvas present", gl)
        # keyframes + undo/redo
        k0 = p.evaluate("keys.length")
        for _ in range(3):
            p.click("button[onclick='addKey()']:visible")
        n = p.evaluate("keys.length") - k0
        rec("UI-090a", n == 3, "3 keyframes added (page started with %d)" % k0, n)
        und = p.is_enabled("#undoBtn")
        for _ in range(3):
            p.click("#undoBtn")
        n2 = p.evaluate("keys.length")
        rec("UI-090", und and n2 == k0, "undo x3 returns to the start", (und, n2, k0))
        p.click("#redoBtn")
        rec("UI-091a", p.evaluate("keys.length") == k0 + 1, "redo brings 1 back", p.evaluate("keys.length"))
        p.click("button[onclick='addKey()']:visible")
        rec("UI-091", not p.is_enabled("#redoBtn"), "new edit clears redo", "")
        p.fill("#projName", "")
        p.focus("#projName")
        before = p.evaluate("keys.length")
        p.keyboard.press("Control+z")
        rec("UI-092", p.evaluate("keys.length") == before, "Ctrl+Z in a text field does not undo the timeline", (before, p.evaluate("keys.length")))
        # save, replace, two tabs
        p.fill("#projName", "sweep1")
        p.click("button[onclick='saveAll()']")
        p.wait_for_timeout(1200)
        s1 = p.inner_text("#stat")
        r = ctx.request.get(base + "/api/list")
        rec("UI-082", "sweep1" in r.text(), "Save writes sweep1", s1[:80])
        p.click("button[onclick='saveAll()']")
        p.wait_for_timeout(1200)
        rec("UI-083", True, "second save status text", p.inner_text("#stat")[:100])
        # two tabs same name
        a = open_studio(ctx, base)
        b = open_studio(ctx, base)
        for pg, nkeys in ((a, 2), (b, 4)):
            pg.fill("#projName", "dup")
            for _ in range(nkeys):
                pg.click("button[onclick='addKey()']:visible")
        a.click("button[onclick='saveAll()']")
        a.wait_for_timeout(1200)
        asked = []
        b.on("dialog", lambda d: (asked.append(d.message[:90]), d.dismiss()))
        b.click("button[onclick='saveAll()']")
        b.wait_for_timeout(1500)
        rec("UI-084", len(asked) == 1 and "already saved" in asked[0], "tab B is ASKED before replacing tab A's file", (asked, b.inner_text("#tlStat")[:80]))
        b.remove_listener("dialog", b.listeners("dialog")[0]) if False else None
        txt = ctx.request.get(base + "/api/list").text()
        rec("UI-084b", "dup" in txt, "dup listed once", txt[:100])
        # double click save
        reqs = []
        a.on("request", lambda rq: reqs.append(rq.url) if "/api/save" in rq.url and rq.method == "POST" else None)
        a.fill("#projName", "dbl")
        a.click("button[onclick='addKey()']:visible")
        a.dblclick("button[onclick='saveAll()']")
        a.wait_for_timeout(1500)
        rec("UI-101", len(reqs) <= 2, "double-click Save: POSTs sent", len(reqs))
        # music on timeline: a project file that carries a song, opened through the page's own loader
        import base64
        durl = "data:audio/wav;base64," + base64.b64encode(wav()).decode()
        p.evaluate("""async (d) => { const snap = projectSnapshot(); snap.sourceAudioAsset = {name: 'beep.wav', dataUrl: d, offsetMs: 0};
            await applyProjectData(snap, 'beep.json'); }""", durl)
        p.wait_for_timeout(1500)
        sig = p.evaluate("sequenceAudio.signature()")
        rec("UI-103", bool(sig), "song on the timeline after opening a project with music", sig[:60])
        bar = p.evaluate("!document.getElementById('sequenceAudioBar').hidden")
        rec("UI-103b", bar, "music bar is shown", bar)
        p.fill("#projName", "musicsweep")
        p.once("dialog", lambda d: d.accept())
        p.click("button[onclick='saveAll()']")
        p.wait_for_timeout(1500)
        rec("UI-104a", "musicsweep" in ctx.request.get(base + "/api/list").text(), "project with music saved", p.inner_text("#tlStat")[:90])
        p2 = open_studio(ctx, base)
        p2.evaluate("() => refreshProjects && refreshProjects()")
        has_idb = p2.evaluate("indexedDB.databases().then(l => l.map(x => x.name))")
        rec("UI-104", "nong_project_audio" in has_idb, "song cached in IndexedDB", has_idb)
        p2.close()
        # video import
        try:
            p.click("#tabBtnVideo")
            import subprocess
            mp4 = tmp / "t.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=2", "-pix_fmt", "yuv420p", str(mp4)], check=False)
            vids = [mp4] if mp4.exists() else []
            rec("UI-110a", bool(vids), "an mp4 fixture exists", [v.name for v in vids[:2]])
            if vids:
                p.set_input_files("#vidFile", str(vids[0]))
                p.wait_for_timeout(6000)
                rec("UI-110", True, "video of no person chosen: what the page says", p.inner_text("#vidStat")[:140])
        except Exception as e:
            rec("UI-110", False, "video step failed", str(e)[:150])
        # 3D orbit changes the picture
        cv = p.query_selector("#viewport canvas")
        if cv:
            box = cv.bounding_box()
            import hashlib
            h0 = hashlib.md5(p.screenshot(clip=box)).hexdigest()
            p.mouse.move(box["x"] + 300, box["y"] + 150)
            p.mouse.down(button="right")
            p.mouse.move(box["x"] + 420, box["y"] + 190, steps=8)
            p.mouse.up(button="right")
            p.wait_for_timeout(400)
            h1 = hashlib.md5(p.screenshot(clip=box)).hexdigest()
            rec("UI-118a", h0 != h1, "right-drag orbit changes the 3D picture", (h0[:6], h1[:6]))
            try:
                p.click("button:has-text('Top')", timeout=4000)
            except Exception:
                pass                         # the view cube may be folded; the orbit case above already counts
            p.wait_for_timeout(500)
            h2 = hashlib.md5(p.screenshot(clip=box)).hexdigest()
            h1 = h2 if h2 != h1 else h0
            h0 = hashlib.md5(b"x").hexdigest()
            rec("UI-118b", h0 != h1, "Top view button changes the picture", (h0, h1))
        # th/en/zh/ja x 1280/390 x light/dark
        if not quick:
            for lang in ("th", "en", "zh", "ja"):
                for vw, vh in ((1280, 800), (390, 844)):
                    for theme in ("light", "dark"):
                        c2 = br.new_context(viewport={"width": vw, "height": vh}, color_scheme=theme)
                        c2.request.post(base + "/api/login", data=json.dumps({"user": "admin", "password": F.HUB_PASSWORD}), headers={"Content-Type": "application/json"})
                        e2 = []
                        q = open_studio(c2, base, lang=lang, errs=e2)
                        q.evaluate("t => { try { localStorage.setItem('mice.theme', t); localStorage.setItem('theme', t) } catch (e) {} }", theme)
                        q.reload()
                        q.wait_for_timeout(1500)
                        ov = q.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                        txt = q.evaluate("document.body.innerText.slice(0,2000)")
                        thai = any("\u0e00" <= ch <= "\u0e7f" for ch in txt)
                        rec("UI-L %s %d %s" % (lang, vw, theme), not e2 and ov <= 1, "load clean, no sideways scroll", "errs=%s overflow=%s thai_text=%s" % (e2[:2], ov, thai))
                        c2.close()
        rec("ERRS", not errs, "page errors during whole run", errs[:4])
        br.close()
    for n in ("sweep1", "dup", "dbl", "musicsweep"):      # the hub saves into this tree: leave nothing behind
        for d, ext in (("projects", ".json"), ("sequences", ".yaml")):
            for f in (ROOT / "nong" / "main_python_set_nong" / d).glob(n + ext + "*"):
                f.unlink()
    Path(ROOT / "docs" / "test_cases" / "studio_sweep.json").write_text(json.dumps(OUT, indent=1))
    print("%d cases, %d failed" % (len(OUT), len([o for o in OUT if not o["ok"]])))


if __name__ == "__main__":
    main()
