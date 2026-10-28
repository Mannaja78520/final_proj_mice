"""Where each AI writes its limit notice, read incrementally (only new bytes).

One class per log format; config/ai_watch.json picks the class per provider
by "kind", so a new provider with a known format needs no code. Offsets live
in the watcher state, so a restart never re-reads a whole 300 MB history.
"""
import datetime as dt
import glob
import json
import os
import re
from dataclasses import dataclass, field


@dataclass
class LimitHit:
    provider: str
    source: str             # file the notice is in
    session: str            # what to resume: a session id, or the log file
    cwd: str
    text: str
    written_at: dt.datetime
    size_after: int         # source size right after the notice: growth = someone continued
    extra: dict = field(default_factory=dict)

    @property
    def key(self):
        return "%s|%s|%s" % (self.provider, self.session, self.written_at.isoformat())


def _ts(value, fallback):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return fallback


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


class Source:
    """A glob of append-only files. Subclasses turn one new line into a hit."""

    def __init__(self, provider, spec, matcher, expand):
        self.provider = provider
        self.glob = expand(spec["glob"])
        self.prefilter = spec.get("prefilter") or []
        self.matcher = matcher

    def files(self):
        return sorted(glob.glob(self.glob))

    def scan(self, offsets, meta, oldest):
        """New hits since the stored offset. A file first seen is read from
        the start but only if it changed after `oldest` (history skip)."""
        for path in self.files():
            try:
                st = os.stat(path)
            except OSError:
                continue
            start = offsets.get(path)
            if start is None and st.st_mtime < oldest.timestamp():
                offsets[path] = st.st_size
                continue
            start = start or 0
            if st.st_size < start:      # rewritten file: read again
                start = 0
            if st.st_size == start:
                continue
            with open(path, "rb") as f:
                f.seek(start)
                data = f.read()
            end = data.rfind(b"\n") + 1  # leave a half-written line for next time
            offsets[path] = start + end
            pos = start
            for raw in data[:end].splitlines(keepends=True):
                pos += len(raw)
                line = raw.decode("utf-8", "replace")
                self.note_meta(path, line, meta)
                if self.prefilter and not any(p in line for p in self.prefilter):
                    continue
                hit = self.parse(path, line, meta.get(path, {}), st)
                if hit and self.matcher.is_limit(self.provider, hit.text):
                    hit.size_after = pos
                    yield hit

    def note_meta(self, path, line, meta):
        pass

    def parse(self, path, line, meta, st):
        raise NotImplementedError


class ClaudeTranscript(Source):
    def parse(self, path, line, meta, st):
        try:
            row = json.loads(line)
        except ValueError:
            return None
        msg = row.get("message") or {}
        if row.get("type") != "assistant" or msg.get("model") != "<synthetic>":
            return None
        now = dt.datetime.now(dt.timezone.utc)
        return LimitHit(self.provider, path, row.get("sessionId", path), row.get("cwd", ""),
                        _text_of(msg.get("content")), _ts(row.get("timestamp"), now), 0)


class CodexRollout(Source):
    def note_meta(self, path, line, meta):
        if path not in meta and '"session_meta"' in line[:200]:
            try:
                p = json.loads(line).get("payload", {})
                meta[path] = {"session": p.get("session_id") or p.get("id", ""),
                              "cwd": p.get("cwd", "")}
            except ValueError:
                pass

    def parse(self, path, line, meta, st):
        try:
            row = json.loads(line)
        except ValueError:
            return None
        p = row.get("payload") or {}
        err = p.get("error") if isinstance(p.get("error"), dict) else {}
        text = " ".join(str(x) for x in (err.get("message"), err.get("codex_error_info"),
                                          p.get("message") if p.get("type") == "error" else None) if x)
        if not text:
            return None
        if not meta:  # offset started past the header (history skip): read it now
            local = {}
            with open(path, encoding="utf-8", errors="replace") as f:
                self.note_meta(path, f.readline(), local)
            meta = local.get(path, {})
        m = re.search(r"([0-9a-f]{8}-[0-9a-f-]{27})\.jsonl$", path)
        sid = meta.get("session") or (m.group(1) if m else path)
        now = dt.datetime.now(dt.timezone.utc)
        return LimitHit(self.provider, path, sid, meta.get("cwd", ""), text,
                        _ts(row.get("timestamp"), now), 0)


class TextLog(Source):
    """Plain output of a worker this watcher started (stdout+stderr)."""

    def parse(self, path, line, meta, st):
        written = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc)
        return LimitHit(self.provider, path, path, "", line.strip(), written, 0)


KINDS = {"claude_transcript": ClaudeTranscript, "codex_rollout": CodexRollout,
         "text_log": TextLog}
