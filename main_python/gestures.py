"""Arm gestures while the robot talks (A46-1, user 2026-10-22).

*สุ่มท่าทางออกมาให้เข้ากับคำที่พูดแล้วส่งทำพร้อมกัน*: the words of an answer
pick gestures (config/gestures.json), random small "beats" fill the gaps, and
the result is one list of show steps for POST /api/play, timed over how long
the sound lasts.

This file never decides a POSE. Nong Studio fits each gesture to the robot's
own sizes and limits (IK, collisionAt, safe_path.js) and posts the fit here;
a gesture with no fit, or whose words-and-keys changed since, is left out.
What this file adds is timing: when each gesture starts, how fast (the
manner's tempo, a little random), and how the arm gets between them - only
along legs Studio checked: rest -> gesture -> rest, or straight from one
gesture to the next when Studio listed that pair as clear (`direct`).

The user's own gestures and switches live in a git-ignored file beside the
saved moves (STUDIO/gestures.json, or MICE_GESTURES_MINE): a pull never fights
what was made on that PC.
"""
import copy
import hashlib
import json
import os
import random
import re
import threading
from pathlib import Path

_lock = threading.Lock()
_recent = []                 # ids picked lately, across answers (keepRecent)
LATIN = re.compile(r"[a-z]", re.I)


def profile_folder(studio):
    """The same local character selected by Voice; an explicit QC store wins."""
    if os.environ.get("MICE_GESTURES_MINE"):
        return None
    code = Path(__file__).resolve().parent.parent
    spec = json.loads((code / "config/voice_profiles.json").read_text(encoding="utf-8"))
    config = Path(os.environ.get("MICE_VOICE_CONFIG") or (code / "config/voice.json"))
    root = (config.parent / spec["folder"]).resolve()
    pointer = root / "active.json"
    if not pointer.exists():
        return None
    name = json.loads(pointer.read_text(encoding="utf-8"))["name"]
    if (not isinstance(name, str) or not name or len(name) > 80 or name != name.strip()
            or name.startswith(".") or name.endswith(".")
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", name)):
        raise ValueError("Choose a saved character in Voice first.")
    folder = root / name
    if (not folder.is_dir() or folder.is_symlink() or folder.is_junction()
            or folder.resolve().parent != root):
        raise ValueError("That character folder cannot be used.")
    return folder


def mine_path(studio):
    if os.environ.get("MICE_GESTURES_MINE"):
        return Path(os.environ["MICE_GESTURES_MINE"])
    folder = profile_folder(studio)
    path = (folder or Path(studio)) / "gestures.json"
    if folder and (path.is_symlink() or path.resolve().parent != folder.resolve()):
        raise ValueError("That move file is outside this character.")
    return path


def character_state(studio, path=None):
    path = Path(path) if path is not None else mine_path(studio)
    folder = path.parent if not os.environ.get("MICE_GESTURES_MINE") and path != Path(studio) / "gestures.json" else None
    if folder is None:
        return {"character": "", "gestureRevision": "", "readOnly": False}
    revision = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"character": folder.name, "gestureRevision": revision,
            "readOnly": folder.name.lower() == "default"}


def read_mine(studio):
    p = mine_path(studio)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except (OSError, ValueError):
        return {}


def library(shipped, mine):
    """The shipped library with this PC's changes on top. A gesture set to
    null in `mine` is removed; one given as a dict replaces those fields."""
    lib = copy.deepcopy(shipped)
    for k in ("on", "robot"):
        if k in mine:
            lib[k] = mine[k]
    lib["events"] = dict(lib.get("events") or {}, **(mine.get("events") or {}))
    gs = lib.setdefault("gestures", {})
    for gid, g in (mine.get("gestures") or {}).items():
        if g is None:
            gs.pop(gid, None)
        elif isinstance(g, dict):
            gs[gid] = dict(gs.get(gid) or {}, **g)
    return lib


def merge_mine(mine, change):
    """A Studio save: switches and gestures merged in, never the whole file."""
    out = dict(mine)
    for k in ("on", "robot"):
        if k in change:
            out[k] = change[k]
    for k in ("events", "gestures"):
        if isinstance(change.get(k), dict):
            out[k] = dict(out.get(k) or {}, **change[k])
    if isinstance(change.get("fit"), dict):
        out["fit"] = change["fit"]
    return out


