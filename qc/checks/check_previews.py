"""Trial looks sit next to the real page and never change it (A47-17).

User 2026-10-23: try Studio with another tab style and Help split by topic,
"เปิดเป็น dummy เดี่ยวเข้าไปดูแยกว่าจะเอาไม่เอา". Each trial in
main_python/web/previews/previews.json is served at its own address:

  * the trial page is the real page with the trial's files linked in, and a
    strip saying it is a trial with a link back to the real page;
  * the real page comes back byte for byte as it is on disk (no trial in it);
  * every file a trial adds is served by the hub, so nothing 404s.
"""
import json

import qc as F

AREA = "design"
TITLE = "trial looks are their own pages; the real pages are untouched"


def run(t):
    reg = json.loads((F.CODE / "main_python" / "web" / "previews" / "previews.json").read_text(encoding="utf-8"))
    base, main = F.start_hub()
    roots = {"studio": F.CODE / "nong" / "main_python_set_nong" / "web", "hub": F.CODE / "main_python" / "web"}
    # No trial open right now is fine (Help and Studio were kept, A49-1/A49-3);
    # the shared strip stays for the next one.
    t.ok(isinstance(reg.get("previews"), list) and (F.CODE / "main_python" / "web" / "previews" / "trial_bar.js").is_file(),
         "the list of trials reads, and the shared trial strip is there for the next one", reg.get("previews"))
    for p in reg["previews"]:
        code, page = F.get(base + p["path"])
        added = all(("/hubweb/previews/" + f) in page for f in p["add"])
        t.ok(code == 200 and added and 'data-real="%s"' % p["real"] in page and "trial_bar.js" in page,
             "%s is the trial: its files and the way back to %s" % (p["path"], p["real"]), (code, page[-400:]))
        code, real = F.get(base + p["real"])
        disk = (roots[p["root"]] / p["from"]).read_text(encoding="utf-8")
        t.ok(code == 200 and real == disk and "/hubweb/previews/" not in real,
             "%s is still the real page, exactly as on disk" % p["real"], code)
        for f in p["add"]:
            code, _ = F.get(base + "/hubweb/previews/" + f)
            t.ok(code == 200, "%s's file %s is served" % (p["path"], f), code)
