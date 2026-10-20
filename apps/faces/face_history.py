"""Shared history cursor and local-time parsing for the watcher and Voice."""
import threading
from datetime import datetime


def local_when(value):
    """Keep legacy naive times local; convert offset-bearing times first."""
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone().replace(tzinfo=None) if stamp.tzinfo else stamp
    except (TypeError, ValueError, OverflowError):
        return None


class HistoryCursor:
    """Deliver committed rows in sequence order, advancing after consumption.

    latest_seq is only the initial watermark. A partial page or a delayed
    timestamp must never move the cursor past rows we have not processed.
    Each consumer owns a reader, bound to its endpoint/configuration.
    """
    def __init__(self):
        self.after_seq = None
        self._lock = threading.RLock()

    def poll(self, source, fetch, consume, max_pages=20):
        with self._lock:
            try:
                cfg = source["cursor"]
                if self.after_seq is None:
                    doc, why = fetch(source["path"].replace("{page}", "1"))
                    if why:
                        return why
                    latest = doc[cfg["latest"]]
                    if latest is not None and (type(latest) is not int or latest < 0):
                        raise ValueError("invalid latest sequence")
                    self.after_seq = latest or 0
                    return ""
                for _ in range(max_pages):
                    path = cfg["path"].replace("{after_seq}", str(self.after_seq))
                    doc, why = fetch(path)
                    if why:
                        return why
                    rows = doc[source.get("items") or "items"]
                    if not isinstance(rows, list):
                        raise ValueError("history items are not a list")
                    previous = self.after_seq
                    for row in rows:
                        seq = row[cfg["seq"]]
                        if type(seq) is not int or seq <= previous:
                            raise ValueError("history sequence did not advance")
                        previous = seq
                    nxt = doc[cfg["next"]]
                    if type(nxt) is not int or nxt != previous:
                        raise ValueError("history next sequence does not match its rows")
                    for row in rows:
                        consume(row)
                        self.after_seq = row[cfg["seq"]]
                    if not rows:
                        break
                    latest = doc.get(cfg["latest"])
                    if type(latest) is int and latest == self.after_seq:
                        break
                return ""
            except Exception as exc:  # leave the last successfully consumed row intact
                return "their history cursor could not be read (%s)" % exc