def fitted(lib, fit):
    """{variant id: fit entry} for the gestures whose fit matches the
    library as it is now (keys unchanged since Studio fitted them)."""
    out = {}
    if (fit or {}).get("restDef") != (lib.get("rest") or {}).get("keys"):
        return out                                # the resting hands changed
    defs = (fit or {}).get("defs") or {}
    for gid, g in (lib.get("gestures") or {}).items():
        if defs.get(gid) != g.get("keys"):
            continue                              # changed or never fitted
        for vid in (gid, gid + "~m"):
            e = ((fit or {}).get("gestures") or {}).get(vid)
            if e and e.get("keys"):
                out[vid] = dict(e, id=gid, label=g.get("label") or gid, mirrored=vid != gid)
    return out


def _hits(text, gestures):
    """(position, gesture id, word) for every word of every gesture in the
    text. Thai, Japanese and Chinese have no spaces: a word is found inside
    the text. A Latin word must stand alone ("hi" is not in "this")."""
    low = text.lower()
    out = []
    for gid, g in gestures.items():
        for words in (g.get("words") or {}).values():
            for w in words or []:
                w = str(w).lower().strip()
                if not w:
                    continue
                if LATIN.search(w):
                    pat = r"(?<![a-z])" + re.escape(w) + r"(?![a-z])"
                    out += [(m.start(), gid, w) for m in re.finditer(pat, low)]
                else:
                    i = low.find(w)
                    while i >= 0:
                        out.append((i, gid, w))
                        i = low.find(w, i + 1)
    # A word inside a longer one is not said on its own: "คุณ" in "ขอบคุณ"
    # is a thank-you, not a "you". The longest word at a place wins.
    out.sort(key=lambda h: (h[0], -len(h[2])))
    kept, end = [], -1
    for h in out:
        if h[0] + len(h[2]) <= end:
            continue
        kept.append(h)
        end = max(end, h[0] + len(h[2]))
    return kept


def _speed_floor(a, b, dps):
    """ms the biggest joint change needs at `dps` (the board floors T too)."""
    return max(abs(x - y) for x, y in zip(a, b)) / max(1.0, dps) * 1000.0


