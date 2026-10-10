"""What we asked Face_Regonize to build, spoken in ONE place (system A13).

The brief (Claude Doc "API ที่ขอจาก Face_Regonize", 2026-10-09) asks them for
POST /api/look, a per-camera "who is here now", strangers in the live feed and
a name each person likes to be called. None of it exists in their version yet.

So every route here is used only once THEIR /openapi.json lists it, and every
path and field name comes from config/partners.json `asks` - the brief's
proposal. When their version lands with other names, the fix is that entry.
The watcher (service.py, look.py) and the voice helper both read through here,
so the two can never disagree about what a person looks like.

Nothing here keeps a picture: a /api/look answer that does not say
"kept": false is treated as a refusal, never as a result.
"""
import json
import time
import urllib.error
import urllib.request
import uuid

# Their self-description, per address: (fetched at, paths or None, why).
# Read again after this long, so their update is noticed without a restart.
SPEC_TTL = 30.0
_specs = {}


def asks(entry, name=""):
    a = (entry or {}).get("asks") or {}
    return a.get(name) or {} if name else a


def _api(entry):
    return str((entry or {}).get("api") or "").rstrip("/")


def spec_paths(entry, timeout=3.0):
    """({path: {method: ...}} or None, why). None = could not ask (app off)."""
    api = _api(entry)
    where = asks(entry).get("spec") or "/openapi.json"
    if not api:
        return None, "config/partners.json does not say where the face app is"
    now = time.time()
    got = _specs.get(api)
    if got and now - got[0] < SPEC_TTL:
        return got[1], got[2]
    try:
        with urllib.request.urlopen(api + where, timeout=timeout) as r:
            paths, why = (json.loads(r.read().decode("utf-8")).get("paths") or {}), ""
    except urllib.error.HTTPError as e:              # it answered: no description
        paths, why = {}, "%s answered %s" % (where, e.code)
    except (OSError, ValueError) as e:
        # Not cached: an app that is starting must be asked again next time.
        return None, "the face app is not answering (%s)" % e
    _specs[api] = (now, paths, why)
    return paths, why


def offers(entry, name, timeout=3.0):
    """(True | False | None, why). Whether their app has the route we asked
    for under `name` (look, present). None = could not ask."""
    a = asks(entry, name)
    if not a.get("path"):
        return False, "config/partners.json asks nothing called %s" % name
    paths, why = spec_paths(entry, timeout)
    if paths is None:
        return None, why
    if (paths.get(a["path"]) or {}).get(a.get("method") or "get"):
        return True, ""
    return False, why or "%s %s is not in their version yet" % (
        (a.get("method") or "get").upper(), a["path"])


def person(entry, raw, field_map=None):
    """One face or person from ANY of their answers, in our shape.

    `field_map` lets a source with its own names (the feed's `map`) win; the
    rest come from asks.person. A face is known only when its status says
    matched AND it carries a name or id - a stranger never gets a name here.
    """
    m = dict(asks(entry, "person"))
    m.update({k: v for k, v in (field_map or {}).items() if v})
    g = lambda k, d="": raw.get(m.get(k) or k, d) if isinstance(raw, dict) else d  # noqa: E731
    who = str(g("who") or "").strip()
    pid = str(g("id") or "")
    status = str(g("status") or ("matched" if who else "unknown"))
    known = status == (m.get("matched") or "matched") and bool(who or pid)
    box = g("box", None)
    if not (isinstance(box, list) and len(box) == 4
            and all(isinstance(v, (int, float)) for v in box)):
        box = None
    return {"who": who if known else "", "id": pid if known else "",
            "first": str(g("first") or "") if known else "",
            "known": known, "status": status,
            "callAs": str(g("callAs") or "") if known else "",
            "title": str(g("title") or "") if known else "",
            "lang": str(g("lang") or ""), "box": box, "score": g("score", None),
            "lastSeen": str(g("lastSeen") or "")}


def area(p):
    """The size of a face's box: the biggest one is the closest, and the
    closest is taken to be the person talking (brief 3.5 item 5)."""
    b = p.get("box")
    return max(0.0, (b[2] - b[0])) * max(0.0, (b[3] - b[1])) if b else 0.0


def nearest_first(people):
    return sorted(people, key=area, reverse=True)


def multipart(fields, file_field, jpeg):
    """(body, content type) for one JPEG plus plain fields."""
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                      % (b, k, v)).encode("utf-8"))
    parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; '
                  'filename="frame.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
                  % (b, file_field)).encode("utf-8"))
    parts += [jpeg, ("\r\n--%s--\r\n" % b).encode("utf-8")]
    return b"".join(parts), "multipart/form-data; boundary=" + b


def look(entry, token, jpeg, camera="", timeout=5.0):
    """Ask who is in ONE frame. -> (state, faces, detail).

    state: "ok", "kept" (it did not promise to keep nothing - stop sending),
    or a name from asks.look.codes (busy, loading, tooBig, login, badImage),
    "refused" for any other answer, "off" when nothing answered.
    faces: our person() shape, nearest first, strangers included.
    """
    a = asks(entry, "look")
    if len(jpeg) > int(a.get("maxBytes") or 2 * 1024 * 1024):
        return "tooBig", [], "%d bytes is over their limit" % len(jpeg)
    fields = {k: str(v).replace("{camera}", camera)
              for k, v in (a.get("form") or {}).items()}
    body, ctype = multipart(fields, a.get("field") or "photo", jpeg)
    req = urllib.request.Request(_api(entry) + a["path"], data=body,
                                 headers={"Authorization": "Bearer " + token,
                                          "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            got = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return (a.get("codes") or {}).get(str(e.code), "refused"), [], "answered %s" % e.code
    except (OSError, ValueError) as e:
        return "off", [], str(e)
    # THE PROMISE IS READ, NOT ASSUMED: the whole point of this route is that
    # nothing is stored, and an answer that does not say so is not trusted.
    if got.get(a.get("kept") or "kept") is not False:
        return "kept", [], "the answer did not say kept: false"
    faces = [person(entry, f) for f in (got.get(a.get("faces") or "faces") or [])
             if isinstance(f, dict)]
    return "ok", nearest_first(faces), "%s ms" % got.get(a.get("took") or "took_ms", "?")


def present(entry, token, node, seconds=10, timeout=3.0):
    """Who one of THEIR cameras sees now. -> (answer or None, why).

    answer: {"facesNow", "unknownNow", "people": [person(), nearest first]}.
    """
    a = asks(entry, "present")
    path = a["path"].replace("{node_id}", urllib.request.quote(str(node), safe=""))
    q = str(a.get("query") or "").replace("{seconds}", str(int(seconds)))
    req = urllib.request.Request(_api(entry) + path + ("?" + q if q else ""),
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            got = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, "their present answered %s" % e.code
    except (OSError, ValueError) as e:
        return None, "their present is not answering (%s)" % e
    # Their list names only recognised people (no status field): person()
    # counts a row with a name as matched.
    people = [person(entry, p) for p in (got.get(a.get("people") or "people") or [])
              if isinstance(p, dict)]
    known = [p for p in people if p["known"]]

    def num(k, d):
        v = got.get(a.get(k) or k)
        return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else d
    return {"facesNow": num("facesNow", len(people)),
            "unknownNow": num("unknownNow", len(people) - len(known)),
            "people": nearest_first(known)}, ""
