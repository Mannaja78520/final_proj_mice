"""Who the rig greets, with which words, and when it keeps quiet (system A5).

The watcher (service.py) hands every new arrival to Greeter.consider(). This
file decides; the hub's speaking queue (main_python/hub_speak.py) does the
talking. The words live in rules.json beside this file, edited on the
Reconize screen and read again on every arrival, so nothing needs a restart.

THE FOUR PROMISES, each one a check in qc/checks/check_faces_greet.py:

* A STRANGER IS NEVER CALLED BY A GUESSED NAME. {name} is filled only when the
  face app recognised the person, and a rule that puts {name} in the stranger
  wording is refused when it is saved (A5-1, A5-2).
* ONE PERSON, ONE HELLO PER COOLDOWN, across every camera (A5-3).
* WHETHER THE RIG IS FREE IS ASKED OF THE HUB IN THE SAME STEP AS THE
  GREETING. The watcher sends whenBusy with the request and never reads the
  queue first: read-then-act lets two greetings both see a free rig (A5-4).
  `take` (stop everything else) is never sent from here.
* ONLY A SIGHTING WITH A REAL CAMERA MAY GREET. Their history carries no
  camera, so a history row is counted and nothing else (A5-5).
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rules_file():
    """rules.json beside this file; MICE_FACES_RULES points a check at a copy,
    so QC never rewrites the words somebody chose."""
    return Path(os.environ.get("MICE_FACES_RULES") or HERE / "rules.json")

def address_words():
    """Words a name the face app sends may already start with (call_as
    "พี่บอส"), so {title} is not put in front of it as well. ONE list, the
    Voice helper's: config/voice.json face.addressWords."""
    path = Path(os.environ.get("MICE_VOICE_CONFIG") or HERE.parent.parent / "config" / "voice.json")
    try:
        got = (json.loads(path.read_text(encoding="utf-8")).get("face") or {}).get("addressWords")
    except Exception:                                        # noqa: BLE001
        got = None
    return tuple(w for w in got if w) if isinstance(got, list) and got else ("คุณ",)


ROLES = ("entry", "exit", "watch")
KINDS = ("known", "already", "unknown")
BLANKS = ("{title}", "{name}")


def load(path=None):
    """(rules, why). A broken file greets nobody and says why."""
    path = Path(path or rules_file())
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, "%s is missing, so nobody is greeted" % path.name
    except Exception as e:                                   # noqa: BLE001
        return {}, "%s could not be read (%s), so nobody is greeted" % (path.name, e)
    why = check(got) or milestones_check(got.get("milestones") or [])
    return (got if not why else {}), why


def _unknown_blank(text, where):
    """Any blank other than {title} and {name} is a typo nobody would hear
    until the rig read '{nmae}' aloud to a guest."""
    for blank in re.findall(r"\{[^}]*\}", text or ""):
        if blank not in BLANKS:
            return "%s has %s - the only blanks are {title} and {name}" % (where, blank)
    return ""


def check(r):
    """Why these rules cannot be used, or ''. Used on load AND before a save,
    so the screen hears the reason instead of the rig going quiet later."""
    if not isinstance(r, dict):
        return "the rules are not a list of settings"
    if r.get("whenBusy", "skip") not in ("skip", "queue"):
        return "whenBusy is skip or queue, not %r" % r.get("whenBusy")
    for key in ("cooldownMinutes", "strangerCooldownSeconds"):
        try:
            if float(r.get(key, 0)) < 0:
                return "%s cannot be below zero" % key
        except (TypeError, ValueError):
            return "%s must be a number" % key
    if r.get("unlistedCamera", "watch") not in ROLES:
        return "unlistedCamera is entry, exit or watch"
    sets = [("wording", r.get("wording") or {})]
    for cam, c in (r.get("cameras") or {}).items():
        if not isinstance(c, dict):
            return "camera %s is not a list of settings" % cam
        if c.get("role", "watch") not in ROLES:
            return "camera %s: role is entry, exit or watch" % cam
        # A camera's own words are for its own role only.
        sets.append(("camera %s" % cam, {c.get("role", "watch"): c.get("wording") or {}}))
    for where, wording in sets:
        for role, words in wording.items():
            if not isinstance(words, dict):
                return "%s: the %s words are not a list" % (where, role)
            for kind, text in words.items():
                if kind not in KINDS:
                    return "%s: %s is not known, already or unknown" % (where, kind)
                place = "%s, %s, %s" % (where, role, kind)
                why = _unknown_blank(text, place)
                if why:
                    return why
                if kind == "unknown" and "{name}" in (text or ""):
                    return ("%s puts {name} in the words for a stranger. A stranger "
                            "has no name to say, so it would be a guess." % place)
    return ""


