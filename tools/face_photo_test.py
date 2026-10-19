"""Still photos through our face path, instead of the live webcam (A43-1).

User 2026-10-19: *เทสโดยเอาภาพมาเทสก่อนเลย* - test with pictures before the
camera. A photo is the same every run, so a wrong name or a slow answer is
the code's fault, not the light's. Each photo goes down every road a webcam
frame takes, and each road is timed:

  look     their POST /api/look alone (friend_api.look), what every road waits on
  watcher  the watcher's camera (look.Looker) given the photo as its frame, then
           Voice asking the watcher who stands there (/face?camera=, A13-3)
  voice    Voice's own one-frame check (/identify, the page's Check who I am)
  hub      the same through the RUNNING hub and Voice (real run, --hub)

The watcher and Voice run here on ports of their own, so the rig's own 8769
and 8767 keep working. Nothing is written: /api/look keeps nothing.

    python tools/face_photo_test.py --fake           fake face app, drawn pictures (QC)
    python tools/face_photo_test.py --photos DIR     the real face app on this PC
        --fetch-unknown   add a generated stranger (thispersondoesnotexist.com)
        --hub URL         also through the running hub (default http://127.0.0.1:8642)

A photo's name says what it must give: known_<Name>.jpg (any word of the
name; known_any = anyone known), unknown*.jpg, noface*.jpg. A missing noface
photo is drawn. Photos of real people never go in git: the repo is public.
"""
import argparse
import importlib.util
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
DRAWN = CODE / "qc" / "data" / "face_photos"
CAMERA = "photo-test"
HUB = "http://127.0.0.1:8642"
STRANGER_URL = "https://thispersondoesnotexist.com/"   # generated, nobody real
KINDS = ("known", "unknown", "noface")
# A busy answer is the rig's own webcam taking their model's turn (the PC's
# watcher sends it up to 4 a second): wait and ask again, and say how often.
TRIES = 6


