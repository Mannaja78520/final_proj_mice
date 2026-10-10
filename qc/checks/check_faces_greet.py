"""Who the rig greets, with which words, and when it keeps quiet (system A5).

THE PROMISES, from docs/system_integral.html and the user's own words:

* An unknown person is never greeted with a guessed name. The user asked
  (2026-09-18) for the common word instead - like Mr. or Ms. - so a stranger
  gets the title and nothing else, and a rule that puts {name} in the
  stranger's words is refused when it is saved, not discovered when spoken.
* One person, one hello per cooldown, whichever camera sees them.
* Whether the rig is free is decided by the hub in the same step as the
  greeting (whenBusy on the request). Reading the queue first and then
  posting lets two greetings both see a free rig.
* Only a sighting with a real camera greets. Their history rows carry no
  camera at all, so they are counted and nothing else.

THE TRAP THAT SHAPED service.py: their app publishes one match twice, and the
copy tagged "kiosk" (not a place) can arrive first. That first copy is only
counted, and the merge swallows the second - so the copy that names a real
door must still reach the greeter, or nobody is ever greeted at all.
"""
import importlib.util
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "the rig greets by name only when it knows the person and the camera"


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / "apps" / "faces"))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ev(who, pid, camera="door-1", known=True, has=True):
    return {"who": who, "id": pid, "known": known, "camera": camera,
            "hasCamera": has, "source": "ws"}


