"""The hub's side of the shared job scheduler: one order for the GPU across programs.

Voice, the face app, video tools and the hub itself all want the same GPU. Each
program orders its OWN work (tools/jobsched.py); this adds the order BETWEEN
programs: a program asks `/api/scheduler/acquire` for a place, works, then
`/release`. Loopback only (a LAN visitor must not be able to hold the GPU), and
every lease expires, so a crashed holder cannot freeze the rest.
"""
import json
import sys
import threading

NOT_MINE = object()
_hub = None
_table = None
_lock = threading.Lock()


def bind(hub):
    global _hub
    _hub = hub


def table():
    global _table
    with _lock:
        if _table is None:
            sys.path.insert(0, str(_hub.asset("tools")))
            import jobsched
            sched = jobsched.Scheduler.from_file(_hub.asset("config", "scheduler.json"))
            _table = jobsched.LeaseTable(sched, resource="gpu", ttl=60)
        return _table


def gate(klass):
    """For the hub's own heavy jobs (video sound, encoding): `with gate("encode"):`."""
    return table().sched.gate(klass)


class SchedulerRoutes:
    def api_scheduler(self, method, path, q):
        if not path.startswith("/api/scheduler"):
            return NOT_MINE
        local = self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")
        try:
            if path == "/api/scheduler" and method == "GET":
                return self.send_json({"ok": True, **table().status()})
            if method != "POST" or path not in ("/api/scheduler/acquire", "/api/scheduler/release"):
                return self.send_err("not a scheduler call", 404)
            if not local:
                return self.send_err("only programs on this PC may take a place", 403)
            data = json.loads(self.body(8192).decode("utf-8") or "{}")
            if path.endswith("release"):
                return self.send_json({"ok": table().release(str(data.get("token", "")))})
            wait = max(0.0, min(float(data.get("wait", 20)), 60.0))
            try:
                token = table().acquire(str(data.get("class", "normal")), str(data.get("owner", ""))[:40], wait)
            except TimeoutError as exc:
                return self.send_json({"ok": False, "error": str(exc)}, code=408)
            return self.send_json({"ok": True, "token": token})
        except (ValueError, TypeError) as exc:
            return self.send_err(str(exc), 400)