def _load(name, rel):
    sys.path.insert(0, str(CODE / "apps" / "faces"))
    spec = importlib.util.spec_from_file_location(name, CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("_faces_service_photos", "apps/faces/service.py")
L = _load("_faces_look_photos", "apps/faces/look.py")
friend_api = S.friend_api


# ------------------------------------------------------------------ photos
def expect(path):
    """('known', name) | ('unknown', '') | ('noface', '') | (None, '') from a file name."""
    stem = Path(path).stem
    low = stem.lower()
    if low.startswith("known_"):
        return "known", stem[len("known_"):]
    if low.startswith("unknown"):
        return "unknown", ""
    if low.startswith(("noface", "no_face")):
        return "noface", ""
    return None, ""


def as_jpeg(path, limit):
    """The photo as JPEG bytes under their size limit. -> (bytes, why-not).

    A phone photo is often over their 2 MB, or a PNG: ffmpeg (on the PC for the
    webcam) makes it a 1280-wide JPEG, the kind the webcam road sends anyway."""
    raw = Path(path).read_bytes()
    if raw[:2] == b"\xff\xd8" and len(raw) <= limit:
        return raw, ""
    ff = shutil.which("ffmpeg")
    if not ff:
        return None, "not a JPEG under %d bytes, and no ffmpeg to make it one" % limit
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-i", str(path),
                        "-vf", "scale='min(1280,iw)':-2", "-frames:v", "1", "-q:v", "4",
                        "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                       capture_output=True, timeout=60)
    if r.returncode or r.stdout[:2] != b"\xff\xd8":
        return None, "ffmpeg could not read it: %s" % r.stderr.decode(errors="replace")[:200]
    return r.stdout, ""


def fetch_stranger(folder):
    """A generated face nobody enrolled: their site draws a new one each time."""
    dest = Path(folder) / "unknown_generated.jpg"
    if dest.is_file():
        return dest, ""
    try:
        req = urllib.request.Request(STRANGER_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        return dest, ""
    except (OSError, ValueError) as e:
        return None, "could not fetch a generated stranger (%s)" % e


def photo_list(folder, fetch_unknown=False):
    """[(kind, name, path)] in the order known, unknown, noface - the last
    no-face look makes Voice forget the name again (forget_person)."""
    out, notes = [], []
    if fetch_unknown:
        _got, why = fetch_stranger(folder)
        notes += [why] if why else []
    for p in sorted(Path(folder).iterdir()):
        kind, name = expect(p)
        if kind and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            out.append((kind, name, p))
        elif p.is_file():
            notes.append("%s skipped: name it known_<Name>, unknown or noface" % p.name)
    if not any(k == "noface" for k, _n, _p in out):
        out.append(("noface", "", DRAWN / "noface.jpg"))
    out.sort(key=lambda x: KINDS.index(x[0]))
    return out, notes


# ------------------------------------------------------------------ verdicts
def matches(want, names):
    names = [n for n in names if n]
    if not want or want.lower() == "any":
        return bool(names)
    w = want.lower()
    return any(w in n.lower() or n.lower() in w for n in names)


def judge(kind, want, faces, names):
    """(passed, what was found). faces None = this road does not count them."""
    if kind == "known":
        return matches(want, names), ", ".join(names) or "nobody known"
    if names:
        return False, "named %s" % ", ".join(names)
    if kind == "unknown":
        return faces is None or faces >= 1, "a face nobody knows" if faces != 0 else "no face"
    return not faces, "no face" if not faces else "%d face(s)" % faces


def voice_verdict(kind, want, got):
    """Voice's /identify answer -> (passed, found). It says why it has no name:
    'nobody the face app knows...' or 'no face in that picture...'."""
    if got.get("ok"):
        return judge(kind, want, None, [got.get("person") or ""])
    err = str(got.get("error") or "")
    if err.startswith("nobody"):
        return kind == "unknown", "a face nobody knows"
    if err.startswith("no face"):
        return kind == "noface", "no face"
    return False, err or "no answer"


def _busy(state):
    return state in ("busy", "loading")


# ------------------------------------------------------------------ roads
def road_look(st, jpeg):
    token, why = st.token_now()
    if not token:
        return {"state": "no login", "detail": why}
    for n in range(TRIES):
        began = time.time()
        state, faces, detail = friend_api.look(st.entry(), token, jpeg, CAMERA, timeout=30)
        took = time.time() - began
        if not _busy(state):
            break
        time.sleep(min(4.0, 0.5 * 2 ** n))
    return {"state": state, "detail": detail, "seconds": took, "tries": n + 1,
            "faces": len(faces), "names": [f["who"] for f in faces if f["known"]]}


def road_watcher(st, looker, voice, jpeg):
    """The photo as the camera's frame, then Voice asks the watcher."""
    looker.frames = lambda seen, timeout: (seen + 1, jpeg)
    began = time.time()
    for n in range(TRIES):
        looker.busy = 0
        looker.step(0)
        if st.scenes.get(CAMERA, {}).get("at", 0) >= began:
            break
        time.sleep(min(4.0, 0.5 * 2 ** n))
    else:
        return {"state": looker.status.get("state"), "detail": looker.status.get("why")}
    seen = st.present(CAMERA, 10)
    got = _get_json(voice + "/face?camera=" + CAMERA)
    took = time.time() - began
    return {"state": "ok", "seconds": took, "tries": n + 1, "faces": seen["facesNow"],
            "names": [got.get("person") or ""] if got.get("person") else [],
            "watcher": [p.get("who") for p in seen["people"]]}


def road_identify(base, path, jpeg):
    for n in range(TRIES):
        began = time.time()
        got = _post_jpeg(base + path, jpeg)
        if "busy" not in str(got.get("error") or "") and \
                "loading" not in str(got.get("error") or ""):
            break
        time.sleep(min(4.0, 0.5 * 2 ** n))
    took = time.time() - began
    # Who Voice says is there NOW: a name from the photo before must be gone.
    after = _get_json(base + path.replace("/identify", "/face"))
    return {"answer": got, "seconds": took, "tries": n + 1, "after": after.get("person") or ""}


def _get_json(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": "answered %s" % e.code}
    except (OSError, ValueError) as e:
        return {"ok": False, "error": "not answering (%s)" % e}


def _post_jpeg(url, jpeg, timeout=60):
    req = urllib.request.Request(url, data=jpeg, headers={"Content-Type": "image/jpeg"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": "answered %s" % e.code}
    except (OSError, ValueError) as e:
        return {"ok": False, "error": "not answering (%s)" % e}


# ------------------------------------------------------------------ the rig
def free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_watcher(st):
    """The real watcher's answers (/present, /state) for this State, on a port of its own."""
    handler = type("PhotoHandler", (S.Handler,), {"state": st})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_port


def start_voice(tmp, watcher, env):
    """The real apps/voice/service.py: no speech models, faces from `watcher`."""
    port = free_port()
    cfg = Path(tmp) / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % port,
        "stt": {"enabled": False}, "llm": {"enabled": False}, "tts": {"enabled": False},
        "face": {"on": True, "watcher": watcher + "/state", "rememberSeconds": 3}}),
        encoding="utf-8")
    faq = Path(tmp) / "qa.json"
    faq.write_text('{"faqs": []}', encoding="utf-8")
    log = open(Path(tmp) / "voice.log", "wb")
    proc = subprocess.Popen([sys.executable, "-u", str(CODE / "apps" / "voice" / "service.py"),
                             "--config", str(cfg), "--faq", str(faq), "--port", str(port)],
                            stdout=log, stderr=subprocess.STDOUT, env=env)
    base = "http://127.0.0.1:%d" % port
    deadline = time.time() + 90
    while time.time() < deadline and proc.poll() is None:
        if _get_json(base + "/health", 2).get("ok"):
            return proc, base
        time.sleep(0.3)
    proc.kill()
    raise RuntimeError("Voice did not start - see %s" % (Path(tmp) / "voice.log"))


def listen_feed(st, heard, stop):
    """Count what their live feed (WS events-feed) says while photos are looked
    at: /api/look keeps nothing, so it should say nothing about them."""
    src = st.ws_source()
    token, _why = st.token_now()
    if not (src and token):
        heard.append({"error": "no live feed to listen to"})
        return
    try:
        feed = S.wsclient.connect(S.wsclient.ws_url(st.partner().get("api") or "",
                                                    src.get("path") or "", token))
    except Exception as e:                                   # noqa: BLE001
        heard.append({"error": "the live feed did not connect (%s)" % e})
        return
    try:
        for msg in feed.messages(idle_timeout=1):
            if stop.is_set():
                return
            if msg:
                heard.append(msg)
    except Exception as e:                                   # noqa: BLE001
        heard.append({"error": "the live feed dropped (%s)" % e})
    finally:
        feed.close()


# ------------------------------------------------------------------ fake
FAKE_KNOWN = {"box": [0.34, 0.23, 0.66, 0.77], "face_score": 0.93, "status": "matched",
              "person_id": "u-7", "participant_id": "P0777", "first_name": "Somchai",
              "name": "Somchai Jaidee", "confidence": 0.71, "call_as": "", "title": "",
              "language": "th"}
# A stranger still carries the nearest enrolled person, under the threshold:
# naming them anyway is the mistake this road must catch.
FAKE_STRANGER = {"box": [0.34, 0.23, 0.66, 0.77], "face_score": 0.88, "status": "unknown",
                 "person_id": "u-9", "name": "Closest Guess", "confidence": 0.31}


def fake_rig(tmp):
    """A fake face app that knows the drawn pictures, and the env pointing at it."""
    sys.path.insert(0, str(CODE / "qc" / "lib"))
    import fake_friend
    photos = [("known", "Somchai", DRAWN / "drawn_known.jpg"),
              ("unknown", "", DRAWN / "drawn_unknown.jpg"),
              ("noface", "", DRAWN / "noface.jpg")]
    by_bytes = {photos[0][2].read_bytes(): [FAKE_KNOWN],
                photos[1][2].read_bytes(): [FAKE_STRANGER]}
    fake = fake_friend.FakeFriend(offers={"look"})
    fake.answer = lambda jpeg: by_bytes.get(jpeg, [])
    fake.delay = 0.08               # their model on the PC, 2026-10-15: 0.08-0.35 s
    sys.path.insert(0, str(CODE / "tools"))
    import registry
    entry = dict(registry.load(CODE / "config" / "partners.json")["reconize"], api=fake.url)
    partners = Path(tmp) / "partners.json"
    partners.write_text(json.dumps({"reconize": entry}), encoding="utf-8")
    login = Path(tmp) / "faces_login.json"
    login.write_text(json.dumps({"reconize": {"username": "qc", "password": "qc"}}),
                     encoding="utf-8")
    env = dict(os.environ, MICE_PARTNERS=str(partners), MICE_FACES_LOGIN=str(login))
    os.environ["MICE_FACES_LOGIN"] = str(login)
    st = S.State("reconize")
    st.partners = {"reconize": entry}
    st._live, st._live_at = entry, 10 ** 12          # no re-probe of a real app
    return fake, st, env, photos


# ------------------------------------------------------------------ run
def run(photos, st, env, tmp, hub=None, feed=False):
    """Every photo down every road. -> {"rows": [...], "feed": [...], "passed": bool}"""
    friend_api._specs.clear()
    st.look = {"holdSeconds": 10, "staleSeconds": 5}
    st.partner()
    looker = L.Looker(st, CAMERA, None, per_second=4)
    st.lookers.append(looker)
    srv, watcher = start_watcher(st)
    proc, voice = start_voice(tmp, watcher, env)
    heard, stop = [], threading.Event()
    if feed:
        threading.Thread(target=listen_feed, args=(st, heard, stop), daemon=True).start()
        time.sleep(1.0)
    limit = int(friend_api.asks(st.entry(), "look").get("maxBytes") or 2 * 1024 * 1024)
    rows = []
    try:
        for kind, want, path in photos:
            row = {"photo": Path(path).name, "kind": kind, "want": want, "roads": {}}
            rows.append(row)
            jpeg, why = as_jpeg(path, limit)
            if jpeg is None:
                row["error"] = why
                continue
            got = road_look(st, jpeg)
            ok, found = (judge(kind, want, got["faces"], got["names"])
                         if got["state"] == "ok" else (False, got["state"] + ": " + got["detail"]))
            row["roads"]["look"] = dict(got, passed=ok, found=found)
            got = road_watcher(st, looker, voice, jpeg)
            ok, found = (judge(kind, want, got["faces"], got["names"])
                         if got["state"] == "ok" else (False, "%s: %s" % (got["state"], got["detail"])))
            row["roads"]["watcher"] = dict(got, passed=ok, found=found)
            for road, base, where in (("voice", voice, "/identify"),
                                      ("hub", hub, "/api/voice/identify")):
                if not base:
                    continue
                got = road_identify(base, where, jpeg)
                ok, found = voice_verdict(kind, want, got["answer"])
                # Our own Voice only: the running one also sees the live webcam.
                if road == "voice" and kind != "known" and got["after"]:
                    ok, found = False, "still says %s" % got["after"]
                row["roads"][road] = dict(got, passed=ok, found=found)
    finally:
        stop.set()
        proc.kill()
        srv.shutdown()
    passed = all(r.get("roads") and not r.get("error")
                 and all(x["passed"] for x in r["roads"].values()) for r in rows)
    return {"rows": rows, "feed": heard, "passed": passed}


def report(result, out=print):
    out("%-24s %-8s %-8s %-6s %-28s %s" % ("photo", "expect", "road", "", "found", "time"))
    times = {}
    for r in result["rows"]:
        if r.get("error"):
            out("%-24s %-8s %s" % (r["photo"][:24], r["kind"], "SKIPPED: " + r["error"]))
            continue
        first = True
        for road, x in r["roads"].items():
            secs = x.get("seconds")
            if secs is not None:
                times.setdefault(road, []).append(secs)
            extra = ""
            if road == "look" and x.get("detail"):
                extra = " (their model %s)" % x["detail"]
            if x.get("tries", 1) > 1:
                extra += " after %d busy tries" % (x["tries"] - 1)
            out("%-24s %-8s %-8s %-6s %-28s %s" % (
                r["photo"][:24] if first else "", r["kind"] if first else "", road,
                "PASS" if x["passed"] else "FAIL", str(x["found"])[:28],
                ("%.2f s" % secs if secs is not None else "-") + extra))
            first = False
    out("")
    for road, ts in times.items():
        out("%-8s %d looks: fastest %.2f s, middle %.2f s, slowest %.2f s"
            % (road, len(ts), min(ts), statistics.median(ts), max(ts)))
    if result.get("feed"):
        msgs = [m for m in result["feed"] if "error" not in m]
        errs = [m["error"] for m in result["feed"] if "error" in m]
        out("their live feed: %d message(s) while the photos were looked at%s"
            % (len(msgs), (" - " + "; ".join(errs)) if errs else ""))
    out("RESULT: %s" % ("PASS" if result["passed"] else "FAIL"))


def main(argv=None):
    # A Thai name on a Windows cp1252 console killed tools mid-run (sabotage.py).
    for out in (sys.stdout, sys.stderr):
        try:
            out.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fake", action="store_true", help="a fake face app and drawn pictures")
    ap.add_argument("--photos", help="folder of known_<Name> / unknown / noface photos")
    ap.add_argument("--fetch-unknown", action="store_true",
                    help="add a generated stranger's face to the folder first")
    ap.add_argument("--hub", nargs="?", const=HUB, default=None,
                    help="also through the running hub (default %s)" % HUB)
    ap.add_argument("--no-feed", action="store_true", help="do not listen to their live feed")
    ap.add_argument("--json", help="write the results here too")
    a = ap.parse_args(argv)
    if bool(a.fake) == bool(a.photos):
        ap.error("give --fake or --photos DIR")
    tmp = tempfile.mkdtemp(prefix="mice_photos_")
    if a.fake:
        fake, st, env, photos = fake_rig(tmp)
        notes, feed = [], False
    else:
        photos, notes = photo_list(a.photos, a.fetch_unknown)
        st, env, feed, fake = S.State("reconize"), dict(os.environ), not a.no_feed, None
    for n in notes:
        print("note: " + n)
    try:
        result = run(photos, st, env, tmp, hub=a.hub, feed=feed)
    finally:
        if fake:
            fake.stop()
    report(result)
    if a.json:
        Path(a.json).write_text(json.dumps(result, ensure_ascii=False, indent=1,
                                           default=str), encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
