"""Read only the published progress fields of local MICE handoff files."""
import json
import re
import stat
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HEAD_BYTES = 16 * 1024
DEFAULT_STALE_HOURS = 6
TITLE = re.compile(r"^#\s+(.+)$", re.M)
SECTION = re.compile(r"^##\s+([^\n]+)\s*$", re.M)
FIELD = re.compile(r"^(Owner|Model|Updated|Status|State|Branch|Last commit):[ \t]*(.*)$", re.M | re.I)
SHA = re.compile(r"[a-f0-9]{7,40}\b", re.I)
BRANCH = re.compile(r"[\w.-]+(?:/[\w.-]+)*", re.ASCII)
SECRET = re.compile(
    r"\b(?:password|passwd|api[ _-]?key|secret|credential|(?:access|refresh)[ _-]?token|"
    r"private[ _-]?key|authorization|bearer|cookie)\b|\b(?:token|pwd)\s*[:=]|"
    r"\b(?:sk-[\w-]+|gh[pousr]_[\w]+|github_pat_[\w]+|AKIA[A-Z0-9]{16}|"
    r"eyJ[\w-]+\.[\w-]+\.[\w-]+)\b|\b[A-Za-z0-9_-]{28,}\b",
    re.I,
)
LINK = re.compile(r"!?\[([^\]]*)\]\([^\n]*?\)|<?\b(?:[a-z]+://|www\.)\S+>?|"
                  r"\b[A-Za-z]:[/\\]\S+|\\\\\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]+",
                  re.I)
MODELS = re.compile(r"\b(?:gpt-\d[\w.-]*(?: (?:sol|luna|astra|terra))?|"
                    r"gemini [\d.]+(?: (?:flash|pro))?|"
                    r"claude (?:opus|sonnet|haiku)(?: [\d.]+)?)\b", re.I)


