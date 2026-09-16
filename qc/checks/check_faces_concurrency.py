"""Poll/live races and partial-frame timeouts must not duplicate or corrupt arrivals."""
import importlib.util
import socket
import threading
import types
import urllib.error
from collections import OrderedDict

import qc as F

AREA = "hub"
TITLE = "concurrent arrivals, token renewal and interrupted frames remain consistent"
SOLO = True


def module(name):
    spec = importlib.util.spec_from_file_location(
        "_faces_race_" + name, F.CODE / "apps/faces" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def event(camera=""):
    return dict(id="p1", who="Ann", known=True, when="2026-09-14T10:00:00",
                camera=camera, source="ws" if camera else "poll")


def run(t):
    svc, ws = module("service"), module("wsclient")
    state = svc.State("reconize")
    entered, release, second_read = (threading.Event() for _ in range(3))
    errors = []

    class PausedRecent(OrderedDict):
        def get(self, key, default=None):
            value = super().get(key, default)
            if threading.current_thread().name == "first-arrival":
                entered.set()
                if not release.wait(3):
                    raise RuntimeError("test did not release first arrival")
            else:
                second_read.set()
            return value

    state.recent = PausedRecent()

    def ingest(camera):
        try:
            state.note(event(camera))
        except Exception as exc:
            errors.append(str(exc))

    first = threading.Thread(target=ingest, args=("",), name="first-arrival", daemon=True)
    second = threading.Thread(target=ingest, args=("door-in",), daemon=True)
    first.start()
    try:
        t.ok(entered.wait(2), "first arrival paused between lookup and insert")
        second.start()
        t.ok(not second_read.wait(0.2), "second arrival cannot enter incomplete duplicate lookup")
    finally:
        release.set()
        first.join(3)
        if second.ident is not None:
            second.join(3)
    t.ok(not errors and not first.is_alive() and not second.is_alive(),
         "both ingestion calls finish without error", errors)
    t.eq(len(state.people), 1, "simultaneous copies publish one arrival")
    t.eq(state.people[0]["camera"], "door-in", "live camera improves the same arrival")
    snapshot = state.snapshot()
    state.note(event("another-door"))
    state.people[0]["camera"] = "changed-after-snapshot"
    t.eq(snapshot["people"][0]["camera"], "door-in", "HTTP snapshot owns its event copies")

    # Pause real poll processing at its HTTP boundary while the live feed publishes.
    state = svc.State("reconize")
    state.token, state.token_dies = "poll-token", 10**12
    entered.clear()
    release.clear()
    polled = []
    def fetch(src, token, page):
        if page != 1:
            return [], ""
        entered.set()
        release.wait(3)
        return [dict(id="row1", participant_id="p1", name="Ann",
                     detected_at="2026-09-14T10:00:00", status="matched"),
                dict(id="row2", participant_id="p2", name="Ben",
                     detected_at="2026-09-14T09:59:59", status="matched")], ""
    state._fetch = fetch
    worker = threading.Thread(target=lambda: polled.append(state.poll_once()), daemon=True)
    worker.start()
    try:
        t.ok(entered.wait(2), "poll paused while reading history")
        state.note(event("door-in"))
    finally:
        release.set()
        worker.join(3)
    t.ok(not worker.is_alive() and polled, "poll resumes after live publication")
    t.eq(sorted(e["id"] for e in state.people), ["p1", "p2"],
         "poll and live arrivals both survive with no duplicate")
    t.eq(next(e for e in state.people if e["id"] == "p1")["camera"], "door-in",
         "history cannot erase live camera information")

    # Both callers reach an expired token while the first HTTP refresh is paused.
    state = svc.State("reconize")
    entered.clear()
    release.clear()
    overlap = threading.Event()
    calls, tokens = [], []

    def login():
        calls.append(1)
        if len(calls) > 1:
            overlap.set()
        entered.set()
        release.wait(3)
        state.token, state.token_dies = "replacement", 10**12
        return state.token, ""

    state.login = login
    first = threading.Thread(target=lambda: tokens.append(state.token_now()), daemon=True)
    second = threading.Thread(target=lambda: tokens.append(state.token_now()), daemon=True)
    first.start()
    try:
        t.ok(entered.wait(2), "first token refresh has started")
        second.start()
        t.ok(not overlap.wait(0.2), "a second expired-token caller waits for the refresh")
    finally:
        release.set()
        first.join(3)
        second.join(3)
    t.eq(len(calls), 1, "concurrent callers perform one login")
    t.eq(tokens, [("replacement", ""), ("replacement", "")], "both callers receive refreshed token")
    state.invalidate_token("old-token")
    t.eq(state.token, "replacement", "stale rejection keeps the newer login")
    state.invalidate_token("replacement")
    t.eq(state.token, "", "rejection of current token requests renewal")

    state.token = "old-token"
    original_urlopen = svc.urllib.request.urlopen
    def stale_http(req, **kwargs):
        state.token = "new-token"
        raise urllib.error.HTTPError(req.full_url, 401, "expired", {}, None)
    try:
        svc.urllib.request.urlopen = stale_http
        rows, why = state._fetch(state.poll_source(), "old-token", 1)
        t.ok(not rows and why, "HTTP refusal is reported")
        t.eq(state.token, "new-token", "actual stale HTTP 401 preserves replacement token")
    finally:
        svc.urllib.request.urlopen = original_urlopen

    class ScriptedSocket:
        def __init__(self, chunks):
            self.chunks = iter(chunks)

        def recv(self, size):
            chunk = next(self.chunks)
            if isinstance(chunk, Exception):
                raise chunk
            return chunk

        def settimeout(self, seconds):
            pass

    feed = ws.Feed("ws://127.0.0.1/unused")
    feed.sock = ScriptedSocket([socket.timeout(), b'\x81\x02{}'])
    messages = feed.messages()
    t.eq(next(messages), None, "clean idle timeout keeps connection usable")
    t.eq(next(messages), {}, "next complete frame survives clean idle timeout")
    for partial in (b'\x81\x02', b'\x81\x7e\x00', b'\x81\x7e\x00\x02{',
                    b'\x81\x7f\x00\x00', b'\x81\x02{'):
        feed = ws.Feed("ws://127.0.0.1/unused")
        feed.sock = ScriptedSocket([partial, socket.timeout()])
        why = ""
        try:
            next(feed.messages())
        except ws.FeedClosed as exc:
            why = str(exc)
        t.contains(why, "mid-frame", "consumed-header timeout reconnects instead of losing framing")

    # Failed upgrade must release the socket even though connect() returns no Feed.
    closed = []
    original_connect, original_close = ws.Feed.connect, ws.Feed.close
    def failed_connect(self):
        raise ws.FeedClosed("upgrade refused")
    try:
        ws.Feed.connect = failed_connect
        ws.Feed.close = lambda self: closed.append(True)
        try:
            ws.connect("ws://127.0.0.1/unused")
        except ws.FeedClosed:
            pass
        t.eq(closed, [True], "failed upgrade closes its connection")
    finally:
        ws.Feed.connect, ws.Feed.close = original_connect, original_close

    # Capture main's thread target, then drive real reconnect handling with a fake feed.
    state = svc.State("reconize")
    state.token, state.token_dies = "old-token", 10**12
    targets, waits = [], []
    class CaptureThread:
        def __init__(self, target, **kwargs):
            targets.append(target)
        def start(self):
            pass
    class Server:
        def __init__(self, *args):
            pass
        def serve_forever(self):
            raise KeyboardInterrupt()
    svc.State = lambda partner: state
    svc.threading = types.SimpleNamespace(Thread=CaptureThread)
    svc.ThreadingHTTPServer = Server
    svc.main([])
    clock = [0.0]
    class StopTest(Exception):
        pass
    def sleep(delay):
        waits.append(delay)
        if len(waits) == 4:
            raise StopTest()
    attempts = []
    class ClosingFeed:
        def messages(self, **kwargs):
            if len(attempts) == 3:
                clock[0] += 31
                yield {"name": "Ann", "participant_id": "p1", "at": "2026-09-14T10:00:00"}
            if len(attempts) == 1:
                state.token = "new-token"
                raise svc.wsclient.FeedClosed("expired", svc.wsclient.CLOSE_BAD_TOKEN)
            raise svc.wsclient.FeedClosed("disconnected")
        def close(self):
            pass
    original_connect = svc.wsclient.connect
    try:
        def connect(url):
            attempts.append(url)
            return ClosingFeed()
        svc.wsclient.connect = connect
        svc.time = types.SimpleNamespace(time=lambda: 100, monotonic=lambda: clock[0], sleep=sleep)
        try:
            next(fn for fn in targets if fn.__name__ == "live_feed")()
        except StopTest:
            pass
        t.eq(waits, [1.0, 2.0, 1.0, 2.0],
             "immediate disconnect backs off; sustained connection resets wait")
        t.eq(state.token, "new-token", "actual stale WebSocket rejection preserves newer token")
    finally:
        svc.wsclient.connect = original_connect
