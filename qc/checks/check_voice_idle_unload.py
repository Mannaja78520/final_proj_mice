"""The Voice helper lets its models go from the GPU when nobody asks, and wakes them on demand.

User 2026-11-26: the PC lagged (SolidWorks, typing) while the Voice helper held 5.4 GB of the
12 GB card doing nothing. apps/voice/idle_unload.py frees it after idleUnloadMinutes (15, 0 =
never) without a request. Checked with a fake brain and a fake clock: nothing unloads before
the time, while a request is in flight, in presence/greeter mode, or when switched off; a
listed foreground app (yieldVramWhen) shortens the wait to a minute; the first request after
a sleep is the one that wakes it, shows "warming up" and has its cost kept; the helper's
config file carries the defaults and the service wires the hooks in.
"""
import json
import sys

import qc as F

AREA = "voice"
TITLE = "idle Voice models leave the GPU after N minutes and come back on the next request"


class FakeBrain:
    def __init__(self, **cfg):
        self.cfg = cfg
        self.unloads = 0

    def unload(self):
        self.unloads += 1


def run(t):
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import idle_unload as iu

    now = [0.0]
    apps = {"explorer.exe"}
    used = {"mib": 7686}

    def make(**cfg):
        b = FakeBrain(**cfg)
        u = iu.IdleUnloader(b, clock=lambda: now[0], names=lambda: apps, poll=1,
                            vram_used=lambda: used["mib"])
        return b, u

    b, u = make(idleUnloadMinutes=15)
    now[0] = 14 * 60
    t.ok(not u.tick() and b.unloads == 0, "nothing unloads before the idle time")
    now[0] = 15 * 60 + 1
    used["mib"] = 7686

    def free_on_unload():
        used["mib"] = 2300
    b.unload = lambda: (setattr(b, "unloads", b.unloads + 1), free_on_unload())
    t.ok(u.tick() and b.unloads == 1, "after the idle time the models are unloaded")
    t.ok(u.last_unload and u.last_unload["freedMiB"] == 5386,
         "and how much GPU memory it freed is recorded", repr(u.last_unload))
    t.ok(not u.tick() and b.unloads == 1, "it does not unload twice in a row")

    # wake on the next request, measured
    now[0] += 10
    woke = u.request_start("/ask")
    t.ok(woke and u.warming and u.state()["warming"], "the first request after a sleep reports warming up")
    now[0] += 4.2
    u.request_end()
    t.ok(u.first_request_ms == 4200 and not u.asleep and not u.warming,
         "and its wake-up cost is kept", repr(u.state()))
    now[0] += 5
    u.request_start("/ask")
    u.request_end()
    t.ok(u.first_request_ms == 4200, "a request when it was awake does not overwrite that number")

    # guards
    b, u = make(idleUnloadMinutes=15)
    u.request_start("/ask")
    now[0] += 3600
    t.ok(not u.tick() and b.unloads == 0, "never while a request is being answered")
    u.request_end()
    b, u = make(idleUnloadMinutes=15, presence={"on": True, "seconds": 60})
    now[0] += 3600
    t.ok(not u.tick() and b.unloads == 0, "never in presence/greeter mode")
    b, u = make(idleUnloadMinutes=0)
    now[0] += 3600
    t.ok(not u.tick() and b.unloads == 0, "idleUnloadMinutes 0 means never")

    # yield to a foreground app
    b, u = make(idleUnloadMinutes=15, yieldVramWhen=["SLDWORKS.exe"], yieldVramMinutes=1)
    now[0] += 90
    t.ok(not u.tick() and b.unloads == 0, "a listed app that is not running changes nothing")
    apps.add("sldworks.exe")
    t.ok(u.tick() and b.unloads == 1, "while a listed app runs, an idle helper unloads after a minute")
    b, u = make(idleUnloadMinutes=15, yieldVramWhen=["SLDWORKS.exe"])
    now[0] += 30
    u.request_start("/ask")
    now[0] += 20
    u.request_end()
    now[0] += 50
    t.ok(not u.tick(), "but not while it was used a moment ago")
    b, u = make(idleUnloadMinutes=0, yieldVramWhen=["SLDWORKS.exe"])
    now[0] += 600
    t.ok(not u.tick(), "the switch off (0) also turns the yield off")
    apps.discard("sldworks.exe")

    # config + wiring
    cfg = json.loads((F.CODE / "config" / "voice.json").read_text(encoding="utf-8"))
    t.ok(cfg.get("idleUnloadMinutes") == 15 and cfg.get("yieldVramWhen") == [] and
         cfg.get("yieldVramMinutes") == 1, "config/voice.json carries the defaults (15, none, 1)")
    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    t.ok("idle.request_start(path)" in src and "idle.request_end()" in src
         and "brain.idle_unload = IdleUnloader(brain)" in src and '"idleUnload"' in src
         and "_asleep_note" in src,
         "the service counts requests, starts the watcher and shows the state in /health")