class AiStatus:
    def __init__(self, root, stale_hours=DEFAULT_STALE_HOURS):
        self.root = Path(root).resolve()
        self.stale_seconds = stale_hours * 3600

    @classmethod
    def from_config(cls, root, config):
        try:
            hours = json.loads(Path(config).read_text(encoding="utf-8")).get("staleHours")
            if type(hours) not in (int, float) or not 0 < hours <= 720:
                hours = DEFAULT_STALE_HOURS
        except (OSError, ValueError, TypeError, AttributeError):
            hours = DEFAULT_STALE_HOURS
        return cls(root, hours)

    @staticmethod
    def _plain(value, limit):
        value = LINK.sub(lambda m: m[1] or "", value)
        if SECRET.search(value):
            return ""
        value = re.sub(r"`([^`]*)`", r"\1", value)
        value = re.sub(r"<[^>]*>|[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]", " ", value)
        return " ".join(value.strip(" -*").split())[:limit]

    @classmethod
    def _activity(cls, body):
        lines = []
        fenced = False
        for line in body.splitlines():
            if line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
            elif not fenced and not line.startswith(("    ", "\t")):
                line = cls._plain(line, 360)
                if line:
                    lines.append(line)
        text = " ".join(lines)
        return text if len(text) <= 360 else text[:359].rstrip() + "…"

    @staticmethod
    def _updated(value, mtime):
        value = value.strip()
        try:
            return datetime.fromisoformat(value).timestamp()
        except (ValueError, OverflowError, OSError):
            pass
        # Task files say things like "2026-10-28 19:40 (Bangkok)", "2026-10-29 11:04 UTC",
        # "2026-11-06 (Bangkok)" or a Buddhist-era year. Read the leading date and time and
        # the zone word; a file that gives no date falls back to the file time.
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[ T]+(\d{1,2}):(\d{2}))?", value)
        if not match:
            return mtime
        year, month, day, hour, minute = (int(part or 0) for part in match.groups())
        if year > 2400:
            year -= 543
        rest = value[match.end():]
        zone = re.search(r"(?<![\w])([+-])(\d{1,2})(?::?(\d{2}))?(?!\d)", rest)
        if re.search(r"(?<![A-Za-z])(?:UTC|GMT|Z)(?![A-Za-z])", rest, re.I):
            offset = 0
        elif zone:
            offset = (int(zone[2]) * 60 + int(zone[3] or 0)) * (-1 if zone[1] == "-" else 1)
        else:
            offset = 7 * 60          # the user's clock: Bangkok
        try:
            stamp = datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(minutes=offset)))
            return stamp.timestamp()
        except (ValueError, OverflowError, OSError):
            return mtime

    @staticmethod
    def _agent(owner, model):
        words = (owner + " " + model).lower()
        name = " ".join((MODELS.search(words) or [""])[0].split())
        if "codex" in words or name.startswith("gpt-"):
            return "Codex", name
        if "claude" in words:
            return "Claude", name
        if "gemini" in words or "antigravity" in words:
            return "Gemini", name
        return "", ""

    @staticmethod
    def _state(fields, sections, activity, age, stale_seconds):
        explicit = fields.get("state", fields.get("status", "")).lower().strip()
        doing = activity.lower()
        blocked = sections.get("blocked", sections.get("blocked / limits", "")).strip(" \n-*").lower()
        if explicit in ("done", "complete", "completed") or re.match(r"^(done|complete|completed)[.!]?$", doing):
            return "done"
        if (explicit == "blocked" or doing.startswith(("blocked", "waiting for", "not started (waiting")) or
                (blocked and not re.match(r"^(none\b|no (?:(?:current|remaining) )?block(?:er|s)?\b|n/a\b|[-?]+$)", blocked))):
            return "blocked"
        if explicit == "stale" or age >= stale_seconds or not fields.get("owner", "").strip():
            return "stale"
        return "working"

    def read_task(self, path, now, checkout_branch=""):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                return None
            with path.open("rb") as stream:
                head = stream.read(HEAD_BYTES + 1)
        except OSError:
            return None
        if len(head) > HEAD_BYTES:
            head = head[:HEAD_BYTES].rpartition(b"\n")[0]
        source = head.decode("utf-8-sig", errors="replace")
        headings = list(SECTION.finditer(source))
        meta = source[:headings[0].start()] if headings else source
        fields = {m[1].lower(): m[2].strip() for m in FIELD.finditer(meta)}
        sections = {}
        for i, match in enumerate(headings):
            end = headings[i + 1].start() if i + 1 < len(headings) else len(source)
            sections.setdefault(match[1].lower().strip(), source[match.end():end])
        title = TITLE.search(meta)
        task = self._plain(title[1] if title else "", 140)
        updated = min(now, self._updated(fields.get("updated", ""), info.st_mtime))
        doing = self._activity(sections.get("doing now", ""))
        agent, model = self._agent(fields.get("owner", ""), fields.get("model", ""))
        recorded_branch = re.split(r"[\s;]", fields.get("branch", ""), maxsplit=1)[0]
        if not recorded_branch:
            recorded_branch = checkout_branch
        commit = SHA.match(fields.get("last commit", ""))
        return {
            "name": task or self._plain(path.stem, 140),
            "agent": agent,
            "model": model,
            "activity": doing,
            "state": self._state(fields, sections, doing, now - updated, self.stale_seconds),
            "updated": int(updated),
            "branch": self._plain(recorded_branch, 110) if BRANCH.fullmatch(recorded_branch) else "",
            "commit": commit[0] if commit else "",
        }

    @staticmethod
    def _git_line(path):
        try:
            with path.open("rb") as stream:
                return stream.read(1024).decode("utf-8", errors="replace").strip()
        except OSError:
            return ""

    def _checkouts(self):
        """Use Git's linked worktree pointers. Never visit sibling repos or logs."""
        common = self.root / ".git"
        if common.is_file():
            pointer = self._git_line(common)
            if not pointer.startswith("gitdir: "):
                yield self.root, common
                return
            own = (self.root / pointer[8:]).resolve()
            yield self.root, own
            common = (own / self._git_line(own / "commondir")).resolve()
            if common == own or own.parent != common / "worktrees":
                return
            yield common.parent, common
        else:
            yield self.root, common
        try:
            entries = sorted((common / "worktrees").iterdir())
        except OSError:
            return
        for entry in entries:
            pointer = self._git_line(entry / "gitdir")
            if not pointer:
                continue
            checkout_git = (entry / pointer).resolve()
            if checkout_git.name != ".git" or checkout_git.parent == self.root:
                continue
            back = self._git_line(checkout_git)
            if back.startswith("gitdir: ") and (checkout_git.parent / back[8:]).resolve() == entry:
                yield checkout_git.parent, entry

    @staticmethod
    def _task_files(checkout):
        directory = checkout / "handoff" / "tasks"
        try:
            if directory.resolve() != directory or not (checkout / "HANDOFF.md").is_file():
                return None
            return sorted(directory.glob("*.md"))
        except OSError:
            return None

    def read(self):
        now = time.time()
        tasks = {}
        available = False
        for checkout, git_dir in self._checkouts():
            paths = self._task_files(checkout)
            if paths is None:
                continue
            available = True
            head = self._git_line(git_dir / "HEAD")
            branch = head[len("ref: refs/heads/"):] if head.startswith("ref: refs/heads/") else ""
            for path in paths:
                task = self.read_task(path, now, branch)
                previous = tasks.get(path.stem)
                if task and (previous is None or task["updated"] > previous["updated"]):
                    tasks[path.stem] = task
        return {
            "ok": True,
            "available": available,
            "tasks": sorted(tasks.values(), key=lambda task: -task["updated"]),
        }
