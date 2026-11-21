"""Pages must hand back what they borrow: blob URLs and GPU buffers.

Found 2026-11-21 (leak hunt): Voice's say() revoked its audio blob URL only
in `onended`. The blocked-sound path replaces onended and a failed play()
never ends, so each such answer stayed in memory until the tab closed. Studio's
clearGizmo() removed the joint rings without disposing their geometry and
material (the runtime half of that is in check_studio_leak).

Static half: a page source that creates an object URL must release it from an
event that also fires on failure, and the ring gizmo must dispose what it builds.
"""
import qc as F

AREA = "tools"
TITLE = "pages release blob URLs and ring gizmos (no tab-lifetime leaks)"


def run(t):
    voice = (F.CODE / "apps/voice/app.js").read_text(encoding="utf-8", errors="replace")
    i = voice.find('fetch("/api/voice/say"')
    if t.ok(i >= 0, "voice say() found"):
        body = voice[i:i + 3200]
        t.contains(body, 'addEventListener("error", freeUrl)',
                   "the answer's blob URL is freed when playback fails")
        t.contains(body, 'addEventListener("ended", freeUrl)',
                   "and when it ends, even after onended was replaced")
    for p in ("apps/voice/app.js", "apps/camera/app.js"):
        s = (F.CODE / p).read_text(encoding="utf-8", errors="replace")
        t.ok(s.count("createObjectURL") <= s.count("revokeObjectURL"),
             p + ": every object URL has a revoke",
             "%d created, %d revoked" % (s.count("createObjectURL"), s.count("revokeObjectURL")))
    g = (F.CODE / "nong/main_python_set_nong/web/app_parts/gizmo_rings.js").read_text(
        encoding="utf-8", errors="replace")
    j = g.find("function clearGizmo")
    t.ok(j >= 0 and "geometry.dispose()" in g[j:j + 700] and "material.dispose()" in g[j:j + 700],
         "clearGizmo disposes ring geometry and material",
         "removing a mesh from the scene does not free its GPU buffers")