def _fill(text, title, name):
    return " ".join((text or "").replace("{title}", title)
                    .replace("{name}", name).split())


def decide(event, rules, memory, now=None):
    """(greeting or None, why). Pure: nothing is said and nothing remembered.

    `memory` holds what has been greeted: {"people": {key: time}, "cameras":
    {camera: time}, "today": {key: date}}. `now` is seconds since the epoch.
    """
    now = time.time() if now is None else now
    if not rules:
        return None, "there are no rules to greet with"
    if not rules.get("greet"):
        return None, "greeting is turned off"
    if not event.get("hasCamera"):
        # A5-5. The service decides hasCamera (State.accept); no source can.
        return None, "counted only: this sighting does not say which camera saw them"
    camera = str(event.get("camera") or "")
    cam = (rules.get("cameras") or {}).get(camera) or {}
    role = cam.get("role") or rules.get("unlistedCamera") or "watch"
    if role == "watch":
        return None, "camera %s only counts people" % camera

    known = bool(event.get("known") and event.get("who"))
    key = str(event.get("id") or event.get("who") or "") if known else ""
    if known:
        last = (memory.get("people") or {}).get(key)
        wait = float(rules.get("cooldownMinutes") or 0) * 60
        if last is not None and now - last < wait:
            return None, "%s was greeted %d min ago" % (event.get("who"), (now - last) // 60)
        today = datetime.fromtimestamp(now).date().isoformat()
        # Their own check-in flag is the truth ("already" once they checked in
        # today); ours is the fallback, and it forgets on a watcher restart.
        seen = (memory.get("today") or {}).get(key) == today
        kind = "already" if seen or event.get("repeat") == "already" else "known"
    else:
        last = (memory.get("cameras") or {}).get(camera)
        wait = float(rules.get("strangerCooldownSeconds") or 0)
        if last is not None and now - last < wait:
            return None, "a stranger was greeted at camera %s %d s ago" % (camera, now - last)
        kind = "unknown"

    own = cam.get("wording") or {}
    text = own.get(kind) or ((rules.get("wording") or {}).get(role) or {}).get(kind) or ""
    if not text:
        return None, "there are no %s words for %s at camera %s" % (kind, role, camera)
    title = rules.get("title") or ""
    name = event.get("who") if known else ""
    if known:
        own_title = ((rules.get("people") or {}).get(key) or {}).get("title")
        title = own_title or title
        # The name they asked to be called (their call_as, A13-5). When it
        # already carries its form of address, no second one goes in front.
        if event.get("callAs"):
            name = event["callAs"]
            if not own_title and name.startswith(address_words()):
                title = ""
    greeting = {"text": _fill(text, title, name),
                "to": cam.get("to") or rules.get("to") or "",
                "move": cam.get("move") or "", "module": cam.get("module") or "",
                "whenBusy": rules.get("whenBusy") or "skip"}
    return greeting, "%s at camera %s (%s)" % (kind, camera, role)


class Greeter:
    """Remembers who was greeted and hands greetings to the hub.

    One lock around decide-and-remember, so the live feed and the poll can
    never both decide to greet the same person. The hub call itself is made
    outside the lock: a slow hub must not stall the next arrival.
    """

    def __init__(self, hub="", rules_path=None, post=None):
        self.hub = hub.rstrip("/")
        self.rules_path = rules_path
        self.lock = threading.Lock()
        self.memory = {"people": {}, "cameras": {}, "today": {}}
        self.recent = []
        self.error = ""
        self.post = post or self._post

    def _post(self, greeting):
        """(state, why) from the hub's speaking queue."""
        body = json.dumps(dict(greeting, **{"from": "the face watcher"})).encode("utf-8")
        req = urllib.request.Request(self.hub + "/api/speak", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                got = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                got = json.loads(e.read().decode("utf-8"))
            except Exception:                                # noqa: BLE001
                got = {}
            return "failed", got.get("error") or "the hub refused (%s)" % e.code
        except Exception as e:                               # noqa: BLE001
            return "failed", "the hub is not answering (%s)" % e
        return got.get("state") or "failed", got.get("why") or got.get("error") or ""

    def consider(self, event, now=None):
        """Greet this arrival if the rules say so. Returns what happened."""
        now = time.time() if now is None else now
        rules, why = load(self.rules_path)
        self.error = why
        with self.lock:
            greeting, said = decide(event, rules, self.memory, now)
            if greeting:
                key = str(event.get("id") or event.get("who") or "")
                known = bool(event.get("known") and event.get("who"))
                slot = ("people", key) if known else ("cameras", str(event.get("camera")))
                before = self.memory[slot[0]].get(slot[1])
                # Remembered BEFORE the call, so a second sighting arriving
                # during it is already inside the cooldown.
                self.memory[slot[0]][slot[1]] = now
        if not greeting:
            return self._log(event, "quiet", why or said)
        state, why = self.post(greeting)
        with self.lock:
            if state == "queued":
                if known:
                    self.memory["today"][key] = datetime.fromtimestamp(now).date().isoformat()
            elif self.memory[slot[0]].get(slot[1]) == now:
                # Not said (rig busy, hub down): they may be greeted next time.
                if before is None:
                    self.memory[slot[0]].pop(slot[1], None)
                else:
                    self.memory[slot[0]][slot[1]] = before
        return self._log(event, "said" if state == "queued" else state,
                         why or said, greeting.get("text"))

    def _log(self, event, what, why, text=""):
        entry = {"who": event.get("who") or "", "camera": event.get("camera") or "",
                 "what": what, "why": why, "text": text,
                 "at": datetime.now().isoformat(timespec="seconds")}
        with self.lock:
            self.recent = ([entry] + self.recent)[:50]
        return entry


# ---------------------------------------------------------------- milestones
# A6-2. "100 people arrived, celebrate" (user). Which milestones already fired
# today lives in its OWN file with ONE writer (Milestones), never in
# rules.json: the screen saves rules.json, and a save carrying an old fired
# list would make the rig celebrate the same hundred twice.

def milestones_check(items):
    if not isinstance(items, list):
        return "milestones is a list"
    for m in items:
        try:
            if int(m.get("at")) < 1:
                return "a milestone is a number of people, 1 or more"
        except (TypeError, ValueError, AttributeError):
            return "each milestone needs `at`, a number of people"
        if not (m.get("text") or m.get("move")):
            return "the milestone at %s says nothing and moves nothing" % m.get("at")
        why = _unknown_blank(m.get("text"), "the milestone at %s" % m.get("at"))
        if why or "{name}" in (m.get("text") or ""):
            return why or "a milestone is about a crowd, so it has no {name}"
    return ""


class Milestones:
    """Fires each milestone once per day, and remembers that across restarts."""

    def __init__(self, path, post):
        self.path = Path(path)
        self.post = post
        self.lock = threading.Lock()

    def _read(self, today):
        try:
            got = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            got = {}
        # Their count starts again at midnight, so the fired list does too.
        return got if got.get("date") == today else {"date": today, "fired": []}

    def tick(self, count, rules, today=None):
        """Fire what this count has reached. Returns [(at, state, why)]."""
        today = today or datetime.now().date().isoformat()
        items = (rules or {}).get("milestones") or []
        if not (rules or {}).get("greet") or count is None or milestones_check(items):
            return []
        out = []
        with self.lock:
            done = self._read(today)
            for m in sorted(items, key=lambda m: int(m["at"])):
                at = int(m["at"])
                if at > count or at in done["fired"]:
                    continue
                state, why = self.post({
                    "text": _fill(m.get("text"), (rules or {}).get("title") or "", ""),
                    "move": m.get("move") or "", "module": m.get("module") or "",
                    "to": m.get("to") or (rules or {}).get("to") or "",
                    # A celebration waits its turn; it is not dropped like a hello.
                    "whenBusy": "queue"})
                out.append((at, state, why))
                if state == "queued":
                    done["fired"].append(at)
                    tmp = self.path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(done), encoding="utf-8")
                    tmp.replace(self.path)
        return out

