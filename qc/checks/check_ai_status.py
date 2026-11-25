"""AI work shows bounded, link-free handoff summaries to Hub administrators."""
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import qc as F

AREA = "hub"
TITLE = "AI work reads local handoffs with a size bound, plain wording and admin access"
SLOW = False


class Handoffs:
    def __init__(self, root):
        self.root = root
        self.task_dir = root / "handoff" / "tasks"
        self.task_dir.mkdir(parents=True)
        (root / "HANDOFF.md").write_text("# Handoff", encoding="utf-8")
        self.now = time.time()

    def add(self, name, text):
        path = self.task_dir / (name + ".md")
        path.write_bytes(text.encode("utf-8"))
        return path

    def stamp(self, hours=0):
        return datetime.fromtimestamp(self.now - hours * 3600, timezone.utc).isoformat()


def check_parser(t, AiStatus, folder):
    reader = AiStatus(folder.root)
    t.eq(reader.read()["tasks"], [], "an empty task folder has no rows")
    folder.add("empty", "")
    folder.add("current", f"""# Check the show
Owner: gpt-codex:session (GPT-6.2 Sol)
Updated: {folder.stamp()}
Branch: claude/show
Last commit: e3726c9 details

## Doing now
Check the [phone view](https://example.test/show).
API key: fixture-only
```
Do not display code blocks.
```
## Done
Do not display past notes.
## Blocked
None.
""")
    folder.add("finished", "# Finish the review\nOwner: Claude Sonnet 4.5\nStatus: complete")
    folder.add("waiting", "# Wait for approval\nOwner: Gemini\n## Blocked\nNo approval received yet.")
    folder.add("old", f"# Old work\nOwner: Codex\nUpdated: {folder.stamp(8)}")
    folder.add("huge", "# Big task\nOwner: Claude\n" + ("large line\n" * 200000) +
               "\n## Doing now\nOutside the read limit.")
    rows = {x["name"]: x for x in reader.read()["tasks"]}
    t.eq(set(rows), {"empty", "Check the show", "Finish the review", "Wait for approval",
                     "Old work", "Big task"}, "all new and odd task files appear")
    t.eq(rows["empty"]["state"], "stale", "an ownerless blank file cannot imply active work")
    task = rows["Check the show"]
    t.eq((task["agent"], task["model"], task["branch"], task["commit"], task["state"]),
         ("Codex", "gpt-6.2 sol", "claude/show", "e3726c9", "working"), "working card shows recorded fields")
    t.eq(task["activity"], "Check the phone view.", "only safe text from Doing now is exposed")
    t.eq([rows[name]["state"] for name in ("Finish the review", "Wait for approval", "Old work")],
         ["done", "blocked", "stale"], "finished, waiting and old handoffs stay distinct")
    t.eq(rows["Big task"]["activity"], "", "a heading beyond the read limit cannot appear")
    check_loose_dates(t, AiStatus)
    return task


def check_loose_dates(t, AiStatus):
    """Real task files write dates as words, not strict ISO: the age must still come from the date, not the file time."""
    read = AiStatus._updated
    t.eq(read("2026-10-28 19:40 (Bangkok)", -1), read("2026-10-28T19:40:00+07:00", -1),
         "a Bangkok clock stamp with a zone word is read as that time")
    t.eq(read("2026-10-29 11:04 UTC", -1), read("2026-10-29T11:04:00+00:00", -1), "a UTC stamp is read as UTC")
    t.eq(read("2026-10-29 15:05 (+07)", -1), read("2026-10-29T15:05:00+07:00", -1), "a +07 offset is read")
    t.eq(read("2026-11-06 (Bangkok)", -1), read("2026-11-06T00:00:00+07:00", -1), "a date without a time is read as Bangkok midnight")
    t.eq(read("2569-10-25 15:49 (Bangkok)", -1), read("2026-10-25T15:49:00+07:00", -1), "a Buddhist-era year is converted")
    t.eq(read("no date here", 42), 42, "a file with no date falls back to its file time")


