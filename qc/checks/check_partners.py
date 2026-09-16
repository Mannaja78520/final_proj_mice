"""Outside programs are entries in one file, not code.

Asked 2026-09-08: *make can add more app than this in the future, not only
face reconize, make it dynamic to easy to add.* So Reconize is the FIRST ENTRY
in `config/partners.json`, never a special case, and the second program costs
one entry and no code. This check is what makes that claim testable rather
than a promise: it adds a partner of its own and asserts the hub lists it.

WHAT EACH RULE IS PAYING FOR

  * **A source says what it can NOT tell us.** Reconize's two sources have
    opposite holes, both read out of their code on 2026-09-10:
      - the live feed carries a camera (`node_id`) but NEVER a stranger. Two
        guards drop them: `api/nodes.py:331` publishes only when the status is
        `matched`, and `api/recognition.py:130` only `if person_id`.
      - the history poll carries strangers but NO camera at all: the row is
        built at `api/history.py:71-84` out of id, upload_id, upload_filename,
        person_id, name, participant_id, confidence, status, detected_at.
    So `reports` and `hasCamera` are declared per source, and a source may not
    claim a camera in its field map while saying it has none. Getting this
    wrong is how the rig greets a stranger by the wrong door's words.

  * **A poll must declare its lag window.** Their `detected_at` is stamped when
    the row is BUILT, not when it commits (`models/models.py:64`,
    `default_factory=datetime.now`), so an older-looking row can land after a
    newer one. A cursor that trusts the newest time it has seen silently drops
    people. The window plus a seen-set is what stops that.

  * **No password lives here.** `config/` is not served, but this file is read
    by things that are - and the standing rule in this project is that a login
    lives beside `hub_auth.json`, out of the served tree, out of promotion and
    out of the exe.
"""
import json
import sys

import qc as F


AREA = "registries"
TITLE = "an outside program is one entry, and the next one needs no code"

CFG = "config/partners.json"
NEEDED = ("name", "open", "api", "health", "folder", "login", "events")
SECRET_HINTS = ("password", "passwd", "secret", "token", "jwt", "apikey",
                "api_key", "credential")


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                          # noqa: E402

    raw = (F.CODE / CFG).read_text(encoding="utf-8")
    partners = json.loads(registry.strip_jsonc(raw))
    t.ok("reconize" in partners,
         "the face app is an entry in %s" % CFG, sorted(partners))

    for pid, p in sorted(partners.items()):
        for key in NEEDED:
            t.ok(p.get(key), "%s says its %s" % (pid, key), sorted(p))

        # ---- a source declares what it cannot deliver ------------------
        for src in p.get("events", []):
            where = "%s/%s" % (pid, src.get("kind"))
            t.ok(src.get("reports"),
                 "%s says which people it can report" % where,
                 "a source that does not say is a source the rig will believe "
                 "about people it never sees: %s" % src)
            t.ok("hasCamera" in src,
                 "%s says whether it carries a camera" % where,
                 "greeting per camera needs to know; guessing means the wrong "
                 "door's words, or a greeting from a camera that only watches")
            if not src.get("hasCamera"):
                t.ok("camera" not in (src.get("map") or {}),
                     "%s claims no camera, and maps none" % where,
                     "a map naming a field the payload does not carry is a "
                     "promise the source cannot keep: %s" % src.get("map"))
            if src.get("kind") == "poll":
                t.ok(src.get("lagSeconds"),
                     "%s declares how far behind its cursor it re-reads" % where,
                     "their detected_at is stamped before the row commits "
                     "(models/models.py:64), so a cursor at the newest time "
                     "seen drops rows that land late - and drops the person")

        # ---- and never a login -----------------------------------------
        flat = json.dumps(p).lower()
        leaked = [h for h in SECRET_HINTS
                  if ('"%s"' % h) in flat and h != "jwt"]
        t.eq(leaked, [],
             "%s keeps no login in the registry" % pid)

    # ---- THE TEST: add a partner, with no code change ------------------
    # The same shape check_registries uses for apps, and for the same reason:
    # the promise is *the next one is an entry*, and only adding one proves it.
    base, _main = F.start_hub()
    code, body = F.get(base + "/api/partners")
    t.eq(code, 200, "the hub lists its partners, with no login")
    listed = json.loads(body)
    t.ok(listed.get("ok"), "and says the list was read", listed)
    t.ok("reconize" in (listed.get("partners") or {}),
         "with the face app in it", sorted(listed.get("partners") or {}))

    path = F.CODE / CFG
    before = path.read_text(encoding="utf-8")
    try:
        extra = json.loads(registry.strip_jsonc(before))
        extra["_qc_tmp"] = {
            "name": "QC temp partner", "open": "http://127.0.0.1:1",
            "api": "http://127.0.0.1:2", "health": "/health",
            "folder": ".", "login": {"kind": "none"},
            "events": [{"kind": "poll", "path": "/x", "items": "items",
                        "reports": ["known"], "hasCamera": False,
                        "map": {"who": "name"}, "lagSeconds": 60}],
        }
        path.write_text(json.dumps(extra, indent=2), encoding="utf-8")
        code, body = F.get(base + "/api/partners")
        got = json.loads(body).get("partners") or {}
        t.ok("_qc_tmp" in got,
             "a NEW partner appears from one entry, with no code change and "
             "no restart",
             "that is the whole promise of this file: %s" % sorted(got))
        t.eq(got.get("_qc_tmp", {}).get("name"), "QC temp partner",
             "and it is read as written")
    finally:
        path.write_text(before, encoding="utf-8")

    # ---- a broken file says so, and lists nothing ----------------------
    try:
        path.write_text("{ not json", encoding="utf-8")
        code, body = F.get(base + "/api/partners")
        t.eq(code, 200, "a broken partners file still answers, not a 500")
        bad = json.loads(body)
        t.eq(bad.get("partners"), {}, "and lists nothing rather than guessing")
        t.ok(bad.get("ok") is False and CFG in (bad.get("error") or ""),
             "while naming the file to fix",
             "a screen that says nothing leaves a designer with nowhere to "
             "look: %r" % bad.get("error"))
    finally:
        path.write_text(before, encoding="utf-8")
