"""Read the reset time out of a usage-limit message.

Real samples (2026-10-29): Codex "try again at 3:26 AM.", Claude
"resets 11:50am (Asia/Bangkok)", Claude weekly "resets Nov 3, 9am (Asia/Bangkok)",
Gemini "Please retry in 1h2m3.5s". The patterns live in config/ai_watch.json
(reset_patterns), so a new wording is a config edit.
"""
import datetime as dt
import re

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
UNITS = (("d", 86400), ("h", 3600), ("m", 60), ("s", 1))
DUR = re.compile(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)")


def _offset(text):
    sign = -1 if text.startswith("-") else 1
    h, _, m = text.lstrip("+-").partition(":")
    return dt.timezone(sign * dt.timedelta(hours=int(h), minutes=int(m or 0)))


class ResetClock:
    def __init__(self, cfg):
        pats = cfg.get("reset_patterns", {})
        self.abs = re.compile(pats["abs"], re.I) if pats.get("abs") else None
        self.rel = re.compile(pats["rel"], re.I) if pats.get("rel") else None
        self.zones = {k: v for k, v in cfg.get("timezones", {}).items() if not k.startswith("_")}
        # A clock time with no zone ("try again at 3:26 AM") is the PC's own clock:
        # the CLI prints it in local time while its log stamps are UTC (2026-10-29).
        name = cfg.get("default_timezone", "local")
        self.default = None if name == "local" else self.zone(name, None)

    def zone(self, name, fallback):
        """A named zone: zoneinfo if the PC has tzdata, else the config offset
        table, else the zone the message was written in."""
        if not name:
            return fallback
        if re.fullmatch(r"[+-]\d{1,2}(:\d{2})?", name):
            return _offset(name)
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(name)
        except Exception:  # no tzdata on this PC (2026-10-29)
            pass
        return _offset(self.zones[name]) if name in self.zones else fallback

    def parse(self, text, written_at):
        """Absolute reset time (aware datetime) or None. written_at is the
        aware time the message was written: a bare clock time means the next
        such time after it, a duration counts from it."""
        if self.rel:
            m = self.rel.search(text)
            if m:
                secs = 0.0
                for num, unit in DUR.findall(m.group("dur")):
                    u = unit.lower()
                    secs += float(num) * next((s for k, s in UNITS if u.startswith(k)), 0)
                if secs:
                    return written_at + dt.timedelta(seconds=secs)
        if self.abs:
            for m in self.abs.finditer(text):
                got = self._absolute(m, written_at)
                if got:
                    return got
        return None

    def _absolute(self, m, written_at):
        h, mi = int(m.group("h")), int(m.group("m") or 0)
        ap = (m.group("ap") or "").lower().replace(".", "")
        if ap:
            if not 1 <= h <= 12:
                return None
            h = h % 12 + (12 if ap.startswith("p") else 0)
        elif not m.group("m") and not m.group("mon"):
            return None  # a bare number ("until 3") is not a time
        if h > 23 or mi > 59:
            return None
        tz = self.zone(m.group("tz"), self.default)
        base = written_at.astimezone(tz)  # tz None = the PC's local zone
        mon = (m.group("mon") or "")[:3].lower()
        if mon:
            if mon not in MONTHS:
                return None
            cand = base.replace(month=MONTHS[mon], day=int(m.group("day")), hour=h,
                                minute=mi, second=0, microsecond=0)
            if cand < base - dt.timedelta(days=1):
                cand = cand.replace(year=cand.year + 1)
            return cand
        cand = base.replace(hour=h, minute=mi, second=0, microsecond=0)
        if cand < base - dt.timedelta(minutes=1):
            cand += dt.timedelta(days=1)
        return cand