def plan(lib, fit, text, lang="", manner="", event="", ms=0, seed=None):
    """Pick and time gestures for one spoken answer. Returns a dict: ok,
    steps (for /api/play), picks [{id,label,word,at,mirrored}], ms, total_ms;
    or ok False with `why` (and `off` when gestures are switched off)."""
    text = str(text or "").strip()
    ev = (lib.get("events") or {}).get(event or "") or {}
    if not lib.get("on", True) or ev.get("on") is False:
        return {"ok": False, "off": True,
                "why": "gestures are off" + (" for " + event if ev.get("on") is False else "")}
    if not text:
        return {"ok": False, "why": "nothing is said"}
    use = fitted(lib, fit)
    rest = (fit or {}).get("rest") or {}
    rig = (fit or {}).get("rig") or {}
    if not use or not rest.get("keys") or not rig.get("home"):
        return {"ok": False, "why": "the gestures are not fitted to this robot yet: "
                                    "open Nong Studio once and it fits them itself"}
    mans = lib.get("manners") or {}
    mc = dict(mans.get("_default") or {}, **(mans.get(ev.get("manner") or manner or "") or {}))
    tempo = float(mc.get("tempo", 1.0))
    rnd = random.Random(seed)
    pace = lib.get("pace") or {}
    cps = float(pace.get(lang, pace.get("", 12)) or 12)
    total = float(ms) if ms and float(ms) > 0 else max(800.0, len(text) / cps * 1000.0)
    lead = float(lib.get("leadMs", 300))
    gap = float(lib.get("minGapMs", 250))
    rest_gap = float(lib.get("restGapMs", 900))
    jit = float(lib.get("jitter", 0.15))
    dps = float(lib.get("maxDps", 150))
    lo, hi = rig.get("min") or [0] * 10, rig.get("max") or [180] * 10
    clamp = lambda p: [min(hi[j], max(lo[j], float(v))) for j, v in enumerate(p)]  # noqa: E731

    def length(vid):
        # out of rest, the gesture, back to rest: what the arm is busy for
        g = use[vid]
        legs = g.get("in", []) + g["keys"] + g.get("out", []) + rest.get("keys", [])[-1:]
        return sum(float(x.get("t", 400)) * tempo * (1 + jit) + float(x.get("hold", 0)) for x in legs)

    def variant(gid):
        m = gid + "~m"
        g = (lib.get("gestures") or {}).get(gid) or {}
        if g.get("mirror") and m in use and rnd.random() < float(lib.get("mirrorChance", 0.5)):
            return m
        return gid if gid in use else (m if m in use else None)

    # 1. words: each gesture lands on its word, if the arm is free by then
    gest = {gid: g for gid, g in (lib.get("gestures") or {}).items()
            if gid in use or gid + "~m" in use}
    placed, free = [], -gap                 # a gesture on the very first word is fine
    n = max(1, len(text))
    # every gesture's words take their place, fitted or not: a word inside a
    # longer one belongs to the longer one even when that gesture is left out
    for pos, gid, word in _hits(text, lib.get("gestures") or {}):
        if gid not in gest:
            continue
        at = max(0.0, pos / n * total - lead)
        vid = variant(gid)
        if vid is None or at > total:
            continue
        if at < free + gap:
            # the arm is still busy: a little late is better than never
            if free + gap - at > float(lib.get("lateMs", 1200)):
                continue
            at = free + gap
        placed.append({"at": at, "vid": vid, "word": word})
        free = at + length(vid)
    # 2. beats: random small gestures in the gaps, the manner's number of them
    # A seeded plan (Studio's Show, QC) is the same every time, so it neither
    # reads nor writes the memory of what was picked lately.
    with _lock:
        recent = list(_recent) if seed is None else []
    beats = [gid for gid, g in gest.items() if g.get("beat")]
    want = int(round(float(mc.get("beats", 0.3)) * total / 1000.0))
    prefer = mc.get("prefer") or {}
    tries = 0
    while beats and want > 0 and tries < 40:
        tries += 1
        pool = [b for b in beats if b not in recent[-int(lib.get("keepRecent", 2)):]] or beats
        gid = rnd.choices(pool, weights=[float(prefer.get(b, 1)) for b in pool])[0]
        vid = variant(gid)
        if vid is None:
            continue
        need = length(vid) + 2 * gap
        edges = [0.0] + [p["at"] + length(p["vid"]) for p in placed]
        starts = [p["at"] for p in placed] + [total]
        room = [(e, s) for e, s in zip(edges, starts) if s - e >= need]
        if not room:
            break
        e, s = rnd.choice(room)
        at = e + gap + rnd.random() * (s - e - need)
        placed.append({"at": at, "vid": vid, "word": ""})
        placed.sort(key=lambda p: p["at"])
        recent.append(gid)
        want -= 1
    if seed is None:
        with _lock:
            _recent[:] = (recent + [use[p["vid"]]["id"] for p in placed if p["word"]])[-8:]
    # 3. steps: home -> rest, each gesture from rest (or straight from the one
    # before when Studio checked that pair), back to rest, home at the end
    steps, now = [], 0.0
    home = clamp(rig["home"])
    steps.append({"pose": home, "t": 0, "hold": 0})

    def go(legs):
        nonlocal now
        for leg in legs:
            p = clamp(leg["pose"])
            want_t = float(leg.get("t", 400)) * (tempo if not leg.get("via") else 1.0)
            want_t *= 1.0 + rnd.uniform(-jit, jit)
            t = int(round(max(80.0, _speed_floor(steps[-1]["pose"], p, dps), want_t)))
            hold = int(round(float(leg.get("hold", 0))))
            steps.append({"pose": p, "t": t, "hold": hold})
            now += t + hold

    def wait_until(at):
        nonlocal now
        if at > now:
            steps[-1]["hold"] += int(round(at - now))
            now = at

    direct = set((fit or {}).get("direct") or [])
    go(rest.get("in", []) + rest["keys"])
    at_rest = True
    late = float(lib.get("lateMs", 1200))
    done = []
    for i, p in enumerate(placed):
        g = use[p["vid"]]
        if now > total or now - p["at"] > late:
            # the words have gone by: let it go. The arm only ever goes straight
            # between the pair Studio checked, so it rests before anything else.
            if not at_rest:
                go(use[done[-1]["vid"]].get("out", []) + rest["keys"][-1:])
                at_rest = True
            continue
        done.append(p)
        wait_until(p["at"])
        p["at"] = int(round(now))           # where it really starts
        go(([] if not at_rest else g.get("in", [])) + g["keys"])
        nxt = placed[i + 1] if i + 1 < len(placed) else None
        if nxt and (now > total or now - nxt["at"] > late):
            nxt = None
        if nxt and nxt["at"] - now < rest_gap and (p["vid"] + ">" + nxt["vid"]) in direct:
            at_rest = False
        else:
            go(g.get("out", []) + rest["keys"][-1:])
            at_rest = True
    wait_until(total)
    if not at_rest:                           # the last went straight on: rest first
        go(use[done[-1]["vid"]].get("out", []) + rest["keys"][-1:])
    go(rest.get("out", []) + [{"pose": home, "t": 600}])
    picks = [{"id": use[p["vid"]]["id"], "label": use[p["vid"]]["label"],
              "mirrored": use[p["vid"]]["mirrored"], "word": p["word"], "at": p["at"]}
             for p in done]
    return {"ok": True, "steps": steps, "picks": picks, "ms": int(round(total)),
            "total_ms": int(round(now))}
