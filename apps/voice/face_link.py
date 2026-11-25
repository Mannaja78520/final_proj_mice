"""The voice helper's link to the face app (Reconize): who is in front of the robot.

Moved out of apps/voice/service.py 2026-11-21 (architecture review: Brain was a
2700-line class). Behaviour is unchanged; Brain inherits FaceLink, so every
`brain.identify(...)` etc. still works. State used here (set in Brain.__init__):
_cached_person, _cached_person_at, _reconize_token, _reconize_token_exp, cfg.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
import sys                                           # noqa: E402
sys.path.insert(0, str(CODE / "tools"))
sys.path.insert(0, str(CODE / "apps" / "faces"))
import registry                                      # noqa: E402
import friend_api                                    # noqa: E402
from face_history import HistoryCursor, local_when    # noqa: E402

# What the page says when nothing answers at the face app's address. The page
# turns this one sentence into a Start button, so the words name the fix.
FACE_APP_OFF = "the face app is not running yet - start it and look again"

# What the page says when the face app would STORE the frame. The page stops
# looking on this sentence, so it names the two ways that still work.
FACE_APP_KEEPS = ("the face app would keep this picture, so it was not sent - "
                  "pick a camera the face app watches, or use Open Reconize")

# Their /api/look refusals, in plain words (asks.look.codes names them). A
# 429 lasted over a minute on the PC, 2026-10-15: their model was busy with
# other work, and "refused" sent the user looking for a fault of ours.
FACE_APP_SAYS = {
    "busy": "the face app is busy with other work - it will look again in a moment",
    "loading": "the face app is still loading its face model - wait a moment",
    "tooBig": "that picture is too big for the face app",
    "badImage": "the face app could not read that picture - try again",
}


def short_person_name(person):
    """Extract a friendly conversational first/short name."""
    if not person:
        return ""
    p = str(person).strip().strip("'\"[]")
    parts = p.split()
    return parts[0] if parts else p


def call_name(p):
    """What to call one person from the face app: the name they asked to be
    called (call_as, brief 3.5 item 1) when it sends one, else the first word."""
    return str(p.get("callAs") or "").strip() or short_person_name(p.get("who") or "")


def join_names(names):
    names = [n for n in names if n]
    if not names:
        return ""
    return " และ ".join(names[:2]) if len(names) <= 2 else "%s, %s และทุกท่าน" % (names[0], names[1])


def faces_on(cfg):
    """Face recognition used at all (user 2026-10-15: *let me choose to use
    faces or not*). Off = no look, no name, no wait; missing = on. A function
    of the store, so a check's stand-in Brain needs no method for it."""
    return ((cfg or {}).get("face") or {}).get("on", True) is not False


