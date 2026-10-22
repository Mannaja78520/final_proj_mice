"""What the voice app's questions are about, and which answers give a prize (A47-3).

Called by the hub after every /api/voice/ask it forwards (main.py voice_proxy),
so it sees the question AND the answer without touching the voice helper:

  * topic: the first topic in config/voice_topics.json whose pattern matches
    the question (or the FAQ answer's own "topic"), else "other";
  * one CSV row per question in <data>/.local/voice/questions.csv (people's
    names and words: never under apps/, never in git);
  * prize: the first rule in config/voice_prizes.json whose `when` fits
    (topic, saved-answer question, answer source, a pattern on the question
    or the answer) names an item type; the hub's gacha brain gives it to the
    person asking, and its words are added to the reply (`prize`).

Everything is data: a new topic or prize rule is one entry, no code.
"""
import csv
import json
import re
import time
from pathlib import Path

FIELDS = ["time", "lang", "person", "question", "topic", "source", "answer",
          "prize", "prize_result"]


def _load(path):
    try:
        txt = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    lines = [ln for ln in txt.splitlines() if not ln.lstrip().startswith("//")]
    try:
        return json.loads("\n".join(lines) or "{}")
    except ValueError:
        return {}


def _hit(patterns, text):
    for p in patterns or []:
        try:
            if re.search(p, text or "", re.I):
                return True
        except re.error:
            continue                       # one bad entry must not stop the rest
    return False


def say_prize(prizes_path):
    """Should the prize's words be added to the spoken answer (config "say")."""
    return _load(prizes_path).get("say", True) is not False


def topic_of(question, answer, topics):
    """(topic id) from the question; the answer's own topic when it has one."""
    if answer.get("topic"):
        return str(answer["topic"])
    for t in topics.get("topics") or []:
        if _hit(t.get("patterns"), question):
            return str(t.get("id") or "other")
    return str(topics.get("fallback") or "other")


def prize_for(question, answer, topic, rules, event=""):
    """The item type the first matching rule gives, or ''. A rule's
    `when.event` only fits while that event is the open one (A47-8)."""
    if not rules.get("enabled", True):
        return ""
    if answer.get("prize"):                       # a saved answer may name it itself
        return str(answer["prize"])
    for r in rules.get("rules") or []:
        w = r.get("when") or {}
        if w.get("topic") and w["topic"] != topic:
            continue
        if w.get("event") and str(w["event"]).strip().lower() != str(event or "").strip().lower():
            continue
        if w.get("source") and w["source"] != answer.get("source"):
            continue
        if w.get("question") and not _hit(w["question"] if isinstance(w["question"], list)
                                          else [w["question"]], question):
            continue
        if w.get("answer") and not _hit(w["answer"] if isinstance(w["answer"], list)
                                        else [w["answer"]], answer.get("answer") or ""):
            continue
        return str(r.get("item") or "")
    return ""


class Questions:
    def __init__(self, topics_path, prizes_path, data_dir, give=None, clock=time.time,
                 event=None):
        self.topics_path = Path(topics_path)
        self.prizes_path = Path(prizes_path)
        self.data = Path(data_dir)
        self.give = give                  # give(item, person) -> gacha dispense answer
        self.event = event                # event() -> the prize machines' event name
        self.clock = clock

    @property
    def csv_path(self):
        return self.data / "questions.csv"

    def after_ask(self, req, answer):
        """Log one question; give a prize when a rule says so. -> extra reply fields."""
        question = str(req.get("text") or "")
        if not question or not isinstance(answer, dict):
            return {}
        topic = topic_of(question, answer, _load(self.topics_path))
        rules = _load(self.prizes_path)
        ev = self.event() if self.event else ""
        item = prize_for(question, answer, topic, rules, ev) if answer.get("ok") else ""
        person = str(answer.get("person") or req.get("person") or "")
        extra = {"topic": topic}
        res = ""
        if item and self.give:
            got = self.give(item, person) or {}
            res = "given" if got.get("ok") else (got.get("reason") or "refused")
            extra["prize"] = {"item": item, "ok": bool(got.get("ok")),
                              "machine": got.get("machine", ""),
                              "message": got.get("message", ""),
                              "reason": got.get("reason", "")}
        self.data.mkdir(parents=True, exist_ok=True)
        new = not self.csv_path.is_file()
        with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow({"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.clock())),
                        "lang": answer.get("lang", ""), "person": person,
                        "question": question[:500], "topic": topic,
                        "source": answer.get("source", "") if answer.get("ok") else "failed",
                        "answer": str(answer.get("answer") or "")[:300],
                        "prize": item, "prize_result": res})
        return extra

    def rows(self):
        if not self.csv_path.is_file():
            return []
        with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def stats(self, day=""):
        """Counts for the Voice tab's charts: per topic, per hour, per source,
        per language, top questions; `day` (YYYY-MM-DD) narrows it."""
        out = {"topic": {}, "hour": {str(h): 0 for h in range(24)}, "source": {},
               "lang": {}, "prize": {}, "question": {}, "unsaved": {}, "total": 0, "days": []}
        days = set()
        for r in self.rows():
            d = (r.get("time") or "")[:10]
            days.add(d)
            if day and d != day:
                continue
            out["total"] += 1
            for k in ("topic", "source", "lang"):
                v = r.get(k) or "-"
                out[k][v] = out[k].get(v, 0) + 1
            if r.get("prize"):
                out["prize"][r["prize"]] = out["prize"].get(r["prize"], 0) + 1
            h = (r.get("time") or "")[11:13]
            if h.isdigit():
                out["hour"][str(int(h))] += 1
            q = (r.get("question") or "").strip().lower()
            out["question"][q] = out["question"].get(q, 0) + 1
            if r.get("source") != "faq":       # no saved answer yet: worth writing one
                out["unsaved"][q] = out["unsaved"].get(q, 0) + 1
        for k in ("question", "unsaved"):
            out[k] = dict(sorted(out[k].items(), key=lambda kv: -kv[1])[:15])
        out["days"] = sorted(days)
        return out


def save_topics(path, topics, fallback=None):
    """Write the topic list from the Voice page (A47-8). -> (ok, why).
    Every topic needs an id and its patterns must compile, so one typo on
    the page cannot silently send every question to "other"."""
    clean, seen = [], set()
    for t in topics if isinstance(topics, list) else []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        pats = t.get("patterns") or []
        pats = [str(x).strip() for x in (pats if isinstance(pats, list) else [pats]) if str(x).strip()]
        if not tid or tid in seen:
            return False, "every topic needs its own short name"
        for x in pats:
            try:
                re.compile(x)
            except re.error as e:
                return False, "the words for %s could not be read (%s)" % (tid, e)
        seen.add(tid)
        clean.append({"id": tid, "label": str(t.get("label") or tid), "patterns": pats})
    old = _load(path)
    data = {"fallback": str(fallback or old.get("fallback") or "other"), "topics": clean}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    tmp.replace(p)
    return True, ""