def check_worktree(t, AiStatus, root):
    primary = Handoffs(root / "primary")
    primary.add("paired", f"# Prior copy\nOwner: Claude\nUpdated: {primary.stamp(1)}")
    linked = Handoffs(root / "linked")
    linked.add("paired", f"# Latest copy\nOwner: Gemini\nUpdated: {linked.stamp()}")
    git = primary.root / ".git"
    meta = git / "worktrees" / "linked"
    meta.mkdir(parents=True)
    (meta / "gitdir").write_text(str(linked.root / ".git"), encoding="utf-8")
    (meta / "commondir").write_text("../..", encoding="utf-8")
    (meta / "HEAD").write_text("ref: refs/heads/local/work", encoding="utf-8")
    (linked.root / ".git").write_text(f"gitdir: {meta}", encoding="utf-8")
    for checkout in (primary.root, linked.root):
        cards = AiStatus(checkout).read()["tasks"]
        t.eq([(x["name"], x["branch"]) for x in cards],
             [("Latest copy", "local/work")], "newest handoff wins across linked checkout copies")


def check_route(t, folder, task):
    base, hub = F.start_hub()
    url = base + "/api/ai-status"
    # Use actual Hub sessions in a disposable store, with isolated task files.
    with patch.object(hub, "DATA", folder.root):
        code, body = F.get(url)
        t.eq(code, 200, "the administrator receives the status list")
        t.ok(task in json.loads(body).get("tasks", []), "the route returns the live task records", body[:100])
        t.eq(F.post(url)[0], 404, "AI work has no write route")
        F.logout_qc()
        code, body = F.get(url)
        t.eq((code, json.loads(body).get("tasks")), (401, None), "signed-out requests receive no task data")
        auth = hub.auth()
        auth.add_user("ai-status-test", "disposable-code")
        session, _ = auth.login("disposable-code", "qc-ai-status", "ai-status-test")
        with patch.object(F, "_cookie", [f"{hub.hub_auth.COOKIE}={session}"]):
            code, body = F.get(url)
            t.eq((code, json.loads(body).get("tasks")), (403, None),
                 "ordinary signed-in users receive no task data")
        F.login(base)
    code, body = F.get(base + "/api/apps")
    t.ok(code == 200 and any(app["id"] == "ai-status" for app in json.loads(body)["apps"]),
         "the Tools list contains AI work", str(code))
    t.eq(F.get(base + "/app/ai-status/")[0], 200, "the Tools card opens the AI work page")


def check_words(t):
    from check_designer_first import js_strings, visible_text

    app = F.CODE / "apps" / "ai-status"
    words = json.loads((F.CODE / "qc/data/designer_words.json").read_text(encoding="utf-8"))["banned"]
    copy = visible_text(app / "index.html") + " " + js_strings(app / "status.js")
    t.eq([word for word in words if re.search(r"\b" + re.escape(word) + r"\b", copy)],
         [], "AI work uses designer-first wording")
    for lang, native in {"en": "[a-zA-Z]", "th": r"[฀-๿]",
                         "ja": r"[぀-ヿ]", "zh": r"[一-鿿]"}.items():
        phrases = json.loads((F.CODE / "shared/web/lang" / (lang + ".json")).read_text(encoding="utf-8"))["strings"]
        t.ok(all(re.search(native, phrases.get(key, "")) for key in
                     ("AI work", "Loading AI work…", "No recent update", "Sign in to view AI work.")),
             f"{lang} has the AI work status words", lang)


def run(t):
    sys.path.insert(0, str(F.CODE / "main_python"))
    from ai_status import AiStatus

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        folder = Handoffs(root / "single")
        task = check_parser(t, AiStatus, folder)
        check_worktree(t, AiStatus, root)
        check_route(t, folder, task)
    check_words(t)
