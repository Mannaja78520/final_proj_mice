"""A saved YAML can be deleted from Studio, and a mis-click is recoverable.

Asked 2026-09-17: *make can edit and delete the yaml too*. Editing was already
Load for editing + Save YAML over the same name. Delete moves the file to
sequences/.deleted/ (never erases it), needs a login, and drops it from the list.
"""
import json

import qc as F

AREA = "studio"
TITLE = "a saved YAML can be deleted, needs a login, and is kept aside"


def run(t):
    base, main = F.start_hub()
    seq = main.SEQUENCES
    seq.mkdir(exist_ok=True)
    f = seq / "qc_delete_me.yaml"
    f.write_text("name: qc\nkeys:\n  - pose: 90 90 90 90 90 90 90 90 90 90 T 500\n",
                 encoding="utf-8")
    body = json.dumps({"name": f.name}).encode()
    kept = []
    try:
        F.logout_qc()
        s, _ = F.post(base + "/api/seqdelete", body)
        t.eq(s, 401, "deleting a saved show needs a login")
        t.ok(f.is_file(), "and a refused delete leaves the file alone")

        F.login(base)
        s, b = F.post(base + "/api/seqdelete", body)
        t.eq(s, 200, "logged in, the delete is accepted")
        t.ok(not f.is_file(), "the file is gone from sequences/")
        kept = list((seq / ".deleted").glob("*_" + f.name))
        t.ok(kept, "but kept in sequences/.deleted, not erased", b)
        s, lst = F.get(base + "/api/list?kind=sequences")
        t.ok(f.name not in lst, "and the saved list no longer offers it", lst)

        s, _ = F.post(base + "/api/seqdelete", json.dumps({"name": "../main.py"}).encode())
        t.ok(s == 404 and (main.HERE / "main.py").is_file(),
             "a path outside sequences/ cannot be deleted", s)
    finally:
        for p in kept + [f]:
            try:
                p.unlink()
            except OSError:
                pass

    js = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    html = (F.STUDIO_WEB / "index.html").read_text(encoding="utf-8", errors="replace")
    t.ok("deleteLocalSeq()" in html and "/api/seqdelete" in js,
         "Studio has a Delete button that calls it")
