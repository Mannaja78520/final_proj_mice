"""One person, seen twice by two publishers, is one arrival.

THE CASE THIS EXISTS FOR, read out of their code on 2026-09-10

Their app publishes the same match twice. A central-inference match goes out
under the real camera (their api/nodes.py:332-338), and the background
persistence publishes it again with `node_id` set to the literal string
`"kiosk"` - their own comment at api/recognition.py:135-138 says the kiosk
never registers itself as a node. So one person walking past produces two
events a second or two apart, one of which names a place that is not a place.

Greeting somebody twice is bad. Greeting them at the wrong door is worse. Both
are worse than being a second late, so the copies are merged and the one that
knows a real camera wins.

AND THE RULE THE REVIEW DID NOT STATE

A STRANGER IS NEVER MERGED. An unknown face has no identity at all - their
history row carries `person_id: None`, `name: None`, `participant_id: None`
(api/history.py:71-84). Merging on timing alone would fold two different
strangers into one person, and the rig would greet one of them and ignore the
other. Only the row id tells them apart, and the poll's seen-set already does
that, so unknown faces pass straight through this door untouched.
"""
import importlib.util
from datetime import datetime, timedelta

import qc as F


AREA = "hub"
TITLE = "the same person from two publishers is one arrival, strangers are not"


def _service_module():
    spec = importlib.util.spec_from_file_location(
        "_faces_dedupe_under_test", F.CODE / "apps" / "faces" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ev(who, pid, at, camera="", known=True, source="ws"):
    return {"who": who, "id": pid, "known": known, "status": "matched",
            "when": at.isoformat(), "camera": camera,
            "hasCamera": bool(camera), "source": source}


def run(t):
    svc = _service_module()
    state = svc.State("reconize")
    t.ok(state.partner(), "the face app is in the registry to be watched")

    window = float(state.partner().get("dedupeSeconds") or 0)
    t.ok(window > 0,
         "the merge window is DATA, not a number in the code (%ss)" % window,
         "their two publishers are a second or two apart, and how far apart "
         "is exactly the kind of thing that changes on somebody else's rig")

    now = datetime.now()

    # ---- "kiosk" is a label, not a place --------------------------------
    t.ok(state.partner().get("notACamera"),
         "the registry says which camera labels are not places",
         "their kiosk publishes node_id as the literal string 'kiosk' and "
         "never registers as a node, so it names no door at all")
    t.eq(state.real_camera("kiosk"), False,
         "so 'kiosk' does not count as knowing where somebody is")
    t.eq(state.real_camera("door-in"), True,
         "while a real station does")

    # ---- the real case: the same match, twice, one with a real camera ---
    first, dup = state.accept(ev("Ann", "P1", now, camera="kiosk"))
    t.ok(first is not None and not dup, "the first sighting is an arrival")
    t.eq(first["hasCamera"], False,
         "and it does NOT claim to know the door, because kiosk is not one")

    second, dup = state.accept(ev("Ann", "P1", now + timedelta(seconds=1),
                                  camera="door-in"))
    t.ok(second is None and dup,
         "the same person a second later is NOT a second arrival",
         "their kiosk path republishes every central match, so this happens "
         "on every single person who walks past")
    t.eq(first["camera"], "door-in",
         "and the copy that knows a real camera wins")
    t.eq(first["hasCamera"], True,
         "so a later greeting can be placed at the right door")

    # ---- outside the window it IS somebody arriving again ---------------
    later, dup = state.accept(ev("Ann", "P1",
                                 now + timedelta(seconds=window + 5),
                                 camera="door-in"))
    t.ok(later is not None and not dup,
         "the same person well after the window is a new arrival",
         "somebody who leaves and comes back is a person arriving twice, and "
         "a window that never ends would silence the second one for ever")

    # ---- TWO DIFFERENT STRANGERS ARE TWO PEOPLE -------------------------
    a, dup_a = state.accept(ev("", "", now, known=False, source="poll"))
    b, dup_b = state.accept(ev("", "", now + timedelta(seconds=1),
                               known=False, source="poll"))
    t.ok(a is not None and not dup_a, "an unknown face is an arrival")
    t.ok(b is not None and not dup_b,
         "and a SECOND unknown face is a second arrival, not a repeat",
         "a stranger has no participant id and no name, so merging them on "
         "timing would fold two people into one and the rig would greet one "
         "and ignore the other")

    # ---- and NOT-KNOWN wins over any id an event happens to carry -------
    # The guard has to be `known`, not merely "has an id". A source can hand
    # us a row that carries an identifier while still saying the face was not
    # recognised - their history does exactly that shape, with a status of
    # "unknown". Merging those on the id would fold two unrecognised people
    # into one on the strength of a field that does not identify anybody.
    # Sabotage found this hole in the first version of this check.
    u1, d1 = state.accept(ev("", "same-id", now, known=False, source="poll"))
    u2, d2 = state.accept(ev("", "same-id", now + timedelta(seconds=1),
                             known=False, source="poll"))
    t.ok(u1 is not None and not d1, "an unrecognised row is an arrival")
    t.ok(u2 is not None and not d2,
         "and a second one is NOT merged into it, id or no id",
         "`known` is what decides, because an id on a face nobody recognised "
         "identifies nobody")

    # ---- a known person and a stranger never merge into each other ------
    c, _ = state.accept(ev("Ben", "P2", now + timedelta(seconds=1)))
    t.ok(c is not None, "a known person arriving beside a stranger is kept")
    t.eq(c["who"], "Ben", "and stays themselves")