class FaceLink:
    """Face-app calls and the cached "who is here"; mixed into Brain."""

    def _query_faces_service(self, camera=""):
        """Query loopback faces service at :8769/state.

        `camera` keeps only what one station saw. Their feed carries the
        station in each event (apps/faces/service.py from_ws), which is what
        makes one camera usable by both apps at once: the face app scans, and
        Voice reads the result for the camera the designer picked.
        """
        import urllib.request
        from datetime import datetime
        # The watcher's address is data: apps/faces/service.py is normally on
        # :8769 of this PC, but a check points this at its own.
        where = str((self.cfg.get("face") or {}).get("watcher")
                    or os.environ.get("MICE_FACES_STATE")
                    or "http://127.0.0.1:8769/state")
        # Who is in front of that camera NOW (A13-3): the watcher picks the
        # best source - our camera's look, their present, else their feed -
        # nearest first, with the name each person asked to be called. An
        # older watcher has no /present, and this carries on as before.
        got = self._watcher_present(where, camera, 120)
        # Whether the fast road answered (A42-4): with the watcher down, every
        # look fell to their history - 2.5 s a call on the PC, 2026-10-15 -
        # and the page starts the watcher when it hears this is False.
        self._watcher_ok = got is not None
        if got is not None:
            return join_names([call_name(p) for p in got.get("people") or []])
        try:
            req = urllib.request.Request(where)
            with urllib.request.urlopen(req, timeout=1.0) as r:
                if r.status == 200:
                    data = json.loads(r.read().decode("utf-8"))
                    people = data.get("people") or []
                    active = []
                    seen = set()
                    for p in people:
                        who = (p.get("who") or "").strip()
                        when_str = p.get("when") or ""
                        if camera and str(p.get("camera") or "") != camera:
                            continue
                        if who and p.get("known", True) and when_str:
                            try:
                                w_dt = local_when(when_str)
                                if w_dt and 0 <= (datetime.now() - w_dt).total_seconds() <= self.seen_seconds():
                                    s = short_person_name(who)
                                    if s and s.lower() not in seen:
                                        seen.add(s.lower())
                                        active.append(s)
                            except Exception:
                                pass
                    if active:
                        return " และ ".join(active[:2]) if len(active) <= 2 else f"{active[0]}, {active[1]} และทุกท่าน"
        except Exception:
            pass
        return ""

    def _watcher_present(self, where, camera="", seconds=120):
        """The watcher's /present answer, or None when it has none."""
        from urllib.parse import quote
        url = "%s/present?camera=%s&seconds=%s" % (
            where.rsplit("/state", 1)[0], quote(str(camera or "")), float(seconds))
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                got = json.loads(r.read().decode("utf-8"))
        except Exception:                                    # noqa: BLE001
            return None
        return got if got.get("ok") and isinstance(got.get("people"), list) else None

    def presence_gate(self):
        """(take the question?, why). System A7-1, PRESENCE MODE.

        Opt-in (config voice.json presence.on). It gates ONLY taking a
        question - never the nong's own sequences, a show or a command. And it
        FAILS OPEN: if the face watcher is down, or its app has no camera that
        can tell who stands where, the question is taken. A broken camera
        must never be what makes the rig deaf."""
        import urllib.request
        from urllib.parse import quote
        cfg = self.cfg.get("presence") or {}
        if not cfg.get("on") or not faces_on(self.cfg):
            return True, ""                       # faces off = nobody is checked
        where = str((self.cfg.get("face") or {}).get("watcher")
                    or os.environ.get("MICE_FACES_STATE")
                    or "http://127.0.0.1:8769/state")
        base = where.rsplit("/state", 1)[0]
        url = "%s/presence?seconds=%s&camera=%s" % (
            base, float(cfg.get("seconds") or 60), quote(str(cfg.get("camera") or "")))
        try:
            with urllib.request.urlopen(url, timeout=1.0) as r:
                got = json.loads(r.read().decode("utf-8"))
        except Exception:                                    # noqa: BLE001
            return True, "the face watcher is not answering, so questions stay open"
        if got.get("known") and got.get("present") is False:
            return False, "nobody is standing in front of the camera, so the question was not taken"
        return True, got.get("why") or ""

    def _reconize_api(self):
        """Where Reconize answers, from config/partners.json - the one list.

        Their port moves with an update of theirs, and a second copy of the
        address in this file is how the two would disagree.
        """
        return str(self._reconize_entry().get("api") or "").rstrip("/")

    def _reconize_entry(self):
        """Reconize's whole entry in config/partners.json, {} when unreadable."""
        try:
            # MICE_PARTNERS is what the hub honours too, and it is what lets a
            # check point this at a fake face app instead of the real one.
            path = os.environ.get("MICE_PARTNERS") or (CODE / "config" / "partners.json")
            return registry.load(path).get("reconize") or {}
        except Exception:                               # noqa: BLE001
            return {}

    def look_allowed(self):
        """Whether the face app PROMISES to keep nothing of one frame.

        Their upload stores the frame, a history row and an attendance row.
        `persist=false` was a local patch to their code, never theirs, and
        resetting their folder to their own version removed it (2026-09-29).
        FastAPI ignores a query it does not know, so sending the flag proves
        nothing: only their own /openapi.json listing it counts. Returns
        (True|False|None, why, detail); None = could not ask (app off).
        """
        import urllib.error
        import urllib.request
        # Their POST /api/look keeps nothing by design (A13-4), so it is
        # enough that their app lists it; identify() reads the promise again
        # on every answer.
        if friend_api.offers(self._reconize_entry(), "look")[0]:
            return True, "", "POST /api/look"
        api = self._reconize_api()
        look = self._reconize_entry().get("look") or {}
        name = str(look.get("dontKeep") or "").partition("=")[0]
        if not api or not look.get("path") or not name or not look.get("spec"):
            return False, "config/partners.json does not say how to ask the face app about one picture", ""
        try:
            with urllib.request.urlopen(api + look["spec"], timeout=5) as r:
                doc = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:             # it answered: no description
            return False, FACE_APP_KEEPS, "%s answered %s" % (look["spec"], e.code)
        except OSError as e:
            return None, FACE_APP_OFF, str(e)
        except ValueError as e:                         # not JSON: cannot tell, so no
            return False, FACE_APP_KEEPS, "%s is not readable: %s" % (look["spec"], e)
        op = ((doc.get("paths") or {}).get(look["path"]) or {}).get("post") or {}
        if any(isinstance(p, dict) and p.get("name") == name and p.get("in") == "query"
               for p in (op.get("parameters") or [])):
            return True, "", ""
        return False, FACE_APP_KEEPS, "POST %s has no %s option (%s)" % (
            look["path"], name, look["spec"])

    def _faces_login_path(self):
        """Where the saved face-app login lives.

        The real file never leaves the real tree (promote.py SKIP_FILES keeps
        the password out of every copy), so a check running in .staging found
        nothing and stopped at the first line of every face test. The override
        lets it point at a throwaway login, exactly as MICE_PARTNERS points at
        a fake face app.
        """
        if os.environ.get("MICE_FACES_LOGIN"):
            return Path(os.environ["MICE_FACES_LOGIN"])
        mine = CODE / "main_python" / "faces_login.json"      # this PC's changed login wins
        return mine if mine.is_file() else CODE / "main_python" / "faces_login.default.json"

    def _reconize_login(self, timeout=3.0):
        """A Reconize token, cached for half an hour. '' when it cannot log in."""
        import urllib.request
        l_path = self._faces_login_path()
        if not l_path.is_file():
            return ""
        creds = json.loads(l_path.read_text(encoding="utf-8")).get("reconize") or {}
        u, p = creds.get("username"), creds.get("password")
        if not u or not p:
            return ""
        now = time.time()
        api = self._reconize_api()
        tok = getattr(self, "_reconize_token", "")
        if tok and getattr(self, "_reconize_token_api", None) == api and now < getattr(self, "_reconize_token_exp", 0.0) - 60:
            return tok
        if not api:
            return ""
        body = json.dumps({"username": u, "password": p}).encode("utf-8")
        req = urllib.request.Request(api + "/api/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            tok = json.loads(r.read().decode("utf-8")).get("access_token") or ""
        self._reconize_token = tok
        self._reconize_token_api = api
        self._reconize_token_exp = now + 1800
        return tok

    def camera_choice(self):
        """Which camera the Voice page should open, and how often to look.

        The camera is NOT a new setting here: Reconize already stores an
        app-wide default as the device LABEL (their settings camera_label -
        a browser deviceId means nothing on another machine, which is why
        they chose the label). Voice reads that one, so a designer who picks
        the camera once in the face app has picked it here too.
        config/voice.json can override it per PC, and the page keeps a local
        override of its own, exactly like their kiosk does.
        """
        import urllib.request
        face = self.cfg.get("face") or {}
        if not self.faces_on():                   # nothing to look with, nobody asked
            return {"on": False, "label": "", "from": "", "stations": [],
                    "seconds": float(face.get("autoSeconds") or 5),
                    "look": {"ok": False, "why": "face recognition is switched off", "detail": ""}}
        label = str(face.get("cameraLabel") or "")
        where = "voice.json" if label else ""
        if not label:
            api = self._reconize_api()
            try:
                tok = self._reconize_login()
                if api and tok:
                    req = urllib.request.Request(api + "/api/settings",
                                                 headers={"Authorization": "Bearer " + tok})
                    with urllib.request.urlopen(req, timeout=3) as r:
                        label = str(json.loads(r.read().decode("utf-8")).get("camera_label") or "")
                        where = "the face app" if label else ""
            except Exception:                           # noqa: BLE001
                pass                                    # no default is fine - the browser picks
        ok, why, detail = self.look_allowed()
        return {"on": self.faces_on(), "label": label, "from": where, "stations": self.face_stations(),
                "seconds": float(face.get("autoSeconds") or 5),
                "look": {"ok": ok, "why": why, "detail": detail}}

    def face_stations(self):
        """The cameras the face app is ALREADY watching.

        User 2026-09-18: *in face regconize already make the program that we
        can use 1 camera for many task or program just read it*. Their
        stations - the kiosk, a CCTV node, a phone, the multi-camera local
        agent - all publish what they see to one live feed, and
        apps/faces/service.py already listens to it. So Voice does not have
        to open a second camera to know who is there: picking a station here
        means reading that feed instead, and one camera serves both apps.
        """
        import urllib.request
        out = []
        try:
            api = self._reconize_api()
            tok = self._reconize_login()
            got = {}
            if api and tok:
                req = urllib.request.Request(api + "/api/node/status",
                                             headers={"Authorization": "Bearer " + tok})
                with urllib.request.urlopen(req, timeout=3) as r:
                    got = json.loads(r.read().decode("utf-8"))
        except Exception:                                   # noqa: BLE001
            got = {}
        for n in (got.get("nodes") or []):
            nid = str(n.get("node_id") or "")
            if not nid:
                continue
            out.append({"id": nid,
                        "name": str(n.get("camera_label") or n.get("name") or nid),
                        "online": bool(n.get("online"))})
        # The rig's own cameras the watcher asks through their /api/look
        # (A13-2, config/faces.json look) - pickable like any of theirs.
        where = str((self.cfg.get("face") or {}).get("watcher")
                    or os.environ.get("MICE_FACES_STATE") or "http://127.0.0.1:8769/state")
        ids = {o["id"] for o in out}
        for cam in (self._watcher_present(where, "", 10) or {}).get("cameras") or []:
            if cam not in ids:
                out.append({"id": cam, "name": cam, "online": True})
                ids.add(cam)
        # A rig camera's `dev` is how the page SHOWS it (A42-2, user
        # 2026-10-15 *voice does not show the camera*): the hub's live view of
        # that board. Listed even while the watcher is off - seeing the
        # picture does not need it. Their stations have no address we can
        # show; the page points at their own app for those.
        for cam in self._rig_cameras():
            hit = next((o for o in out if o["id"] == cam["name"]), None)
            if hit is None:
                out.append({"id": cam["name"], "name": cam["name"], "online": False})
                hit = out[-1]
            hit["dev"] = cam["dev"]
        return out

    @staticmethod
    def _rig_cameras():
        """config/faces.json look.cameras, read per call (MICE_FACES_CONFIG
        points a check at a copy, as the hub's own reader does)."""
        path = os.environ.get("MICE_FACES_CONFIG") or (CODE / "config" / "faces.json")
        try:
            cams = (registry.load(path).get("look") or {}).get("cameras") or []
        except Exception:                                   # noqa: BLE001
            return []                                       # no file: no rig camera
        return [{"name": str(c["name"]), "dev": str(c["dev"])}
                for c in cams if isinstance(c, dict) and c.get("name") and c.get("dev")]

    def identify(self, jpeg):
        """Asks Reconize who is in ONE frame, and saves NOTHING.

        User 2026-09-18: *do not save the picture of it because it took my
        rom*. Their upload writes the frame, a history row and an attendance
        row, so the frame goes only to a face app that promises to keep none
        of it (look_allowed); otherwise nothing is sent and the page is told
        why. The name is cached here exactly like a face seen through their
        camera, so the next answer greets the person by name.
        """
        import urllib.error
        import urllib.request
        api = self._reconize_api()
        if not api:
            return "", "config/partners.json does not say where the face app is", ""
        try:
            tok = self._reconize_login()
        except urllib.error.HTTPError as e:             # it answered, and said no
            return "", "the face app did not accept the saved login", str(e)
        except OSError as e:                            # nothing was listening
            # WinError 10061 is a REFUSED CONNECTION, not a refused password.
            # Saying "did not accept the saved login" sent the user looking for
            # a wrong password that was never wrong (user 2026-09-18). Nothing
            # is running: the fix is to start it, so the page offers that.
            return "", FACE_APP_OFF, str(e)
        if not tok:
            return "", "no saved login for the face app - see main_python/faces_login.json", ""
        # Their POST /api/look first (A13-4): built to keep nothing, and says
        # so on every answer ("kept": false), which friend_api checks.
        entry = self._reconize_entry()
        if friend_api.offers(entry, "look")[0]:
            state, faces, detail = friend_api.look(entry, tok, jpeg, "voice-page", timeout=30)
            if state == "kept":
                return "", FACE_APP_KEEPS, detail
            if state == "off":
                return "", FACE_APP_OFF, detail
            if state != "ok":
                return "", FACE_APP_SAYS.get(state, "the face app refused to look at that picture"), \
                    "%s: %s" % (state, detail)
            return self._remember_look([call_name(f) for f in faces if f["known"]], len(faces))
        ok, why, detail = self.look_allowed()
        if not ok:
            return "", why, detail
        look = self._reconize_entry()["look"]
        b = uuid.uuid4().hex
        body = b"".join([
            ('--%s\r\nContent-Disposition: form-data; name="%s"; '
             'filename="frame.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
             % (b, look.get("field") or "photo")).encode(),
            jpeg, ("\r\n--%s--\r\n" % b).encode()])
        req = urllib.request.Request(
            api + look["path"] + "?" + look["dontKeep"], data=body,
            headers={"Authorization": "Bearer " + tok,
                     "Content-Type": "multipart/form-data; boundary=" + b})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                got = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return "", "the face app refused to look at that picture", str(e)
        except OSError as e:
            return "", FACE_APP_OFF, str(e)
        names = []
        for m in (got.get("results") or got.get("matches") or []):
            if str(m.get("status") or "matched") != "matched":
                continue
            who = short_person_name((m.get("name") or m.get("first_name") or "").strip())
            if who and who not in names:
                names.append(who)
        return self._remember_look(names, got.get("faces_total") or got.get("faces") or 0)

    def _remember_look(self, names, faces):
        """(person, why-not, detail) from one look's names, remembered like a
        face seen through their camera."""
        names = list(dict.fromkeys(n for n in names if n))
        if not names:
            # Nobody there, or nobody known: drop the name NOW rather than
            # letting the remembered one ride on. The badge said a name while
            # the same look reported an empty frame (user 2026-09-18: *when
            # don't have face why it still said phuthiphong*).
            self.forget_person()
            return "", ("nobody the face app knows was in that picture"
                        if faces else "no face in that picture - move into the light"), ""
        person = join_names(names)
        self._seen_person = person
        self._seen_at = time.time()
        return person, "", ""

    def _query_reconize_direct(self):
        """Last observations delivered by sequence when the watcher is down.

        Sequence orders delivery; the original observation time controls expiry.
        A delayed write, an empty page or a network outage is not a new sighting.
        """
        import urllib.error
        import urllib.request
        from datetime import datetime
        lock = self.__dict__.setdefault("_history_lock", threading.RLock())
        with lock:
            entry = self._reconize_entry()
            source = next((s for s in entry.get("events") or []
                           if s.get("kind") == "poll" and s.get("cursor")), None)
            if not source:
                return ""
            api = str(entry.get("api") or "").rstrip("/")
            key = (api, json.dumps(source, sort_keys=True))
            if key != getattr(self, "_direct_history_key", None):
                self._direct_history_key = key
                self._direct_history = HistoryCursor()
                self._direct_observations = {}
            mapping = source.get("map") or {}

            def consume(row):
                field = lambda name, default: row.get(mapping.get(name) or default)
                node = str(field("camera", "node_id") or "")
                when = local_when(field("when", "detected_at"))
                if not node or node in (entry.get("notACamera") or []) or not when:
                    return
                age = (datetime.now() - when).total_seconds()
                if not 0 <= age <= self.seen_seconds():
                    return
                seq = row[source["cursor"]["seq"]]
                known = field("status", "status") == (
                    friend_api.asks(entry, "person").get("matched") or "matched")
                name = call_name({"who": field("who", "name"),
                                  "callAs": field("callAs", "call_as")}) if known else ""
                # A row is ONE face. An unknown companion is not an empty
                # camera; only a real scene/look can clear known companions.
                if not name:
                    return
                person_key = (node, str(field("id", "participant_id") or name))
                old = self._direct_observations.get(person_key)
                if old and (when, seq) <= (old["when"], old["seq"]):
                    return
                self._direct_observations[person_key] = {"when": when, "seq": seq, "names": [name]}

            try:
                token = self._reconize_login(timeout=1.5)
                if token:
                    def fetch(path):
                        req = urllib.request.Request(api + path,
                            headers={"Authorization": "Bearer " + token})
                        try:
                            with urllib.request.urlopen(req, timeout=1.5) as response:
                                return json.loads(response.read().decode("utf-8")), ""
                        except urllib.error.HTTPError as exc:
                            if exc.code == 401 and getattr(self, "_reconize_token", "") == token:
                                self._reconize_token = ""
                            return {}, str(exc)
                        except (OSError, ValueError) as exc:
                            return {}, str(exc)
                    self._direct_history.poll(source, fetch, consume)
            except (OSError, ValueError):
                pass
            now = datetime.now()
            self._direct_observations = {node: obs for node, obs in self._direct_observations.items()
                if 0 <= (now - obs["when"]).total_seconds() <= self.seen_seconds()}
            observations = sorted(self._direct_observations.values(),
                                  key=lambda obs: (obs["when"], obs["seq"]), reverse=True)
            return join_names(list(dict.fromkeys(name for obs in observations for name in obs["names"])))

    def address_words(self):
        """Words a Thai name may already start with, so no คุณ is added in
        front (config/voice.json face.addressWords)."""
        got = (self.cfg.get("face") or {}).get("addressWords")
        return tuple(w for w in got if w) if isinstance(got, list) and got else ("คุณ",)

    def seen_seconds(self):
        """How long a face from this page's own camera counts as present.

        It has to be a memory of its own: a look keeps nothing, so there is
        no history row, the next poll finds nothing and the name would vanish
        two seconds later. It is a SETTING because the right length depends on
        the room - user 2026-09-18, after the badge kept naming somebody who
        had walked away: *make can setting by my self in setting to setting
        the time out time*.
        """
        try:
            return max(2.0, float((self.cfg.get("face") or {}).get("rememberSeconds") or 120))
        except Exception:                               # noqa: BLE001
            return 120.0

    def forget_person(self):
        """A look that saw nobody means nobody is there - say so at once."""
        self._seen_person = ""
        self._seen_at = 0.0
        self._cached_person = ""
        self._cached_person_at = time.time()

    def faces_on(self):
        return faces_on(self.cfg)

    def get_detected_person(self, req_person=None, camera=""):
        if req_person and str(req_person).strip():
            return str(req_person).strip()
        if not faces_on(self.cfg):
            return ""
        if camera:
            # One station only, and never the frame this page took itself:
            # asking for a camera means "who does THAT camera see".
            return self._query_faces_service(camera)
        now = time.time()
        seen_at = getattr(self, "_seen_at", 0.0)
        if getattr(self, "_seen_person", "") and (now - seen_at < self.seen_seconds()):
            return self._seen_person
        if hasattr(self, "_cached_person_at") and (now - self._cached_person_at < 2.0):
            return getattr(self, "_cached_person", "")
        return self._person_within_deadline(now)

    def _refresh_person(self):
        """One look at who is there. Runs on a worker thread, one at a time."""
        try:
            person = self._query_faces_service()
            # Their history only when the watcher did NOT answer: its "nobody
            # known" is the answer. Asking anyway cost 2.47 s per look at an
            # unknown face on the PC (2026-10-15, real camera).
            if not person and not getattr(self, "_watcher_ok", False):
                person = self._query_reconize_direct()
            self._cached_person = person or ""
            self._cached_person_at = time.time()
        finally:
            self._person_busy = False
            self._person_done.set()

    def prefetch_person(self):
        """Start the look while the visitor is still being heard (POST /transcribe).

        Hearing takes ~0.7 s on the GPU and the look ~2.3 s, so the name is
        ready (or nearly) when /ask comes: the question is not slowed and the
        greeting still has the name (user 2026-11-25: faster, never worse).
        """
        if not faces_on(self.cfg):
            return
        lock = self.__dict__.setdefault("_person_lock", threading.Lock())
        with lock:
            if not getattr(self, "_person_busy", False):
                self._person_busy = True
                self._person_done = threading.Event()
                threading.Thread(target=self._refresh_person, daemon=True).start()

    def _person_within_deadline(self, now):
        """The name for a question, without making the question wait for the camera.

        PC 2026-11-25: every /ask first did this look, synchronously:
        POST /ask 3.07 s with it, 0.73 s with a name given (the model itself
        answers in 0.2 s). The look runs on a worker thread now; a question
        waits at most `face.askWaitSeconds` (default 0.4) for it, then uses the
        last answer if it is younger than `face.askStaleSeconds` (default 30),
        else nobody. The next question finds the refreshed name.
        """
        fc = self.cfg.get("face") or {}
        wait = float(fc.get("askWaitSeconds", 0.4))
        stale = float(fc.get("askStaleSeconds", 30))
        self.prefetch_person()
        done = self._person_done
        done.wait(wait)
        if time.time() - getattr(self, "_cached_person_at", 0.0) <= stale or done.is_set():
            return getattr(self, "_cached_person", "")
        return ""