def run(t):
    R = _load("_faces_rules_under_test", "apps/faces/rules.py")
    shipped, why = R.load()
    t.ok(shipped and not why, "the shipped rules.json loads", why)
    t.eq(shipped.get("greet"), False,
         "greeting ships turned OFF - nothing spoke before, so on is a choice")
    g, said = R.decide(ev("Ann", "P1"), shipped, {"people": {}, "cameras": {}})
    t.ok(g is None and "off" in said, "and while off nobody is greeted", said)

    rules = json.loads(json.dumps(shipped))
    rules["greet"] = True
    rules["cameras"] = {"door-1": {"role": "entry"}, "door-2": {"role": "entry"},
                        "back": {"role": "exit"}, "hall": {"role": "watch"}}
    rules["people"] = {"P9": {"title": "Dr. "}}
    rules["title"] = "K. "
    rules["wording"]["entry"].update(known="Hello {title}{name}",
                                     already="Back again {title}{name}",
                                     unknown="Hello {title}")
    mem = lambda: {"people": {}, "cameras": {}, "today": {}}   # noqa: E731
    # Noon today, not the clock: "31 minutes later, the same day" crossed
    # midnight when the gate ran at 23:54 on 2026-10-10 and greeted Ann as new.
    now = time.mktime(time.strptime(time.strftime("%Y-%m-%d") + " 12:00",
                                    "%Y-%m-%d %H:%M"))

    g, said = R.decide(ev("Ann", "P1"), rules, mem(), now)
    t.ok(g and g["text"] == "Hello K. Ann", "a known person is greeted by name, "
         "with the common title", g)
    t.eq(g and g["whenBusy"], "skip",
         "the request carries whenBusy, so the hub decides busy in one step")
    t.ok(g and "take" not in g, "and never `take`, which would stop a show", g)
    g, _ = R.decide(ev("Bo", "P9"), rules, mem(), now)
    t.eq(g and g["text"], "Hello Dr. Bo", "a person's own title wins over the common word")

    # ---- a stranger is never named -----------------------------------
    g, said = R.decide(ev("Guessed Name", "", known=False), rules, mem(), now)
    t.ok(g and "Guessed" not in g["text"] and g["text"] == "Hello K.",
         "a stranger gets the common word and NO name, even if a name rode along", g)
    bad = json.loads(json.dumps(rules))
    bad["wording"]["entry"]["unknown"] = "Hello {name}"
    # Past the save check too (a hand-edited file): the blank stays empty.
    g, _ = R.decide(ev("Guessed Name", "", known=False), bad, mem(), now)
    t.ok(g and "Guessed" not in g["text"],
         "even words that slipped past the save never fill a stranger's name", g)
    t.ok("stranger" in R.check(bad),
         "a rule that puts {name} in the stranger's words is refused on save", R.check(bad))
    bad["wording"]["entry"]["unknown"] = "Hello"
    bad["cameras"]["door-1"]["wording"] = {"unknown": "Hi {name}"}
    t.ok("stranger" in R.check(bad), "the same refusal for one camera's own words",
         R.check(bad))
    bad["cameras"]["door-1"]["wording"] = {"known": "Hi {nmae}"}
    t.ok("{nmae}" in R.check(bad), "a misspelt blank is refused, not read aloud",
         R.check(bad))

    # ---- cameras: role and the count-only cases ------------------------
    g, said = R.decide(ev("Ann", "P1", camera="hall"), rules, mem(), now)
    t.ok(g is None and "counts" in said, "a watch camera only counts", said)
    g, said = R.decide(ev("Ann", "P1", camera="new-cam"), rules, mem(), now)
    t.ok(g is None, "a camera nobody set up does not start talking on its own", said)
    g, said = R.decide(ev("Ann", "P1", camera="", has=False), rules, mem(), now)
    t.ok(g is None and "counted" in said,
         "a sighting with no camera (their history) is counted and not greeted", said)
    g, _ = R.decide(ev("Ann", "P1", camera="back"), rules, mem(), now)
    t.ok(g and "ขอบคุณ" in g["text"], "an exit camera says goodbye words", g)

    # ---- cooldown per person, across cameras ---------------------------
    m = mem()
    m["people"]["P1"] = now - 60
    m["today"]["P1"] = time.strftime("%Y-%m-%d", time.localtime(now))
    g, said = R.decide(ev("Ann", "P1", camera="door-2"), rules, m, now)
    t.ok(g is None and "min ago" in said,
         "the same person a minute later at ANOTHER camera is not greeted again", said)
    g, _ = R.decide(ev("Ann", "P1"), rules, m, now + 31 * 60)
    t.eq(g and g["text"], "Back again K. Ann",
         "after the cooldown, the same day, they get the welcome-back words")
    first_today = dict(ev("Fay", "P6"), repeat="already")
    g, _ = R.decide(first_today, rules, mem(), now)
    t.eq(g and g["text"], "Back again K. Fay",
         "their own check-in flag says already, even after our restart forgot")
    m["cameras"]["door-1"] = now - 10
    g, said = R.decide(ev("", "", known=False), rules, m, now)
    t.ok(g is None, "strangers wait per camera, since they have no identity", said)
    g, _ = R.decide(ev("", "", known=False, camera="door-2"), rules, m, now)
    t.ok(g is not None, "while a stranger at another camera is still greeted")

    # ---- the greeter: one decision at a time, and what a busy rig means -
    tmp = Path(tempfile.mkdtemp(prefix="mice_greet_"))
    path = tmp / "rules.json"
    path.write_text(json.dumps(rules), encoding="utf-8")
    sent, gate = [], threading.Event()

    def slow_post(greeting):
        sent.append(greeting)
        gate.wait(2)
        return "queued", ""

    gr = R.Greeter(rules_path=path, post=slow_post)
    th = [threading.Thread(target=gr.consider, args=(ev("Ann", "P1"),)) for _ in range(6)]
    for x in th:
        x.start()
    time.sleep(0.3)
    gate.set()
    for x in th:
        x.join(5)
    t.eq(len(sent), 1, "six sightings of one person at once make ONE greeting")

    replies = ["skipped", "queued"]
    sent.clear()
    gr = R.Greeter(rules_path=path, post=lambda g: (sent.append(g), (replies.pop(0), ""))[1])
    first = gr.consider(ev("Cy", "P3"))
    second = gr.consider(ev("Cy", "P3"))
    t.ok(first["what"] == "skipped" and second["what"] == "said",
         "a greeting the busy rig skipped does not start the cooldown",
         (first, second))
    t.ok(gr.recent and gr.recent[0]["text"].endswith("Cy"),
         "and the screen sees what was said", gr.recent[:1])

    # ---- through the real hub ------------------------------------------
    base, main = F.start_hub()
    main.hub_speak.SPEECH.tts = lambda *a: (None, "qc: no voice here")
    F.logout_qc()
    gr = R.Greeter(hub=base, rules_path=path)
    got = gr.consider(ev("Dee", "P4"))
    jobs = main.hub_speak.SPEECH.status()
    texts = [j.get("text") for j in ([jobs.get("now")] if jobs.get("now") else [])
             + jobs.get("queue", []) + jobs.get("recent", [])]
    t.ok("Hello K. Dee" in texts,
         "the greeting reached the hub's speaking queue with no login", (got, texts[:4]))
    job = [j for j in ([jobs.get("now")] if jobs.get("now") else [])
           + jobs.get("recent", []) + jobs.get("queue", [])
           if j.get("text") == "Hello K. Dee"]
    t.ok(job and job[0].get("whenBusy") == "skip" and job[0].get("from") == "a program on this PC",
         "with whenBusy as the rules say, asked as a program on this PC", job[:1])

    # ---- the kiosk copy first, the real door second ----------------------
    S = _load("_faces_service_greet", "apps/faces/service.py")
    st = S.State("reconize")
    at = time.strftime("%Y-%m-%dT%H:%M:%S")
    a = st.note({"who": "Eve", "id": "P5", "known": True, "when": at,
                 "camera": "kiosk", "source": "ws"})
    a_door = a is not None and a["hasCamera"]
    b = st.note({"who": "Eve", "id": "P5", "known": True, "when": at,
                 "camera": "door-1", "source": "ws"})
    t.ok(a is not None and not a_door, "the kiosk copy is an arrival with no door")
    t.ok(b is not None and b["hasCamera"] and b["camera"] == "door-1",
         "the real door's copy still reaches the greeter, though it was merged",
         "their kiosk copy can come first; without this nobody is ever greeted")
    c = st.note({"who": "Eve", "id": "P5", "known": True, "when": at,
                 "camera": "door-1", "source": "ws"})
    t.ok(c is None, "and a third copy is nothing new")
