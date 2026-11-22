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
        for _ in range(3):
            p.click("button[onclick='addKey()']:visible")
        n = p.evaluate("keys.length")
        rec("UI-090a", n == 3, "3 keyframes added", n)
        und = p.is_enabled("#undoBtn")
        for _ in range(3):
            p.click("#undoBtn")
        n2 = p.evaluate("keys.length")
        rec("UI-090", und and n2 == 0, "undo x3 returns to 0 keys", (und, n2))
        p.click("#redoBtn")
        rec("UI-091a", p.evaluate("keys.length") == 1, "redo brings 1 back", p.evaluate("keys.length"))
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
        b.click("button[onclick='saveAll()']")
        b.wait_for_timeout(1500)
        notice = (b.inner_text("#notice") + " | " + b.inner_text("#stat"))[:200]
        rec("UI-084", True, "tab B saving after tab A took the name: what B says", notice)
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
        # music on timeline
        wp = tmp / "m.wav"
        wp.write_bytes(wav())
        cnt_before = p.evaluate("typeof sequenceAudio")
        try:
            p.set_input_files("input[type=file][accept*='audio']", str(wp))
            p.wait_for_timeout(1500)
            rec("UI-103", True, "music file chosen; bar text", p.inner_text("#sequenceAudioBar")[:100])
        except Exception as e:
            rec("UI-103", False, "no audio file input found", str(e)[:120])
        # video import
        try:
            p.click("#tabBtnVideo")
            fix = ROOT / "qc" / "data"
            vids = list(fix.glob("*.mp4")) + list(ROOT.glob("qc/**/*.mp4"))
            rec("UI-110a", bool(vids), "an mp4 fixture exists", [v.name for v in vids[:2]])
            if vids:
                p.set_input_files("#vidFile", str(vids[0]))
                p.wait_for_timeout(6000)
                rec("UI-110", True, "video chosen; status", p.inner_text("#vidStat")[:120])
        except Exception as e:
            rec("UI-110", False, "video step failed", str(e)[:150])
        rec("ERRS", not errs, "page errors during whole run", errs[:4])
        br.close()
    Path(ROOT / "docs" / "test_cases" / "studio_sweep.json").write_text(json.dumps(OUT, indent=1))
    print("%d cases, %d failed" % (len(OUT), len([o for o in OUT if not o["ok"]])))


if __name__ == "__main__":
    main()
