"""Odd data sent to the hub is answered with plain words, never a crash message.

Found 2026-11-21 (odd-input sweep): 90 of ~1000 weird requests (empty body, JSON
`null` or a list, bytes that are not UTF-8, a name that is not allowed, a missing
field) came back HTTP 500 with raw Python text such as "'NoneType' object has no
attribute 'get'". Those are the sender's mistakes: they must be 400 with words a
person can read, and the hub must keep answering afterwards. Also the browser's
own /favicon.ico request used to log a 404 on every first page load.
"""
import qc as F

AREA = "hub"
TITLE = "odd or broken data gets a plain 400, and /favicon.ico answers"
SLOW = False

CASES = [
    ("/api/save", b"", "empty body"),
    ("/api/save", b"null", "JSON null"),
    ("/api/save", b"[]", "JSON list"),
    ("/api/save", b"\xff\xfe{{{", "not UTF-8"),
    ("/api/save", b'{"name": "\xf0\x9f\x98\x80"}', "name with an emoji"),
    ("/api/save", b'{"x": 1}', "missing name"),
    ("/api/seqdelete", b"null", "JSON null"),
    ("/api/gestures/plan", b"[]", "JSON list"),
]


def run(t):
    base, _main = F.start_hub()
    F.login(base)
    for path, body, what in CASES:
        code, text = F.post(base + path, body)
        t.ok(code == 400, "%s with %s is 400" % (path, what), "%s %s" % (code, text[:120]))
        t.ok("NoneType" not in text and "Traceback" not in text and "utf-8" not in text,
             "%s with %s says no Python words" % (path, what), text[:120])
    code, _ = F.get(base + "/api/version")
    t.ok(code == 200, "the hub still answers afterwards")
    code, _ = F.get(base + "/favicon.ico")
    t.ok(code in (200, 204), "/favicon.ico answers", str(code))

    # A newcomer's Complaints tab showed raw "STUDIO FREEZE {json}" (2026-11-21);
    # the list now says it in words, and a fresh checkout knows no other PC.
    code, page = F.get(base + "/")
    t.ok("Studio stopped answering for" in page, "Complaints lists an automatic freeze report in words")
    import json
    known = json.loads((F.HUB / "known_hubs.json").read_text(encoding="utf-8"))
    t.ok(known.get("hubs") == [], "a fresh checkout ships no stale PC address", str(known))
